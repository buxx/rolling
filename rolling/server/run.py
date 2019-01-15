# coding: utf-8
import argparse
import asyncio
import logging

from aiohttp import web

from hapic.ext.aiohttp.context import AiohttpContext
from hapic.processor.serpyco import SerpycoProcessor
from rolling.kernel import Kernel
from rolling.log import configure_logging
from rolling.log import server_logger
from rolling.server.application import get_application
from rolling.server.extension import hapic


def run(args: argparse.Namespace) -> None:
    # Configure logging
    if args.debug:
        configure_logging(logging.DEBUG)
    else:
        configure_logging(logging.INFO)

    server_logger.info('Read world map source file "{}"'.format(args.world_map_source))
    with open(args.world_map_source, "r") as f:
        world_map_source_raw = f.read()

    server_logger.info(
        'Start kernel with tile maps folder "{}"'.format(args.tile_maps_folder)
    )
    loop = asyncio.get_event_loop()
    kernel = Kernel(
        world_map_source_raw, loop=loop, tile_maps_folder=args.tile_maps_folder
    )
    kernel.init_server_db_session()

    server_logger.info("Create web application")
    app = get_application(kernel)

    # Configure hapic
    server_logger.info("Configure web api")
    context = AiohttpContext(app, debug=args.debug)
    context.handle_exception(Exception, http_code=500)
    hapic.set_context(context)
    hapic.set_processor_class(SerpycoProcessor)

    server_logger.info("Start server listening on {}:{}".format(args.host, args.port))
    web.run_app(app, host=args.host, port=args.port)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Rolling interface")
    parser.add_argument(
        "world_map_source", type=str, help="Raw world source map file path"
    )
    parser.add_argument(
        "tile_maps_folder", type=str, help="Tile maps sources files folder path"
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=str, default=5000, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
