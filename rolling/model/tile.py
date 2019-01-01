# coding: utf-8
import dataclasses
import typing

from rolling.model.meta import TransportType


@dataclasses.dataclass
class ZoneTileModel(object):
    id: str
    char: str
    traversable: typing.Optional[typing.Dict[TransportType, bool]]
