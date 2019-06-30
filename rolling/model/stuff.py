# coding: utf-8
import dataclasses
import enum
import typing


class Unit(enum.Enum):
    LITTER = "L"


@dataclasses.dataclass
class StuffProperties:
    id: str
    name: str
    filled_at: typing.Optional[float] = None
    filled_unity: Unit = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    image: typing.Optional[str] = None
    # TODO BS 2019-06-07: Add list of "capacity" who are object can be used in action
    #  like "Drink", etc


@dataclasses.dataclass
class StuffModel:
    """existing stuff (on zone or carried)"""

    id: int
    name: str
    zone_col_i: int
    zone_row_i: int
    filled_at: typing.Optional[float] = None
    filled_unity: typing.Optional[Unit] = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    image: typing.Optional[str] = None

    def get_full_description(self) -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.weight:
            descriptions.append(f"{self.weight}g")

        if self.filled_at is not None:
            descriptions.append(f"{self.filled_at}%")

        return descriptions

    def get_light_description(self) -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.filled_at is not None:
            descriptions.append(f"{self.filled_at}%")

        return descriptions

    def get_name_and_light_description(self) -> str:
        descriptions = self.get_light_description()

        if not descriptions:
            return self.name

        description = "(" + ", ".join(descriptions) + ")"
        return f"{self.name} ({description})"


@dataclasses.dataclass
class ZoneGenerationStuff:
    stuff: StuffProperties
    probability: float
    meta: typing.Dict[str, typing.Any]


@dataclasses.dataclass
class CharacterInventoryModel:
    stuff: typing.List[StuffModel]
    weight: float = 0.0
    clutter: float = 0.0
