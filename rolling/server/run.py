# coding: utf-8
import argparse

from aiohttp import web

from hapic.ext.aiohttp.context import AiohttpContext
from hapic.processor.serpyco import SerpycoProcessor
from rolling.kernel import Kernel
from rolling.map.source import WorldMapSource
from rolling.server.application import get_application
from rolling.server.extension import hapic


def run(args: argparse.Namespace) -> None:
    with open(args.world_map_source, "r") as f:
        world_map_source_raw = f.read()

    kernel = Kernel(world_map_source_raw, tile_maps_folder=args.tile_maps_folder)
    app = get_application(kernel)

    # Configure hapic
    hapic.set_processor_class(SerpycoProcessor)
    hapic.set_context(AiohttpContext(app))

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

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
