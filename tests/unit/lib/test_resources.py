# coding: utf-8
import pytest

from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.server.document.build import BuildDocument


@pytest.fixture
def worldmapc_test_build_1(worldmapc_kernel: Kernel) -> BuildDocument:
    doc = BuildDocument(
        id=42,
        world_col_i=0,
        world_row_i=0,
        zone_col_i=0,
        zone_row_i=0,
        build_id="TEST_BUILD_1",
        ap_spent=0.0,
        under_construction=True,
    )
    worldmapc_kernel.server_db_session.add(doc)
    worldmapc_kernel.server_db_session.commit()
    return doc


class TestResourceLib:
    def test_unit__add_resource_to__ok__character(
        self, worldmapc_xena_model: CharacterModel, worldmapc_kernel: Kernel
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        assert not kernel.resource_lib.get_carried_by(xena.id)
        kernel.resource_lib.add_resource_to(
            character_id=xena.id, resource_id="BRANCHES", quantity=0.1, commit=True
        )
        carried = kernel.resource_lib.get_carried_by(xena.id)
        assert carried
        assert 1 == len(carried)
        assert "BRANCHES" == carried[0].id
        assert 0.1 == carried[0].quantity

    def test_unit__add_resource_to__ok__build(
        self, worldmapc_kernel: Kernel, worldmapc_test_build_1: BuildDocument
    ) -> None:
        kernel = worldmapc_kernel
        build = worldmapc_test_build_1

        assert not kernel.resource_lib.get_stored_in_build(build.id)
        kernel.resource_lib.add_resource_to(
            build_id=build.id, resource_id="BRANCHES", quantity=0.1, commit=True
        )
        carried = kernel.resource_lib.get_stored_in_build(build.id)
        assert carried
        assert 1 == len(carried)
        assert "BRANCHES" == carried[0].id
        assert 0.1 == carried[0].quantity

    def test_unit__add_resource_to__ok__ground(self, worldmapc_kernel: Kernel) -> None:
        kernel = worldmapc_kernel

        assert not kernel.resource_lib.get_ground_resource(
            world_col_i=0, world_row_i=0, zone_col_i=0, zone_row_i=0
        )
        kernel.resource_lib.add_resource_to(
            ground=True,
            resource_id="BRANCHES",
            quantity=0.1,
            commit=True,
            world_col_i=0,
            world_row_i=0,
            zone_col_i=0,
            zone_row_i=0,
        )
        carried = kernel.resource_lib.get_ground_resource(
            world_col_i=0, world_row_i=0, zone_col_i=0, zone_row_i=0
        )
        assert carried
        assert 1 == len(carried)
        assert "BRANCHES" == carried[0].id
        assert 0.1 == carried[0].quantity
