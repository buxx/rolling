# coding: utf-8
import dataclasses

import abc
from enum import Enum
import typing
from rolling.server.link import QuickAction

from rolling.model.build import ZoneBuildModel
from rolling.model.data import ListOfItemModel
from rolling.rolling_types import ActionType


class ZoneEventType(Enum):
    PLAYER_MOVE = "PLAYER_MOVE"
    CLIENT_WANT_CLOSE = "CLIENT_WANT_CLOSE"
    SERVER_PERMIT_CLOSE = "SERVER_PERMIT_CLOSE"
    CHARACTER_ENTER_ZONE = "CHARACTER_ENTER_ZONE"
    CHARACTER_EXIT_ZONE = "CHARACTER_EXIT_ZONE"
    CLIENT_REQUIRE_AROUND = "CLIENT_REQUIRE_AROUND"
    THERE_IS_AROUND = "THERE_IS_AROUND"
    CLICK_ACTION_EVENT = "CLICK_ACTION_EVENT"
    CLIENT_REQUIRE_NEW_RESUME_TEXT = "CLIENT_REQUIRE_NEW_RESUME_TEXT"
    NEW_RESUME_TEXT = "NEW_RESUME_TEXT"
    NEW_BUILD = "NEW_BUILD"
    REMOVE_BUILD = "REMOVE_BUILD"
    REQUEST_CHAT = "REQUEST_CHAT"
    NEW_CHAT_MESSAGE = "NEW_CHAT_MESSAGE"
    ANIMATED_CORPSE_MOVE = "ANIMATED_CORPSE_MOVE"
    TOP_BAR_MESSAGE = "TOP_BAR_MESSAGE"
    NEW_ANIMATED_CORPSE = "NEW_ANIMATED_CORPSE"
    ZONE_TILE_REPLACE = "ZONE_TILE_REPLACE"
    ZONE_GROUND_RESOURCE_REMOVE = "ZONE_GROUND_RESOURCE_REMOVE"
    ZONE_GROUND_RESOURCE_APPEAR = "ZONE_GROUND_RESOURCE_APPEAR"
    ZONE_GROUND_STUFF_REMOVE = "ZONE_GROUND_STUFF_REMOVE"
    ZONE_GROUND_STUFF_APPEAR = "ZONE_GROUND_STUFF_APPEAR"


T = typing.TypeVar("T")
# FIXME BS: security issue: add user token to permit auth event


@dataclasses.dataclass
class WebSocketEvent(typing.Generic[T]):
    type: ZoneEventType
    world_row_i: int
    world_col_i: int
    data: typing.Optional[T] = dataclasses.field(default=None)


class WebSocketEventData(metaclass=abc.ABCMeta):
    pass


@dataclasses.dataclass
class EmptyData(WebSocketEventData):
    pass


@dataclasses.dataclass
class PlayerMoveData(WebSocketEventData):
    to_row_i: int
    to_col_i: int
    character_id: str


@dataclasses.dataclass
class CharacterEnterZoneData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int
    character_id: str
    spritesheet_id: typing.Optional[str]


@dataclasses.dataclass
class ZoneGroundResourceRemoveData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int
    resource_id: str


@dataclasses.dataclass
class ZoneGroundResourceAppearData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int
    resource_id: str


@dataclasses.dataclass
class ZoneGroundStuffRemoveData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int
    stuff_id: int


@dataclasses.dataclass
class ZoneGroundStuffAppearData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int
    id: str
    stuff_id: str
    classes: typing.List[str]


@dataclasses.dataclass
class ClientRequireAroundData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int
    character_id: str
    explode_take: bool = False


@dataclasses.dataclass
class ThereIsAroundData(WebSocketEventData):
    stuff_count: int
    resource_count: int
    build_count: int
    character_count: int
    quick_actions: typing.List[QuickAction]


class TopBarMessageType(Enum):
    NORMAL = "NORMAL"
    ERROR = "ERROR"


@dataclasses.dataclass
class TopBarMessageData(WebSocketEventData):
    message: str
    type_: TopBarMessageType


@dataclasses.dataclass
class ClickActionData(WebSocketEventData):
    action_type: ActionType
    action_description_id: str
    row_i: int
    col_i: int

    # TODO BS: use automatic compiled serpyco serializer
    def to_dict(self) -> dict:
        return {"row_i": self.row_i, "col_i": self.col_i}


@dataclasses.dataclass
class RequestChatData(WebSocketEventData):
    # TODO BS: use automatic compiled serpyco serializer
    def to_dict(self) -> dict:
        return {}


@dataclasses.dataclass
class NewChatMessageData(WebSocketEventData):
    message: str
    silent: bool
    system: bool
    character_id: typing.Optional[str]

    @classmethod
    def new_character(
        cls,
        character_id: str,
        message: str,
        silent: bool = False,
    ) -> "NewChatMessageData":
        return cls(
            character_id=character_id,
            message=message,
            silent=silent,
            system=False,
        )

    @classmethod
    def new_system(cls, message: str, silent: bool) -> "NewChatMessageData":
        return cls(
            character_id=None,
            message=message,
            silent=silent,
            system=True,
        )


@dataclasses.dataclass
class AnimatedCorpseMoveData(WebSocketEventData):
    animated_corpse_id: int
    to_row_i: int
    to_col_i: int

    # TODO BS: use automatic compiled serpyco serializer
    def to_dict(self) -> dict:
        return {
            "animated_corpse_id": self.animated_corpse_id,
            "to_row_i": self.to_row_i,
            "to_col_i": self.to_col_i,
        }


@dataclasses.dataclass
class ClientRequireNewResumeTextData(WebSocketEventData):
    pass


@dataclasses.dataclass
class NewResumeTextData(WebSocketEventData):
    resume: ListOfItemModel


@dataclasses.dataclass
class NewBuildData(WebSocketEventData):
    build: ZoneBuildModel
    produced_resource_id: typing.Optional[str] = None
    produced_stuff_id: typing.Optional[str] = None
    producer_character_id: typing.Optional[str] = None


@dataclasses.dataclass
class RemoveBuildData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int


@dataclasses.dataclass
class ZoneTileReplaceData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int
    new_tile_id: str


@dataclasses.dataclass
class NewAnimatedCorpseData(WebSocketEventData):
    animated_corpse_id: int


@dataclasses.dataclass
class CharacterExitZoneData(WebSocketEventData):
    character_id: str


zone_event_data_types: typing.Dict[ZoneEventType, typing.Type[WebSocketEventData]] = {
    ZoneEventType.PLAYER_MOVE: PlayerMoveData,
    ZoneEventType.CLIENT_WANT_CLOSE: EmptyData,
    ZoneEventType.SERVER_PERMIT_CLOSE: EmptyData,
    ZoneEventType.CHARACTER_ENTER_ZONE: CharacterEnterZoneData,
    ZoneEventType.CHARACTER_EXIT_ZONE: CharacterExitZoneData,
    ZoneEventType.CLIENT_REQUIRE_AROUND: ClientRequireAroundData,
    ZoneEventType.THERE_IS_AROUND: ThereIsAroundData,
    ZoneEventType.CLICK_ACTION_EVENT: ClickActionData,
    ZoneEventType.CLIENT_REQUIRE_NEW_RESUME_TEXT: ClientRequireNewResumeTextData,
    ZoneEventType.NEW_RESUME_TEXT: NewResumeTextData,
    ZoneEventType.NEW_BUILD: NewBuildData,
    ZoneEventType.REMOVE_BUILD: RemoveBuildData,
    ZoneEventType.REQUEST_CHAT: RequestChatData,
    ZoneEventType.NEW_CHAT_MESSAGE: NewChatMessageData,
    ZoneEventType.ANIMATED_CORPSE_MOVE: AnimatedCorpseMoveData,
    ZoneEventType.TOP_BAR_MESSAGE: TopBarMessageData,
    ZoneEventType.NEW_ANIMATED_CORPSE: NewAnimatedCorpseData,
    ZoneEventType.ZONE_TILE_REPLACE: ZoneTileReplaceData,
    ZoneEventType.ZONE_GROUND_RESOURCE_REMOVE: ZoneGroundResourceRemoveData,
    ZoneEventType.ZONE_GROUND_RESOURCE_APPEAR: ZoneGroundResourceAppearData,
    ZoneEventType.ZONE_GROUND_STUFF_REMOVE: ZoneGroundStuffRemoveData,
    ZoneEventType.ZONE_GROUND_STUFF_APPEAR: ZoneGroundStuffAppearData,
}


@dataclasses.dataclass
class StoryPage:
    id: int
    event_id: int
    text: str
    previous_page_id: typing.Optional[int] = None
    next_page_id: typing.Optional[int] = None
    image_id: typing.Optional[int] = None
    image_extension: typing.Optional[str] = None  # used by client to cache image
