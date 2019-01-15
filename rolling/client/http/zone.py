# coding: utf-8
import typing
from queue import Queue

import aiohttp
from aiohttp.client import _WSRequestContextManager

from rolling.client.http.client import HttpClient
from rolling.client.lib.zone import ZoneLib
from rolling.log import gui_logger
from rolling.model.event import ZoneEvent

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
            msg = await self._ws.receive()

            if msg.tp == aiohttp.MsgType.text:
                self._proceed_received_package(msg.data)

            elif msg.tp == aiohttp.MsgType.closed:
                gui_logger.info(f"Websocket closed by server")
                break
            elif msg.tp == aiohttp.MsgType.error:
                gui_logger.info(f"Websocket closed by server with error")
                break

    def _proceed_received_package(self, data: str) -> None:
        gui_logger.debug(f'Received package: "{data}"')
        # fill self._received_zone_queue with ZoneEvent objects

    async def send_event(self, event: ZoneEvent) -> None:
        pass  # TODO
