# coding: utf-8
import dataclasses
import enum
import typing

import serpyco

if typing.TYPE_CHECKING:
    from rolling.model.stuff import StuffMaterialType


class ActionType(enum.Enum):
    FILL = "FILL"
    ATTACK_WITH = "ATTACK_WITH"


@dataclasses.dataclass
class ActionProperties:
    type_: ActionType
    fill_acceptable_types: typing.List["StuffMaterialType"] = serpyco.field(
        default_factory=list
    )
