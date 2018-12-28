# coding: utf-8
import typing

from rolling.exception import RollingError
from rolling.gui.kernel import Kernel
from rolling.map.source import TileMapSource
from rolling.map.source import WorldMapSource
from rolling.map.type.world import WorldMapTileType

if typing.TYPE_CHECKING:
    from rolling.map.generator.filler import TileMapFiller


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
        north_west_type: typing.Type[WorldMapTileType],
        north_type: typing.Type[WorldMapTileType],
        north_est_type: typing.Type[WorldMapTileType],
        west_type: typing.Type[WorldMapTileType],
        est_type: typing.Type[WorldMapTileType],
        south_west_type: typing.Type[WorldMapTileType],
        south_type: typing.Type[WorldMapTileType],
        south_est_type: typing.Type[WorldMapTileType],
        generate_type: typing.Type[WorldMapTileType],
        width: int,
        height: typing.Optional[int] = None,
    ) -> TileMapSource:
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
                    self._current_raw_source += self._filler.get_char(self)

            self._current_raw_source += "\n"

        return TileMapSource(self._kernel, self._current_raw_source)


class FromWorldMapGenerator(object):
    def __init__(self, world_map_source: WorldMapSource) -> None:
        self._world_map_source = world_map_source

    def generate_types(self) -> typing.List[TileMapSource]:
        return []
