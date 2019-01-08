#  coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request

from rolling.kernel import Kernel
from rolling.model.world import WorldMapLegendModel
from rolling.model.world import WorldMapModel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.server.lib.world import WorldLib


class WorldController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)
        self._world_lib = WorldLib(self._kernel)

    @hapic.with_api_doc()
    @hapic.output_body(WorldMapModel)
    async def get_world(self, request: Request) -> WorldMapModel:
        return self._world_lib.get_world()

    @hapic.with_api_doc()
    @hapic.output_body(WorldMapLegendModel)
    async def get_legend(self, request: Request) -> WorldMapLegendModel:
        return self._world_lib.get_legend()

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/world/legend", self.get_legend),
                web.get("/world", self.get_world),
            ]
        )
