# coding: utf-8
import argparse
import os

from rolling.kernel import Kernel, ServerConfig
from rolling.map.generator.filler.simple import SimpleFillerFactory
from rolling.map.generator.generator import FromWorldMapGenerator
from rolling.map.source import WorldMapSource


def run(args: argparse.Namespace) -> None:
    os.makedirs(args.export_folder, exist_ok=True)

    with open(args.source, "r") as f:
        raw_world = f.read()

    config = ServerConfig.from_config_file_path(args.server_config_file_path)
    kernel = Kernel(server_config=config, world_map_str=raw_world)
    world_map_source = WorldMapSource(kernel, raw_world)
    generator = FromWorldMapGenerator(
        kernel,
        default_map_width=args.map_widths,
        default_map_height=args.map_heights,
        filler_factory=SimpleFillerFactory(),
        world_map_source=world_map_source,
    )

    tile_maps = generator.generate()
    for tile_map in tile_maps:
        tile_map_str = "::GEO\n"

        for row in tile_map.source.geography.rows:
            for world_map_tile_type in row:
                char = tile_map.source.legend.get_str_with_type(world_map_tile_type)
                tile_map_str += char

            tile_map_str += "\n"

        tile_map_file_path = os.path.join(
            args.export_folder, "{}-{}.txt".format(tile_map.row_i, tile_map.col_i)
        )
        with open(tile_map_file_path, "w+") as f:
            f.write(tile_map_str)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tile map generator")
    parser.add_argument("source", type=str, help="World source map")
    parser.add_argument("export_folder", type=str, help="Export folder")
    parser.add_argument(
        "--map-widths", type=int, default=129, help="Default generated map widths"
    )
    parser.add_argument(
        "--map-heights", type=int, default=129, help="Default generated map heights"
    )
    parser.add_argument(
        "--server-config-file-path",
        type=str,
        help="server config file path",
        default="./server.ini",
    )
    # TODO BS 2018-12-29: Permit choose filler factory

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
