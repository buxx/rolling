# coding: utf-8
import dataclasses
import typing


@dataclasses.dataclass
class EmptyModel:
    pass


def get_on_and_around_coordinates(
    x: int, y: int
) -> typing.List[typing.Tuple[int, int]]:
    return [
        (x, y),
        (x - 1, y - 1),
        (x, y - 1),
        (x + 1, y - 1),
        (x - 1, y),
        (x + 1, y),
        (x - 1, y + 1),
        (x, y + 1),
        (x + 1, y + 1),
    ]
