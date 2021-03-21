# coding: utf-8
import typing

from rolling.model.measure import Unit


class GlobalTranslation:
    def __init__(self) -> None:
        self._translation: typing.Dict[typing.Any, str] = {
            Unit.LITTER: "litres",
            Unit.CUBIC: "mètre cubes",
            Unit.GRAM: "grammes",
            Unit.KILOGRAM: "kilo-grammes",
            Unit.UNIT: "unités",
        }
        self._short_translation: typing.Dict[typing.Any, str] = {
            Unit.LITTER: "l",
            Unit.CUBIC: "m³",
            Unit.GRAM: "g",
            Unit.KILOGRAM: "kg",
            Unit.UNIT: "u",
        }

    def get(self, key: typing.Any, short: bool = False) -> str:
        if short:
            return self._short_translation[key]
        return self._translation[key]
