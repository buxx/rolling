# coding: utf-8
import dataclasses
import copy

import typing

from rolling.rolling_types import ActionType


@dataclasses.dataclass
class CharacterActionLink:
    name: str
    link: str
    cost: typing.Optional[float] = None
    merge_by: typing.Optional[typing.Any] = None
    group_name: typing.Optional[str] = None
    back_url: typing.Optional[str] = None
    category: typing.Optional[str] = None
    classes1: typing.List[str] = dataclasses.field(default_factory=list)
    classes2: typing.List[str] = dataclasses.field(default_factory=list)
    additional_link_parameters_for_quick_action: typing.Optional[
        typing.Dict[str, typing.Union[str, int, float]]
    ] = dataclasses.field(default_factory=dict)
    is_web_browser_link: bool = False

    def get_as_str(self) -> str:
        if not self.cost:
            return self.name
        return f"{self.name} ({self.cost} points d'actions)"

    def clone_for_quick_action(self) -> "CharacterActionLink":
        link: "CharacterActionLink" = copy.copy(self)
        if "?" not in link.link:
            link.link += "?"
        link.link += "&" + "&".join(
            f"{key}={value}"
            for key, value in (
                list(self.additional_link_parameters_for_quick_action.items())
                + [("quick_action", "1")]
            )
        )
        link.additional_link_parameters_for_quick_action = None
        return link
