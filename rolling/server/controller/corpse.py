# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from hapic.data import HapicData
import typing

from sqlalchemy.exc import NoResultFound

from rolling.kernel import Kernel
from rolling.model.corpse import AnimatedCorpseModel, GetAnimatedCorpsePath, \
    SignalNewAnimatedCorpsePath
from rolling.model.corpse import GetAnimatedCorpsesQuery
from rolling.model.event import WebSocketEvent, ZoneEventType, NewAnimatedCorpseData
from rolling.server.controller.base import BaseController
from rolling.server.document.corpse import AnimatedCorpseDocument
from rolling.server.extension import hapic
from rolling.server.processor import RollingSerpycoProcessor


class AnimatedCorpseController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    def bind(self, app: Application) -> None:
        app.add_routes([
            web.get("/ac/", self.get_animated_corpses),
            web.get("/ac/{animated_corpse_id}", self.get_animated_corpse),
            web.put("/ac-signal/new/{animated_corpse_id}", self.signal_new),
        ])

    @hapic.with_api_doc()
    @hapic.input_query(GetAnimatedCorpsesQuery)
    @hapic.output_body(AnimatedCorpseModel, processor=RollingSerpycoProcessor(many=True))
    async def get_animated_corpses(
        self, request: Request, hapic_data: HapicData
    ) -> typing.List[AnimatedCorpseDocument]:
        return self._kernel.animated_corpse_lib.get_all(
            world_row_i=hapic_data.query.world_row_i, world_col_i=hapic_data.query.world_col_i
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetAnimatedCorpsePath)
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.output_body(AnimatedCorpseModel)
    async def get_animated_corpse(
        self, request: Request, hapic_data: HapicData
    ) -> AnimatedCorpseDocument:
        return self._kernel.animated_corpse_lib.get(hapic_data.path.animated_corpse_id)

    @hapic.with_api_doc()
    @hapic.input_path(SignalNewAnimatedCorpsePath)
    @hapic.handle_exception(NoResultFound, http_code=404)
    async def signal_new(
        self, request: Request, hapic_data: HapicData
    ) -> Response:
        from rolling.server.application import HEADER_NAME__DISABLE_AUTH_TOKEN
        if request.headers.get(HEADER_NAME__DISABLE_AUTH_TOKEN) != self._kernel.server_config.disable_auth_token:
            return Response(status=403)

        animated_corpse = self._kernel.animated_corpse_lib.get(hapic_data.path.animated_corpse_id)

        event = WebSocketEvent(
            type=ZoneEventType.NEW_ANIMATED_CORPSE,
            world_row_i=animated_corpse.world_row_i,
            world_col_i=animated_corpse.world_col_i,
            data=NewAnimatedCorpseData(animated_corpse_id=animated_corpse.id),
        )
        await self._kernel.server_zone_events_manager.send_to_sockets(
            event,
            world_row_i=animated_corpse.world_row_i,
            world_col_i=animated_corpse.world_col_i,
        )

        return Response(status=204)

