# coding: utf-8
import aiohttp_jinja2
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from pathlib import Path
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

    @hapic.with_api_doc()
    @aiohttp_jinja2.template("infos.html")
    async def infos(self, request: Request) -> dict:
        return {
            "game": self._kernel.game,
        }

    def bind(self, app: Application) -> None:
        Path("game/media/bg").mkdir(parents=True, exist_ok=True)
        app.add_routes(
            [
                web.get("/system/version", self.version),
                web.get("/infos", self.infos),
                web.static("/media", "game/media"),
                web.static("/media_bg", "game/media/bg"),
            ]
        )
