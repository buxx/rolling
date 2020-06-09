# coding: utf-8
import dataclasses
import datetime as datetime_
import typing

import serpyco

from rolling.exception import RollingError
from rolling.model.stuff import StuffModel
from rolling.server.document.business import OfferItemPosition
from rolling.server.document.business import OfferOperand
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.gui.map.object import DisplayObject
    from rolling.kernel import Kernel


MINIMUM_BEFORE_TIRED = 49
MINIMUM_BEFORE_EXHAUSTED = 79
FIGHT_AP_CONSUME = 3
FIGHT_LP_REQUIRE = 1.0
FIGHT_TIREDNESS_INCREASE = 35


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
class PickFromInventoryQueryModel:
    callback_url: str
    cancel_url: str
    title: typing.Optional[str] = None
    resource_id: typing.Optional[str] = None
    resource_quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    stuff_id: typing.Optional[str] = None
    stuff_quantity: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)


@dataclasses.dataclass
class ConversationsQueryModel:
    with_character_id: typing.Optional[str] = None


@dataclasses.dataclass
class GetCharacterWithPathModel:
    character_id: str
    with_character_id: str


@dataclasses.dataclass
class GetOfferPathModel:
    character_id: str
    offer_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class SeeOfferPathModel:
    character_id: str
    owner_id: str
    offer_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class SeeOfferQueryModel:
    mark_as_read: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class DealOfferQueryModel:
    request_item_id: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    offer_item_id: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    confirm: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class RemoveOfferItemPathModel:
    character_id: str
    offer_id: int = serpyco.number_field(cast_on_load=True)
    item_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class UpdateOfferQueryModel:
    open: int = serpyco.number_field(cast_on_load=True, default=0)
    close: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class AddOfferItemQuery:
    position: OfferItemPosition
    value: typing.Optional[str] = None
    quantity: float = serpyco.number_field(cast_on_load=True, default=None)
    # bellow: from inventory pick
    resource_id: typing.Optional[str] = None
    resource_quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    stuff_id: typing.Optional[str] = None
    stuff_quantity: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)


@dataclasses.dataclass
class CreateOfferQueryModel:
    permanent: int = serpyco.number_field(cast_on_load=True, default=0)
    with_character_id: typing.Optional[str] = None


@dataclasses.dataclass
class CreateOfferBodyModel:
    title: typing.Optional[str] = None


@dataclasses.dataclass
class GetOfferBodyModel:
    request_operand: typing.Optional[str] = None
    offer_operand: typing.Optional[str] = None


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
class GetLookCharacterModel:
    character_id: str
    with_character_id: str


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
class WithCharacterActionModel:
    character_id: str
    with_character_id: str
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
    tiredness: int = 0

    _display_object = None

    bags: typing.List[StuffModel] = serpyco.field(default_factory=list)
    # FIXME BS NOW: fill them from doc
    weapon: typing.Optional[StuffModel] = None
    shield: typing.Optional[StuffModel] = None
    armor: typing.Optional[StuffModel] = None

    unread_event: bool = False
    unread_zone_message: bool = False
    unread_conversation: bool = False
    unvote_affinity_relation: bool = False
    unread_transactions: bool = False

    @property
    def tired(self) -> bool:
        return self.tiredness > MINIMUM_BEFORE_TIRED

    @property
    def exhausted(self) -> bool:
        return self.tiredness > MINIMUM_BEFORE_EXHAUSTED

    @property
    def vulnerable(self) -> bool:
        return not self.is_defend_ready()

    def is_attack_ready(self) -> bool:
        return (
            not self.exhausted
            and self.action_points >= FIGHT_AP_CONSUME
            and self.life_points > FIGHT_LP_REQUIRE
        )

    def is_defend_ready(self) -> bool:
        # FIXME BS: keep exhausted ?
        return not self.exhausted and self.life_points > FIGHT_LP_REQUIRE

    def associate_display_object(self, display_object: "DisplayObject") -> None:
        self._display_object = display_object

    @property
    def force_weapon_multiplier(self) -> float:
        # FIXME: character spec
        return 1.0

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
