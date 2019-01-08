# coding: utf-8
import typing

import dataclasses
from rolling.map.geography import WorldMapGeography
from rolling.map.geography import ZoneMapGeography
from rolling.map.legend import WorldMapLegend
from rolling.map.legend import ZoneMapLegend
from rolling.map.type.world import WorldMapTileType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel

BLOCK_LEGEND_NAME = "LEGEND"
BLOCK_GEOGRAPHY_NAME = "GEO"


class MapSource(object):
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
        # self._river = self._create_river(raw_source)
        # self._others = self._create_others(raw_source)

    @property
    def raw_source(self) -> str:
        return self._raw_source

    @property
    def legend(self) -> WorldMapLegend:
        return self._legend

    @property
    def geography(self) -> WorldMapGeography:
        return self._geography

    def _create_legend(self, raw_source: str) -> WorldMapLegend:
        # TODO BS 2018-11-03: raise if not found
        legend_lines = self._get_blocks(raw_source, BLOCK_LEGEND_NAME)[0]
        raw_legend = {}

        for legend_line in legend_lines:
            key, value = legend_line.split(" ")
            raw_legend[key] = value

        return WorldMapLegend(raw_legend, WorldMapTileType)

    def _create_geography(self, raw_source: str) -> WorldMapGeography:
        # TODO BS 2018-11-03: raise if not found
        geography_lines = self._get_blocks(raw_source, BLOCK_GEOGRAPHY_NAME)[0]
        return WorldMapGeography(self._legend, geography_lines)


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
        geography_lines = self._get_blocks(
            raw_source, BLOCK_GEOGRAPHY_NAME, strip_=False
        )[0]
        return ZoneMapGeography(
            self.legend, geography_lines, missing_right_tile_str=" "
        )


@dataclasses.dataclass(frozen=True)
class ZoneMap(object):
    row_i: int
    col_i: int
    source: ZoneMapSource
