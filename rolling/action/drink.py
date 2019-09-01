# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import CharacterAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import ImpossibleAction
from rolling.model.effect import CharacterEffectDescriptionModel
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel
    from rolling.game.base import GameConfig


@dataclasses.dataclass
class DrinkResourceModel:
    resource_type: str


@dataclasses.dataclass
class DrinkStuffModel:
    stuff_id: int = serpyco.field(cast_on_load=True)


class DrinkResourceAction(CharacterAction):
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
        }

    def check_is_possible(self, character: "CharacterModel") -> None:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        for resource in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            # FIXME BS NOW: from config !!!
            material_type="LIQUID",
        ):
            if resource.type_.value in accept_resources_ids:
                return

        raise ImpossibleAction("Il n'y a pas à boire à proximité")

    def check_request_is_possible(
        self, character: "CharacterModel", input_: DrinkResourceModel
    ) -> None:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        for resource in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            # FIXME BS NOW: from config !!!
            material_type="LIQUID",
        ):
            if (
                resource.type_ == input_.resource_type
                and input_.resource_type.value in accept_resources_ids
            ):
                return

        raise ImpossibleAction(
            f"Il n'y a pas de {input_.resource_type.value} à proximité"
        )

    def get_character_action_links(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        character_actions: typing.List[CharacterActionLink] = []
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]

        for resource in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            # FIXME BS NOW: from config !!!
            material_type="LIQUID",
        ):
            if resource.type_.value in accept_resources_ids:
                query_params = self.input_model(resource_type=resource.type_.value)
                character_actions.append(
                    CharacterActionLink(
                        name=f"Drink {resource.name}",
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
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]

        if input_.resource_type.value in accept_resources_ids:
            effects: typing.List[
                CharacterEffectDescriptionModel
            ] = self._description.properties["effects"]

            for effect in effects:
                self._effect_manager.enable_effect(character_doc, effect)
                self._kernel.server_db_session.add(character_doc)
                self._kernel.server_db_session.commit()

        return Description(
            title="Action effectué", items=[Part(label="Continue", go_back_zone=True)]
        )


class DrinkStuffAction(WithStuffAction):
    input_model = typing.Type[DrinkStuffModel]

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
            and stuff.filled_with_resource.value in accept_resources_ids
        ):
            return

        raise ImpossibleAction(f"Il n'y a pas de quoi boire la dedans")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        # TODO BS 2019-07-31: check is owned stuff
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]

        if (
            stuff.filled_with_resource is not None
            and stuff.filled_with_resource.value in accept_resources_ids
        ):
            return

        raise ImpossibleAction(f"Il n'y a pas de quoi boire la dedans")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        if (
            stuff.filled_with_resource is not None
            and stuff.filled_with_resource.value in accept_resources_ids
        ):
            query_params = self.input_model(stuff_id=stuff.id)
            return [
                CharacterActionLink(
                    name=f"Drink {stuff.filled_with_resource.value}",
                    link=get_with_stuff_action_url(
                        character.id,
                        ActionType.DRINK_STUFF,
                        query_params=self.input_model_serializer.dump(query_params),
                        stuff_id=stuff.id,
                    ),
                    cost=self.get_cost(character, stuff),
                )
            ]

        return []

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        message = self._kernel.character_lib.drink_stuff(character.id, stuff.id)

        return Description(
            title=message, items=[Part(label="Continuer", go_back_zone=True)]
        )
