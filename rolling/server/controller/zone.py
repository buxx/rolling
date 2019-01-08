#  coding: utf-8
import typing

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request

from hapic import HapicData
from hapic.processor.serpyco import SerpycoProcessor
from rolling.exception import NoZoneMapError
from rolling.kernel import Kernel
from rolling.model.zone import GetZonePathModel
from rolling.model.zone import ZoneMapModel
from rolling.model.zone import ZoneTileTypeModel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.server.lib.zone import ZoneLib


class ZoneController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)
        self._tile_lib = ZoneLib(self._kernel)

    @hapic.with_api_doc()
    @hapic.output_body(ZoneTileTypeModel, processor=SerpycoProcessor(many=True))
    async def get_tiles(self, request: Request) -> typing.List[ZoneTileTypeModel]:
        return self._tile_lib.get_all_tiles()

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.output_body(ZoneMapModel)
    async def get_zone(self, request: Request, hapic_data: HapicData) -> ZoneMapModel:
        return self._tile_lib.get_zone(
            row_i=hapic_data.path.row_i, col_i=hapic_data.path.col_i
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/zone/tiles", self.get_tiles),
                web.get("/zone/{row_i}/{col_i}", self.get_zone),
            ]
        )
