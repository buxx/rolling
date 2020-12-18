# coding: utf-8
import pytest
from unittest import mock

from rolling.action.base import ActionDescriptionModel
from rolling.action.build import BringResourceModel
from rolling.action.build import BringResourcesOnBuild
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from rolling.server.document.build import BuildDocument
from rolling.server.document.resource import ResourceDocument


@pytest.fixture
def worldmapc_mock_build_document(worldmapc_kernel: Kernel,) -> BuildDocument:
    kernel = worldmapc_kernel
    build_document = BuildDocument(
        id=42,
        world_col_i=0,
        world_row_i=0,
        zone_col_i=0,
        zone_row_i=0,
        build_id="TEST_BUILD_1",
        ap_spent=0.0,
        under_construction=True,
    )

    with mock.patch.object(kernel.build_lib, "get_build_doc", return_value=build_document):
        yield build_document


@pytest.fixture
def action(worldmapc_kernel: Kernel) -> BringResourcesOnBuild:
    action = BringResourcesOnBuild(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="ACTION_ID",
            action_type=ActionType.BRING_RESOURCE_ON_BUILD,
            base_cost=0.5,
            properties={},
        ),
    )
    yield action


class TestBringResourcesOnBuild:
    def test_unit__get_character_actions__nothing_on_place_and_no_progress(
        self,
        action: BringResourcesOnBuild,
        worldmapc_xena_model: CharacterModel,
        worldmapc_mock_build_document: BuildDocument,
    ) -> None:
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        character_actions = action.get_character_actions(xena, build.id)
        assert character_actions
        assert 1 == len(character_actions)
        character_action = character_actions.pop()
        assert (
            "/character/xena/with-build-action/"
            "BRING_RESOURCE_ON_BUILD/42/ACTION_ID"
            "?resource_id=BRANCHES" == character_action.link
        )
        assert (
            "Apporter Petit bois pour la construction "
            "(manque 0.001 mètre cubes soit 100%)" == character_action.name
        )

    def test_unit__get_character_actions__something_on_place_and_no_progress(
        self,
        action: BringResourcesOnBuild,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_mock_build_document: BuildDocument,
    ) -> None:
        kernel = worldmapc_kernel
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        # Add some resources in building
        kernel.server_db_session.add(
            ResourceDocument(
                resource_id="BRANCHES",  # see src/game1/game.toml
                quantity=0.00075,  # 50%, see src/game1/game.toml
                in_built_id=build.id,
            )
        )
        kernel.server_db_session.commit()

        character_actions = action.get_character_actions(xena, build.id)
        assert character_actions
        assert 1 == len(character_actions)
        character_action = character_actions.pop()
        assert (
            "/character/xena/with-build-action/"
            "BRING_RESOURCE_ON_BUILD/42/ACTION_ID"
            "?resource_id=BRANCHES" == character_action.link
        )
        assert (
            "Apporter Petit bois pour la construction "
            "(manque 0.00025 mètre cubes soit 25%)" == character_action.name
        )

    def test_unit__get_character_actions__something_on_place_and_have_progress(
        self,
        action: BringResourcesOnBuild,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_mock_build_document: BuildDocument,
    ) -> None:
        kernel = worldmapc_kernel
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        # Add some resources in building
        kernel.server_db_session.add(
            ResourceDocument(
                resource_id="BRANCHES",  # see src/game1/game.toml
                quantity=0.00025,  # 50%, see src/game1/game.toml
                in_built_id=build.id,
            )
        )
        build.ap_spent = 1.0  # 50%, see src/game1/game.toml
        kernel.server_db_session.add(build)
        kernel.server_db_session.commit()

        character_actions = action.get_character_actions(xena, build.id)
        assert character_actions
        assert 1 == len(character_actions)
        character_action = character_actions.pop()
        assert (
            "/character/xena/with-build-action/"
            "BRING_RESOURCE_ON_BUILD/42/ACTION_ID"
            "?resource_id=BRANCHES" == character_action.link
        )
        assert (
            "Apporter Petit bois pour la construction "
            "(manque 0.00025 mètre cubes soit 25%)" == character_action.name
        )

    def test_unit__get_character_actions__all_on_place_and_have_progress(
        self,
        action: BringResourcesOnBuild,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_mock_build_document: BuildDocument,
    ) -> None:
        kernel = worldmapc_kernel
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        # Add some resources in building
        kernel.server_db_session.add(
            ResourceDocument(
                resource_id="BRANCHES",  # see src/game1/game.toml
                quantity=0.0005,  # 50%, see src/game1/game.toml
                in_built_id=build.id,
            )
        )
        build.ap_spent = 1.0  # 50%, see src/game1/game.toml
        kernel.server_db_session.add(build)
        kernel.server_db_session.commit()

        character_actions = action.get_character_actions(xena, build.id)
        assert not character_actions

    def test_unit__perform__nothing_on_place_and_no_progress(
        self,
        action: BringResourcesOnBuild,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_mock_build_document: BuildDocument,
    ) -> None:
        kernel = worldmapc_kernel
        build = worldmapc_mock_build_document
        xena = worldmapc_xena_model

        kernel.resource_lib.add_resource_to(
            character_id=xena.id, resource_id="BRANCHES", quantity=0.00025
        )

        assert not kernel.resource_lib.get_stored_in_build(build.id)
        action.perform(
            xena,
            build_id=build.id,
            input_=BringResourceModel(
                resource_id="BRANCHES", quantity=0.00025  # see src/game1/game.toml
            ),
        )
        resources = kernel.resource_lib.get_stored_in_build(build.id)
        assert resources
        resource = resources.pop()
        assert resource.id == "BRANCHES"
        assert 0.00025 == resource.quantity
