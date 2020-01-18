# coding: utf-8
import asyncio
import json
import typing

import aiohttp
from aiohttp import web
from aiohttp.web_request import Request

from rolling.exception import DisconnectClient
from rolling.exception import UnableToProcessEvent
from rolling.exception import UnknownEvent
from rolling.log import server_logger
from rolling.model.event import EmptyData
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.model.serializer import ZoneEventSerializerFactory
from rolling.server.zone.event import EventProcessorFactory

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class ZoneEventsManager:
    def __init__(self, kernel: "Kernel", loop: asyncio.AbstractEventLoop) -> None:
        self._sockets: typing.Dict[typing.Tuple[int, int], typing.List[web.WebSocketResponse]] = {}
        self._event_processor_factory = EventProcessorFactory(kernel, self)
        self._event_serializer_factory = ZoneEventSerializerFactory()
        self._loop = loop or asyncio.get_event_loop()
        self._kernel = kernel

    async def get_new_socket(
        self, request: Request, row_i: int, col_i: int
    ) -> web.WebSocketResponse:
        server_logger.info(f"Create websocket for zone {row_i},{col_i}")

        # Create socket
        socket = web.WebSocketResponse()
        await socket.prepare(request)

        # TODO BS 2019-01-23: Implement a heartbeat to close sockets where client disapear
        # see https://github.com/aio-libs/aiohttp/issues/961#issuecomment-239647597
        # Something lik asyncio.ensure_future(self._heartbeat(ws))

        # Make it available for send job
        self._sockets.setdefault((row_i, col_i), []).append(socket)

        # Start to listen client messages
        await self._listen(socket, row_i, col_i)

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
                except DisconnectClient:
                    await socket.send_str(
                        self._event_serializer_factory.get_serializer(
                            ZoneEventType.SERVER_PERMIT_CLOSE
                        ).dump_json(
                            ZoneEvent(type=ZoneEventType.SERVER_PERMIT_CLOSE, data=EmptyData())
                        )
                    )
                    return

        server_logger.info(f"Websocket of zone {row_i},{col_i} closed")

    async def _process_msg(
        self, row_i: int, col_i: int, msg, socket: web.WebSocketResponse
    ) -> None:
        event_dict = json.loads(msg.data)
        event_type = ZoneEventType(event_dict["type"])
        event = self._event_serializer_factory.get_serializer(event_type).load(event_dict)
        await self._process_event(row_i, col_i, event, socket)

    async def _process_event(
        self, row_i: int, col_i: int, event: ZoneEvent, socket: web.WebSocketResponse
    ) -> None:
        try:
            event_processor = self._event_processor_factory.get_processor(event.type)
        except UnknownEvent:
            server_logger.warning(f"Unknown received event type '{event.type}'")
            return

        try:
            await event_processor.process(row_i, col_i, event)
        except UnableToProcessEvent as exc:
            server_logger.debug(f"Unable to process event {event.type}: {str(exc)}")

            exception_event = exc.event
            exception_event_str = self._event_serializer_factory.get_serializer(
                exception_event.type
            ).dump_json(exception_event)

            # FIXME: do kept this feature ?
            await socket.send_str(exception_event_str)

    async def get_sockets(
        self, row_i: int, col_i: int
    ) -> typing.AsyncIterable[web.WebSocketResponse]:
        for socket in self._sockets[(row_i, col_i)]:
            yield socket
