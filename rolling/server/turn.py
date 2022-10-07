# coding: utf-8
import argparse
import logging
import asyncio

from rolling.log import configure_logging
from rolling.log import server_logger
from rolling.server.base import get_kernel
from rolling.kernel import ServerConfig
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.server.lib.turn import TurnLib


async def run(args: argparse.Namespace) -> None:
    # Configure logging
    if args.debug:
        configure_logging(logging.DEBUG)
    else:
        configure_logging(logging.INFO)

    if args.sentry:
        import sentry_sdk
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(dsn=args.sentry, integrations=[SqlalchemyIntegration()])

    config = ServerConfig.from_config_file_path(args.server_config_file_path)
    kernel = get_kernel(config)
    character_lib = CharacterLib(kernel)
    stuff_lib = StuffLib(kernel)
    turn_lib = TurnLib(
        kernel,
        character_lib=character_lib,
        stuff_lib=stuff_lib,
        logger=server_logger,
        disable_natural_needs=args.disable_natural_needs,
    )
    turn_lib.execute_turn()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pass the game turn")
    parser.add_argument(
        "server_config_file_path",
        type=str,
        help="server config file path",
        default="./server.ini",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--sentry", type=str, help="Sentry address to use", default=None
    )
    parser.add_argument(
        "--disable-natural-needs",
        action="store_true",
        help="Disable natural needs of characters",
    )

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
