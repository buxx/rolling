# coding: utf-8
import typing

from rolling.model.event import ZoneEvent

if typing.TYPE_CHECKING:
    from rolling.util import CornerEnum


class RollingError(Exception):
    pass


class SourceLoadError(RollingError):
    pass


class TileTypeNotFound(RollingError):
    pass


class NoDefaultTileType(RollingError):
    pass


class NoZoneMapError(RollingError):
    pass


class NotConnectedToServer(RollingError):
    pass


class ZoneWebsocketJobFinished(RollingError):
    pass


class UnableToProcessEvent(RollingError):
    def __init__(self, msg: str, event: ZoneEvent) -> None:
        super().__init__(msg)
        self._event = event

    @property
    def event(self) -> ZoneEvent:
        return self._event


class ComponentNotPrepared(RollingError):
    pass


class MoveToOtherZoneError(RollingError):
    def __init__(self, corner: "CornerEnum") -> None:
        self._corner = corner

    @property
    def corner(self) -> "CornerEnum":
        return self._corner


class SameZoneError(RollingError):
    pass


class NoDisplayObjectAtThisPosition(RollingError):
    pass


class GamePlayError(RollingError):
    pass


class CantMoveCharacter(GamePlayError):
    pass


class CantMoveBecauseSurcharge(CantMoveCharacter):
    pass


class ClientServerExchangeError(RollingError):
    pass


class ConfigurationError(RollingError):
    pass


class UnknownStuffError(ConfigurationError):
    pass


class CantFill(GamePlayError):
    pass


class CantEmpty(GamePlayError):
    pass


class ImpossibleAction(GamePlayError):
    pass


class NoMetaLine(SourceLoadError):
    pass
