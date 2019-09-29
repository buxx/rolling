# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_resource_action_url
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
class EatResourceModel:
    pass


@dataclasses.dataclass
class EatStuffModel:
    pass


class EatResourceAction(WithResourceAction):
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
            "require": action_config_raw["require"],
        }

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        accept_resources_ids = [
            rd.id for rd in self._description.properties["accept_resources"]
        ]
        if resource_id in accept_resources_ids:
            return

        raise ImpossibleAction("Non consommable")

    def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: EatResourceModel
    ) -> None:
        self.check_is_possible(character, resource_id)

        # TODO BS 2019-09-14: perf
        carried_resource = next(
            (
                cr
                for cr in self._kernel.resource_lib.get_carried_by(character.id)
                if cr.id == resource_id
            )
        )

        require = self._description.properties["require"]
        if carried_resource.quantity >= require:
            return

        unit_name = self._kernel.translation.get(carried_resource.unit)
        raise ImpossibleAction(
            f"Vous ne possédez pas assez de {carried_resource.name} "
            f"({require} {unit_name} requis)"
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
                    link=get_with_resource_action_url(
                        character_id=character.id,
                        action_type=ActionType.EAT_RESOURCE,
                        resource_id=resource_id,
                        query_params={},
                    ),
                    cost=None,
                )
            ]

        return []

    def perform(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> Description:
        character_doc = self._character_lib.get_document(character.id)
        effects: typing.List[
            CharacterEffectDescriptionModel
        ] = self._description.properties["effects"]

        self._kernel.resource_lib.reduce(
            character.id,
            resource_id,
            quantity=self._description.properties["require"],
            commit=False,
        )
        for effect in effects:
            self._effect_manager.enable_effect(character_doc, effect)

        self._kernel.server_db_session.add(character_doc)
        self._kernel.server_db_session.commit()

        return Description(
            title="Action effectué", items=[Part(label="Continue", go_back_zone=True)]
        )


class EatStuffAction(WithStuffAction):
    input_model: typing.Type[EatStuffModel] = EatStuffModel
    input_model_serializer = serpyco.Serializer(input_model)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {
            "accept_stuff_ids": action_config_raw["accept_stuffs"],
            "effects": [
                game_config.character_effects[e]
                for e in action_config_raw["character_effects"]
            ],
        }

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        # TODO BS 2019-07-31: check is owned stuff
        if stuff.stuff_id in self._description.properties["accept_stuff_ids"]:
            return

        raise ImpossibleAction(f"Vous ne pouvez pas le manger")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        if stuff.stuff_id in self._description.properties["accept_stuff_ids"]:
            return [
                CharacterActionLink(
                    name=f"Manger {stuff.name}",
                    link=get_with_stuff_action_url(
                        character.id,
                        ActionType.EAT_STUFF,
                        query_params={},
                        stuff_id=stuff.id,
                    ),
                    cost=self.get_cost(character, stuff),
                )
            ]

        return []

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        character_doc = self._character_lib.get_document(character.id)
        effects: typing.List[
            CharacterEffectDescriptionModel
        ] = self._description.properties["effects"]

        self._kernel.stuff_lib.destroy(stuff.id, commit=False)
        for effect in effects:
            self._effect_manager.enable_effect(character_doc, effect)

        self._kernel.server_db_session.add(character_doc)
        self._kernel.server_db_session.commit()

        return Description(
            title="Action effectué", items=[Part(label="Continue", go_back_zone=True)]
        )
