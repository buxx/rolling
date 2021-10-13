import pytest

from rolling.action.base import ActionDescriptionModel
from rolling.action.destroy import DestroyBuildAction
from rolling.action.destroy import DestroyBuildModel
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from rolling.server.document.build import DOOR_MODE__CLOSED
from tests.fixtures import create_stuff


@pytest.fixture
def power_off_action(worldmapc_kernel: Kernel) -> DestroyBuildAction:
    action = DestroyBuildAction(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="ACTION_ID",
            action_type=ActionType.DESTROY_BUILD,
            base_cost=0.0,
            properties={},
        ),
    )
    yield action


class TestDestroyBuildAction:
    def test_destroy_door_with_relations(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        power_off_action: DestroyBuildAction,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        door = kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=10,
            zone_col_i=10,
            build_id="DOOR",
            under_construction=False,
        )
        kernel.door_lib.update(
            character_id=xena.id,
            build_id=door.id,
            new_mode=DOOR_MODE__CLOSED,
        )
        assert kernel.door_lib.get_door_relations_query(door.id).count()
        assert kernel.build_lib.get_all_ids(None)

        # When
        description = power_off_action.perform(
            xena,
            build_id=door.id,
            input_=DestroyBuildModel(
                spent_all_ap=1,
            ),
        )

        # Then
        assert not kernel.door_lib.get_door_relations_query(door.id).count()
        assert not kernel.build_lib.get_all_ids(None)
        assert description.back_to_zone

    def test_destroy_door_one_ap(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        power_off_action: DestroyBuildAction,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        door = kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=10,
            zone_col_i=10,
            build_id="DOOR",
            under_construction=False,
        )
        assert kernel.build_lib.get_all_ids(None)

        # When
        description = power_off_action.perform(
            xena,
            build_id=door.id,
            input_=DestroyBuildModel(
                spent_1_ap=1,
            ),
        )

        # Then
        assert kernel.build_lib.get_all_ids(None)
        assert not description.back_to_zone

        # When
        description = power_off_action.perform(
            xena,
            build_id=door.id,
            input_=DestroyBuildModel(
                spent_1_ap=1,
            ),
        )

        # Then
        assert not kernel.build_lib.get_all_ids(None)
        assert description.back_to_zone

    def test_destroy_build_with_ressource_and_stuffs(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        power_off_action: DestroyBuildAction,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        build = kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=10,
            zone_col_i=10,
            build_id="TEST_BUILD_1",
            under_construction=False,
        )
        kernel.resource_lib.add_resource_to(
            resource_id="RES1",
            build_id=build.id,
            quantity=1.0,
        )
        stuff = create_stuff(kernel, stuff_id="STONE_HAXE")
        kernel.stuff_lib.place_in_build(
            build_id=build.id,
            stuff_id=stuff.id,
        )

        # When
        description = power_off_action.perform(
            xena,
            build_id=build.id,
            input_=DestroyBuildModel(
                spent_all_ap=1,
            ),
        )

        # Then
        assert not kernel.build_lib.get_all_ids(None)
        assert description.back_to_zone
        assert kernel.resource_lib.get_ground_resource(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=10,
            zone_col_i=10,
        )
        assert kernel.stuff_lib.get_base_query(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=10,
            zone_col_i=10,
        ).count()
