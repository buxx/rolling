# coding: utf-8
import dataclasses
import random
import typing

from rolling.exception import RollingError
from rolling.map.geography import WorldMapGeography
from rolling.map.geography import ZoneMapGeography
from rolling.map.legend import WorldMapLegend
from rolling.map.legend import ZoneMapLegend
from rolling.map.meta import WorldMapMeta
from rolling.map.type.property.traversable import traversable_properties
from rolling.map.type.world import WorldMapTileType
from rolling.model.meta import TransportType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel

BLOCK_LEGEND_NAME = "LEGEND"
BLOCK_GEOGRAPHY_NAME = "GEO"
BLOCK_META_NAME = "META"


class MapSource:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def _get_blocks(
        self, source: str, block_name: str, strip_: bool = True
    ) -> typing.List[typing.List[str]]:
        found = False
        block_lines = []
        blocks = []
        lines = source.splitlines()
        # ensure empty line
        lines.append("") if lines[-1].strip() else None

        for raw_line in lines:
            line = raw_line.strip() if strip_ else raw_line

            # Inspect enter or out searched block
            if line.startswith("::") or line == "":
                if line.startswith("::{}".format(block_name)):
                    found = True
                    continue
                elif found:
                    found = False
                    blocks.append(block_lines)

            if found:
                block_lines.append(line)

        return blocks


class WorldMapSource(MapSource):
    def __init__(self, kernel: "Kernel", raw_source: str) -> None:
        super().__init__(kernel)
        self._raw_source = raw_source
        self._legend = self._create_legend(raw_source)
        self._geography = self._create_geography(raw_source)
        self._meta = self._create_meta(raw_source)
        # self._river = self._create_river(raw_source)
        # self._others = self._create_others(raw_source)

    @property
    def raw_source(self) -> str:
        return self._raw_source

    @property
    def legend(self) -> WorldMapLegend:
        return self._legend

    @property
    def meta(self) -> WorldMapMeta:
        return self._meta

    @property
    def geography(self) -> WorldMapGeography:
        return self._geography

    def _create_legend(self, raw_source: str) -> WorldMapLegend:
        # FIXME NOW BS: 2019-01-28: Get it from kernel if no legend in file
        try:
            legend_lines = self._get_blocks(raw_source, BLOCK_LEGEND_NAME)[0]
            # TODO BS 2019-01-28: Use appropriate exception
        except IndexError:
            return self._kernel.world_map_legend

        raw_legend = {}

        for legend_line in legend_lines:
            key, value = legend_line.split(" ")
            raw_legend[key] = value

        return WorldMapLegend(raw_legend, WorldMapTileType)

    def _create_geography(self, raw_source: str) -> WorldMapGeography:
        # TODO BS 2018-11-03: raise if not found
        geography_lines = self._get_blocks(raw_source, BLOCK_GEOGRAPHY_NAME)[0]
        return WorldMapGeography(self._legend, geography_lines)

    def _create_meta(self, raw_source: str) -> WorldMapMeta:
        try:
            lines = self._get_blocks(raw_source, BLOCK_META_NAME)[0]
        except IndexError:
            lines = []
        return WorldMapMeta(self._kernel, lines)


class ZoneMapSource(MapSource):
    def __init__(self, kernel: "Kernel", raw_source: str) -> None:
        super().__init__(kernel)
        self._raw_source = raw_source
        self._geography = self._create_geography(raw_source)

    @property
    def raw_source(self) -> str:
        return self._raw_source

    @property
    def legend(self) -> ZoneMapLegend:
        return self._kernel.tile_map_legend

    @property
    def geography(self) -> ZoneMapGeography:
        return self._geography

    def _create_geography(self, raw_source: str) -> ZoneMapGeography:
        # TODO BS 2018-11-03: raise if not found
        geography_lines = self._get_blocks(raw_source, BLOCK_GEOGRAPHY_NAME, strip_=False)[0]
        return ZoneMapGeography(self.legend, geography_lines, missing_right_tile_str=" ")

    def get_start_zone_coordinates(
        self, world_row_i: int, world_col_i: int
    ) -> typing.Tuple[int, int]:
        available_coordinates: typing.List[typing.Tuple[int, int]] = []

        for row_i, row in enumerate(self.geography.rows):
            for col_i, map_tile_type in enumerate(row):
                if traversable_properties[map_tile_type].get(TransportType.WALKING.value):
                    available_coordinates.append((row_i, col_i))

        if not available_coordinates:
            raise RollingError(f"No traversable coordinate in zone {world_row_i},{world_col_i}")

        return random.choice(available_coordinates)


@dataclasses.dataclass(frozen=True)
class ZoneMap:
    row_i: int
    col_i: int
    source: ZoneMapSource
