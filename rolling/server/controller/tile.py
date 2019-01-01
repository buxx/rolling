#  coding: utf-8
import typing

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic.processor.serpyco import SerpycoProcessor

from rolling.kernel import Kernel
from rolling.model.tile import ZoneTileModel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.server.lib.tile import TileLib


class TileController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)
        self._tile_lib = TileLib(self._kernel)

    @hapic.with_api_doc()
    @hapic.output_body(ZoneTileModel, processor=SerpycoProcessor(many=True))
    async def get_tiles(self, request: Request) -> typing.List[ZoneTileModel]:
        return self._tile_lib.get_all_tiles()

    def bind(self, app: Application) -> None:
        app.add_routes(
            [web.get("/tiles", self.get_tiles)]
        )
