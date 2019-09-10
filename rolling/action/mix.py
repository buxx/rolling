# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import WithResourceAction
from rolling.action.base import get_with_resource_action_url
from rolling.exception import ImpossibleAction
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.game.base import GameConfig


@dataclasses.dataclass
class MixResourceModel:
    with_resource_ids: typing.List[str]
    quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )


class MixResourcesAction(WithResourceAction):
    input_model: typing.Type[MixResourceModel] = MixResourceModel
    input_model_serializer = serpyco.Serializer(input_model)

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        if not self._kernel.resource_lib.have_resource(character.id, resource_id):
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

    def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> None:
        self.check_is_possible(character, resource_id)
        raise NotImplementedError("Tester si quantity nécessaire ok")

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
                other_resource_ids = [
                    r.resource.id
                    for r in resource_mix_description.required_resources
                    if r.resource.id != resource_id
                ]
                query_params = self.input_model_serializer.dump(
                    self.input_model(with_resource_ids=other_resource_ids)
                )
                actions.append(
                    CharacterActionLink(
                        name=f"Produire de {resource_mix_description.produce_resource.name} avec {with_str}",
                        link=get_with_resource_action_url(
                            character_id=character.id,
                            action_type=ActionType.MIX_RESOURCES,
                            resource_id=carried_resource.id,
                            query_params=query_params,
                        ),
                        cost=self.get_cost(character, resource_id),
                    )
                )

        return actions

    def perform(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> Description:
        raise NotImplementedError("todo")
