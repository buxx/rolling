import dataclasses

import serpyco
from rolling.action.base import CharacterAction, get_character_action_url
import typing
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from guilang.description import Description
from guilang.description import Part
from guilang.description import Type

from rolling.server.link import CharacterActionLink, ExploitableTile
from rolling.util import get_on_and_around_coordinates


if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class TakeModel:
    zone_row_i: int = serpyco.number_field(cast_on_load=True)
    zone_col_i: int = serpyco.number_field(cast_on_load=True)


class TakeAction(CharacterAction):
    exclude_from_actions_page = True
    input_model = TakeModel
    input_model_serializer: serpyco.Serializer(TakeModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass

    async def check_request_is_possible(
        self, character: "CharacterModel", input_: typing.Any
    ) -> None:
        pass

    def get_cost(
        self, character: "CharacterModel", input_: typing.Optional[typing.Any] = None
    ) -> typing.Optional[float]:
        return 0.0

    def get_quick_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        inspect_zone_positions = get_on_and_around_coordinates(
            character.zone_row_i, character.zone_col_i
        )
        stuffs: typing.List[typing.Tuple[(int, int), StuffModel]] = []
        resources: typing.List[
            typing.Tuple[(int, int), CarriedResourceDescriptionModel]
        ] = []

        for row_i, col_i in inspect_zone_positions:
            for stuff in self._kernel.stuff_lib.get_zone_stuffs(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=row_i,
                zone_col_i=col_i,
            ):
                stuffs.append(((row_i, col_i), stuff))

            for resource in self._kernel.resource_lib.get_ground_resource(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=row_i,
                zone_col_i=col_i,
            ):
                resources.append(((row_i, col_i), resource))

        if stuffs or resources:
            exploitable_tiles = []

            for (row_i, col_i), stuff in stuffs:
                exploitable_tiles.append(
                    ExploitableTile(
                        zone_row_i=row_i,
                        zone_col_i=col_i,
                        classes=[stuff.stuff_id],
                    )
                )

            for (row_i, col_i), resource in resources:
                exploitable_tiles.append(
                    ExploitableTile(
                        zone_row_i=row_i,
                        zone_col_i=col_i,
                        classes=[resource.id],
                    )
                )

            return [
                CharacterActionLink(
                    name="Ramasser",
                    link=get_character_action_url(
                        character_id=character.id,
                        action_type=ActionType.TAKE_AROUND,
                        action_description_id=self._description.id,
                        query_params={},
                    ),
                    cost=None,
                    classes1=["TAKE"],
                    all_tiles_at_once=False,
                    exploitable_tiles=exploitable_tiles,
                    quick_action_key="P",
                )
            ]

        return []

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return []

    async def perform(
        self, character: "CharacterModel", input_: TakeModel
    ) -> Description:
        for stuff in self._kernel.stuff_lib.get_zone_stuffs(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.zone_row_i,
            zone_col_i=input_.zone_col_i,
        ):
            self._kernel.stuff_lib.set_carried_by(stuff.id, character_id=character.id)
            await self._kernel.stuff_lib.send_zone_ground_stuff_removed(
                stuff_id=stuff.id,
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=input_.zone_row_i,
                zone_col_i=input_.zone_col_i,
            )

        for resource in self._kernel.resource_lib.get_ground_resource(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.zone_row_i,
            zone_col_i=input_.zone_col_i,
        ):
            self._kernel.resource_lib.reduce_on_ground(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=input_.zone_row_i,
                zone_col_i=input_.zone_col_i,
                resource_id=resource.id,
                quantity=resource.quantity,
            )
            self._kernel.resource_lib.add_resource_to(
                character_id=character.id,
                resource_id=resource.id,
                quantity=resource.quantity,
            )
            await self._kernel.resource_lib.send_zone_ground_resource_removed(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=input_.zone_row_i,
                zone_col_i=input_.zone_col_i,
                resource_id=resource.id,
            )

        return Description(
            title="Récupéré",
            quick_action_response="Récupéré",
            exploitable_success=(input_.zone_row_i, input_.zone_col_i),
        )
