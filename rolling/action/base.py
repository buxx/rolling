# coding: utf-8
import dataclasses

import abc
import serpyco
import typing
from urllib.parse import urlencode

from guilang.description import Description
from rolling.model.event import WebSocketEvent
from rolling.rolling_types import ActionType
from rolling.server.controller.url import CHARACTER_ACTION
from rolling.server.controller.url import WITH_BUILD_ACTION
from rolling.server.controller.url import WITH_CHARACTER_ACTION
from rolling.server.controller.url import WITH_RESOURCE_ACTION
from rolling.server.controller.url import WITH_STUFF_ACTION
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


def remove_none_values(dict_: dict) -> dict:
    new_dict = dict(dict_)
    for key, value in list(new_dict.items()):
        if value is None:
            del new_dict[key]
    return new_dict


def get_character_action_url(
    character_id: str, action_type: ActionType, action_description_id: str, query_params: dict
) -> str:
    query_params = remove_none_values(query_params)
    base_url = CHARACTER_ACTION.format(
        character_id=character_id,
        action_type=action_type.value,
        action_description_id=action_description_id,
    )
    return f"{base_url}?{urlencode(query_params)}"


def get_with_build_action_url(
    character_id: str,
    build_id: int,
    action_type: ActionType,
    action_description_id: str,
    query_params: dict,
) -> str:
    query_params = remove_none_values(query_params)
    base_url = WITH_BUILD_ACTION.format(
        character_id=character_id,
        action_type=action_type.value,
        build_id=str(build_id),
        action_description_id=action_description_id,
    )
    return f"{base_url}?{urlencode(query_params)}"


def get_with_stuff_action_url(
    character_id: str,
    action_type: ActionType,
    stuff_id: int,
    query_params: dict,
    action_description_id: str,
) -> str:
    query_params = remove_none_values(query_params)
    base_url = WITH_STUFF_ACTION.format(
        character_id=character_id,
        action_type=action_type.value,
        stuff_id=str(stuff_id),
        action_description_id=action_description_id,
    )
    return f"{base_url}?{urlencode(query_params)}"


def get_with_resource_action_url(
    character_id: str,
    action_type: ActionType,
    resource_id: str,
    query_params: dict,
    action_description_id: str,
) -> str:
    query_params = remove_none_values(query_params)
    base_url = WITH_RESOURCE_ACTION.format(
        character_id=character_id,
        action_type=action_type.value,
        resource_id=resource_id,
        action_description_id=action_description_id,
    )
    return f"{base_url}?{urlencode(query_params)}"


def get_with_character_action_url(
    character_id: str,
    action_type: ActionType,
    with_character_id: str,
    query_params: dict,
    action_description_id: str,
) -> str:
    query_params = remove_none_values(query_params)
    base_url = WITH_CHARACTER_ACTION.format(
        character_id=character_id,
        action_type=action_type.value,
        with_character_id=with_character_id,
        action_description_id=action_description_id,
    )
    return f"{base_url}?{urlencode(query_params)}"


def get_character_actions_url(character: "CharacterModel") -> str:
    return f"/_describe/character/{character.id}/on_place_actions"


@dataclasses.dataclass
class ActionDescriptionModel:
    id: str
    action_type: ActionType
    base_cost: float
    properties: typing.Dict[str, typing.Any]
    name: typing.Optional[str] = None


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
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        pass

    @classmethod
    def input_model_from_request(cls, parameters: typing.Dict[str, typing.Any]) -> typing.Any:
        return cls.input_model_serializer.load(parameters)

    @property
    def description(self) -> ActionDescriptionModel:
        return self._description


class WithStuffAction(Action):
    @abc.abstractmethod
    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
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

    def get_cost(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        input_: typing.Optional[typing.Any] = None,
    ) -> typing.Optional[float]:
        return self._description.base_cost

    @abc.abstractmethod
    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> Description:
        pass


class WithBuildAction(Action):
    @abc.abstractmethod
    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        pass

    @abc.abstractmethod
    def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: typing.Any
    ) -> None:
        pass

    @abc.abstractmethod
    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        pass

    def get_cost(
        self, character: "CharacterModel", build_id: int, input_: typing.Optional[typing.Any] = None
    ) -> typing.Optional[float]:
        return self._description.base_cost

    @abc.abstractmethod
    def perform(
        self, character: "CharacterModel", build_id: int, input_: typing.Any
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

    def get_cost(
        self,
        character: "CharacterModel",
        resource_id: str,
        input_: typing.Optional[typing.Any] = None,
    ) -> typing.Optional[float]:
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
    def check_request_is_possible(self, character: "CharacterModel", input_: typing.Any) -> None:
        pass

    @abc.abstractmethod
    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        pass

    @abc.abstractmethod
    def perform(self, character: "CharacterModel", input_: typing.Any) -> Description:
        pass

    def perform_from_event(
        self, character: "CharacterModel", input_: typing.Any
    ) -> typing.Tuple[typing.List[WebSocketEvent], typing.List[WebSocketEvent]]:
        """
        return: [0]: all zone websockets; [1]: sender socket
        """
        pass

    def get_cost(
        self, character: "CharacterModel", input_: typing.Optional[typing.Any] = None
    ) -> typing.Optional[float]:
        return self._description.base_cost


class WithCharacterAction(Action):
    @abc.abstractmethod
    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        pass

    @abc.abstractmethod
    def check_request_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: typing.Any
    ) -> None:
        pass

    @abc.abstractmethod
    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        pass

    def get_cost(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: typing.Optional[typing.Any] = None,
    ) -> typing.Optional[float]:
        return self._description.base_cost

    @abc.abstractmethod
    def perform(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: typing.Any
    ) -> Description:
        pass
