# coding: utf-8
import argparse
import asyncio
import logging

from rolling.client.http.client import HttpClient
from rolling.gui.controller import Controller
from rolling.kernel import Kernel
from rolling.log import configure_logging
from rolling.log import gui_logger


def run(args: argparse.Namespace) -> None:
    # Configure logging
    if args.debug:
        configure_logging(logging.DEBUG)
    else:
        configure_logging(logging.INFO)

    client = HttpClient(server_address=args.server_address)

    loop = asyncio.get_event_loop()
    kernel = Kernel(loop=loop)
    controller = Controller(client=client, kernel=kernel)

    gui_logger.info("Start gui")
    controller.main()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Rolling interface")
    parser.add_argument("--server-address", type=str, help="Game server address")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
