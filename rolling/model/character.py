# coding: utf-8
import dataclasses


@dataclasses.dataclass
class CreateCharacterModel(object):
    name: str


@dataclasses.dataclass
class GetCharacterPathModel(object):
    id: str


@dataclasses.dataclass
class CharacterModel(object):
    id: str
    name: str
