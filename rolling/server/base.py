# coding: utf-8
from aiohttp import WSMessage
from aiohttp import web
from aiohttp.web_request import Request
import asyncio
import typing
from rolling.kernel import ServerConfig

from rolling.log import server_logger

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


def get_kernel(config: ServerConfig) -> "Kernel":
    from rolling.kernel import Kernel

    world_map_source_raw = None

    if config.worldmap:
        server_logger.info('Read world map source file "{}"'.format(config.worldmap))
        with open(config.worldmap, "r") as f:
            world_map_source_raw = f.read()

    if config.zones:
        server_logger.info('Start kernel with zones folder "{}"'.format(config.zones))

    loop = asyncio.get_event_loop()
    kernel = Kernel(
        server_config=config,
        world_map_str=world_map_source_raw,
        loop=loop,
    )

    kernel.init_server_db_session()
    return kernel
