# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import WithBuildAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_with_build_action_url
from rolling.action.utils import check_common_is_possible
from rolling.action.utils import fill_base_action_properties
from rolling.exception import ImpossibleAction
from rolling.exception import MissingResource
from rolling.exception import NoCarriedResource
from rolling.exception import NotEnoughActionPoints
from rolling.exception import NotEnoughResource
from rolling.model.build import BuildBuildRequireResourceDescription
from rolling.model.build import BuildRequireResourceDescription
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.resource import ResourceDescriptionModel
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.document.build import BuildDocument
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import EmptyModel
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel


def get_build_progress(build_doc: BuildDocument, kernel: "Kernel") -> float:
    if not build_doc.under_construction:
        return 100

    build_description = kernel.game.config.builds[build_doc.build_id]
    build_spent_ap = float(build_doc.ap_spent)
    return (build_spent_ap * 100) / build_description.cost


class BeginBuildAction(CharacterAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {
            "build_id": action_config_raw["build"],
            "require_resources": [
                BuildRequireResourceDescription(resource_id=r["resource"], quantity=r["quantity"])
                for r in action_config_raw.get("require_resources", [])
            ],
        }

    def check_is_possible(self, character: "CharacterModel") -> None:
        # TODO BS 2019-09-30: check is character have skill and stuff (but not resources
        # because we want to permit begin construction)
        pass

    def check_request_is_possible(self, character: "CharacterModel", input_: typing.Any) -> None:
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
                cost=self.get_cost(character, input_=None),
            )
        ]

    def perform(self, character: "CharacterModel", input_: typing.Any) -> Description:
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]
        build_doc = self._kernel.build_lib.place_build(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            build_id=build_description.id,
            under_construction=True,
        )
        self._kernel.character_lib.reduce_action_points(
            character_id=character.id, cost=self.get_cost(character, input_)
        )
        return Description(
            title=f"{build_description.name} commencé",
            items=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    label="Voir le batiment",
                    is_link=True,
                    form_action=DESCRIBE_BUILD.format(
                        build_id=build_doc.id, character_id=character.id
                    ),
                ),
            ],
            force_back_url=f"/_describe/character/{character.id}/build_actions",
        )


@dataclasses.dataclass
class BringResourceModel:
    resource_id: str
    quantity: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


class BringResourcesOnBuild(WithBuildAction):
    input_model = BringResourceModel
    input_model_serializer = serpyco.Serializer(BringResourceModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        return

    def check_request_is_possible(
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
        stored_resources_by_resource_id: typing.Dict[str, CarriedResourceDescriptionModel] = {
            stored_resource.id: stored_resource for stored_resource in stored_resources
        }

        resource_description = kernel.game.config.resources[required_resource.resource_id]
        try:
            stored_resource = stored_resources_by_resource_id[required_resource.resource_id]
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

            left_str = quantity_to_str(left, resource_description.unit, kernel=self._kernel)

            query_params = BringResourcesOnBuild.input_model_serializer.dump(
                BringResourcesOnBuild.input_model(resource_id=required_resource.resource_id)
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
                )
            )

        return actions

    def perform(
        self, character: "CharacterModel", build_id: int, input_: typing.Any
    ) -> Description:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)

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
            left_str = quantity_to_str(left, resource_description.unit, kernel=self._kernel)
            unit_str = self._kernel.translation.get(resource_description.unit)

            return Description(
                title=f"Cette construction nécessite encore {left_str} "
                f"de {resource_description.name} (soit {round(left_percent)}%)",
                can_be_back_url=True,
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
                                label=f"Quantité ({unit_str}) ?", type_=Type.NUMBER, name="quantity"
                            )
                        ],
                    )
                ],
            )

        resource_description = self._kernel.game.config.resources[input_.resource_id]
        try:
            self._kernel.resource_lib.reduce_carried_by(
                character.id, resource_id=input_.resource_id, quantity=input_.quantity, commit=False
            )
        except (NotEnoughResource, NoCarriedResource):
            raise ImpossibleAction(
                f"{character.name} ne possède pas assez de {resource_description.name}"
            )

        self._kernel.resource_lib.add_resource_to(
            build_id=build_doc.id,
            resource_id=input_.resource_id,
            quantity=input_.quantity,
            commit=False,
        )
        self._kernel.server_db_session.commit()

        build_description = self._kernel.game.config.builds[build_doc.build_id]
        quantity_str = quantity_to_str(
            input_.quantity, resource_description.unit, kernel=self._kernel
        )

        return Description(
            title=f"{quantity_str} {resource_description.name} déposé pour {build_description.name}",
            items=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    label="Voir le batiment",
                    is_link=True,
                    form_action=DESCRIBE_BUILD.format(
                        build_id=build_doc.id, character_id=character.id
                    ),
                ),
            ],
            force_back_url=f"/_describe/character/{character.id}/build_actions",
        )


@dataclasses.dataclass
class ConstructBuildModel:
    cost_to_spent: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


class ConstructBuildAction(WithBuildAction):
    input_model = ConstructBuildModel
    input_model_serializer = serpyco.Serializer(ConstructBuildModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        if not build_doc.under_construction:
            raise ImpossibleAction("Cette construction est terminée")

    def check_request_is_possible(
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

    def _get_biggest_left_percent(
        self, build_doc: BuildDocument, raise_if_missing: bool = False
    ) -> float:
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        biggest_left_percent = 0.0

        for required_resource in build_description.build_require_resources:
            resource_description, left, left_percent = BringResourcesOnBuild.get_resource_infos(
                self._kernel,
                required_resource,
                build_doc=build_doc,
                raise_if_missing=raise_if_missing,
            )
            if left_percent > biggest_left_percent:
                biggest_left_percent = left_percent

        return biggest_left_percent

    def perform(
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
        max_pa_to_spent = maximum_pa_to_reach - float(build_doc.ap_spent)

        if input_.cost_to_spent is None:
            title = (
                f"Cette construction est avancée à {round(build_progress)}%. Compte tenu des "
                f"réserves, vous pouvez avancer jusqu'a "
                f"{round(able_to_percent)}%, soit y passer maximum "
                f"{round(max_pa_to_spent, 2)} point d'actions"
            )
            return Description(
                title=title,
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
                                label=f"Y passer combien de temps (point d'actions) ?",
                                type_=Type.NUMBER,
                                name="cost_to_spent",
                            )
                        ],
                    )
                ],
            )

        input_cost_to_spent = input_.cost_to_spent

        if input_.cost_to_spent > max_pa_to_spent:
            input_cost_to_spent = max_pa_to_spent

        # TODO BS 2019-10-08: When skills/stuff improve ap spent, compute real ap spent here and
        # indicate by error how much time to spent to spent max
        real_progress_cost = input_cost_to_spent

        if character.action_points < input_cost_to_spent:
            raise ImpossibleAction("Pas assez de Points d'Actions")

        consume_resources_percent = (real_progress_cost * 100) / build_description.cost

        self._kernel.build_lib.progress_build(
            build_doc.id,
            real_progress_cost=real_progress_cost,
            consume_resources_percent=consume_resources_percent,
            commit=False,
        )
        self._kernel.character_lib.reduce_action_points(
            character.id, cost=input_cost_to_spent, commit=False
        )
        self._kernel.server_db_session.commit()

        return Description(
            title=f"Travail effectué",
            items=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    label="Voir le batiment",
                    is_link=True,
                    form_action=DESCRIBE_BUILD.format(
                        build_id=build_doc.id, character_id=character.id
                    ),
                ),
            ],
            force_back_url=f"/_describe/character/{character.id}/build_actions",
        )


class BuildAction(CharacterAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        properties = fill_base_action_properties(cls, game_config, {}, action_config_raw)
        properties["build_id"] = action_config_raw["build"]
        return properties

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass

    def check_request_is_possible(self, character: "CharacterModel", input_: EmptyModel) -> None:
        check_common_is_possible(
            kernel=self._kernel, description=self._description, character=character
        )
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]

        for require in build_description.build_require_resources:
            if not self._kernel.resource_lib.have_resource(
                character.id, resource_id=require.resource_id, quantity=require.quantity
            ):
                resource_properties = self._kernel.game.config.resources[require.resource_id]
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
                link=get_character_action_url(
                    character_id=character.id,
                    action_type=ActionType.BUILD,
                    action_description_id=self._description.id,
                    query_params={},
                ),
                cost=self.get_cost(character),
            )
        ]

    def perform(self, character: "CharacterModel", input_: EmptyModel) -> Description:
        build_id = self._description.properties["build_id"]
        build_description = self._kernel.game.config.builds[build_id]
        build_doc = self._kernel.build_lib.place_build(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            build_id=build_description.id,
            under_construction=False,
            commit=False,
        )
        self._kernel.character_lib.reduce_action_points(
            character_id=character.id, cost=self.get_cost(character, input_), commit=False
        )
        for require in build_description.build_require_resources:
            self._kernel.resource_lib.reduce_carried_by(
                character.id,
                resource_id=require.resource_id,
                quantity=require.quantity,
                commit=False,
            )
        self._kernel.server_db_session.commit()

        return Description(
            title=f"{build_description.name} construit",
            items=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    label="Voir le batiment",
                    is_link=True,
                    form_action=DESCRIBE_BUILD.format(
                        build_id=build_doc.id, character_id=character.id
                    ),
                ),
            ],
            force_back_url=f"/_describe/character/{character.id}/build_actions",
        )
