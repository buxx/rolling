# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_with_resource_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.server.transfer import BiDirectionalTransferByUrl
from rolling.server.transfer import ResourceLine
from rolling.server.transfer import StuffLine
from rolling.util import get_on_and_around_coordinates
from rolling.util import str_quantity_to_float

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel


class TransfertGroundByUrl(BiDirectionalTransferByUrl):
    def __init__(
        self,
        kernel: "Kernel",
        character: "CharacterModel",
        partial_quantities: typing.Optional[typing.Dict[str, float]],
    ):
        self.__kernel = kernel
        self._character = character
        self._partial_quantities = partial_quantities or {}

    @property
    def _kernel(self) -> "Kernel":
        return self.__kernel

    def _get_default_left_partial_quantity(self, resource_id: str) -> float:
        return self._partial_quantities.get(f"left_{resource_id}_partial_quantity")

    def _get_default_right_partial_quantity(self, resource_id: str) -> float:
        return self._partial_quantities.get(f"right_{resource_id}_partial_quantity")

    def _get_title(self) -> str:
        return "Prendre/Déposer des choses"

    def _get_left_title(self) -> str:
        return "Votre inventaire"

    def _get_right_title(self) -> str:
        return "Autour de vous"

    def _get_left_stuffs(self) -> typing.List[StuffLine]:
        stuff_lines: typing.List[StuffLine] = []
        for carried_stuff in self._kernel.stuff_lib.get_carried_by(self._character.id):
            stuff_lines.append(StuffLine(stuff=carried_stuff, movable=True))
        return stuff_lines

    def _get_right_stuffs(self) -> typing.List[StuffLine]:
        scan_coordinates: typing.List[typing.Tuple[int, int]] = get_on_and_around_coordinates(
            x=self._character.zone_row_i, y=self._character.zone_col_i, exclude_on=False, distance=1
        )
        stuff_lines: typing.List[StuffLine] = []

        for around_row_i, around_col_i in scan_coordinates:
            for stuff in self._kernel.stuff_lib.get_zone_stuffs(
                world_row_i=self._character.world_row_i,
                world_col_i=self._character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            ):
                stuff_lines.append(StuffLine(stuff=stuff, movable=True))

        return stuff_lines

    def _get_left_resources(self) -> typing.List[ResourceLine]:
        resource_lines: typing.List[ResourceLine] = []
        for carried_resource in self._kernel.resource_lib.get_carried_by(
            character_id=self._character.id
        ):
            resource_lines.append(ResourceLine(resource=carried_resource, movable=True))
        return resource_lines

    def _get_right_resources(self) -> typing.List[ResourceLine]:
        scan_coordinates: typing.List[typing.Tuple[int, int]] = get_on_and_around_coordinates(
            x=self._character.zone_row_i, y=self._character.zone_col_i, exclude_on=False, distance=1
        )
        resource_lines: typing.List[ResourceLine] = []

        for around_row_i, around_col_i in scan_coordinates:
            for carried_resource in self._kernel.resource_lib.get_ground_resource(
                world_row_i=self._character.world_row_i,
                world_col_i=self._character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            ):
                resource_lines.append(ResourceLine(resource=carried_resource, movable=True))

        return resource_lines

    def _get_here_url(
        self, partial_quantities: typing.Optional[typing.Dict[str, float]] = None
    ) -> str:
        partial_quantities = partial_quantities or {}
        query_params: typing.Dict[str, str] = {}
        for key_name, value in partial_quantities.items():
            query_params[f"{key_name}_partial_quantity"] = str(value)

        return get_character_action_url(
            character_id=self._character.id,
            action_type=ActionType.TRANSFER_GROUND,
            action_description_id="TRANSFER_GROUND",
            query_params=query_params,
        )

    def _get_move_stuff_right_url(
        self,
        stuff_id: int,
        stuff_quantity: typing.Optional[int] = None,
        partial_quantities: typing.Optional[typing.Dict[str, float]] = None,
    ) -> str:
        return get_with_stuff_action_url(
            character_id=self._character.id,
            stuff_id=stuff_id,
            action_type=ActionType.DROP_STUFF,
            action_description_id="DROP_STUFF",
            query_params={"quantity": stuff_quantity, "then_redirect_url": self._get_here_url()},
        )

    def _get_move_stuff_left_url(
        self,
        stuff_id: int,
        stuff_quantity: typing.Optional[int] = None,
        partial_quantities: typing.Optional[typing.Dict[str, float]] = None,
    ) -> str:
        return get_with_stuff_action_url(
            character_id=self._character.id,
            stuff_id=stuff_id,
            action_type=ActionType.TAKE_STUFF,
            action_description_id="TAKE_STUFF",
            query_params={
                "quantity": stuff_quantity,
                "then_redirect_url": self._get_here_url(partial_quantities),
            },
        )

    def _get_move_resource_right_url(
        self,
        resource_id: str,
        resource_quantity: typing.Optional[str] = None,
        partial_quantities: typing.Optional[typing.Dict[str, float]] = None,
    ) -> str:
        return get_with_resource_action_url(
            character_id=self._character.id,
            resource_id=resource_id,
            action_type=ActionType.DROP_RESOURCE,
            action_description_id="DROP_RESOURCE",
            query_params={
                "quantity": resource_quantity,
                "then_redirect_url": self._get_here_url(partial_quantities),
            },
        )

    def _get_move_resource_left_url(
        self,
        resource_id: str,
        resource_quantity: typing.Optional[str] = None,
        partial_quantities: typing.Optional[typing.Dict[str, float]] = None,
    ) -> str:
        return get_with_resource_action_url(
            character_id=self._character.id,
            resource_id=resource_id,
            action_type=ActionType.TAKE_RESOURCE,
            action_description_id="TAKE_RESOURCE",
            query_params={"quantity": resource_quantity, "then_redirect_url": self._get_here_url()},
        )


@dataclasses.dataclass
class TransfertGroundCharacterModel:
    partial_quantities: typing.Optional[typing.Dict[str, float]] = None


class TransfertGroundCharacterAction(CharacterAction):
    input_model = TransfertGroundCharacterModel
    input_model_serializer = serpyco.Serializer(TransfertGroundCharacterModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    @classmethod
    def input_model_from_request(
        cls, parameters: typing.Dict[str, typing.Any]
    ) -> TransfertGroundCharacterModel:
        partial_quantities: typing.Optional[typing.Dict[str, float]] = {}
        for parameter_name, parameter_value in parameters.items():
            if parameter_name.endswith("_partial_quantity"):
                partial_quantities[parameter_name] = str_quantity_to_float(parameter_value)
        return TransfertGroundCharacterModel(
            partial_quantities=partial_quantities,
        )

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass

    def check_request_is_possible(
        self, character: "CharacterModel", input_: TransfertGroundCharacterModel
    ) -> None:
        pass  # note: check done by drop/take related actions

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name="Prendre/Déposer",
                link=get_character_action_url(
                    character_id=character.id,
                    action_type=ActionType.TRANSFER_GROUND,
                    action_description_id=self._description.id,
                    query_params={},
                ),
            )
        ]

    def perform(
        self, character: "CharacterModel", input_: TransfertGroundCharacterModel
    ) -> Description:
        return TransfertGroundByUrl(
            self._kernel, character, partial_quantities=input_.partial_quantities
        ).get_description()
