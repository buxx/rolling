# coding: utf-8
import asyncio
import typing

from aiohttp import web, WSMessage
from aiohttp.web_request import Request

from rolling.log import server_logger

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


def get_kernel(
    world_map_source_path: typing.Optional[str] = None,
    tile_maps_folder_path: typing.Optional[str] = None,
    game_config_folder: typing.Optional[str] = None,
    server_db_path: str = "server.db",
) -> "Kernel":
    from rolling.kernel import Kernel
    world_map_source_raw = None

    if world_map_source_path:
        server_logger.info('Read world map source file "{}"'.format(world_map_source_path))
        with open(world_map_source_path, "r") as f:
            world_map_source_raw = f.read()

    if tile_maps_folder_path:
        server_logger.info('Start kernel with tile maps folder "{}"'.format(tile_maps_folder_path))

    loop = asyncio.get_event_loop()
    kernel = Kernel(
        world_map_source_raw,
        loop=loop,
        tile_maps_folder=tile_maps_folder_path,
        game_config_folder=game_config_folder,
        server_db_path=server_db_path,
    )

    kernel.init_server_db_session()
    return kernel


class BaseEventSocketWrapper:

    async def send_to_zone_str(self, message: str) -> None:
        await self._socket.send_str(message)

    async def prepare(self, request: Request) -> None:
        await self._socket.prepare(request)

    def iter(self) -> typing.AsyncIterable[WSMessage]:
        for msg in self._socket:
            yield msg

    def exception(self) -> typing.Optional[BaseException]:
        return self._socket.exception()


class ZoneEventSocketWrapper(BaseEventSocketWrapper):
    def __init__(
        self, kernel: "Kernel", socket: web.WebSocketResponse, zone_row_i: int, zone_col_i: int
    ) -> None:
        self._kernel = kernel
        self._socket = socket
        self._zone_row_i = zone_row_i
        self._zone_col_i = zone_col_i

    async def send_to_zone_str(self, message: str, repeat_to_world: bool = True) -> None:
        await super().send_to_zone_str(message)
        if repeat_to_world:
            # Replicate message on world websockets
            for socket in self._kernel.server_world_events_manager.get_sockets():
                await socket.send_to_world_str(
                    message,
                    zone_row_i=self._zone_row_i,
                    zone_col_i=self._zone_col_i,
                    repeat_to_zone=False,
                )


class WorldEventSocketWrapper(BaseEventSocketWrapper):
    def __init__(
        self, kernel: "Kernel", socket: web.WebSocketResponse
    ) -> None:
        self._kernel = kernel
        self._socket = socket

    async def send_to_world_str(
        self, message: str, zone_row_i: int, zone_col_i: int, repeat_to_zone: bool = True
    ) -> None:
        await super().send_to_zone_str(message)
        if repeat_to_zone:
            # Replicate message on concerned zone websockets
            for socket in self._kernel.server_zone_events_manager.get_sockets(
                row_i=zone_row_i, col_i=zone_col_i
            ):
                await socket.send_to_zone_str(message, repeat_to_world=False)
