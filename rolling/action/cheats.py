# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_character_actions_url
from rolling.exception import ImpossibleAction
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class CheatsModel:
    cheat_id: typing.Optional[str] = None


class CheatsCharacterAction(CharacterAction):
    input_model = CheatsModel
    input_model_serializer = serpyco.Serializer(CheatsModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def _get_available_cheats(self, character: "CharacterModel") -> typing.Set[str]:
        available_cheats: typing.Set[str] = set()

        if "*" in self._kernel.game.config.cheats:
            available_cheats.update(set(self._kernel.game.config.cheats["*"]))

        if character.id in self._kernel.game.config.cheats:
            available_cheats.update(set(self._kernel.game.config.cheats[character.id]))

        return available_cheats

    def check_is_possible(self, character: "CharacterModel") -> None:
        if not self._get_available_cheats(character):
            raise ImpossibleAction("Vous n'avez pas accès")

    async def check_request_is_possible(
        self, character: "CharacterModel", input_: CheatsModel
    ) -> None:
        if not input_.cheat_id:
            raise ImpossibleAction("Choix du cheat nécessaire")

        if input_.cheat_id in self._get_available_cheats(character):
            return

        raise ImpossibleAction("Ce cheat ne vous est pas accessible")

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        available_cheats = self._get_available_cheats(character)
        action_links: typing.List[CharacterActionLink] = []

        if "increase_ap" in available_cheats:
            action_links.append(
                CharacterActionLink(
                    name="(Triche) S'ajouter des PA",
                    link=get_character_action_url(
                        character_id=character.id,
                        action_type=ActionType.CHEATS,
                        action_description_id=self._description.id,
                        query_params={"cheat_id": "increase_ap"},
                    ),
                    group_name="Triche",
                )
            )

        if "reduce_tiredness" in available_cheats:
            action_links.append(
                CharacterActionLink(
                    name="(Triche) Réduire la fatigue",
                    link=get_character_action_url(
                        character_id=character.id,
                        action_type=ActionType.CHEATS,
                        action_description_id=self._description.id,
                        query_params={"cheat_id": "reduce_tiredness"},
                    ),
                    group_name="Triche",
                )
            )

        return action_links

    async def perform(
        self, character: "CharacterModel", input_: CheatsModel
    ) -> Description:
        if input_.cheat_id == "increase_ap":
            character_doc = self._kernel.character_lib.get_document(character.id)
            character_doc.action_points = 24.0
            self._kernel.server_db_session.add(character_doc)
            self._kernel.server_db_session.commit()
            return Description(
                title="Points d'actions rechargés",
                back_url=get_character_actions_url(character),
            )
        if input_.cheat_id == "reduce_tiredness":
            self._kernel.character_lib.reduce_tiredness(character.id, 100)
            return Description(
                title="Plus de fatigue", back_url=get_character_actions_url(character)
            )
