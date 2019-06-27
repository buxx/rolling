# coding: utf-8
import typing

from rolling.kernel import Kernel

PALETTE_CHARACTER = "PALETTE_CHARACTER"
PALETTE_STUFF = "PALETTE_STUFF"
PALETTE_POSITION = "PALETTE_POSITION"
PALETTE_BG_COLOR = "BG_COLOR_H{}"


class PaletteGenerator:
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    def create_palette(self) -> typing.List[typing.Tuple[str, str, str, str, str, str]]:
        palette = [(PALETTE_CHARACTER, "", "", "", "light blue,bold", "")]
        source_types = list(self._kernel.world_map_legend.get_all_types()) + list(
            self._kernel.tile_map_legend.get_all_types()
        )

        for tile_type in source_types:
            # palette can be:
            # (name, foreground, background, mono, foreground_high, background_high)
            palette.append(
                (
                    tile_type.get_full_id(),
                    tile_type.foreground_color,
                    tile_type.background_color,
                    tile_type.mono,
                    tile_type.foreground_high_color,
                    tile_type.background_high_color,
                )
            )

        for i in range(256):
            palette.append((PALETTE_BG_COLOR.format(i), "white", "", "", "", f"h{i}"))

        return palette
