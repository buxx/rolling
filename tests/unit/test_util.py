# coding: utf-8
from rolling.util import get_corner, CornerEnum


def test_get_corner():
    str_map = """
    00001112222
    0000XXX2222
    000XXXXX222
    00XXXXXXX22
    7XXXXXXXXX3
    7XXXXXXXXX3
    7XXXXXXXXX3
    66XXXXXXX44
    666XXXXX444
    6666XXX4444
    66665554444
    """
    corners = {
        "0": CornerEnum.TOP_LEFT,
        "1": CornerEnum.TOP,
        "2": CornerEnum.TOP_RIGHT,
        "3": CornerEnum.RIGHT,
        "4": CornerEnum.BOTTOM_RIGHT,
        "5": CornerEnum.BOTTOM,
        "6": CornerEnum.BOTTOM_LEFT,
        "7": CornerEnum.LEFT,
        "X": None
    }

    for row_i, line in enumerate([line.strip() for line in str_map.splitlines() if line.strip()]):
        for col_i, charr in enumerate(line):
            real_row_i = row_i - 1
            real_col_i = col_i - 1
            expected_corner = corners[charr]

            assert expected_corner == get_corner(9, 9, real_row_i, real_col_i)
