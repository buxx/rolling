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
