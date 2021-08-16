# coding: utf-8
import dataclasses

import abc
from enum import Enum
import typing

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
    NEW_RESUME_TEXT = "NEW_RESUME_TEXT"
    NEW_BUILD = "NEW_BUILD"
    REQUEST_CHAT = "REQUEST_CHAT"
    NEW_CHAT_MESSAGE = "NEW_CHAT_MESSAGE"
    ANIMATED_CORPSE_MOVE = "ANIMATED_CORPSE_MOVE"
    TOP_BAR_MESSAGE = "TOP_BAR_MESSAGE"
    NEW_ANIMATED_CORPSE = "NEW_ANIMATED_CORPSE"


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


@dataclasses.dataclass
class ClientRequireAroundData(WebSocketEventData):
    zone_row_i: int
    zone_col_i: int
    character_id: str


@dataclasses.dataclass
class ThereIsAroundData(WebSocketEventData):
    stuff_count: int
    resource_count: int
    build_count: int
    character_count: int


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
    character_id: str
    message_count: int
    next: bool
    previous: bool
    previous_conversation_id: typing.Optional[int] = None

    # TODO BS: use automatic compiled serpyco serializer
    def to_dict(self) -> dict:
        return {
            "previous_conversation_id": self.previous_conversation_id,
            "character_id": self.character_id,
            "message_count": self.message_count,
        }


@dataclasses.dataclass
class NewChatMessageData(WebSocketEventData):
    character_id: str
    message: str
    conversation_id: typing.Optional[int] = None
    conversation_title: typing.Optional[str] = None

    # TODO BS: use automatic compiled serpyco serializer
    def to_dict(self) -> dict:
        return {
            "character_id": self.character_id,
            "conversation_id": self.conversation_id,
            "conversation_title": self.conversation_title,
            "message": self.message,
        }


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
class NewResumeTextData(WebSocketEventData):
    resume: ListOfItemModel


@dataclasses.dataclass
class NewBuildData(WebSocketEventData):
    build: ZoneBuildModel


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
    ZoneEventType.NEW_RESUME_TEXT: NewResumeTextData,
    ZoneEventType.NEW_BUILD: NewBuildData,
    ZoneEventType.REQUEST_CHAT: RequestChatData,
    ZoneEventType.NEW_CHAT_MESSAGE: NewChatMessageData,
    ZoneEventType.ANIMATED_CORPSE_MOVE: AnimatedCorpseMoveData,
    ZoneEventType.TOP_BAR_MESSAGE: TopBarMessageData,
    ZoneEventType.NEW_ANIMATED_CORPSE: NewAnimatedCorpseData,
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
