# coding: utf-8
import pytest
from unittest import mock

from rolling.action.base import ActionDescriptionModel
from rolling.action.build import ConstructBuildAction
from rolling.action.build import ConstructBuildModel
from rolling.exception import ImpossibleAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from rolling.server.document.build import BuildDocument
from rolling.server.document.resource import ResourceDocument


@pytest.fixture
def worldmapc_mock_build_document(
    worldmapc_kernel: Kernel,
) -> BuildDocument:
    kernel = worldmapc_kernel
    return kernel.build_lib.place_build(
        world_col_i=0,
        world_row_i=0,
        zone_col_i=0,
        zone_row_i=0,
        build_id="TEST_BUILD_1",
        under_construction=True,
    )


@pytest.fixture
def worldmapc_mock_build_document2(
    worldmapc_kernel: Kernel,
) -> BuildDocument:
    kernel = worldmapc_kernel
    return kernel.build_lib.place_build(
        world_col_i=0,
        world_row_i=0,
        zone_col_i=0,
        zone_row_i=0,
        build_id="TEST_BUILD_2",
        under_construction=True,
    )


@pytest.fixture
def action(worldmapc_kernel: Kernel) -> ConstructBuildAction:
    action = ConstructBuildAction(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="ACTION_ID",
            action_type=ActionType.BRING_RESOURCE_ON_BUILD,
            base_cost=0.0,
            properties={},
        ),
    )
    yield action


class TestConstructBuildAction:
    def test__get_character_actions__build_finished(
        self,
        action: ConstructBuildAction,
        worldmapc_mock_build_document: BuildDocument,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        build.under_construction = False
        assert not action.get_character_actions(xena, build.id)

    def test__get_character_actions__build_not_started_no_resources(
        self,
        action: ConstructBuildAction,
        worldmapc_mock_build_document: BuildDocument,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        build.under_construction = True
        actions = action.get_character_actions(xena, build.id)
        assert actions
        assert 1 == len(actions)
        action = actions.pop()
        assert (
            f"/character/xena/with-build-action/CONSTRUCT_BUILD/{build.id}/ACTION_ID?"
            == action.link
        )
        assert "Faire avancer la construction" == action.name

    async def test__perform_some_hours__build_not_started_no_resources(
        self,
        action: ConstructBuildAction,
        worldmapc_mock_build_document: BuildDocument,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        with pytest.raises(ImpossibleAction) as exc:
            await action.perform(
                xena,
                build.id,
                input_=ConstructBuildModel(
                    cost_to_spent=1.0  # no resource so 0% progress possible
                ),
            )
        assert "Il manque Petit bois" == str(exc.value)

    async def test__perform__build_not_started_with_some_resources(
        self,
        action: ConstructBuildAction,
        worldmapc_kernel: Kernel,
        worldmapc_mock_build_document: BuildDocument,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        kernel = worldmapc_kernel
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        kernel.server_db_session.add(
            ResourceDocument(
                resource_id="BRANCHES",  # see src/game1/game.toml
                quantity=0.0005,  # 50% see src/game1/game.toml
                in_built_id=build.id,
            )
        )

        assert build.under_construction
        assert 0.0 == float(build.ap_spent)

        # Possible, but 1.0 really spent
        await action.perform(
            xena,
            build.id,
            input_=ConstructBuildModel(
                cost_to_spent=1.1
            ),  # no resource so 50% progress possible
        )

        xena_ = kernel.character_lib.get(xena.id)
        assert 24.0 - 1.0 == xena_.action_points
        assert build.under_construction
        assert 1.0 == float(build.ap_spent)

        assert not kernel.resource_lib.get_stored_in_build(build_id=build.id)

        # If try to continue, miss resources
        with pytest.raises(ImpossibleAction) as exc:
            await action.perform(
                xena,
                build.id,
                input_=ConstructBuildModel(
                    cost_to_spent=1.0  # no resource so 50% max progress possible
                ),
            )
        assert "Il manque Petit bois" == str(exc.value)

        # Add some branches
        kernel.server_db_session.add(
            ResourceDocument(
                resource_id="BRANCHES",  # see src/game1/game.toml
                quantity=0.0005,  # 50% see src/game1/game.toml
                in_built_id=build.id,
            )
        )

        assert 24.0 - 1.0 == xena_.action_points
        assert build.under_construction
        assert 1.0 == float(build.ap_spent)

        # can finish now
        await action.perform(
            xena,
            build.id,
            input_=ConstructBuildModel(
                cost_to_spent=1.0
            ),  # no resource so 50% progress possible
        )

        xena_ = kernel.character_lib.get(xena.id)
        assert 24.0 - 2.0 == xena_.action_points
        assert not build.under_construction
        assert 2.0 == float(build.ap_spent)
        assert not kernel.resource_lib.get_stored_in_build(build_id=build.id)

    async def test__perform__build_not_started_with_multiple_resources(
        self,
        action: ConstructBuildAction,
        worldmapc_kernel: Kernel,
        worldmapc_mock_build_document2: BuildDocument,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        kernel = worldmapc_kernel
        build = worldmapc_mock_build_document2
        xena = worldmapc_xena_model
        assert not build.is_on

        # Missing branches (and stone)
        with pytest.raises(ImpossibleAction) as exc:
            await action.perform(xena, build.id, input_=ConstructBuildModel())
        assert "Il manque Petit bois" == str(exc.value)

        kernel.server_db_session.add(
            ResourceDocument(
                resource_id="BRANCHES",  # see src/game1/game.toml
                quantity=0.0005,  # 50% see src/game1/game.toml
                in_built_id=build.id,
            )
        )

        assert build.under_construction
        assert 0.0 == float(build.ap_spent)

        # Missing stones
        with pytest.raises(ImpossibleAction) as exc:
            await action.perform(xena, build.id, input_=ConstructBuildModel())
        assert "Il manque Pierre" == str(exc.value)

        kernel.server_db_session.add(
            ResourceDocument(
                resource_id="STONE",  # see src/game1/game.toml
                quantity=2.0,  # 20% see src/game1/game.toml
                in_built_id=build.id,
            )
        )

        # Possible, but 0.2 really spent (20% stones)
        await action.perform(
            xena, build.id, input_=ConstructBuildModel(cost_to_spent=2.0)
        )

        xena_ = kernel.character_lib.get(xena.id)
        assert 24.0 - 0.4 == xena_.action_points
        assert build.under_construction
        assert 0.4 == float(build.ap_spent)

        resources = kernel.resource_lib.get_stored_in_build(build_id=build.id)
        assert resources
        assert 1 == len(resources)
        resource = resources.pop()
        assert "BRANCHES" == resource.id
        assert 0.0003 == resource.quantity

        # If try to continue, miss resources
        with pytest.raises(ImpossibleAction) as exc:
            await action.perform(xena, build.id, input_=ConstructBuildModel())
        assert "Il manque Pierre" == str(exc.value)

        assert 24.0 - 0.4 == xena_.action_points
        assert build.under_construction
        assert 0.4 == float(build.ap_spent)

        # Add some stones and branches
        kernel.resource_lib.add_resource_to(
            resource_id="BRANCHES",  # see src/game1/game.toml
            quantity=0.0005,  # 50% see src/game1/game.toml
            build_id=build.id,
        )
        kernel.resource_lib.add_resource_to(
            resource_id="STONE",  # see src/game1/game.toml
            quantity=8.0,  # 50% see src/game1/game.toml
            build_id=build.id,
        )

        # can finish now
        await action.perform(
            xena, build.id, input_=ConstructBuildModel(cost_to_spent=1.8)
        )

        xena_ = kernel.character_lib.get(xena.id)
        assert 24.0 - 2.0 == xena_.action_points
        assert not build.under_construction
        assert 2.0 == float(build.ap_spent)
        assert not kernel.resource_lib.get_stored_in_build(build_id=build.id)
        assert build.is_on
