# coding: utf-8
import argparse
import asyncio

import urwid

from rolling.client.http.client import HttpClient
from rolling.gui.controller import Controller
from rolling.gui.image.widget import ImageWidget
from rolling.kernel import Kernel


def run(args: argparse.Namespace) -> None:
    def exit_(*args, **kwargs):
        raise urwid.ExitMainLoop()

    image_widget = ImageWidget(args.image, callback=exit_)
    client = HttpClient(server_address="http://127.0.0.1")

    loop = asyncio.get_event_loop()
    kernel = Kernel(loop=loop)
    controller = Controller(client=client, kernel=kernel, root_menu_mode="exit_only")
    controller.view.main_content_container.original_widget = image_widget

    controller.main()


def main() -> None:
    parser = argparse.ArgumentParser(description="View image in 256 term colors")
    parser.add_argument("image", type=str, help="image path")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
