# coding: utf-8
import abc
import dataclasses
from enum import Enum
import typing

from rolling.model.build import ZoneBuildModel


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


T = typing.TypeVar("T")
# FIXME BS: security issue: add user token to permit auth event


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
class ClientRequireAroundData(ZoneEventData):
    zone_row_i: int
    zone_col_i: int
    character_id: str


@dataclasses.dataclass
class ThereIsAroundData(ZoneEventData):
    items: typing.List[typing.Tuple[str, typing.Optional[str]]]


@dataclasses.dataclass
class ClickActionData(ZoneEventData):
    base_url: str
    row_i: int
    col_i: int

    # TODO BS: use automatic compiled serpyco serializer
    def to_dict(self) -> dict:
        return {"row_i": self.row_i, "col_i": self.col_i}


@dataclasses.dataclass
class NewResumeTextData(ZoneEventData):
    resume: typing.List[typing.Tuple[str, typing.Optional[str]]]


@dataclasses.dataclass
class NewBuildData(ZoneEventData):
    build: ZoneBuildModel


@dataclasses.dataclass
class CharacterExitZoneData(ZoneEventData):
    character_id: str


zone_event_data_types: typing.Dict[ZoneEventType, typing.Type[ZoneEventData]] = {
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
