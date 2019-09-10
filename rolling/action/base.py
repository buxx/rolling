# coding: utf-8
import abc
import dataclasses
import typing
from urllib.parse import urlencode

import serpyco

from guilang.description import Description
from rolling.server.controller.url import CHARACTER_ACTION
from rolling.server.controller.url import WITH_RESOURCE_ACTION
from rolling.server.controller.url import WITH_STUFF_ACTION
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


def get_character_action_url(
    character_id: str,
    action_type: ActionType,
    action_description_id: str,
    query_params: dict,
) -> str:
    base_url = CHARACTER_ACTION.format(
        character_id=character_id,
        action_type=action_type.value,
        action_description_id=action_description_id,
    )
    return f"{base_url}?{urlencode(query_params)}"


def get_with_stuff_action_url(
    character_id: str, action_type: ActionType, stuff_id: int, query_params: dict
) -> str:
    base_url = WITH_STUFF_ACTION.format(
        character_id=character_id, action_type=action_type.value, stuff_id=str(stuff_id)
    )
    return f"{base_url}?{urlencode(query_params)}"


def get_with_resource_action_url(
    character_id: str, action_type: ActionType, resource_id: str, query_params: dict
) -> str:
    base_url = WITH_RESOURCE_ACTION.format(
        character_id=character_id,
        action_type=action_type.value,
        resource_id=resource_id,
    )
    return f"{base_url}?{urlencode(query_params)}"


@dataclasses.dataclass
class ActionDescriptionModel:
    id: str
    action_type: ActionType
    base_cost: float
    properties: dict


class Action(abc.ABC):
    input_model: typing.Type[object]
    input_model_serializer: serpyco.Serializer

    def __init__(self, kernel: "Kernel", description: ActionDescriptionModel) -> None:
        self._kernel = kernel
        self._description = description
        self._character_lib = kernel.character_lib
        self._effect_manager = kernel.effect_manager

    @classmethod
    @abc.abstractmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        pass


class WithStuffAction(Action):
    @abc.abstractmethod
    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        pass

    @abc.abstractmethod
    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> None:
        pass

    @abc.abstractmethod
    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        pass

    def get_cost(self, character: "CharacterModel", stuff: "StuffModel") -> float:
        return self._description.base_cost

    @abc.abstractmethod
    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> Description:
        pass


class WithResourceAction(Action):
    @abc.abstractmethod
    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        pass

    @abc.abstractmethod
    def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: typing.Any
    ) -> None:
        pass

    @abc.abstractmethod
    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        pass

    def get_cost(self, character: "CharacterModel", resource_id: str) -> float:
        return self._description.base_cost

    @abc.abstractmethod
    def perform(
        self, character: "CharacterModel", resource_id: str, input_: typing.Any
    ) -> Description:
        pass


class CharacterAction(Action):
    @abc.abstractmethod
    def check_is_possible(self, character: "CharacterModel") -> None:
        pass

    @abc.abstractmethod
    def check_request_is_possible(
        self, character: "CharacterModel", input_: typing.Any
    ) -> None:
        pass

    @abc.abstractmethod
    def get_character_action_links(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        pass

    @abc.abstractmethod
    def perform(self, character: "CharacterModel", input_: typing.Any) -> Description:
        pass

    def get_cost(self, character: "CharacterModel") -> float:
        return self._description.base_cost
