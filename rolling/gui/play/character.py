# coding: utf-8
import typing
import urwid

from rolling.model.character import CreateCharacterModel


class CreateCharacterBox(urwid.Filler):
    def __init__(self, callback: typing.Callable[[CreateCharacterModel], None]):
        self._edit = urwid.Edit(u"Character name?\n")
        self._callback = callback
        super().__init__(self._edit)

    def keypress(self, size, key):
        if key != "enter":
            return super().keypress(size, key)

        self._callback(CreateCharacterModel(name=self._edit.edit_text))
