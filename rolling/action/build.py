# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import CharacterAction
from rolling.action.base import WithBuildAction
from rolling.action.base import get_character_action_url
from rolling.exception import ImpossibleAction
from rolling.model.build import BuildRequireResourceDescription
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import EmptyModel, quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.game.base import GameConfig


class BuildAction(CharacterAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {
            "build_id": action_config_raw["build"],
            "require_resources": [
                BuildRequireResourceDescription(
                    resource_id=r["resource"], quantity=r["quantity"]
                )
                for r in action_config_raw.get("require_resources", [])
            ],
        }

    def check_is_possible(self, character: "CharacterModel") -> None:
        # TODO BS 2019-09-30: check is character have skill and stuff (but not resources
        # because we want to permit begin construction)
        pass

    def check_request_is_possible(
        self, character: "CharacterModel", input_: typing.Any
    ) -> None:
        self.check_is_possible(character)

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        try:
            self.check_is_possible(character)
        except ImpossibleAction:
            pass

        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]
        return [
            CharacterActionLink(
                name=build_description.name,
                link=get_character_action_url(
                    character_id=character.id,
                    action_type=ActionType.BUILD,
                    action_description_id=self._description.id,
                    query_params={},
                ),
                cost=self.get_cost(character, input_=None),
            )
        ]

    def perform(self, character: "CharacterModel", input_: typing.Any) -> Description:
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]
        build_doc = self._kernel.build_lib.place_start_build(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            build_id=build_description.id,
        )
        return Description(
            title=f"{build_description.name} commencé",
            items=[Part(text="Continuer", is_link=True, form_action=DESCRIBE_BUILD.format(
                build_id=build_doc.id,
                character_id=character.id,
            ))],
        )


@dataclasses.dataclass
class BringResourceModel:
    resource_id: str
    quantity: float


class BringResourcesOnBuild(WithBuildAction):
    input_model = BringResourceModel
    input_model_serializer = serpyco.Serializer(BringResourceModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        return

    def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: typing.Any
    ) -> None:
        return

    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        actions: typing.List[CharacterActionLink] = []
        stored_resources = self._kernel.resource_lib.get_stored_in_build(build_id)
        stored_resources_by_resource_id: typing.Dict[str, CarriedResourceDescriptionModel] = {
            stored_resource.id: stored_resources
            for stored_resource in stored_resources
        }

        for required_resource in build_description.build_require_resources:
            resource_description = self._kernel.game.config.resources[
                required_resource.resource_id
            ]
            try:
                stored_resource = stored_resources_by_resource_id[required_resource.resource_id]
                stored_resource_quantity = stored_resource.quantity
            except KeyError:
                stored_resource_quantity = 0.0
            left = required_resource.quantity - stored_resource_quantity
            left = left if left > 0.0 else 0.0
            left_str = quantity_to_str(left, resource_description.unit, kernel=self._kernel)

            query_params = BringResourcesOnBuild.input_model_serializer.dump(
                BringResourcesOnBuild.input_model(
                    resource_id=required_resource.resource_id,
                    quantity=left,
                ))
            actions.append(
                CharacterActionLink(
                    name=f"Apporter {resource_description.name} (manque {left_str})",
                    link=get_character_action_url(
                        character_id=character.id,
                        action_type=ActionType.BRING_RESOURCE_ON_BUILD,
                        action_description_id=self._description.id,
                        query_params=query_params,
                    ),
                    cost=None,
                )
            )

        return actions

    def perform(
        self, character: "CharacterModel", build_id: int, input_: typing.Any
    ) -> Description:
        pass
