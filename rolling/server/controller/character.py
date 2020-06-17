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
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import WithBuildAction
from rolling.action.base import WithCharacterAction
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.exception import CantMoveCharacter, UserDisplayError
from rolling.exception import ImpossibleAction
from rolling.exception import NotEnoughActionPoints
from rolling.kernel import Kernel
from rolling.model.character import CharacterActionModel
from rolling.model.character import CharacterModel
from rolling.model.character import DescribeStoryQueryModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import GetCharacterWithPathModel
from rolling.model.character import GetLookCharacterModel
from rolling.model.character import GetLookInventoryResourceModel
from rolling.model.character import GetLookResourceModel
from rolling.model.character import GetLookStuffModelModel
from rolling.model.character import GetMoveZoneInfosModel
from rolling.model.character import ListOfStrModel
from rolling.model.character import MoveCharacterQueryModel
from rolling.model.character import PickFromInventoryQueryModel
from rolling.model.character import PostTakeStuffModelModel
from rolling.model.character import TakeResourceModel
from rolling.model.character import UpdateCharacterCardBodyModel
from rolling.model.character import WithBuildActionModel
from rolling.model.character import WithCharacterActionModel
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
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_RESOURCE_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_STUFF_URL
from rolling.server.controller.url import TAKE_STUFF_URL
from rolling.server.controller.url import WITH_BUILD_ACTION
from rolling.server.controller.url import WITH_CHARACTER_ACTION
from rolling.server.controller.url import WITH_RESOURCE_ACTION
from rolling.server.controller.url import WITH_STUFF_ACTION
from rolling.server.effect import EffectManager
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.util import character_can_drink_in_its_zone
from rolling.util import clamp
from rolling.util import display_g_or_kg
from rolling.util import get_character_stuff_filled_with_water
from rolling.util import get_description_for_not_enough_ap
from rolling.util import quantity_to_str

base_skills = ["strength", "perception", "endurance", "charism", "intelligence", "agility", "luck"]


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
        maximum_points = self._kernel.game.config.create_character_max_points
        parts = [
            Part(
                text="Traits physionomiques"
            ),
        ]
        for skill_id in base_skills:
            skill_description = self._kernel.game.config.skills[skill_id]
            parts.append(
                Part(
                    label=skill_description.name,
                    type_=Type.NUMBER,
                    default_value=str(skill_description.default),
                    name=skill_id,
                )
            )

        parts.append(
            Part(
                text="Spécialisations",
            )
        )

        for skill_id in self._kernel.game.config.create_character_skills:
            skill_description = self._kernel.game.config.skills[skill_id]
            parts.append(
                Part(
                    label=skill_description.name,
                    type_=Type.NUMBER,
                    default_value=str(skill_description.default),
                    name=skill_id,
                )
            )

        return Description(
            title="Créer votre personnage",
            items=[
                Part(
                    text="C'est le moment de créer votre personnage. Ci-dessous, vous pouvez "
                         f"répartir jusqu'à {maximum_points} points de compétences."
                ),
                Part(
                    is_form=True,
                    form_action="/_describe/character/create/do",
                    items=[
                        Part(
                            label="Nom du personnage",
                            type_=Type.NUMBER,
                            name="name",
                        ),
                    ] + parts,
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_body(UpdateCharacterCardBodyModel)
    @hapic.output_body(Description)
    async def _describe_character_card(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._character_lib.get(hapic_data.path.character_id)
        doc = self._character_lib.get_document(character.id)

        if (
            hapic_data.body.attack_allowed_loss_rate is not None
            or hapic_data.body.defend_allowed_loss_rate is not None
        ):
            if hapic_data.body.attack_allowed_loss_rate is not None:
                input_ = int(hapic_data.body.attack_allowed_loss_rate)
                input_ = clamp(input_, 0, 100)
                doc.attack_allowed_loss_rate = input_
            if hapic_data.body.defend_allowed_loss_rate is not None:
                input_ = int(hapic_data.body.defend_allowed_loss_rate)
                input_ = clamp(input_, 0, 100)
                doc.defend_allowed_loss_rate = input_
            self._kernel.server_db_session.add(doc)
            self._kernel.server_db_session.commit()

        return Description(
            title="Fiche de personnage",
            can_be_back_url=True,
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
                Part(label="Fatigué", text="oui" if character.tired else "non"),
                Part(label="Exténué", text="oui" if character.exhausted else "non"),
                Part(
                    label="Arme",
                    text=character.weapon.name if character.weapon else "aucune",
                    is_link=True if character.weapon else False,
                    align="left",
                    form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=character.weapon.id
                    )
                    if character.weapon
                    else None,
                ),
                Part(
                    label="Bouclier",
                    text=character.shield.name if character.shield else "aucun",
                    is_link=True if character.shield else False,
                    align="left",
                    form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=character.weapon.id
                    )
                    if character.weapon
                    else None,
                ),
                Part(
                    label="Armure",
                    text=character.armor.name if character.armor else "aucune",
                    is_link=True if character.armor else False,
                    align="left",
                    form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=character.weapon.id
                    )
                    if character.weapon
                    else None,
                ),
                Part(text=""),
                Part(
                    is_form=True,
                    form_action=f"/_describe/character/{character.id}/card",
                    items=[
                        Part(
                            text="Si vous occupez la position de chef de guerre, vous pouvez "
                            "décider de la part de perte maximale dans vos rangs avant "
                            "d'ordonner le replis"
                        ),
                        Part(
                            label="Lorsque vous menez un assault (%)",
                            type_=Type.NUMBER,
                            name="attack_allowed_loss_rate",
                            default_value=str(doc.attack_allowed_loss_rate),
                        ),
                        Part(
                            label="Lorsque vous êtes attaqué (%)",
                            type_=Type.NUMBER,
                            name="defend_allowed_loss_rate",
                            default_value=str(doc.defend_allowed_loss_rate),
                        ),
                    ],
                ),
            ],
            footer_links=[
                Part(
                    is_link=True,
                    label="Caractéristiques et compétences",
                    form_action=f"/character/{character.id}/skills_and_knowledge",
                )
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def skills_and_knowledge(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO: check same zone
        character = self._character_lib.get(hapic_data.path.character_id)
        items = [Part(text="# CARACTERISTIQUES")]

        for skill_description in self._kernel.game.config.skills.values():
            skill_value = character.get_skill_value(skill_description.id)
            items.append(Part(text=f"{skill_description.name}: {skill_value}"))

        items.append(Part(text="# COMPETENCES"))

        for knowledge_description in self._kernel.game.config.knowledge.values():
            if character.have_knowledge(knowledge_description.id):
                items.append(Part(text=f"{knowledge_description.name}"))

        return Description(
            title=f"Caractéristiques et compétences de {character.name}",
            items=items,
            footer_links=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    label="Fiche personnage",
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/card",
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterWithPathModel)
    @hapic.output_body(Description)
    async def with_character_card(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO: check same zone
        character = self._character_lib.get(hapic_data.path.character_id)
        with_character = self._character_lib.get(hapic_data.path.with_character_id)
        return Description(
            title=f"Fiche de {with_character.name}",
            items=[Part(text="Personnage"), Part(text=f"Nom: {with_character.name}")],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_inventory(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(character.id)
        inventory_parts = self._get_inventory_parts(character, inventory)

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
            ]
            + inventory_parts,
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(PickFromInventoryQueryModel)
    @hapic.output_body(Description)
    async def pick_from_inventory(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(character.id)
        form_parts = []
        form_action = (
            f"/_describe/character/{character.id}/pick_from_inventory"
            f"?callback_url={hapic_data.query.callback_url}"
            f"&cancel_url={hapic_data.query.cancel_url}"
            f"&title={hapic_data.query.title}"
        )
        can_be_back_url = True

        if hapic_data.query.resource_id is None and hapic_data.query.stuff_id is None:
            stuff_displayed: typing.Dict[str, bool] = {s.stuff_id: False for s in inventory.stuff}
            for stuff in inventory.stuff:
                if stuff_displayed[stuff.stuff_id]:
                    continue

                form_parts.append(
                    Part(
                        label=stuff.get_name_and_light_description(self._kernel),
                        is_link=True,
                        form_action=form_action + f"&stuff_id={stuff.stuff_id}",
                    )
                )

            for resource in inventory.resource:
                form_parts.append(
                    Part(
                        label=resource.name,
                        text=f"{resource.get_full_description(self._kernel)}",
                        is_link=True,
                        form_action=form_action + f"&resource_id={resource.id}",
                    )
                )
        else:
            form_action = hapic_data.query.callback_url + (
                "?" if "?" not in hapic_data.query.callback_url else ""
            )
            can_be_back_url = False

            if hapic_data.query.resource_id is not None:
                form_action = f"{form_action}&resource_id={hapic_data.query.resource_id}"
                default_value = self._kernel.resource_lib.get_one_carried_by(
                    character.id, resource_id=hapic_data.query.resource_id
                ).quantity
                resource_description = self._kernel.game.config.resources[
                    hapic_data.query.resource_id
                ]
                unit_str = self._kernel.translation.get(resource_description.unit)
                quantity_prefix = "resource_"
            else:
                form_action = f"{form_action}&stuff_id={hapic_data.query.stuff_id}"
                default_value = self._kernel.stuff_lib.have_stuff_count(
                    character.id, stuff_id=hapic_data.query.stuff_id
                )
                unit_str = "unité"
                quantity_prefix = "stuff_"

            form_parts.append(
                Part(
                    label=f"Quantité ({unit_str}) ?",
                    name=f"{quantity_prefix}quantity",
                    type_=Type.NUMBER,
                    default_value=str(default_value),
                )
            )

        return Description(
            title=hapic_data.query.title or "Choisir depuis votre inventaire",
            items=[
                Part(
                    is_form=True,
                    form_action=form_action,
                    form_values_in_query=True,
                    items=form_parts,
                ),
                Part(label="Retour", is_link=True, form_action=hapic_data.query.cancel_url),
            ],
            can_be_back_url=can_be_back_url,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterWithPathModel)
    @hapic.output_body(Description)
    async def with_inventory(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO: check same zone
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        with_character = self._kernel.character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(with_character.id)
        inventory_parts = self._get_inventory_parts(with_character, inventory)

        return Description(title="Inventory", items=inventory_parts, can_be_back_url=True)

    def _get_inventory_parts(
        self, character: CharacterModel, inventory: CharacterInventoryModel
    ) -> typing.List[Part]:
        stuff_items: typing.List[Part] = []
        resource_items: typing.List[Part] = []
        bags = self._character_lib.get_used_bags(character.id)
        bags_string = "Aucun" if not bags else ", ".join([bag.name for bag in bags])
        stuff_count: typing.Dict[str, int] = {}

        for stuff in inventory.stuff:
            stuff_count.setdefault(stuff.stuff_id, 0)
            stuff_count[stuff.stuff_id] += 1

        stuff_displayed: typing.Dict[str, bool] = {s.stuff_id: False for s in inventory.stuff}
        for stuff in inventory.stuff:
            if stuff_displayed[stuff.stuff_id]:
                continue

            name = stuff.get_name()
            descriptions: typing.List[str] = stuff.get_full_description(self._kernel)

            description = ""
            if descriptions:
                description = " (" + ", ".join(descriptions) + ")"

            if stuff_count[stuff.stuff_id] > 1:
                text = f"{stuff_count[stuff.stuff_id]} {name}{description}"
            else:
                text = f"{name}{description}"
            stuff_items.append(
                Part(
                    text=text,
                    is_link=True,
                    align="left",
                    form_action=DESCRIBE_INVENTORY_STUFF_ACTION.format(
                        character_id=character.id, stuff_id=stuff.id
                    ),
                )
            )
            stuff_displayed[stuff.stuff_id] = True

        for resource in inventory.resource:
            resource_items.append(
                Part(
                    text=f"{resource.get_full_description(self._kernel)}",
                    is_link=True,
                    align="left",
                    form_action=DESCRIBE_INVENTORY_RESOURCE_ACTION.format(
                        character_id=character.id, resource_id=resource.id
                    ),
                )
            )

        return [
            Part(text=f"Sac(s): {bags_string}"),
            Part(text=" "),
            Part(text="Items:"),
            *stuff_items,
            Part(text=" "),
            Part(text="Resources:"),
            *resource_items,
        ]

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_on_place_actions(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character_actions = self._character_lib.get_on_place_actions(hapic_data.path.character_id)

        return Description(
            title="Que voulez-vous faire ?",
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in character_actions
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_build_actions(self, request: Request, hapic_data: HapicData) -> Description:
        build_actions = self._character_lib.get_build_actions(hapic_data.path.character_id)

        return Description(
            title="Démarrer une construction",
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in build_actions
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_events(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get_document(hapic_data.path.character_id, dead=None)
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

        return Description(title="Histoire", is_long_text=True, items=parts, can_be_back_url=True)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(DescribeStoryQueryModel)
    @hapic.output_body(Description)
    async def _describe_story(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get_document(hapic_data.path.character_id, dead=None)
        event = self._kernel.character_lib.get_event(hapic_data.query.event_id)
        if not hapic_data.query.story_page_id:
            story_page = self._kernel.character_lib.get_first_story_page(hapic_data.query.event_id)
        else:
            story_page = self._kernel.character_lib.get_story_page(hapic_data.query.story_page_id)

        items = []
        footer_links = []
        if story_page.previous_page_id:
            footer_links.append(
                Part(
                    label="Page précédente",
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/story"
                    f"?event_id={event.id}&story_page_id={story_page.previous_page_id}",
                )
            )

        items.append(Part(text=story_page.text))

        if story_page.next_page_id:
            footer_links.append(
                Part(
                    label="Page suivante",
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/story"
                    f"?event_id={event.id}&story_page_id={story_page.next_page_id}",
                )
            )

        footer_links.append(
            Part(
                label="Retour aux évènements",
                is_link=True,
                form_action=f"/_describe/character/{character.id}/events",
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
            footer_links=footer_links,
            can_be_back_url=True,
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
            title=stuff.get_name_and_light_description(self._kernel),
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
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookCharacterModel)
    @hapic.output_body(Description)
    async def _describe_look_character(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        # TODO BS: check is in same zone
        character = self._character_lib.get(hapic_data.path.character_id)
        with_character = self._character_lib.get(hapic_data.path.with_character_id)
        actions = self._character_lib.get_with_character_actions(
            character=character, with_character=with_character
        )
        return Description(
            title=with_character.name,
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in actions
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookResourceModel)
    @hapic.input_query(TakeResourceModel)
    @hapic.output_body(Description)
    async def _describe_look_resource(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        resource_description = self._kernel.game.config.resources[hapic_data.path.resource_id]
        ground_resources = self._kernel.resource_lib.get_ground_resource(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=hapic_data.path.row_i,
            zone_col_i=hapic_data.path.col_i,
        )
        ground_resource_ids = [r.id for r in ground_resources]
        if hapic_data.path.resource_id not in ground_resource_ids:
            return Description(
                title="Cette ressource n'est plus là", items=[Part(is_link=True, go_back_zone=True)]
            )
        ground_resource = next(r for r in ground_resources if r.id == hapic_data.path.resource_id)

        available_str = quantity_to_str(
            ground_resource.quantity, ground_resource.unit, self._kernel
        )
        unit_str = self._kernel.translation.get(ground_resource.unit)
        if not hapic_data.query.quantity:
            return Description(
                title=resource_description.name,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=DESCRIBE_LOOK_AT_RESOURCE_URL.format(
                            character_id=character.id,
                            resource_id=hapic_data.path.resource_id,
                            row_i=hapic_data.path.row_i,
                            col_i=hapic_data.path.col_i,
                        ),
                        items=[
                            Part(
                                label=f"Récupérer quelle quantité ({unit_str}, {available_str} disponible)?",
                                name="quantity",
                                type_=Type.NUMBER,
                                default_value=str(ground_resource.quantity),
                            )
                        ],
                    )
                ],
                can_be_back_url=True,
            )

        self._kernel.resource_lib.add_resource_to(
            character_id=character.id,
            resource_id=hapic_data.path.resource_id,
            quantity=hapic_data.query.quantity,
            commit=False,
        )
        self._kernel.resource_lib.reduce_on_ground(
            resource_id=hapic_data.path.resource_id,
            quantity=hapic_data.query.quantity,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=hapic_data.path.row_i,
            zone_col_i=hapic_data.path.col_i,
            commit=True,
        )

        return Description(
            title=f"{resource_description.name} récupéré",
            items=[Part(is_link=True, go_back_zone=True)],
            can_be_back_url=True,
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
            title=stuff.get_name_and_light_description(self._kernel),
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in actions
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookInventoryResourceModel)
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
            can_be_back_url=True,
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
                items=[Part(text=str(exc)), Part(label="Continuer", go_back_zone=True)],
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
                items=[Part(text=str(exc)), Part(label="Continuer", go_back_zone=True)],
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
                items=[Part(text=str(exc)), Part(label="Continuer", go_back_zone=True)],
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
                items=[Part(text=str(exc)), Part(label="Continuer", go_back_zone=True)],
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
                items=[Part(text=str(exc)), Part(label="Continuer", go_back_zone=True)],
            )

        return action.perform(
            character=character_model, resource_id=hapic_data.path.resource_id, input_=input_
        )

    @hapic.with_api_doc()
    @hapic.input_path(WithCharacterActionModel)
    @hapic.output_body(Description)
    async def with_character_action(self, request: Request, hapic_data: HapicData) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithCharacterAction,
            self._action_factory.create_action(
                action_type, action_description_id=hapic_data.path.action_description_id
            ),
        )
        input_ = action.input_model_serializer.load(dict(request.query))
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)
        with_character_model = self._kernel.character_lib.get(hapic_data.path.with_character_id)

        cost = action.get_cost(character_model, with_character_model, input_=input_)
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
                character=character_model, with_character=with_character_model, input_=input_
            )
        except ImpossibleAction as exc:
            return Description(
                title="Action impossible",
                items=[Part(text=str(exc)), Part(label="Continuer", go_back_zone=True)],
            )

        return action.perform(
            character=character_model, with_character=with_character_model, input_=input_
        )

    @hapic.with_api_doc()
    @hapic.output_body(Description)
    async def create_character_do(self, request: Request) -> Description:
        data = await request.json()
        skills: typing.Dict[str, float] = {}
        skills_total = 0.0

        for skill_id in base_skills + self._kernel.game.config.create_character_skills:
            value = float(data[skill_id])

            if value < 0.0:
                raise UserDisplayError("Valeur négative refusée")

            skills[skill_id] = value
            skills_total += value

        maximum_points = self._kernel.game.config.create_character_max_points
        if skills_total > maximum_points:
            raise UserDisplayError(
                f"Vous avez choisis {skills_total} points au total ({maximum_points} max)"
            )

        if len(data["name"]) < 3 or len(data["name"]) > 21:
            raise UserDisplayError(
                f"Le nom du personnage doit faire entre 3 et 21 caractères"
            )

        character_id = self._character_lib.create(data["name"], skills)
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
        return self._character_lib.get(
            hapic_data.path.character_id,
            compute_unread_event=True,
            compute_unread_zone_message=True,
            compute_unread_conversation=True,
            compute_unvote_affinity_relation=True,
            compute_unread_transactions=True,
        )

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
        parts = [
            Part(
                text=f"Le voyage que vous envisagez nécéssite {round(move_info.cost, 2)} Point d'Actions"
            )
        ]

        if move_info.can_move:
            buttons.insert(
                0, Part(label="Effectuer le voyage", is_link=True, form_action=travel_url)
            )
        else:
            for reason in move_info.cannot_move_reasons:
                parts.append(Part(text=reason))

        return Description(title="Effectuer un voyage ...", items=parts + buttons)

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
    @hapic.output_body(Description)
    async def describe_move(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._character_lib.get(hapic_data.path.character_id)
        to_world_row = hapic_data.query.to_world_row
        to_world_col = hapic_data.query.to_world_col
        move_to_zone_type = self._kernel.world_map_source.geography.rows[to_world_row][to_world_col]
        zone_properties = self._kernel.game.world_manager.get_zone_properties(move_to_zone_type)
        move_info = self._character_lib.get_move_to_zone_infos(
            hapic_data.path.character_id, world_row_i=to_world_row, world_col_i=to_world_col
        )

        if move_info.can_move:
            messages = ["Le voyage c'est bien déroulé"]
        else:
            messages = list(move_info.cannot_move_reasons)

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
            title="Effectuer un voyage ...",
            items=[Part(text=message) for message in messages] + [Part(go_back_zone=True)],
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
            can_be_back_url=True,
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
            can_be_back_url=True,
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
            can_be_back_url=True,
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/_describe/character/create", self._describe_create_character),
                web.post("/_describe/character/create", self._describe_create_character),
                web.get("/_describe/character/{character_id}/card", self._describe_character_card),
                web.post("/_describe/character/{character_id}/card", self._describe_character_card),
                web.post(
                    "/character/{character_id}/card/{with_character_id}", self.with_character_card
                ),
                web.get("/_describe/character/{character_id}/inventory", self._describe_inventory),
                web.post("/_describe/character/{character_id}/inventory", self._describe_inventory),
                web.post(
                    "/character/{character_id}/inventory/{with_character_id}", self.with_inventory
                ),
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
                web.post("/_describe/character/create/do", self.create_character_do),
                web.get("/character/{character_id}", self.get),
                web.get("/_describe/character/{character_id}/inventory", self._describe_inventory),
                web.post(
                    "/_describe/character/{character_id}/pick_from_inventory",
                    self.pick_from_inventory,
                ),
                web.post("/_describe/character/{character_id}/move", self.describe_move),
                web.post(TAKE_STUFF_URL, self.take_stuff),
                web.post(DESCRIBE_LOOK_AT_STUFF_URL, self._describe_look_stuff),
                web.post(DESCRIBE_LOOK_AT_RESOURCE_URL, self._describe_look_resource),
                web.post(DESCRIBE_LOOK_AT_CHARACTER_URL, self._describe_look_character),
                web.post(DESCRIBE_INVENTORY_STUFF_ACTION, self._describe_inventory_look_stuff),
                web.post(
                    DESCRIBE_INVENTORY_RESOURCE_ACTION, self._describe_inventory_look_resource
                ),
                web.post(CHARACTER_ACTION, self.character_action),
                web.post(WITH_STUFF_ACTION, self.with_stuff_action),
                web.post(WITH_BUILD_ACTION, self.with_build_action),
                web.post(WITH_RESOURCE_ACTION, self.with_resource_action),
                web.post(WITH_CHARACTER_ACTION, self.with_character_action),
                web.get("/character/{character_id}/zone_data", self.get_zone_data),
                web.get("/character/{character_id}/resume_texts", self.get_resume_texts),
                web.get("/character/{character_id}/dead", self.is_dead),
                web.post("/character/{character_id}/post_mortem", self.get_post_mortem),
                web.post("/character/{character_id}/AP", self.describe_ap),
                web.post("/character/{character_id}/turn", self.describe_turn),
                web.post(
                    "/character/{character_id}/skills_and_knowledge", self.skills_and_knowledge
                ),
            ]
        )
