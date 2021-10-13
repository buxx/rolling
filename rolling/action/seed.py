import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import RequestClicks
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.action.utils import fill_base_action_properties
from rolling.exception import ImpossibleAction
from rolling.exception import NoCarriedResource
from rolling.exception import NotEnoughResource
from rolling.model.build import ZoneBuildModelContainer
from rolling.model.data import ListOfItemModel
from rolling.model.event import NewBuildData
from rolling.model.event import NewResumeTextData
from rolling.model.event import WebSocketEvent
from rolling.model.event import ZoneEventType
from rolling.rolling_types import ActionType
from rolling.server.document.build import BuildDocument
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class SeedModel:
    row_i: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    col_i: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)


class SeedAction(CharacterAction):
    input_model = SeedModel
    input_model_serializer = serpyco.Serializer(SeedModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        properties = fill_base_action_properties(
            cls, game_config, {}, action_config_raw
        )
        resource_id = action_config_raw["resource_id"]
        properties["build_id"] = action_config_raw["build_id"]
        properties["resource_id"] = resource_id
        properties["consume"] = action_config_raw["consume"]
        # Check resource is properly configure (and crash at server startup if not)
        assert (
            game_config.resources[properties["resource_id"]].grow_speed is not None
        ), f"{resource_id} must have a grow_speed value"
        return properties

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass

    def _get_concerned_build_and_check_is_possible(
        self, character: "CharacterModel", input_: SeedModel
    ) -> BuildDocument:
        builds = self._kernel.build_lib.get_zone_build(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=input_.row_i,
            zone_col_i=input_.col_i,
        )
        wanted_build_id = self._description.properties["build_id"]
        if wanted_build_id not in [build.build_id for build in builds]:
            raise ImpossibleAction("Pas de terrain adapté ici")

        concerned_build = next(
            build for build in builds if build.build_id == wanted_build_id
        )
        if self._kernel.farming_lib.is_seeded(build=concerned_build):
            raise ImpossibleAction("Déjà semé ici")

        return concerned_build

    def check_request_is_possible(
        self, character: "CharacterModel", input_: SeedModel
    ) -> None:
        resource_id = self._description.properties["resource_id"]
        if not self._kernel.resource_lib.get_one_carried_by(
            character_id=character.id,
            resource_id=resource_id,
            empty_object_if_not=True,
        ).quantity:
            resource_description = self._kernel.game.config.resources[resource_id]
            raise ImpossibleAction(
                f"Vous ne possedez pas de {resource_description.name}"
            )

        if input_.row_i is not None and input_.col_i is not None:
            self._get_concerned_build_and_check_is_possible(
                character=character, input_=input_
            )

    def get_base_url(self, character: "CharacterModel") -> str:
        return get_character_action_url(
            character_id=character.id,
            action_type=ActionType.SEED,
            action_description_id=self._description.id,
            query_params={},
        )

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name=self._description.name,
                link=self.get_base_url(character),
                cost=self.get_cost(character),
                group_name="Semer",
                category="Agriculture",
            )
        ]

    def perform(self, character: "CharacterModel", input_: SeedModel) -> Description:
        return Description(
            request_clicks=RequestClicks(
                action_type=ActionType.SEED,
                action_description_id=self._description.id,
                cursor_classes=["SEEDS"],
                many=True,
            )
        )

    def perform_from_event(
        self, character: "CharacterModel", input_: SeedModel
    ) -> typing.Tuple[typing.List[WebSocketEvent], typing.List[WebSocketEvent]]:
        assert input_.row_i
        assert input_.col_i
        concerned_build: BuildDocument = (
            self._get_concerned_build_and_check_is_possible(
                character=character, input_=input_
            )
        )
        resource_id = self._description.properties["resource_id"]

        try:
            self._kernel.resource_lib.reduce_carried_by(
                character_id=character.id,
                resource_id=resource_id,
                quantity=self._description.properties["consume"],
                commit=False,
            )
        except (NoCarriedResource, NotEnoughResource):
            resource_description = self._kernel.game.config.resources[resource_id]
            raise ImpossibleAction(f"Pas assez de {resource_description.name}")

        self._kernel.farming_lib.seed(
            build=concerned_build,
            resource_id=resource_id,
            commit=False,
        )
        self._kernel.character_lib.reduce_action_points(
            character_id=character.id,
            cost=self.get_cost(character=character, input_=input_),
            commit=False,
        )

        self._kernel.server_db_session.commit()

        build_description = self._kernel.game.config.builds[concerned_build.build_id]
        build_container = ZoneBuildModelContainer(
            doc=concerned_build, desc=build_description
        )
        growing_state_classes = self._kernel.farming_lib.get_growing_state_classes(
            build=concerned_build
        )
        build_container.classes = (
            build_description.classes
            + [concerned_build.build_id]
            + growing_state_classes
        )

        return (
            [
                WebSocketEvent(
                    type=ZoneEventType.NEW_BUILD,
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    data=NewBuildData(build=build_container),
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
