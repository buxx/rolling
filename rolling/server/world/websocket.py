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


class WorldEventsManager:
    def __init__(self, kernel: "Kernel", loop: asyncio.AbstractEventLoop) -> None:
        self._sockets: typing.List[web.WebSocketResponse] = []
        self._event_processor_factory = EventProcessorFactory(kernel, self)
        self._event_serializer_factory = ZoneEventSerializerFactory()
        self._loop = loop or asyncio.get_event_loop()
        self._kernel = kernel

    async def get_new_socket(self, request: Request) -> web.WebSocketResponse:
        server_logger.info(f"Create websocket for world")

        # Create socket
        socket = web.WebSocketResponse()
        await socket.prepare(request)

        # TODO BS 2019-01-23: Implement a heartbeat to close sockets where client disapear
        # see https://github.com/aio-libs/aiohttp/issues/961#issuecomment-239647597
        # Something lik asyncio.ensure_future(self._heartbeat(ws))

        # Make it available for send job
        self._sockets.append(socket)

        # Start to listen client messages
        try:
            await self._listen(socket)
        except CancelledError:
            server_logger.debug(f"world websocket seems cancelled")

        # If this code reached: ws is disconnected
        server_logger.debug(f"remove world websocket")
        self._sockets.remove(socket)

        return socket

    async def _listen(self, socket: web.WebSocketResponse) -> None:
        server_logger.info(f"Listen websocket for world")
        async for msg in socket:
            server_logger.debug(f"Receive message on websocket for world: {msg}")

            if msg.type == aiohttp.WSMsgType.ERROR:
                server_logger.error(f"World websocket closed with exception {socket.exception()}")
            else:
                try:
                    await self._process_msg(msg, socket)
                except DisconnectClient:
                    await socket.send_str(
                        self._event_serializer_factory.get_serializer(
                            ZoneEventType.SERVER_PERMIT_CLOSE
                        ).dump_json(
                            WebSocketEvent(type=ZoneEventType.SERVER_PERMIT_CLOSE, data=EmptyData())
                        )
                    )
                    return

        server_logger.info(f"Websocket of world closed")

    async def _process_msg(
        self, msg, socket: web.WebSocketResponse
    ) -> None:
        event_dict = json.loads(msg.data)
        event_type = ZoneEventType(event_dict["type"])
        event = self._event_serializer_factory.get_serializer(event_type).load(event_dict)
        await self._process_event(event, socket)

    async def _process_event(
        self, event: WebSocketEvent, socket: web.WebSocketResponse
    ) -> None:
        try:
            event_processor = self._event_processor_factory.get_processor(event.type)
        except UnknownEvent:
            server_logger.warning(f"Unknown received event type '{event.type}'")
            return

        try:
            await event_processor.process(event, sender_socket=socket)
        except UnableToProcessEvent as exc:
            server_logger.debug(f"Unable to process event {event.type}: {str(exc)}")

            exception_event = exc.event
            exception_event_str = self._event_serializer_factory.get_serializer(
                exception_event.type
            ).dump_json(exception_event)

            # FIXME: do kept this feature ?
            await socket.send_str(exception_event_str)

    def get_sockets(self) -> typing.Iterable[web.WebSocketResponse]:
        for socket in self._sockets:
            yield socket
