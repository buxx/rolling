#  coding: utf-8
import typing

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from hapic import HapicData
from sqlalchemy.orm.exc import NoResultFound

from guilang.description import Description
from guilang.description import Part
from rolling.exception import CantEmpty
from rolling.exception import CantFill
from rolling.exception import CantMoveCharacter
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.character import DrinkMaterialModel
from rolling.model.character import EmptyStuffModel
from rolling.model.character import FillStuffWithModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import GetLookStuffModelModel
from rolling.model.character import MoveCharacterQueryModel
from rolling.model.character import PostTakeStuffModelModel
from rolling.model.stuff import CharacterInventoryModel
from rolling.server.controller.base import BaseController
from rolling.server.controller.url import DESCRIBE_DRINK_RESOURCE
from rolling.server.controller.url import DESCRIBE_EMPTY_STUFF
from rolling.server.controller.url import DESCRIBE_INVENTORY_STUFF_ACTION
from rolling.server.controller.url import DESCRIBE_LOOT_AT_STUFF_URL
from rolling.server.controller.url import DESCRIBE_STUFF_FILL_WITH_RESOURCE
from rolling.server.controller.url import POST_CHARACTER_URL
from rolling.server.controller.url import TAKE_STUFF_URL
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.util import EmptyModel


class CharacterController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)
        self._character_lib = CharacterLib(self._kernel)
        self._stuff_lib = StuffLib(self._kernel)

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
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_character_card(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._character_lib.get(hapic_data.path.character_id)
        return Description(
            title="Character card",
            items=[
                Part(text="This is your character card"),
                Part(text="------------"),
                Part(label="Name", text=character.name),
                Part(label="Max life", text=str(character.max_life_comp)),
                Part(
                    label="Hunting and collecting",
                    text=str(character.hunting_and_collecting_comp),
                ),
                Part(label="Find water", text=str(character.find_water_comp)),
                Part(
                    label="Feeling thirsty",
                    text="yes" if character.feel_thirsty else "no",
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        inventory = self._character_lib.get_inventory(hapic_data.path.character_id)
        stuff_items: typing.List[Part] = []

        for stuff in inventory.stuff:
            name = stuff.name
            descriptions: typing.List[str] = stuff.get_full_description()

            description = ""
            if descriptions:
                description = " (" + ", ".join(descriptions) + ")"

            stuff_items.append(
                Part(
                    text=f"{name}{description}",
                    is_link=True,
                    form_action=DESCRIBE_INVENTORY_STUFF_ACTION.format(
                        character_id=hapic_data.path.character_id, stuff_id=stuff.id
                    ),
                )
            )

        return Description(
            title="Inventory",
            items=[
                Part(text=f"total weight: {inventory.weight}g"),
                Part(text=f"total clutter: {inventory.clutter}"),
                Part(text="Items:"),
                *stuff_items,
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_on_place_actions(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character_actions = self._character_lib.get_on_place_actions(
            hapic_data.path.character_id
        )

        return Description(
            title="Here, you can:",
            items=[
                Part(text=action.name, form_action=action.link, is_link=True)
                for action in character_actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookStuffModelModel)
    @hapic.output_body(Description)
    async def _describe_look_stuff(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        stuff = self._stuff_lib.get_stuff(hapic_data.path.stuff_id)
        actions = self._character_lib.get_on_stuff_actions(
            character_id=hapic_data.path.character_id, stuff_id=hapic_data.path.stuff_id
        )
        return Description(
            title=stuff.get_name_and_light_description(),
            image=stuff.image,
            items=[
                Part(text=action.name, form_action=action.link, is_link=True)
                for action in actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookStuffModelModel)
    @hapic.output_body(Description)
    async def _describe_inventory_look_stuff(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        stuff = self._stuff_lib.get_stuff(hapic_data.path.stuff_id)
        actions = self._character_lib.get_on_stuff_actions(
            character_id=hapic_data.path.character_id, stuff_id=hapic_data.path.stuff_id
        )
        return Description(
            title=stuff.get_name_and_light_description(),
            items=[
                Part(text=action.name, form_action=action.link, is_link=True)
                for action in actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(FillStuffWithModel)
    @hapic.output_body(Description)
    async def _describe_fill_stuff_with(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        # TODO BS 2019-07-04: Check stuff is carried (or have capacity to)
        # TODO BS 2019-07-04: Check filling is possible
        # (see rolling.game.world.WorldManager#get_resource_on_or_around)
        stuff = self._stuff_lib.get_stuff(hapic_data.path.stuff_id)
        resource_type = hapic_data.path.resource_type

        try:
            self._stuff_lib.fill_stuff_with_resource(stuff, resource_type)
        except CantFill as exc:
            return Description(
                title=str(exc), items=[Part(label="Go back", go_back_zone=True)]
            )

        return Description(
            title=f"{stuff.name} filled with {resource_type.value}",
            items=[Part(label="Continue", go_back_zone=True)],
        )

    @hapic.with_api_doc()
    @hapic.input_path(EmptyStuffModel)
    @hapic.output_body(Description)
    async def _describe_empty_stuff(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        # TODO BS 2019-07-04: Check stuff is carried (or have capacity to)
        stuff = self._stuff_lib.get_stuff(hapic_data.path.stuff_id)

        try:
            self._stuff_lib.empty_stuff(stuff)
        except CantEmpty as exc:
            return Description(
                title=str(exc), items=[Part(label="Go back", go_back_zone=True)]
            )

        return Description(
            title=f"Emptied {stuff.name}",
            items=[Part(label="Continue", go_back_zone=True)],
        )

    @hapic.with_api_doc()
    @hapic.input_path(DrinkMaterialModel)
    @hapic.output_body(Description)
    async def _describe_drink_material(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        # TODO BS 2019-07-04: Check if material is available
        message = self._character_lib.drink_material(
            hapic_data.path.character_id, hapic_data.path.resource_type
        )

        return Description(
            title=message, items=[Part(label="Continue", go_back_zone=True)]
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
        return self._character_lib.get(hapic_data.path.character_id)

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(CharacterInventoryModel)
    async def get_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> CharacterInventoryModel:
        return self._character_lib.get_inventory(hapic_data.path.character_id)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(MoveCharacterQueryModel)
    @hapic.handle_exception(CantMoveCharacter)
    @hapic.output_body(EmptyModel)
    async def move(self, request: Request, hapic_data: HapicData) -> Response:
        character = self._character_lib.get(hapic_data.path.character_id)
        self._character_lib.move(
            character,
            to_world_row=hapic_data.query.to_world_row,
            to_world_col=hapic_data.query.to_world_col,
        )
        return Response(status=204)

    @hapic.with_api_doc()
    @hapic.input_path(PostTakeStuffModelModel)
    @hapic.output_body(EmptyModel, default_http_code=204)
    async def take_stuff(self, request: Request, hapic_data: HapicData) -> Response:
        self._character_lib.take_stuff(
            character_id=hapic_data.path.character_id, stuff_id=hapic_data.path.stuff_id
        )
        return Response(status=204)

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/_describe/character/create", self._describe_create_character),
                web.get(
                    "/_describe/character/{character_id}/card",
                    self._describe_character_card,
                ),
                web.get(
                    "/_describe/character/{character_id}/inventory",
                    self._describe_inventory,
                ),
                web.get(
                    "/_describe/character/{character_id}/on_place_actions",
                    self._describe_on_place_actions,
                ),
                web.post(POST_CHARACTER_URL, self.create),
                web.get("/character/{character_id}", self.get),
                web.get(
                    "/_describe/character/{character_id}/inventory",
                    self._describe_inventory,
                ),
                web.put("/character/{character_id}/move", self.move),
                web.post(TAKE_STUFF_URL, self.take_stuff),
                web.post(DESCRIBE_LOOT_AT_STUFF_URL, self._describe_look_stuff),
                web.post(
                    DESCRIBE_INVENTORY_STUFF_ACTION, self._describe_inventory_look_stuff
                ),
                web.post(
                    DESCRIBE_STUFF_FILL_WITH_RESOURCE, self._describe_fill_stuff_with
                ),
                web.post(DESCRIBE_EMPTY_STUFF, self._describe_empty_stuff),
                web.post(DESCRIBE_DRINK_RESOURCE, self._describe_drink_material),
            ]
        )
