# coding: utf-8
import json
from queue import Queue
import typing

import aiohttp
from aiohttp import WSMessage
from aiohttp.client import _WSRequestContextManager
import serpyco

from rolling.client.http.client import HttpClient
from rolling.client.lib.zone import ZoneLib
from rolling.gui.event import EventProcessorFactory
from rolling.log import gui_logger
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.model.event import zone_event_data_types
from rolling.model.serializer import ZoneEventSerializerFactory

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller


class ZoneWebSocketClient(object):
    def __init__(
        self,
        controller: "Controller",
        zone_lib: ZoneLib,
        client_getter: typing.Callable[[], HttpClient],
        received_zone_queue: Queue,
    ) -> None:
        self._controller = controller
        self._zone_lib = zone_lib
        self._client_getter = client_getter
        self._ws: typing.Optional[_WSRequestContextManager] = None
        self._received_zone_queue = received_zone_queue
        self._event_processor_factory = EventProcessorFactory(
            self._controller.kernel, controller
        )
        self._event_serializer_factory = ZoneEventSerializerFactory()

    async def make_connection(self, row_i: int, col_i: int) -> None:
        session = aiohttp.ClientSession()
        websocket_url = self._client_getter().get_zone_events_url(row_i, col_i)
        gui_logger.debug(f'Connect websocket to "{websocket_url}"')
        self._ws = await session.ws_connect(websocket_url)

    async def listen(self) -> None:
        while True:
            msg: WSMessage = await self._ws.receive()

            if msg.type == aiohttp.WSMsgType.text:
                await self._proceed_received_package(msg.data)

            elif msg.type == aiohttp.WSMsgType.closed:
                gui_logger.info(f"Websocket closed by server")
                break
            elif msg.type == aiohttp.WSMsgType.error:
                gui_logger.info(f"Websocket closed by server with error")
                break

    async def _proceed_received_package(self, msg_data: str) -> None:
        gui_logger.debug(f'Received package: "{msg_data}"')

        event_dict = json.loads(msg_data)
        event_type = ZoneEventType(event_dict["type"])
        event = self._event_serializer_factory.get_serializer(event_type).load(
            event_dict
        )

        processor = self._event_processor_factory.get_processor(event.type)
        await processor.process(event)

    async def send_event(self, event: ZoneEvent) -> None:
        event_str = self._event_serializer_factory.get_serializer(event.type).dump_json(
            event
        )
        await self._ws.send_str(event_str)
