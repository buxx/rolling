# coding: utf-8
import abc
import dataclasses
from enum import Enum
import typing


class ZoneEventType(Enum):
    PLAYER_MOVE = "PLAYER_MOVE"
    CLIENT_WANT_CLOSE = "CLIENT_WANT_CLOSE"
    SERVER_PERMIT_CLOSE = "SERVER_PERMIT_CLOSE"
    CHARACTER_ENTER_ZONE = "CHARACTER_ENTER_ZONE"
    CHARACTER_EXIT_ZONE = "CHARACTER_EXIT_ZONE"


T = typing.TypeVar("T")


@dataclasses.dataclass
class ZoneEvent(typing.Generic[T]):
    type: ZoneEventType
    data: typing.Optional[T] = dataclasses.field(default=None)


class ZoneEventData(metaclass=abc.ABCMeta):
    pass


@dataclasses.dataclass
class EmptyData(ZoneEventData):
    pass


@dataclasses.dataclass
class PlayerMoveData(ZoneEventData):
    to_row_i: int
    to_col_i: int
    character_id: str


@dataclasses.dataclass
class CharacterEnterZoneData(ZoneEventData):
    zone_row_i: int
    zone_col_i: int
    character_id: str


@dataclasses.dataclass
class CharacterExitZoneData(ZoneEventData):
    character_id: str


zone_event_data_types: typing.Dict[ZoneEventType, typing.Type[ZoneEventData]] = {
    ZoneEventType.PLAYER_MOVE: PlayerMoveData,
    ZoneEventType.CLIENT_WANT_CLOSE: EmptyData,
    ZoneEventType.SERVER_PERMIT_CLOSE: EmptyData,
    ZoneEventType.CHARACTER_ENTER_ZONE: CharacterEnterZoneData,
    ZoneEventType.CHARACTER_EXIT_ZONE: CharacterExitZoneData,
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
