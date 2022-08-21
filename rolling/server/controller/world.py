# coding: utf-8
import dataclasses
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic import HapicData

from rolling.kernel import Kernel
from rolling.model.world import WorldAsCharacter
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic


@dataclasses.dataclass
class CharacterIdModel:
    character_id: str


class WorldController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    @hapic.with_api_doc()
    async def get_world_source(self, request: Request) -> web.Response:
        return web.Response(body=self._kernel.world_map_source.raw_source)

    async def events(self, request: Request):
        # TODO BS 2019-01-23: Establish world websocket must require access like private key
        return await self._kernel.server_world_events_manager.get_new_socket(request)

    @hapic.with_api_doc()
    @hapic.input_path(CharacterIdModel)
    @hapic.output_body(WorldAsCharacter)
    async def get_world_as_character(
        self, request: Request, hapic_data: HapicData
    ) -> web.Response:
        return self._kernel.world_lib.get_world_as_character(
            hapic_data.path.character_id
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/world/source", self.get_world_source),
                web.get(
                    "/world/as-character/{character_id}", self.get_world_as_character
                ),
                web.get("/world/events", self.events),
                web.get("/ws/world/events", self.events),
            ]
        )
