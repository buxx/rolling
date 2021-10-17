import pytest
import shutil

from rolling.action.base import ActionDescriptionModel
from rolling.action.collect import CollectResourceAction
from rolling.action.collect import CollectResourceModel
from rolling.kernel import Kernel
from rolling.map.type.zone import DeadTree
from rolling.map.type.zone import Dirt
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType


@pytest.fixture
def follow_action(worldmapc_kernel: Kernel) -> CollectResourceAction:
    return CollectResourceAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            action_type=ActionType.COLLECT_RESOURCE,
            base_cost=0.0,
            id="COLLECT_RESOURCE",
            properties={},
        ),
    )


@pytest.fixture
def tmp_zone_folder(worldmapc_kernel: Kernel):
    tmp_zone_folder_ = "/tmp/zones"
    shutil.rmtree(tmp_zone_folder_, ignore_errors=True)
    shutil.copytree(worldmapc_kernel.zone_maps_folder, tmp_zone_folder_)
    worldmapc_kernel._zone_maps_folder = tmp_zone_folder_


class TestCollectResourceAction:
    @pytest.mark.usefixtures("tmp_zone_folder")
    async def test_collect_more_than_tile_capacity(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        follow_action: CollectResourceAction,
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        xena_doc = kernel.character_lib.get_document(xena.id)
        xena_doc.world_row_i = 1
        xena_doc.world_col_i = 2
        xena_doc.zone_row_i = 0
        xena_doc.zone_col_i = 160
        kernel.server_db_session.add(xena_doc)
        kernel.server_db_session.commit()
        xena = kernel.character_lib.document_to_model(xena_doc)
        kernel.zone_lib.create_zone_ressource_doc(
            world_row_i=1,
            world_col_i=2,
            zone_row_i=0,
            zone_col_i=160,
            resource_id="WOOD",
            quantity=1.0,
            destroy_when_empty=True,
        )

        # check fixtures
        follow_action.check_is_possible(xena)
        assert (
            kernel.tile_maps_by_position[(1, 2)].source.geography.rows[0][160]
            == DeadTree
        )
        assert (
            kernel.resource_lib.get_one_carried_by(
                xena.id, resource_id="WOOD", empty_object_if_not=True
            ).quantity
            == 0.0
        )

        # When
        await follow_action.perform(
            xena,
            input_=CollectResourceModel(
                resource_id="WOOD",
                quantity=3.0,  # More than in dead tree,
                row_i=0,
                col_i=160,
            ),
        )

        # Then
        assert (
            kernel.tile_maps_by_position[(1, 2)].source.geography.rows[0][160] == Dirt
        )
        assert (
            kernel.resource_lib.get_one_carried_by(
                xena.id, resource_id="WOOD", empty_object_if_not=True
            ).quantity
            == 1.0
        )
