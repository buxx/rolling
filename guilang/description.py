# coding: utf-8

import dataclasses
import enum
import typing


class Type(enum.Enum):
    STRING = "STRING"
    TEXT = "TEXT"
    NUMBER = "NUMBER"

    @classmethod
    def from_python_type(cls, python_type) -> "Type":
        if python_type == str:
            return cls.STRING
        elif python_type in (float, int):
            return cls.NUMBER

        raise NotImplementedError(f"{python_type} not managed yet")


@dataclasses.dataclass
class Part:
    text: typing.Optional[str] = None
    is_form: bool = False
    form_action: typing.Optional[str] = None
    form_values_in_query: bool = False
    items: typing.List["Part"] = dataclasses.field(default_factory=list)
    type_: typing.Optional[Type] = None
    label: typing.Optional[str] = None
    name: typing.Optional[str] = None
    is_link: bool = False
    go_back_zone: bool = False
    default_value: typing.Optional[str] = None

    @classmethod
    def from_dataclass_fields(cls, dataclass_, is_form: bool = False) -> typing.List["Part"]:
        items: typing.List[Part] = []

        for field in dataclasses.fields(dataclass_):
            type_ = Type.TEXT if field.metadata.get("is_text") else Type.from_python_type(field.type)
            items.append(Part(
                label=field.metadata.get("label", None),
                type_=type_,
                name=field.name,
            ))

        return items


@dataclasses.dataclass
class Description:
    title: typing.Optional[str] = None
    items: typing.List[Part] = dataclasses.field(default_factory=list)
    image: typing.Optional[str] = None
    image_id: typing.Optional[int] = None
    image_extension: typing.Optional[str] = None  # used by client to cache image
    is_long_text: bool = False
    new_character_id: typing.Optional[str] = None
