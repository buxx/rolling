# coding: utf-8
import pytest
from unittest import mock

from rolling.action.base import ActionDescriptionModel
from rolling.action.build import BringResourceModel
from rolling.action.build import BringResourcesOnBuild
from rolling.action.build_deposit import DepositToBuildAction
from rolling.action.build_deposit import DepositToModel
from rolling.action.build_take import TakeFromBuildAction
from rolling.action.build_take import TakeFromModel
from rolling.exception import ImpossibleAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
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
def build4(
    worldmapc_kernel: Kernel,
) -> BuildDocument:
    kernel = worldmapc_kernel
    return kernel.build_lib.place_build(
        world_col_i=0,
        world_row_i=0,
        zone_col_i=0,
        zone_row_i=0,
        build_id="TEST_BUILD_4",
        under_construction=True,
    )


@pytest.fixture
def build5(
    worldmapc_kernel: Kernel,
) -> BuildDocument:
    kernel = worldmapc_kernel
    return kernel.build_lib.place_build(
        world_col_i=0,
        world_row_i=0,
        zone_col_i=0,
        zone_row_i=0,
        build_id="TEST_BUILD_5",
        under_construction=True,
    )


@pytest.fixture
def build6(
    worldmapc_kernel: Kernel,
) -> BuildDocument:
    kernel = worldmapc_kernel
    return kernel.build_lib.place_build(
        world_col_i=0,
        world_row_i=0,
        zone_col_i=0,
        zone_row_i=0,
        build_id="TEST_BUILD_6",
        under_construction=True,
    )


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


@pytest.fixture
def deposit_action(worldmapc_kernel: Kernel) -> DepositToBuildAction:
    return DepositToBuildAction(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="DEPOSIT_ON_BUILD",
            action_type=ActionType.DEPOSIT_ON_BUILD,
            base_cost=1.0,
            properties={},
        ),
    )


@pytest.fixture
def take_action(worldmapc_kernel: Kernel) -> TakeFromBuildAction:
    return TakeFromBuildAction(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="TAKE_FROM_BUILD",
            action_type=ActionType.TAKE_FROM_BUILD,
            base_cost=1.0,
            properties={},
        ),
    )


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
            f"BRING_RESOURCE_ON_BUILD/{build.id}/ACTION_ID"
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
            f"BRING_RESOURCE_ON_BUILD/{build.id}/ACTION_ID"
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
            f"BRING_RESOURCE_ON_BUILD/{build.id}/ACTION_ID"
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

    @pytest.mark.usefixtures("worldmapc_xena_wood")
    def test_deposit_resource_on_build_allowing_it_because_allow_all(
        self,
        worldmapc_kernel: Kernel,
        build5: BuildDocument,
        worldmapc_xena_model: CharacterModel,
        deposit_action: DepositToBuildAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        # Given
        assert not kernel.resource_lib.get_stored_in_build(build5.id)

        # When
        deposit_action.perform(
            character=xena,
            build_id=build5.id,
            input_=DepositToModel(
                deposit_resource_id="WOOD",
                deposit_resource_quantity=0.2,
            ),
        )

        # Then
        assert kernel.resource_lib.get_stored_in_build(build5.id)
        assert 1 == len(kernel.resource_lib.get_stored_in_build(build5.id))
        assert kernel.resource_lib.get_stored_in_build(build5.id)[0].id == "WOOD"

    @pytest.mark.usefixtures("worldmapc_xena_wood")
    @pytest.mark.usefixtures("worldmapc_xena_stone")
    def test_deposit_resource_on_build_allowing_it_because_allow_limit(
        self,
        worldmapc_kernel: Kernel,
        build6: BuildDocument,
        worldmapc_xena_model: CharacterModel,
        deposit_action: DepositToBuildAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        # Given
        assert not kernel.resource_lib.get_stored_in_build(build6.id)

        # When
        with pytest.raises(ImpossibleAction):
            deposit_action.perform(
                character=xena,
                build_id=build6.id,
                input_=DepositToModel(
                    deposit_resource_id="WOOD",
                    deposit_resource_quantity=0.2,
                ),
            )
        deposit_action.perform(
            character=xena,
            build_id=build6.id,
            input_=DepositToModel(
                deposit_resource_id="STONE",
                deposit_resource_quantity=2,
            ),
        )

        # Then
        assert kernel.resource_lib.get_stored_in_build(build6.id)
        assert 1 == len(kernel.resource_lib.get_stored_in_build(build6.id))
        assert kernel.resource_lib.get_stored_in_build(build6.id)[0].id == "STONE"

    @pytest.mark.usefixtures("worldmapc_xena_stone")
    def test_deposit_resource_on_build_refusing_it_because_not_allow(
        self,
        worldmapc_kernel: Kernel,
        build4: BuildDocument,
        worldmapc_xena_model: CharacterModel,
        deposit_action: DepositToBuildAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        # Given
        assert not kernel.resource_lib.get_stored_in_build(build4.id)

        # When
        with pytest.raises(ImpossibleAction):
            deposit_action.perform(
                character=xena,
                build_id=build4.id,
                input_=DepositToModel(
                    deposit_resource_id="STONE",
                    deposit_resource_quantity=2,
                ),
            )

        # Then
        assert not kernel.resource_lib.get_stored_in_build(build4.id)

    def test_deposit_stuff_on_build_allowing_it_because_allow_all(
        self,
        worldmapc_kernel: Kernel,
        build5: BuildDocument,
        worldmapc_xena_model: CharacterModel,
        deposit_action: DepositToBuildAction,
        worldmapc_xena_haxe_weapon: StuffModel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        haxe = worldmapc_xena_haxe_weapon

        # Given
        assert not kernel.resource_lib.get_stored_in_build(build5.id)

        # When
        deposit_action.perform(
            character=xena,
            build_id=build5.id,
            input_=DepositToModel(
                deposit_stuff_id=haxe.id,
                deposit_resource_quantity=1,
            ),
        )

        # Then
        assert kernel.stuff_lib.get_from_build(build5.id)
        assert 1 == len(kernel.stuff_lib.get_from_build(build5.id))
        assert kernel.stuff_lib.get_from_build(build5.id)[0].id == haxe.id

    def test_deposit_stuff_on_build_refusing_it_because_allow_limit(
        self,
        worldmapc_kernel: Kernel,
        build6: BuildDocument,
        worldmapc_xena_model: CharacterModel,
        deposit_action: DepositToBuildAction,
        worldmapc_xena_haxe_weapon: StuffModel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        haxe = worldmapc_xena_haxe_weapon

        # Given
        assert not kernel.resource_lib.get_stored_in_build(build6.id)

        # When
        with pytest.raises(ImpossibleAction):
            deposit_action.perform(
                character=xena,
                build_id=build6.id,
                input_=DepositToModel(
                    deposit_stuff_id=haxe.id,
                    deposit_stuff_quantity=1,
                ),
            )

        # Then
        assert not kernel.stuff_lib.get_from_build(build6.id)

    def test_deposit_stuff_on_build_refusing_it_because_not_allow(
        self,
        worldmapc_kernel: Kernel,
        build4: BuildDocument,
        worldmapc_xena_model: CharacterModel,
        deposit_action: DepositToBuildAction,
        worldmapc_xena_haxe_weapon: StuffModel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        haxe = worldmapc_xena_haxe_weapon

        # Given
        assert not kernel.resource_lib.get_stored_in_build(build4.id)

        # When
        with pytest.raises(ImpossibleAction):
            deposit_action.perform(
                character=xena,
                build_id=build4.id,
                input_=DepositToModel(
                    deposit_stuff_id=haxe.id,
                    deposit_stuff_quantity=1,
                ),
            )

        # Then
        assert not kernel.stuff_lib.get_from_build(build4.id)

    @pytest.mark.usefixtures("worldmapc_xena_wood")
    def test_take_resource_from_build(
        self,
        worldmapc_kernel: Kernel,
        build5: BuildDocument,
        worldmapc_xena_model: CharacterModel,
        deposit_action: DepositToBuildAction,
        take_action: TakeFromBuildAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        # Given
        deposit_action.perform(
            character=xena,
            build_id=build5.id,
            input_=DepositToModel(
                deposit_resource_id="WOOD",
                deposit_resource_quantity=0.2,
            ),
        )
        assert kernel.resource_lib.get_stored_in_build(build5.id)

        # When
        take_action.perform(
            character=xena,
            build_id=build5.id,
            input_=TakeFromModel(
                take_resource_id="WOOD",
                take_resource_quantity=0.2,
            ),
        )

        # Then
        assert not kernel.resource_lib.get_stored_in_build(build5.id)

    def test_take_stuff_from_build(
        self,
        worldmapc_kernel: Kernel,
        build5: BuildDocument,
        worldmapc_xena_model: CharacterModel,
        deposit_action: DepositToBuildAction,
        take_action: TakeFromBuildAction,
        worldmapc_xena_haxe_weapon: StuffModel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        haxe = worldmapc_xena_haxe_weapon

        # Given
        deposit_action.perform(
            character=xena,
            build_id=build5.id,
            input_=DepositToModel(
                deposit_stuff_id=haxe.id,
                deposit_stuff_quantity=1,
            ),
        )
        assert kernel.stuff_lib.get_from_build(build5.id)

        # When
        take_action.perform(
            character=xena,
            build_id=build5.id,
            input_=TakeFromModel(
                take_stuff_id=haxe.id,
                take_stuff_quantity=1,
            ),
        )

        # Then
        assert not kernel.stuff_lib.get_from_build(build5.id)
