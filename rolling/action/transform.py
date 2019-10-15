# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import ImpossibleAction
from rolling.exception import NotEnoughActionPoints
from rolling.model.stuff import StuffGenerateResourceProperties
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.game.base import GameConfig
    from rolling.model.stuff import StuffModel


@dataclasses.dataclass
class TransformStuffIntoResourcesInputModel:
    resource_id: typing.Optional[str] = None


class TransformStuffIntoResourcesAction(WithStuffAction):
    input_model = TransformStuffIntoResourcesInputModel
    input_model_serializer = serpyco.Serializer(TransformStuffIntoResourcesInputModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def _get_can_generate_resource_properties(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.Iterable[StuffGenerateResourceProperties]:
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff.stuff_id
        )
        for generate_resource in stuff_properties.generate_resources:
            abilities_ok = False

            if not generate_resource.require_one_of_ability:
                abilities_ok = True
            elif character.have_one_of_abilities(generate_resource.require_one_of_ability):
                abilities_ok = True

            if abilities_ok:
                yield generate_resource

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        for can_generate_resource_property in self._get_can_generate_resource_properties(
            character, stuff
        ):
            return

        raise ImpossibleAction("Aucune tranformation possible")

    def _get_generate_resource_property(
        self, character: "CharacterModel", stuff: "StuffModel", resource_id: str
    ) -> StuffGenerateResourceProperties:
        for can_generate_resource_property in self._get_can_generate_resource_properties(
            character, stuff
        ):
            if can_generate_resource_property.resource_id == resource_id:
                return can_generate_resource_property

        raise ImpossibleAction(f"Pas possible de générer la ressource {resource_id}")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []

        for can_generate_resource_property in self._get_can_generate_resource_properties(
            character, stuff
        ):
            resource_id = can_generate_resource_property.resource_id
            resource_description = self._kernel.game.config.resources[resource_id]
            quantity_str = quantity_to_str(
                quantity=can_generate_resource_property.quantity,
                unit=resource_description.unit,
                kernel=self._kernel,
            )

            query_params = self.input_model_serializer.dump(
                self.input_model(resource_id=resource_id)
            )
            actions.append(
                CharacterActionLink(
                    name=f"Transformer en {resource_description.name} ({quantity_str})",
                    link=get_with_stuff_action_url(
                        character_id=character.id,
                        stuff_id=stuff.id,
                        action_type=ActionType.TRANSFORM_STUFF_TO_RESOURCES,
                        query_params=query_params,
                        action_description_id=self._description.id,
                    ),
                    cost=can_generate_resource_property.cost,
                )
            )

        return actions

    def get_cost(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: typing.Optional[typing.Any] = None,
    ) -> typing.Optional[float]:
        return self._description.base_cost

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        if input_.resource_id is not None:
            generate_resource_property = self._get_generate_resource_property(
                character, stuff, resource_id=input_.resource_id
            )

            if generate_resource_property.cost > character.action_points:
                raise NotEnoughActionPoints(generate_resource_property.cost)

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        self.check_request_is_possible(character, stuff, input_)
        # FIXME BS 2019-10-15: to code
        return Description(title="TODO", items=[])
