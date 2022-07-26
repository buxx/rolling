# coding: utf-8
from collections import defaultdict
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_resource_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.action.utils import check_common_is_possible
from rolling.action.utils import fill_base_action_properties
from rolling.exception import ImpossibleAction
from rolling.exception import NotEnoughActionPoints
from rolling.exception import RollingError
from rolling.exception import WrongInputError
from rolling.model.measure import Unit
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.server.util import with_multiple_carried_stuffs
from rolling.util import ExpectedQuantityContext
from rolling.util import InputQuantityContext
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


@dataclasses.dataclass
class TransformStuffIntoResourcesModel:
    quantity: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )


class TransformStuffIntoResourcesAction(WithStuffAction):
    input_model = TransformStuffIntoResourcesModel
    input_model_serializer = serpyco.Serializer(TransformStuffIntoResourcesModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )
        properties.update({"produce": action_config_raw["produce"]})
        return properties

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if (
            stuff.stuff_id
            not in self._description.properties["required_one_of_stuff_ids"]
        ):
            raise ImpossibleAction("Non concerné")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        resources_str_parts = []
        for produce in self._description.properties["produce"]:
            resource_id = produce["resource"]
            resource_description = self._kernel.game.config.resources[resource_id]
            resources_str_parts.append(f"{resource_description.name}")
        resources_str = ", ".join(resources_str_parts)

        return [
            CharacterActionLink(
                name=f"Transformer en {resources_str}",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    stuff_id=stuff.id,
                    action_type=ActionType.TRANSFORM_STUFF_TO_RESOURCES,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
                classes1=[resource_description.id],
            )
        ]

    async def check_request_is_possible(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: TransformStuffIntoResourcesModel,
    ) -> None:
        check_common_is_possible(
            self._kernel, character=character, description=self._description
        )
        self.check_is_possible(character, stuff)

    def get_cost(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: typing.Optional[typing.Any] = None,
    ) -> typing.Optional[float]:
        return self._description.base_cost

    async def perform(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: TransformStuffIntoResourcesModel,
    ) -> Description:
        await self.check_request_is_possible(character, stuff, input_)

        async def do_for_one(
            character_: "CharacterModel",
            stuff_: "StuffModel",
            input__: TransformStuffIntoResourcesModel,
        ) -> typing.List[Part]:
            character_doc = self._kernel.character_lib.get_document(id_=character_.id)
            if character_doc.action_points < self._description.base_cost:
                raise NotEnoughActionPoints(self._description.base_cost)

            for produce in self._description.properties["produce"]:
                resource_id = produce["resource"]
                if "coeff" in produce:
                    quantity = stuff_.weight * produce["coeff"]
                else:
                    quantity = produce["quantity"]
                self._kernel.resource_lib.add_resource_to(
                    character_id=character_.id,
                    resource_id=resource_id,
                    quantity=quantity,
                    commit=False,
                )

            await self._kernel.character_lib.reduce_action_points(
                character_id=character_.id, cost=self._description.base_cost
            )
            self._kernel.stuff_lib.destroy(stuff_.id)
            self._kernel.server_db_session.commit()
            return []

        return await with_multiple_carried_stuffs(
            self,
            self._kernel,
            character=character,
            stuff=stuff,
            input_=input_,
            action_type=ActionType.TRANSFORM_STUFF_TO_RESOURCES,
            do_for_one_func=do_for_one,
            title="Transformation effectué",
            success_parts=[
                Part(
                    is_link=True,
                    label="Voir l'inventaire",
                    form_action=f"/_describe/character/{character.id}/inventory",
                    classes=["primary"],
                )
            ],
        )


@dataclasses.dataclass
class TransformStuffIntoStuffModel:
    quantity: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )


class TransformStuffIntoStuffAction(WithStuffAction):
    input_model = TransformStuffIntoStuffModel
    input_model_serializer = serpyco.Serializer(TransformStuffIntoStuffModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )
        properties.update({"produce": action_config_raw["produce"]})
        properties.update({"cost_per_unit": action_config_raw["cost_per_unit"]})
        return properties

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if (
            stuff.stuff_id
            not in self._description.properties["required_one_of_stuff_ids"]
        ):
            raise ImpossibleAction("Non concerné")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        stuffs_str_parts = []
        for produce in self._description.properties["produce"]:
            stuff_id = produce["stuff"]
            stuff_description = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
            )
            stuffs_str_parts.append(stuff_description.name)
        stuff_str = ", ".join(stuffs_str_parts)

        return [
            CharacterActionLink(
                name=self._description.name or f"Transformer en {stuff_str}",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    stuff_id=stuff.id,
                    action_type=ActionType.TRANSFORM_STUFF_TO_STUFF,
                    query_params={},
                    action_description_id=self._description.id,
                ),
            )
        ]

    async def check_request_is_possible(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: TransformStuffIntoResourcesModel,
    ) -> None:
        check_common_is_possible(
            self._kernel, character=character, description=self._description
        )
        self.check_is_possible(character, stuff)

    def get_cost(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: typing.Optional[TransformStuffIntoStuffModel] = None,
    ) -> typing.Optional[float]:
        if input_ is None:
            return None

        return self._description.base_cost + (
            self._description.properties["cost_per_unit"] * (input_.quantity or 1)
        )

    async def perform(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: TransformStuffIntoResourcesModel,
    ) -> Description:
        await self.check_request_is_possible(character, stuff, input_)
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff.stuff_id
        )

        illustration: typing.Optional[str] = None
        for produce in self._description.properties["produce"]:
            illustration = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                produce["stuff"]
            ).illustration
            if illustration:
                break

        max_quantity = self._kernel.stuff_lib.get_stuff_count(
            character_id=character.id, stuff_id=stuff.stuff_id
        )

        if not input_.quantity:
            return Description(
                title=self._description.name,
                illustration_name=illustration,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_stuff_action_url(
                            character_id=character.id,
                            action_type=ActionType.TRANSFORM_STUFF_TO_STUFF,
                            stuff_id=stuff.id,
                            query_params=self.input_model_serializer.dump(input_),
                            action_description_id=self._description.id,
                        ),
                        items=[
                            Part(
                                label=f"Quelle quantité ?",
                                type_=Type.NUMBER,
                                name="quantity",
                                default_value=str(max_quantity),
                                min_value=0.0,
                                max_value=max_quantity,
                            )
                        ],
                    )
                ],
            )

        total_cost = self.get_cost(character, stuff=stuff, input_=input_)
        if character.action_points < total_cost:
            raise ImpossibleAction(
                f"Pas assez de points d'actions ({total_cost} nécéssaires)"
            )

        await self._kernel.character_lib.reduce_action_points(
            character_id=character.id, cost=self._description.base_cost
        )

        done_count = 0
        produced: typing.DefaultDict[str, int] = defaultdict(lambda: 0)
        for _ in range(input_.quantity):
            try:
                stuff_ = self._kernel.stuff_lib.get_carried_by(
                    character_id=character.id, stuff_id=stuff.stuff_id
                ).pop()
            except IndexError:
                break

            self._kernel.stuff_lib.destroy(stuff_id=stuff_.id)

            for produce in self._description.properties["produce"]:
                stuff_id: str = produce["stuff"]
                stuff_description = (
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
                )
                new_stuff_doc = (
                    self._kernel.stuff_lib.create_document_from_stuff_properties(
                        stuff_description
                    )
                )
                new_stuff_doc.carried_by_id = character.id
                self._kernel.server_db_session.add(new_stuff_doc)
                self._kernel.server_db_session.commit()
                await self._kernel.character_lib.reduce_action_points(
                    character_id=character.id,
                    cost=self._description.properties["cost_per_unit"],
                )
                produced[stuff_description.name] += 1
            done_count += 1

        produced_str = ", ".join(
            [f"{count} {name}" for name, count in produced.items()]
        )
        return Description(
            title=self._description.name,
            items=[
                Part(
                    text=f"{done_count} {stuff_properties.name} transformé(es) en {produced_str}"
                )
            ],
        )


@dataclasses.dataclass
class QuantityModel:
    quantity: typing.Optional[str] = None


class TransformResourcesIntoResourcesAction(WithResourceAction):
    input_model = QuantityModel
    input_model_serializer = serpyco.Serializer(QuantityModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        for produce in action_config_raw["produce"]:
            if "resource" not in produce or "coeff" not in produce:
                raise RollingError(
                    f"Misconfiguration for following action content: {action_config_raw}"
                )

        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )
        properties["required_resource_id"] = action_config_raw["required_resource_id"]
        properties["produce"] = action_config_raw["produce"]
        properties["cost_per_unit"] = action_config_raw["cost_per_unit"]
        return properties

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        if resource_id != self._description.properties["required_resource_id"]:
            raise ImpossibleAction("Non concerné")

    async def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: QuantityModel
    ) -> None:
        self.check_is_possible(character, resource_id)
        check_common_is_possible(
            kernel=self._kernel, description=self._description, character=character
        )

        required_resource_id = self._description.properties["required_resource_id"]
        if input_.quantity is not None:
            carried_resource = self._kernel.resource_lib.get_one_carried_by(
                character.id, resource_id=required_resource_id
            )
            user_input_context = InputQuantityContext.from_carried_resource(
                user_input=input_.quantity, carried_resource=carried_resource
            )
            if carried_resource.quantity < user_input_context.real_quantity:
                raise ImpossibleAction(f"Vous n'en possédez pas assez")
            cost = self.get_cost(character, resource_id=resource_id, input_=input_)
            if character.action_points < cost:
                raise ImpossibleAction(
                    f"{character.name} no possède pas assez de points d'actions "
                    f"({round(cost, 2)} nécessaires)"
                )

    def _adapt_quantity(self, quantity: float) -> float:
        there_is_unit = -1
        for produce in self._description.properties["produce"]:
            produce_resource = self._kernel.game.config.resources[produce["resource"]]
            if produce_resource.unit == Unit.UNIT:
                if there_is_unit != -1 and produce["coeff"] % there_is_unit:
                    raise ImpossibleAction(
                        "Erreur configuration serveur: les productions doivent"
                        " etre unitaires et multiples entiers"
                    )

                there_is_unit = produce["coeff"]
            elif there_is_unit != -1:
                raise ImpossibleAction(
                    "Erreur configuration serveur: les productions doivent etre unitaires"
                )

        if there_is_unit == -1:
            return quantity

        produce_quantity = quantity * there_is_unit
        if produce_quantity < 1.0:
            raise WrongInputError("Pas assez de matière première")
        not_round = float("0." + str(str(produce_quantity).split(".")[1]))

        if not not_round:
            return quantity

        return quantity - (not_round / there_is_unit)

    def get_cost(
        self,
        character: "CharacterModel",
        resource_id: str,
        input_: typing.Optional[QuantityModel] = None,
    ) -> typing.Optional[float]:
        if input_ and input_.quantity is not None:
            carried_resource = self._kernel.resource_lib.get_one_carried_by(
                character.id, resource_id=resource_id, empty_object_if_not=True
            )
            user_input_context = InputQuantityContext.from_carried_resource(
                user_input=input_.quantity, carried_resource=carried_resource
            )
            real_quantity = self._adapt_quantity(user_input_context.real_quantity)
            return self._description.base_cost + (
                self._description.properties["cost_per_unit"] * real_quantity
            )
        return self._description.base_cost

    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        classes: typing.Optional[typing.List[str]] = None
        for produce in self._description.properties["produce"]:
            classes = [produce["resource"]]
            break

        return [
            CharacterActionLink(
                name=self._description.name,
                link=get_with_resource_action_url(
                    character_id=character.id,
                    action_type=ActionType.TRANSFORM_RESOURCES_TO_RESOURCES,
                    action_description_id=self._description.id,
                    resource_id=resource_id,
                    query_params={},
                ),
                cost=self.get_cost(character, resource_id),
                classes1=classes,
            )
        ]

    async def perform(
        self, character: "CharacterModel", resource_id: str, input_: QuantityModel
    ) -> Description:
        base_cost = self.get_cost(character, resource_id=resource_id)
        cost_per_unit = self._description.properties["cost_per_unit"]
        required_resource_description = self._kernel.game.config.resources[
            self._description.properties["required_resource_id"]
        ]
        carried_resource = self._kernel.resource_lib.get_one_carried_by(
            character.id, resource_id=required_resource_description.id
        )
        expected_quantity_context = ExpectedQuantityContext.from_carried_resource(
            self._kernel, carried_resource
        )
        cost_per_unit = (
            cost_per_unit * 1000
            if expected_quantity_context.display_kg
            else cost_per_unit
        )
        default_quantity = expected_quantity_context.default_quantity

        if input_.quantity is None:
            return Description(
                title=self._description.name,
                can_be_back_url=False,
                back_url=None,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_resource_action_url(
                            character_id=character.id,
                            action_type=ActionType.TRANSFORM_RESOURCES_TO_RESOURCES,
                            resource_id=resource_id,
                            query_params=self.input_model_serializer.dump(input_),
                            action_description_id=self._description.id,
                        ),
                        items=[
                            Part(
                                text=(
                                    f"Vous possedez "
                                    f"{expected_quantity_context.carried_quantity_str} "
                                    f"de {carried_resource.name}"
                                )
                            ),
                            Part(
                                label=(
                                    f"Quantité en {expected_quantity_context.display_unit_name} "
                                    f"(coût: {base_cost} + {cost_per_unit} par "
                                    f"{expected_quantity_context.display_unit_name}) ?"
                                ),
                                type_=Type.NUMBER,
                                name="quantity",
                                default_value=str(default_quantity),
                                min_value=0.0,
                                max_value=carried_resource.quantity,
                            ),
                        ],
                    )
                ],
            )

        user_input_context = InputQuantityContext.from_carried_resource(
            user_input=input_.quantity, carried_resource=carried_resource
        )
        real_quantity = self._adapt_quantity(user_input_context.real_quantity)
        cost = self.get_cost(character, resource_id=resource_id, input_=input_)
        self._kernel.resource_lib.reduce_carried_by(
            character.id, carried_resource.id, quantity=real_quantity, commit=False
        )
        produced_resources_txts = []
        for produce in self._description.properties["produce"]:
            produce_resource = self._kernel.game.config.resources[produce["resource"]]
            produce_quantity = real_quantity * produce["coeff"]
            produce_quantity_str = quantity_to_str(
                produce_quantity, produce_resource.unit, self._kernel
            )
            produced_resources_txts.append(
                f"{produce_resource.name}: {produce_quantity_str}"
            )
            self._kernel.resource_lib.add_resource_to(
                character_id=character.id,
                resource_id=produce["resource"],
                quantity=produce_quantity,
                commit=False,
            )
        await self._kernel.character_lib.reduce_action_points(
            character_id=character.id, cost=cost, commit=False
        )
        self._kernel.server_db_session.commit()

        parts = [Part(text=txt) for txt in produced_resources_txts]
        return Description(title=f"Effectué", items=parts)
