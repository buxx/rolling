# coding: utf-8
import urwid

from rolling.gui.image.convert import convert_img_to_urwid
from rolling.gui.palette import PALETTE_BG_COLOR


class ImageWidget(urwid.Widget):
    _sizing = frozenset([urwid.BOX])

    def __init__(self, image_path: str, callback):
        self._image_path = image_path
        self._callback = callback

    def render(self, size, focus=False):
        width, height = size
        colors = convert_img_to_urwid(
            self._image_path, max_width=width, max_height=height
        )

        # TODO BS 2019-06-27: Optimize by prepare lists
        rows = []
        attributes = []

        for i in range(height):
            row_str = " " * width
            rows.append(row_str.encode())

        image_columns = len(colors[0])
        image_rows = len(colors)

        if image_columns > width:
            image_columns = width

        if image_rows > height:
            image_rows = height

        empty_columns = width - image_columns
        empty_rows = height - image_rows

        left_empty_columns = 0
        right_empty_columns = 0
        if empty_columns:
            left_empty_columns = empty_columns // 2
            right_empty_columns = (
                empty_columns // 2 if not empty_columns % 2 else empty_columns // 2 + 1
            )

        top_empty_rows = 0
        bottom_empty_rows = 0
        if empty_rows:
            top_empty_rows = empty_rows // 2
            bottom_empty_rows = (
                empty_rows // 2 if not empty_rows % 2 else empty_rows // 2 + 1
            )

        for i in range(top_empty_rows):
            attributes.append([(None, width)])

        for i in range(image_rows):
            image_attributes = []
            for ii in range(image_columns):
                # TODO BS 2019-06-27: Optimize by use real number of same color
                image_attributes.append((PALETTE_BG_COLOR.format(colors[i][ii]), 1))

            attributes.append(
                [(None, left_empty_columns)]
                + image_attributes
                + [(None, right_empty_columns)]
            )

        for i in range(bottom_empty_rows):
            attributes.append([(None, width)])

        # FIXME BS 2019-06-27: screen seems broken when terminal is too small (and to big image ?)
        return urwid.TextCanvas(text=rows, attr=attributes, maxcol=width)

    def selectable(self):
        self._callback()

    def keypress(self, size, key):
        pass
