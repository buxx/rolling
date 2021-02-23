# coding: utf-8
import pytest

from rolling.action.base import ActionDescriptionModel
from rolling.action.build_power import PowerOffBuildAction, PowerOnBuildAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from rolling.server.document.build import BuildDocument
from rolling.util import EmptyModel


@pytest.fixture
def build1(
    worldmapc_kernel: Kernel,
) -> BuildDocument:
    kernel = worldmapc_kernel
    return kernel.build_lib.place_build(
        world_col_i=0,
        world_row_i=0,
        zone_col_i=0,
        zone_row_i=0,
        build_id="TEST_BUILD_1",
        under_construction=False,
    )


@pytest.fixture
def power_off_action(worldmapc_kernel: Kernel) -> PowerOffBuildAction:
    action = PowerOffBuildAction(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="ACTION_ID",
            action_type=ActionType.POWER_OFF_BUILD,
            base_cost=0.5,
            properties={},
        ),
    )
    yield action


@pytest.fixture
def power_on_action(worldmapc_kernel: Kernel) -> PowerOnBuildAction:
    action = PowerOnBuildAction(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="ACTION_ID",
            action_type=ActionType.POWER_ON_BUILD,
            base_cost=0.5,
            properties={},
        ),
    )
    yield action


class TestPowerBuild:
    def test_power_on_build_with_enough_resources(
        self,
        worldmapc_kernel: Kernel,
        build1: BuildDocument,
        power_on_action: PowerOnBuildAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        # Given
        kernel.resource_lib.add_resource_to(
            build_id=build1.id,
            resource_id="BRANCHES",
            quantity=0.002,  # power on require 0.001
        )
        assert not kernel.build_lib.get_build_doc(build1.id).is_on
        assert kernel.resource_lib.have_resource(
            resource_id="BRANCHES", build_id=build1.id, quantity=0.002
        )

        # When
        power_on_action.perform(xena, build_id=build1.id, input_=EmptyModel())

        # Then
        assert kernel.build_lib.get_build_doc(build1.id).is_on
        assert kernel.resource_lib.have_resource(
            resource_id="BRANCHES", build_id=build1.id, quantity=0.001
        )

    def test_power_on_build_with_not_enough_resources(
        self,
        worldmapc_kernel: Kernel,
        build1: BuildDocument,
        power_on_action: PowerOnBuildAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        # Given
        kernel.resource_lib.add_resource_to(
            build_id=build1.id,
            resource_id="BRANCHES",
            quantity=0.0005,  # power on require 0.001
        )
        assert not kernel.build_lib.get_build_doc(build1.id).is_on
        assert kernel.resource_lib.have_resource(
            resource_id="BRANCHES", build_id=build1.id, quantity=0.0005
        )

        # When
        power_on_action.perform(xena, build_id=build1.id, input_=EmptyModel())

        # Then
        assert not kernel.build_lib.get_build_doc(build1.id).is_on
        assert kernel.resource_lib.have_resource(
            resource_id="BRANCHES", build_id=build1.id, quantity=0.0005
        )

    def test_power_on_build_with_no_resources(
        self,
        worldmapc_kernel: Kernel,
        build1: BuildDocument,
        power_on_action: PowerOnBuildAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        # Given
        assert not kernel.build_lib.get_build_doc(build1.id).is_on

        # When
        power_on_action.perform(xena, build_id=build1.id, input_=EmptyModel())

        # Then
        assert not kernel.build_lib.get_build_doc(build1.id).is_on

    def test_power_off_build(
        self,
        worldmapc_kernel: Kernel,
        build1: BuildDocument,
        power_off_action: PowerOnBuildAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        # Given
        build1.is_on = True
        kernel.server_db_session.commit()

        # When
        power_off_action.perform(xena, build_id=build1.id, input_=EmptyModel())

        # Then
        assert not kernel.build_lib.get_build_doc(build1.id).is_on
