# coding: utf-8
import dataclasses
import enum
import typing

import serpyco

if typing.TYPE_CHECKING:
    from rolling.model.material import MaterialType


class ActionType(enum.Enum):
    FILL = "FILL"
    EMPTY = "EMPTY"
    ATTACK_WITH = "ATTACK_WITH"


@dataclasses.dataclass
class ActionProperties:
    type_: ActionType
    fill_acceptable_types: typing.List["MaterialType"] = serpyco.field(
        default_factory=list
    )
