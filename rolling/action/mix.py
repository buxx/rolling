# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import WithResourceAction
from rolling.action.base import get_with_resource_action_url
from rolling.action.utils import check_common_is_possible
from rolling.exception import ImpossibleAction
from rolling.exception import NoCarriedResource
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class MixResourceModel:
    resource_mix_id: str
    quantity: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


class MixResourcesAction(WithResourceAction):
    input_model: typing.Type[MixResourceModel] = MixResourceModel
    input_model_serializer = serpyco.Serializer(input_model)

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        if not self._kernel.resource_lib.have_resource(
            character_id=character.id, resource_id=resource_id
        ):
            raise ImpossibleAction("Vous ne possedez pas cette resource")

        # TODO BS 2019-09-10: manage more than two resource mix
        for carried_resource in self._kernel.resource_lib.get_carried_by(character.id):
            for resource_mix_description in self._kernel.game.config.get_resource_mixs_with(
                [resource_id, carried_resource.id]
            ):
                return

        raise ImpossibleAction("Aucune association possible")

    def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> None:
        self.check_is_possible(character, resource_id)
        resource_mix = self._kernel.game.config.resource_mixs[input_.resource_mix_id]
        check_common_is_possible(self._kernel, character=character, description=resource_mix)

        if input_.quantity is not None:
            unit_name = self._kernel.translation.get(resource_mix.produce_resource.unit)

            for required_resource in resource_mix.required_resources:
                carried_resource = self._kernel.resource_lib.get_one_carried_by(
                    character_id=character.id, resource_id=required_resource.resource.id
                )
                required_quantity = required_resource.coeff * input_.quantity
                if carried_resource.quantity < required_quantity:
                    raise ImpossibleAction(
                        f"Vous ne possédez pas assez de {required_resource.resource.name}: "
                        f"Quantité nécessaire: {required_quantity} {unit_name}, "
                        f"vous n'en avez que {carried_resource.quantity} {unit_name}"
                    )

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []

        for carried_resource in self._kernel.resource_lib.get_carried_by(character.id):
            if carried_resource.id == resource_id:
                continue

            for resource_mix_description in self._kernel.game.config.get_resource_mixs_with(
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
            return resource_mix_description.cost * input_.quantity
        return self._description.base_cost

    def perform(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> Description:
        base_cost = self.get_cost(character, resource_id=resource_id)
        resource_mix_description = self._kernel.game.config.resource_mixs[input_.resource_mix_id]
        unit_name = self._kernel.translation.get(resource_mix_description.produce_resource.unit)
        cost_per_unit = resource_mix_description.cost

        if input_.quantity is None:
            required_str = ", ".join(
                [
                    f"{round(r.coeff * 100)}% {r.resource.name}"
                    for r in resource_mix_description.required_resources
                ]
            )
            have_parts = [Part(text="Vous possédez :")]
            for required in resource_mix_description.required_resources:
                unit_str = self._kernel.translation.get(required.resource.unit)
                try:
                    have_quantity = self._kernel.resource_lib.get_one_carried_by(
                        character_id=character.id, resource_id=required.resource.id
                    ).quantity
                except NoCarriedResource:
                    have_quantity = 0.0
                have_parts.append(
                    Part(text=f"{required.resource.name} : {have_quantity} {unit_str}")
                )
            return Description(
                title=f"Faire {resource_mix_description.produce_resource.name}",
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
                            Part(
                                text=(
                                    f"Quantité en {unit_name} "
                                    f"(coût: {base_cost} + {cost_per_unit} par {unit_name}, "
                                    f"avec {required_str}) ?"
                                )
                            ),
                            *have_parts,
                            Part(
                                label="Quantité ?",
                                type_=Type.NUMBER,
                                name="quantity",
                            ),
                        ],
                    )
                ],
            )

        # Make mix
        for required_resource in resource_mix_description.required_resources:
            required_quantity = required_resource.coeff * input_.quantity
            self._kernel.resource_lib.reduce_carried_by(
                character.id, required_resource.resource.id, required_quantity, commit=False
            )

        self._kernel.resource_lib.add_resource_to(
            character_id=character.id,
            resource_id=resource_mix_description.produce_resource.id,
            quantity=input_.quantity,
            commit=False,
        )
        self._kernel.character_lib.reduce_action_points(
            character_id=character.id,
            cost=self.get_cost(character, resource_id=resource_id, input_=input_),
            commit=False,
        )
        self._kernel.server_db_session.commit()

        return Description(
            title=f"{input_.quantity} {unit_name} produits",
            back_url=f"/_describe/character/{character.id}/inventory",
        )
