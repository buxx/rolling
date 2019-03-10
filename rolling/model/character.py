# coding: utf-8
import dataclasses
import typing

from rolling.exception import RollingError

if typing.TYPE_CHECKING:
    from rolling.gui.map.object import DisplayObject


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
    _display_object = None

    def associate_display_object(self, display_object: "DisplayObject") -> None:
        self._display_object = display_object

    @property
    def display_object(self) -> "DisplayObject":
        if self._display_object is None:
            raise RollingError("You are trying to use property who si not set")

        return self._display_object
