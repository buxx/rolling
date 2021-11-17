# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import ActionDescriptionModel
from rolling.action.base import CharacterAction
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_with_resource_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.action.utils import ConfirmModel
from rolling.action.utils import check_common_is_possible
from rolling.action.utils import fill_base_action_properties
from rolling.exception import ImpossibleAction
from rolling.exception import RollingError
from rolling.exception import WrongInputError
from rolling.model.skill import DEFAULT_MAXIMUM_SKILL
from rolling.rolling_types import ActionType
from rolling.server.controller.url import DESCRIBE_LOOK_AT_STUFF_URL
from rolling.server.link import CharacterActionLink
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


@dataclasses.dataclass
class CraftInput:
    quantity: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )


class BaseCraftStuff:
    @classmethod
    def _get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        for require in action_config_raw["require"]:
            if "resource" not in require and "stuff" not in require:
                raise RollingError(
                    "Misconfiguration for action "
                    "CraftStuffWithResourceAction/CraftStuffWithStuffAction (require "
                    "must contain stuff or resource key"
                )

        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )
        properties.update(
            {
                "produce": action_config_raw["produce"],
                "require": action_config_raw["require"],
            }
        )
        return properties

    async def _perform(
        self,
        character: "CharacterModel",
        description: ActionDescriptionModel,
        input_: CraftInput,
        cost: float,
        dry_run: bool = True,
    ) -> None:
        if character.action_points < cost:
            raise ImpossibleAction(
                f"{character.name} no possède pas assez de points d'actions "
                f"({round(cost, 2)} nécessaires)"
            )

        carried_resources = self._kernel.resource_lib.get_carried_by(character.id)
        carried_stuffs = self._kernel.stuff_lib.get_carried_by(character.id)

        for require in description.properties["require"]:
            if "stuff" in require:
                required_quantity = input_.quantity * int(require["quantity"])
                stuff_id = require["stuff"]
                stuff_properties = (
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
                )
                carried_stuffs = [c for c in carried_stuffs if c.stuff_id == stuff_id]
                owned_quantity = len(carried_stuffs)

                if owned_quantity < required_quantity:
                    raise ImpossibleAction(
                        f"Vous ne possédez pas assez de {stuff_properties.name}: {required_quantity} nécessaire(s)"
                    )

                if not dry_run:
                    for i in range(required_quantity):
                        stuff_to_destroy = carried_stuffs[i]
                        self._kernel.stuff_lib.destroy(stuff_to_destroy.id)

            elif "resource" in require:
                required_quantity = input_.quantity * require["quantity"]
                resource_id = require["resource"]
                resource_properties = self._kernel.game.config.resources[resource_id]
                try:
                    carried_resource = next(
                        (c for c in carried_resources if c.id == resource_id)
                    )
                except StopIteration:
                    raise WrongInputError(
                        f"Vous ne possédez pas de {resource_properties.name}"
                    )
                if carried_resource.quantity < required_quantity:
                    missing_quantity_str = quantity_to_str(
                        kernel=self._kernel,
                        quantity=(required_quantity - carried_resource.quantity),
                        unit=carried_resource.unit,
                    )
                    raise ImpossibleAction(
                        f"Vous ne possédez pas assez de {carried_resource.name}: {missing_quantity_str} de plus nécessaire(s)"
                    )

                if not dry_run:
                    self._kernel.resource_lib.reduce_carried_by(
                        character_id=character.id,
                        resource_id=resource_id,
                        quantity=required_quantity,
                    )

        if dry_run:
            return

        for produce in description.properties["produce"]:
            stuff_id = produce["stuff"]
            quantity = produce["quantity"]
            stuff_properties = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
            )

            for i in range(int(quantity)):
                stuff_doc = (
                    self._kernel.stuff_lib.create_document_from_stuff_properties(
                        properties=stuff_properties,
                        world_row_i=character.world_row_i,
                        world_col_i=character.world_col_i,
                        zone_row_i=character.zone_row_i,
                        zone_col_i=character.zone_col_i,
                    )
                )
                self._kernel.stuff_lib.add_stuff(stuff_doc, commit=False)
                self._kernel.stuff_lib.set_carried_by__from_doc(
                    stuff_doc, character_id=character.id, commit=False
                )
        await self._kernel.character_lib.reduce_action_points(
            character_id=character.id, cost=cost, commit=False
        )
        self._kernel.server_db_session.commit()


class CraftStuffWithResourceAction(WithResourceAction, BaseCraftStuff):
    input_model = CraftInput
    input_model_serializer = serpyco.Serializer(CraftInput)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return cls._get_properties_from_config(game_config, action_config_raw)

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        for require in self._description.properties["require"]:
            if "resource" in require and resource_id in require["resource"]:
                return

        raise ImpossibleAction("non concerné")

    async def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: CraftInput
    ) -> None:
        self.check_is_possible(character, resource_id=resource_id)
        check_common_is_possible(
            kernel=self._kernel, description=self._description, character=character
        )
        if input_.quantity is not None:
            await self._perform(
                character,
                description=self._description,
                input_=input_,
                cost=self.get_cost(character, resource_id=resource_id, input_=input_),
                dry_run=True,
            )

    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        try:
            self.check_is_possible(character, resource_id)
        except ImpossibleAction:
            return []

        return [
            CharacterActionLink(
                name=self._description.name,
                link=get_with_resource_action_url(
                    character_id=character.id,
                    action_type=ActionType.CRAFT_STUFF_WITH_RESOURCE,
                    action_description_id=self._description.id,
                    resource_id=resource_id,
                    query_params={},
                ),
                cost=self.get_cost(character, resource_id),
                category="Artisanat",
            )
        ]

    def get_cost(
        self,
        character: "CharacterModel",
        resource_id: str,
        input_: typing.Optional[CraftInput] = None,
    ) -> typing.Optional[float]:
        bonus = character.get_skill_value("intelligence") + character.get_skill_value(
            "crafts"
        )
        base_cost = max(
            self._description.base_cost / 2, self._description.base_cost - bonus
        )
        if input_ and input_.quantity:
            return base_cost * input_.quantity
        return base_cost

    async def perform(
        self, character: "CharacterModel", resource_id: str, input_: CraftInput
    ) -> Description:
        if input_.quantity is None:
            return Description(
                title=self._description.name,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_resource_action_url(
                            character_id=character.id,
                            action_type=ActionType.CRAFT_STUFF_WITH_RESOURCE,
                            resource_id=resource_id,
                            query_params=self.input_model_serializer.dump(input_),
                            action_description_id=self._description.id,
                        ),
                        items=[
                            Part(
                                label=f"Quelle quantité ?",
                                type_=Type.NUMBER,
                                name="quantity",
                            )
                        ],
                    )
                ],
            )

        cost = self.get_cost(character, resource_id=resource_id, input_=input_)
        await self._perform(
            character,
            description=self._description,
            input_=input_,
            cost=cost,
            dry_run=True,
        )
        await self._perform(
            character,
            description=self._description,
            input_=input_,
            cost=cost,
            dry_run=False,
        )
        return Description(
            title="Action effectué avec succès",
            back_url=f"/_describe/character/{character.id}/on_place_actions",
        )


class CraftStuffWithStuffAction(WithStuffAction, BaseCraftStuff):
    input_model = CraftInput
    input_model_serializer = serpyco.Serializer(CraftInput)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return cls._get_properties_from_config(game_config, action_config_raw)

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        # Consider action ca be possible (displayed in interface) if at least one of required stuff
        # is owned by character
        carried = self._kernel.stuff_lib.get_carried_by(character.id)
        carried_stuff_ids = [r.stuff_id for r in carried]

        for require in self._description.properties["require"]:
            if "stuff" in require and require["stuff"] in carried_stuff_ids:
                return

        raise ImpossibleAction("Aucune resource requise n'est possédé")

    def get_cost(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: typing.Optional[typing.Any] = None,
    ) -> typing.Optional[float]:
        bonus = character.get_skill_value("intelligence") + character.get_skill_value(
            "crafts"
        )
        base_cost = max(
            self._description.base_cost / 2, self._description.base_cost - bonus
        )
        if input_ and input_.quantity:
            return base_cost * input_.quantity
        return base_cost

    async def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: CraftInput
    ) -> None:
        self.check_is_possible(character, stuff=stuff)
        check_common_is_possible(
            kernel=self._kernel, description=self._description, character=character
        )
        if input_.quantity is not None:
            cost = self.get_cost(character, stuff=stuff, input_=input_)
            await self._perform(
                character,
                description=self._description,
                input_=input_,
                cost=cost,
                dry_run=True,
            )

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        try:
            self.check_is_possible(character, stuff)
        except ImpossibleAction:
            return []

        return [
            # FIXME BS NOW: all CharacterActionLink must generate a can_be_back_url=True
            CharacterActionLink(
                name=self._description.name,
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.CRAFT_STUFF_WITH_STUFF,
                    action_description_id=self._description.id,
                    stuff_id=stuff.id,
                    query_params={},
                ),
                cost=self.get_cost(character, stuff),
                category="Artisanat",
            )
        ]

    async def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: CraftInput
    ) -> Description:
        if input_.quantity is None:
            return Description(
                title=self._description.name,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_stuff_action_url(
                            character_id=character.id,
                            action_type=ActionType.CRAFT_STUFF_WITH_STUFF,
                            stuff_id=stuff.id,
                            query_params=self.input_model_serializer.dump(input_),
                            action_description_id=self._description.id,
                        ),
                        items=[
                            Part(
                                label=f"Quelle quantité ?",
                                type_=Type.NUMBER,
                                name="quantity",
                            )
                        ],
                    )
                ],
            )

        cost = self.get_cost(character, stuff=stuff, input_=input_)
        await self._perform(
            character,
            description=self._description,
            input_=input_,
            cost=cost,
            dry_run=True,
        )
        await self._perform(
            character,
            description=self._description,
            input_=input_,
            cost=cost,
            dry_run=False,
        )
        return Description(
            title="Action effectué avec succès",
            back_url=f"/_describe/character/{character.id}/on_place_actions",
        )


@dataclasses.dataclass
class BeginStuffModel(ConfirmModel):
    description: typing.Optional[str] = None


class BeginStuffConstructionAction(CharacterAction):
    input_model = BeginStuffModel
    input_model_serializer = serpyco.Serializer(BeginStuffModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        for consume in action_config_raw["consume"]:
            if "resource" not in consume and "stuff" not in consume:
                raise RollingError(f"Action config is not correct: {action_config_raw}")

        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )
        properties["produce_stuff_id"] = action_config_raw["produce_stuff_id"]
        properties["consume"] = action_config_raw["consume"]
        properties["craft_ap"] = action_config_raw["craft_ap"]
        properties["default_description"] = action_config_raw.get(
            "default_description", ""
        )
        properties["link_group_name"] = action_config_raw.get("link_group_name", None)
        return properties

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass  # Always accept to display this action

    async def check_request_is_possible(
        self, character: "CharacterModel", input_: BeginStuffModel
    ) -> None:
        if input_.confirm:
            self.check_is_possible(character)
            stuff_description = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    self.description.properties["produce_stuff_id"]
                )
            )
            check_common_is_possible(
                self._kernel,
                description=self._description,
                character=character,
                illustration_name=stuff_description.illustration,
            )

            cost = self.get_cost(character)
            if character.action_points < cost:
                raise ImpossibleAction(
                    f"{character.name} no possède pas assez de points d'actions "
                    f"({round(cost, 2)} nécessaires)"
                )

            for consume in self._description.properties["consume"]:
                if "resource" in consume:
                    resource_id = consume["resource"]
                    resource_description = self._kernel.game.config.resources[
                        resource_id
                    ]
                    quantity = consume["quantity"]
                    quantity_str = quantity_to_str(
                        quantity, resource_description.unit, self._kernel
                    )
                    if not self._kernel.resource_lib.have_resource(
                        character_id=character.id,
                        resource_id=resource_id,
                        quantity=quantity,
                    ):
                        resource_description = self._kernel.game.config.resources[
                            resource_id
                        ]
                        raise ImpossibleAction(
                            f"Vous ne possédez pas assez de {resource_description.name}: {quantity_str} nécessaire(s)"
                        )

                elif "stuff" in consume:
                    stuff_id = consume["stuff"]
                    quantity = consume["quantity"]
                    if (
                        self._kernel.stuff_lib.get_stuff_count(
                            character_id=character.id, stuff_id=stuff_id
                        )
                        < quantity
                    ):
                        stuff_properties = (
                            self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                                stuff_id
                            )
                        )
                        raise ImpossibleAction(
                            f"Vous ne possédez pas assez de {stuff_properties.name}: {quantity} nécessaire(s)"
                        )

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name=f"{self._description.name}",
                link=get_character_action_url(
                    character_id=character.id,
                    action_type=ActionType.BEGIN_STUFF_CONSTRUCTION,
                    action_description_id=self._description.id,
                    query_params={},
                ),
                group_name=self._description.properties["link_group_name"],
                category="Artisanat",
            )
        ]

    async def perform(
        self, character: "CharacterModel", input_: BeginStuffModel
    ) -> Description:
        require_txts = []
        for consume in self._description.properties["consume"]:
            if "resource" in consume:
                resource_id = consume["resource"]
                resource_description = self._kernel.game.config.resources[resource_id]
                quantity_str = quantity_to_str(
                    consume["quantity"], resource_description.unit, self._kernel
                )
                require_txts.append(f" - {quantity_str} de {resource_description.name}")

            elif "stuff" in consume:
                stuff_id = consume["stuff"]
                stuff_properties = (
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
                )
                require_txts.append(
                    f" - {consume['quantity']} de {stuff_properties.name}"
                )

        if not input_.confirm:
            stuff_description = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    self.description.properties["produce_stuff_id"]
                )
            )
            start_cost = self.get_cost(character, input_=input_)
            craft_ap_cost = self.description.properties["craft_ap"]
            items = [
                Part(
                    text=f"Temps de travail nécessaire : {start_cost} + {craft_ap_cost} points d'actions"
                ),
                Part(text=""),
                Part(text="Nécessite : "),
            ]

            for require_txt in require_txts:
                items.append(Part(text=require_txt))

            items.append(
                Part(
                    label=f"Commencer le travail ({start_cost} points d'actions)",
                    is_link=True,
                    form_action=get_character_action_url(
                        character_id=character.id,
                        action_type=ActionType.BEGIN_STUFF_CONSTRUCTION,
                        action_description_id=self._description.id,
                        query_params={"confirm": 1},
                    ),
                )
            )

            return Description(
                title=f"Commencer {stuff_description.name}",
                items=items,
                illustration_name=stuff_description.illustration,
            )

        if not input_.description:
            return Description(
                title=f"Commencer {self._description.name}",
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.BEGIN_STUFF_CONSTRUCTION,
                            query_params={"confirm": 1},
                            action_description_id=self._description.id,
                        ),
                        items=[Part(text="Consommera :")]
                        + [Part(text=txt) for txt in require_txts]
                        + [
                            Part(
                                label=f"Vous pouvez fournir une description de l'objet",
                                type_=Type.STRING,
                                name="description",
                                default_value=self._description.properties[
                                    "default_description"
                                ],
                            )
                        ],
                    )
                ],
            )

        for consume in self._description.properties["consume"]:
            if "resource" in consume:
                resource_id = consume["resource"]
                self._kernel.resource_lib.reduce_carried_by(
                    character.id,
                    resource_id=resource_id,
                    quantity=consume["quantity"],
                    commit=False,
                )

            elif "stuff" in consume:
                stuff_id = consume["stuff"]
                carried_stuffs = self._kernel.stuff_lib.get_carried_by(
                    character.id, stuff_id=stuff_id
                )
                for i in range(consume["quantity"]):
                    self._kernel.stuff_lib.destroy(carried_stuffs[i].id, commit=False)

        stuff_id = self._description.properties["produce_stuff_id"]
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff_id
        )
        stuff_doc = self._kernel.stuff_lib.create_document_from_stuff_properties(
            properties=stuff_properties,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        )
        stuff_doc.description = input_.description or ""
        stuff_doc.carried_by_id = character.id
        stuff_doc.ap_spent = 0.0
        stuff_doc.ap_required = self._description.properties["craft_ap"]
        stuff_doc.under_construction = True
        self._kernel.stuff_lib.add_stuff(stuff_doc, commit=False)
        await self._kernel.character_lib.reduce_action_points(
            character.id, cost=self.get_cost(character), commit=False
        )
        self._kernel.server_db_session.commit()

        return Description(
            title=f"{stuff_properties.name} commencé",
            footer_links=[
                Part(
                    is_link=True,
                    label="Voir l'objet commencé",
                    form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=stuff_doc.id
                    ),
                    classes=["primary"],
                )
            ],
            back_url=f"/_describe/character/{character.id}/on_place_actions",
        )


@dataclasses.dataclass
class ContinueStuffModel:
    ap: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


class ContinueStuffConstructionAction(WithStuffAction):
    input_model = ContinueStuffModel
    input_model_serializer = serpyco.Serializer(ContinueStuffModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )
        properties["produce_stuff_id"] = action_config_raw["produce_stuff_id"]
        return properties

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if not stuff.under_construction:
            raise ImpossibleAction("Non concérné")
        if self._description.properties["produce_stuff_id"] != stuff.stuff_id:
            raise ImpossibleAction("Non concérné")

    async def check_request_is_possible(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: ContinueStuffModel,
    ) -> None:
        self.check_is_possible(character, stuff)
        check_common_is_possible(
            self._kernel, description=self._description, character=character
        )
        if input_.ap:
            if character.action_points < input_.ap:
                raise WrongInputError(
                    f"{character.name} ne possède passez de points d'actions"
                )

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name=f"Continuer le travail",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.CONTINUE_STUFF_CONSTRUCTION,
                    action_description_id=self._description.id,
                    query_params={},
                    stuff_id=stuff.id,
                ),
                cost=self.get_cost(character, stuff),
                merge_by="continue_craft",
                category="Artisanat",
            )
        ]

    def get_cost(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: typing.Optional[CraftInput] = None,
    ) -> typing.Optional[float]:
        return 0.0  # we use only one action description in config and we don't want ap for continue

    async def perform(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: ContinueStuffModel,
    ) -> Description:
        bonus = character.get_skill_value("intelligence") + character.get_skill_value(
            "crafts"
        )
        bonus_divider = max(1.0, (bonus * 2) / DEFAULT_MAXIMUM_SKILL)
        remain_ap = stuff.ap_required - stuff.ap_spent
        remain_ap_for_character = remain_ap / bonus_divider

        if not input_.ap:
            return Description(
                title=f"Continuer de travailler sur {stuff.name}",
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_stuff_action_url(
                            character_id=character.id,
                            action_type=ActionType.CONTINUE_STUFF_CONSTRUCTION,
                            query_params={},
                            action_description_id=self._description.id,
                            stuff_id=stuff.id,
                        ),
                        items=[
                            Part(
                                text=f"Il reste {round(remain_ap, 3)} PA à passer ({round(remain_ap_for_character, 3)} avec vos bonus)"
                            ),
                            Part(
                                label=f"Combien de points d'actions dépenser ?",
                                type_=Type.NUMBER,
                                name="ap",
                            ),
                        ],
                    )
                ],
                footer_links=[
                    Part(
                        is_link=True,
                        label="Voir l'objet",
                        form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                            character_id=character.id, stuff_id=stuff.id
                        ),
                        classes=["primary"],
                    )
                ],
            )

        consume_ap = min(remain_ap, input_.ap * bonus_divider)
        stuff_doc = self._kernel.stuff_lib.get_stuff_doc(stuff.id)
        stuff_doc.ap_spent = float(stuff_doc.ap_spent) + consume_ap
        await self._kernel.character_lib.reduce_action_points(
            character.id, consume_ap, commit=False
        )

        if stuff_doc.ap_spent >= stuff_doc.ap_required:
            stuff_doc.under_construction = False
            title = f"Construction de {stuff.name} terminé"
        else:
            title = f"Construction de {stuff.name} avancé"

        self._kernel.server_db_session.commit()
        return Description(
            title=title,
            footer_links=[
                Part(
                    is_link=True,
                    label="Voir l'objet",
                    form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=stuff_doc.id
                    ),
                    classes=["primary"],
                )
            ],
            back_url=f"/_describe/character/{character.id}/on_place_actions",
        )
