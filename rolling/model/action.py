# coding: utf-8
import abc
import dataclasses
import enum
import typing

import serpyco

from rolling.server.controller.url import DESCRIBE_DRINK_RESOURCE
from rolling.server.lib.action import CharacterAction

if typing.TYPE_CHECKING:
    from rolling.model.material import MaterialType
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel


class ActionType(enum.Enum):
    FILL = "FILL"
    EMPTY = "EMPTY"
    ATTACK_WITH = "ATTACK_WITH"
    DRINK = "DRINK"


@dataclasses.dataclass
class ActionProperties:
    type_: ActionType
    acceptable_material_types: typing.List["MaterialType"] = serpyco.field(
        default_factory=list
    )


class Action(abc.ABC):
    @abc.abstractmethod
    def get_available_actions(self) -> typing.List[CharacterAction]:
        pass


class DrinkAction(Action):
    def __init__(
        self,
        kernel: "Kernel",
        character: "CharacterModel",
        acceptable_material_types: typing.List["MaterialType"],
    ) -> None:
        self._kernel = kernel
        self._character = character
        self._acceptable_material_types = acceptable_material_types

    def get_available_actions(self) -> typing.List[CharacterAction]:
        character_actions: typing.List[CharacterAction] = []

        for acceptable_material_type in self._acceptable_material_types:
            for resource in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=self._character.world_row_i,
                world_col_i=self._character.world_col_i,
                zone_row_i=self._character.zone_row_i,
                zone_col_i=self._character.zone_col_i,
                material_type=acceptable_material_type,
            ):
                character_actions.append(
                    CharacterAction(
                        name=f"Drink {resource.name}",
                        link=DESCRIBE_DRINK_RESOURCE.format(
                            character_id=self._character.id,
                            resource_type=resource.type_.value,
                        ),
                    )
                )

        return character_actions
