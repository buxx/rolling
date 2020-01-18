# coding: utf-8
import abc
import dataclasses
from enum import Enum
import typing


class ZoneEventType(Enum):
    PLAYER_MOVE = "PLAYER_MOVE"
    CLIENT_WANT_CLOSE = "CLIENT_WANT_CLOSE"
    SERVER_PERMIT_CLOSE = "SERVER_PERMIT_CLOSE"


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


zone_event_data_types: typing.Dict[ZoneEventType, typing.Type[ZoneEventData]] = {
    ZoneEventType.PLAYER_MOVE: PlayerMoveData,
    ZoneEventType.CLIENT_WANT_CLOSE: EmptyData,
    ZoneEventType.SERVER_PERMIT_CLOSE: EmptyData,
}
