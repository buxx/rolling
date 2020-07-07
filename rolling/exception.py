# coding: utf-8
import typing

from requests import Response

from rolling.model.event import ZoneEvent

if typing.TYPE_CHECKING:
    from rolling.util import CornerEnum


class RollingError(Exception):
    pass


class UserDisplayError(RollingError):
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


class WebsocketError(RollingError):
    pass


class DisconnectClient(WebsocketError):
    pass


class EventError(RollingError):
    pass


class UnknownEvent(EventError):
    pass


class UnableToProcessEvent(EventError):
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


class CannotMoveToZoneError(RollingError):
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
    def __init__(self, message: str, response: Response) -> None:
        super().__init__(message)
        self.response = response


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


class NoCarriedResource(GamePlayError):
    pass


class NotEnoughResource(GamePlayError):
    pass


class MissingResource(GamePlayError):
    pass


class NotEnoughActionPoints(GamePlayError):
    def __init__(self, cost: float, msg: typing.Optional[str] = None):
        super().__init__(str)
        self.cost = cost


class NoMetaLine(SourceLoadError):
    pass


class CantChangeZone(RollingError):
    pass


class ServerTurnError(RollingError):
    pass


class WrongStrInput(RollingError):
    pass
