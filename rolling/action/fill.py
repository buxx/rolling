# coding: utf-8
import typing

from rolling.action.base import WithStuffAction, get_with_stuff_action_url
from rolling.exception import ImpossibleAction
from rolling.model.types import MaterialType
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel, FillStuffWithResourceModel
    from rolling.model.stuff import StuffModel
    from rolling.game.base import GameConfig


class FillStuffAction(WithStuffAction):
    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        # FIXME BS 2019-08-02: material type en fonction de stuff fill_unity
        for fill_acceptable_type in [MaterialType.LIQUID, MaterialType.SANDY]:
            for resource in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=character.zone_row_i,
                zone_col_i=character.zone_col_i,
                material_type=fill_acceptable_type,
            ):
                return

        raise ImpossibleAction("Rien à proximité ne correspond")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: "FillStuffWithResourceModel",
    ) -> None:
        # TODO BS 2019-08-01: check owned
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []

        # FIXME BS 2019-08-02: material type en fonction de stuff fill_unity
        for fill_acceptable_type in [MaterialType.LIQUID, MaterialType.SANDY]:
            for resource in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=character.zone_row_i,
                zone_col_i=character.zone_col_i,
                material_type=fill_acceptable_type,
            ):
                query_params = dict(
                    resource_type=resource.type_.value,
                )
                actions.append(
                    CharacterActionLink(
                        name=f"Fill {stuff.name} with {resource.name}",
                        link=get_with_stuff_action_url(
                            character_id=character.id,
                            action_type=ActionType.FILL_STUFF,
                            stuff_id=stuff.id,
                            query_params=query_params,
                        ),
                        cost=self.get_cost(character, stuff),
                    )
                )

        return actions
