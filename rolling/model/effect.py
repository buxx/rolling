# coding: utf-8
import dataclasses
import typing


@dataclasses.dataclass
class CharacterEffectDescriptionModel:
    id: str
    attributes_to_false: typing.List[str]
    attributes_to_true: typing.List[str]
    factors: typing.Dict[str, float]
    disappear_at_turn: bool = True
