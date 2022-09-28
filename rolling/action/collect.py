# coding: utf-8
import collections
import dataclasses

import serpyco
from sqlalchemy.exc import NoResultFound
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.bonus import Bonus, Bonuses
from rolling.exception import ImpossibleAction
from rolling.exception import RollingError
from rolling.model.zone import ZoneMapTileProduction
from rolling.rolling_types import ActionType
from rolling.server.document.resource import ZoneResourceDocument
from rolling.server.link import CharacterActionLink, ExploitableTile
from rolling.util import Quantity, QuantityEncoder, get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class CollectResourceModel:
    resource_id: str
    zone_row_i: int = serpyco.number_field(cast_on_load=True)
    zone_col_i: int = serpyco.number_field(cast_on_load=True)
    quantity: typing.Optional[Quantity] = None
    quantity_auto: int = serpyco.number_field(cast_on_load=True, default=0)


# FIXME BS 2019-08-29: Permit collect only some material (like no liquid)
class CollectResourceAction(CharacterAction):
    input_model = CollectResourceModel
    input_model_serializer = serpyco.Serializer(
        input_model, type_encoders={Quantity: QuantityEncoder()}
    )

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel") -> None:
        for _ in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        ):
            return

        raise ImpossibleAction("Il n'y a rien à collecter ici")

    async def check_request_is_possible(
        self, character: "CharacterModel", input_: input_model
    ) -> None:
        productions = self._kernel.game.world_manager.get_resources_at(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.zone_row_i,
            zone_col_i=input_.zone_col_i,
        )
        if input_.resource_id in [production.resource.id for production in productions]:
            return

        raise ImpossibleAction(f"Il n'y a pas de '{input_.resource_id}' à cet endroit")

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        inspect_zone_positions = get_on_and_around_coordinates(
            character.zone_row_i, character.zone_col_i
        )
        character_actions: typing.List[CharacterActionLink] = []
        productions: typing.DefaultDict[
            str, typing.List[typing.Tuple[int, int]]
        ] = collections.defaultdict(list)

        for zone_row_i, zone_col_i in inspect_zone_positions:
            for production in self._kernel.game.world_manager.get_resources_at(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=zone_row_i,
                zone_col_i=zone_col_i,
            ):
                productions[production.resource.id].append((zone_row_i, zone_col_i))

        for resource_id, coordinates in productions.items():
            resource_description = self._kernel.game.config.resources[resource_id]
            query_params = self.input_model(
                resource_id=resource_id,
                zone_row_i=coordinates[0][0],
                zone_col_i=coordinates[0][1],
            )
            character_actions.append(
                CharacterActionLink(
                    name=f"Exploiter {resource_description.name}",
                    link=get_character_action_url(
                        character_id=character.id,
                        action_type=ActionType.COLLECT_RESOURCE,
                        action_description_id=self._description.id,
                        query_params=self.input_model_serializer.dump(query_params),
                    ),
                    additional_link_parameters_for_quick_action={"quantity_auto": 1},
                    cost=None,
                    merge_by=(ActionType.COLLECT_RESOURCE, resource_id),
                    group_name="Exploiter des ressources",
                    classes1=["COLLECT"],
                    classes2=[resource_id],
                    use_classes2_for_button=True,
                    # rollgui2 compatibility
                    all_tiles_at_once=False,
                    exploitable_tiles=[
                        ExploitableTile(
                            zone_row_i=zone_row_i,
                            zone_col_i=zone_col_i,
                            classes=[resource_id],
                        )
                        for (zone_row_i, zone_col_i) in coordinates
                    ],
                )
            )

        return character_actions

    def get_quick_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            link.clone_for_quick_action()
            for link in self.get_character_actions(character)
        ]

    def get_cost(
        self,
        character: "CharacterModel",
        input_: typing.Optional[CollectResourceModel] = None,
    ) -> typing.Optional[float]:
        if (
            input_
            and (input_.quantity is not None or input_.quantity_auto)
            and input_.resource_id is not None
        ):
            try:
                production = self._get_production(character, input_=input_)
            except StopIteration:
                raise ImpossibleAction("Plus de ressource à cet endroit")

            if input_.quantity_auto:
                quantity = production.extract_quick_action_quantity
                input_.quantity = Quantity(quantity)

            return self._bonuses(character, input_=input_).apply(
                input_.quantity.as_real_float() * production.extract_cost_per_unit
            )

    def _bonuses(
        self, character: "CharacterModel", input_: CollectResourceModel
    ) -> Bonuses:
        bonuses = []
        if stuff_bonus := self._kernel._character_lib.get_stuff_bonus(
            character.id,
            qualifiers=[ActionType.COLLECT_RESOURCE, input_.resource_id],
        ):
            bonuses.append(stuff_bonus)

        production = self._get_production(character, input_=input_)
        if skill_bonus := self._kernel._character_lib.get_skill_bonus(
            character, skills_ids=list(production.skills_bonus.keys())
        ):
            bonuses.append(skill_bonus)

        return Bonuses(bonuses)

    def _get_production(
        self, character: "CharacterModel", input_: CollectResourceModel
    ) -> ZoneMapTileProduction:
        return next(
            production
            for production in self._kernel.game.world_manager.get_resources_at(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=input_.zone_row_i,
                zone_col_i=input_.zone_col_i,
            )
            if production.resource.id == input_.resource_id
        )

    async def perform(
        self, character: "CharacterModel", input_: CollectResourceModel
    ) -> Description:
        assert input_.resource_id is not None
        assert input_.zone_row_i is not None
        assert input_.zone_col_i is not None

        character_doc = self._kernel.character_lib.get_document(character.id)
        resource_description = self._kernel.game.config.resources[input_.resource_id]
        production = self._get_production(character, input_=input_)

        if input_.quantity is None and not input_.quantity_auto:
            unit_name = self._kernel.translation.get(resource_description.unit)

            bonuses = self._bonuses(character, input_=input_)
            extract_cost_per_unit = bonuses.apply(production.extract_cost_per_unit)
            bonuses_sentences = [f"Bonus appliqués :"]
            if bonuses_names := bonuses.names():
                bonuses_sentences.extend([f" - {name}" for name in bonuses_names])
            else:
                bonuses_sentences.append(" - aucun")
            return Description(
                title=f"Extraire {resource_description.name}",
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.COLLECT_RESOURCE,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(input_),
                        ),
                        items=[
                            Part(
                                text=f"Extraire 1 {unit_name} demande {round(extract_cost_per_unit, 4)} PA"
                            ),
                            *[Part(text=text) for text in bonuses_sentences],
                            Part(
                                label=f"Quantité à extraire ?",
                                type_=Type.NUMBER,
                                name="quantity",
                                default_value=production.ui_extract_default_quantity,
                                min_value=production.ui_extract_min_quantity,
                                max_value=production.ui_extract_max_quantity,
                            ),
                        ],
                    )
                ],
            )

        quantity = input_.quantity
        if input_.quantity_auto:
            quantity_ = production.extract_quick_action_quantity
            input_.quantity = Quantity(quantity_)

        if not production.infinite:
            try:
                zone_resource_doc: ZoneResourceDocument = (
                    self._kernel.zone_lib.get_zone_ressource_doc(
                        world_row_i=character.world_row_i,
                        world_col_i=character.world_col_i,
                        zone_row_i=input_.zone_row_i,
                        zone_col_i=input_.zone_col_i,
                        resource_id=input_.resource_id,
                    )
                )
            except NoResultFound:
                raise RollingError(
                    "No zone resource found around : "
                    f"world_row_i:{character.world_row_i}, "
                    f"world_row_i:{character.world_col_i}, "
                    f"zone_row_i:{input_.zone_row_i}, "
                    f"zone_col_i:{input_.zone_col_i}, "
                    f"resource_id:{input_.resource_id}"
                )

            if zone_resource_doc.quantity < quantity.as_real_float():
                quantity = Quantity(zone_resource_doc.quantity)
                input_ = CollectResourceModel(
                    resource_id=input_.resource_id,
                    zone_row_i=input_.zone_row_i,
                    zone_col_i=input_.zone_col_i,
                    quantity=quantity,
                )

        cost = self.get_cost(character, input_=input_)
        if cost is None:
            raise RollingError("Cost compute should not be None !")

        self._kernel.resource_lib.add_resource_to(
            character_id=character_doc.id,
            resource_id=input_.resource_id,
            quantity=quantity.as_real_float(),
            commit=False,
        )
        if not production.infinite:
            await self._kernel.zone_lib.reduce_resource_quantity(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=input_.zone_row_i,
                zone_col_i=input_.zone_col_i,
                resource_id=input_.resource_id,
                quantity=quantity.as_real_float(),
                allow_reduce_more_than_possible=True,
                commit=False,
            )

        await self._kernel.character_lib.reduce_action_points(
            character.id, cost, commit=False
        )
        for (
            bonis_skill_id,
            bonus_increment_coefficient,
        ) in production.skills_bonus.items():
            self._kernel.character_lib.increase_skill(
                character.id,
                skill_id=bonis_skill_id,
                increment=input_.quantity.as_real_float() * bonus_increment_coefficient,
            )
        self._kernel.server_db_session.commit()

        text = f"{round(quantity.as_real_float(), 4)}{self._kernel.translation.get(resource_description.unit, short=True)} {resource_description.name}"
        return Description(
            title=f"Récupérer du {resource_description.name}",
            items=[Part(text=text)],
            quick_action_response=text,
            exploitable_success=(input_.zone_row_i, input_.zone_col_i),
        )
