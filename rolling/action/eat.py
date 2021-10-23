# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithResourceAction
from rolling.action.base import get_with_resource_action_url
from rolling.exception import ImpossibleAction
from rolling.exception import NotEnoughResource
from rolling.exception import WrongInputError
from rolling.model.effect import CharacterEffectDescriptionModel
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.server.document.character import CharacterDocument
    from rolling.server.document.stuff import StuffDocument


@dataclasses.dataclass
class EatResourceModel:
    all_possible: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=0
    )


class EatResourceAction(WithResourceAction):
    exclude_from_actions_page = True
    input_model: typing.Type[EatResourceModel] = EatResourceModel
    input_model_serializer = serpyco.Serializer(input_model)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {
            "accept_resources": [
                game_config.resources[r] for r in action_config_raw["accept_resources"]
            ],
            "effects": [
                game_config.character_effects[e]
                for e in action_config_raw["character_effects"]
            ],
            "consume_per_tick": action_config_raw["consume_per_tick"],
        }

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        if resource_id in accept_resources_ids:
            return

        raise ImpossibleAction("Non consommable")

    async def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: EatResourceModel
    ) -> None:
        self.check_is_possible(character, resource_id)

        # FIXME BS 2019-09-14: perf
        carried_resource = next(
            (
                cr
                for cr in self._kernel.resource_lib.get_carried_by(character.id)
                if cr.id == resource_id
            )
        )

        consume_per_tick = self._description.properties["consume_per_tick"]
        if carried_resource.quantity >= consume_per_tick:
            return

        unit_name = self._kernel.translation.get(carried_resource.unit)
        raise WrongInputError(
            f"Vous ne possédez pas/plus assez de {carried_resource.name} "
            f"({consume_per_tick} {unit_name} requis)"
        )

    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        # TODO BS 2019-09-14: perf
        carried_resource = next(
            (
                cr
                for cr in self._kernel.resource_lib.get_carried_by(character.id)
                if cr.id == resource_id
            )
        )

        if carried_resource.id in accept_resources_ids:
            return [
                # FIXME BS NOW: il semblerait que que comme on ne donne pas le description_id,
                # lorsque on veux consommer la resource, l'action factory prend la première, et donc
                # pas la bonne. Revoir ça, je pense qu'il faut systématiquement donner un
                # description_id. Voir les conséquences.
                CharacterActionLink(
                    name=f"Manger {carried_resource.name}",
                    link=self._get_url(
                        character=character, resource_id=resource_id, all_possible=False
                    ),
                    cost=None,
                )
            ]

        return []

    def _get_url(
        self, character: "CharacterModel", resource_id: str, all_possible: bool
    ) -> str:
        return get_with_resource_action_url(
            character_id=character.id,
            action_type=ActionType.EAT_RESOURCE,
            resource_id=resource_id,
            query_params={"all_possible": 1 if all_possible else 0},
            action_description_id=self._description.id,
        )

    @classmethod
    def eat(
        cls,
        kernel: "Kernel",
        character_doc: "CharacterDocument",
        resource_id: str,
        all_possible: bool,
        consume_per_tick: float,
    ) -> None:
        while True:
            not_enough_resource_exc = None

            try:
                kernel.resource_lib.reduce_carried_by(
                    character_doc.id,
                    resource_id,
                    quantity=consume_per_tick,
                    commit=False,
                    force_before_raise=True,
                )
            except NotEnoughResource as exc:
                not_enough_resource_exc = exc

            reduce_hunger_by = kernel.game.config.hunger_change_per_tick
            if not_enough_resource_exc:
                reduce_hunger_by = reduce_hunger_by * (
                    not_enough_resource_exc.available_quantity / consume_per_tick
                )

            character_doc.hunger = max(
                0.0, float(character_doc.hunger) - reduce_hunger_by
            )
            kernel.server_db_session.add(character_doc)
            kernel.server_db_session.commit()

            if not_enough_resource_exc:
                break

            if (
                not all_possible
                or float(character_doc.hunger)
                <= kernel.game.config.stop_auto_eat_hunger
            ):
                break

    async def perform(
        self, character: "CharacterModel", resource_id: str, input_: EatResourceModel
    ) -> Description:
        character_doc = self._character_lib.get_document(character.id)

        self.eat(
            self._kernel,
            character_doc=character_doc,
            resource_id=resource_id,
            all_possible=bool(input_.all_possible),
            consume_per_tick=self._description.properties["consume_per_tick"],
        )

        return Description(
            title="Action effectué",
            items=[
                Part(
                    text=(
                        f"Etat de votre faim: "
                        f"{self._kernel.character_lib.get_hunger_sentence(character_doc.hunger)}"
                    )
                ),
                Part(
                    label="Manger encore",
                    is_link=True,
                    form_values_in_query=True,
                    form_action=self._get_url(
                        character=character, resource_id=resource_id, all_possible=False
                    ),
                ),
                Part(
                    label="Manger jusqu'à plus faim",
                    is_link=True,
                    form_values_in_query=True,
                    form_action=self._get_url(
                        character=character, resource_id=resource_id, all_possible=True
                    ),
                ),
            ],
            back_url=f"/_describe/character/{character.id}/inventory",
        )
