# coding: utf-8
import argparse

from rolling.client.http.client import HttpClient
from rolling.gui.controller import Controller
from rolling.gui.kernel import Kernel


def run(args: argparse.Namespace) -> None:
    client = HttpClient(server_address=args.server_address)

    with open('tests/src/worldmapa.txt') as world_map_file:
        world_map_str = world_map_file.read()

    kernel = Kernel(world_map_str)
    controller = Controller(client=client, kernel=kernel)
    controller.main()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Rolling interface")
    parser.add_argument("--server-address", type=str, help="Game server address")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
