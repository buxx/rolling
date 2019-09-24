#  coding: utf-8
import typing

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic import HapicData
from hapic.processor.serpyco import SerpycoProcessor

from rolling.exception import NoZoneMapError
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
from rolling.model.zone import GetZonePathModel
from rolling.model.zone import ZoneMapModel
from rolling.model.zone import ZoneTileTypeModel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.server.lib.zone import ZoneLib


class ZoneController(BaseController):
    def __init__(
        self,
        kernel: Kernel,
        character_lib: typing.Optional[CharacterLib] = None,
        stuff_lib: typing.Optional[StuffLib] = None,
    ) -> None:
        super().__init__(kernel)
        self._tile_lib = ZoneLib(self._kernel)
        self._character_lib = character_lib or CharacterLib(self._kernel)
        self._stuff_lib = stuff_lib or StuffLib(self._kernel)

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

    async def events(self, request: Request):
        # TODO BS 2019-01-23: Establish zone websocket must require character in zone
        return await self._kernel.server_zone_events_manager.get_new_socket(
            request,
            row_i=request.match_info["row_i"],
            col_i=request.match_info["col_i"],
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.output_body(CharacterModel, processor=SerpycoProcessor(many=True))
    async def get_characters(
        self, request: Request, hapic_data: HapicData
    ) -> typing.List[CharacterModel]:
        return self._character_lib.get_zone_players(
            row_i=request.match_info["row_i"], col_i=request.match_info["col_i"]
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.output_body(StuffModel, processor=SerpycoProcessor(many=True))
    async def get_stuff(
        self, request: Request, hapic_data: HapicData
    ) -> typing.List[StuffModel]:
        return self._stuff_lib.get_zone_stuffs(
            world_row_i=request.match_info["row_i"],
            world_col_i=request.match_info["col_i"],
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/zones/tiles", self.get_tiles),
                web.get("/zones/{row_i}/{col_i}", self.get_zone),
                web.get("/zones/{row_i}/{col_i}/events", self.events),
                # TODO BS 2019-01-23: put /zones/{row_i}/{col_i}/enter to ask entering in zone
                web.get("/zones/{row_i}/{col_i}/characters", self.get_characters),
                web.get("/zones/{row_i}/{col_i}/stuff", self.get_stuff),
            ]
        )
