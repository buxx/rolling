# coding: utf-8
import typing

from rolling.map.source import WorldMapSource

WORLD_VOID_STR = " "


class WorldMapRenderEngine(object):
    def __init__(self, world_map_source: WorldMapSource) -> None:
        self._world_map_source = world_map_source
        self._rows: typing.List[str] = None
        self._attributes = None

    @property
    def rows(self) -> typing.List[str]:
        return self._rows

    @property
    def attributes(self):
        return self._attributes

    def render(self, width: int, height: int) -> None:
        map_width = self._world_map_source.geography.width
        map_height = self._world_map_source.geography.height

        # compute static void left and right
        width_difference = width - map_width
        if width_difference > 1:
            left_void = width_difference // 2
            right_void = left_void + 1 if width_difference % 2 else left_void
        elif width_difference == 1:
            left_void = 1
            right_void = 0
        else:
            left_void = 0
            right_void = 0

        # compute static void top and bottom
        height_difference = height - map_height
        if height_difference > 1:
            top_void = height_difference // 2
            bottom_void = top_void + 1 if height_difference % 2 else top_void
        elif height_difference == 1:
            top_void = 1
            bottom_void = 0
        else:
            top_void = 0
            bottom_void = 0

        # prepare void values
        self._rows = [WORLD_VOID_STR * width] * top_void
        map_display_height = map_height if height_difference > 0 else height
        self._rows.extend([WORLD_VOID_STR * left_void] * map_display_height)
        self._rows.extend([WORLD_VOID_STR * width] * bottom_void)
        self._attributes = []

        # fill rows and attributes line per line
        for row_i, row in enumerate(self._world_map_source.geography.rows):

            # do not fill outside screen
            if row_i == height:
                break

            for col_i, col in enumerate(row):

                # do not fill outside screen
                if col_i == width:
                    break

                tile_str = self._world_map_source.legend.get_str_with_type(col)
                self._rows[row_i + top_void] += tile_str
                # self._rows[row_i+top_void] += u'a'

        # fill right
        for row_i, row in enumerate(
            self._rows[top_void : len(self._rows) - bottom_void], start=top_void
        ):
            self._rows[row_i] += WORLD_VOID_STR * right_void

        # encode
        for row_i, row in enumerate(self._rows):
            self._rows[row_i] = row.encode()

        # compute attributes
        for row_i, row in enumerate(self._rows):
            self._attributes.append([("WORLD_TILE__SEA", len(row))])

        pass
        # self._rows = [u'⁙'.encode()*width]*height
        # self._attributes = [
        #     [('test', len(u'⁙'.encode()*width))],
        # ]*height
