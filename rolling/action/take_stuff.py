# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from rolling.action.base import WithStuffAction
from rolling.server.link import CharacterActionLink
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


@dataclasses.dataclass
class TakeStuffModel:
    quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    then_redirect_url: typing.Optional[str] = None

    @property
    def quantity_int(self) -> typing.Optional[int]:
        if self.quantity is None:
            return None

        return int(self.quantity)


class TakeStuffAction(WithStuffAction):
    input_model = TakeStuffModel
    input_model_serializer = serpyco.Serializer(TakeStuffModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self,
        character: "CharacterModel",
        stuff: "StuffModel",
        from_inventory_only: bool = False,
    ) -> None:
        pass  # TODO: check if stuff is near, is not carried, is not protected ...

    async def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: TakeStuffModel
    ) -> None:
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        pass  # do not display action in actions page

    async def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: TakeStuffModel
    ) -> Description:
        # FIXME BS NOW: manage correctly ImpossibleAction
        self._kernel.character_lib.take_stuff(
            character_id=character.id, stuff_id=stuff.id
        )

        around_stuffs_like_this: typing.List[StuffModel] = []
        taken_stuffs: typing.List[StuffModel] = [stuff]
        if input_.quantity_int:
            stuff_to_find = input_.quantity_int - 1
            scan_coordinates: typing.List[
                typing.Tuple[int, int]
            ] = get_on_and_around_coordinates(
                x=character.zone_row_i,
                y=character.zone_col_i,
                exclude_on=False,
                distance=1,
            )
            for around_row_i, around_col_i in scan_coordinates:
                for around_stuff in self._kernel.stuff_lib.get_zone_stuffs(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=around_row_i,
                    zone_col_i=around_col_i,
                    stuff_id=stuff.stuff_id,
                ):
                    around_stuffs_like_this.append(around_stuff)

            for _ in range(min(stuff_to_find, len(around_stuffs_like_this))):
                taken_stuff = around_stuffs_like_this.pop()
                self._kernel.character_lib.take_stuff(
                    character_id=character.id, stuff_id=taken_stuff.id
                )
                taken_stuffs.append(taken_stuff)

        for taken_stuff in taken_stuffs:
            await self._kernel.stuff_lib.send_zone_ground_stuff_removed(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=taken_stuff.zone_row_i,
                zone_col_i=taken_stuff.zone_col_i,
                stuff_id=taken_stuff.id,
            )

        return Description(
            title="Objet(s) récupéré(s)",
            redirect=input_.then_redirect_url,
            quick_action_response=f"{len(taken_stuffs)} récupéré(s)",
        )
