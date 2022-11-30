# coding: utf-8
import collections
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
from rolling.action.utils import BeginBuildModel
from rolling.action.utils import check_common_is_possible
from rolling.action.utils import fill_base_action_properties
from rolling.availability import Availability
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
    quantity: typing.Optional[float] = serpyco.number_field(
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
        properties["link_group_name"] = action_config_raw.get("link_group_name", None)
        return properties

    async def _perform(
        self,
        character: "CharacterModel",
        description: ActionDescriptionModel,
        input_: CraftInput,
        cost: float,
        dry_run: bool = True,
    ) -> typing.List[Part]:
        parts = []
        assert input_.quantity is not None

        if character.action_points < cost:
            raise ImpossibleAction(
                f"{character.name} no possède pas assez de points d'actions "
                f"({round(cost, 2)} nécessaires)"
            )

        availability = Availability.new(self._kernel, character)
        available_resources = availability.resources()

        for require in description.properties["require"]:
            if "stuff" in require:
                required_quantity = int(input_.quantity) * int(require["quantity"])
                stuff_id = require["stuff"]
                stuff_properties = (
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
                )
                available_stuffs = availability.stuffs(
                    under_construction=False, stuff_id=stuff_id
                )
                owned_quantity = len(available_stuffs)

                if owned_quantity < required_quantity:
                    raise ImpossibleAction(
                        f"Vous ne possédez pas assez de {stuff_properties.name}: {required_quantity} nécessaire(s)"
                    )

                if not dry_run:
                    for i in range(required_quantity):
                        stuff_to_destroy = available_stuffs[i]
                        self._kernel.stuff_lib.destroy(
                            stuff_to_destroy.id, commit=False
                        )

            elif "resource" in require:
                required_quantity = int(input_.quantity) * require["quantity"]
                resource_id = require["resource"]
                resource_properties = self._kernel.game.config.resources[resource_id]
                try:
                    available_resource = next(
                        (
                            c
                            for c in available_resources.resources
                            if c.id == resource_id
                        )
                    )
                except StopIteration:
                    raise WrongInputError(
                        f"Vous ne possédez pas de {resource_properties.name}"
                    )
                if available_resource.quantity < required_quantity:
                    missing_quantity_str = quantity_to_str(
                        kernel=self._kernel,
                        quantity=(required_quantity - available_resource.quantity),
                        unit=available_resource.unit,
                    )
                    raise ImpossibleAction(
                        f"Vous ne possédez pas assez de {available_resource.name}: {missing_quantity_str} de plus nécessaire(s)"
                    )

                if not dry_run:
                    reductions = availability.reduce_resource(
                        resource_id,
                        required_quantity,
                    )
                    parts.extend(reductions.resume_parts(self._kernel))

        if dry_run:
            return []

        produced_counts_txts = collections.defaultdict(lambda: 0)
        for produce in description.properties["produce"]:
            stuff_id = produce["stuff"]
            quantity = produce["quantity"] * int(input_.quantity)
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
                produced_counts_txts[stuff_properties.name] += 1
        await self._kernel.character_lib.reduce_action_points(
            character_id=character.id, cost=cost, commit=False
        )
        self._kernel.server_db_session.commit()

        parts.append(Part(""))
        parts.append(Part("Objet(s) produit(s) :"))
        for name, count in produced_counts_txts.items():
            parts.append(Part(f"  - {count} {name}"))

        return parts


class CraftStuffWithResourceAction(WithResourceAction, BaseCraftStuff):
    input_model = CraftInput
    input_model_serializer = serpyco.Serializer(CraftInput)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return cls._get_properties_from_config(game_config, action_config_raw)

    def check_is_possible(
        self,
        character: "CharacterModel",
        resource_id: str,
        from_inventory_only: bool = False,
    ) -> None:
        if from_inventory_only:
            carried_resource_ids = [
                resource.id
                for resource in Availability.new(self._kernel, character)
                .resources(from_inventory_only=True)
                .resources
                if resource.id == resource_id
            ]
        else:
            carried_resource_ids = [
                resource.id
                for resource in Availability.new(self._kernel, character)
                .resources()
                .resources
            ]

        required_txts = []
        for require in self.description.properties["require"]:
            if require["resource"] in carried_resource_ids:
                return

            resource_description = self._kernel.game.config.resources[
                require["resource"]
            ]
            required_txts.append(resource_description.name)

        raise ImpossibleAction(
            f"Vous devez posséder au moins l'une des ressources suivantes : {', '.join(required_txts)}"
        )

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
        classes: typing.Optional[typing.List[str]] = None
        for produce in self._description.properties["produce"]:
            stuff_id = produce["stuff"]
            classes = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
            ).classes + [stuff_id]
            break

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
                group_name=self._description.properties["link_group_name"],
                cost=self.get_cost(character, resource_id),
                category="Artisanat",
                classes1=classes,
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
            return base_cost * int(input_.quantity)
        return base_cost

    async def perform(
        self, character: "CharacterModel", resource_id: str, input_: CraftInput
    ) -> Description:
        if input_.quantity is None:

            illustration: typing.Optional[str] = None
            for produce in self._description.properties["produce"]:
                illustration = (
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                        produce["stuff"]
                    ).illustration
                )
                if illustration:
                    break

            produce_txts = ["Production de :"]
            for produce in self._description.properties["produce"]:
                if "resource" in produce:
                    resource_description = self._kernel.game.config.resources[
                        produce["resource"]
                    ]
                    produce_txts.append(f" - {resource_description.name}")
                elif "stuff" in produce:
                    stuff_properties = (
                        self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                            produce["stuff"]
                        )
                    )
                    produce_txts.append(f" - {stuff_properties.name}")
            produce_txts.append("")

            cost = self.get_cost(character, resource_id=resource_id, input_=input_)
            require_txts = ["Requiert :", f" - {cost} PA"]
            for consume in self._description.properties["require"]:
                if "resource" in consume:
                    resource_id = consume["resource"]
                    resource_description = self._kernel.game.config.resources[
                        resource_id
                    ]
                    quantity_str = quantity_to_str(
                        consume["quantity"], resource_description.unit, self._kernel
                    )
                    require_txts.append(
                        f" - {quantity_str} de {resource_description.name}"
                    )

                elif "stuff" in consume:
                    stuff_id = consume["stuff"]
                    stuff_properties = (
                        self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                            stuff_id
                        )
                    )
                    require_txts.append(
                        f" - {consume['quantity']} de {stuff_properties.name}"
                    )

            require_txts.append("")

            # Indicate required abilities too
            if required_one_of_abilities := self._description.properties.get(
                "required_one_of_abilities"
            ):
                require_txts.append("Requiert une des habilités :")
                for required_one_of_ability in required_one_of_abilities:
                    require_txts.append(f" - {required_one_of_ability.name}")
                require_txts.append("")

            if required_all_abilities := self._description.properties.get(
                "required_all_abilities"
            ):
                require_txts.append("Requiert les habilités :")
                for required_all_ability in required_all_abilities:
                    require_txts.append(f" - {required_all_ability.name}")

            take_from_parts = Availability.new(
                self._kernel, character
            ).take_from_parts()

            return Description(
                title=self._description.name,
                illustration_name=illustration,
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
                        items=[Part(text=text) for text in produce_txts]
                        + [Part(text=text) for text in require_txts]
                        + [Part(text=""), *take_from_parts, Part(text="")]
                        + [
                            Part(
                                label=f"Quelle quantité en produire ?",
                                type_=Type.NUMBER,
                                name="quantity",
                                default_value="1",
                                min_value=1,
                                max_value=100,
                                expect_integer=True,
                            )
                        ],
                    )
                ],
            )

        cost = self.get_cost(character, resource_id=resource_id, input_=input_)
        parts = await self._perform(
            character,
            description=self._description,
            input_=input_,
            cost=cost,
            dry_run=False,
        )
        return Description(
            title="Action effectué avec succès",
            back_url=f"/_describe/character/{character.id}/on_place_actions",
            reload_inventory=True,
            items=parts,
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
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        from_inventory_only: bool = False,
    ) -> None:
        # Consider action ca be possible (displayed in interface) if at least one of required stuff
        # is owned by character
        availability = Availability.new(self._kernel, character)
        carried = availability.stuffs(
            under_construction=False, from_inventory_only=from_inventory_only
        )
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
            return base_cost * int(input_.quantity)
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
        classes: typing.Optional[typing.List[str]] = None
        for produce in self._description.properties["produce"]:
            stuff_id = produce["stuff"]
            classes = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
            ).classes + [stuff_id]
            break

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
                classes1=classes,
            )
        ]

    async def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: CraftInput
    ) -> Description:
        if input_.quantity is None:

            illustration: typing.Optional[str] = None
            for produce in self._description.properties["produce"]:
                illustration = (
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                        produce["stuff"]
                    ).illustration
                )
                if illustration:
                    break

            return Description(
                title=self._description.name,
                illustration_name=illustration,
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
                                label=f"Quelle quantité en produire ?",
                                type_=Type.NUMBER,
                                name="quantity",
                                default_value="1",
                                min_value=1,
                                max_value=100,
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
            reload_inventory=True,
        )


@dataclasses.dataclass
class BeginStuffModel(BeginBuildModel):
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
        availability = Availability.new(self._kernel, character)

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
                    if (
                        quantity
                        > availability.resource(
                            resource_id,
                            empty_object_if_not=True,
                        ).resource.quantity
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
                    if quantity > len(
                        [
                            s
                            for s in availability.stuffs(
                                under_construction=False, stuff_id=stuff_id
                            ).stuffs
                        ]
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
        stuff_description = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            self._description.properties["produce_stuff_id"]
        )

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
                classes1=stuff_description.classes + [stuff_description.id],
            )
        ]

    async def perform(
        self, character: "CharacterModel", input_: BeginStuffModel
    ) -> Description:
        availability = Availability.new(self._kernel, character)
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
                Part(text=f"Temps de travail nécessaire :"),
                Part(text=f" - {start_cost} PA tout de suite"),
                Part(text=f" - {craft_ap_cost} PA à effectuer ensuite"),
                Part(text=""),
                Part(text="Nécessite en ressources : "),
            ]

            for require_txt in require_txts:
                items.append(Part(text=require_txt))

            items.append(Part(text=""))

            # Indicate required abilities too
            if required_one_of_abilities := self._description.properties.get(
                "required_one_of_abilities"
            ):
                items.append(Part(text="Requiert une des habilités :"))
                for required_one_of_ability in required_one_of_abilities:
                    items.append(Part(text=f" - {required_one_of_ability.name}"))
                items.append(Part(text=""))

            if required_all_abilities := self._description.properties.get(
                "required_all_abilities"
            ):
                items.append(Part(text="Requiert les habilités :"))
                for required_all_ability in required_all_abilities:
                    items.append(Part(text=f" - {required_all_ability.name}"))
                items.append(Part(text=""))

            items.extend(availability.take_from_parts())
            items.append(Part(""))

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

        parts = []
        for consume in self._description.properties["consume"]:
            if "resource" in consume:
                parts.append(Part(""))
                resource_id = consume["resource"]
                ###########################################
                resource_reductions = availability.reduce_resource(
                    resource_id, consume["quantity"]
                )
                parts.extend(resource_reductions.resume_parts(self._kernel))

            elif "stuff" in consume:
                parts.append(Part(""))
                parts.append(
                    Part(
                        f"Objets utilisés ( (depuis {availability.take_from_one_line_txt()})) :"
                    )
                )
                stuff_id = consume["stuff"]
                stuffs = availability.stuffs(
                    under_construction=False, stuff_id=stuff_id
                )
                for i in range(consume["quantity"]):
                    self._kernel.stuff_lib.destroy(stuffs[i].id, commit=False)
                    parts.append(f"  - {stuffs[i].name}")

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
            items=[
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
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        from_inventory_only: bool = False,
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
                classes1=(
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                        stuff.stuff_id
                    )
                ).classes
                + [stuff.stuff_id],
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
                                default_value="1.0",
                                min_value=1.0,
                                max_value=min(character.action_points, remain_ap),
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
            reload_inventory=True,
        )
