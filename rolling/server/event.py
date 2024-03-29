# coding: utf-8
import abc
import datetime
import time
import uuid
from aiohttp import web
from sqlalchemy.orm import exc
from sqlalchemy.orm.exc import NoResultFound
import typing

from rolling.exception import CantMove, WrongInputError
from rolling.exception import DisconnectClient
from rolling.exception import ImpossibleAction
from rolling.exception import UnknownEvent
from rolling.log import server_logger
from rolling.model.data import ListOfItemModel
from rolling.model.event import AnimatedCorpseMoveData, NewResumeTextData
from rolling.model.event import ClickActionData
from rolling.model.event import ClientRequireAroundData
from rolling.model.event import NewChatMessageData
from rolling.model.event import PlayerMoveData
from rolling.model.event import RequestChatData
from rolling.model.event import ThereIsAroundData
from rolling.model.event import TopBarMessageData
from rolling.model.event import TopBarMessageType
from rolling.model.event import WebSocketEvent
from rolling.model.event import ZoneEventType
from rolling.server.chat import LiveChatOperator
from rolling.server.lib.character import CharacterLib
from rolling.server.link import CharacterActionLink, QuickAction
from rolling.types import WorldPoint
from rolling.util import (
    ROLLGUI1_COMPAT,
    get_on_and_around_coordinates,
    url_without_zone_coordinates,
)

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.server.zone.websocket import ZoneEventsManager


class EventProcessor(metaclass=abc.ABCMeta):
    def __init__(
        self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager"
    ) -> None:
        self._zone_events_manager = zone_events_manager
        self._kernel = kernel

    async def process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent,
        sender_socket: web.WebSocketResponse,
    ) -> None:
        self._check(row_i, col_i, event)
        await self._process(row_i, col_i, event, sender_socket=sender_socket)

    def _check(self, row_i: int, col_i: int, event: WebSocketEvent) -> None:
        pass

    @abc.abstractmethod
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent,
        sender_socket: web.WebSocketResponse,
    ) -> None:
        pass


# FIXME BS NOW EVENT: type of zone_events_manager must be a base abstract class
# FIXME BS NOW EVENT: world event manager must add zone coordinates to sent event
class PlayerMoveProcessor(EventProcessor):
    def __init__(
        self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager"
    ) -> None:
        super().__init__(kernel, zone_events_manager)
        self._character_lib = CharacterLib(self._kernel)

    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent[PlayerMoveData],
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

        await self._zone_events_manager.send_to_sockets(event, row_i, col_i)


class ClientWantCloseProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent[PlayerMoveData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        server_logger.error("DEBUG :: ClientWantCloseProcessor")
        raise DisconnectClient(sender_socket)


class ThereIsAroundProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent[ClientRequireAroundData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        await self.send_around(
            row_i=row_i,
            col_i=col_i,
            character_id=event.data.character_id,
            sender_socket=sender_socket,
            explode_take=event.data.explode_take,
        )

    async def send_around(
        self,
        row_i: int,
        col_i: int,
        character_id: str,
        sender_socket: web.WebSocketResponse,
        explode_take: bool = False,
    ) -> None:
        character = self._kernel.character_lib.get_document(character_id)

        if ROLLGUI1_COMPAT:
            around_character = get_on_and_around_coordinates(
                x=character.zone_row_i, y=character.zone_col_i
            )

            stuff_count = 0
            for row_i, col_i in around_character:
                # FIXME BS: Optimisation here (give all coordinates and make only one query)
                # And only id/name
                stuff_count += self._kernel.stuff_lib.count_zone_stuffs(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                )

            resource_count = 0
            for row_i, col_i in around_character:
                # FIXME BS: Optimisation here (give all coordinates and make only one query)
                # And only id/name
                resource_count += self._kernel.resource_lib.count_ground_resource(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                )

            build_count = 0
            for row_i, col_i in around_character:
                # FIXME BS: Optimisation here (give all coordinates and make only one query)
                # And only id/name
                build_count += self._kernel.build_lib.count_zone_build(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                    is_floor=False,
                )

            character_count = 0
            for row_i, col_i in around_character:
                # FIXME BS: Optimisation here (give all coordinates and make only one query)
                # And only id/name
                character_count += self._kernel.character_lib.count_zone_characters(
                    row_i=character.world_row_i,
                    col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                    exclude_ids=[character.id],
                )

        quick_actions = self._kernel.character_lib.get_on_place_actions(
            character.id, quick_actions_only=True
        )

        if ROLLGUI1_COMPAT:
            if explode_take:
                quick_actions.extend(
                    (
                        list(
                            self._kernel.character_lib.get_on_place_stuff_actions(
                                character, quick_actions=True
                            )
                        )
                    )
                    + (
                        list(
                            self._kernel.character_lib.get_on_place_resource_actions(
                                character, quick_actions=True
                            )
                        )
                    )
                )
            else:
                # If there is something to pick, add quick action
                there_is_around = False
                try:
                    next(
                        self._kernel.character_lib.get_on_place_stuff_actions(character)
                    )
                    there_is_around = True
                except StopIteration:
                    pass
                try:
                    next(
                        self._kernel.character_lib.get_on_place_resource_actions(
                            character
                        )
                    )
                    there_is_around = True
                except StopIteration:
                    pass

                if there_is_around:
                    quick_actions.append(
                        CharacterActionLink(
                            name="Regarder ce qu'il y a à ramasser autour",
                            link=f"/character/{character_id}/send-around?explode_take=1&quick_action=1&disable_resend_quick_actions=1",
                            classes1=["TAKE"],
                        )
                    )

        # TODO : Quick action are rewrite for rollgui2. Simplify code when rollgui1 outdated
        new_quick_actions = []
        for quick_action in quick_actions:
            if quick_action.direct_action:
                url = quick_action.link
            else:
                url = url_without_zone_coordinates(quick_action.link)
            new_quick_actions.append(
                QuickAction(
                    uuid=uuid.uuid4().hex,
                    name=quick_action.name,
                    base_url=url,
                    classes1=quick_action.classes1,
                    classes2=quick_action.classes2,
                    exploitable_tiles=quick_action.exploitable_tiles,
                    all_tiles_at_once=quick_action.all_tiles_at_once,
                    direct_action=quick_action.direct_action,
                    quick_action_key=quick_action.quick_action_key,
                    # rollgui1 compatibility bellow
                    link=quick_action.link,
                    force_open_description=quick_action.force_open_description,
                )
            )

        around_event = WebSocketEvent(
            type=ZoneEventType.THERE_IS_AROUND,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            data=ThereIsAroundData(
                stuff_count=stuff_count,
                resource_count=resource_count,
                build_count=build_count,
                character_count=character_count,
                quick_actions=new_quick_actions,
            ),
        )
        event_str = self._kernel.event_serializer_factory.get_serializer(
            ZoneEventType.THERE_IS_AROUND
        ).dump_json(around_event)
        await self._kernel.server_zone_events_manager.respond_to_socket(
            socket=sender_socket,
            event_str=event_str,
        )


class SendResumeTextProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent[ClientRequireAroundData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        character_id = (
            self._kernel._server_zone_events_manager.get_character_id_for_socket(
                sender_socket
            )
        )
        character = self._kernel.character_lib.get_document(character_id)
        event = WebSocketEvent(
            type=ZoneEventType.NEW_RESUME_TEXT,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            data=NewResumeTextData(
                resume=ListOfItemModel(
                    self._kernel.character_lib.get_resume_text(character.id)
                )
            ),
        )
        event_str = self._kernel.event_serializer_factory.get_serializer(
            ZoneEventType.NEW_RESUME_TEXT
        ).dump_json(event)
        await self._kernel.server_zone_events_manager.respond_to_socket(
            socket=sender_socket,
            event_str=event_str,
        )


class ClickActionProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent[ClickActionData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        character_id = (
            self._kernel.server_zone_events_manager.get_character_id_for_socket(
                sender_socket
            )
        )
        character = self._kernel.character_lib.get(character_id)
        try:
            action = self._kernel.action_factory.create_action(
                action_type=event.data.action_type,
                action_description_id=event.data.action_description_id,
            )
        except NotImplementedError:
            server_logger.error(
                f"No action for '{event.data.action_type}' "
                f"and '{event.data.action_description_id}' found for process click action event !"
            )
            return
        input_ = action.input_model_from_request(event.data.to_dict())

        try:
            await action.check_request_is_possible(character, input_)
            zone_events, sender_events = await action.perform_from_event(
                character, input_
            )
        except (ImpossibleAction, WrongInputError) as exc:
            await self._kernel.server_zone_events_manager.respond_to_socket(
                socket=sender_socket,
                event_str=self._kernel.event_serializer_factory.get_serializer(
                    ZoneEventType.TOP_BAR_MESSAGE
                ).dump_json(
                    WebSocketEvent(
                        type=ZoneEventType.TOP_BAR_MESSAGE,
                        world_row_i=row_i,
                        world_col_i=col_i,
                        data=TopBarMessageData(
                            message=str(exc).replace("\n", " "),
                            type_=TopBarMessageType.ERROR,
                        ),
                    )
                ),
            )
            return

        for event in zone_events:
            await self._zone_events_manager.send_to_sockets(event, row_i, col_i)

        for sender_event in sender_events:
            event_str = self._kernel.event_serializer_factory.get_serializer(
                sender_event.type
            ).dump_json(sender_event)
            server_logger.debug(f"Send event on socket: {event_str}")
            await self._kernel.server_zone_events_manager.respond_to_socket(
                socket=sender_socket,
                event_str=event_str,
            )


class RequestChatProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent[RequestChatData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        sender_character_id = (
            self._kernel.server_zone_events_manager.get_character_id_for_socket(
                sender_socket
            )
        )
        sender_character_doc = self._kernel.character_lib.get_document(
            sender_character_id
        )

        # Send previous messages (TODO: optimize with one ws object)
        cached_messages = self._kernel.chat_state.messages(WorldPoint((row_i, col_i)))
        for cached_message in cached_messages:
            await self._kernel.message_lib.send_character_chat_message(
                world_row_i=row_i,
                world_col_i=col_i,
                character_id=cached_message.author_id,
                message=cached_message.message,
                silent=True,
                only_to=sender_socket,
            )

        if cached_messages:
            last_cached_message = cached_messages[-1]
            since_seconds = int(time.time()) - last_cached_message.timestamp
            if since_seconds < 60:
                message = "🕐 Dernier message il a quelque secondes"
            elif since_seconds < 60 * 10:
                message = "🕐 Dernier message il a quelques minutes"
            elif since_seconds < 3600:
                message = "🕐 Dernier message il a moins d'une heure"
            else:
                message = "🕐 Dernier message il a plus d'une heure"

            await self._kernel.message_lib.send_system_chat_message(
                world_row_i=row_i,
                world_col_i=col_i,
                message=message,
                silent=True,
                only_to=sender_socket,
            )

        # Send chat system message for each connected player
        here_character_ids = (
            self._kernel.server_zone_events_manager.get_active_zone_characters_ids(
                world_row_i=sender_character_doc.world_row_i,
                world_col_i=sender_character_doc.world_col_i,
            )
        )
        other_here_character_ids = [
            here_character_id
            for here_character_id in here_character_ids
            if here_character_id != sender_character_id
        ]
        for other_here_character_id in other_here_character_ids:
            other_character_doc_ = self._kernel.character_lib.get_document(
                other_here_character_id
            )
            await self._kernel.message_lib.send_system_chat_message(
                world_row_i=other_character_doc_.world_row_i,
                world_col_i=other_character_doc_.world_col_i,
                message=f"💡 Le joueur de {other_character_doc_.name} est connecté",
                silent=True,
                only_to=sender_socket,
            )


class NewChatMessageProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent[NewChatMessageData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        character_id = (
            self._kernel.server_zone_events_manager.get_character_id_for_socket(
                sender_socket
            )
        )
        if character_id is not None:
            character_name = self._kernel.character_lib.get_name(character_id)
            await LiveChatOperator(self._kernel).received_message(
                character_id=character_id,
                message=f"📝 {character_name}: {event.data.message}",
            )


class AnimatedCorpseMoveProcessor(EventProcessor):
    async def _process(
        self,
        row_i: int,
        col_i: int,
        event: WebSocketEvent[AnimatedCorpseMoveData],
        sender_socket: web.WebSocketResponse,
    ) -> None:
        try:
            animated_corpse = self._kernel.animated_corpse_lib.get(
                event.data.animated_corpse_id
            )
        except NoResultFound:
            server_logger.error(
                f"No animated corpse found for id {event.data.animated_corpse_id}"
            )
            return

        new_zone_row_i = animated_corpse.zone_row_i
        new_zone_col_i = animated_corpse.zone_col_i

        try:
            self._kernel.animated_corpse_lib.move(
                animated_corpse,
                to_zone_row_i=event.data.to_row_i,
                to_zone_col_i=event.data.to_col_i,
            )
            new_zone_row_i = event.data.to_row_i
            new_zone_col_i = event.data.to_col_i
        except CantMove:
            server_logger.debug("cant move")
            pass

        await self._kernel.server_zone_events_manager.send_to_sockets(
            WebSocketEvent(
                type=ZoneEventType.ANIMATED_CORPSE_MOVE,
                world_row_i=animated_corpse.world_row_i,
                world_col_i=animated_corpse.world_col_i,
                data=AnimatedCorpseMoveData(
                    animated_corpse_id=animated_corpse.id,
                    to_row_i=new_zone_row_i,
                    to_col_i=new_zone_col_i,
                ),
            ),
            world_row_i=animated_corpse.world_row_i,
            world_col_i=animated_corpse.world_col_i,
        )


class EventProcessorFactory:
    # FIXME BS NOW EVENT: type of zone_events_manager must be a base abstract class
    def __init__(
        self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager"
    ) -> None:
        self._processors: typing.Dict[ZoneEventType, EventProcessor] = {}

        for zone_event_type, processor_type in [
            (ZoneEventType.PLAYER_MOVE, PlayerMoveProcessor),
            (ZoneEventType.CLIENT_WANT_CLOSE, ClientWantCloseProcessor),
            (ZoneEventType.CLIENT_REQUIRE_AROUND, ThereIsAroundProcessor),
            (ZoneEventType.CLIENT_REQUIRE_NEW_RESUME_TEXT, SendResumeTextProcessor),
            (ZoneEventType.CLICK_ACTION_EVENT, ClickActionProcessor),
            (ZoneEventType.REQUEST_CHAT, RequestChatProcessor),
            (ZoneEventType.NEW_CHAT_MESSAGE, NewChatMessageProcessor),
            (ZoneEventType.ANIMATED_CORPSE_MOVE, AnimatedCorpseMoveProcessor),
        ]:
            self._processors[zone_event_type] = processor_type(
                kernel, zone_events_manager
            )

    def get_processor(self, zone_event_type: ZoneEventType) -> EventProcessor:
        try:
            return self._processors[zone_event_type]
        except KeyError:
            raise UnknownEvent(f"Unknown event type '{zone_event_type}'")
