# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from rolling.action.base import CharacterAction
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class EmptyModel:
    pass


class TravelAction(CharacterAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass  # always authorize display travel description page

    async def check_request_is_possible(
        self, character: "CharacterModel", input_: typing.Any
    ) -> None:
        self.check_is_possible(character)

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        action_links: typing.List[CharacterActionLink] = []

        for world_row_i_modifier, world_col_i_modifier, direction_name in (
            (-1, -1, "Nord-Ouest"),
            (-1, 0, "Nord"),
            (-1, 1, "Nord-Est"),
            (0, 1, "Est"),
            (1, 1, "Sud-Est"),
            (1, 0, "Sud"),
            (1, -1, "Sud-Ouest"),
            (0, -1, "Ouest"),
        ):
            new_world_row_i = character.world_row_i + world_row_i_modifier
            new_world_col_i = character.world_col_i + world_col_i_modifier
            action_links.append(
                CharacterActionLink(
                    name=f"Voyager vers {direction_name}",
                    link=(
                        f"/_describe/character/{character.id}"
                        f"/move-to-zone/{new_world_row_i}/{new_world_col_i}"
                    ),
                    # FIXME BS NOW: pas ici on dirait ...
                    # back_url=get_character_action_url(
                    #     character_id=character.id,
                    #     action_type=ActionType.TRAVEL,
                    #     query_params={},
                    #     action_description_id=self._description.id,
                    # ),
                    group_name="Voyager",
                )
            )

        return action_links

    async def perform(
        self, character: "CharacterModel", input_: typing.Any
    ) -> Description:
        pass  # action links are descriptions
