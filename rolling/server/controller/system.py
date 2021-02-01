# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import pkg_resources

from rolling.kernel import Kernel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic

version = pkg_resources.require("rolling")[0].version


class SystemController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    @hapic.with_api_doc()
    async def version(self, request: Request) -> Response:
        return Response(status=200, body=version)

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/system/version", self.version),
                web.static("/media", "game/media"),
                web.static("/media_bg", "game/media/bg"),
            ]
        )
