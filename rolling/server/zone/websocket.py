# coding: utf-8
import aiohttp
from aiohttp import web
from aiohttp.web_request import Request
import asyncio
from concurrent.futures._base import CancelledError
import json
import typing

from rolling.exception import DisconnectClient
from rolling.exception import UnableToProcessEvent
from rolling.exception import UnknownEvent
from rolling.log import server_logger
from rolling.model.event import EmptyData
from rolling.model.event import WebSocketEvent
from rolling.model.event import ZoneEventType
from rolling.model.serializer import ZoneEventSerializerFactory
from rolling.server.event import EventProcessorFactory

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class ZoneEventsManager:
    def __init__(self, kernel: "Kernel", loop: asyncio.AbstractEventLoop) -> None:
        self._sockets: typing.Dict[typing.Tuple[int, int], typing.List[web.WebSocketResponse]] = {}
        self._sockets_character_id: typing.Dict[web.WebSocketResponse, str] = {}
        self._sockets_associated_reader_token: typing.Dict[web.WebSocketResponse, str] = {}
        self._sockets_by_token: typing.Dict[str, web.WebSocketResponse] = {}
        self._event_processor_factory = EventProcessorFactory(kernel, self)
        self._event_serializer_factory = ZoneEventSerializerFactory()
        self._loop = loop or asyncio.get_event_loop()
        self._kernel = kernel

    def get_character_id_for_socket(self, socket: web.WebSocketResponse) -> str:
        return self._sockets_character_id[socket]

    async def close_websocket(self, socket_to_remove: web.WebSocketResponse) -> None:
        try:
            await socket_to_remove.close()
        except CancelledError:
            pass  # consider ok if already closed

        for sockets in self._sockets.values():
            try:
                sockets.remove(socket_to_remove)
            except ValueError:
                pass

        try:
            del self._sockets_character_id[socket_to_remove]
        except KeyError:
            pass

        try:
            del self._sockets_associated_reader_token[socket_to_remove]
        except KeyError:
            pass

        for token, socket in list(self._sockets_by_token.items()):
            if socket == socket_to_remove:
                del self._sockets_by_token[token]

    async def get_new_socket(
        self,
        request: Request,
        row_i: int,
        col_i: int,
        character_id: str,
        reader_token: typing.Optional[str] = None,
        token: typing.Optional[str] = None,
    ) -> web.WebSocketResponse:
        server_logger.info(f"Create websocket for zone {row_i},{col_i} ({reader_token},{token})")

        # Create socket
        socket = web.WebSocketResponse()
        await socket.prepare(request)

        # TODO BS 2019-01-23: Implement a heartbeat to close sockets where client disapear
        # see https://github.com/aio-libs/aiohttp/issues/961#issuecomment-239647597
        # Something lik asyncio.ensure_future(self._heartbeat(ws))

        # Make it available for send job
        self._sockets.setdefault((row_i, col_i), []).append(socket)
        self._sockets_character_id[socket] = character_id

        if token:
            self._sockets_by_token[token] = socket

        if reader_token:
            self._sockets_associated_reader_token[socket] = reader_token

        # Start to listen client messages
        try:
            await self._listen(socket, row_i, col_i)
        except CancelledError:
            server_logger.debug(f"websocket ({row_i},{col_i}) seems cancelled")

        # If this code reached: ws is disconnected
        server_logger.debug(f"remove websocket ({row_i},{col_i})")
        await self.close_websocket(socket)

        return socket

    async def _listen(self, socket: web.WebSocketResponse, row_i: int, col_i: int) -> None:
        server_logger.info(f"Listen websocket for zone {row_i},{col_i}")
        async for msg in socket:
            server_logger.debug(f"Receive message on websocket for zone {row_i},{col_i}: {msg}")

            if msg.type == aiohttp.WSMsgType.ERROR:
                server_logger.error(f"Zone websocket closed with exception {socket.exception()}")
            else:
                try:
                    await self._process_msg(row_i, col_i, msg, socket)
                except DisconnectClient as exc:
                    await self.respond_to_socket(
                        exc.socket,
                        self._event_serializer_factory.get_serializer(
                            ZoneEventType.SERVER_PERMIT_CLOSE
                        ).dump_json(
                            WebSocketEvent(
                                world_row_i=0,
                                world_col_i=0,
                                type=ZoneEventType.SERVER_PERMIT_CLOSE,
                                data=EmptyData(),
                            )
                        ),
                    )
                    return

        server_logger.info(f"Websocket of zone {row_i},{col_i} closed")

    async def _process_msg(
        self, row_i: int, col_i: int, msg, socket: web.WebSocketResponse
    ) -> None:
        event_dict = json.loads(msg.data)
        event_type = ZoneEventType(event_dict["type"])
        # Event zone coordinate is mandatory
        event_dict["world_row_i"] = row_i
        event_dict["world_col_i"] = col_i
        event = self._event_serializer_factory.get_serializer(event_type).load(event_dict)
        await self._process_event(row_i, col_i, event, socket)

    async def _process_event(
        self, row_i: int, col_i: int, event: WebSocketEvent, socket: web.WebSocketResponse
    ) -> None:
        try:
            event_processor = self._event_processor_factory.get_processor(event.type)
        except UnknownEvent:
            server_logger.warning(f"Unknown received event type '{event.type}'")
            return

        try:
            await event_processor.process(row_i, col_i, event, sender_socket=socket)
        except UnableToProcessEvent as exc:
            server_logger.debug(f"Unable to process event {event.type}: {str(exc)}")

            exception_event = exc.event
            exception_event_str = self._event_serializer_factory.get_serializer(
                exception_event.type
            ).dump_json(exception_event)

            # FIXME: do kept this feature ?
            await socket.send_str(exception_event_str)

    def get_sockets(self, row_i: int, col_i: int) -> typing.Iterable[web.WebSocketResponse]:
        for socket in self._sockets.get((row_i, col_i), []):
            yield socket

    async def send_to_sockets(
        self,
        event: WebSocketEvent,
        world_row_i: int,
        world_col_i: int,
        repeat_to_world: bool = True,
        character_ids: typing.Optional[typing.List[str]] = None,
    ) -> str:
        event_str = self._kernel.event_serializer_factory.get_serializer(event.type).dump_json(
            event
        )

        for socket in self.get_sockets(world_row_i, world_col_i):
            if (
                character_ids is not None
                and self.get_character_id_for_socket(socket) not in character_ids
            ):
                continue

            try:
                server_logger.debug(event_str)
                await socket.send_str(event_str)
            except Exception as exc:
                server_logger.exception(exc)

        # Replicate message on world websockets
        if repeat_to_world:
            await self._kernel.server_world_events_manager.send_to_sockets(
                event, world_row_i=world_row_i, world_col_i=world_col_i, repeat_to_zone=False
            )

        return event_str

    def get_active_zone_characters_ids(
        self, world_row_i: int, world_col_i: int
    ) -> typing.List[str]:
        return [
            self.get_character_id_for_socket(socket)
            for socket in self.get_sockets(world_row_i, world_col_i)
        ]

    async def respond_to_socket(self, socket: web.WebSocketResponse, event_str: str) -> None:
        associated_reader_token = self._sockets_associated_reader_token.get(socket)

        if not associated_reader_token:
            await socket.send_str(event_str)
            return

        if associated_reader_token not in self._sockets_by_token:
            server_logger.warning(f"No associated reader ws for toen '{associated_reader_token}' !")
            return

        associated_reader_ws = self._sockets_by_token.get(associated_reader_token)
        await associated_reader_ws.send_str(event_str)
