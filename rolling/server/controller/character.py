import hashlib
import pathlib
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from hapic import HapicData
import json
import serpyco
from sqlalchemy.orm.exc import NoResultFound
import typing
import urllib.parse

import random
from guilang.description import Description, DescriptionType
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import WithBuildAction
from rolling.action.base import WithCharacterAction
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_resource_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import CantMoveCharacter
from rolling.exception import ImpossibleAction
from rolling.exception import ImpossibleAttack
from rolling.exception import NotEnoughActionPoints
from rolling.exception import UserDisplayError
from rolling.exception import WrongInputError
from rolling.kernel import Kernel
from rolling.model.character import (
    CharacterActionModel,
    CharacterModelApi,
    ChooseAvatarQuery,
    CreateCharacterQueryModel,
    ExplodeTakeQuery,
    GetCharacterQueryModel,
    OnPlaceActionQuery,
    SetupCharacterSpritesheetQuery,
)
from rolling.model.character import CharacterModel
from rolling.model.character import ChooseBetweenStuffInventoryStuffModelModel
from rolling.model.character import DescribeStoryQueryModel
from rolling.model.character import DoorPathModel
from rolling.model.character import GetCharacterAndPendingActionPathModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import GetCharacterWithPathModel
from rolling.model.character import GetLookCharacterModel
from rolling.model.character import GetLookInventoryResourceModel
from rolling.model.character import GetLookResourceModel
from rolling.model.character import GetLookStuffModelModel
from rolling.model.character import GetMoveZoneInfosModel
from rolling.model.character import MoveCharacterQueryModel
from rolling.model.character import PendingActionQueryModel
from rolling.model.character import PickFromInventoryQueryModel
from rolling.model.character import SharedInventoryQueryModel
from rolling.model.character import TakeResourceModel
from rolling.model.character import UpdateCharacterCardBodyModel
from rolling.model.character import WithBuildActionModel
from rolling.model.character import WithCharacterActionModel
from rolling.model.character import WithResourceActionModel
from rolling.model.character import WithStuffActionModel
from rolling.model.data import ListOfItemModel
from rolling.model.event import CharacterEnterZoneData, ClientRequireAroundData
from rolling.model.event import CharacterExitZoneData
from rolling.model.event import WebSocketEvent
from rolling.model.event import ZoneEventType
from rolling.model.measure import Unit
from rolling.model.resource import (
    CarriedResourceDescriptionModel,
    CarriedResourceDescriptionModelApi,
)
from rolling.model.stuff import (
    CharacterInventoryModel,
    CharacterInventoryModelApi,
    StuffModelApi,
)
from rolling.model.stuff import StuffModel
from rolling.model.zone import MoveZoneInfos
from rolling.model.zone import ZoneRequiredPlayerData
from rolling.rolling_types import ActionType
from rolling.server.action import ActionFactory
from rolling.server.controller.base import BaseController
from rolling.server.controller.url import CHARACTER_ACTION
from rolling.server.controller.url import DESCRIBE_INVENTORY_RESOURCE_ACTION
from rolling.server.controller.url import DESCRIBE_INVENTORY_STUFF_ACTION
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_RESOURCE_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_STUFF_URL
from rolling.server.controller.url import WITH_BUILD_ACTION
from rolling.server.controller.url import WITH_CHARACTER_ACTION
from rolling.server.controller.url import WITH_RESOURCE_ACTION
from rolling.server.controller.url import WITH_STUFF_ACTION
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.build import DOOR_MODE_LABELS
from rolling.server.document.build import DOOR_MODE__CLOSED_EXCEPT_FOR
from rolling.server.document.build import DoorDocument
from rolling.server.effect import EffectManager
from rolling.server.extension import hapic
from rolling.server.lib.character import (
    DEFAULT_CHARACTER_SPRITESHEETS_IDENTIFIERS,
    CharacterLib,
)
from rolling.server.lib.stuff import StuffLib
from rolling.server.transfer import TransferStuffOrResources
from rolling.util import (
    ILLUSTRATION_AVATAR_PATTERN,
    ExpectedQuantityContext,
    Quantity,
    QuantityEncoder,
)
from rolling.util import InputQuantityContext
from rolling.util import clamp
from rolling.util import display_g_or_kg
from rolling.util import get_exception_for_not_enough_ap
import rrolling

base_skills = ["strength", "endurance", "intelligence", "agility"]


class ShareWithAffinityStuffOrResources(TransferStuffOrResources):
    def __init__(
        self, kernel: Kernel, character: CharacterModel, affinity: AffinityDocument
    ) -> None:
        self.__kernel = kernel
        self._character = character
        self._affinity = affinity

    @property
    def _kernel(self) -> "Kernel":
        return self.__kernel

    def _get_available_stuffs(self) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_carried_by(
            character_id=self._character.id, exclude_shared_with_affinity=True
        )

    def _get_available_resources(self) -> typing.List[CarriedResourceDescriptionModel]:
        return self._kernel.resource_lib.get_carried_by(
            character_id=self._character.id, exclude_shared_with_affinity=True
        )

    def _get_footer_build_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        pass

    def _get_url(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
    ) -> str:
        url = (
            f"/_describe/character/{self._character.id}"
            f"/shared-inventory/add?affinity_id={self._affinity.id}"
        )

        if stuff_id:
            url += f"&stuff_id={stuff_id}"

        if stuff_quantity:
            url += f"&stuff_quantity={stuff_quantity}"

        if resource_id:
            url += f"&resource_id={resource_id}"

        if resource_quantity:
            url += f"&resource_quantity={resource_quantity}"

        return url

    def _get_title(
        self,
        stuff_id: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
    ) -> str:
        if stuff_id is not None:
            stuff = self._kernel.stuff_lib.get_stuff(stuff_id)
            return f"Partager {stuff.name} avec {self._affinity.name}"

        if resource_id is not None:
            resource_description = self._kernel.game.config.resources[resource_id]
            return f"Partager {resource_description.name} avec {self._affinity.name}"

        return f"Partager avec {self._affinity.name}"

    def _get_footer_character_id(
        self, sizing_up_quantity: bool
    ) -> typing.Optional[str]:
        return None

    def _get_footer_affinity_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        if sizing_up_quantity:
            return None
        return self._affinity.id

    def _get_stuff(self, stuff_id: int) -> StuffModel:
        return self._kernel.stuff_lib.get_stuff(stuff_id)

    def _get_likes_this_stuff(self, stuff_id: str) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_carried_by(
            self._character.id,
            exclude_crafting=False,
            stuff_id=stuff_id,
            exclude_shared_with_affinity=True,
        )

    def _transfer_stuff(self, stuff_id: int) -> None:
        self._kernel.stuff_lib.set_shared_with_affinity(stuff_id, self._affinity.id)

    def _get_carried_resource(
        self, resource_id: str
    ) -> CarriedResourceDescriptionModel:
        return self._kernel.resource_lib.get_one_carried_by(
            character_id=self._character.id,
            resource_id=resource_id,
            exclude_shared_with_affinity=True,
        )

    def check_can_transfer_stuff(self, stuff_id: int, quantity: int = 1) -> None:
        try:
            stuff: StuffModel = self._kernel.stuff_lib.get_stuff(stuff_id)
        except NoResultFound:
            raise ImpossibleAction(f"Objet inexistant")

        if quantity > self._kernel.stuff_lib.get_stuff_count(
            character_id=self._character.id,
            stuff_id=stuff.stuff_id,
            exclude_shared_with_affinity=True,
        ):
            raise WrongInputError(f"{self._character.name} n'en a pas assez")

    def check_can_transfer_resource(self, resource_id: str, quantity: float) -> None:
        if not self._kernel.resource_lib.have_resource(
            character_id=self._character.id,
            resource_id=resource_id,
            quantity=quantity,
            exclude_shared_with_affinity=True,
        ):
            raise WrongInputError(f"{self._character.name} n'en a pas assez")

    def _transfer_resource(self, resource_id: str, quantity: float) -> None:
        self._kernel.resource_lib.reduce_carried_by(
            character_id=self._character.id,
            resource_id=resource_id,
            quantity=quantity,
            exclude_shared_with_affinity=True,
        )
        self._kernel.resource_lib.add_resource_to(
            character_id=self._character.id,
            resource_id=resource_id,
            quantity=quantity,
            shared_with_affinity_id=self._affinity.id,
        )

    def _get_stuff_name(self, stuff: StuffModel) -> str:
        return stuff.get_name_and_light_description(self._kernel)

    def _get_resource_name(self, resource: CarriedResourceDescriptionModel) -> str:
        return resource.get_light_description(self._kernel)

    def _get_zone_coordinates(self) -> typing.Optional[typing.Tuple[int, int]]:
        return None

    def _get_classes(self) -> typing.List[str]:
        return []


class SeeSharedWithAffinityStuffOrResources(TransferStuffOrResources):
    def __init__(
        self, kernel: Kernel, character: CharacterModel, affinity: AffinityDocument
    ) -> None:
        self.__kernel = kernel
        self._character = character
        self._affinity = affinity

    @property
    def _kernel(self) -> "Kernel":
        return self.__kernel

    def _get_available_stuffs(self) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_shared_with_affinity(
            character_id=self._character.id, affinity_id=self._affinity.id
        )

    def _get_available_resources(self) -> typing.List[CarriedResourceDescriptionModel]:
        return self._kernel.resource_lib.get_shared_with_affinity(
            character_id=self._character.id, affinity_id=self._affinity.id
        )

    def _get_url(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
    ) -> str:
        url = (
            f"/_describe/character/{self._character.id}"
            f"/shared-inventory?affinity_id={self._affinity.id}"
        )

        if stuff_id:
            url += f"&stuff_id={stuff_id}"

        if stuff_quantity:
            url += f"&stuff_quantity={stuff_quantity}"

        if resource_id:
            url += f"&resource_id={resource_id}"

        if resource_quantity:
            url += f"&resource_quantity={resource_quantity}"

        return url

    def _get_title(
        self,
        stuff_id: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
    ) -> str:
        if stuff_id is not None:
            stuff = self._kernel.stuff_lib.get_stuff(stuff_id)
            return f"Ne plus partager {stuff.name} avec {self._affinity.name}"

        if resource_id is not None:
            resource_description = self._kernel.game.config.resources[resource_id]
            return f"Ne plus partager {resource_description.name} avec {self._affinity.name}"

        return f"Inventaire partagé avec {self._affinity.name}"

    def _get_footer_links(self, sizing_up_quantity: bool) -> typing.List[Part]:
        if sizing_up_quantity:
            return []

        return [
            Part(
                is_link=True,
                label="Partager quelque chose",
                form_action=(
                    f"/_describe/character/{self._character.id}"
                    f"/shared-inventory/add?affinity_id={self._affinity.id}"
                ),
            )
        ]

    def _get_footer_character_id(
        self, sizing_up_quantity: bool
    ) -> typing.Optional[str]:
        return None

    def _get_footer_affinity_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        if sizing_up_quantity:
            return None
        return self._affinity.id

    def _get_footer_build_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return None

    def _get_stuff(self, stuff_id: int) -> StuffModel:
        return self._kernel.stuff_lib.get_stuff(stuff_id)

    def _get_likes_this_stuff(self, stuff_id: str) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_carried_by(
            self._character.id,
            exclude_crafting=False,
            stuff_id=stuff_id,
            shared_with_affinity_ids=[self._affinity.id],
        )

    def _transfer_stuff(self, stuff_id: int) -> None:
        self._kernel.stuff_lib.unshare_with_affinity(stuff_id)

    def _get_carried_resource(
        self, resource_id: str
    ) -> CarriedResourceDescriptionModel:
        return self._kernel.resource_lib.get_one_carried_by(
            character_id=self._character.id,
            resource_id=resource_id,
            shared_with_affinity_ids=[self._affinity.id],
        )

    def check_can_transfer_stuff(self, stuff_id: int, quantity: int = 1) -> None:
        try:
            stuff: StuffModel = self._kernel.stuff_lib.get_stuff(stuff_id)
        except NoResultFound:
            raise ImpossibleAction(f"Objet inexistant")

        if quantity > self._kernel.stuff_lib.get_stuff_count(
            character_id=self._character.id,
            stuff_id=stuff.stuff_id,
            shared_with_affinity_ids=[self._affinity.id],
        ):
            raise WrongInputError(f"{self._character.name} n'en a pas assez")

    def check_can_transfer_resource(self, resource_id: str, quantity: float) -> None:
        if not self._kernel.resource_lib.have_resource(
            character_id=self._character.id,
            resource_id=resource_id,
            quantity=quantity,
            shared_with_affinity_ids=[self._affinity.id],
        ):
            raise WrongInputError(f"{self._character.name} n'en a pas assez")

    def _transfer_resource(self, resource_id: str, quantity: float) -> None:
        self._kernel.resource_lib.reduce_carried_by(
            character_id=self._character.id,
            resource_id=resource_id,
            quantity=quantity,
            shared_with_affinity_ids=[self._affinity.id],
        )
        self._kernel.resource_lib.add_resource_to(
            character_id=self._character.id,
            resource_id=resource_id,
            quantity=quantity,
            exclude_shared_with_affinity=True,
        )

    def _get_stuff_name(self, stuff: StuffModel) -> str:
        return stuff.get_name_and_light_description(self._kernel)

    def _get_resource_name(self, resource: CarriedResourceDescriptionModel) -> str:
        return resource.get_light_description(self._kernel)

    def _get_zone_coordinates(self) -> typing.Optional[typing.Tuple[int, int]]:
        return None

    def _get_classes(self) -> typing.List[str]:
        return []


class CharacterController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel
        self._character_lib = CharacterLib(self._kernel)
        self._stuff_lib = StuffLib(self._kernel)
        self._effect_manager = EffectManager(self._kernel)
        self._action_factory = ActionFactory(self._kernel)

    @hapic.with_api_doc()
    @hapic.input_query(CreateCharacterQueryModel)
    @hapic.output_body(Description)
    async def _describe_create_character(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        if hapic_data.query.spawn_to == 0:
            spawn_points = self._kernel.spawn_point_lib.get_all()
            spawn_points_parts = []
            for spawn_point in spawn_points:
                affinity = self._kernel.affinity_lib.get_affinity(
                    spawn_point.affinity_id
                )
                spawn_points_parts.append(
                    Part(
                        is_link=True,
                        label=f"Choisir '{affinity.name}'",
                        form_action=f"/_describe/character/create?spawn_to={spawn_point.id}",
                    )
                )

            if not spawn_points:
                spawn_points_parts.append(
                    Part(text="Aucun lieu d'apparition à cet instant")
                )

            return Description(
                title="Créer votre personnage",
                items=[
                    Part(
                        text=(
                            "Vous vous apprêtez à donner vie à un personnage dans cet univers. "
                            "En premier lieu, vous pouvez choisir où votre personnage sera envoyé. "
                        )
                    ),
                    Part(text=" "),
                ]
                + spawn_points_parts
                + [
                    Part(text=" "),
                    Part(
                        is_link=True,
                        label="Choisir une destination inconnue",
                        form_action="/_describe/character/create?spawn_to=-1",
                    ),
                ],
            )

        maximum_points = self._kernel.game.config.create_character_max_points
        parts = [Part(label="Traits physionomiques", classes=["h2"])]

        for skill_id in base_skills:
            skill_description = self._kernel.game.config.skills[skill_id]
            parts.append(
                Part(
                    label=skill_description.name,
                    type_=Type.NUMBER,
                    default_value=str(skill_description.default),
                    name=f"skill__{skill_id}",
                    min_value=self._kernel.game.config.min_character_card_input_at_create,
                    max_value=self._kernel.game.config.max_character_card_input_at_create,
                )
            )

        parts.append(Part(label="Spécialisations", classes=["h2"]))

        for skill_id in self._kernel.game.config.create_character_skills:
            skill_description = self._kernel.game.config.skills[skill_id]
            parts.append(
                Part(
                    label=skill_description.name,
                    type_=Type.NUMBER,
                    default_value=str(skill_description.default),
                    name=f"skill__{skill_id}",
                    min_value=self._kernel.game.config.min_character_card_input_at_create,
                    max_value=self._kernel.game.config.max_character_card_input_at_create,
                )
            )

        create_character_knowledges = (
            self._kernel.game.config.create_character_knowledges
        )
        if (
            create_character_knowledges
            and self._kernel.game.config.create_character_knowledges_count
        ):
            parts.append(Part(label="Connaissances", classes=["h2"]))
            for knowledge_id in create_character_knowledges:
                knowledge_description = self._kernel.game.config.knowledge[knowledge_id]
                parts.append(
                    Part(
                        is_checkbox=True,
                        label=knowledge_description.name,
                        name=f"knowledge__{knowledge_description.id}",
                    )
                )
            # there is a bug in gui (checkbox not displayed if are at end)
            parts.append(Part(label=""))

        return Description(
            title="Créer votre personnage",
            items=[
                Part(
                    text=(
                        "C'est le moment de créer votre personnage. Ci-dessous, vous pouvez "
                        f"répartir jusqu'à {maximum_points} points de compétences et choisir "
                        f"{self._kernel.game.config.create_character_knowledges_count} "
                        f"connaissance(s)."
                    ),
                    classes=["p"],
                ),
                Part(
                    is_form=True,
                    form_action=f"/_describe/character/create/do?spawn_to={hapic_data.query.spawn_to}",
                    items=[
                        Part(label="Nom du personnage", type_=Type.STRING, name="name")
                    ]
                    + parts,
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

        # FIXME BS NOW: ajouter un bouton et vue (si action descr existe) personnages suivis
        followed_count = self._character_lib.get_followed_count(character.id)
        parts = [
            Part(
                is_link=True,
                form_action=f"/character/{character.id}/followed",
                label=f"Vous suivez {followed_count} personnages",
            )
        ]

        if not character.avatar_uuid:
            parts.append(
                Part(
                    label="Choisir un avatar",
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/card/choose-avatar",
                )
            )

        inventory = self._kernel.character_lib.get_inventory(character)
        inventory_weight = inventory.weight
        inventory_weight_str = f"{round(inventory_weight/1000,3)}kg"
        weight_capacity = character.get_weight_capacity(self._kernel)
        weight_capacity_str = f"{round(weight_capacity/1000,3)}kg"
        inventory_clutter = inventory.clutter
        clutter_capacity = character.get_clutter_capacity(self._kernel)
        weight_over_str = " (surcharge !)" if inventory.over_weight else ""
        clutter_over_str = " (surcharge !)" if inventory.over_clutter else ""

        illustration_name = (
            ILLUSTRATION_AVATAR_PATTERN.format(avatar_uuid=character.avatar_uuid)
            if character.avatar_uuid
            else ILLUSTRATION_AVATAR_PATTERN.format(avatar_uuid="0000")
        )
        return Description(
            title="Fiche de personnage",
            illustration_name=illustration_name,
            can_be_back_url=True,
            items=[
                Part(label="Nom", text=character.name),
                Part(
                    label="Points d'actions restants",
                    text=f"{str(character.action_points)}",
                ),
                Part(
                    label="Points de vie",
                    text=f"{self._kernel.character_lib.get_health_text(character)} ({character.life_points})",
                ),
                Part(label="Soif", text=str(round(character.thirst, 0))),
                Part(label="Faim", text=str(round(character.hunger, 0))),
                Part(
                    label="Fatigué",
                    text=("oui" if character.tired else "non")
                    + f" {character.tiredness}",
                ),
                Part(label="Exténué", text="oui" if character.is_exhausted else "non"),
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
                    classes=["link"],
                ),
                Part(
                    label="Bouclier",
                    text=character.shield.name if character.shield else "aucun",
                    is_link=True if character.shield else False,
                    align="left",
                    form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=character.shield.id
                    )
                    if character.shield
                    else None,
                    classes=["link"],
                ),
                Part(
                    label="Armure",
                    text=character.armor.name if character.armor else "aucune",
                    is_link=True if character.armor else False,
                    align="left",
                    form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=character.armor.id
                    )
                    if character.armor
                    else None,
                    classes=["link"],
                ),
                Part(
                    label="Sac",
                    text=character.bags[0].name if character.bags else "aucune",
                    is_link=True if character.bags else False,
                    align="left",
                    form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=character.bags[0].id
                    )
                    if character.bags
                    else None,
                    classes=["link"],
                ),
                Part(
                    text=f"Poids transporté : {inventory_weight_str}/{weight_capacity_str}{weight_over_str}"
                ),
                Part(
                    text=f"Encombrement transporté : {inventory_clutter}/{clutter_capacity}{clutter_over_str}"
                ),
                Part(text=""),
                # Part(
                #     is_form=True,
                #     form_action=f"/_describe/character/{character.id}/card",
                #     items=[
                #         Part(
                #             text="Si vous occupez la position de chef de guerre, vous pouvez "
                #             "décider de la part de perte maximale dans vos rangs avant "
                #             "d'ordonner le replis"
                #         ),
                #         Part(
                #             label="Lorsque vous menez un assault (%)",
                #             type_=Type.NUMBER,
                #             name="attack_allowed_loss_rate",
                #             default_value=str(doc.attack_allowed_loss_rate),
                #         ),
                #         Part(
                #             label="Lorsque vous êtes attaqué (%)",
                #             type_=Type.NUMBER,
                #             name="defend_allowed_loss_rate",
                #             default_value=str(doc.defend_allowed_loss_rate),
                #         ),
                #     ],
                # ),
            ]
            + parts,
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
    async def skills_and_knowledge(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
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
                Part(
                    label="Fiche personnage",
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/card",
                )
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterWithPathModel)
    @hapic.output_body(Description)
    async def with_character_card(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        # TODO: check same zone
        character = self._character_lib.get(hapic_data.path.character_id)
        with_character = self._character_lib.get(hapic_data.path.with_character_id)
        illustration_name = (
            ILLUSTRATION_AVATAR_PATTERN.format(avatar_uuid=with_character.avatar_uuid)
            if with_character.avatar_uuid
            else ILLUSTRATION_AVATAR_PATTERN.format(avatar_uuid="0000")
        )
        return Description(
            title=f"Fiche de {with_character.name}",
            illustration_name=illustration_name,
            items=[Part(text="Personnage"), Part(text=f"Nom: {with_character.name}")],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(CharacterInventoryModelApi)
    async def _get_inventory_data(
        self, request: Request, hapic_data: HapicData
    ) -> CharacterInventoryModelApi:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(character, include_equip=True)
        stuffs = []
        resources = []

        seen_stuffs: typing.Set[str] = set()
        for stuff in inventory.stuff:
            is_equip = bool(stuff.used_by)
            seen_id = f"{stuff.stuff_id}_{stuff.under_construction}_{is_equip}"
            if seen_id not in seen_stuffs:
                seen_stuffs.add(seen_id)
                similar_stuffs = [
                    s
                    for s in inventory.stuff
                    if stuff.stuff_id == s.stuff_id
                    and stuff.under_construction == s.under_construction
                    and bool(stuff.used_by) == bool(s.used_by)
                ]
                count = len(similar_stuffs)
                weight = sum([s.weight for s in similar_stuffs])
                clutter = sum([s.clutter for s in similar_stuffs])
                unit_str = self._kernel.translation.get(Unit.KILOGRAM, short=True)
                equi_str = " (équipé)" if is_equip else ""
                infos = f"{count}x {stuff.name}, {round(weight / 1000, 3)} {unit_str}, {clutter} d'encombrement{equi_str}"
                is_heavy = (
                    weight / character.get_weight_capacity(self._kernel)
                    >= self._kernel.game.config.ratio_item_is_heavy
                )
                is_cumbersome = (
                    clutter / character.get_clutter_capacity(self._kernel)
                    >= self._kernel.game.config.ratio_item_is_cumbersome
                )
                stuffs.append(
                    StuffModelApi(
                        ids=[s.id for s in similar_stuffs],
                        stuff_id=stuff.stuff_id,
                        name=stuff.name,
                        infos=infos,
                        under_construction=stuff.under_construction,
                        classes=stuff.classes + [stuff.stuff_id],
                        is_equipment=stuff.weapon or stuff.shield or stuff.armor,
                        count=count,
                        drop_base_url=get_with_stuff_action_url(
                            character_id=hapic_data.path.character_id,
                            stuff_id=stuff.id,
                            action_type=ActionType.DROP_STUFF,
                            action_description_id="DROP_STUFF",
                            query_params={
                                "quantity": count,
                            },
                        ),
                        is_heavy=is_heavy,
                        is_cumbersome=is_cumbersome,
                        is_equip=is_equip,
                    )
                )

        for resource in inventory.resource:
            resource_description = self._kernel.game.config.resources[resource.id]
            clutter = resource_description.clutter * resource.quantity
            weight = resource_description.weight * resource.quantity
            if resource_description.unit == Unit.GRAM:
                kg_str = self._kernel.translation.get(Unit.KILOGRAM, short=True)
                quantity_str = f"{round(resource.quantity/1000, 3)}{kg_str}"
                infos = f"{quantity_str} {resource.name}, {clutter} d'encombrement"
            else:
                unit_str = self._kernel.translation.get(
                    resource_description.unit, short=True
                )
                quantity_str = f"{round(resource.quantity, 5)}{unit_str}"
                infos = f"{quantity_str} {resource.name}, {clutter} d'encombrement"
            is_heavy = (
                weight / character.get_weight_capacity(self._kernel)
                >= self._kernel.game.config.ratio_item_is_heavy
            )
            is_cumbersome = (
                clutter / character.get_clutter_capacity(self._kernel)
                >= self._kernel.game.config.ratio_item_is_cumbersome
            )
            unit_str = self._kernel.translation.get(
                resource_description.unit, short=True
            )
            resources.append(
                CarriedResourceDescriptionModelApi(
                    id=resource.id,
                    name=resource.name,
                    weight=resource.weight,
                    clutter=resource.clutter,
                    infos=infos,
                    classes=[resource.id],
                    quantity=resource.quantity,
                    quantity_str=quantity_str,
                    drop_base_url=get_with_resource_action_url(
                        character_id=hapic_data.path.character_id,
                        resource_id=resource.id,
                        action_type=ActionType.DROP_RESOURCE,
                        action_description_id="DROP_RESOURCE",
                        query_params={
                            "quantity": f"{resource.quantity} {unit_str}",
                        },
                    ),
                    is_heavy=is_heavy,
                    is_cumbersome=is_cumbersome,
                )
            )

        inventory_api = CharacterInventoryModelApi(
            stuff=stuffs,
            resource=resources,
            clutter=inventory.clutter,
            weight=inventory.weight,
            over_weight=inventory.over_weight,
            over_clutter=inventory.over_clutter,
        )

        return inventory_api

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(character)
        inventory_parts = self._get_inventory_parts(
            request,
            character,
            inventory,
            then_redirect_url=f"/_describe/character/{character.id}/inventory",
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

        footer_links = []

        count_things_shared_withs = 0
        for affinity_relation in self._kernel.affinity_lib.get_accepted_affinities(
            character_id=character.id
        ):
            count_things_shared_withs += (
                self._kernel.affinity_lib.count_things_shared_with_affinity(
                    character_id=character.id, affinity_id=affinity_relation.affinity_id
                )
            )

        if count_things_shared_withs:
            footer_links.append(
                Part(
                    is_link=True,
                    label=f"Voir ce qui est paratgé ({count_things_shared_withs})",
                    form_action=f"/_describe/character/{character.id}/inventory/shared-with",
                )
            )

        return Description(
            title="Inventaire",
            items=[
                Part(
                    text=f"Poids transporté: {weight_str} ({max_weight_str} max{weight_overcharge})"
                ),
                Part(
                    text=f"Encombrement: {round(inventory.clutter, 2)} ({round(max_clutter, 2)} max{clutter_overcharge})"
                ),
            ]
            + inventory_parts,
            footer_links=footer_links,
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_shared_with_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        items = []

        for affinity_relation in self._kernel.affinity_lib.get_accepted_affinities(
            character_id=character.id
        ):
            affinity = self._kernel.affinity_lib.get_affinity(
                affinity_relation.affinity_id
            )
            count_things_shared_with = (
                self._kernel.affinity_lib.count_things_shared_with_affinity(
                    character_id=character.id, affinity_id=affinity_relation.affinity_id
                )
            )
            items.append(
                Part(
                    is_link=True,
                    label=f"Avec {affinity.name} ({count_things_shared_with})",
                    form_action=(
                        f"/_describe/character/{character.id}"
                        f"/shared-inventory?affinity_id={affinity.id}"
                    ),
                )
            )

        return Description(
            title="Inventaire partagé avec des affinités",
            items=items,
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(SharedInventoryQueryModel)
    @hapic.output_body(Description)
    async def _describe_shared_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        input_: SharedInventoryQueryModel = hapic_data.query
        character_id = hapic_data.path.character_id
        character = self._kernel.character_lib.get(character_id)
        affinity_id = input_.affinity_id
        affinity = self._kernel.affinity_lib.get_affinity(affinity_id)

        return SeeSharedWithAffinityStuffOrResources(
            kernel=self._kernel, character=character, affinity=affinity
        ).get_description(
            stuff_id=input_.stuff_id,
            stuff_quantity=input_.stuff_quantity_int,
            resource_id=input_.resource_id,
            resource_quantity=input_.resource_quantity,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(SharedInventoryQueryModel)
    @hapic.output_body(Description)
    async def _describe_add_to_shared_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        input_: SharedInventoryQueryModel = hapic_data.query
        character_id = hapic_data.path.character_id
        character = self._kernel.character_lib.get(character_id)
        affinity_id = input_.affinity_id
        affinity = self._kernel.affinity_lib.get_affinity(affinity_id)

        return ShareWithAffinityStuffOrResources(
            kernel=self._kernel, character=character, affinity=affinity
        ).get_description(
            stuff_id=input_.stuff_id,
            stuff_quantity=input_.stuff_quantity_int,
            resource_id=input_.resource_id,
            resource_quantity=input_.resource_quantity,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(PickFromInventoryQueryModel)
    @hapic.output_body(Description)
    async def pick_from_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(character)
        form_parts = []
        form_action = (
            f"/_describe/character/{character.id}/pick_from_inventory"
            f"?callback_url={hapic_data.query.callback_url}"
            f"&cancel_url={hapic_data.query.cancel_url}"
            f"&title={hapic_data.query.title}"
        )
        can_be_back_url = True

        if hapic_data.query.resource_id is None and hapic_data.query.stuff_id is None:
            stuff_displayed: typing.Dict[str, bool] = {
                s.stuff_id: False for s in inventory.stuff
            }
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
                form_action = (
                    f"{form_action}&resource_id={hapic_data.query.resource_id}"
                )
                default_value = self._kernel.resource_lib.get_one_carried_by(
                    character.id, resource_id=hapic_data.query.resource_id
                ).quantity
                resource_description = self._kernel.game.config.resources[
                    hapic_data.query.resource_id
                ]
                unit_str = self._kernel.translation.get(resource_description.unit)
                quantity_prefix = "resource_"
                expect_integer = False
            else:
                form_action = f"{form_action}&stuff_id={hapic_data.query.stuff_id}"
                default_value = self._kernel.stuff_lib.get_stuff_count(
                    character_id=character.id, stuff_id=hapic_data.query.stuff_id
                )
                unit_str = "unité"
                quantity_prefix = "stuff_"
                expect_integer = True

            form_parts.append(
                Part(
                    label=f"Quantité ({unit_str}) ?",
                    name=f"{quantity_prefix}quantity",
                    type_=Type.NUMBER,
                    default_value=str(default_value),
                    expect_integer=expect_integer,
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
                )
            ],
            can_be_back_url=can_be_back_url,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterWithPathModel)
    @hapic.output_body(Description)
    async def with_inventory(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        # TODO: check same zone
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        with_character = self._kernel.character_lib.get(
            hapic_data.path.with_character_id
        )
        inventory = self._character_lib.get_inventory(with_character)
        inventory_parts = self._get_inventory_parts(
            request,
            with_character,
            inventory,
            disable_stuff_link=True,
            disable_drop_links=True,
        )

        return Description(
            title="Inventory", items=inventory_parts, can_be_back_url=True
        )

    def _get_inventory_parts(
        self,
        request: Request,
        character: CharacterModel,
        inventory: CharacterInventoryModel,
        disable_stuff_link: bool = False,
        disable_drop_links: bool = False,
        then_redirect_url: typing.Optional[str] = None,
    ) -> typing.List[Part]:
        stuff_items: typing.List[Part] = []
        resource_items: typing.List[Part] = []
        bags = self._character_lib.get_used_bags(character.id)
        bags_string = "Aucun" if not bags else ", ".join([bag.name for bag in bags])
        stuff_count: typing.Dict[str, int] = {}
        stuff_by_stuff_ids: typing.Dict[str, typing.List[StuffModel]] = {}

        for stuff in inventory.stuff:
            stuff_count.setdefault(stuff.stuff_id, 0)
            stuff_by_stuff_ids.setdefault(stuff.stuff_id, [])
            stuff_count[stuff.stuff_id] += 1
            stuff_by_stuff_ids[stuff.stuff_id].append(stuff)

        stuff_displayed: typing.Dict[str, bool] = {
            s.stuff_id: False for s in inventory.stuff
        }
        for stuff in inventory.stuff:
            if stuff_displayed[stuff.stuff_id]:
                continue

            name = stuff.get_name()
            if stuff_count[stuff.stuff_id] > 1:
                total_weight = sum(s.weight for s in stuff_by_stuff_ids[stuff.stuff_id])
                total_clutter = sum(
                    s.clutter for s in stuff_by_stuff_ids[stuff.stuff_id]
                )
                description = (
                    f" ({display_g_or_kg(total_weight)}, "
                    f"{round(total_clutter, 2)} encombrement)"
                )
            else:
                descriptions: typing.List[str] = stuff.get_full_description(
                    self._kernel
                )

                description = ""
                if descriptions:
                    description = " (" + ", ".join(descriptions) + ")"

            if stuff_count[stuff.stuff_id] > 1:
                text = f"{stuff_count[stuff.stuff_id]} {name}{description}"
            else:
                text = f"{name}{description}"

            if stuff_count[stuff.stuff_id] > 1:
                form_action = "/_describe/character/{character_id}/inventory/choose-between-stuff/{stuff_id}".format(
                    character_id=character.id, stuff_id=stuff.stuff_id
                )
            else:
                form_action = DESCRIBE_INVENTORY_STUFF_ACTION.format(
                    character_id=character.id, stuff_id=stuff.id
                )
            is_link = True

            if disable_stuff_link:
                form_action = None
                is_link = False

            if disable_drop_links:
                stuff_items.append(
                    Part(
                        text=text,
                        is_link=is_link,
                        align="left",
                        form_action=form_action,
                        classes=stuff.classes + [stuff.stuff_id],
                    )
                )
            else:
                partial_drop_url = get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.DROP_STUFF,
                    stuff_id=stuff.id,
                    query_params={
                        "quantity": "1",
                        "then_redirect_url": f"{then_redirect_url}",
                    },
                    action_description_id="DROP_STUFF",
                )
                drop_url = get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.DROP_STUFF,
                    stuff_id=stuff.id,
                    query_params={
                        "quantity": str(stuff_count[stuff.stuff_id]),
                        "then_redirect_url": f"{then_redirect_url}",
                    },
                    action_description_id="DROP_STUFF",
                )
                stuff_items.append(
                    Part(
                        columns=15,
                        items=[
                            Part(
                                is_column=True,
                                colspan=13,
                                items=[
                                    Part(
                                        text=text,
                                        is_link=is_link,
                                        align="left",
                                        form_action=form_action,
                                        classes=stuff.classes + [stuff.stuff_id],
                                    )
                                ],
                            ),
                            Part(
                                is_column=True,
                                items=[
                                    Part(
                                        label=drop_url,
                                        is_link=is_link,
                                        form_action=drop_url,
                                        classes=["drop_item"],
                                    )
                                ],
                            ),
                            Part(
                                is_column=True,
                                items=[
                                    Part(
                                        label=partial_drop_url,
                                        is_link=is_link,
                                        form_action=partial_drop_url,
                                        classes=["partial_drop_item"],
                                    )
                                ],
                            ),
                        ],
                    )
                )
            stuff_displayed[stuff.stuff_id] = True

        resource: CarriedResourceDescriptionModel
        for resource in inventory.resource:
            form_action = DESCRIBE_INVENTORY_RESOURCE_ACTION.format(
                character_id=character.id, resource_id=resource.id
            )
            is_link = True

            if disable_stuff_link:
                form_action = None
                is_link = False

            if disable_drop_links:
                resource_items.append(
                    Part(
                        text=f"{resource.get_full_description(self._kernel)}",
                        is_link=is_link,
                        align="left",
                        form_action=form_action,
                        classes=[resource.id],
                    )
                )
            else:
                unit_str = self._kernel.translation.get(resource.unit, short=True)
                partial_quantity: str = request.query.get(
                    f"{resource.id}_partial_quantity",
                    str(round(resource.quantity * 0.1, 4)) + unit_str,
                )
                partial_drop_url = get_with_resource_action_url(
                    character_id=character.id,
                    action_type=ActionType.DROP_RESOURCE,
                    resource_id=resource.id,
                    query_params={
                        "quantity": partial_quantity,
                        "then_redirect_url": f"{then_redirect_url}"
                        f"?{resource.id}_partial_quantity={partial_quantity}",
                    },
                    action_description_id="DROP_RESOURCE",
                )
                drop_url = get_with_resource_action_url(
                    character_id=character.id,
                    action_type=ActionType.DROP_RESOURCE,
                    resource_id=resource.id,
                    query_params={
                        "quantity": str(resource.quantity) + unit_str,
                        "then_redirect_url": then_redirect_url,
                    },
                    action_description_id="DROP_RESOURCE",
                )
                resource_items.append(
                    Part(
                        columns=15,
                        items=[
                            Part(
                                is_column=True,
                                colspan=13,
                                items=[
                                    Part(
                                        text=f"{resource.get_full_description(self._kernel)}",
                                        is_link=is_link,
                                        align="left",
                                        form_action=form_action,
                                        classes=[resource.id],
                                    )
                                ],
                            ),
                            Part(
                                is_column=True,
                                items=[
                                    Part(
                                        label=drop_url,
                                        is_link=is_link,
                                        form_action=drop_url,
                                        classes=["drop_item"],
                                    )
                                ],
                            ),
                            Part(
                                is_column=True,
                                items=[
                                    Part(
                                        label=partial_drop_url,
                                        is_link=is_link,
                                        form_action=partial_drop_url,
                                        classes=["partial_drop_item"],
                                    )
                                ],
                            ),
                        ],
                    )
                )

        return [
            Part(text=f"Sac(s): {bags_string}", classes=["h2"]),
            Part(text=" "),
            Part(text="Objets", classes=["h2"]),
            *stuff_items,
            Part(text=" "),
            Part(text="Resources", classes=["h2"]),
            *resource_items,
        ]

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _main_actions(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character_id = hapic_data.path.character_id
        grid_buttons = []

        for main_action in self._kernel.game.config.main_actions:
            filter_action_types = ",".join(main_action.action_types)
            grid_buttons.append(
                Part(
                    label=main_action.name,
                    classes=[main_action.class_],
                    form_action=(
                        f"/_describe/character/{character_id}/on_place_actions"
                        f"?filter_action_types={filter_action_types}"
                        f"&from_main_action_name={main_action.name}"
                    ),
                    is_link=True,
                )
            )

        return Description(
            title="Actions principales",
            is_grid=True,
            items=grid_buttons,
            footer_links=[
                Part(
                    is_link=True,
                    label="Toutes les actions",
                    form_action=f"/_describe/character/{character_id}/on_place_actions",
                )
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(OnPlaceActionQuery)
    @hapic.output_body(Description)
    async def _describe_on_place_actions(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        filter_action_types = None
        if hapic_data.query.filter_action_types:
            filter_action_types = hapic_data.query.filter_action_types.split(",")
        character_actions = self._character_lib.get_on_place_actions(
            hapic_data.path.character_id,
            filter_action_types=filter_action_types,
        )
        pending_actions_count = self._kernel.character_lib.get_pending_actions_count(
            hapic_data.path.character_id
        )
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        zone_properties = (
            self._kernel.game.world_manager.get_zone_properties_by_coordinates(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
            )
        )

        parts = []
        if filter_action_types is None and pending_actions_count:
            parts.append(
                Part(
                    is_link=True,
                    form_action=f"/_describe/character/{hapic_data.path.character_id}/pending_actions",
                    label=f"{pending_actions_count} propositions d'actions",
                )
            )

        if from_main_action_name := hapic_data.query.from_main_action_name:
            main_action = next(
                main_action
                for main_action in self._kernel.game.config.main_actions
                if main_action.name == from_main_action_name
            )
            if main_action_description := main_action.description:
                parts.append(Part(text=main_action_description))

        action_parts = []
        action_categories = list(sorted(set([a.category for a in character_actions])))
        for action_category in action_categories:
            # TODO : for now, dont add a text line with category
            # action_parts.append(Part(classes=["h2"], text=action_category or "Autres"))
            for character_action in character_actions:
                if character_action.category == action_category:
                    action_parts.append(
                        Part(
                            text=character_action.get_as_str(),
                            form_action=character_action.link,
                            is_link=True,
                            link_group_name=character_action.group_name,
                            classes=character_action.classes1,
                            classes2=character_action.classes2,
                            cost=character_action.cost,
                            use_classes2_for_button=character_action.use_classes2_for_button,
                        )
                    )

        return Description(
            title="Que voulez-vous faire ?",
            illustration_name=zone_properties.illustration,
            disable_illustration_row=True,
            items=parts + action_parts,
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def pending_actions(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        pending_actions = self._kernel.character_lib.get_pending_actions(
            hapic_data.path.character_id
        )

        parts = []
        for pending_action in pending_actions:
            parts.append(
                Part(
                    is_link=True,
                    form_action=f"/_describe/character/{hapic_data.path.character_id}/pending_actions/{pending_action.id}",
                    label=pending_action.name,
                )
            )

        return Description(
            title="Propositions d'actions", items=parts, can_be_back_url=True
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterAndPendingActionPathModel)
    @hapic.input_query(PendingActionQueryModel)
    @hapic.output_body(Description)
    async def pending_action(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        pending_action = self._kernel.character_lib.get_pending_action(
            hapic_data.path.pending_action_id,
            check_authorized_character_id=hapic_data.path.character_id,
        )

        if hapic_data.query.do:
            try:
                return await self._kernel.action_factory.execute_pending(pending_action)
            except (ImpossibleAction, WrongInputError) as exc:
                return Description(
                    title="Action impossible",
                    quick_action_response=str(exc).replace("\n", " "),
                    type_=DescriptionType.ERROR,
                    back_url=f"/_describe/character/{hapic_data.path.character_id}/pending_actions/{pending_action.id}",
                    items=[Part(text=line) for line in str(exc).split("\n")],
                    footer_links=[
                        Part(
                            is_link=True,
                            label="Retourner aux propositions d'actions",
                            form_action=f"/_describe/character/{hapic_data.path.character_id}/pending_actions",
                        )
                    ],
                    illustration_name=getattr(exc, "illustration_name", None),
                )

        return Description(
            title=pending_action.name,
            back_url=None,
            items=[
                Part(
                    is_link=True,
                    label="Effectuer cette action",
                    form_action=f"/_describe/character/{hapic_data.path.character_id}/pending_actions/{pending_action.id}?do=1",
                )
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_build_actions(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        build_actions = self._character_lib.get_build_actions(
            hapic_data.path.character_id
        )

        return Description(
            title="Démarrer une construction",
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                    classes=action.classes1,
                )
                for action in build_actions
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def _describe_events(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get_document(
            hapic_data.path.character_id, dead=None
        )
        character_events = self._character_lib.get_last_events(
            hapic_data.path.character_id, count=100
        )
        parts = []
        event_ids_to_mark_read = []
        for event in character_events:
            there_is_story = bool(
                self._kernel.character_lib.count_story_pages(event.id)
            )
            unread = "*" if event.unread else ""

            form_action = None
            if there_is_story:
                form_action = f"/_describe/character/{character.id}/story?event_id={event.id}&mark_read=1"

            parts.append(
                Part(
                    text=f"Tour {event.turn}{unread}: {event.text}",
                    is_link=there_is_story,
                    form_action=form_action,
                )
            )

            if not there_is_story and event.unread:
                event_ids_to_mark_read.append(event.id)

            if event_ids_to_mark_read:
                self._kernel.character_lib.mark_event_as_read(event_ids_to_mark_read)

        return Description(
            title="Histoire", is_long_text=True, items=parts, can_be_back_url=True
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(DescribeStoryQueryModel)
    @hapic.output_body(Description)
    async def _describe_story(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get_document(
            hapic_data.path.character_id, dead=None
        )
        event = self._kernel.character_lib.get_event(hapic_data.query.event_id)
        if not hapic_data.query.story_page_id:
            story_page = self._kernel.character_lib.get_first_story_page(
                hapic_data.query.event_id
            )
        else:
            story_page = self._kernel.character_lib.get_story_page(
                hapic_data.query.story_page_id
            )

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
            self._kernel.character_lib.mark_event_as_read([event.id])

        return Description(
            title=event.text,
            is_long_text=True,
            items=items,
            footer_links=footer_links,
            can_be_back_url=True,
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
        illustration_name = (
            ILLUSTRATION_AVATAR_PATTERN.format(avatar_uuid=with_character.avatar_uuid)
            if with_character.avatar_uuid
            else ILLUSTRATION_AVATAR_PATTERN.format(avatar_uuid="0000")
        )
        return Description(
            title=with_character.name,
            illustration_name=illustration_name,
            items=[
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                    is_web_browser_link=action.is_web_browser_link,
                )
                for action in actions
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookResourceModel)
    @hapic.input_query(TakeResourceModel)
    @hapic.output_body(Description)
    async def _describe_look_resource(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        resource_description = self._kernel.game.config.resources[
            hapic_data.path.resource_id
        ]
        ground_resources = self._kernel.resource_lib.get_ground_resource(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=hapic_data.path.row_i,
            zone_col_i=hapic_data.path.col_i,
        )
        ground_resource_ids = [r.id for r in ground_resources]
        if hapic_data.path.resource_id not in ground_resource_ids:
            return Description(
                title="Cette ressource n'est plus là", items=[Part(is_link=True)]
            )
        ground_resource = next(
            r for r in ground_resources if r.id == hapic_data.path.resource_id
        )
        expected_quantity_context = ExpectedQuantityContext.from_carried_resource(
            self._kernel, ground_resource
        )
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
                                label=(
                                    f"Récupérer quelle quantité "
                                    f"({expected_quantity_context.display_unit_name} ?)"
                                ),
                                name="quantity",
                                type_=Type.NUMBER,
                                min=0.0,
                                max=expected_quantity_context.default_quantity_float,
                                default_value=expected_quantity_context.default_quantity,
                            )
                        ],
                    )
                ],
                can_be_back_url=True,
            )

        user_input_context = InputQuantityContext.from_carried_resource(
            user_input=hapic_data.query.quantity,
            carried_resource=ground_resource,
        )

        self._kernel.resource_lib.add_resource_to(
            character_id=character.id,
            resource_id=hapic_data.path.resource_id,
            quantity=user_input_context.real_quantity,
            commit=False,
        )
        self._kernel.resource_lib.reduce_on_ground(
            resource_id=hapic_data.path.resource_id,
            quantity=user_input_context.real_quantity,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=hapic_data.path.row_i,
            zone_col_i=hapic_data.path.col_i,
            commit=True,
        )

        return Description(
            title=f"{resource_description.name} récupéré",
            items=[Part(is_link=True)],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(ChooseBetweenStuffInventoryStuffModelModel)
    @hapic.output_body(Description)
    async def _choose_between_stuff(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        stuffs = self._kernel.stuff_lib.get_carried_by(
            character_id=hapic_data.path.character_id,
            stuff_id=hapic_data.path.stuff_id,
            exclude_crafting=False,
        )
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            hapic_data.path.stuff_id
        )

        parts = []
        for stuff in stuffs:
            description_str = ", ".join(stuff.get_full_description(self._kernel))
            under_construction_str = "*" if stuff.under_construction else ""
            label = (
                f"{under_construction_str}{stuff_properties.name} ({description_str})"
            )
            parts.append(
                Part(
                    label=label,
                    is_link=True,
                    form_action=DESCRIBE_INVENTORY_STUFF_ACTION.format(
                        character_id=hapic_data.path.character_id, stuff_id=stuff.id
                    ),
                )
            )

        return Description(
            title=f"Choix de {stuff_properties.name}", items=parts, can_be_back_url=True
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetLookStuffModelModel)
    @hapic.output_body(Description)
    async def _describe_inventory_look_stuff(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        stuff = self._stuff_lib.get_stuff(hapic_data.path.stuff_id)
        actions = self._character_lib.get_on_stuff_actions(
            character_id=hapic_data.path.character_id,
            stuff_id=hapic_data.path.stuff_id,
            from_inventory_only=True,
        )
        text_lines = stuff.get_full_description(self._kernel)
        props = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff.stuff_id
        )

        if props.is_bag:
            text_lines.append(f"- Sac capacité de {props.clutter_capacity}l")

        for ability_id in props.abilities:
            ability_description = self._kernel.game.config.abilities[ability_id]
            text_lines.append(f" - Permet {ability_description.name}")

        if props.weapon:
            text_lines.append(f" - Est une arme")

        if props.shield:
            text_lines.append(f" - Est un bouclier")

        if props.armor:
            text_lines.append(f" - Est une armure")

        for skill_bonus_id in props.skills_bonus:
            skill_bonus_description = self._kernel.game.config.skills[skill_bonus_id]
            text_lines.append(f" - Compétence associé : {skill_bonus_description.name}")

        for bonus_string in props.bonuses_strings():
            text_lines.append(f" - Bonus : {bonus_string}")

        text_lines.append("")

        return Description(
            title=stuff.get_name_and_light_description(self._kernel),
            illustration_name=stuff.illustration,
            items=[Part(text=line) for line in text_lines]
            + [
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
    @hapic.input_path(GetLookInventoryResourceModel)
    @hapic.output_body(Description)
    async def _describe_inventory_look_resource(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        resource_description = self._kernel.game.config.resources[
            hapic_data.path.resource_id
        ]
        actions = self._character_lib.get_on_resource_actions(
            character_id=hapic_data.path.character_id,
            resource_id=hapic_data.path.resource_id,
            from_inventory_only=True,
        )
        carried = self._kernel.resource_lib.get_one_carried_by(
            character_id=hapic_data.path.character_id,
            resource_id=hapic_data.path.resource_id,
        )

        return Description(
            title=resource_description.name,  # TODO BS 2019-09-05: add quantity in name
            illustration_name=resource_description.illustration,
            items=[Part(text=carried.get_full_description(self._kernel))]
            + [
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                    classes=action.classes1,
                )
                for action in actions
            ],
            can_be_back_url=True,
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
        # FIXME : instanciate serializer once and for all
        input_ = serpyco.Serializer(
            action.input_model, type_encoders={Quantity: QuantityEncoder()}
        ).load(
            dict(request.query)
        )  # TODO perf
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)

        try:
            cost = action.get_cost(character_model, input_=input_)
            if cost is not None and character_model.action_points < cost:
                raise get_exception_for_not_enough_ap(character_model, cost)

            await action.check_request_is_possible(character_model, input_)
            return await action.perform(character_model, input_)
        except (ImpossibleAction, WrongInputError) as exc:
            return Description(
                title="Action impossible",
                quick_action_response=str(exc).replace("\n", " "),
                type_=DescriptionType.ERROR,
                items=[Part(text=line) for line in str(exc).split("\n")],
                illustration_name=getattr(exc, "illustration_name", None),
            )

    @hapic.with_api_doc()
    @hapic.input_path(WithStuffActionModel)
    @hapic.output_body(Description)
    async def with_stuff_action(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithStuffAction,
            self._action_factory.create_action(
                action_type, action_description_id=hapic_data.path.action_description_id
            ),
        )
        input_ = serpyco.Serializer(action.input_model).load(
            dict(request.query)
        )  # TODO perf
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)
        # TODO BS 2019-07-04: Check character owning ...
        stuff = self._kernel.stuff_lib.get_stuff(hapic_data.path.stuff_id)

        try:
            cost = action.get_cost(character_model, stuff, input_=input_)
            if cost is not None and character_model.action_points < cost:
                raise get_exception_for_not_enough_ap(character_model, cost)

            await action.check_request_is_possible(
                character=character_model, stuff=stuff, input_=input_
            )
            return await action.perform(
                character=character_model, stuff=stuff, input_=input_
            )
        except (ImpossibleAction, WrongInputError) as exc:
            return Description(
                title="Action impossible",
                quick_action_response=str(exc).replace("\n", " "),
                type_=DescriptionType.ERROR,
                items=[Part(text=line) for line in str(exc).split("\n")],
                illustration_name=getattr(exc, "illustration_name", None),
            )

    @hapic.with_api_doc()
    @hapic.input_path(WithBuildActionModel)
    @hapic.output_body(Description)
    async def with_build_action(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithBuildAction,
            self._action_factory.create_action(
                action_type, action_description_id=hapic_data.path.action_description_id
            ),
        )
        input_ = action.input_model_from_request(dict(request.query))
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)
        # TODO BS 2019-07-04: Check character can action on build...

        try:
            cost = action.get_cost(
                character_model, hapic_data.path.build_id, input_=input_
            )
            if cost is not None and character_model.action_points < cost:
                raise get_exception_for_not_enough_ap(character_model, cost)

            await action.check_request_is_possible(
                character=character_model,
                build_id=hapic_data.path.build_id,
                input_=input_,
            )
        except NotEnoughActionPoints as exc:
            raise get_exception_for_not_enough_ap(character_model, exc.cost)
        except (ImpossibleAction, WrongInputError) as exc:
            return Description(
                title="Action impossible",
                quick_action_response=str(exc).replace("\n", " "),
                type_=DescriptionType.ERROR,
                items=[Part(text=line) for line in str(exc).split("\n")],
                illustration_name=getattr(exc, "illustration_name", None),
                not_enough_ap=True,
            )

        # FIXME BS 2019-10-03: check_request_is_possible must be done everywhere
        #  in perform like in this action !
        try:
            return await action.perform(
                character=character_model,
                build_id=hapic_data.path.build_id,
                input_=input_,
            )
        except (ImpossibleAction, WrongInputError) as exc:
            return Description(
                title="Action impossible",
                quick_action_response=str(exc).replace("\n", " "),
                type_=DescriptionType.ERROR,
                items=[Part(text=line) for line in str(exc).split("\n")],
                illustration_name=getattr(exc, "illustration_name", None),
                is_quick_error=True,
            )

    @hapic.with_api_doc()
    @hapic.input_path(WithResourceActionModel)
    @hapic.output_body(Description)
    async def with_resource_action(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithResourceAction,
            self._action_factory.create_action(
                action_type, action_description_id=hapic_data.path.action_description_id
            ),
        )
        input_ = action.input_model_from_request(dict(request.query))
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)

        try:
            cost = action.get_cost(
                character_model, hapic_data.path.resource_id, input_=input_
            )
            if cost is not None and character_model.action_points < cost:
                raise get_exception_for_not_enough_ap(character_model, cost)

            await action.check_request_is_possible(
                character=character_model,
                resource_id=hapic_data.path.resource_id,
                input_=input_,
            )
            return await action.perform(
                character=character_model,
                resource_id=hapic_data.path.resource_id,
                input_=input_,
            )
        except (ImpossibleAction, WrongInputError) as exc:
            return Description(
                title="Action impossible",
                quick_action_response=str(exc).replace("\n", " "),
                type_=DescriptionType.ERROR,
                items=[Part(text=line) for line in str(exc).split("\n")],
                illustration_name=getattr(exc, "illustration_name", None),
            )

    @hapic.with_api_doc()
    @hapic.input_path(WithCharacterActionModel)
    @hapic.output_body(Description)
    async def with_character_action(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        action_type = hapic_data.path.action_type
        action = typing.cast(
            WithCharacterAction,
            self._action_factory.create_action(
                action_type, action_description_id=hapic_data.path.action_description_id
            ),
        )
        input_ = action.input_model_from_request(dict(request.query))
        character_model = self._kernel.character_lib.get(hapic_data.path.character_id)
        with_character_model = self._kernel.character_lib.get(
            hapic_data.path.with_character_id
        )

        try:
            cost = action.get_cost(character_model, with_character_model, input_=input_)
            if cost is not None and character_model.action_points < cost:
                raise get_exception_for_not_enough_ap(character_model, cost)

            await action.check_request_is_possible(
                character=character_model,
                with_character=with_character_model,
                input_=input_,
            )
            return await action.perform(
                character=character_model,
                with_character=with_character_model,
                input_=input_,
            )
        except ImpossibleAttack as exc:
            return Description(
                title="Action impossible",
                quick_action_response=str(exc).replace("\n", " "),
                type_=DescriptionType.ERROR,
                items=[Part(text=exc.msg)]
                + (
                    [Part(text=f"- {msg_line}") for msg_line in exc.msg_lines]
                    if exc.msg_lines
                    else []
                ),
            )
        except (ImpossibleAction, WrongInputError) as exc:
            return Description(
                title="Action impossible",
                quick_action_response=str(exc).replace("\n", " "),
                type_=DescriptionType.ERROR,
                items=[Part(text=line) for line in str(exc).split("\n")],
                illustration_name=getattr(exc, "illustration_name", None),
            )

    @hapic.with_api_doc()
    @hapic.input_query(CreateCharacterQueryModel)
    @hapic.output_body(Description)
    async def create_character_do(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        data = await request.json()
        skills: typing.Dict[str, float] = {}
        skills_total = 0.0

        if len(data["name"]) < 3 or len(data["name"]) > 21:
            raise UserDisplayError(
                f"Le nom du personnage doit faire entre 3 et 21 caractères"
            )

        if not self._kernel.character_lib.name_available(data["name"]):
            raise UserDisplayError(f"Le nom du personnage n'est pas disponible")

        for skill_id in base_skills + self._kernel.game.config.create_character_skills:
            value = float(data[f"skill__{skill_id}"])

            if value < 0.0:
                raise UserDisplayError("Valeur négative refusée")

            skills[skill_id] = value
            skills_total += value

        maximum_points = self._kernel.game.config.create_character_max_points
        if skills_total > maximum_points:
            raise UserDisplayError(
                f"Vous avez choisis {skills_total} points au total ({maximum_points} max)"
            )

        create_character_knowledges = (
            self._kernel.game.config.create_character_knowledges
        )
        knowledges = []
        if (
            create_character_knowledges
            and self._kernel.game.config.create_character_knowledges_count
        ):
            if (
                len(
                    [
                        k_id
                        for k_id in create_character_knowledges
                        if f"knowledge__{k_id}" in data
                        and data[f"knowledge__{k_id}"] == "on"
                    ]
                )
                > self._kernel.game.config.create_character_knowledges_count
            ):
                raise UserDisplayError(f"Vous avez choisis trop de connaissances")
            for knowledge_id in create_character_knowledges:
                if (
                    f"knowledge__{knowledge_id}" in data
                    and data[f"knowledge__{knowledge_id}"] == "on"
                ):
                    knowledges.append(knowledge_id)

        character_id = self._character_lib.create(
            data["name"],
            skills,
            knowledges,
            spawn_to=(
                hapic_data.query.spawn_to if hapic_data.query.spawn_to != -1 else None
            ),
        )
        character_doc = self._kernel.character_lib.get_document(character_id)
        account = self._kernel.account_lib.get_account_for_id(request["account_id"])
        account.current_character_id = character_id
        character_doc.account_id = account.id
        self._kernel.server_db_session.add(account)
        self._kernel.server_db_session.add(character_doc)
        self._kernel.server_db_session.commit()

        # Create Tracim account
        tracim_account = rrolling.tracim.Account(
            username=rrolling.tracim.Username(character_doc.name_slug),
            password=rrolling.tracim.Password(character_doc.tracim_password),
            email=rrolling.tracim.Email(account.email),
        )
        tracim_user_id = rrolling.tracim.Dealer(
            self._kernel.server_config.tracim_config
        ).ensure_account(tracim_account)
        character_doc.tracim_user_id = tracim_user_id

        # Create Tracim space and access
        space_name = self._kernel.character_lib.character_home_space_name(character_doc)
        tracim_home_space_id = rrolling.tracim.Dealer(
            self._kernel.server_config.tracim_config
        ).ensure_space(rrolling.tracim.SpaceName(space_name))
        character_doc.tracim_home_space_id = tracim_home_space_id

        rrolling.tracim.Dealer(
            self._kernel.server_config.tracim_config
        ).ensure_space_role(
            rrolling.tracim.SpaceId(tracim_home_space_id),
            rrolling.tracim.AccountId(character_doc.tracim_user_id),
            "reader",
        )

        for space_id, role in self._kernel.server_config.tracim_common_spaces:
            rrolling.tracim.Dealer(
                self._kernel.server_config.tracim_config
            ).ensure_space_role(
                rrolling.tracim.SpaceId(space_id),
                rrolling.tracim.AccountId(character_doc.tracim_user_id),
                role,
            )

        self._kernel.server_db_session.add(character_doc)
        self._kernel.server_db_session.commit()

        self._character_lib.add_event(
            character_doc.id,
            title=self._kernel.game.config.create_character_event_title,
            message=f"<p>{self._kernel.game.config.create_character_event_story_text}</p>",
        )

        spritesheet_filename = self._kernel.character_lib.spritesheet_filename(
            character_doc
        )
        await self._kernel.send_to_zone_sockets(
            character_doc.world_row_i,
            character_doc.world_col_i,
            event=WebSocketEvent(
                type=ZoneEventType.CHARACTER_ENTER_ZONE,
                world_row_i=character_doc.world_row_i,
                world_col_i=character_doc.world_col_i,
                data=CharacterEnterZoneData(
                    character_id=character_id,
                    zone_row_i=character_doc.zone_row_i,
                    zone_col_i=character_doc.zone_col_i,
                    spritesheet_filename=spritesheet_filename,
                ),
            ),
        )
        return Description(
            title="Pret a commencer l'aventure !",
            items=[Part(label="Continuer")],
            new_character_id=character_id,
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.input_query(GetCharacterQueryModel)
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(CharacterModelApi)
    async def get(self, request: Request, hapic_data: HapicData) -> CharacterModel:
        return self._character_lib.get(
            hapic_data.path.character_id,
            compute_unread_event=bool(hapic_data.query.compute_unread_event),
            compute_unread_zone_message=bool(hapic_data.query.compute_unread_event),
            compute_unread_conversation=bool(hapic_data.query.compute_unread_event),
            compute_unvote_affinity_relation=bool(
                hapic_data.query.compute_unread_event
            ),
            compute_unread_transactions=bool(hapic_data.query.compute_unread_event),
            compute_pending_actions=bool(hapic_data.query.compute_unread_event),
            dead=False,
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
        try:
            move_info = self._character_lib.get_move_to_zone_infos(
                hapic_data.path.character_id,
                world_row_i=hapic_data.path.world_row_i,
                world_col_i=hapic_data.path.world_col_i,
            )
        except (ImpossibleAction, WrongInputError) as exc:
            return Description(
                title="Effectuer un voyage ...",
                quick_action_response=str(exc).replace("\n", " "),
                type_=DescriptionType.ERROR,
                items=[Part(text=line) for line in str(exc).split("\n")],
                illustration_name=getattr(exc, "illustration_name", None),
            )

        buttons = [Part(label="Rester ici")]
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

        if move_info.followers_can:
            parts.append(
                Part(
                    text=f"{len(move_info.followers_can)} personnage(s) vous suivront dans ce déplacement"
                )
            )

        if move_info.followers_cannot:
            names = ", ".join([f.name for f in move_info.followers_cannot])
            parts.append(
                Part(
                    text=f"{len(move_info.followers_cannot)} personnage(s) ne pourront pas vous suivre dans ce déplacement: {names}"
                )
            )

        if move_info.can_move:
            buttons.insert(
                0,
                Part(label="Effectuer le voyage", is_link=True, form_action=travel_url),
            )
        else:
            for reason in move_info.cannot_move_reasons:
                parts.append(Part(text=reason))

        return Description(title="Effectuer un voyage ...", items=parts + buttons)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(MoveCharacterQueryModel)
    @hapic.handle_exception(CantMoveCharacter)
    @hapic.output_body(Description)
    async def describe_move(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        move_done = False
        character = self._character_lib.get(hapic_data.path.character_id)
        to_world_row = hapic_data.query.to_world_row
        to_world_col = hapic_data.query.to_world_col
        move_to_zone_type = self._kernel.world_map_source.geography.rows[to_world_row][
            to_world_col
        ]
        zone_properties = self._kernel.game.world_manager.get_zone_properties(
            move_to_zone_type
        )
        move_info = self._character_lib.get_move_to_zone_infos(
            hapic_data.path.character_id,
            world_row_i=to_world_row,
            world_col_i=to_world_col,
        )

        if move_info.can_move:
            messages = ["Le voyage c'est bien déroulé"]
            move_done = True
        else:
            messages = list(move_info.cannot_move_reasons)

        for character_ in (
            move_info.followers_can + move_info.followers_discreetly_can + [character]
        ):
            await self._kernel.send_to_zone_sockets(
                character_.world_row_i,
                character_.world_col_i,
                event=WebSocketEvent(
                    world_row_i=character_.world_row_i,
                    world_col_i=character_.world_col_i,
                    type=ZoneEventType.CHARACTER_EXIT_ZONE,
                    data=CharacterExitZoneData(character_id=character_.id),
                ),
            )

            character_doc = await self._character_lib.move(
                character_,
                to_world_row=hapic_data.query.to_world_row,
                to_world_col=hapic_data.query.to_world_col,
            )
            spritesheet_filename = self._kernel.character_lib.spritesheet_filename(
                character_doc
            )
            await self._kernel.send_to_zone_sockets(
                hapic_data.query.to_world_row,
                hapic_data.query.to_world_col,
                event=WebSocketEvent(
                    type=ZoneEventType.CHARACTER_ENTER_ZONE,
                    world_row_i=character_doc.world_row_i,
                    world_col_i=character_doc.world_col_i,
                    data=CharacterEnterZoneData(
                        character_id=character_.id,
                        zone_row_i=character_doc.zone_row_i,
                        zone_col_i=character_doc.zone_col_i,
                        spritesheet_filename=spritesheet_filename,
                    ),
                ),
            )
            await self._character_lib.reduce_action_points(
                character_.id, zone_properties.move_cost
            )

            if character_ != character:
                self._kernel.character_lib.add_event(
                    character_.id,
                    title=f"Vous avez suivis {character.name}",
                    message="",
                )
                # FIXME BS NOW: si connecté, event pour voyage !

            # If character own socket, consider it in new zone
            socket = self._kernel.server_zone_events_manager.get_character_socket(
                character_.id
            )
            if socket is not None:
                self._kernel.server_zone_events_manager.change_socket_zone_to(
                    socket, hapic_data.query.to_world_row, hapic_data.query.to_world_col
                )

        for character_ in (
            move_info.followers_cannot + move_info.followers_discreetly_cannot
        ):
            self._kernel.character_lib.add_event(
                character_.id,
                f"Vous n'avez pas pu suivre {character.name} (fatigue ou surcharge)",
                message="",
            )

        return Description(
            title="Effectuer un voyage ...",
            items=[Part(text=message) for message in messages],
            reload_zone=move_done,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(ZoneRequiredPlayerData)
    async def get_zone_data(
        self, request: Request, hapic_data: HapicData
    ) -> ZoneRequiredPlayerData:
        character = self._character_lib.get(hapic_data.path.character_id)
        inventory = self._character_lib.get_inventory(character)

        return ZoneRequiredPlayerData(
            weight_overcharge=inventory.over_weight,
            clutter_overcharge=inventory.over_clutter,
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(ListOfItemModel)
    async def get_resume_texts(
        self, request: Request, hapic_data: HapicData
    ) -> ListOfItemModel:
        return ListOfItemModel(
            self._kernel.character_lib.get_resume_text(hapic_data.path.character_id)
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
    async def get_post_mortem(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character_doc = self._kernel.character_lib.get_document(
            hapic_data.path.character_id, dead=True
        )
        return Description(
            title=f"{character_doc.name} est mort",
            items=[
                Part(
                    f"Ouvrir l'espace RP de {character_doc.name}",
                    form_action=f"/character/{character_doc.id}/open-rp",
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
        character_doc = self._kernel.character_lib.get_document(
            hapic_data.path.character_id
        )
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
    async def describe_turn(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        return Description(
            title=f"Ecoulement du temps",
            items=[
                Part(
                    # FIXME: to do ...
                    text=(
                        """TODO
                        """
                    )
                )
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def followed(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._character_lib.get(hapic_data.path.character_id)
        parts = []
        followed: CharacterModel
        for follow, followed in self._kernel.character_lib.get_followed(character.id):
            here = (
                followed.world_row_i == character.world_row_i
                and followed.world_col_i == character.world_col_i
            )
            parts.append(
                Part(
                    is_link=True,
                    label=f"{followed.name}"
                    + (" (n'est pas dans cette zone)" if not here else ""),
                    form_action=DESCRIBE_LOOK_AT_CHARACTER_URL.format(
                        character_id=character.id, with_character_id=followed.id
                    ),
                )
            )
        return Description(
            title=f"Personnages suivis",
            items=parts,
            footer_links=[
                Part(
                    label="Fiche personnage",
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/card",
                )
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def describe_around_items(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        character_actions = list(
            self._kernel.character_lib.get_on_place_stuff_actions(character)
        ) + list(self._kernel.character_lib.get_on_place_resource_actions(character))
        parts = [
            Part(
                text=action.get_as_str(),
                form_action=action.link,
                is_link=True,
                link_group_name=action.group_name,
            )
            for action in character_actions
        ]

        return Description(
            title=f"Objet et ressources autour", items=parts, can_be_back_url=True
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def describe_around_builds(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        character_actions = self._kernel.character_lib.get_on_place_build_actions(
            character
        )
        parts = [
            Part(
                text=action.get_as_str(),
                form_action=action.link,
                is_link=True,
                link_group_name=action.group_name,
            )
            for action in character_actions
        ]

        return Description(title=f"Bâtiments autour", items=parts, can_be_back_url=True)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def describe_around_characters(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        character_actions = self._kernel.character_lib.get_on_place_character_actions(
            character
        )
        parts = [
            Part(
                text=action.get_as_str(),
                form_action=action.link,
                is_link=True,
                link_group_name=action.group_name,
            )
            for action in character_actions
        ]

        return Description(
            title=f"Personnages autour", items=parts, can_be_back_url=True
        )

    @hapic.with_api_doc()
    @hapic.input_path(DoorPathModel)
    @hapic.output_body(Description)
    async def door(self, request: Request, hapic_data: HapicData) -> Description:
        character_id = hapic_data.path.character_id
        character_doc = self._kernel.character_lib.get_document(character_id)
        door_id = hapic_data.path.door_id
        relation: typing.Optional[DoorDocument] = None
        relation_mode: typing.Optional[str] = None
        access_locked = self._kernel.door_lib.is_access_locked_for(
            character_id=character_id, build_id=door_id
        )
        enabled_affinity_ids = []
        all_affinities = list(
            set(
                self._kernel.affinity_lib.get_accepted_affinities_docs(
                    character_id=character_id
                )
                + self._kernel.affinity_lib.get_affinities_without_relations(
                    character_id=character_id,
                    with_alive_character_in_world_row_i=character_doc.world_row_i,
                    with_alive_character_in_world_col_i=character_doc.world_col_i,
                )
            )
        )

        door_rule_changed = False
        new_affinity_ids = None
        deleted = False
        # Proceed eventual mode changes
        if request.query.get("mode"):
            new_affinity_ids = []
            new_mode = list(DOOR_MODE_LABELS.keys())[
                list(DOOR_MODE_LABELS.values()).index(request.query["mode"])
            ]
            if new_mode is None:
                self._kernel.door_lib.delete(
                    character_id=character_id,
                    build_id=door_id,
                )
                deleted = True
            else:
                self._kernel.door_lib.update(
                    character_id=character_id,
                    build_id=door_id,
                    new_mode=new_mode,
                )
            door_rule_changed = True

        # Proceed eventual affinity ids changes
        for query_key in request.query.keys():
            if query_key.startswith("affinity_"):
                new_affinity_ids.append(int(query_key.replace("affinity_", "")))

        if not deleted and new_affinity_ids is not None:
            self._kernel.door_lib.update(
                character_id=character_id,
                build_id=door_id,
                new_affinity_ids=new_affinity_ids,
            )
            door_rule_changed = True

        if door_rule_changed:
            await self._kernel.door_lib.trigger_character_change_rule(
                character_id=character_id, build_id=door_id
            )

        # Prepare display of page
        try:
            relation = self._kernel.door_lib.get_character_with_door_relation(
                character_id=character_id, build_id=door_id
            )
            relation_mode = relation.mode
            enabled_affinity_ids = json.loads(relation.affinity_ids)
            all_affinities += self._kernel.affinity_lib.get_multiple(
                enabled_affinity_ids
            )
            all_affinities = list(set(all_affinities))
        except NoResultFound:
            pass

        description_parts = []
        if access_locked:
            description_parts.append(
                Part(
                    text=self._kernel.door_lib.get_is_access_locked_for_description(
                        character_id=character_id, build_id=door_id
                    )
                )
            )
            if relation is not None:
                description_parts.append(
                    Part(
                        text=(
                            "Si dans le futur cette porte ne vous es plus fermé, vous appliquerez "
                            "le comportement décrit ci-dessous :"
                        )
                    )
                )

        description_parts.append(
            Part(
                text=self._kernel.door_lib.get_relation_description(
                    character_id=character_id, build_id=door_id
                )
            )
        )

        return Description(
            title=f"Gestion de porte",
            items=description_parts
            + [
                Part(
                    is_form=True,
                    form_action=f"/character/{character_id}/door/{door_id}",
                    form_values_in_query=True,
                    items=[
                        Part(text="Votre comportement avec cette porte :"),
                        Part(
                            label="Comportement à l'égard de cette porte",
                            choices=DOOR_MODE_LABELS.values(),
                            name="mode",
                            value=DOOR_MODE_LABELS[relation_mode],
                        ),
                        Part(
                            text=(
                                f"Si '{DOOR_MODE_LABELS[DOOR_MODE__CLOSED_EXCEPT_FOR]}' choisi, "
                                "laisser passer les membres de quelles affinités ?"
                            )
                        ),
                    ]
                    + (
                        [
                            Part(
                                label=affinity.name,
                                name=f"affinity_{affinity.id}",
                                is_checkbox=True,
                                value="on",
                                checked=affinity.id in enabled_affinity_ids,
                            )
                            for affinity in all_affinities
                        ]
                        if all_affinities
                        else [Part(text=" - Aucune affinité en présence")]
                    ),
                )
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(ChooseAvatarQuery)
    @hapic.output_body(Description)
    async def _choose_avatar(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        if character.avatar_uuid is not None:
            return Description(
                title="Choix d'avatar",
                items=[Part(text=f"{character.name} possède déjà un avatar")],
            )

        avatars_count = len(self._kernel.avatars_paths)
        avatar_index = random.randrange(start=0, stop=avatars_count)

        if hapic_data.query.choose:
            self._kernel.character_lib.setup_avatar_from_pool(
                character.id, avatar_index=hapic_data.query.choose
            )
            return Description(reload_zone=True)

        return Description(
            title=f"Choix de l'avatar de {character.name}",
            illustration_name=f"pool_avatar__{avatar_index}.png",
            items=[
                Part(
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/card/choose-avatar?choose={avatar_index}",
                    label="Choisir cet avatar",
                    classes=["primary"],
                ),
                Part(
                    is_link=True,
                    form_action=f"/_describe/character/{character.id}/card/choose-avatar",
                    label="Afficher un nouvel avatar",
                    classes=["secondary"],
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(ExplodeTakeQuery)
    @hapic.output_body(Description)
    async def send_around(self, request: Request, hapic_data: HapicData) -> Response:
        character_id = hapic_data.path.character_id
        character = self._kernel.character_lib.get(character_id)
        character_socket = self._kernel.server_zone_events_manager.get_character_socket(
            character_id
        )
        character_socket is not None
        await self._kernel.server_zone_events_manager._event_processor_factory.get_processor(
            zone_event_type=ZoneEventType.CLIENT_REQUIRE_AROUND
        ).process(
            row_i=character.zone_row_i,
            col_i=character.zone_col_i,
            event=WebSocketEvent(
                type=ZoneEventType.CLIENT_REQUIRE_AROUND,
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                data=ClientRequireAroundData(
                    zone_row_i=character.zone_row_i,
                    zone_col_i=character.zone_col_i,
                    character_id=character_id,
                    explode_take=bool(hapic_data.query.explode_take),
                ),
            ),
            sender_socket=character_socket,
        )
        return Description(title="no content", quick_action_response="")

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    async def open_rp(self, request: Request, hapic_data: HapicData) -> Response:
        character_id = hapic_data.path.character_id
        tracim_account = self._kernel.character_lib.get_tracim_account(character_id)

        description = Description(
            title="Open RP",
            open_new_tab=self._kernel.server_config.rp_url,
        )

        session_key = rrolling.tracim.Dealer(
            self._kernel.server_config.tracim_config
        ).get_new_session_key(tracim_account)

        response = web.Response(
            status=200,
            body=Description.serializer().dump_json(description),
            content_type="application/json",
        )
        response.set_cookie(
            "session_key",
            session_key,
            # expires="Sat, 12-Nov-2022 21:45:47 GMT",
            httponly=True,
            path="/",
            samesite="Lax",
        )
        return response

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    async def unread_messages_count(
        self, request: Request, hapic_data: HapicData
    ) -> Response:
        character_id = hapic_data.path.character_id
        character_doc = self._kernel.character_lib.get_document(character_id)
        tracim_account = self._kernel.character_lib.get_tracim_account(character_id)
        count = rrolling.tracim.Dealer(
            self._kernel.server_config.tracim_config
        ).get_unread_messages_count(
            tracim_account,
            rrolling.tracim.AccountId(character_doc.tracim_user_id),
        )

        response = web.Response(
            status=200,
            body=str(count),
        )

        return response

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(SetupCharacterSpritesheetQuery)
    @hapic.output_body(Description)
    async def spritesheet_setup(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character_id = hapic_data.path.character_id
        character_doc = self._kernel.character_lib.get_document(character_id)
        assert character_doc.spritesheet_identifiers is None
        layers = []
        character_identifiers = DEFAULT_CHARACTER_SPRITESHEETS_IDENTIFIERS
        data = {}
        body_type = None

        try:
            data = await request.json()
            pass
        except json.JSONDecodeError:
            pass

        parts = [Part("Choisissez parmi les possibilités ci-dessous")]
        form_part = Part(
            is_form=True,
            form_action=f"/character/{character_id}/spritesheet-setup",
            submit_label="Aperçu",
        )
        parts.append(form_part)

        for create_character in self._kernel.game.spritesheets.create_character:
            form_part.items.append(Part(""))
            form_part.items.append(Part(create_character.name))
            if create_character.group_by_variant:
                values = create_character.values(
                    self._kernel.character_spritesheets_identifiers
                )

                if create_character.permit_none:
                    values = dict([("NONE", "Aucun(e)")] + list(values.items()))

                if create_character.take_variant_from is None:
                    variants = create_character.variants(
                        self._kernel.character_spritesheets_identifiers
                    )
                    if create_character.allowed_variants is not None:
                        variants = [
                            variant
                            for variant in variants
                            if variant in create_character.allowed_variants
                        ]

                    variant_value = data.get(
                        f"{create_character.name}_variant",
                        create_character.default_variant,
                    )
                    form_part.items.append(Part("Nuance de couleur"))
                    form_part.items.append(
                        Part(
                            label="Nuance de couleur",
                            choices=variants,
                            name=f"{create_character.name}_variant",
                            value=variant_value,
                        )
                    )
                else:
                    variant_value = data.get(
                        f"{create_character.take_variant_from}_variant",
                        create_character.default_variant,
                    )

                if create_character.take_variant_from is None:
                    form_part.items.append(Part("Type"))
                value = data.get(
                    create_character.name, values[create_character.default_value]
                )
                form_part.items.append(
                    Part(
                        label=create_character.name,
                        choices=values.values(),
                        name=create_character.name,
                        value=value,
                        dont_wrap=create_character.dont_wrap,
                    )
                )

                if variant_value and value and value != "Aucun(e)":
                    identifier = list(values.keys())[list(values.values()).index(value)]
                    layers.append(f"{identifier}({variant_value})")

                    if create_character.extract_body_type_from is not None:
                        body_type = identifier.split("::")[
                            create_character.extract_body_type_from
                        ]

        if layers:
            character_identifiers = " ".join(layers)

        parts.append(
            Part(
                is_link=True,
                label="Valider définitivement",
                form_action=f"/character/{character_id}/spritesheet-setup?validate={urllib.parse.quote(character_identifiers)}",
            )
        )

        reload_zone = False
        if identifiers := hapic_data.query.validate:
            character_doc.spritesheet_identifiers = identifiers
            character_doc.spritesheet_body_type = body_type
            character_doc.spritesheet_set = True
            self._kernel.server_db_session.add(character_doc)
            self._kernel.server_db_session.commit()
            reload_zone = True

        illustration_name = self._kernel.spritesheet_illustration(
            character_identifiers,
        ).name
        return Description(
            title="Apparence du personnage",
            illustration_name=illustration_name,
            items=parts,
            force_tight=True,
            reload_zone=reload_zone,
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/_describe/character/create", self._describe_create_character),
                web.post(
                    "/_describe/character/create", self._describe_create_character
                ),
                web.get(
                    "/_describe/character/{character_id}/card",
                    self._describe_character_card,
                ),
                web.post(
                    "/_describe/character/{character_id}/card",
                    self._describe_character_card,
                ),
                web.post(
                    "/_describe/character/{character_id}/card/choose-avatar",
                    self._choose_avatar,
                ),
                web.post(
                    "/character/{character_id}/card/{with_character_id}",
                    self.with_character_card,
                ),
                web.get(
                    "/_describe/character/{character_id}/inventory",
                    self._describe_inventory,
                ),
                web.post(
                    "/_describe/character/{character_id}/inventory",
                    self._describe_inventory,
                ),
                web.get(
                    "/character/{character_id}/inventory-data",
                    self._get_inventory_data,
                ),
                web.post(
                    "/_describe/character/{character_id}/inventory/choose-between-stuff/{stuff_id}",
                    self._choose_between_stuff,
                ),
                web.post(
                    "/_describe/character/{character_id}/inventory/shared-with",
                    self._describe_shared_with_inventory,
                ),
                web.post(
                    "/character/{character_id}/inventory/{with_character_id}",
                    self.with_inventory,
                ),
                web.get(
                    "/_describe/character/{character_id}/on_place_actions",
                    self._describe_on_place_actions,
                ),
                web.post(
                    "/_describe/character/{character_id}/on_place_actions",
                    self._describe_on_place_actions,
                ),
                web.post(
                    "/_describe/character/{character_id}/main_actions",
                    self._main_actions,
                ),
                web.post(
                    "/_describe/character/{character_id}/pending_actions",
                    self.pending_actions,
                ),
                web.post(
                    "/_describe/character/{character_id}/pending_actions/{pending_action_id}",
                    self.pending_action,
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
                web.get(
                    "/_describe/character/{character_id}/events", self._describe_events
                ),
                web.post(
                    "/_describe/character/{character_id}/events", self._describe_events
                ),
                web.post(
                    "/_describe/character/{character_id}/story", self._describe_story
                ),
                web.post("/_describe/character/create/do", self.create_character_do),
                web.get("/character/{character_id}", self.get),
                # web.get(
                #     "/_describe/character/{character_id}/inventory",
                #     self._describe_inventory,
                # ),
                web.post(
                    "/_describe/character/{character_id}/shared-inventory",
                    self._describe_shared_inventory,
                ),
                web.post(
                    "/_describe/character/{character_id}/shared-inventory/add",
                    self._describe_add_to_shared_inventory,
                ),
                web.post(
                    "/_describe/character/{character_id}/pick_from_inventory",
                    self.pick_from_inventory,
                ),
                web.post(
                    "/_describe/character/{character_id}/move", self.describe_move
                ),
                web.post(DESCRIBE_LOOK_AT_STUFF_URL, self._describe_look_stuff),
                web.post(DESCRIBE_LOOK_AT_RESOURCE_URL, self._describe_look_resource),
                web.post(DESCRIBE_LOOK_AT_CHARACTER_URL, self._describe_look_character),
                web.post(
                    DESCRIBE_INVENTORY_STUFF_ACTION, self._describe_inventory_look_stuff
                ),
                web.post(
                    DESCRIBE_INVENTORY_RESOURCE_ACTION,
                    self._describe_inventory_look_resource,
                ),
                web.post(CHARACTER_ACTION, self.character_action),
                web.post(WITH_STUFF_ACTION, self.with_stuff_action),
                web.post(WITH_BUILD_ACTION, self.with_build_action),
                web.post(WITH_RESOURCE_ACTION, self.with_resource_action),
                web.post(WITH_CHARACTER_ACTION, self.with_character_action),
                web.get("/character/{character_id}/zone_data", self.get_zone_data),
                web.get(
                    "/character/{character_id}/resume_texts", self.get_resume_texts
                ),
                web.get("/character/{character_id}/dead", self.is_dead),
                web.post("/character/{character_id}/post_mortem", self.get_post_mortem),
                web.post("/character/{character_id}/AP", self.describe_ap),
                web.post("/character/{character_id}/turn", self.describe_turn),
                web.post(
                    "/character/{character_id}/skills_and_knowledge",
                    self.skills_and_knowledge,
                ),
                web.post("/character/{character_id}/followed", self.followed),
                web.post(
                    "/character/{character_id}/describe_around_items",
                    self.describe_around_items,
                ),
                web.post(
                    "/character/{character_id}/describe_around_characters",
                    self.describe_around_characters,
                ),
                web.post(
                    "/character/{character_id}/describe_around_builds",
                    self.describe_around_builds,
                ),
                web.post("/character/{character_id}/door/{door_id}", self.door),
                web.post("/character/{character_id}/send-around", self.send_around),
                web.post("/character/{character_id}/open-rp", self.open_rp),
                web.get("/character/{character_id}/open-rp", self.open_rp),
                web.post(
                    "/character/{character_id}/spritesheet-setup",
                    self.spritesheet_setup,
                ),
                web.get(
                    "/character/{character_id}/unread-messages-count",
                    self.unread_messages_count,
                ),
            ]
        )
