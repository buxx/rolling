import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithBuildAction
from rolling.action.base import get_with_build_action_url
from rolling.exception import ImpossibleAction
from rolling.exception import NotEnoughActionPoints
from rolling.exception import WrongInputError
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.util import get_health_percent_sentence

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class DestroyBuildModel:
    spent_1_ap: typing.Optional[int] = serpyco.number_field(
        default=0, cast_on_load=True
    )
    spent_6_ap: typing.Optional[int] = serpyco.number_field(
        default=0, cast_on_load=True
    )
    spent_all_ap: typing.Optional[int] = serpyco.number_field(
        default=0, cast_on_load=True
    )


class DestroyBuildAction(WithBuildAction):
    exclude_from_actions_page: bool = True
    input_model = DestroyBuildModel
    input_model_serializer = serpyco.Serializer(DestroyBuildModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        if build_doc.health is None:
            raise ImpossibleAction("Ce bâtiment ne peut être détruit")

    def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: DestroyBuildModel
    ) -> None:
        self.check_is_possible(character, build_id=build_id)

    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name="Détruire",
                link=self._get_url(
                    character=character, build_id=build_id, input_=DestroyBuildModel()
                ),
            )
        ]

    def _get_url(
        self, character: "CharacterModel", build_id: int, input_: DestroyBuildModel
    ) -> str:
        return get_with_build_action_url(
            action_description_id=self._description.id,
            action_type=ActionType.DESTROY_BUILD,
            build_id=build_id,
            character_id=character.id,
            query_params=self.input_model_serializer.dump(input_),
        )

    def perform(
        self, character: "CharacterModel", build_id: int, input_: DestroyBuildModel
    ) -> Description:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        destroy_robustness_per_ap = self._kernel.game.config.destroy_robustness_per_ap

        if input_.spent_1_ap or input_.spent_6_ap or input_.spent_all_ap:
            to_spent = 999_999_999
            if input_.spent_1_ap:
                to_spent = 1
            if input_.spent_6_ap:
                to_spent = 6

            for _ in range(to_spent):
                try:
                    self._kernel.character_lib.reduce_action_points(
                        character_id=character.id,
                        cost=1.0,
                        check=True,
                    )
                except NotEnoughActionPoints:
                    raise ImpossibleAction("Pas assez de points d'actions")

                build_doc.health = build_doc.health - destroy_robustness_per_ap

                if build_doc.health <= 0:
                    break

        if build_doc.health <= 0:
            self._kernel.build_lib.delete(build_id)
            return Description(back_to_zone=True)

        build_health_percent = int(
            round((build_doc.health / build_description.robustness) * 100)
        )
        return Description(
            title=f"Détruire {build_description.name}",
            items=[
                Part(
                    text=f"État : {get_health_percent_sentence(build_health_percent)}"
                ),
                Part(
                    is_link=True,
                    label="Dépenser 1 AP",
                    form_action=self._get_url(
                        character=character,
                        build_id=build_id,
                        input_=DestroyBuildModel(
                            spent_1_ap=1,
                        ),
                    ),
                ),
                Part(
                    is_link=True,
                    label="Dépenser maximum 6 AP",
                    form_action=self._get_url(
                        character=character,
                        build_id=build_id,
                        input_=DestroyBuildModel(
                            spent_6_ap=1,
                        ),
                    ),
                ),
                Part(
                    is_link=True,
                    label="Y passer le temps nécessaire",
                    form_action=self._get_url(
                        character=character,
                        build_id=build_id,
                        input_=DestroyBuildModel(
                            spent_all_ap=1,
                        ),
                    ),
                ),
            ],
        )
