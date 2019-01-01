# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application

from rolling.kernel import Kernel
from rolling.server.controller.character import CharacterController
from rolling.server.controller.tile import TileController


def get_application(kernel: Kernel) -> Application:
    app = web.Application()

    # Bind routes
    CharacterController(kernel).bind(app)
    TileController(kernel).bind(app)

    return app
