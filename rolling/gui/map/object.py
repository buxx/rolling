# coding: utf-8


class DisplayObject(object):
    def __init__(self, x: int, y: int) -> None:
        self._x = x
        self._y = y

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y

    @property
    def char(self) -> str:
        return 'X'


class DisplayObjectManager(object):
