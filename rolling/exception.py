# coding: utf-8
from rolling.model.event import ZoneEvent


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
    def __init__(self, row_i: int, col_i: int) -> None:
        self._row_i = row_i
        self._col_i = col_i

    @property
    def row_i(self) -> int:
        return self._row_i

    @property
    def col_i(self) -> int:
        return self._col_i


class SameZoneError(RollingError):
    pass


class NoDisplayObjectAtThisPosition(RollingError):
    pass


class GamePlayError(RollingError):
    pass


class CantMoveCharacter(GamePlayError):
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
