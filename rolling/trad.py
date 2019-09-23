# coding: utf-8
import typing

from rolling.model.measure import Unit


class GlobalTranslation:
    def __init__(self) -> None:
        self._translation: typing.Dict[typing.Any, str] = {
            Unit.LITTER: "litre",
            Unit.CUBIC: "mètre cube",
            Unit.GRAM: "gramme",
        }

    def get(self, key: typing.Any) -> str:
        return self._translation[key]
