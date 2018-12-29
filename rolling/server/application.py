# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application

from rolling.kernel import Kernel
from rolling.server.controller.character import CharacterController


def get_application(kernel: Kernel) -> Application:
    app = web.Application()

    # Bind routes
    CharacterController(kernel).bind(app)

    return app
