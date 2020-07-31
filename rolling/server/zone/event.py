# coding: utf-8
import abc
import typing

from aiohttp import web

from rolling.exception import DisconnectClient
from rolling.exception import ImpossibleAction
from rolling.exception import UnknownEvent
from rolling.log import server_logger
from rolling.model.character import CharacterModel
from rolling.model.event import ClickActionData
from rolling.model.event import ClientRequireAroundData
from rolling.model.event import PlayerMoveData
from rolling.model.event import ThereIsAroundData
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.serializer import ZoneEventSerializerFactory
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_RESOURCE_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_STUFF_URL
from rolling.server.document.build import BuildDocument
from rolling.server.lib.character import CharacterLib
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.server.zone.websocket import ZoneEventsManager
    from rolling.kernel import Kernel


class EventProcessor(metaclass=abc.ABCMeta):
    def __init__(self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager") -> None:
        self._zone_events_manager = zone_events_manager
        self._kernel = kernel
        self._event_serializer_factory = ZoneEventSerializerFactory()

    async def process(
        self, row_i: int, col_i: int, event: ZoneEvent, sender_socket: web.WebSocketResponse
    ) -> None:
        self._check(row_i, col_i, event)
        await self._process(row_i, col_i, event, sender_socket=sender_socket)

    def _check(self, row_i: int, col_i: int, event: ZoneEvent) -> None:
        pass

    @abc.abstractmethod
    async def _process(
        self, row_i: int, col_i: int, event: ZoneEvent, sender_socket: web.WebSocketResponse
    ) -> None:
        pass


class PlayerMoveProcessor(EventProcessor):
    def __init__(self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager") -> None:
        super().__init__(kernel, zone_events_manager)
        self._character_lib = CharacterLib(self._kernel)

    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: ZoneEvent[PlayerMoveData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        # FIXME BS 2019-01-23: Check what move is possible (tile can be a rock, or water ...)
        # TODO BS 2019-01-23: Check given character id is authenticated used (security)
        # FIXME BS 2020-07-04: Check there is no build with traversable false
        # FIXME BS 2020-07-04: check move is just near previous position + refuse move event
        character = self._character_lib.get(event.data.character_id)
        self._character_lib.move_on_zone(
            character, to_row_i=event.data.to_row_i, to_col_i=event.data.to_col_i
        )

        event_str = self._event_serializer_factory.get_serializer(event.type).dump_json(event)
        for socket in self._zone_events_manager.get_sockets(row_i, col_i):
            server_logger.debug(f"Send event on socket: {event_str}")

            try:
                await socket.send_str(event_str)
            except Exception as exc:
                server_logger.exception(exc)


class ClientWantCloseProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: ZoneEvent[PlayerMoveData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        raise DisconnectClient()


class ThereIsAroundProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: ZoneEvent[ClientRequireAroundData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        character = self._kernel.character_lib.get_document(event.data.character_id)
        around_character = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i
        )

        stuffs: typing.List[StuffModel] = []
        for row_i, col_i in around_character:
            # FIXME BS: Optimisation here (give all coordinates and make only one query)
            # And only id/name
            stuffs.extend(
                self._kernel.stuff_lib.get_zone_stuffs(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                )
            )

        resources: typing.List[CarriedResourceDescriptionModel] = []
        for row_i, col_i in around_character:
            # FIXME BS: Optimisation here (give all coordinates and make only one query)
            # And only id/name
            resources.extend(
                self._kernel.resource_lib.get_ground_resource(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                )
            )

        builds: typing.List[BuildDocument] = []
        for row_i, col_i in around_character:
            # FIXME BS: Optimisation here (give all coordinates and make only one query)
            # And only id/name
            builds.extend(
                self._kernel.build_lib.get_zone_build(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                )
            )

        characters: typing.List[CharacterModel] = []
        for row_i, col_i in around_character:
            # FIXME BS: Optimisation here (give all coordinates and make only one query)
            # And only id/name
            characters.extend(
                self._kernel.character_lib.get_zone_players(
                    row_i=character.world_row_i,
                    col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                    exclude_ids=[character.id],
                )
            )

        items: typing.List[typing.Tuple[str, typing.Optional[str]]] = []
        for stuff in stuffs:
            items.append(
                (
                    stuff.name,
                    DESCRIBE_LOOK_AT_STUFF_URL.format(character_id=character.id, stuff_id=stuff.id),
                )
            )
        for resource in resources:
            items.append(
                (
                    resource.name,
                    DESCRIBE_LOOK_AT_RESOURCE_URL.format(
                        character_id=character.id,
                        resource_id=resource.id,
                        row_i=resource.ground_row_i,
                        col_i=resource.ground_col_i,
                    ),
                )
            )
        for build in builds:
            build_properties = self._kernel.game.config.builds[build.build_id]
            items.append(
                (
                    build_properties.name,
                    DESCRIBE_BUILD.format(character_id=character.id, build_id=build.id),
                )
            )
        for character_ in characters:
            items.append(
                (
                    character_.name,
                    DESCRIBE_LOOK_AT_CHARACTER_URL.format(
                        character_id=character.id, with_character_id=character_.id
                    ),
                )
            )

        around_event = ZoneEvent(type=ZoneEventType.THERE_IS_AROUND, data=ThereIsAroundData(items))
        event_str = self._event_serializer_factory.get_serializer(
            ZoneEventType.THERE_IS_AROUND
        ).dump_json(around_event)
        await sender_socket.send_str(event_str)


class ClickActionProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: ZoneEvent[ClickActionData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        # FIXME Experimental way to identify action ...for now, only manage build ...
        path = event.data.base_url.split("?")[0]
        parts = path.split("/")
        character_id: str = parts[2]
        build_description_id: str = parts[5]
        character = self._kernel.character_lib.get(character_id)

        # FIXME BS: use dicts instead list for action descriptions
        description = next(
            ad
            for ad in self._kernel.game.config.actions[ActionType.BUILD]
            if ad.id == build_description_id
        )
        action = self._kernel.action_factory.get_build_action(description)
        input_ = action.input_model_serializer.load(event.data.to_dict())
        try:
            action.check_request_is_possible(character, input_)
            zone_events, sender_events = action.perform_from_event(character, input_)
        except ImpossibleAction as exc:
            # TODO BS: send event error
            server_logger.error(f"impossible action {build_description_id}: {str(exc)}")
            return

        for zone_event in zone_events:
            event_str = self._event_serializer_factory.get_serializer(zone_event.type).dump_json(
                zone_event
            )
            for socket in self._zone_events_manager.get_sockets(row_i, col_i):
                server_logger.debug(f"Send event on socket: {event_str}")

                try:
                    await socket.send_str(event_str)
                except Exception as exc:
                    server_logger.exception(exc)

        for sender_event in sender_events:
            event_str = self._event_serializer_factory.get_serializer(sender_event.type).dump_json(
                sender_event
            )
            server_logger.debug(f"Send event on socket: {event_str}")
            await sender_socket.send_str(event_str)


class EventProcessorFactory:
    def __init__(self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager") -> None:
        self._processors: typing.Dict[ZoneEventType, EventProcessor] = {}

        for zone_event_type, processor_type in [
            (ZoneEventType.PLAYER_MOVE, PlayerMoveProcessor),
            (ZoneEventType.CLIENT_WANT_CLOSE, ClientWantCloseProcessor),
            (ZoneEventType.CLIENT_REQUIRE_AROUND, ThereIsAroundProcessor),
            (ZoneEventType.CLICK_ACTION_EVENT, ClickActionProcessor),
        ]:
            self._processors[zone_event_type] = processor_type(kernel, zone_events_manager)

    def get_processor(self, zone_event_type: ZoneEventType) -> EventProcessor:
        try:
            return self._processors[zone_event_type]
        except KeyError:
            raise UnknownEvent(f"Unknown event type '{zone_event_type}'")
