# coding: utf-8
import asyncio

from rolling.kernel import Kernel
from rolling.log import server_logger


def get_kernel(world_map_source_path: str, tile_maps_folder_path: str) -> Kernel:
    server_logger.info('Read world map source file "{}"'.format(world_map_source_path))
    with open(world_map_source_path, "r") as f:
        world_map_source_raw = f.read()

    server_logger.info(
        'Start kernel with tile maps folder "{}"'.format(tile_maps_folder_path)
    )
    loop = asyncio.get_event_loop()
    kernel = Kernel(
        world_map_source_raw, loop=loop, tile_maps_folder=tile_maps_folder_path
    )
    kernel.init_server_db_session()
    return kernel
