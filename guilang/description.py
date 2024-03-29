# coding: utf-8

import dataclasses
import enum
import typing
import serpyco

from rolling.rolling_types import ActionType


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
    expect_integer: bool = False
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
    classes2: typing.List[str] = dataclasses.field(default_factory=list)
    is_web_browser_link: bool = False
    is_column: bool = False
    colspan: int = 1
    columns: int = 0
    min_value: typing.Optional[float] = None
    max_value: typing.Optional[float] = None
    display_int_buttons: bool = False
    cost: typing.Optional[float] = None
    use_classes2_for_button: bool = False
    dont_wrap: bool = False

    @classmethod
    def from_dataclass_fields(
        cls, dataclass_, is_form: bool = False
    ) -> typing.List["Part"]:
        items: typing.List[Part] = []

        for field in dataclasses.fields(dataclass_):
            type_ = (
                Type.TEXT
                if field.metadata.get("is_text")
                else Type.from_python_type(field.type)
            )
            items.append(
                Part(
                    label=field.metadata.get("label", None),
                    type_=type_,
                    name=field.name,
                )
            )

        return items

    def __post_init__(self) -> None:
        if self.is_link and self.label is None and self.text is not None:
            self.label = self.text
            self.text = None


@dataclasses.dataclass
class RequestClicks:
    action_type: ActionType
    action_description_id: str
    cursor_classes: typing.List[str]
    many: bool = False


class DescriptionType(str, enum.Enum):
    DEFAULT = "DEFAULT"
    ERROR = "ERROR"


@dataclasses.dataclass
class Description(serpyco.SerializerMixin):
    type_: DescriptionType = DescriptionType.DEFAULT
    title: typing.Optional[str] = None
    items: typing.List[Part] = dataclasses.field(default_factory=list)
    footer_links: typing.List[Part] = dataclasses.field(default_factory=list)
    back_url: typing.Optional[str] = None
    back_url_is_zone: bool = False
    back_to_zone: bool = False
    illustration_name: typing.Optional[str] = None
    disable_illustration_row: bool = False
    is_long_text: bool = False
    new_character_id: typing.Optional[str] = None
    account_created: bool = False
    redirect: typing.Optional[str] = None
    can_be_back_url: bool = False
    request_clicks: typing.Optional[RequestClicks] = None
    footer_with_character_id: typing.Optional[str] = None
    footer_actions: bool = True
    footer_inventory: bool = True
    footer_with_build_id: typing.Optional[int] = None
    footer_with_affinity_id: typing.Optional[int] = None
    character_ap: typing.Optional[str] = None
    quick_action_response: typing.Optional[str] = None
    action_uuid: typing.Optional[str] = None
    not_enough_ap: bool = False
    exploitable_success: typing.Optional[typing.Tuple[int, int]] = None
    deposit_success: typing.Optional[
        typing.Tuple[typing.Tuple[int, int], typing.List[str]]
    ] = None
    is_quick_error: bool = False
    is_grid: bool = False
    reload_zone: bool = False
    reload_inventory: bool = False
    open_new_tab: typing.Optional[str] = None
    force_tight: bool = False
