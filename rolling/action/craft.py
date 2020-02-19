# coding: utf-8
import typing

from guilang.description import Description
from rolling.action.base import WithResourceAction, WithStuffAction, get_with_resource_action_url, \
    get_with_stuff_action_url
from rolling.exception import RollingError, ImpossibleAction
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel
    from rolling.game.base import GameConfig


class BaseCraftStuff:
    @classmethod
    def _get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        for require in action_config_raw["require"]:
            if "resource" not in require and "stuff" not in require:
                raise RollingError(
                    "Misconfiguration for action "
                    "CraftStuffWithResourceAction/CraftStuffWithStuffAction (require "
                    "must contain stuff or resource key"
                )

        return {
            "required_one_of_stuff_ids": action_config_raw["required_one_of_stuffs"],
            "required_all_stuff_ids": action_config_raw["required_all_stuffs"],
            "required_one_of_skill_ids": action_config_raw["required_one_of_skills"],
            "required_all_skill_ids": action_config_raw["required_all_skills"],
            "required_one_of_ability_ids": action_config_raw["required_one_of_ability"],
            "produce": action_config_raw["produce"],
            "require": action_config_raw["require"],
        }


class CraftStuffWithResourceAction(WithResourceAction, BaseCraftStuff):
    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return cls._get_properties_from_config(game_config, action_config_raw)

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        # Consider action ca be possible (displayed in interface) if at least one of required
        # resources is owned by character
        carried = self._kernel.resource_lib.get_carried_by(character.id)
        carried_ids = [r.id for r in carried]

        for require in self._description.properties["require"]:
            if "resource" in require and require["resource"] in carried_ids:
                return

        raise ImpossibleAction("Aucune resource requise n'est possédé")

    def check_request_is_possible(self, character: "CharacterModel", resource_id: str,
                                  input_: typing.Any) -> None:
        pass

    def get_character_actions(self, character: "CharacterModel", resource_id: str) -> typing.List[
        CharacterActionLink]:
        try:
            self.check_is_possible(character, resource_id)
        except ImpossibleAction:
            return []

        return [
            CharacterActionLink(
                name=self._description.name,
                link=get_with_resource_action_url(
                    character_id=character.id,
                    action_type=ActionType.CRAFT_STUFF_WITH_RESOURCE,
                    action_description_id=self._description.id,
                    resource_id=resource_id,
                    query_params={},
                ),
                cost=self.get_cost(character, resource_id),
            )
        ]

    def perform(self, character: "CharacterModel", resource_id: str,
                input_: typing.Any) -> Description:
        pass


class CraftStuffWithStuffAction(WithStuffAction, BaseCraftStuff):
    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return cls._get_properties_from_config(game_config, action_config_raw)

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        # Consider action ca be possible (displayed in interface) if at least one of required stuff
        # is owned by character
        carried = self._kernel.stuff_lib.get_carried_by(character.id)
        carried_ids = [r.id for r in carried]

        for require in self._description.properties["require"]:
            if "stuff" in require and require["stuff"] in carried_ids:
                return

        raise ImpossibleAction("Aucune resource requise n'est possédé")

    def check_request_is_possible(self, character: "CharacterModel", stuff: "StuffModel",
                                  input_: typing.Any) -> None:
        pass

    def get_character_actions(self, character: "CharacterModel", stuff: "StuffModel") -> \
    typing.List[CharacterActionLink]:
        try:
            self.check_is_possible(character, stuff)
        except ImpossibleAction:
            return []

        return [
            CharacterActionLink(
                name=self._description.name,
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.CRAFT_STUFF_WITH_RESOURCE,
                    action_description_id=self._description.id,
                    stuff_id=stuff.id,
                    query_params={},
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

    def perform(self, character: "CharacterModel", stuff: "StuffModel",
                input_: typing.Any) -> Description:
        pass
