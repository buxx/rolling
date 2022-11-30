# coding: utf-8
import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import CantFill
from rolling.exception import ImpossibleAction
from rolling.model.character import FillStuffWithResourceModel
from rolling.rolling_types import ActionType
from rolling.server.controller.url import DESCRIBE_LOOK_AT_STUFF_URL
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


class FillStuffAction(WithStuffAction):
    input_model: typing.Type[FillStuffWithResourceModel] = FillStuffWithResourceModel
    input_model_serializer = serpyco.Serializer(input_model)

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
        for _ in self._kernel.game.config.fill_with_material_ids:
            for _ in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=character.zone_row_i,
                zone_col_i=character.zone_col_i,
            ):
                return

        raise ImpossibleAction("Rien à proximité ne correspond")

    async def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        # TODO BS 2019-08-01: check owned
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []

        for fill_acceptable_type in self._kernel.game.config.fill_with_material_ids:
            for production in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=character.zone_row_i,
                zone_col_i=character.zone_col_i,
            ):
                query_params = self.input_model(resource_id=production.resource.id)
                actions.append(
                    CharacterActionLink(
                        name=f"Remplir {stuff.name} avec {production.resource.name}",
                        link=get_with_stuff_action_url(
                            character_id=character.id,
                            action_type=ActionType.FILL_STUFF,
                            stuff_id=stuff.id,
                            query_params=self.input_model_serializer.dump(query_params),
                            action_description_id=self._description.id,
                        ),
                        cost=self.get_cost(character, stuff),
                        group_name=f"Remplir {stuff.name} avec {production.resource.name}",
                    )
                )

        return actions

    async def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        footer_links = [
            Part(
                is_link=True,
                label="Voir l'objet",
                form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                    character_id=character.id, stuff_id=stuff.id
                ),
                classes=["primary"],
            )
        ]

        try:
            self._kernel.stuff_lib.fill_stuff_with_resource(stuff, input_.resource_id)
        except CantFill as exc:
            return Description(title=str(exc), footer_links=footer_links)

        resource_description = self._kernel.game.config.resources[input_.resource_id]
        return Description(
            title=f"{stuff.name} rempli(e) avec {resource_description.name}",
            footer_links=footer_links,
            reload_inventory=True,
        )
