# coding: utf-8
import argparse
import asyncio
import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound

from hapic.ext.aiohttp.context import AiohttpContext
from hapic.processor.serpyco import SerpycoProcessor
from rolling.kernel import Kernel
from rolling.log import configure_logging
from rolling.log import server_logger
from rolling.server.application import get_application
from rolling.server.base import get_kernel
from rolling.server.extension import hapic


def run(args: argparse.Namespace) -> None:
    # Configure logging
    if args.debug:
        configure_logging(logging.DEBUG)
    else:
        configure_logging(logging.INFO)

    kernel = get_kernel(
        args.world_map_source, args.tile_maps_folder, args.game_config_folder
    )
    server_logger.info("Create web application")
    app = get_application(kernel)

    # Configure hapic
    server_logger.info("Configure web api")
    context = AiohttpContext(app, debug=args.debug)
    context.handle_exception(HTTPNotFound, http_code=404)
    context.handle_exception(Exception, http_code=500)
    hapic.set_processor_class(SerpycoProcessor)
    hapic.set_context(context)

    server_logger.info("Start server listening on {}:{}".format(args.host, args.port))
    web.run_app(app, host=args.host, port=args.port, access_log=server_logger)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Rolling interface")
    parser.add_argument(
        "world_map_source", type=str, help="Raw world source map file path"
    )
    parser.add_argument(
        "tile_maps_folder", type=str, help="Tile maps sources files folder path"
    )
    parser.add_argument(
        "game_config_folder", type=str, help="Directory path with game configs"
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=str, default=5000, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
