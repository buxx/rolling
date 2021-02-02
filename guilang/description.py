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
    submit_label: typing.Optional[str] = None
    items: typing.List["Part"] = dataclasses.field(default_factory=list)
    type_: typing.Optional[Type] = None
    label: typing.Optional[str] = None
    name: typing.Optional[str] = None
    is_link: bool = False
    default_value: typing.Optional[str] = None
    link_group_name: typing.Optional[str] = None
    align: typing.Optional[str] = None
    value: typing.Optional[str] = None
    is_checkbox: bool = False
    checked: bool = False
    choices: typing.Optional[typing.List[str]] = None
    search_by_str: bool = False
    id: typing.Optional[int] = None
    classes: typing.List[str] = dataclasses.field(default_factory=list)

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
class RequestClicks:
    base_url: str
    cursor_classes: typing.List[str]
    many: bool = False


@dataclasses.dataclass
class Description:
    title: typing.Optional[str] = None
    items: typing.List[Part] = dataclasses.field(default_factory=list)
    footer_links: typing.List[Part] = dataclasses.field(default_factory=list)
    back_url: typing.Optional[str] = None
    back_url_is_zone: bool = False
    back_to_zone: bool = True
    illustration_name: typing.Optional[str] = None
    disable_illustration_row: bool = False
    is_long_text: bool = False
    new_character_id: typing.Optional[str] = None
    redirect: typing.Optional[str] = None
    can_be_back_url: bool = False
    request_clicks: typing.Optional[RequestClicks] = None
    footer_with_character_id: typing.Optional[str] = None
    footer_actions: bool = True
    footer_inventory: bool = True
    footer_with_build_id: typing.Optional[int] = None
    footer_with_affinity_id: typing.Optional[int] = None
