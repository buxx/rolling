# coding: utf-8
import typing

from rolling.exception import NoDefaultTileType
from rolling.model.world import WorldAsCharacter, WorldMapLegendModel
from rolling.model.zone import WorldTileTypeModel

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class WorldLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def get_legend(self) -> WorldMapLegendModel:
        try:
            legend_default_type = (
                self._kernel.world_map_source.legend.get_default_type()
            )
            default_type = WorldTileTypeModel(
                id=legend_default_type.id,
                foreground_color=legend_default_type.foreground_color,
                background_color=legend_default_type.background_color,
                mono=legend_default_type.mono,
                foreground_high_color=legend_default_type.foreground_high_color,
                background_high_color=legend_default_type.background_high_color,
            )
        except NoDefaultTileType:
            default_type = None

        all_types: typing.List[WorldTileTypeModel] = []
        for legend_type in self._kernel.world_map_source.legend.get_all_types():
            all_types.append(
                WorldTileTypeModel(
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

    def get_world_as_character(self, character_id: str) -> WorldAsCharacter:
        # TODO : World will not be entirely visible for a character
        rows_as_character = []

        for original_row in self._kernel.world_map_source.geography.rows:
            row_as_character = []
            for original_tile_type in original_row:
                row_as_character.append(original_tile_type.id)
            rows_as_character.append(row_as_character)

        return WorldAsCharacter(rows=rows_as_character)
