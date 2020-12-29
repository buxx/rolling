# coding: utf-8
import dataclasses

import serpyco
import typing


@dataclasses.dataclass
class ItemModel:
    name: str
    value_is_str: bool = False
    value_is_float: bool = False
    value_str: typing.Optional[str] = None
    value_float: typing.Optional[float] = None
    url: typing.Optional[str] = None
    classes: typing.List[str] = serpyco.field(default_factory=list)


@dataclasses.dataclass
class ListOfItemModel:
    items: typing.List[ItemModel]
