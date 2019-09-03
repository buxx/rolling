# coding: utf-8
import dataclasses
import datetime as datetime_
import typing

import serpyco

from rolling.exception import RollingError
from rolling.model.stuff import StuffModel
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.gui.map.object import DisplayObject
    from rolling.kernel import Kernel


@dataclasses.dataclass
class CreateCharacterModel:
    name: str = serpyco.string_field(
        metadata={"label": "Name"}, min_length=2, max_length=32
    )
    background_story: str = serpyco.field(
        metadata={"label": "Background story", "is_text": True}
    )
    max_life_comp: float = serpyco.field(metadata={"label": "Max life points"})
    hunting_and_collecting_comp: float = serpyco.field(
        metadata={"label": "Hunt and collect ability"}
    )
    find_water_comp: float = serpyco.field(metadata={"label": "Find water ability"})


@dataclasses.dataclass
class GetCharacterPathModel:
    character_id: str


@dataclasses.dataclass
class PostTakeStuffModelModel:
    character_id: str
    stuff_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class GetLookStuffModelModel:
    character_id: str
    stuff_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class FillStuffWithResourceModel:
    resource_id: str = serpyco.field()


@dataclasses.dataclass
class CharacterActionModel:
    character_id: str
    action_description_id: str
    action_type: ActionType


@dataclasses.dataclass
class WithStuffActionModel:
    character_id: str
    stuff_id: str
    action_type: ActionType


@dataclasses.dataclass
class MoveCharacterQueryModel:
    to_world_row: int = serpyco.number_field(cast_on_load=True)
    to_world_col: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class CharacterModel:
    id: str
    name: str

    background_story: str
    max_life_comp: float
    hunting_and_collecting_comp: float
    find_water_comp: float
    life_points: float
    action_points: float

    world_col_i: int = None
    world_row_i: int = None
    zone_col_i: int = None
    zone_row_i: int = None

    feel_thirsty: bool = True
    dehydrated: bool = False

    _display_object = None

    bags: typing.List[StuffModel] = serpyco.field(default_factory=list)

    weight_overcharge: bool = False
    clutter_overcharge: bool = False

    def associate_display_object(self, display_object: "DisplayObject") -> None:
        self._display_object = display_object

    @property
    def display_object(self) -> "DisplayObject":
        if self._display_object is None:
            raise RollingError("You are trying to use property which is not set")

        return self._display_object

    def get_weight_capacity(self, kernel: "Kernel") -> float:
        return kernel.game.config.default_weight_capacity

    def get_clutter_capacity(self, kernel: "Kernel") -> float:
        return kernel.game.config.default_clutter_capacity + sum([bag.clutter_capacity for bag in self.bags])


@dataclasses.dataclass
class CharacterEventModel:
    datetime: datetime_.datetime
    text: str
