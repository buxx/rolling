#  coding: utf-8
import uuid

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from sqlalchemy.orm.exc import NoResultFound

from hapic import HapicData
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.character import GetCharacterPathModel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib


class CharacterController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)
        self._character_lib = CharacterLib(self._kernel)

    @hapic.with_api_doc()
    @hapic.input_body(CreateCharacterModel)
    @hapic.output_body(CharacterModel)
    async def create(self, request: Request, hapic_data: HapicData) -> CharacterModel:
        character_id = self._character_lib.create(hapic_data.body)
        return self._character_lib.get(character_id)

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(CharacterModel)
    async def get(self, request: Request, hapic_data: HapicData) -> CharacterModel:
        return self._character_lib.get(hapic_data.path.id)

    def bind(self, app: Application) -> None:
        app.add_routes(
            [web.post("/character", self.create), web.get("/character/{id}", self.get)]
        )
