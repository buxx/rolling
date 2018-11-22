# coding: utf-8
import argparse

from rolling.client.http.client import HttpClient
from rolling.gui.controller import Controller


def run(args: argparse.Namespace) -> None:
    client = HttpClient(server_address=args.server_address)

    controler = Controller(client=client)
    controler.main()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Rolling interface")
    parser.add_argument("--server-address", type=str, help="Game server address")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
