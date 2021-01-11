#  coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request

from rolling.kernel import Kernel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic


class WorldController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    @hapic.with_api_doc()
    async def get_world_source(self, request: Request) -> web.Response:
        return web.Response(body=self._kernel.world_map_source.raw_source)

    async def events(self, request: Request):
        # TODO BS 2019-01-23: Establish world websocket must require access like private key
        return await self._kernel.server_world_events_manager.get_new_socket(request)

    def bind(self, app: Application) -> None:
        app.add_routes(
            [web.get("/world/source", self.get_world_source), web.get("/world/events", self.events)]
        )
