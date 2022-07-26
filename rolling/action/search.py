# coding: utf-8
import dataclasses

import random
import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.action.utils import check_common_is_possible
from rolling.action.utils import fill_base_action_properties
from rolling.exception import ImpossibleAction
from rolling.exception import RollingError
from rolling.exception import WrongInputError
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class SearchMaterialModel:
    ap: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


class SearchMaterialAction(CharacterAction):
    input_model = SearchMaterialModel
    input_model_serializer = serpyco.Serializer(SearchMaterialModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )

        for produce in action_config_raw["produce"]:
            if "resource" not in produce and "stuff" not in produce:
                raise RollingError(
                    "Misconfiguration for action SearchMaterialAction (produce "
                    f"must contain stuff or resource key ({action_config_raw})"
                )
            if "quantity_per_hour" not in produce or "random_loss" not in produce:
                raise RollingError(
                    "Misconfiguration for action SearchMaterialAction (produce "
                    f"must contain quantity_per_hour or random_loss key ({action_config_raw})"
                )

        properties.update({"produce": action_config_raw["produce"]})
        return properties

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass  # Always display these actions

    async def check_request_is_possible(
        self, character: "CharacterModel", input_: SearchMaterialModel
    ) -> None:
        check_common_is_possible(
            self._kernel, character=character, description=self._description
        )
        if input_.ap and character.action_points < input_.ap:
            raise WrongInputError(
                f"{character.name} ne possède pas assez de points d'actions"
            )

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        classes: typing.Optional[typing.List[str]] = None
        for produce in self._description.properties["produce"]:
            classes = [produce["resource"]]
            break

        return [
            CharacterActionLink(
                name=self._description.name,
                link=get_character_action_url(
                    character_id=character.id,
                    action_type=ActionType.SEARCH_MATERIAL,
                    action_description_id=self._description.id,
                    query_params={},
                ),
                cost=self.get_cost(character),
                group_name="Chercher du matériel/ressources",
                classes1=classes,
            )
        ]

    async def perform(
        self, character: "CharacterModel", input_: SearchMaterialModel
    ) -> Description:
        if not input_.ap:
            return Description(
                title=self._description.name,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.SEARCH_MATERIAL,
                            query_params=self.input_model_serializer.dump(input_),
                            action_description_id=self._description.id,
                        ),
                        items=[
                            Part(
                                label=f"Y passer combien de temps (PA) ?",
                                type_=Type.NUMBER,
                                name="ap",
                                default_value="1.0",
                                min_value=1.0,
                                max_value=character.action_points,
                            )
                        ],
                    )
                ],
            )

        ap_spent = input_.ap
        zone_state = self._kernel.game.world_manager.get_zone_state(
            world_row_i=character.world_row_i, world_col_i=character.world_col_i
        )
        found: typing.List[typing.Tuple[str, float]] = []
        for produce in self._description.properties["produce"]:
            resource_id = produce["resource"]
            quantity_per_hour = produce["quantity_per_hour"]
            random_loss = produce["random_loss"]
            quantity_found = ap_spent * quantity_per_hour
            # FIXME BS NOW: bonus with action config skill ?
            quantity_found = quantity_found - (
                quantity_found * random.randint(0, random_loss) / 100
            )

            # Test if zone contain absolute resource
            if zone_state.is_there_resource(
                resource_id, check_from_absolute=True, check_from_tiles=False
            ):
                zone_state.reduce_resource(resource_id, quantity_found, commit=False)
            # Test if zone contain resource in some tile
            elif zone_state.is_there_resource(
                resource_id, check_from_absolute=False, check_from_tiles=True
            ):
                zone_geography = zone_state.zone_map.source.geography
                (
                    extract_from_row_i,
                    extract_from_col_i,
                ) = zone_geography.get_random_tile_position_containing_resource(
                    resource_id, self._kernel
                )
                zone_state.reduce_resource_from_tile(
                    resource_id,
                    quantity_found,
                    tile_row_i=extract_from_row_i,
                    tile_col_i=extract_from_col_i,
                    commit=False,
                )
            else:
                continue

            found.append((resource_id, quantity_found))
            self._kernel.resource_lib.add_resource_to(
                character_id=character.id,
                resource_id=resource_id,
                quantity=quantity_found,
                commit=False,
            )
        parts: typing.List[Part] = []

        await self._kernel.character_lib.reduce_action_points(
            character_id=character.id, cost=input_.ap, commit=False
        )
        self._kernel.server_db_session.commit()

        for resource_id, quantity in found:
            resource_description = self._kernel.game.config.resources[resource_id]
            quantity_str = quantity_to_str(
                quantity, resource_description.unit, self._kernel
            )
            parts.append(Part(text=f"{quantity_str} de {resource_description.name}"))

        if not found:
            parts.append(
                Part(
                    text=(
                        "Vous n'avez rien trouvé ! Cela peut s'expliquer par de la malchance, "
                        "de l'incompétence, ou qu'il n'y en pas ici (si vous avez cherché quelque "
                        "chose que l'on ne trouve pas dans cette zone ...)"
                    )
                )
            )

        return Description(title="Vous avez récupéré", items=parts)
