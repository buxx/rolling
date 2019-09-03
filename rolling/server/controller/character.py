#  coding: utf-8
import typing

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from hapic import HapicData
import serpyco
from sqlalchemy.orm.exc import NoResultFound

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import CharacterAction
from rolling.action.base import WithStuffAction
from rolling.exception import CantMoveCharacter
from rolling.exception import ImpossibleAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterActionModel
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import GetLookStuffModelModel
from rolling.model.character import MoveCharacterQueryModel
from rolling.model.character import PostTakeStuffModelModel
from rolling.model.character import WithStuffActionModel
from rolling.model.stuff import CharacterInventoryModel
from rolling.model.zone import ZoneRequiredPlayerData
from rolling.server.action import ActionFactory
from rolling.server.controller.base import BaseController
from rolling.server.controller.url import CHARACTER_ACTION
from rolling.server.controller.url import DESCRIBE_INVENTORY_STUFF_ACTION
from rolling.server.controller.url import DESCRIBE_LOOT_AT_STUFF_URL
from rolling.server.controller.url import POST_CHARACTER_URL
from rolling.server.controller.url import TAKE_STUFF_URL
from rolling.server.controller.url import WITH_STUFF_ACTION
from rolling.server.effect import EffectManager
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.util import EmptyModel


class CharacterController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)
        self._character_lib = CharacterLib(self._kernel)
        self._stuff_lib = StuffLib(self._kernel)
        self._effect_manager = EffectManager(self._kernel)
        self._action_factory = ActionFactory(self._kernel)

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
                Part(label="Life", text=str(character.life_points)),
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
                Part(
                    label="Remaining action points", text=str(character.action_points)
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(hapic_data.path.character_id)
        stuff_items: typing.List[Part] = []
        resource_items: typing.List[Part] = []
        bags = self._character_lib.get_used_bags(hapic_data.path.character_id)
        bags_string = "Aucun" if not bags else ", ".join([bag.name for bag in bags])

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

        for resource in inventory.resource:
            resource_items.append(
                Part(
                    text=f"{resource.get_full_description(self._kernel)}",
                    # TODO BS 2019-09-02: actions
                    # is_link=True,
                    # form_action=DESCRIBE_INVENTORY_STUFF_ACTION.format(
                    #     character_id=hapic_data.path.character_id, stuff_id=stuff.id
                    # ),
                )
            )

        max_weight = character.get_weight_capacity(self._kernel)
        max_clutter = character.get_clutter_capacity(self._kernel)

        weight_overcharge = ""
        clutter_overcharge = ""

        if inventory.weight > character.get_weight_capacity(self._kernel):
            weight_overcharge = " !surcharge!"

        if inventory.clutter > character.get_clutter_capacity(self._kernel):
            clutter_overcharge = " !surcharge!"

        return Description(
            title="Inventory",
            items=[
                Part(text=f"Poids transporté: {inventory.weight}g ({max_weight} max{weight_overcharge})"),
                Part(text=f"Encombrement: {inventory.clutter} ({max_clutter} max{clutter_overcharge})"),
                Part(text=f"Sac(s): {bags_string}"),
                Part(text="Items:"),
                *stuff_items,
                Part(text="Resources:"),
                *resource_items,
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
                Part(text=action.get_as_str(), form_action=action.link, is_link=True)
                for action in character_actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_events(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character_events = self._character_lib.get_last_events(
            hapic_data.path.character_id, count=100
        )

        return Description(
            title="Events:",
            is_long_text=True,
            items=[
                Part(
                    text=event.datetime.strftime(f"%d %b %Y at %H:%M:%S : {event.text}")
                )
                for event in character_events
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
                Part(text=action.get_as_str(), form_action=action.link, is_link=True)
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
                Part(text=action.get_as_str(), form_action=action.link, is_link=True)
                for action in actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(CharacterActionModel)
    @hapic.output_body(Description)
    async def character_action(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        action_type = hapic_data.path.action_type
        action_description_id = hapic_data.path.action_description_id
        action = typing.cast(
            CharacterAction,
            self._action_factory.create_action(action_type, action_description_id),
        )
        input_ = serpyco.Serializer(action.input_model).load(
            dict(request.query)
        )  # TODO perf
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)

        try:
            action.check_request_is_possible(character_model, input_)
        except ImpossibleAction as exc:
            return Description(
                title="Action impossible",
                items=[Part(text=str(exc)), Part(label="Continue", go_back_zone=True)],
            )

        return action.perform(character_model, input_)

    @hapic.with_api_doc()
    @hapic.input_path(WithStuffActionModel)
    @hapic.output_body(Description)
    async def with_stuff_action(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithStuffAction,
            self._action_factory.create_action(action_type, action_description_id=None),
        )
        input_ = serpyco.Serializer(action.input_model).load(
            dict(request.query)
        )  # TODO perf
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)
        # TODO BS 2019-07-04: Check character owning ...
        stuff = self._kernel.stuff_lib.get_stuff(hapic_data.path.stuff_id)

        try:
            action.check_request_is_possible(
                character=character_model, stuff=stuff, input_=input_
            )
        except ImpossibleAction as exc:
            return Description(
                title="Action impossible",
                items=[Part(text=str(exc)), Part(label="Continue", go_back_zone=True)],
            )

        return action.perform(character=character_model, stuff=stuff, input_=input_)

    @hapic.with_api_doc()
    @hapic.input_body(CreateCharacterModel)
    @hapic.output_body(CharacterModel, default_http_code=201)
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

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(ZoneRequiredPlayerData)
    async def get_zone_data(self, request: Request, hapic_data: HapicData) -> ZoneRequiredPlayerData:
        character = self._character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(hapic_data.path.character_id)

        return ZoneRequiredPlayerData(
            weight_overcharge=inventory.weight > character.get_weight_capacity(self._kernel),
            clutter_overcharge=inventory.clutter > character.get_clutter_capacity(self._kernel),
        )

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
                web.get(
                    "/_describe/character/{character_id}/events", self._describe_events
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
                web.post(CHARACTER_ACTION, self.character_action),
                web.post(WITH_STUFF_ACTION, self.with_stuff_action),
                web.get("/character/{character_id}/zone_data", self.get_zone_data)
            ]
        )
