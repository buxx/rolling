# coding: utf-8
import typing
from enum import Enum

from pip._internal.utils.misc import enum

from rolling.exception import RollingError
from rolling.kernel import Kernel
from rolling.map.source import WorldMapSource
from rolling.map.source import ZoneMap
from rolling.map.source import ZoneMapSource

if typing.TYPE_CHECKING:
    from rolling.map.generator.filler import TileMapFiller, FillerFactory


class Border(Enum):
    top_left = "top_left"
    top = "top"
    top_right = "top_right"
    right = "right"
    bottom_right = "bottom_right"
    bottom = "bottom"
    bottom_left = "bottom_left"
    left = "left"


class TileMapGenerator(object):
    def __init__(self, kernel: Kernel, filler: "TileMapFiller") -> None:
        self._kernel = kernel
        self._filler = filler
        self._current_raw_source = ""

    @property
    def kernel(self) -> Kernel:
        return self._kernel

    def generate(
        self,
        width: int,
        height: typing.Optional[int] = None,
        north_west_map: typing.Optional[ZoneMapSource] = None,
        north_map: typing.Optional[ZoneMapSource] = None,
        north_est_map: typing.Optional[ZoneMapSource] = None,
        west_map: typing.Optional[ZoneMapSource] = None,
        est_map: typing.Optional[ZoneMapSource] = None,
        south_west_map: typing.Optional[ZoneMapSource] = None,
        south_map: typing.Optional[ZoneMapSource] = None,
        south_est_map: typing.Optional[ZoneMapSource] = None,
    ) -> ZoneMapSource:
        height = height or width

        # Must be odd
        if not width % 2 or not height % 2:
            raise RollingError(
                "Width and height must be odd: given values are {}x{}".format(
                    width, height
                )
            )

        self._current_raw_source = "::GEO\n"
        part_len = width // 3
        top_void_part = 0, part_len - 1
        bottom_void_part = height - part_len, height - 1
        reduce_counter = part_len
        reduce2_counter = 0

        for row_i in range(height):

            if row_i <= top_void_part[1]:
                left_void_part = 0, part_len - 1 - row_i
                right_void_part = width - part_len + row_i, width - 1
            elif row_i >= bottom_void_part[0]:
                left_void_part = 0, part_len - reduce_counter
                right_void_part = width - reduce2_counter - 1, width - 1
                reduce_counter -= 1
                reduce2_counter += 1
            else:
                left_void_part = -1, -1
                right_void_part = width + 1, width + 1

            for col_i in range(width):
                # Fill with empty
                # TODO BS 2018-12-28: Idea can be fill other map tiles
                if col_i <= left_void_part[1] or col_i >= right_void_part[0]:
                    self._current_raw_source += " "  # FIXME fom type
                else:
                    is_border = False
                    distance_from_border = 0
                    border = None

                    # TODO BS 2019-03-07: give info about border

                    self._current_raw_source += self._filler.get_char(
                        self,
                        is_border=is_border,
                        distance_from_border=distance_from_border,
                        border=border,
                    )

            self._current_raw_source += "\n"

        return ZoneMapSource(self._kernel, self._current_raw_source)


class FromWorldMapGenerator(object):
    def __init__(
        self,
        kernel: Kernel,
        world_map_source: WorldMapSource,
        filler_factory: "FillerFactory",
        default_map_width: int,
        default_map_height: typing.Optional[int] = None,
    ) -> None:
        self._kernel = kernel
        self._world_map_source = world_map_source
        self._filler_factory = filler_factory
        self._default_map_width = default_map_width
        self._default_map_height = default_map_height

    def generate(self) -> typing.List[ZoneMap]:
        tile_maps: typing.List[ZoneMap] = []

        for row_i, row in enumerate(self._world_map_source.geography.rows):
            for col_i, world_map_tile_type in enumerate(row):

                filler = self._filler_factory.create(
                    world_map_tile_type, row_i, col_i, self._world_map_source
                )
                tile_map_generator = TileMapGenerator(self._kernel, filler)
                tile_map_source = tile_map_generator.generate(
                    # TODO BS 2018-12-29: Give around tile map sources
                    self._default_map_width,
                    self._default_map_height,
                )
                tile_maps.append(ZoneMap(row_i, col_i, tile_map_source))

        return tile_maps
