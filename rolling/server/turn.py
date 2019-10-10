# coding: utf-8
import argparse
import logging

from rolling.log import configure_logging
from rolling.log import server_logger
from rolling.server.base import get_kernel
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.server.lib.turn import TurnLib


def run(args: argparse.Namespace) -> None:
    # Configure logging
    if args.debug:
        configure_logging(logging.DEBUG)
    else:
        configure_logging(logging.INFO)

    kernel = get_kernel(args.world_map_source, args.tile_maps_folder, args.game_config_folder)
    character_lib = CharacterLib(kernel)
    stuff_lib = StuffLib(kernel)
    turn_lib = TurnLib(kernel, character_lib, stuff_lib, logger=server_logger)
    turn_lib.execute_turn()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pass the game turn")
    parser.add_argument("world_map_source", type=str, help="Raw world source map file path")
    parser.add_argument("tile_maps_folder", type=str, help="Tile maps sources files folder path")
    parser.add_argument("game_config_folder", type=str, help="Directory path with game configs")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
