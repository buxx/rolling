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
from rolling.server.base import ZoneEventSocketWrapper

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class ZoneEventsManager:
    def __init__(self, kernel: "Kernel", loop: asyncio.AbstractEventLoop) -> None:
        self._sockets: typing.Dict[typing.Tuple[int, int], typing.List[ZoneEventSocketWrapper]] = {}
        self._sockets_character_id: typing.Dict[ZoneEventSocketWrapper, str] = {}
        self._event_processor_factory = EventProcessorFactory(kernel, self)
        self._event_serializer_factory = ZoneEventSerializerFactory()
        self._loop = loop or asyncio.get_event_loop()
        self._kernel = kernel

    def get_character_id_for_socket(self, socket: ZoneEventSocketWrapper) -> str:
        return self._sockets_character_id[socket]

    async def get_new_socket(
        self, request: Request, row_i: int, col_i: int, character_id: str
    ) -> ZoneEventSocketWrapper:
        server_logger.info(f"Create websocket for zone {row_i},{col_i}")

        # Create socket
        socket = ZoneEventSocketWrapper(self._kernel, web.WebSocketResponse(), row_i, col_i)
        await socket.prepare(request)

        # TODO BS 2019-01-23: Implement a heartbeat to close sockets where client disapear
        # see https://github.com/aio-libs/aiohttp/issues/961#issuecomment-239647597
        # Something lik asyncio.ensure_future(self._heartbeat(ws))

        # Make it available for send job
        self._sockets.setdefault((row_i, col_i), []).append(socket)
        self._sockets_character_id[socket] = character_id

        # Start to listen client messages
        try:
            await self._listen(socket, row_i, col_i)
        except CancelledError:
            server_logger.debug(f"websocket ({row_i},{col_i}) seems cancelled")

        # If this code reached: ws is disconnected
        server_logger.debug(f"remove websocket ({row_i},{col_i})")
        self._sockets[(row_i, col_i)].remove(socket)
        del self._sockets_character_id[socket]

        return socket

    async def _listen(self, socket: ZoneEventSocketWrapper, row_i: int, col_i: int) -> None:
        server_logger.info(f"Listen websocket for zone {row_i},{col_i}")
        async for msg in socket.iter():
            server_logger.debug(f"Receive message on websocket for zone {row_i},{col_i}: {msg}")

            if msg.type == aiohttp.WSMsgType.ERROR:
                server_logger.error(f"Zone websocket closed with exception {socket.exception()}")
            else:
                try:
                    await self._process_msg(row_i, col_i, msg, socket)
                except DisconnectClient:
                    await socket.send_to_zone_str(
                        self._event_serializer_factory.get_serializer(
                            ZoneEventType.SERVER_PERMIT_CLOSE
                        ).dump_json(
                            WebSocketEvent(type=ZoneEventType.SERVER_PERMIT_CLOSE, data=EmptyData())
                        )
                    )
                    return

        server_logger.info(f"Websocket of zone {row_i},{col_i} closed")

    async def _process_msg(
        self, row_i: int, col_i: int, msg, socket: ZoneEventSocketWrapper
    ) -> None:
        event_dict = json.loads(msg.data)
        event_type = ZoneEventType(event_dict["type"])
        event = self._event_serializer_factory.get_serializer(event_type).load(event_dict)
        await self._process_event(row_i, col_i, event, socket)

    async def _process_event(
        self, row_i: int, col_i: int, event: WebSocketEvent, socket: ZoneEventSocketWrapper
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
            await socket.send_to_zone_str(exception_event_str)

    def get_sockets(self, row_i: int, col_i: int) -> typing.Iterable[ZoneEventSocketWrapper]:
        for socket in self._sockets.get((row_i, col_i), []):
            yield socket

    def get_active_zone_characters_ids(self, world_row_i: int, world_col_i: int) -> typing.List[str]:
        return [
            self.get_character_id_for_socket(socket)
            for socket in self.get_sockets(world_row_i, world_col_i)
        ]
