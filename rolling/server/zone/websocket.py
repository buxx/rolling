# coding: utf-8
import asyncio
import json
import typing

import aiohttp
from aiohttp import web
from aiohttp.web_request import Request
import serpyco

from rolling.exception import UnableToProcessEvent
from rolling.log import server_logger
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.model.event import zone_event_data_types
from rolling.server.zone.event import EventProcessorFactory

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class ZoneEventsManager(object):
    def __init__(self, kernel: "Kernel", loop: asyncio.AbstractEventLoop) -> None:
        self._sockets: typing.Dict[
            typing.Tuple[int, int], typing.List[web.WebSocketResponse]
        ] = {}
        self._event_processor_factory = EventProcessorFactory(kernel, self)
        self._loop = loop
        self._kernel = kernel

    async def get_new_socket(
        self, request: Request, row_i: int, col_i: int
    ) -> web.WebSocketResponse:
        server_logger.info(f"Create websocket for zone {row_i},{col_i}")

        # Create socket
        socket = web.WebSocketResponse()
        await socket.prepare(request)

        # Make it available for send job
        self._sockets.setdefault((row_i, col_i), []).append(socket)

        # Start to listen client messages
        await self._listen(socket, row_i, col_i)

        return socket

    async def _listen(
        self, socket: web.WebSocketResponse, row_i: int, col_i: int
    ) -> None:
        server_logger.info(f"Listen websocket for zone {row_i},{col_i}")
        async for msg in socket:
            server_logger.debug(
                f"Receive message on websocket for zone {row_i},{col_i}: {msg}"
            )

            if msg.type == aiohttp.WSMsgType.ERROR:
                server_logger.error(
                    f"Zone websocket closed with exception {socket.exception()}"
                )
            else:
                await self._process_msg(row_i, col_i, msg, socket)

        server_logger.info(f"Websocket of zone {row_i},{col_i} closed")

    async def _process_msg(
        self, row_i: int, col_i: int, msg, socket: web.WebSocketResponse
    ) -> None:
        event_dict = json.loads(msg.data)
        # TODO BS 2019-01-22: Prepare all these serializer to improve performances
        data_type = zone_event_data_types[ZoneEventType(event_dict["type"])]
        serializer = serpyco.Serializer(ZoneEvent[data_type])

        event = serializer.load(event_dict)
        await self._process_event(row_i, col_i, event, socket)

    async def _process_event(
        self, row_i: int, col_i: int, event: ZoneEvent, socket: web.WebSocketResponse
    ) -> None:
        event_processor = self._event_processor_factory.get_processor(event.type)
        try:
            await event_processor.process(row_i, col_i, event)
        except UnableToProcessEvent as exc:
            server_logger.debug(f"Unable to process event {event.type}: {str(exc)}")

            # FIXME BS 2019-01-23: Refactorize these serializers !
            # TODO BS 2019-01-22: Prepare all these serializer to improve performances
            exception_event = exc.event
            data_type = zone_event_data_types[exception_event.type]
            serializer = serpyco.Serializer(ZoneEvent[data_type])

            exception_event_str = serializer.dump_json(exception_event)
            await socket.send_str(exception_event_str)

    def get_sockets(self, row_i: int, col_i: int) -> typing.List[web.WebSocketResponse]:
        return self._sockets[(row_i, col_i)]
