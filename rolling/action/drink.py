# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import CharacterAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import CantEmpty
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
    from rolling.model.stuff import StuffModel
    from rolling.server.document.character import CharacterDocument
    from rolling.server.document.stuff import StuffDocument


@dataclasses.dataclass
class DrinkResourceModel:
    resource_id: str


@dataclasses.dataclass
class DrinkStuffModel:
    stuff_id: int = serpyco.field(cast_on_load=True)
    all_possible: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=0
    )


class DrinkResourceAction(CharacterAction):
    exclude_from_actions_page = True
    input_model: typing.Type[DrinkResourceModel] = DrinkResourceModel
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
            "like_water": action_config_raw["like_water"],
            "consume_per_tick": action_config_raw["consume_per_tick"],
        }

    def check_is_possible(self, character: "CharacterModel") -> None:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        for production in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        ):
            if production.resource.id in accept_resources_ids:
                return

        raise ImpossibleAction("Il n'y a pas à boire à proximité")

    def check_request_is_possible(
        self, character: "CharacterModel", input_: DrinkResourceModel
    ) -> None:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        for production in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        ):
            if (
                production.resource.id == input_.resource_id
                and input_.resource_id in accept_resources_ids
            ):
                return

        raise WrongInputError(f"Il n'y a pas de {input_.resource_id} à proximité")

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        character_actions: typing.List[CharacterActionLink] = []
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]

        for production in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        ):
            if production.resource.id in accept_resources_ids:
                query_params = self.input_model(resource_id=production.resource.id)
                character_actions.append(
                    CharacterActionLink(
                        name=f"Boire {production.resource.name}",
                        link=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.DRINK_RESOURCE,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(query_params),
                        ),
                        cost=self.get_cost(character),
                    )
                )

        return character_actions

    def perform(self, character: "CharacterModel", input_: input_model) -> Description:
        character_doc = self._character_lib.get_document(character.id)
        effects: typing.List[
            CharacterEffectDescriptionModel
        ] = self._description.properties["effects"]

        for effect in effects:
            self._effect_manager.enable_effect(character_doc, effect)

        # NOTE: consider here infinite resource
        character_doc.thirst = 0.0
        self._kernel.server_db_session.add(character_doc)
        self._kernel.server_db_session.commit()

        return Description(title="Vous avez bu")


class DrinkStuffAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[DrinkStuffModel] = DrinkStuffModel
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
            "like_water": action_config_raw["like_water"],
            "consume_per_tick": action_config_raw["consume_per_tick"],
        }

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        # TODO BS 2019-07-31: check is owned stuff
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        if (
            stuff.filled_with_resource is not None
            and stuff.filled_with_resource in accept_resources_ids
        ):
            return

        raise ImpossibleAction(f"Il n'y a pas de quoi boire la dedans")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        # TODO BS 2019-07-31: check is owned stuff
        self.check_is_possible(character, stuff)

        if stuff.filled_value < self._description.properties["consume_per_tick"]:
            raise WrongInputError(f"Pas assez pour boire")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        if (
            stuff.filled_with_resource is not None
            and stuff.filled_with_resource in accept_resources_ids
        ):
            resource_description = self._kernel.game.config.resources[
                stuff.filled_with_resource
            ]
            return [
                CharacterActionLink(
                    name=f"Boire {resource_description.name}",
                    link=self._get_url(character, stuff, all_possible=False),
                    cost=self.get_cost(character, stuff),
                )
            ]

        return []

    def _get_url(
        self, character: "CharacterModel", stuff: "StuffModel", all_possible: bool
    ) -> str:
        return get_with_stuff_action_url(
            character.id,
            ActionType.DRINK_STUFF,
            query_params={
                "stuff_id": stuff.id,
                "all_possible": 1 if all_possible else 0,
            },
            stuff_id=stuff.id,
            action_description_id=self._description.id,
        )

    @classmethod
    def drink(
        cls,
        kernel: "Kernel",
        character_doc: "CharacterDocument",
        stuff_doc: "StuffDocument",
        all_possible: bool,
        consume_per_tick: float,
    ) -> None:
        while True:
            not_enough_resource_exc = None

            try:
                stuff_doc.empty(
                    kernel, remove_value=consume_per_tick, force_before_raise=True
                )
            except CantEmpty:
                break
            except NotEnoughResource as exc:
                not_enough_resource_exc = exc

            reduce_thirst_by = kernel.game.config.thirst_change_per_tick
            if not_enough_resource_exc:
                reduce_thirst_by = reduce_thirst_by * (
                    not_enough_resource_exc.available_quantity / consume_per_tick
                )

            character_doc.thirst = max(
                0.0, float(character_doc.thirst) - reduce_thirst_by
            )
            kernel.server_db_session.add(stuff_doc)
            kernel.server_db_session.add(character_doc)
            kernel.server_db_session.commit()

            if not_enough_resource_exc:
                break

            if (
                not all_possible
                or float(character_doc.thirst)
                <= kernel.game.config.stop_auto_drink_thirst
            ):
                break

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        character_doc = self._character_lib.get_document(character.id)

        stuff_doc = self._kernel.stuff_lib.get_stuff_doc(stuff.id)
        self.drink(
            self._kernel,
            character_doc,
            stuff_doc,
            all_possible=bool(input_.all_possible),
            consume_per_tick=self._description.properties["consume_per_tick"],
        )

        return Description(
            title="Boire",
            items=[
                Part(
                    text=(
                        f"Etat de votre soif: "
                        f"{self._kernel.character_lib.get_thirst_sentence(character_doc.thirst)}"
                    )
                ),
                Part(
                    label="Boire encore",
                    is_link=True,
                    form_values_in_query=True,
                    form_action=self._get_url(character, stuff, all_possible=False),
                ),
                Part(
                    label="Boire jusqu'à plus soif",
                    is_link=True,
                    form_values_in_query=True,
                    form_action=self._get_url(character, stuff, all_possible=True),
                ),
            ],
        )
