# coding: utf-8
import abc
import dataclasses
from enum import Enum
import typing


class ZoneEventType(Enum):
    PLAYER_MOVE = "PLAYER_MOVE"


T = typing.TypeVar("T")


@dataclasses.dataclass
class ZoneEvent(typing.Generic[T]):
    type: ZoneEventType
    data: T


class ZoneEventData(metaclass=abc.ABCMeta):
    pass


@dataclasses.dataclass
class PlayerMoveData(ZoneEventData):
    to_row_i: int
    to_col_i: int
    character_id: str


zone_event_data_types: typing.Dict[ZoneEventType, typing.Type[ZoneEventData]] = {
    ZoneEventType.PLAYER_MOVE: PlayerMoveData
}
