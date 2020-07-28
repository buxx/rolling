# coding: utf-8
import typing

from rolling.action.base import WithResourceAction, WithStuffAction
from rolling.exception import ImpossibleAction, ErrorWhenConsume
from rolling.model.character import CharacterModel
from rolling.model.consume import Consumeable
from rolling.model.stuff import StuffModel


class EatResourceFromCharacterInventory(Consumeable):
    def __init__(self, character: CharacterModel, resource_id: str, action: WithResourceAction, input_: typing.Any) -> None:
        self._character = character
        self._action = action
        self._resource_id = resource_id
        self._input_ = input_

    def consume(self) -> None:
        try:
            self._action.perform(self._character, resource_id=self._resource_id, input_=self._input_)
        except ImpossibleAction as exc:
            raise ErrorWhenConsume(str(exc)) from exc


class EatStuffFromCharacterInventory(Consumeable):
    def __init__(self, character: CharacterModel, stuff: StuffModel, action: WithStuffAction, input_: typing.Any) -> None:
        self._character = character
        self._action = action
        self._stuff = stuff
        self._input_ = input_

    def consume(self) -> None:
        try:
            self._action.perform(self._character, stuff=self._stuff, input_=self._input_)
        except ImpossibleAction as exc:
            raise ErrorWhenConsume(str(exc)) from exc
