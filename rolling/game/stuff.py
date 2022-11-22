# coding: utf-8
import typing

from rolling.exception import UnknownStuffError

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.stuff import StuffProperties


class StuffManager:
    def __init__(self, kernel: "Kernel", items: typing.List["StuffProperties"]) -> None:
        self._kernel = kernel
        self._items = items
        self._items_by_id = dict(((s.id, s) for s in items))

    @property
    def items(self) -> typing.List["StuffProperties"]:
        return self._items

    def get_stuff_properties_by_id(self, stuff_id: str) -> "StuffProperties":
        try:
            return self._items_by_id[stuff_id]
        except KeyError:
            raise UnknownStuffError(f'Unknown stuff "{stuff_id}"')

    def get_weapon_descriptions(self) -> typing.List["StuffProperties"]:
        weapons = []

        for item in self._items:
            if item.weapon:
                weapons.append(item)

        return weapons

    def get_shield_descriptions(self) -> typing.List["StuffProperties"]:
        shields = []

        for item in self._items:
            if item.shield:
                shields.append(item)

        return shields

    def get_armor_descriptions(self) -> typing.List["StuffProperties"]:
        armors = []

        for item in self._items:
            if item.armor:
                armors.append(item)

        return armors
