# coding: utf-8
import abc
import dataclasses
import typing

import serpyco

from rolling.model.resource import resource_type_materials
from rolling.model.types import MaterialType
from rolling.server.controller.url import DESCRIBE_DRINK_RESOURCE
from rolling.server.controller.url import DESCRIBE_DRINK_STUFF
from rolling.server.controller.url import DESCRIBE_EMPTY_STUFF
from rolling.server.controller.url import DESCRIBE_STUFF_FILL_WITH_RESOURCE
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


@dataclasses.dataclass
class ActionProperties:
    type_: ActionType
    acceptable_material_types: typing.List["MaterialType"] = serpyco.field(
        default_factory=list
    )


class Action(abc.ABC):
    DEFAULT_COST = 0.0


class OnStuffAction(Action):
    def __init__(self, kernel: "Kernel", action_properties: ActionProperties) -> None:
        self._kernel = kernel
        self._properties = action_properties

    @abc.abstractmethod
    def get_cost(self, character: "CharacterModel", stuff: "StuffModel") -> float:
        pass

    @abc.abstractmethod
    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        pass


class CharacterAction(Action):
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    @abc.abstractmethod
    def get_cost(self, character: "CharacterModel") -> float:
        pass

    @abc.abstractmethod
    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        pass


class FillStuffAction(OnStuffAction):
    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []

        for fill_acceptable_type in self._properties.acceptable_material_types:
            for resource in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=character.zone_row_i,
                zone_col_i=character.zone_col_i,
                material_type=fill_acceptable_type,
            ):
                actions.append(
                    CharacterActionLink(
                        name=f"Fill {stuff.name} with {resource.name}",
                        link=DESCRIBE_STUFF_FILL_WITH_RESOURCE.format(
                            character_id=character.id,
                            stuff_id=stuff.id,
                            resource_type=resource.type_.value,
                        ),
                        cost=self.get_cost(character, stuff),
                    )
                )

        return actions

    def get_cost(self, character: "CharacterModel", stuff: "StuffModel") -> float:
        return self.DEFAULT_COST


class EmptyStuffAction(OnStuffAction):
    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Empty {stuff.name}",
                link=DESCRIBE_EMPTY_STUFF.format(
                    character_id=character.id, stuff_id=stuff.id
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def get_cost(self, character: "CharacterModel", stuff: "StuffModel") -> float:
        return self.DEFAULT_COST


class DrinkResourceAction(CharacterAction):
    acceptable_material_types: typing.List[MaterialType] = [MaterialType.LIQUID]

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        character_actions: typing.List[CharacterActionLink] = []

        for acceptable_material_type in self.acceptable_material_types:
            for resource in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=character.zone_row_i,
                zone_col_i=character.zone_col_i,
                material_type=acceptable_material_type,
            ):
                character_actions.append(
                    CharacterActionLink(
                        name=f"Drink {resource.name}",
                        link=DESCRIBE_DRINK_RESOURCE.format(
                            character_id=character.id,
                            resource_type=resource.type_.value,
                        ),
                        cost=self.get_cost(character),
                    )
                )

        return character_actions

    def get_cost(self, character: "CharacterModel") -> float:
        return self.DEFAULT_COST


class DrinkStuffAction(OnStuffAction):
    acceptable_material_types: typing.List[MaterialType] = [MaterialType.LIQUID]

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        if stuff.filled_with_resource is not None:
            if (
                resource_type_materials[stuff.filled_with_resource]
                in self.acceptable_material_types
            ):
                return [
                    CharacterActionLink(
                        name=f"Drink {stuff.filled_with_resource.value}",
                        link=DESCRIBE_DRINK_STUFF.format(
                            character_id=character.id, stuff_id=stuff.id
                        ),
                        cost=self.get_cost(character, stuff),
                    )
                ]

        return []

    def get_cost(self, character: "CharacterModel", stuff: "StuffModel") -> float:
        return self.DEFAULT_COST
