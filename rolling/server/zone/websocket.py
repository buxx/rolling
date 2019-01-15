# coding: utf-8
import asyncio
import typing

import aiohttp
from aiohttp import web
from aiohttp.web_request import Request

from rolling.log import server_logger


class ZoneEventsManager(object):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._sockets: typing.Dict[
            typing.Tuple[int, int], typing.List[web.WebSocketResponse]
        ] = {}
        # self._connection_established: typing.Dict[web.WebSocketResponse, asyncio.Event] = {}
        self._loop = loop

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

            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == "close":
                    await socket.close()
                else:
                    await socket.send_str(msg.data + "/answer")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                server_logger.error(
                    f"Zone websocket closed with exception {socket.exception()}"
                )

        server_logger.info(f"Websocket of zone {row_i},{col_i} closed")
