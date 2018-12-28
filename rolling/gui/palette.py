# coding: utf-8
import typing

from rolling.gui.kernel import Kernel


PALETTE_CHARACTER = "CHARACTER"


class PaletteGenerator(object):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    def create_palette(self) -> typing.List[typing.Tuple[str, str, str, str, str, str]]:
        palette = [
            (PALETTE_CHARACTER, '', '', '', 'light blue,bold', ''),
        ]
        source_types = list(
            self._kernel.world_map_source.legend.get_all_types()
        ) + list(self._kernel.tile_map_legend.get_all_types())

        for world_map_tile_type in source_types:
            # palette can be:
            # (name, foreground, background, mono, foreground_high, background_high)
            palette.append(
                (
                    world_map_tile_type.get_full_id(),
                    world_map_tile_type.foreground_color,
                    world_map_tile_type.background_color,
                    world_map_tile_type.mono,
                    world_map_tile_type.foreground_high_color,
                    world_map_tile_type.background_high_color,
                )
            )

        return palette
