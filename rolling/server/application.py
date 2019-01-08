# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application

from rolling.kernel import Kernel
from rolling.server.controller.character import CharacterController
from rolling.server.controller.world import WorldController
from rolling.server.controller.zone import ZoneController


def get_application(kernel: Kernel) -> Application:
    app = web.Application()

    # Bind routes
    CharacterController(kernel).bind(app)
    ZoneController(kernel).bind(app)
    WorldController(kernel).bind(app)

    return app
