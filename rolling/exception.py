# coding: utf-8
from requests import Response
import typing

from rolling.model.event import WebSocketEvent

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
    def __init__(self, socket) -> None:
        self.socket = socket


class EventError(RollingError):
    pass


class UnknownEvent(EventError):
    pass


class UnableToProcessEvent(EventError):
    def __init__(self, msg: str, event: WebSocketEvent) -> None:
        super().__init__(msg)
        self._event = event

    @property
    def event(self) -> WebSocketEvent:
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


class CantMove(GamePlayError):
    pass


class CantMoveCharacter(CantMove):
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
    def __init__(self, message: str, illustration_name: typing.Optional[str] = None):
        super().__init__(message)
        self.illustration_name = illustration_name


class ImpossibleAttack(ImpossibleAction):
    def __init__(self, msg: str, msg_lines: typing.Optional[typing.List[str]] = None) -> None:
        self.msg = msg
        self.msg_lines = msg_lines


class NoCarriedResource(GamePlayError):
    pass


class NotEnoughResource(GamePlayError):
    def __init__(
        self, resource_id: str, required_quantity: float, available_quantity: float
    ) -> None:
        self.resource_id = resource_id
        self.required_quantity = required_quantity
        self.available_quantity = available_quantity


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


class ErrorWhenConsume(RollingError):
    pass


class AccountError(UserDisplayError):
    pass


class AccountNotFound(AccountError):
    pass


class UsernameAlreadyUsed(AccountError):
    pass


class EmailAlreadyUsed(AccountError):
    pass


class EmailWrongFormat(AccountError):
    pass


class NotSamePassword(AccountError):
    pass
