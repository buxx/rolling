# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic.data import HapicData
import typing

from rolling.kernel import Kernel
from rolling.model.corpse import AnimatedCorpseModel
from rolling.model.corpse import GetAnimatedCorpsesQuery
from rolling.server.controller.base import BaseController
from rolling.server.document.corpse import AnimatedCorpseDocument
from rolling.server.extension import hapic
from rolling.server.processor import RollingSerpycoProcessor


class AnimatedCorpseController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    def bind(self, app: Application) -> None:
        app.add_routes([web.get("/ac/", self.get_animated_corpses)])

    @hapic.with_api_doc()
    @hapic.input_query(GetAnimatedCorpsesQuery)
    @hapic.output_body(AnimatedCorpseModel, processor=RollingSerpycoProcessor(many=True))
    async def get_animated_corpses(
        self, request: Request, hapic_data: HapicData
    ) -> typing.List[AnimatedCorpseDocument]:
        return self._kernel.animated_corpse_lib.get_all(
            world_row_i=hapic_data.query.world_row_i, world_col_i=hapic_data.query.world_col_i
        )
