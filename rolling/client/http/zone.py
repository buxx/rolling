# coding: utf-8
from queue import Queue
import typing

import aiohttp
from aiohttp import WSMessage
from aiohttp.client import _WSRequestContextManager
import serpyco

from rolling.client.http.client import HttpClient
from rolling.client.lib.zone import ZoneLib
from rolling.log import gui_logger
from rolling.model.event import ZoneEvent
from rolling.model.event import zone_event_data_types

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

    async def make_connection(self, row_i: int, col_i: int) -> None:
        session = aiohttp.ClientSession()
        websocket_url = self._client_getter().get_zone_events_url(row_i, col_i)
        gui_logger.debug(f'Connect websocket to "{websocket_url}"')
        self._ws = await session.ws_connect(websocket_url)

    async def listen(self) -> None:
        while True:
            msg: WSMessage = await self._ws.receive()

            if msg.type == aiohttp.WSMsgType.text:
                self._proceed_received_package(msg.data)

            elif msg.type == aiohttp.WSMsgType.closed:
                gui_logger.info(f"Websocket closed by server")
                break
            elif msg.type == aiohttp.WSMsgType.error:
                gui_logger.info(f"Websocket closed by server with error")
                break

    def _proceed_received_package(self, data: str) -> None:
        gui_logger.debug(f'Received package: "{data}"')
        # fill self._received_zone_queue with ZoneEvent objects

    async def send_event(self, event: ZoneEvent) -> None:
        # TODO BS 2019-01-22: Prepare all these serializer to improve performances
        data_type = zone_event_data_types[event.type]
        serializer = serpyco.Serializer(ZoneEvent[data_type])

        event_str = serializer.dump_json(event)
        await self._ws.send_str(event_str)
