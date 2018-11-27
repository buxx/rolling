# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application

from rolling.server.controller.character import CharacterController


def get_application() -> Application:
    app = web.Application()

    # Bind routes
    CharacterController().bind(app)

    return app
