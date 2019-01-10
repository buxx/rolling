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
    world_col_i: int = None
    world_row_i: int = None
    zone_col_i: int = None
    zone_row_i: int = None
