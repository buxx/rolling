#  coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from sqlalchemy.orm.exc import NoResultFound

from guilang.description import Description
from guilang.description import Part
from hapic import HapicData
from rolling.exception import CantMoveCharacter
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import MoveCharacterQueryModel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib
from rolling.util import EmptyModel

POST_CHARACTER_URL = "/character"


class CharacterController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)
        self._character_lib = CharacterLib(self._kernel)

    @hapic.with_api_doc()
    @hapic.output_body(Description)
    async def _describe_create_character(self, request: Request) -> Description:
        return Description(
            title="Create your character",
            items=[
                Part(
                    text="It's your character who play this game. "
                    "Prepare a beautiful story for him"
                ),
                Part(
                    is_form=True,
                    form_action=POST_CHARACTER_URL,
                    items=[*Part.from_dataclass_fields(CreateCharacterModel)],
                ),
            ],
        )

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

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(MoveCharacterQueryModel)
    @hapic.handle_exception(CantMoveCharacter)
    @hapic.output_body(EmptyModel)
    async def move(self, request: Request, hapic_data: HapicData) -> Response:
        character = self._character_lib.get(hapic_data.path.id)
        self._character_lib.move(
            character,
            to_world_row=hapic_data.query.to_world_row,
            to_world_col=hapic_data.query.to_world_col,
        )
        return Response(status=204)

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/_describe/create_character", self._describe_create_character),
                web.post(POST_CHARACTER_URL, self.create),
                web.get("/character/{id}", self.get),
                web.put("/character/{id}/move", self.move),
            ]
        )
