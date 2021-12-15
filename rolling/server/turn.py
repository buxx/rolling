# coding: utf-8
import argparse
import logging
import asyncio

from rolling.log import configure_logging
from rolling.log import server_logger
from rolling.server.base import get_kernel
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

    kernel = get_kernel(
        world_map_source_path=args.world_map_source,
        tile_maps_folder_path=args.tile_maps_folder,
        game_config_folder=args.game_config_folder,
        server_config_file_path=args.server_config_file_path,
    )
    character_lib = CharacterLib(kernel)
    stuff_lib = StuffLib(kernel)
    turn_lib = TurnLib(
        kernel,
        character_lib=character_lib,
        stuff_lib=stuff_lib,
        logger=server_logger,
    )
    turn_lib.execute_turn()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pass the game turn")
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
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--sentry", type=str, help="Sentry address to use", default=None
    )

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
