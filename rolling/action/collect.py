# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.exception import ImpossibleAction
from rolling.exception import RollingError
from rolling.model.extraction import ExtractableResourceDescriptionModel
from rolling.model.resource import ResourceDescriptionModel
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.server.document.character import CharacterDocument


@dataclasses.dataclass
class CollectResourceModel:
    resource_id: str
    row_i: int = serpyco.number_field(cast_on_load=True)
    col_i: int = serpyco.number_field(cast_on_load=True)
    quantity: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


# FIXME BS 2019-08-29: Permit collect only some material (like no liquid)
class CollectResourceAction(CharacterAction):
    input_model: typing.Type[CollectResourceModel] = CollectResourceModel
    input_model_serializer = serpyco.Serializer(input_model)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel") -> None:
        for resource in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        ):
            return

        raise ImpossibleAction("Il n'y a rien à collecter ici")

    def check_request_is_possible(self, character: "CharacterModel", input_: input_model) -> None:
        # FIXME BS 2019-08-27: check input_.row_i and input_.col_i are near
        # FIXME BS 2019-08-29: check if quantity is possible
        resources = self._kernel.game.world_manager.get_resources_at(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.row_i,
            zone_col_i=input_.col_i,
        )
        resource_ids = [resource.id for resource in resources]

        if input_.resource_id in resource_ids:
            return

        raise ImpossibleAction(f"Il n'y a pas de '{input_.resource_id}' à cet endroit")

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        inspect_zone_positions = get_on_and_around_coordinates(
            character.zone_row_i, character.zone_col_i
        )
        character_actions: typing.List[CharacterActionLink] = []

        for row_i, col_i in inspect_zone_positions:
            for resource in self._kernel.game.world_manager.get_resources_at(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=row_i,
                zone_col_i=col_i,
            ):
                tile_type = self._kernel.tile_maps_by_position[
                    (character.world_row_i, character.world_col_i)
                ].source.geography.rows[row_i][col_i]
                query_params = self.input_model(resource_id=resource.id, row_i=row_i, col_i=col_i)
                character_actions.append(
                    CharacterActionLink(
                        name=f"Récupérer {resource.name} sur {tile_type.name}",
                        link=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.COLLECT_RESOURCE,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(query_params),
                        ),
                        cost=None,
                        merge_by=(ActionType.COLLECT_RESOURCE, resource.id),
                        group_name="Ramasser du matériel ou des ressources",
                    )
                )

        return character_actions

    def _get_resource_and_cost(
        self, character: "CharacterDocument", input_: input_model
    ) -> typing.Tuple[ResourceDescriptionModel, ExtractableResourceDescriptionModel, float]:
        tile_type = self._kernel.tile_maps_by_position[
            (character.world_row_i, character.world_col_i)
        ].source.geography.rows[input_.row_i][input_.col_i]
        extractable_resources: typing.Dict[
            str, ExtractableResourceDescriptionModel
        ] = self._kernel.game.config.extractions[tile_type.id].resources
        resource_extraction_description: ExtractableResourceDescriptionModel = extractable_resources[
            input_.resource_id
        ]
        resource: ResourceDescriptionModel = self._kernel.game.config.resources[input_.resource_id]
        # TODO BS 2019-08-29: cost per unit modified by competence / stuff
        cost_per_unit = resource_extraction_description.cost_per_unit

        return resource, resource_extraction_description, cost_per_unit

    def get_cost(
        self, character: "CharacterModel", input_: typing.Optional[input_model] = None
    ) -> typing.Optional[float]:
        if input_.quantity is not None:
            character_doc = self._character_lib.get_document(character.id)
            resource, resource_extraction_description, cost_per_unit = self._get_resource_and_cost(
                character_doc, input_
            )
            return input_.quantity * resource_extraction_description.cost_per_unit

    def perform(self, character: "CharacterModel", input_: input_model) -> Description:
        character_doc = self._character_lib.get_document(character.id)
        resource, resource_extraction_description, cost_per_unit = self._get_resource_and_cost(
            character_doc, input_
        )

        if input_.quantity is None:
            unit_name = self._kernel.translation.get(resource.unit)

            return Description(
                title=f"Récupérer du {resource.name}",
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.COLLECT_RESOURCE,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(input_),
                        ),
                        items=[
                            Part(
                                label=f"Quantité (coût: {cost_per_unit} par {unit_name}) ?",
                                type_=Type.NUMBER,
                                name="quantity",
                            )
                        ],
                    )
                ],
            )

        self._kernel.resource_lib.add_resource_to(
            character_id=character_doc.id,
            resource_id=input_.resource_id,
            quantity=input_.quantity,
            commit=False,
        )

        cost = self.get_cost(character, input_=input_)
        if cost is None:
            raise RollingError("Cost compute should not be None !")

        self._kernel.character_lib.reduce_action_points(character.id, cost, commit=False)
        self._kernel.server_db_session.commit()

        return Description(
            title=f"{input_.quantity} {self._kernel.translation.get(resource.unit)} récupéré",
            footer_links=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements")
            ],
        )
