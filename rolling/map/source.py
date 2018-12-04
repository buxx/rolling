# coding: utf-8
import typing

from rolling.map.legend import WorldMapLegend
from rolling.map.world.geography import WorldMapGeography

BLOCK_LEGEND_NAME = "LEGEND"
BLOCK_GEOGRAPHY_NAME = "GEO"


class WorldMapSource(object):
    def __init__(self, raw_source: str) -> None:
        self._legend = self._create_legend(raw_source)
        self._geography = self._create_geography(raw_source)
        # self._river = self._create_river(raw_source)
        # self._others = self._create_others(raw_source)

    @property
    def legend(self) -> WorldMapLegend:
        return self._legend

    @property
    def geography(self) -> WorldMapGeography:
        return self._geography

    def _get_blocks(
        self, source: str, block_name: str
    ) -> typing.List[typing.List[str]]:
        found = False
        block_lines = []
        blocks = []
        lines = source.splitlines()
        # ensure empty line
        lines.append("") if lines[-1].strip() else None

        for raw_line in lines:
            line = raw_line.strip()

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

    def _create_legend(self, raw_source: str) -> WorldMapLegend:
        # TODO BS 2018-11-03: raise if not found
        legend_lines = self._get_blocks(raw_source, BLOCK_LEGEND_NAME)[0]
        raw_legend = {}

        for legend_line in legend_lines:
            key, value = legend_line.split(" ")
            raw_legend[key] = value

        return WorldMapLegend(raw_legend)

    def _create_geography(self, raw_source: str) -> WorldMapGeography:
        # TODO BS 2018-11-03: raise if not found
        geography_lines = self._get_blocks(raw_source, BLOCK_GEOGRAPHY_NAME)[0]
        return WorldMapGeography(self._legend, geography_lines)
