# coding: utf-8
from copy import copy
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import WithResourceAction
from rolling.action.base import get_with_resource_action_url
from rolling.action.utils import check_common_is_possible
from rolling.exception import ImpossibleAction, NotEnoughActionPoints, NotEnoughResource
from rolling.exception import NoCarriedResource
from rolling.exception import WrongInputError
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.util import ExpectedQuantityContext, Quantity, QuantityEncoder
from rolling.util import InputQuantityContext

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class MixResourceModel:
    resource_mix_id: str
    quantity: typing.Optional[Quantity] = None


class MixResourcesAction(WithResourceAction):
    input_model: typing.Type[MixResourceModel] = MixResourceModel
    input_model_serializer = serpyco.Serializer(
        input_model, type_encoders={Quantity: QuantityEncoder()}
    )

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        if not self._kernel.resource_lib.have_resource(
            character_id=character.id, resource_id=resource_id
        ):
            raise ImpossibleAction("Vous ne possedez pas cette resource")

        # TODO BS 2019-09-10: manage more than two resource mix
        for carried_resource in self._kernel.resource_lib.get_carried_by(character.id):
            for (
                resource_mix_description
            ) in self._kernel.game.config.get_resource_mixs_with(
                [resource_id, carried_resource.id]
            ):
                return

        raise ImpossibleAction("Aucune association possible")

    async def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> None:
        self.check_is_possible(character, resource_id)
        resource_mix = self._kernel.game.config.resource_mixs[input_.resource_mix_id]
        check_common_is_possible(
            self._kernel, character=character, description=resource_mix
        )

        if input_.quantity is not None:
            unit_name = self._kernel.translation.get(resource_mix.produce_resource.unit)
            multiplier = int(
                input_.quantity.as_real_float() / resource_mix.produce_quantity
            )

            for required_resource in resource_mix.required_resources:
                carried_resource = self._kernel.resource_lib.get_one_carried_by(
                    character_id=character.id,
                    resource_id=required_resource.resource.id,
                    empty_object_if_not=True,
                )
                required_quantity = required_resource.quantity * multiplier
                if carried_resource.quantity < required_quantity:
                    raise WrongInputError(
                        f"Vous ne possédez pas assez de {required_resource.resource.name}: "
                        f"Quantité nécessaire: {required_quantity} {unit_name}, "
                        f"vous n'en avez que {carried_resource.quantity} {unit_name}"
                    )

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []

        for carried_resource in self._kernel.resource_lib.get_carried_by(character.id):
            if carried_resource.id == resource_id:
                continue

            for (
                resource_mix_description
            ) in self._kernel.game.config.get_resource_mixs_with(
                [resource_id, carried_resource.id]
            ):
                with_str = ", ".join(
                    [
                        r.resource.name
                        for r in resource_mix_description.required_resources
                        if r.resource.id != resource_id
                    ]
                )
                query_params = self.input_model_serializer.dump(
                    self.input_model(resource_mix_id=resource_mix_description.id)
                )
                actions.append(
                    CharacterActionLink(
                        name=f"Produire de {resource_mix_description.produce_resource.name} avec {with_str}",
                        link=get_with_resource_action_url(
                            character_id=character.id,
                            action_type=ActionType.MIX_RESOURCES,
                            resource_id=carried_resource.id,
                            query_params=query_params,
                            action_description_id=self._description.id,
                        ),
                        cost=None,
                        category="Production",
                        classes1=[resource_mix_description.produce_resource.id],
                        group_name="Mélanger des ressources",
                    )
                )

        return actions

    def get_cost(
        self,
        character: "CharacterModel",
        resource_id: str,
        input_: typing.Optional[input_model] = None,
    ) -> typing.Optional[float]:
        if input_ and input_.quantity is not None:
            resource_mix_description = self._kernel.game.config.resource_mixs[
                input_.resource_mix_id
            ]
            return (
                self._description.base_cost
                + resource_mix_description.cost_per_quantity
                * int(
                    input_.quantity.as_real_float()
                    / resource_mix_description.produce_quantity
                )
            )
        return self._description.base_cost

    def _get_maximum_multiplier_capacity(
        self, character: "CharacterModel", mix_id: str
    ) -> int:
        mix_description = self._kernel.game.config.resource_mixs[mix_id]
        carried_resources = [
            self._kernel.resource_lib.get_one_carried_by(
                character_id=character.id,
                resource_id=required_resource.resource.id,
                empty_object_if_not=True,
            )
            for required_resource in mix_description.required_resources
        ]
        available_quantities = {
            carried_resource.id: carried_resource.quantity
            for carried_resource in carried_resources
        }

        available_counts = [
            int(
                available_quantities[required_resource.resource.id]
                / required_resource.quantity
            )
            for required_resource in mix_description.required_resources
        ]
        available_counts.append(
            int(character.action_points / mix_description.cost_per_quantity)
        )

        return min(available_counts)

    async def perform(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> Description:
        base_cost = self.get_cost(character, resource_id=resource_id)
        mix_description = self._kernel.game.config.resource_mixs[input_.resource_mix_id]
        produce_unit_name = self._kernel.translation.get(
            mix_description.produce_resource.unit
        )
        produce_quantity = mix_description.produce_quantity

        if input_.quantity is None:
            multiplier = self._get_maximum_multiplier_capacity(
                character,
                mix_id=input_.resource_mix_id,
            )
            maximum_produce_quantity = produce_quantity * float(multiplier)

            parts = [
                Part(
                    text=(
                        f"Pour produire {mix_description.produce_quantity} {produce_unit_name} "
                        f"de {mix_description.produce_resource.name} il faut :"
                    )
                )
            ]

            for required_resource in mix_description.required_resources:
                unit_name = self._kernel.translation.get(
                    required_resource.resource.unit
                )
                parts.append(
                    Part(
                        text=(
                            f" - {required_resource.quantity} "
                            f"{unit_name} de {required_resource.resource.name}"
                        )
                    )
                )

            parts.append(Part(text="Vous possédez :"))

            for required in mix_description.required_resources:
                unit_str = self._kernel.translation.get(required.resource.unit)
                have_quantity = self._kernel.resource_lib.get_one_carried_by(
                    character_id=character.id,
                    resource_id=required.resource.id,
                    empty_object_if_not=True,
                ).quantity

                parts.append(
                    Part(
                        text=f" - {have_quantity} {unit_str} de {required.resource.name}"
                    )
                )

            parts.append(
                Part(
                    text=(
                        f"Produire {mix_description.produce_resource.name} coûte {base_cost} PA, "
                        f"puis {mix_description.cost_per_quantity} PA "
                        f" par {mix_description.produce_quantity} {produce_unit_name}."
                    )
                )
            )

            produce_resource_id = mix_description.produce_resource.id
            produce_resource_description = self._kernel.game.config.resources[
                produce_resource_id
            ]
            maximum = Quantity(
                maximum_produce_quantity,
                default_unit=mix_description.produce_resource.unit,
            ).convert()
            return Description(
                title=f"Produire {mix_description.produce_resource.name}",
                illustration_name=produce_resource_description.illustration,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_resource_action_url(
                            character_id=character.id,
                            action_type=ActionType.MIX_RESOURCES,
                            resource_id=resource_id,
                            query_params=self.input_model_serializer.dump(input_),
                            action_description_id=self._description.id,
                        ),
                        items=[
                            *parts,
                            Part(
                                label=f"Produire combien de {mix_description.produce_resource.name} ({unit_name}) ?",
                                type_=Type.NUMBER,
                                name="quantity",
                                min_value=0.0,
                                max_value=maximum.as_real_float(),
                                default_value=maximum.zero_str(),
                            ),
                        ],
                    )
                ],
            )

        input_.quantity.assert_unit(ImpossibleAction("Vous devez saisir une unité"))
        parts = []
        desired_multiplier = int(
            input_.quantity.as_real_float() / mix_description.produce_quantity
        )
        required_ap = self.get_cost(character, resource_id=resource_id, input_=input_)

        try:
            # AP
            await self._kernel.character_lib.reduce_action_points(
                character_id=character.id,
                cost=required_ap,
                check=True,
                commit=False,
            )
            # Reduce
            for required_resource in mix_description.required_resources:
                self._kernel.resource_lib.reduce_carried_by(
                    character.id,
                    required_resource.resource.id,
                    required_resource.quantity * desired_multiplier,
                    commit=False,
                )
            # Create
            produced_quantity = mix_description.produce_quantity * desired_multiplier
            self._kernel.resource_lib.add_resource_to(
                character_id=character.id,
                resource_id=mix_description.produce_resource.id,
                quantity=produced_quantity,
                commit=False,
            )
            parts.append(
                Part(
                    text=(
                        f"Vous avez produit {produced_quantity} {produce_unit_name} "
                        f"de {mix_description.produce_resource.name}"
                    )
                )
            )
        except (NoCarriedResource, NotEnoughResource):
            parts.append(
                Part(
                    text=(
                        f"Vous n'avez pas pu produire la quantité demandé : "
                        "Pas assez de resources"
                    )
                )
            )
        except NotEnoughActionPoints:
            parts.append(
                Part(
                    text=(
                        f"Vous n'avez pas pu produire la quantité demandé : "
                        "Pas assez de Points d'Actions"
                    )
                )
            )

        return Description(
            title=f"Produire {mix_description.produce_resource.name}",
            back_url=f"/_describe/character/{character.id}/inventory",
            items=parts,
            reload_inventory=True,
        )
