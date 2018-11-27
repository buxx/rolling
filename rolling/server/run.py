# coding: utf-8
import argparse

from aiohttp import web
from hapic.ext.aiohttp.context import AiohttpContext
from hapic.processor.serpyco import SerpycoProcessor

from rolling.server.application import get_application
from rolling.server.extension import hapic


def run(args: argparse.Namespace) -> None:
    app = get_application()

    # Configure hapic
    hapic.set_processor_class(SerpycoProcessor)
    hapic.set_context(AiohttpContext(app))

    web.run_app(app, host=args.host, port=args.port)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Rolling interface")
    parser.add_argument("--host", type=str, default='127.0.0.1', help="Server host")
    parser.add_argument("--port", type=str, default=5000, help="Server port")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
