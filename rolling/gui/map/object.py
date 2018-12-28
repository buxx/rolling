# coding: utf-8
import time
import typing

from rolling.gui.palette import PALETTE_CHARACTER


class DisplayObject(object):
    def __init__(self, x: int, y: int) -> None:
        self._x = x
        self._y = y

    @property
    def palette_id(self) -> str:
        raise NotImplementedError()

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y

    @property
    def char(self) -> str:
        raise NotImplementedError()


class Character(DisplayObject):
    @property
    def palette_id(self) -> str:
        return PALETTE_CHARACTER

    @property
    def char(self) -> str:
        return "ጰ"


class DisplayObjectManager(object):
    def __init__(self, objects: typing.List[DisplayObject], period: float = 1.0):
        self._period: float = period
        self._objects: typing.List[DisplayObject] = objects
        self._timings: typing.Dict[DisplayObject, typing.Tuple[bool, float]] = {}
        self._objects_by_position: typing.Dict[
            typing.Tuple[int, int], typing.List[DisplayObject]
        ] = {}

    @property
    def objects_by_position(
        self
    ) -> typing.Dict[typing.Tuple[int, int], typing.List[DisplayObject]]:
        return self._objects_by_position

    @property
    def display_objects(self):
        return self._objects

    @display_objects.setter
    def display_objects(self, display_objects: typing.List[DisplayObject]) -> None:
        self._objects = display_objects

    def init(self):
        self._objects_by_position = {}
        for display_object in self._objects:
            display_object_position = (display_object.x, display_object.y)
            self._objects_by_position.setdefault(display_object_position, [])
            self._objects_by_position[display_object_position].append(display_object)

    def get_final_str(self, x: int, y: int, default: str) -> str:
        try:
            display_objects = self._objects_by_position[(x, y)]
            for display_object in display_objects:
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
