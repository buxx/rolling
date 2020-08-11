# coding: utf-8
import argparse
import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound
from hapic.error.serpyco import DefaultErrorSchema
from hapic.error.serpyco import SerpycoDefaultErrorBuilder
from hapic.ext.aiohttp.context import AiohttpContext
from hapic.processor.main import ProcessValidationError

from rolling.exception import UserDisplayError
from rolling.log import configure_logging
from rolling.log import server_logger
from rolling.server.application import get_application
from rolling.server.base import get_kernel
from rolling.server.document.build import BuildDocument
from rolling.server.extension import hapic
from rolling.server.processor import RollingSerpycoProcessor


class ErrorBuilder(SerpycoDefaultErrorBuilder):
    def build_from_exception(
        self, exception: Exception, include_traceback: bool = False
    ) -> DefaultErrorSchema:
        server_logger.exception(exception)
        return super().build_from_exception(exception, include_traceback)

    def build_from_validation_error(self, error: ProcessValidationError) -> DefaultErrorSchema:
        server_logger.debug(str(error))
        return super().build_from_validation_error(error)


def run(args: argparse.Namespace) -> None:
    # Configure logging
    if args.debug:
        configure_logging(logging.DEBUG)
    else:
        configure_logging(logging.INFO)

    kernel = get_kernel(
        args.world_map_source,
        args.tile_maps_folder,
        args.game_config_folder,
        server_db_path=args.server_db_path,
    )
    server_logger.info("Create web application")
    app = get_application(kernel)

    # Configure hapic
    server_logger.info("Configure web api")
    context = AiohttpContext(app, debug=args.debug, default_error_builder=ErrorBuilder())
    context.handle_exception(HTTPNotFound, http_code=404)
    context.handle_exception(UserDisplayError, http_code=400)
    context.handle_exception(Exception, http_code=500)
    hapic.set_processor_class(RollingSerpycoProcessor)
    hapic.set_context(context)
    hapic.add_documentation_view("/doc")

    if args.sentry:
        import sentry_sdk
        from sentry_sdk.integrations.aiohttp import AioHttpIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=args.sentry, integrations=[AioHttpIntegration(), SqlalchemyIntegration()]
        )

    kernel.init()
    server_logger.info("Start server listening on {}:{}".format(args.host, args.port))
    web.run_app(app, host=args.host, port=args.port, access_log=server_logger)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Rolling interface")
    parser.add_argument("world_map_source", type=str, help="Raw world source map file path")
    parser.add_argument("tile_maps_folder", type=str, help="Tile maps sources files folder path")
    parser.add_argument("game_config_folder", type=str, help="Directory path with game configs")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=str, default=5000, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--sentry", type=str, help="Sentry address to use", default=None)
    parser.add_argument("--server-db-path", type=str, help="path of server.db", default="server.db")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
