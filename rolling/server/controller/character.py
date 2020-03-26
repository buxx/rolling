#  coding: utf-8
import datetime
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
from rolling.action.base import WithBuildAction
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.exception import CantMoveCharacter
from rolling.exception import ImpossibleAction
from rolling.exception import NotEnoughActionPoints
from rolling.kernel import Kernel
from rolling.model.character import CharacterActionModel
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.character import DescribeStoryQueryModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import GetLookResourceModelModel
from rolling.model.character import GetLookStuffModelModel
from rolling.model.character import GetMoveZoneInfosModel
from rolling.model.character import ListOfStrModel
from rolling.model.character import MoveCharacterQueryModel
from rolling.model.character import PostTakeStuffModelModel
from rolling.model.character import WithBuildActionModel
from rolling.model.character import WithResourceActionModel
from rolling.model.character import WithStuffActionModel
from rolling.model.event import CharacterEnterZoneData
from rolling.model.event import CharacterExitZoneData
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.model.stuff import CharacterInventoryModel
from rolling.model.zone import MoveZoneInfos
from rolling.model.zone import ZoneRequiredPlayerData
from rolling.server.action import ActionFactory
from rolling.server.controller.base import BaseController
from rolling.server.controller.url import CHARACTER_ACTION
from rolling.server.controller.url import DESCRIBE_INVENTORY_RESOURCE_ACTION
from rolling.server.controller.url import DESCRIBE_INVENTORY_STUFF_ACTION
from rolling.server.controller.url import DESCRIBE_LOOT_AT_STUFF_URL
from rolling.server.controller.url import POST_CHARACTER_URL
from rolling.server.controller.url import TAKE_STUFF_URL
from rolling.server.controller.url import WITH_BUILD_ACTION
from rolling.server.controller.url import WITH_RESOURCE_ACTION
from rolling.server.controller.url import WITH_STUFF_ACTION
from rolling.server.effect import EffectManager
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.util import EmptyModel
from rolling.util import character_can_drink_in_its_zone
from rolling.util import display_g_or_kg
from rolling.util import get_character_stuff_filled_with_water
from rolling.util import get_description_for_not_enough_ap


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
                    form_action="/_describe/character/create/do",
                    items=[*Part.from_dataclass_fields(CreateCharacterModel)]
                    + [Part(go_back_zone=True)],
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
            title="Fiche de personnage",
            items=[
                Part(text="Personnage"),
                Part(text="------------"),
                Part(label="Nom", text=character.name),
                Part(
                    label="Points d'actions restants", text=f"{str(character.action_points)}/24.0"
                ),
                Part(
                    label="Points de vie",
                    text=f"{str(character.life_points)}/{str(character.max_life_comp)}",
                ),
                Part(label="Soif", text="oui" if character.feel_thirsty else "non"),
                Part(label="Faim", text="oui" if character.feel_hungry else "non"),
                Part(text="Compétences"),
                Part(text="------------"),
                Part(label="Chasse et ceuillete", text=str(character.hunting_and_collecting_comp)),
                Part(label="Trouver de l'eau", text=str(character.find_water_comp)),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_inventory(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(hapic_data.path.character_id)
        stuff_items: typing.List[Part] = []
        resource_items: typing.List[Part] = []
        bags = self._character_lib.get_used_bags(hapic_data.path.character_id)
        bags_string = "Aucun" if not bags else ", ".join([bag.name for bag in bags])

        for stuff in inventory.stuff:
            name = stuff.get_name()
            descriptions: typing.List[str] = stuff.get_full_description()

            description = ""
            if descriptions:
                description = " (" + ", ".join(descriptions) + ")"

            stuff_items.append(
                Part(
                    text=f"{name}{description}",
                    is_link=True,
                    align="left",
                    form_action=DESCRIBE_INVENTORY_STUFF_ACTION.format(
                        character_id=hapic_data.path.character_id, stuff_id=stuff.id
                    ),
                )
            )

        for resource in inventory.resource:
            resource_items.append(
                Part(
                    text=f"{resource.get_full_description(self._kernel)}",
                    is_link=True,
                    align="left",
                    form_action=DESCRIBE_INVENTORY_RESOURCE_ACTION.format(
                        character_id=hapic_data.path.character_id, resource_id=resource.id
                    ),
                )
            )

        max_weight = character.get_weight_capacity(self._kernel)
        max_clutter = character.get_clutter_capacity(self._kernel)

        weight_overcharge = ""
        clutter_overcharge = ""

        if inventory.weight > character.get_weight_capacity(self._kernel):
            weight_overcharge = " surcharge!"

        if inventory.clutter > character.get_clutter_capacity(self._kernel):
            clutter_overcharge = " surcharge!"

        weight_str = display_g_or_kg(inventory.weight)
        max_weight_str = display_g_or_kg(max_weight)
        return Description(
            title="Inventory",
            items=[
                Part(
                    text=f"Poids transporté: {weight_str} ({max_weight_str} max{weight_overcharge})"
                ),
                Part(
                    text=f"Encombrement: {round(inventory.clutter, 2)} ({round(max_clutter, 2)} max{clutter_overcharge})"
                ),
                Part(text=f"Sac(s): {bags_string}"),
                Part(text=" "),
                Part(text="Items:"),
                *stuff_items,
                Part(text=" "),
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
        character_actions = self._character_lib.get_on_place_actions(hapic_data.path.character_id)

        return Description(
            title="Ici, vous pouvez:",
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in character_actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_build_actions(self, request: Request, hapic_data: HapicData) -> Description:
        build_actions = self._character_lib.get_build_actions(hapic_data.path.character_id)

        return Description(
            title="Ici pouvez démarrer la construction de:",
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in build_actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_events(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get_document(hapic_data.path.character_id)
        character_events = self._character_lib.get_last_events(
            hapic_data.path.character_id, count=100
        )
        parts = []
        for event in character_events:
            there_is_story = bool(self._kernel.character_lib.count_story_pages(event.id))
            unread = "*" if event.unread else ""

            form_action = None
            if there_is_story:
                form_action = (
                    f"/_describe/character/{character.id}/story?event_id={event.id}&mark_read=1"
                )

            parts.append(
                Part(
                    text=f"Tour {event.turn}{unread}: {event.text}",
                    is_link=there_is_story,
                    form_action=form_action,
                )
            )

        return Description(title="Histoire", is_long_text=True, items=parts)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(DescribeStoryQueryModel)
    @hapic.output_body(Description)
    async def _describe_story(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get_document(hapic_data.path.character_id)
        event = self._kernel.character_lib.get_event(hapic_data.query.event_id)
        if not hapic_data.query.story_page_id:
            story_page = self._kernel.character_lib.get_first_story_page(hapic_data.query.event_id)
        else:
            story_page = self._kernel.character_lib.get_story_page(hapic_data.query.story_page_id)

        items = []
        if story_page.previous_page_id:
            items.append(
                Part(
                    label="Page précédente",
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/story"
                    f"?event_id={event.id}&story_page_id={story_page.previous_page_id}",
                )
            )

        items.append(Part(text=story_page.text))

        if story_page.next_page_id:
            items.append(
                Part(
                    label="Page suivante",
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/story"
                    f"?event_id={event.id}&story_page_id={story_page.next_page_id}",
                )
            )

        if hapic_data.query.mark_read:
            event.read = True
            self._kernel.server_db_session.add(event)
            self._kernel.server_db_session.commit()

        return Description(
            title=event.text,
            image_id=story_page.image_id,
            image_extension=story_page.image_extension,
            is_long_text=True,
            items=items,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookStuffModelModel)
    @hapic.output_body(Description)
    async def _describe_look_stuff(self, request: Request, hapic_data: HapicData) -> Description:
        stuff = self._stuff_lib.get_stuff(hapic_data.path.stuff_id)
        actions = self._character_lib.get_on_stuff_actions(
            character_id=hapic_data.path.character_id, stuff_id=hapic_data.path.stuff_id
        )
        return Description(
            title=stuff.get_name_and_light_description(),
            image=stuff.image,
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
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
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookResourceModelModel)
    @hapic.output_body(Description)
    async def _describe_inventory_look_resource(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        resource_description = self._kernel.game.config.resources[hapic_data.path.resource_id]
        actions = self._character_lib.get_on_resource_actions(
            character_id=hapic_data.path.character_id, resource_id=hapic_data.path.resource_id
        )
        return Description(
            title=resource_description.name,  # TODO BS 2019-09-05: add quantity in name
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in actions
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(CharacterActionModel)
    @hapic.output_body(Description)
    async def character_action(self, request: Request, hapic_data: HapicData) -> Description:
        action_type = hapic_data.path.action_type
        action_description_id = hapic_data.path.action_description_id
        action = typing.cast(
            CharacterAction, self._action_factory.create_action(action_type, action_description_id)
        )
        input_ = serpyco.Serializer(action.input_model).load(dict(request.query))  # TODO perf
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)

        cost = action.get_cost(character_model, input_=input_)
        if cost is not None and character_model.action_points < cost:
            return Description(
                title="Action impossible",
                items=[
                    Part(
                        text=f"{character_model.name} ne possède plus assez de points d'actions "
                        f"({character_model.action_points} restant et {cost} nécessaires)"
                    ),
                    Part(label="Continue", go_back_zone=True),
                ],
            )

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
    async def with_stuff_action(self, request: Request, hapic_data: HapicData) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithStuffAction,
            self._action_factory.create_action(
                action_type, action_description_id=hapic_data.path.action_description_id
            ),
        )
        input_ = serpyco.Serializer(action.input_model).load(dict(request.query))  # TODO perf
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)
        # TODO BS 2019-07-04: Check character owning ...
        stuff = self._kernel.stuff_lib.get_stuff(hapic_data.path.stuff_id)

        cost = action.get_cost(character_model, stuff, input_=input_)
        if cost is not None and character_model.action_points < cost:
            return Description(
                title="Action impossible",
                items=[
                    Part(
                        text=f"{character_model.name} ne possède plus assez de points d'actions "
                        f"({character_model.action_points} restant et {cost} nécessaires)"
                    ),
                    Part(label="Continue", go_back_zone=True),
                ],
            )

        try:
            action.check_request_is_possible(character=character_model, stuff=stuff, input_=input_)
        except ImpossibleAction as exc:
            return Description(
                title="Action impossible",
                items=[Part(text=str(exc)), Part(label="Continue", go_back_zone=True)],
            )

        return action.perform(character=character_model, stuff=stuff, input_=input_)

    @hapic.with_api_doc()
    @hapic.input_path(WithBuildActionModel)
    @hapic.output_body(Description)
    async def with_build_action(self, request: Request, hapic_data: HapicData) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithBuildAction,
            self._action_factory.create_action(
                action_type, action_description_id=hapic_data.path.action_description_id
            ),
        )
        input_ = action.input_model_serializer.load(dict(request.query))
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)
        # TODO BS 2019-07-04: Check character can action on build...

        cost = action.get_cost(character_model, hapic_data.path.build_id, input_=input_)
        if cost is not None and character_model.action_points < cost:
            return get_description_for_not_enough_ap(character_model, cost)

        try:
            action.check_request_is_possible(
                character=character_model, build_id=hapic_data.path.build_id, input_=input_
            )
        except NotEnoughActionPoints as exc:
            return get_description_for_not_enough_ap(character_model, exc.cost)
        except ImpossibleAction as exc:
            return Description(
                title="Action impossible",
                items=[Part(text=str(exc)), Part(label="Continue", go_back_zone=True)],
            )

        # FIXME BS 2019-10-03: check_request_is_possible must be done everywhere
        #  in perform like in this action !
        try:
            return action.perform(
                character=character_model, build_id=hapic_data.path.build_id, input_=input_
            )
        except ImpossibleAction as exc:
            return Description(
                title="Action impossible",
                items=[Part(text=str(exc)), Part(label="Continue", go_back_zone=True)],
            )

    @hapic.with_api_doc()
    @hapic.input_path(WithResourceActionModel)
    @hapic.output_body(Description)
    async def with_resource_action(self, request: Request, hapic_data: HapicData) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithResourceAction,
            self._action_factory.create_action(
                action_type, action_description_id=hapic_data.path.action_description_id
            ),
        )
        input_ = action.input_model_serializer.load(dict(request.query))
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)

        cost = action.get_cost(character_model, hapic_data.path.resource_id, input_=input_)
        if cost is not None and character_model.action_points < cost:
            return Description(
                title="Action impossible",
                items=[
                    Part(
                        text=f"{character_model.name} ne possède plus assez de points d'actions "
                        f"({character_model.action_points} restant et {cost} nécessaires)"
                    ),
                    Part(label="Continue", go_back_zone=True),
                ],
            )

        try:
            action.check_request_is_possible(
                character=character_model, resource_id=hapic_data.path.resource_id, input_=input_
            )
        except ImpossibleAction as exc:
            return Description(
                title="Action impossible",
                items=[Part(text=str(exc)), Part(label="Continue", go_back_zone=True)],
            )

        return action.perform(
            character=character_model, resource_id=hapic_data.path.resource_id, input_=input_
        )

    @hapic.with_api_doc()
    @hapic.input_body(CreateCharacterModel)
    @hapic.output_body(CharacterModel, default_http_code=201)
    async def create(self, request: Request, hapic_data: HapicData) -> CharacterModel:
        character_id = self._character_lib.create(hapic_data.body)
        return self._character_lib.get(character_id)

    @hapic.with_api_doc()
    @hapic.input_body(CreateCharacterModel)
    @hapic.output_body(Description)
    async def create_from_description(self, request: Request, hapic_data: HapicData) -> Description:
        character_id = self._character_lib.create(hapic_data.body)
        character_doc = self._kernel.character_lib.get_document(character_id)
        await self._kernel.send_to_zone_sockets(
            character_doc.world_row_i,
            character_doc.world_col_i,
            event=ZoneEvent(
                type=ZoneEventType.CHARACTER_ENTER_ZONE,
                data=CharacterEnterZoneData(
                    character_id=character_id,
                    zone_row_i=character_doc.zone_row_i,
                    zone_col_i=character_doc.zone_col_i,
                ),
            ),
        )
        return Description(
            title="Pret a commencer l'aventure !",
            items=[Part(label="Continuer", go_back_zone=True)],
            new_character_id=character_id,
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(CharacterModel)
    async def get(self, request: Request, hapic_data: HapicData) -> CharacterModel:
        return self._character_lib.get(hapic_data.path.character_id, compute_unread_event=True)

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.input_path(GetMoveZoneInfosModel)
    @hapic.output_body(MoveZoneInfos)
    async def get_move_to_zone_infos(
        self, request: Request, hapic_data: HapicData
    ) -> MoveZoneInfos:
        return self._character_lib.get_move_to_zone_infos(
            hapic_data.path.character_id,
            world_row_i=hapic_data.path.world_row_i,
            world_col_i=hapic_data.path.world_col_i,
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.input_path(GetMoveZoneInfosModel)
    @hapic.output_body(Description)
    async def describe_move_to_zone_infos(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        move_info = self._character_lib.get_move_to_zone_infos(
            hapic_data.path.character_id,
            world_row_i=hapic_data.path.world_row_i,
            world_col_i=hapic_data.path.world_col_i,
        )

        buttons = [Part(label="Rester ici", go_back_zone=True)]
        travel_url = (
            f"/_describe/character/{hapic_data.path.character_id}/move"
            f"?to_world_row={hapic_data.path.world_row_i}"
            f"&to_world_col={hapic_data.path.world_col_i}"
        )
        if move_info.can_move:
            text = f"Le voyage que vous envisagez nécéssite {round(move_info.cost, 2)} PA"
            buttons.insert(
                0, Part(label="Effectuer le voyage", is_link=True, form_action=travel_url)
            )
        else:
            text = (
                f"Le voyage que vous envisagez nécéssite {round(move_info.cost, 2)} PA. "
                f"Il ne vous reste pas assez de PA pour l'effectuer."
            )

        return Description(title="Effectuer un voyage ...", items=[Part(text=text)] + buttons)

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(CharacterInventoryModel)
    async def get_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> CharacterInventoryModel:
        return self._character_lib.get_inventory(hapic_data.path.character_id)

    # FIXME BS: remove (and update tui client ?)
    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(MoveCharacterQueryModel)
    @hapic.handle_exception(CantMoveCharacter)
    @hapic.output_body(EmptyModel)
    async def move(self, request: Request, hapic_data: HapicData) -> Response:
        character = self._character_lib.get(hapic_data.path.character_id)
        to_world_row = hapic_data.query.to_world_row
        to_world_col = hapic_data.query.to_world_col
        move_to_zone_type = self._kernel.world_map_source.geography.rows[to_world_row][to_world_col]
        zone_properties = self._kernel.game.world_manager.get_zone_properties(move_to_zone_type)

        if zone_properties.move_cost > character.action_points:
            message = (
                f"Ce déplacement coute {zone_properties.move_cost} points d'action mais "
                f"{character.name} n'en possède que {character.action_points}"
            )
            return web.json_response({"message": message}, status=400)

        await self._kernel.send_to_zone_sockets(
            character.world_row_i,
            character.world_col_i,
            event=ZoneEvent(
                type=ZoneEventType.CHARACTER_EXIT_ZONE,
                data=CharacterExitZoneData(character_id=hapic_data.path.character_id),
            ),
        )
        character_doc = self._character_lib.move(
            character,
            to_world_row=hapic_data.query.to_world_row,
            to_world_col=hapic_data.query.to_world_col,
        )
        await self._kernel.send_to_zone_sockets(
            hapic_data.query.to_world_row,
            hapic_data.query.to_world_col,
            event=ZoneEvent(
                type=ZoneEventType.CHARACTER_ENTER_ZONE,
                data=CharacterEnterZoneData(
                    character_id=hapic_data.path.character_id,
                    zone_row_i=character_doc.zone_row_i,
                    zone_col_i=character_doc.zone_col_i,
                ),
            ),
        )
        self._character_lib.reduce_action_points(character.id, zone_properties.move_cost)
        return Response(status=204)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(MoveCharacterQueryModel)
    @hapic.handle_exception(CantMoveCharacter)
    @hapic.output_body(Description)
    async def describe_move(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._character_lib.get(hapic_data.path.character_id)
        to_world_row = hapic_data.query.to_world_row
        to_world_col = hapic_data.query.to_world_col
        move_to_zone_type = self._kernel.world_map_source.geography.rows[to_world_row][to_world_col]
        zone_properties = self._kernel.game.world_manager.get_zone_properties(move_to_zone_type)

        if zone_properties.move_cost > character.action_points:
            message = (
                f"Ce déplacement coute {zone_properties.move_cost} points d'action mais "
                f"{character.name} n'en possède que {character.action_points}"
            )
        else:
            message = "Le voyage c'est bien déroulé"

        await self._kernel.send_to_zone_sockets(
            character.world_row_i,
            character.world_col_i,
            event=ZoneEvent(
                type=ZoneEventType.CHARACTER_EXIT_ZONE,
                data=CharacterExitZoneData(character_id=hapic_data.path.character_id),
            ),
        )
        character_doc = self._character_lib.move(
            character,
            to_world_row=hapic_data.query.to_world_row,
            to_world_col=hapic_data.query.to_world_col,
        )
        await self._kernel.send_to_zone_sockets(
            hapic_data.query.to_world_row,
            hapic_data.query.to_world_col,
            event=ZoneEvent(
                type=ZoneEventType.CHARACTER_ENTER_ZONE,
                data=CharacterEnterZoneData(
                    character_id=hapic_data.path.character_id,
                    zone_row_i=character_doc.zone_row_i,
                    zone_col_i=character_doc.zone_col_i,
                ),
            ),
        )
        self._character_lib.reduce_action_points(character.id, zone_properties.move_cost)

        return Description(
            title="Effectuer un voyage ...", items=[Part(text=message), Part(go_back_zone=True)]
        )

    @hapic.with_api_doc()
    @hapic.input_path(PostTakeStuffModelModel)
    @hapic.output_body(Description)
    async def take_stuff(self, request: Request, hapic_data: HapicData) -> Description:
        self._character_lib.take_stuff(
            character_id=hapic_data.path.character_id, stuff_id=hapic_data.path.stuff_id
        )
        return Description(title="Objet récupéré", items=[Part(go_back_zone=True)])

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(ZoneRequiredPlayerData)
    async def get_zone_data(
        self, request: Request, hapic_data: HapicData
    ) -> ZoneRequiredPlayerData:
        character = self._character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(hapic_data.path.character_id)

        return ZoneRequiredPlayerData(
            weight_overcharge=inventory.weight > character.get_weight_capacity(self._kernel),
            clutter_overcharge=inventory.clutter > character.get_clutter_capacity(self._kernel),
        )

    def _get_next_turn_str_value(self) -> str:
        last_state = self._kernel.universe_lib.get_last_state()
        last_turn_since = datetime.datetime.utcnow() - last_state.turned_at
        next_turn_in_seconds = self._kernel.game.config.day_turn_every - last_turn_since.seconds
        m, s = divmod(next_turn_in_seconds, 60)
        h, m = divmod(m, 60)
        return f"{h}h{m}m"

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(ListOfStrModel)
    async def get_resume_texts(self, request: Request, hapic_data: HapicData) -> ListOfStrModel:
        character = self._character_lib.get(hapic_data.path.character_id)

        hungry = "oui" if character.feel_hungry else "non"
        thirsty = "oui" if character.feel_thirsty else "non"
        next_turn_in_str = self._get_next_turn_str_value()

        can_drink_str = "Non"
        if character_can_drink_in_its_zone(
            self._kernel, character
        ) or get_character_stuff_filled_with_water(self._kernel, character.id):
            can_drink_str = "Oui"

        return ListOfStrModel(
            [
                (f"PV: {round(character.life_points, 1)}", None),
                (f"PA: {round(character.action_points, 1)}", f"/character/{character.id}/AP"),
                (f"Faim: {hungry}", None),
                (f"Soif: {thirsty}", None),
                ("", None),
                (f"Passage: {next_turn_in_str}", f"/character/{character.id}/turn"),
                (f"De quoi boire: {can_drink_str}", None),
            ]
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.handle_exception(NoResultFound, http_code=404)
    async def is_dead(self, request: Request, hapic_data: HapicData) -> Response:
        character_doc = self._kernel.character_lib.get_document(
            hapic_data.path.character_id, dead=True
        )
        return Response(body="0" if character_doc.alive else "1")

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def get_post_mortem(self, request: Request, hapic_data: HapicData) -> Description:
        character_doc = self._kernel.character_lib.get_document(
            hapic_data.path.character_id, dead=True
        )
        return Description(
            title=f"{character_doc.name} est mort",
            items=[
                Part(
                    label="Voir les évènements",
                    form_action=f"/_describe/character/{hapic_data.path.character_id}/events",
                    is_link=True,
                ),
                Part(
                    label="Créer un nouveau personnage",
                    form_action="/_describe/character/create",
                    is_link=True,
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def describe_ap(self, request: Request, hapic_data: HapicData) -> Description:
        character_doc = self._kernel.character_lib.get_document(hapic_data.path.character_id)
        return Description(
            title=f"Points d'actions (PA) disponibles",
            items=[
                Part(
                    text=f"Pour ce tour-ci, il reste {round(character_doc.action_points, 2)} "
                    f"points d'action à {character_doc.name}."
                ),
                Part(
                    text="Qu'est-ce que sont les PA ? Les points d'actions, c'est un certain "
                    "nombre d'unité de temps dont dispose votre personnage pour effectuer"
                    "ses actions d'ici le prochain passage de tour. Les économiser revient à "
                    "rester oisif. Ce qui n'est pas dénué d'intêrret pour le moral de votre "
                    "personnage !"
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def describe_ap(self, request: Request, hapic_data: HapicData) -> Description:
        character_doc = self._kernel.character_lib.get_document(hapic_data.path.character_id)
        return Description(
            title=f"Points d'actions (PA) disponibles",
            items=[
                Part(
                    text=f"Pour ce tour-ci, il reste {round(character_doc.action_points, 2)} "
                    f"points d'action à {character_doc.name}."
                ),
                Part(
                    text="Qu'est-ce que sont les PA ? Les points d'actions, c'est un certain "
                    "nombre d'unité de temps dont dispose votre personnage pour effectuer "
                    "ses actions d'ici le prochain passage de tour. Les économiser revient à "
                    "rester oisif. Ce qui n'est pas dénué d'intêrret pour le moral de votre "
                    "personnage !"
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def describe_turn(self, request: Request, hapic_data: HapicData) -> Description:
        next_turn_in_str = self._get_next_turn_str_value()
        return Description(
            title=f"Passage de tour",
            items=[
                Part(
                    text=f"Dans exactement {next_turn_in_str}, le passage de tour sera effectué. "
                    f"Cela signifie que le temps passe dans le jeu: l'herbe pousse, "
                    f"l'eau coule, les feux s'éteignent s'il n'ont plus de bois à bruler ... "
                    f"Mais cela signifie aussi que les personnages perdent des points de vie "
                    f"s'il n'ont pas a boire ou a manger par exemple !"
                )
            ],
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/_describe/character/create", self._describe_create_character),
                web.post("/_describe/character/create", self._describe_create_character),
                web.get("/_describe/character/{character_id}/card", self._describe_character_card),
                web.post("/_describe/character/{character_id}/card", self._describe_character_card),
                web.get("/_describe/character/{character_id}/inventory", self._describe_inventory),
                web.post("/_describe/character/{character_id}/inventory", self._describe_inventory),
                web.get(
                    "/_describe/character/{character_id}/on_place_actions",
                    self._describe_on_place_actions,
                ),
                web.post(
                    "/_describe/character/{character_id}/on_place_actions",
                    self._describe_on_place_actions,
                ),
                web.get(
                    "/character/{character_id}/move-to-zone/{world_row_i}/{world_col_i}",
                    self.get_move_to_zone_infos,
                ),
                web.post(
                    "/_describe/character/{character_id}/move-to-zone/{world_row_i}/{world_col_i}",
                    self.describe_move_to_zone_infos,
                ),
                web.get(
                    "/_describe/character/{character_id}/build_actions",
                    self._describe_build_actions,
                ),
                web.post(
                    "/_describe/character/{character_id}/build_actions",
                    self._describe_build_actions,
                ),
                web.get("/_describe/character/{character_id}/events", self._describe_events),
                web.post("/_describe/character/{character_id}/events", self._describe_events),
                web.post("/_describe/character/{character_id}/story", self._describe_story),
                web.post(POST_CHARACTER_URL, self.create),
                web.post("/_describe/character/create/do", self.create_from_description),
                web.get("/character/{character_id}", self.get),
                web.get("/_describe/character/{character_id}/inventory", self._describe_inventory),
                web.put("/character/{character_id}/move", self.move),
                web.post("/_describe/character/{character_id}/move", self.describe_move),
                web.post(TAKE_STUFF_URL, self.take_stuff),
                web.post(DESCRIBE_LOOT_AT_STUFF_URL, self._describe_look_stuff),
                web.post(DESCRIBE_INVENTORY_STUFF_ACTION, self._describe_inventory_look_stuff),
                web.post(
                    DESCRIBE_INVENTORY_RESOURCE_ACTION, self._describe_inventory_look_resource
                ),
                web.post(CHARACTER_ACTION, self.character_action),
                web.post(WITH_STUFF_ACTION, self.with_stuff_action),
                web.post(WITH_BUILD_ACTION, self.with_build_action),
                web.post(WITH_RESOURCE_ACTION, self.with_resource_action),
                web.get("/character/{character_id}/zone_data", self.get_zone_data),
                web.get("/character/{character_id}/resume_texts", self.get_resume_texts),
                web.get("/character/{character_id}/dead", self.is_dead),
                web.post("/character/{character_id}/post_mortem", self.get_post_mortem),
                web.post("/character/{character_id}/AP", self.describe_ap),
                web.post("/character/{character_id}/turn", self.describe_turn),
            ]
        )
