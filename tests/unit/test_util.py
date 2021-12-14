# coding: utf-8
import pytest

from rolling.util import CornerEnum
from rolling.util import get_corner
from rolling.util import get_opposite_zone_place
from rolling.util import square_walker


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
        "X": None,
    }

    for row_i, line in enumerate(
        [line.strip() for line in str_map.splitlines() if line.strip()]
    ):
        for col_i, charr in enumerate(line):
            real_row_i = row_i - 1
            real_col_i = col_i - 1
            expected_corner = corners[charr]

            assert expected_corner == get_corner(9, 9, real_row_i, real_col_i)


@pytest.mark.parametrize(
    "expected_row_i,expected_col_i,from_,zone_width,zone_height",
    [
        (0, 4, CornerEnum.TOP, 9, 9),
        (7, 2, CornerEnum.TOP_RIGHT, 9, 9),
        (4, 8, CornerEnum.RIGHT, 9, 9),
        (7, 6, CornerEnum.BOTTOM_RIGHT, 9, 9),
        (8, 4, CornerEnum.BOTTOM, 9, 9),
        (1, 6, CornerEnum.BOTTOM_LEFT, 9, 9),
        (4, 0, CornerEnum.LEFT, 9, 9),
        (1, 2, CornerEnum.TOP_LEFT, 9, 9),
    ],
)
def test_get_opposite_zone_place(
    expected_row_i: int,
    expected_col_i: int,
    from_: CornerEnum,
    zone_width: int,
    zone_height: int,
):
    assert get_opposite_zone_place(
        from_=from_, zone_width=zone_width, zone_height=zone_height
    ) == (
        expected_row_i,
        expected_col_i,
    )


def test_square_walker():
    walker = square_walker(0, 0)
    points = [next(walker) for i in range(9)]
    assert points == [
        (0, 0),
        (-1, -1),
        (0, -1),
        (1, -1),
        (1, 0),
        (1, 1),
        (0, 1),
        (-1, 1),
        (-1, 0),
    ]


def test_square_walker2():
    walker = square_walker(0, 0)
    points = [next(walker) for i in range(25)]
    assert points == [
        (0, 0),
        (-1, -1),
        (0, -1),
        (1, -1),
        (1, 0),
        (1, 1),
        (0, 1),
        (-1, 1),
        (-1, 0),
        (-2, -2),
        (-1, -2),
        (0, -2),
        (1, -2),
        (2, -2),
        (2, -1),
        (2, 0),
        (2, 1),
        (2, 2),
        (1, 2),
        (0, 2),
        (-1, 2),
        (-2, 2),
        (-2, 1),
        (-2, 0),
        (-2, -1),
    ]
