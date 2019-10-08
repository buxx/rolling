# coding: utf-8
import time
import typing

from rolling.exception import NoDisplayObjectAtThisPosition
from rolling.gui.palette import PALETTE_CHARACTER
from rolling.gui.palette import PALETTE_POSITION
from rolling.gui.palette import PALETTE_STD_BUILD
from rolling.gui.palette import PALETTE_STUFF
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel


class DisplayObject:
    permanent: bool = False

    def __init__(self, row_i: int, col_i: int) -> None:
        self._row_i = row_i
        self._col_i = col_i

    @property
    def palette_id(self) -> str:
        raise NotImplementedError()

    @property
    def row_i(self) -> int:
        return self._row_i

    @row_i.setter
    def row_i(self, value: int) -> None:
        self._row_i = value

    @property
    def col_i(self) -> int:
        return self._col_i

    @col_i.setter
    def col_i(self, value: int) -> None:
        self._col_i = value

    @property
    def char(self) -> str:
        raise NotImplementedError()

    @property
    def id(self) -> str:
        raise NotImplementedError()


class Character(DisplayObject):
    def __init__(self, row_i: int, col_i: int, character: CharacterModel) -> None:
        super().__init__(row_i, col_i)
        self._character = character

    @property
    def palette_id(self) -> str:
        return PALETTE_CHARACTER

    @property
    def char(self) -> str:
        return "ጰ"

    @property
    def id(self) -> str:
        return self._character.id


class CurrentPlayer(Character):
    def __init__(self, row_i: int, col_i: int, character: CharacterModel) -> None:
        super().__init__(row_i, col_i, character)
        character.associate_display_object(self)

    def move_with_offset(self, new_offset: typing.Tuple[int, int]) -> None:
        self._row_i -= new_offset[0]
        self._col_i -= new_offset[1]


class CurrentPosition(DisplayObject):
    @property
    def palette_id(self) -> str:
        return PALETTE_POSITION

    @property
    def char(self) -> str:
        return "x"

    @property
    def id(self) -> str:
        return "__current_position__"


class StuffDisplay(DisplayObject):
    def __init__(self, row_i: int, col_i: int, stuff: StuffModel) -> None:
        super().__init__(row_i, col_i)
        self._stuff = stuff

    @property
    def palette_id(self) -> str:
        return PALETTE_STUFF

    @property
    def char(self) -> str:
        return "i"

    @property
    def id(self) -> str:
        return str(self._stuff.id)


class BuildDisplay(DisplayObject):
    permanent: bool = True

    def __init__(
        self,
        row_i: int,
        col_i: int,
        id_: int,
        char: str,
        palette_id: str = PALETTE_STD_BUILD,
    ) -> None:
        self._row_i = row_i
        self._col_i = col_i
        self._char = char
        self._palette_id = palette_id
        self._id = str(id_)

    @property
    def palette_id(self) -> str:
        # TODO BS 2019-10-02: generate palette at startup from server
        return self._palette_id

    @property
    def char(self) -> str:
        return self._char

    @property
    def id(self) -> str:
        return self._id


class DisplayObjectManager:
    def __init__(self, objects: typing.List[DisplayObject], period: float = 0.50):
        self._period: float = period
        self._objects: typing.List[DisplayObject] = objects
        self._timings: typing.Dict[DisplayObject, typing.Tuple[bool, float]] = {}
        self._objects_by_position: typing.Dict[
            typing.Tuple[int, int], typing.List[DisplayObject]
        ] = {}
        self._objects_by_ids: typing.Dict[str, DisplayObject] = {}
        self._current_player: CurrentPlayer = None

    @property
    def objects_by_position(
        self
    ) -> typing.Dict[typing.Tuple[int, int], typing.List[DisplayObject]]:
        return self._objects_by_position

    @property
    def objects_by_ids(self) -> typing.Dict[str, DisplayObject]:
        return self._objects_by_ids

    @property
    def display_objects(self) -> typing.List[DisplayObject]:
        return self._objects

    @display_objects.setter
    def display_objects(self, display_objects: typing.List[DisplayObject]) -> None:
        self._objects = display_objects

    @property
    def current_player(self) -> CurrentPlayer:
        return self._current_player

    def initialize(self) -> None:
        self._objects = []
        self._objects_by_position = {}

    def refresh_indexes(self):
        self._objects_by_position = {}
        self._objects_by_ids = {}

        for display_object in self._objects:
            display_object_position = (display_object.row_i, display_object.col_i)
            self._objects_by_position.setdefault(display_object_position, [])
            self._objects_by_position[display_object_position].append(display_object)
            self._objects_by_ids[display_object.id] = display_object

            # TODO BS 2019-03-08: more elegant way to give CurrentPlayer
            if isinstance(display_object, CurrentPlayer):
                self._current_player = display_object

    def add_object(self, display_object: DisplayObject) -> None:
        self._objects.append(display_object)

    def get_objects_for_position(self, x: int, y: int) -> typing.List[DisplayObject]:
        try:
            return self._objects_by_position[(x, y)]
        except KeyError:
            raise NoDisplayObjectAtThisPosition()

    def get_final_str(self, x: int, y: int, default: str) -> str:
        try:
            display_objects = self._objects_by_position[(x, y)]
            for display_object in display_objects:
                # if permanent, bypass timing
                if display_object.permanent:
                    return display_object.char

                try:
                    displayed, displayed_time = self._timings[display_object]
                    if time.time() - displayed_time >= self._period:
                        self._timings[display_object] = (not displayed, time.time())

                    if displayed:
                        return display_objects[0].char
                    else:
                        continue

                except KeyError:
                    self._timings[display_object] = (True, time.time())
                    return display_objects[0].char
        except KeyError:
            pass

        return default
