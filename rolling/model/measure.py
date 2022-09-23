# coding: utf-8
import enum


class Unit(enum.Enum):
    LITTER = "L"
    CUBIC = "M3"
    GRAM = "G"
    KILOGRAM = "KG"
    UNIT = "U"

    def as_str(self) -> str:
        if self == self.LITTER:
            return "l"
        if self == self.CUBIC:
            return "m³"
        if self == self.GRAM:
            return "g"
        if self == self.KILOGRAM:
            return "kg"
        if self == self.UNIT:
            return "u"

        raise NotImplementedError()
