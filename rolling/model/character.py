# coding: utf-8
import dataclasses

import datetime as datetime_
import serpyco
import typing

from rolling.exception import RollingError
from rolling.model.knowledge import KnowledgeDescription
from rolling.model.skill import CharacterSkillModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from rolling.server.document.business import OfferItemPosition
import slugify

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.fight import Weapon
    from rolling.server.lib.fight import FightDetails


MINIMUM_BEFORE_TIRED = 49
MINIMUM_BEFORE_EXHAUSTED = 79
FIGHT_AP_CONSUME = 3
FIGHT_LP_REQUIRE = 1.0
FIGHT_TIREDNESS_INCREASE = 35
STRENGTH_SKILL_ID = "strength"
MAXIMUM_FORCE_WEAPON_MULTIPLIER = 2.0


@dataclasses.dataclass
class GetCharacterPathModel:
    character_id: str


@dataclasses.dataclass
class OnPlaceActionQuery:
    filter_action_types: typing.Optional[str] = None
    from_main_action_name: typing.Optional[str] = None


@dataclasses.dataclass
class ExplodeTakeQuery:
    explode_take: int = serpyco.number_field(cast_on_load=True, default=1)


@dataclasses.dataclass
class GetCharacterQueryModel:
    compute_unread_event: int = serpyco.number_field(cast_on_load=True, default=0)
    compute_unread_zone_message: int = serpyco.number_field(
        cast_on_load=True, default=0
    )
    compute_unread_conversation: int = serpyco.number_field(
        cast_on_load=True, default=0
    )
    compute_unvote_affinity_relation: int = serpyco.number_field(
        cast_on_load=True, default=0
    )
    compute_unread_transactions: int = serpyco.number_field(
        cast_on_load=True, default=0
    )
    compute_pending_actions: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class ChooseAvatarQuery:
    choose: typing.Optional[int] = serpyco.field(cast_on_load=True, default=None)


@dataclasses.dataclass
class SharedInventoryQueryModel:
    affinity_id: int = serpyco.field(cast_on_load=True)
    resource_id: typing.Optional[str] = None
    resource_quantity: typing.Optional[str] = None
    stuff_id: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    stuff_quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )

    @property
    def stuff_quantity_int(self) -> typing.Optional[int]:
        if self.stuff_quantity is None:
            return None

        return int(self.stuff_quantity)


@dataclasses.dataclass
class GetCharacterAndPendingActionPathModel:
    character_id: str
    pending_action_id: int = serpyco.field(cast_on_load=True)


@dataclasses.dataclass
class CreateCharacterQueryModel:
    spawn_to: typing.Optional[int] = serpyco.field(cast_on_load=True, default=0)


@dataclasses.dataclass
class PendingActionQueryModel:
    do: int = serpyco.field(cast_on_load=True, default=0)


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
    stuff_quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )

    @property
    def stuff_quantity_int(self) -> typing.Optional[int]:
        if self.stuff_quantity is None:
            return None

        return int(self.stuff_quantity)


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
class DoorPathModel:
    character_id: str
    door_id: int = serpyco.number_field(cast_on_load=True)


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
    request_item_id: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    offer_item_id: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
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
    stuff_quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )

    @property
    def stuff_quantity_int(self) -> typing.Optional[int]:
        if self.stuff_quantity is None:
            return None

        return int(self.stuff_quantity)


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
    request: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    rejected: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    fighter: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )


@dataclasses.dataclass
class GetConversationPathModel:
    character_id: str
    conversation_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class GetConversationQueryModel:
    conversation_id: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    current_zone: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class PostConversationBodyModel:
    message: typing.Optional[str] = serpyco.number_field(default=None)


@dataclasses.dataclass
class PostSetupConversationQueryModel:
    character_id: typing.List[str] = serpyco.field(default_factory=list)


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
class SetupCharacterSpritesheetQuery:
    validate: typing.Optional[str] = None


@dataclasses.dataclass
class GetLookStuffModelModel:
    character_id: str
    stuff_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class ChooseBetweenStuffInventoryStuffModelModel:
    character_id: str
    stuff_id: str


@dataclasses.dataclass
class GetLookCharacterModel:
    character_id: str
    with_character_id: str


@dataclasses.dataclass
class TakeResourceModel:
    quantity: typing.Optional[str] = None


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
    story_page_id: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    mark_read: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class CharacterModel:
    id: str
    name: str

    @property
    def name_slug(self) -> str:
        return slugify.slugify(self.name)

    alive: bool

    spritesheet_filename: str
    spritesheet_set: bool
    background_story: str
    max_life_comp: float
    hunting_and_collecting_comp: float
    find_water_comp: float
    life_points: float
    action_points: float
    max_action_points: float
    attack_allowed_loss_rate: int
    defend_allowed_loss_rate: int
    skills: typing.Dict[str, CharacterSkillModel]
    knowledges: typing.Dict[str, KnowledgeDescription]
    # NOTE: must be feed (like with knowledges) at creation
    ability_ids: typing.List[str] = serpyco.field(default_factory=list)

    world_col_i: int = None
    world_row_i: int = None
    zone_col_i: int = None
    zone_row_i: int = None

    tiredness: int = 0  # %
    thirst: float = 0  # %
    hunger: float = 0  # %

    is_thirsty: bool = False
    is_hunger: bool = False

    @property
    def is_tired(self) -> bool:
        return self.tired

    @property
    def is_vulnerable(self) -> bool:
        return self.vulnerable

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
    pending_actions: int = 0

    # Must match with data/character_avatar/{uuid}.png
    avatar_uuid: typing.Optional[str] = None
    avatar_is_validated: bool = False

    tracim_user_id: typing.Optional[int] = None
    tracim_home_space_id: typing.Optional[int] = None
    tracim_password: typing.Optional[str] = None

    @property
    def tired(self) -> bool:
        return self.tiredness > MINIMUM_BEFORE_TIRED

    @property
    def is_exhausted(self) -> bool:
        return self.tiredness > MINIMUM_BEFORE_EXHAUSTED

    @property
    def vulnerable(self) -> bool:
        return not self.is_defend_ready

    @property
    def is_attack_ready(self) -> bool:
        return (
            not self.is_exhausted
            and self.action_points >= FIGHT_AP_CONSUME
            and self.life_points > FIGHT_LP_REQUIRE
        )

    @property
    def is_defend_ready(self) -> bool:
        # FIXME BS: keep exhausted ?
        return not self.is_exhausted and self.life_points > FIGHT_LP_REQUIRE

    def associate_display_object(self, display_object: "DisplayObject") -> None:
        self._display_object = display_object

    def force_weapon_multiplier(
        self, details: typing.Optional["FightDetails"] = None
    ) -> float:
        skill_value = self.get_skill_value(STRENGTH_SKILL_ID)
        force_weapon_multiplier_ = min(MAXIMUM_FORCE_WEAPON_MULTIPLIER, skill_value)

        if details is not None:
            details.new_debug_story_line("<li>")
            details.new_debug_story_line(
                f"force_weapon_multiplier = min({MAXIMUM_FORCE_WEAPON_MULTIPLIER}, '{self.name}'.{STRENGTH_SKILL_ID}({skill_value})) -> {force_weapon_multiplier_}"
            )
            details.new_debug_story_line("</li>")

        return force_weapon_multiplier_

    @property
    def display_object(self) -> "DisplayObject":
        if self._display_object is None:
            raise RollingError("You are trying to use property which is not set")

        return self._display_object

    def get_weight_capacity(self, kernel: "Kernel") -> float:
        return kernel.game.config.default_weight_capacity * max(
            2.0, self.get_skill_value(STRENGTH_SKILL_ID)
        )

    def get_clutter_capacity(self, kernel: "Kernel") -> float:
        return kernel.game.config.default_clutter_capacity + sum(
            [bag.clutter_capacity for bag in self.bags]
        )

    def have_abilities(self, abilities: typing.List[str]) -> typing.List[str]:
        have_abilities = []
        for ability_id in abilities:
            if ability_id in self.ability_ids:
                have_abilities.append(ability_id)
        return have_abilities

    def get_skill_value(self, skill_id: str) -> float:
        return self.skills[skill_id].value

    def have_knowledge(self, knowledge_id: str) -> bool:
        return knowledge_id in self.knowledges

    def get_with_weapon_coeff(
        self,
        weapon: "Weapon",
        kernel: "Kernel",
        details: typing.Optional["FightDetails"] = None,
    ) -> float:
        better_coeff = 1.0
        better_coeff_skill_name = "no special skill"
        for bonus_skill_id in weapon.get_bonus_with_skills(kernel):
            with_this_skill_bonus = self.get_skill_value(bonus_skill_id) / 2
            if with_this_skill_bonus > better_coeff:
                better_coeff = with_this_skill_bonus
                better_coeff_skill_name = bonus_skill_id

        if details is not None:
            details.new_debug_story_line("<li>")
            details.new_debug_story_line(
                f"with_weapon_coeff = {better_coeff_skill_name}({better_coeff})"
            )
            details.new_debug_story_line("</li>")

        return better_coeff


@dataclasses.dataclass
class CharacterModelApi:
    id: str
    name: str
    alive: bool
    max_life_comp: float
    hunting_and_collecting_comp: float
    find_water_comp: float
    life_points: float
    action_points: float
    max_action_points: float
    skills: typing.Dict[str, CharacterSkillModel]
    knowledges: typing.Dict[str, KnowledgeDescription]
    ability_ids: typing.List[str]

    world_col_i: int
    world_row_i: int
    zone_col_i: int
    zone_row_i: int

    tiredness: int
    thirst: float
    hunger: float

    is_thirsty: bool
    is_hunger: bool
    is_tired: bool
    is_exhausted: bool
    is_vulnerable: bool
    is_attack_ready: bool
    is_defend_ready: bool

    bags: typing.List[StuffModel]
    weapon: typing.Optional[StuffModel] = None
    shield: typing.Optional[StuffModel] = None
    armor: typing.Optional[StuffModel] = None

    unread_event: bool = False
    unread_zone_message: bool = False
    unread_conversation: bool = False
    unvote_affinity_relation: bool = False
    unread_transactions: bool = False
    pending_actions: int = 0

    avatar_uuid: typing.Optional[str] = None
    avatar_is_validated: bool = False
    spritesheet_filename: typing.Optional[str] = None
    spritesheet_set: bool = False


@dataclasses.dataclass
class CharacterEventModel:
    id: int
    datetime: datetime_.datetime
    turn: int
    text: str
    unread: bool
