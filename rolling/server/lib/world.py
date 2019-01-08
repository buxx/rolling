# coding: utf-8
import typing

from rolling.exception import NoDefaultTileType
from rolling.kernel import Kernel
from rolling.model.tile import WorldMapTileTypeModel
from rolling.model.world import WorldMapLegendModel
from rolling.model.world import WorldMapModel


class WorldLib(object):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    def get_legend(self) -> WorldMapLegendModel:
        try:
            legend_default_type = (
                self._kernel.world_map_source.legend.get_default_type()
            )
            default_type = WorldMapTileTypeModel(
                id=legend_default_type.id,
                foreground_color=legend_default_type.foreground_color,
                background_color=legend_default_type.background_color,
                mono=legend_default_type.mono,
                foreground_high_color=legend_default_type.foreground_high_color,
                background_high_color=legend_default_type.background_high_color,
            )
        except NoDefaultTileType:
            default_type = None

        all_types: typing.List[WorldMapTileTypeModel] = []
        for legend_type in self._kernel.world_map_source.legend.get_all_types():
            all_types.append(
                WorldMapTileTypeModel(
                    id=legend_type.id,
                    foreground_color=legend_type.foreground_color,
                    background_color=legend_type.background_color,
                    mono=legend_type.mono,
                    foreground_high_color=legend_type.foreground_high_color,
                    background_high_color=legend_type.background_high_color,
                )
            )

        legend = WorldMapLegendModel(default_type=default_type, all_types=all_types)
        return legend

    def get_world(self) -> WorldMapModel:
        return WorldMapModel(raw_source=self._kernel.world_map_source.raw_source)
