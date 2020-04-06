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
    name: str = serpyco.string_field(metadata={"label": "Name"}, min_length=2, max_length=32)
    max_life_comp: float = serpyco.number_field(
        metadata={"label": "Max life points (max 5.0)"}, minimum=1, maximum=5
    )


@dataclasses.dataclass
class GetCharacterPathModel:
    character_id: str


@dataclasses.dataclass
class UpdateCharacterCardBodyModel:
    attack_allowed_loss_rate: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    defend_allowed_loss_rate: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )


@dataclasses.dataclass
class GetAffinityPathModel:
    character_id: str
    affinity_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class GetAffinityRelationPathModel:
    character_id: str
    relation_character_id: str
    affinity_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class ManageAffinityQueryModel:
    join_type: typing.Optional[str] = None
    confirm: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class ManageAffinityRelationQueryModel:
    disallowed: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class ManageAffinityRelationBodyModel:
    status: typing.Optional[str] = None


@dataclasses.dataclass
class ModifyAffinityRelationQueryModel:
    request: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    rejected: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    fighter: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)


@dataclasses.dataclass
class GetConversationPathModel:
    character_id: str
    conversation_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class GetMoveZoneInfosModel:
    character_id: str
    world_row_i: int = serpyco.number_field(cast_on_load=True)
    world_col_i: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class PostTakeStuffModelModel:
    character_id: str
    stuff_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class GetLookStuffModelModel:
    character_id: str
    stuff_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class TakeResourceModel:
    quantity: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


@dataclasses.dataclass
class GetLookResourceModel:
    character_id: str
    resource_id: str
    row_i: int = serpyco.number_field(cast_on_load=True)
    col_i: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class GetLookInventoryResourceModel:
    character_id: str
    resource_id: str


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
    # FIXME BS 2019-09-09: should be int no ?
    action_type: ActionType
    action_description_id: str
    stuff_id: int = serpyco.field(cast_on_load=True)


@dataclasses.dataclass
class WithBuildActionModel:
    character_id: str
    action_type: ActionType
    action_description_id: str
    build_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class WithResourceActionModel:
    character_id: str
    resource_id: str
    action_type: ActionType
    action_description_id: str


@dataclasses.dataclass
class MoveCharacterQueryModel:
    to_world_row: int = serpyco.number_field(cast_on_load=True)
    to_world_col: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class DescribeStoryQueryModel:
    event_id: int = serpyco.number_field(cast_on_load=True)
    story_page_id: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    mark_read: int = serpyco.number_field(cast_on_load=True, default=0)


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
    attack_allowed_loss_rate: int
    defend_allowed_loss_rate: int
    # FIXME BS 2019-10-14: base code of that
    ability_ids: typing.List[str] = serpyco.field(default_factory=list)

    world_col_i: int = None
    world_row_i: int = None
    zone_col_i: int = None
    zone_row_i: int = None

    feel_thirsty: bool = True
    dehydrated: bool = False
    feel_hungry: bool = True
    starved: bool = False

    _display_object = None

    bags: typing.List[StuffModel] = serpyco.field(default_factory=list)

    weight_overcharge: bool = False
    clutter_overcharge: bool = False
    unread_event: bool = False
    unread_zone_message: bool = False
    unread_conversation: bool = False
    unvote_affinity_relation: bool = False

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
        return kernel.game.config.default_clutter_capacity + sum(
            [bag.clutter_capacity for bag in self.bags]
        )

    def have_one_of_abilities(self, abilities: typing.List[str]) -> bool:
        for ability in abilities:
            if ability in self.ability_ids:
                return True
        return False


@dataclasses.dataclass
class CharacterEventModel:
    id: int
    datetime: datetime_.datetime
    turn: int
    text: str
    unread: bool


@dataclasses.dataclass
class ListOfStrModel:
    items: typing.List[typing.Tuple[str, typing.Optional[str]]]
