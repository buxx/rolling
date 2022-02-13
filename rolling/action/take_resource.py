# coding: utf-8
import dataclasses

import copy
import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import WithResourceAction
from rolling.action.base import get_with_resource_action_url
from rolling.exception import ImpossibleAction, NoCarriedResource, NotEnoughResource
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.util import ExpectedQuantityContext
from rolling.util import InputQuantityContext
from rolling.util import get_on_and_around_coordinates
from rolling.compare import GroundResourceCompare

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class TakeResourceModel:
    quantity: typing.Optional[str] = None
    then_redirect_url: typing.Optional[str] = None


class TakeResourceAction(WithResourceAction):
    input_model = TakeResourceModel
    input_model_serializer = serpyco.Serializer(TakeResourceModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        pass

    async def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: TakeResourceModel
    ) -> None:
        pass

    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        return []  # do not display action in actions page

    async def perform(
        self, character: "CharacterModel", resource_id: str, input_: TakeResourceModel
    ) -> Description:
        # FIXME BS NOW: manage correctly ImpossibleAction
        resource_description = self._kernel.game.config.resources[resource_id]
        around_carried_resources: typing.List[CarriedResourceDescriptionModel] = []
        scan_coordinates: typing.List[
            typing.Tuple[int, int]
        ] = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i, exclude_on=False, distance=1
        )
        for around_row_i, around_col_i in scan_coordinates:
            around_carried_resources.extend(
                self._kernel.resource_lib.get_ground_resource(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=around_row_i,
                    zone_col_i=around_col_i,
                )
            )

        # FIXME try/catch indexerror -> ImpossibleAction
        try:
            ground_resource = copy.deepcopy(around_carried_resources[0])
        except IndexError:
            raise ImpossibleAction("Ressource introuvable")
        ground_resource.quantity = sum(acr.quantity for acr in around_carried_resources)

        if not input_.quantity:
            expected_quantity_context = ExpectedQuantityContext.from_carried_resource(
                self._kernel, ground_resource
            )
            return Description(
                title=resource_description.name,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_resource_action_url(
                            character_id=character.id,
                            resource_id=resource_id,
                            action_type=ActionType.TAKE_RESOURCE,
                            action_description_id="TAKE_RESOURCE",
                            query_params=self.input_model_serializer.dump(input_),
                        ),
                        items=[
                            Part(
                                label=(
                                    f"Récupérer quelle quantité "
                                    f"({expected_quantity_context.display_unit_name} ?)"
                                ),
                                name="quantity",
                                type_=Type.NUMBER,
                                default_value=expected_quantity_context.default_quantity,
                            )
                        ],
                    )
                ],
                can_be_back_url=True,
            )

        user_input_context = InputQuantityContext.from_carried_resource(
            user_input=input_.quantity,
            carried_resource=ground_resource,
        )

        # Prepare to compare what have been taken
        ground_resources_snapshot = GroundResourceCompare(
            self._kernel,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        ).snapshot()

        try:
            reduced_quantity = self._kernel.resource_lib.reduce(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_coordinates=scan_coordinates,
                resource_id=resource_id,
                quantity=user_input_context.real_quantity,
                commit=False,
                force_before_raise=True,
            )
        except NotEnoughResource as exc:
            reduced_quantity = exc.available_quantity
        except NoCarriedResource:
            return Description(
                title="Pas de ressources",
                quick_action_response="Rien ici",
            )

        self._kernel.resource_lib.add_resource_to(
            character_id=character.id,
            resource_id=resource_id,
            quantity=reduced_quantity,
            commit=True,
        )

        for (
            row_i,
            col_i,
        ), resource_ids in ground_resources_snapshot.get_missing().items():
            for resource_id in resource_ids:
                await self._kernel.resource_lib.send_zone_ground_resource_removed(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=row_i,
                    zone_col_i=col_i,
                    resource_id=resource_id,
                )

        return Description(
            title=f"{reduced_quantity}{self._kernel.translation.get(resource_description.unit)} {resource_description.name}",
            quick_action_response=f"{resource_description.name}",
            redirect=input_.then_redirect_url,
        )
