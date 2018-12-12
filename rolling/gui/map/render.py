# coding: utf-8
import typing

from rolling.exception import NoDefaultTileType
from rolling.exception import TileTypeNotFound
from rolling.map.source import WorldMapSource

WORLD_VOID_STR = " "


class WorldMapRenderEngine(object):
    def __init__(self, world_map_source: WorldMapSource) -> None:
        self._world_map_source = world_map_source
        self._rows: typing.List[str] = None
        self._attributes: typing.List[
            typing.List[typing.Tuple[typing.Optional[str], int]]
        ] = None

    @property
    def rows(self) -> typing.List[str]:
        return self._rows

    @property
    def attributes(self):
        return self._attributes

    def render(
        self,
        width: int,
        height: int,
        offset_horizontal: int = 0,
        offset_vertical: int = 0,
    ) -> None:
        map_width = self._world_map_source.geography.width
        map_height = self._world_map_source.geography.height

        try:
            default_type = self._world_map_source.legend.get_default_type()
            default_str = self._world_map_source.legend.get_str_with_type(default_type)
        except NoDefaultTileType:
            default_str = WORLD_VOID_STR

        # compute static void left and right
        width_difference = width - map_width
        if width_difference > 1:
            left_void = width_difference // 2
            right_void = left_void + 1 if width_difference % 2 else left_void
            left_void = left_void + offset_horizontal
            right_void = right_void - offset_horizontal
        elif width_difference == 1:
            left_void = 1 + offset_horizontal
            right_void = 0 - offset_horizontal
        else:
            left_void = 0 + offset_horizontal
            right_void = 0 - offset_horizontal

        # compute static void top and bottom
        height_difference = height - map_height
        if height_difference > 1:
            top_void = height_difference // 2
            bottom_void = top_void + 1 if height_difference % 2 else top_void
            top_void = top_void + offset_vertical
            bottom_void = bottom_void - offset_vertical
        elif height_difference == 1:
            top_void = 1 + offset_vertical
            bottom_void = 0 - offset_vertical
        else:
            top_void = 0 + offset_vertical
            bottom_void = 0 - offset_vertical

        # prepare void values
        self._rows = [default_str * width] * top_void
        map_display_height = (map_height if height_difference > 0 else height) - abs(
            offset_vertical
        )
        self._rows.extend([default_str * left_void] * map_display_height)
        self._rows.extend([default_str * width] * bottom_void)
        self._attributes: typing.List[
            typing.List[typing.Tuple[typing.Optional[str], int]]
        ] = []

        # fill rows and attributes line per line
        for row_i, row in enumerate(self._world_map_source.geography.rows):
            row_left_void = left_void
            row_right_void = right_void

            if (row_i + top_void) < 0:
                continue

            # do not fill outside screen
            if row_i == height:
                break

            # do not fill outside screen
            if row_i + top_void + 1 > height:
                break

            for col_i, col in enumerate(row):

                # do not fill outside screen
                if col_i == width:
                    break

                # Avoid char if left void need to suppress it
                if row_left_void < 0:
                    row_left_void += 1
                    continue

                # Avoid chars if right void need to suppress them
                if row_right_void < 0:
                    if col_i == len(row) + row_right_void:
                        break

                tile_str = self._world_map_source.legend.get_str_with_type(col)
                self._rows[row_i + top_void] += tile_str
                # self._rows[row_i+top_void] += u'a'

        # fill right
        for row_i, row in enumerate(
            self._rows[top_void : len(self._rows) - bottom_void], start=top_void
        ):
            self._rows[row_i] += default_str * right_void

        # compute attributes
        for row_i, row in enumerate(self._rows):
            last_seen_char = None
            self._attributes.append([])

            for char in row:
                if last_seen_char != char:
                    try:
                        tile_type = self._world_map_source.legend.get_type_with_str(
                            char
                        )
                        self._attributes[row_i].append(
                            (tile_type.get_full_id(), len(char.encode()))
                        )
                    except TileTypeNotFound:
                        self._attributes[row_i].append((None, 1))
                else:
                    self._attributes[row_i][-1] = (
                        self._attributes[row_i][-1][0],
                        self._attributes[row_i][-1][1] + len(char.encode()),
                    )
                last_seen_char = char

        # encode
        for row_i, row in enumerate(self._rows):
            self._rows[row_i] = row.encode()

        pass
        # self._rows = [u'⁙'.encode()*width]*height
        # self._attributes = [
        #     [('test', len(u'⁙'.encode()*width))],
        # ]*height
