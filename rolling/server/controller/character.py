#  coding: utf-8
import uuid

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request

from rolling.model.character import CharacterModel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic


class CharacterController(BaseController):
    @hapic.with_api_doc()
    @hapic.output_body(CharacterModel)
    async def create(self, request: Request) -> CharacterModel:
        return CharacterModel(id=str(uuid.uuid4()), name="Rick")

    def bind(self, app: Application) -> None:
        app.add_routes([web.post("/character", self.create)])
