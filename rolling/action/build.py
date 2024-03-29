# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import RequestClicks
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import WithBuildAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_with_build_action_url
from rolling.action.utils import BeginBuildModel
from rolling.action.utils import check_common_is_possible
from rolling.action.utils import fill_base_action_properties
from rolling.action.utils import get_build_description_parts
from rolling.exception import ImpossibleAction
from rolling.exception import MissingResource
from rolling.exception import NoCarriedResource
from rolling.exception import NotEnoughResource
from rolling.model.build import BuildBuildRequireResourceDescription
from rolling.model.build import BuildRequireResourceDescription
from rolling.model.build import ZoneBuildModelContainer
from rolling.model.data import ListOfItemModel
from rolling.model.event import NewBuildData
from rolling.model.event import NewResumeTextData
from rolling.model.event import WebSocketEvent
from rolling.model.event import ZoneEventType
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.resource import ResourceDescriptionModel
from rolling.rolling_types import ActionType
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.document.build import BuildDocument
from rolling.server.link import CharacterActionLink
from rolling.util import ExpectedQuantityContext
from rolling.util import InputQuantityContext
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel


QUICK_ACTION_COST_TO_SPENT = 5.0


def get_build_progress(build_doc: BuildDocument, kernel: "Kernel") -> float:
    if not build_doc.under_construction:
        return 100

    build_description = kernel.game.config.builds[build_doc.build_id]
    build_spent_ap = float(build_doc.ap_spent)
    return (build_spent_ap * 100) / build_description.cost


class BeginBuildAction(CharacterAction):
    input_model = BeginBuildModel
    input_model_serializer = serpyco.Serializer(BeginBuildModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {
            "build_id": action_config_raw["build"],
            "require_resources": [
                BuildRequireResourceDescription(
                    resource_id=r["resource"], quantity=r["quantity"]
                )
                for r in action_config_raw.get("require_resources", [])
            ],
        }

    def check_is_possible(self, character: "CharacterModel") -> None:
        # TODO BS 2019-09-30: check is character have skill and stuff (but not resources
        # because we want to permit begin construction)
        pass

    async def check_request_is_possible(
        self, character: "CharacterModel", input_: typing.Any
    ) -> None:
        self.check_is_possible(character)

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        try:
            self.check_is_possible(character)
        except ImpossibleAction:
            pass

        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]
        return [
            CharacterActionLink(
                name=build_description.name,
                link=get_character_action_url(
                    character_id=character.id,
                    action_type=ActionType.BEGIN_BUILD,
                    action_description_id=self._description.id,
                    query_params={},
                ),
                group_name=build_description.group_name,
                classes1=build_description.classes + [build_description.id],
            )
        ]

    async def perform(
        self, character: "CharacterModel", input_: BeginBuildModel
    ) -> Description:
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]

        if not input_.confirm:
            items = get_build_description_parts(
                self._kernel, build_description, include_build_parts=True
            )

            cost = self.get_cost(character, input_=input_)
            items.append(
                Part(
                    label=f"Construire ({cost} PA)",
                    is_link=True,
                    form_action=get_character_action_url(
                        character_id=character.id,
                        action_type=ActionType.BEGIN_BUILD,
                        action_description_id=self._description.id,
                        query_params={"confirm": 1},
                    ),
                )
            )

            return Description(
                title=f"Construire {build_description.name}",
                items=items,
                illustration_name=build_description.illustration,
            )

        return Description(
            request_clicks=RequestClicks(
                action_type=ActionType.BEGIN_BUILD,
                action_description_id=self._description.id,
                cursor_classes=build_description.classes + [build_id],
                many=build_description.many,
            ),
        )

    async def perform_from_event(
        self, character: "CharacterModel", input_: BeginBuildModel
    ) -> typing.Tuple[typing.List[WebSocketEvent], typing.List[WebSocketEvent]]:
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]

        build_doc = self._kernel.build_lib.place_build(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.row_i,
            zone_col_i=input_.col_i,
            build_id=build_description.id,
            under_construction=True,
        )
        await self._kernel.character_lib.reduce_action_points(
            character_id=character.id, cost=self.get_cost(character, input_)
        )

        return (
            [
                WebSocketEvent(
                    type=ZoneEventType.NEW_BUILD,
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    data=NewBuildData(
                        build=ZoneBuildModelContainer(
                            doc=build_doc, desc=build_description
                        )
                    ),
                )
            ],
            [
                WebSocketEvent(
                    type=ZoneEventType.NEW_RESUME_TEXT,
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    data=NewResumeTextData(
                        resume=ListOfItemModel(
                            self._kernel.character_lib.get_resume_text(character.id)
                        )
                    ),
                )
            ],
        )


@dataclasses.dataclass
class BringResourceModel:
    resource_id: str
    quantity: typing.Optional[str] = None


class BringResourcesOnBuild(WithBuildAction):
    input_model = BringResourceModel
    input_model_serializer = serpyco.Serializer(BringResourceModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        return

    async def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: typing.Any
    ) -> None:
        return

    @classmethod
    def get_resource_infos(
        cls,
        kernel: "Kernel",
        required_resource: BuildBuildRequireResourceDescription,
        build_doc: BuildDocument,
        raise_if_missing: bool = False,
    ) -> typing.Tuple[ResourceDescriptionModel, float, float]:
        build_progress = get_build_progress(build_doc, kernel=kernel)
        stored_resources = kernel.resource_lib.get_stored_in_build(build_doc.id)
        stored_resources_by_resource_id: typing.Dict[
            str, CarriedResourceDescriptionModel
        ] = {
            stored_resource.id: stored_resource for stored_resource in stored_resources
        }

        resource_description = kernel.game.config.resources[
            required_resource.resource_id
        ]
        try:
            stored_resource = stored_resources_by_resource_id[
                required_resource.resource_id
            ]
            stored_resource_quantity = stored_resource.quantity
        except KeyError:
            if raise_if_missing:
                raise MissingResource(f"Il manque {resource_description.name}")
            stored_resource_quantity = 0.0

        absolute_left = required_resource.quantity - (
            required_resource.quantity * (build_progress / 100)
        )
        with_stored_left = absolute_left - stored_resource_quantity

        if with_stored_left < 0.0:
            with_stored_left = 0.0

        left = with_stored_left
        if left:
            left_percent = (left * 100) / required_resource.quantity
        else:
            left_percent = 0.0

        return resource_description, left, left_percent

    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]

        for required_resource in build_description.build_require_resources:
            resource_description, left, left_percent = self.get_resource_infos(
                self._kernel, required_resource, build_doc=build_doc
            )
            if left <= 0:
                continue

            left_str = quantity_to_str(
                left, resource_description.unit, kernel=self._kernel
            )

            query_params = BringResourcesOnBuild.input_model_serializer.dump(
                BringResourcesOnBuild.input_model(
                    resource_id=required_resource.resource_id
                )
            )
            name = (
                f"Apporter {resource_description.name} pour la construction "
                f"(manque {left_str} soit {round(left_percent)}%)"
            )
            actions.append(
                CharacterActionLink(
                    name=name,
                    link=get_with_build_action_url(
                        character_id=character.id,
                        build_id=build_id,
                        action_type=ActionType.BRING_RESOURCE_ON_BUILD,
                        action_description_id=self._description.id,
                        query_params=query_params,
                    ),
                    cost=None,
                    classes1=[resource_description.id],
                )
            )

        return actions

    async def perform(
        self, character: "CharacterModel", build_id: int, input_: typing.Any
    ) -> Description:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        carried_resource = self._kernel.resource_lib.get_one_carried_by(
            character_id=character.id,
            resource_id=input_.resource_id,
            empty_object_if_not=True,
        )
        expected_quantity_context = ExpectedQuantityContext.from_carried_resource(
            self._kernel, carried_resource
        )

        if input_.quantity is None:
            build_description = self._kernel.game.config.builds[build_doc.build_id]
            required_resource = next(
                (
                    brr
                    for brr in build_description.build_require_resources
                    if brr.resource_id == input_.resource_id
                )
            )
            resource_description, left, left_percent = self.get_resource_infos(
                self._kernel, required_resource, build_doc=build_doc
            )
            left_str = quantity_to_str(
                left, resource_description.unit, kernel=self._kernel
            )

            return Description(
                title=f"Cette construction nécessite encore {left_str} "
                f"de {resource_description.name} (soit {round(left_percent)}%)",
                can_be_back_url=True,
                footer_with_build_id=build_doc.id,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_build_action_url(
                            character_id=character.id,
                            build_id=build_id,
                            action_type=ActionType.BRING_RESOURCE_ON_BUILD,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(input_),
                        ),
                        items=[
                            Part(
                                label=f"Quantité ({expected_quantity_context.display_unit}) ?",
                                type_=Type.NUMBER,
                                name="quantity",
                                min_value=0.0,
                                max_value=expected_quantity_context.default_quantity_float,
                                default_value=expected_quantity_context.default_quantity,
                            )
                        ],
                    )
                ],
            )

        resource_description = self._kernel.game.config.resources[input_.resource_id]
        user_input_context = InputQuantityContext.from_carried_resource(
            user_input=input_.quantity, carried_resource=carried_resource
        )
        try:
            self._kernel.resource_lib.reduce_carried_by(
                character.id,
                resource_id=input_.resource_id,
                quantity=user_input_context.real_quantity,
                commit=False,
            )
        except (NotEnoughResource, NoCarriedResource):
            raise ImpossibleAction(
                f"{character.name} ne possède pas assez de {resource_description.name}"
            )

        self._kernel.resource_lib.add_resource_to(
            build_id=build_doc.id,
            resource_id=input_.resource_id,
            quantity=user_input_context.real_quantity,
            commit=False,
        )
        self._kernel.server_db_session.commit()

        build_description = self._kernel.game.config.builds[build_doc.build_id]
        quantity_str = quantity_to_str(
            user_input_context.real_quantity,
            resource_description.unit,
            kernel=self._kernel,
        )

        return Description(
            title=build_description.name,
            items=[
                Part(
                    text=(
                        f"{quantity_str} {resource_description.name} "
                        f"déposé pour {build_description.name}"
                    )
                )
            ],
            footer_with_build_id=build_doc.id,
            back_url=DESCRIBE_BUILD.format(
                build_id=build_doc.id, character_id=character.id
            ),
        )


@dataclasses.dataclass
class ConstructBuildModel:
    cost_to_spent: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )


class ConstructBuildAction(WithBuildAction):
    input_model = ConstructBuildModel
    input_model_serializer = serpyco.Serializer(ConstructBuildModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        if not build_doc.under_construction:
            raise ImpossibleAction("Cette construction est terminée")

    async def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: typing.Any
    ) -> None:
        # FIXME BS 2019-10-03: delete all check_request_is_possible and move into perform
        pass

    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        if build_doc.under_construction:
            return [
                CharacterActionLink(
                    name=f"Faire avancer la construction",
                    link=get_with_build_action_url(
                        character_id=character.id,
                        build_id=build_id,
                        action_type=ActionType.CONSTRUCT_BUILD,
                        action_description_id=self._description.id,
                        query_params={},
                    ),
                    cost=None,
                )
            ]

        return []

    def get_quick_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        if build_doc.under_construction:
            return [
                CharacterActionLink(
                    name=f"Continuer la construction",
                    link=get_with_build_action_url(
                        character_id=character.id,
                        build_id=build_id,
                        action_type=ActionType.CONSTRUCT_BUILD,
                        action_description_id=self._description.id,
                        query_params={"cost_to_spent": QUICK_ACTION_COST_TO_SPENT},
                    ),
                    cost=None,
                    direct_action=True,
                    classes1=["DO_BUILD_WORK"],
                    classes2=build_description.classes + [build_description.id],
                )
            ]
        return []

    def _get_biggest_left_percent(
        self, build_doc: BuildDocument, raise_if_missing: bool = False
    ) -> float:
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        biggest_left_percent = 0.0

        for required_resource in build_description.build_require_resources:
            (
                resource_description,
                left,
                left_percent,
            ) = BringResourcesOnBuild.get_resource_infos(
                self._kernel,
                required_resource,
                build_doc=build_doc,
                raise_if_missing=raise_if_missing,
            )
            if left_percent > biggest_left_percent:
                biggest_left_percent = left_percent

        return biggest_left_percent

    async def perform(
        self, character: "CharacterModel", build_id: int, input_: input_model
    ) -> Description:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_progress = get_build_progress(build_doc, kernel=self._kernel)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        try:
            lowest_required_left_percent = self._get_biggest_left_percent(
                build_doc, raise_if_missing=True
            )
        except MissingResource as exc:
            raise ImpossibleAction(str(exc))

        able_to_percent = 100 - lowest_required_left_percent
        maximum_pa_to_reach = build_description.cost * (able_to_percent / 100)
        max_pa_to_spent = round(maximum_pa_to_reach - float(build_doc.ap_spent), 2)

        if input_.cost_to_spent is None:
            title = (
                f"Cette construction est avancée à {round(build_progress)}%. Compte tenu des "
                f"réserves, vous pouvez avancer jusqu'a "
                f"{round(able_to_percent)}%, soit y passer maximum "
                f"{round(max_pa_to_spent, 2)} point d'actions"
            )
            return Description(
                title=title,
                footer_with_build_id=build_doc.id,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_build_action_url(
                            character_id=character.id,
                            build_id=build_id,
                            action_type=ActionType.CONSTRUCT_BUILD,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(input_),
                        ),
                        items=[
                            Part(
                                label=f"Y passer combien de temps (Point d'Actions) ?",
                                type_=Type.NUMBER,
                                name="cost_to_spent",
                                min_value=1.0,
                                max_value=min(character.action_points, max_pa_to_spent),
                            )
                        ],
                    )
                ],
            )

        # TODO : There is a bug in this code, rewrite the logic
        # For now, hack :
        if not max_pa_to_spent:
            raise ImpossibleAction(f"Pas assez ede matière")

        input_cost_to_spent = input_.cost_to_spent

        if input_.cost_to_spent > max_pa_to_spent:
            input_cost_to_spent = max_pa_to_spent

        # TODO BS 2019-10-08: When skills/stuff improve ap spent, compute real ap spent here and
        # indicate by error how much time to spent to spent max
        real_progress_cost = input_cost_to_spent

        if character.action_points < input_cost_to_spent:
            raise ImpossibleAction("Pas assez de Points d'Actions")

        consume_resources_percent = (real_progress_cost * 100) / build_description.cost

        await self._kernel.build_lib.progress_build(
            build_doc.id,
            real_progress_cost=real_progress_cost,
            consume_resources_percent=consume_resources_percent,
            commit=False,
        )
        await self._kernel.character_lib.reduce_action_points(
            character.id, cost=input_cost_to_spent, commit=False
        )
        self._kernel.server_db_session.commit()

        return Description(
            title=f"Travail effectué",
            footer_with_build_id=build_doc.id,
            back_url=DESCRIBE_BUILD.format(
                build_id=build_doc.id, character_id=character.id
            ),
            quick_action_response="Travail effectué",
        )


@dataclasses.dataclass
class BuildModel:
    row_i: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    col_i: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)


class BuildAction(CharacterAction):
    input_model = BuildModel
    input_model_serializer = serpyco.Serializer(BuildModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )
        properties["build_id"] = action_config_raw["build"]
        return properties

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass

    async def check_request_is_possible(
        self, character: "CharacterModel", input_: BuildModel
    ) -> None:
        check_common_is_possible(
            kernel=self._kernel, description=self._description, character=character
        )
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]

        if character.action_points < self.get_cost(character, input_):
            raise ImpossibleAction("Pas assez de points d'actions")

        for require in build_description.build_require_resources:
            if not self._kernel.resource_lib.have_resource(
                character_id=character.id,
                resource_id=require.resource_id,
                quantity=require.quantity,
            ):
                resource_properties = self._kernel.game.config.resources[
                    require.resource_id
                ]
                required_quantity_str = quantity_to_str(
                    require.quantity, resource_properties.unit, self._kernel
                )
                raise ImpossibleAction(
                    f"Vous ne possedez pas assez de {resource_properties.name} "
                    f"({required_quantity_str} requis)"
                )

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]
        return [
            CharacterActionLink(
                name=build_description.name,
                link=self.get_base_url(character),
                cost=self.get_cost(character),
                group_name=build_description.group_name,
                classes1=build_description.classes + [build_id],
            )
        ]

    def get_base_url(self, character: "CharacterModel") -> str:
        return get_character_action_url(
            character_id=character.id,
            action_type=ActionType.BUILD,
            action_description_id=self._description.id,
            query_params={},
        )

    async def perform(
        self, character: "CharacterModel", input_: BuildModel
    ) -> Description:
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]
        return Description(
            request_clicks=RequestClicks(
                action_type=ActionType.BUILD,
                action_description_id=self._description.id,
                cursor_classes=build_description.classes + [build_id],
                many=build_description.many,
            )
        )

    async def perform_from_event(
        self, character: "CharacterModel", input_: BuildModel
    ) -> typing.Tuple[typing.List[WebSocketEvent], typing.List[WebSocketEvent]]:
        assert input_.row_i
        assert input_.col_i
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]

        if not self._kernel.is_buildable_coordinate(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.row_i,
            zone_col_i=input_.col_i,
            for_build_id=build_id,
        ):
            raise ImpossibleAction("Emplacement non disponible")

        await self._kernel.zone_lib.destroy_tile(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.row_i,
            zone_col_i=input_.col_i,
            replace_by=None,
        )
        build_doc = self._kernel.build_lib.place_build(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.row_i,
            zone_col_i=input_.col_i,
            build_id=build_description.id,
            under_construction=False,
            commit=False,
        )
        await self._kernel.character_lib.reduce_action_points(
            character_id=character.id,
            cost=self.get_cost(character, input_),
            commit=False,
        )
        for require in build_description.build_require_resources:
            self._kernel.resource_lib.reduce_carried_by(
                character.id,
                resource_id=require.resource_id,
                quantity=require.quantity,
                commit=False,
            )
        self._kernel.server_db_session.commit()

        return (
            [
                WebSocketEvent(
                    type=ZoneEventType.NEW_BUILD,
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    data=NewBuildData(
                        build=ZoneBuildModelContainer(
                            doc=build_doc, desc=build_description
                        )
                    ),
                )
            ],
            [
                WebSocketEvent(
                    type=ZoneEventType.NEW_RESUME_TEXT,
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    data=NewResumeTextData(
                        resume=ListOfItemModel(
                            self._kernel.character_lib.get_resume_text(character.id)
                        )
                    ),
                )
            ],
        )
