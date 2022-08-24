# coding: utf-8
import pathlib
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp_basicauth_middleware import basic_auth_middleware
import aiohttp_jinja2
import argparse
from hapic.error.serpyco import DefaultErrorSchema
from hapic.error.serpyco import SerpycoDefaultErrorBuilder
from hapic.ext.aiohttp.context import AiohttpContext
from hapic.processor.main import ProcessValidationError
import jinja2
import logging
import os
from serpyco import ValidationError
import signal
import asyncio

from rolling.exception import UserDisplayError
from rolling.log import configure_logging
from rolling.log import server_logger
from rolling.server.application import get_application
from rolling.server.base import get_kernel
from rolling.server.extension import hapic
from rolling.server.processor import RollingSerpycoProcessor


class ErrorBuilder(SerpycoDefaultErrorBuilder):
    def build_from_exception(
        self, exception: Exception, include_traceback: bool = False
    ) -> DefaultErrorSchema:
        if isinstance(exception, UserDisplayError):
            return DefaultErrorSchema(message=str(exception))
        elif isinstance(exception, ValueError):
            server_logger.exception(exception)
            return DefaultErrorSchema(
                message=(
                    "Une erreur serveur est survenue. Une erreur de saisie peut en être la cause"
                )
            )
        elif isinstance(exception, ValidationError):
            server_logger.exception(exception)
            return DefaultErrorSchema(
                message=(f"Il y a une erreur de saisie: {exception.args[0]}")
            )

        server_logger.exception(exception)
        return DefaultErrorSchema(message="Une erreur serveur est survenue")

    def build_from_validation_error(
        self, error: ProcessValidationError
    ) -> DefaultErrorSchema:
        server_logger.debug(str(error))
        err = super().build_from_validation_error(error)
        return err


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
        args.server_config_file_path,
    )
    server_logger.info("Create web application")

    if args.serve_static_files:
        for check_file_path in (
            pathlib.Path(args.serve_static_files) / "engine.wasm",
            pathlib.Path(args.serve_static_files) / "graphics.png",
            pathlib.Path(args.serve_static_files) / "mq_js_bundle.js",
            pathlib.Path(args.serve_static_files) / "rollgui2.js",
        ):
            if not check_file_path.exists():
                print(f"'{check_file_path}' not found or not readable")
                exit(1)

    app = get_application(
        kernel,
        disable_auth=args.disable_auth,
        serve_static_files=args.serve_static_files,
    )
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")
        ),
    )
    app.middlewares.append(
        basic_auth_middleware(
            ("/admin",),
            {kernel.server_config.admin_login: kernel.server_config.admin_password},
        )
    )

    # Configure hapic
    server_logger.info("Configure web api")
    context = AiohttpContext(
        app, debug=args.debug, default_error_builder=ErrorBuilder()
    )
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
            dsn=args.sentry,
            integrations=[AioHttpIntegration(), SqlalchemyIntegration()],
        )

    kernel.init()
    kernel.ensure_avatar_medias()
    kernel.ensure_loading_medias()
    kernel_tasks = kernel.tasks()

    server_logger.info("Start server listening on {}:{}".format(args.host, args.port))
    signal.signal(signal.SIGHUP, kernel.on_sighup_signal)

    async def on_startup(app):
        for task in kernel_tasks:
            asyncio.create_task(task)

    app.on_startup.append(on_startup)

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
    parser.add_argument(
        "server_config_file_path",
        type=str,
        help="server config file path",
        default="./server.ini",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=str, default=5000, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--serve-static-files",
        type=str,
        help="Serve static files with python instead apache/nginx with given folder path",
    )
    parser.add_argument(
        "--sentry", type=str, help="Sentry address to use", default=None
    )
    parser.add_argument(
        "--server-db-path", type=str, help="path of server.db", default="server.db"
    )
    parser.add_argument("--disable-auth", action="store_true", default=False)

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
