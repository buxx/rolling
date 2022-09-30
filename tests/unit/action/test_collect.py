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
from rolling.util import Quantity
from tests.utils import parts_text


@pytest.fixture
def collect_action(worldmapc_kernel: Kernel) -> CollectResourceAction:
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
        collect_action: CollectResourceAction,
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
            replace_by_when_destroyed=None,
        )

        # check fixtures
        collect_action.check_is_possible(xena)
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
        await collect_action.perform(
            xena,
            input_=CollectResourceModel(
                resource_id="WOOD",
                quantity=Quantity(3.0),  # More than in dead tree,
                zone_row_i=0,
                zone_col_i=160,
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

    @pytest.mark.usefixtures("tmp_zone_folder")
    async def test_collect_bonuses(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        collect_action: CollectResourceAction,
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
            quantity=10.0,  # This is a big tree :)
            destroy_when_empty=True,
            replace_by_when_destroyed=None,
        )
        original_ap = xena.action_points
        extract_cost_per_unit = 0.01

        # Preliminaries checks
        assert xena.skills["logging"].value == 0.0

        # When
        description = await collect_action.perform(
            xena,
            input_=CollectResourceModel(
                resource_id="WOOD",
                zone_row_i=0,
                zone_col_i=160,
            ),
        )

        # Then
        assert (
            parts_text(description.items)
            == "Extraire 1 mètre cubes demande 0.01 PA\nBonus appliqués :\n - aucun"
        )

        # When
        description = await collect_action.perform(
            xena,
            input_=CollectResourceModel(
                resource_id="WOOD",
                zone_row_i=0,
                zone_col_i=160,
                quantity=Quantity(5.0),
            ),
        )
        xena = kernel.character_lib.get(xena.id)

        # Then
        assert xena.action_points == original_ap - (5.0 * extract_cost_per_unit)
        assert xena.skills["logging"].counter == 6.0
        assert round(xena.skills["logging"].value, 3) == 1.292

        # When
        description = await collect_action.perform(
            xena,
            input_=CollectResourceModel(
                resource_id="WOOD",
                zone_row_i=0,
                zone_col_i=160,
            ),
        )

        # Then
        assert (
            parts_text(description.items)
            == "Extraire 1 mètre cubes demande 0.0087 PA\nBonus appliqués :\n - Bûcheronnage (PAx0.871)"
        )

        # When
        description = await collect_action.perform(
            xena,
            input_=CollectResourceModel(
                resource_id="WOOD",
                zone_row_i=0,
                zone_col_i=160,
                quantity=Quantity(5.0),
            ),
        )
        xena = kernel.character_lib.get(xena.id)

        # Then
        assert round(xena.action_points, 2) == round(
            original_ap
            - (5.0 * extract_cost_per_unit)
            - (5.0 * extract_cost_per_unit * 0.871),
            2,
        )
