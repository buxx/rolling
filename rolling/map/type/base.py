# coding: utf-8
import abc
import typing


class MapTileType(metaclass=abc.ABCMeta):
    id = NotImplemented
    name = None
    foreground_color = "white"
    background_color = ""
    mono = ""
    foreground_high_color = ""
    background_high_color = "#000"

    _full_id_pattern = NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_all(cls) -> typing.Dict[str, typing.Type["MapTileType"]]:
        """Return all tile types"""

    @classmethod
    def get_for_id(cls, id_: str) -> typing.Type["MapTileType"]:
        return cls.get_all()[id_]

    @classmethod
    def get_full_id(cls) -> str:
        return cls._full_id_pattern.format(cls.id)

    @classmethod
    def get_name(cls) -> str:
        if cls.name is not None:
            return cls.name
        return cls.id
