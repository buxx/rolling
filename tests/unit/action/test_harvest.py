import pytest
import shutil

from rolling.action.base import ActionDescriptionModel
from rolling.action.harvest import HarvestAction
from rolling.action.harvest import HarvestModel
from rolling.kernel import Kernel
from rolling.map.type.zone import DeadTree
from rolling.map.type.zone import Dirt
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from rolling.exception import ImpossibleAction
from tests.utils import place_build_on_character_position


@pytest.fixture
def harvest_action(worldmapc_kernel: Kernel) -> HarvestAction:
    return HarvestAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            action_type=ActionType.HARVEST,
            base_cost=0.0,
            id="HARVEST",
            properties={},
        ),
    )


@pytest.mark.usefixtures("disable_tracim")
class TestHarvestAction:
    @pytest.mark.asyncio
    async def test_collect_cereals_from_field_with_one_ready_ploughed_land(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        harvest_action: HarvestAction,
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        action = harvest_action
        original_xena_ap = xena.action_points

        # ready to harvest
        ploughed_land = place_build_on_character_position(kernel, xena, "PLOUGHED_LAND")
        ploughed_land.seeded_with = "CEREAL"
        ploughed_land.grow_progress = kernel.game.config.grow_progress_4
        kernel.server_db_session.add(ploughed_land)
        kernel.server_db_session.commit()

        # When/Then
        action.check_is_possible(xena)
        await action.check_request_is_possible(
            xena,
            input_=HarvestModel(
                resource_id="CEREAL",
                ap=6.0,
            ),
        )
        await action.perform(
            xena,
            input_=HarvestModel(
                resource_id="CEREAL",
                ap=6.0,
            ),
        )
        assert (
            str(
                kernel.resource_lib.get_one_carried_by(
                    character_id=xena.id,
                    resource_id="CEREAL",
                    empty_object_if_not=True,
                ).quantity
            )
            == "2.0"
        )
        ploughed_land = kernel.build_lib.get_build_doc(ploughed_land.id)
        assert ploughed_land.seeded_with is None
        assert ploughed_land.grow_progress == 0
        xena_doc = kernel.character_lib.get_document(xena.id)
        # see tests/src/game1/game.toml
        assert xena_doc.action_points == original_xena_ap - 1.0

    @pytest.mark.asyncio
    async def test_collect_cereals_from_fields_with_all_ready_ploughed_lands(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        harvest_action: HarvestAction,
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        action = harvest_action
        original_xena_ap = xena.action_points

        # ready to harvest
        ploughed_land = place_build_on_character_position(kernel, xena, "PLOUGHED_LAND")
        ploughed_land.seeded_with = "CEREAL"
        ploughed_land.grow_progress = kernel.game.config.grow_progress_4
        kernel.server_db_session.add(ploughed_land)
        kernel.server_db_session.commit()

        ploughed_land2 = place_build_on_character_position(
            kernel, xena, "PLOUGHED_LAND", zone_row_modifier=1
        )
        ploughed_land2.seeded_with = "CEREAL"
        ploughed_land2.grow_progress = kernel.game.config.grow_progress_4
        kernel.server_db_session.add(ploughed_land2)
        kernel.server_db_session.commit()

        # When/Then
        action.check_is_possible(xena)
        await action.check_request_is_possible(
            xena,
            input_=HarvestModel(
                resource_id="CEREAL",
                ap=6.0,
            ),
        )
        await action.perform(
            xena,
            input_=HarvestModel(
                resource_id="CEREAL",
                ap=6.0,
            ),
        )
        assert (
            str(
                kernel.resource_lib.get_one_carried_by(
                    character_id=xena.id,
                    resource_id="CEREAL",
                    empty_object_if_not=True,
                ).quantity
            )
            == "4.0"
        )
        ploughed_land = kernel.build_lib.get_build_doc(ploughed_land.id)
        assert ploughed_land.seeded_with is None
        assert ploughed_land.grow_progress == 0
        ploughed_land2 = kernel.build_lib.get_build_doc(ploughed_land2.id)
        assert ploughed_land2.seeded_with is None
        assert ploughed_land2.grow_progress == 0
        xena_doc = kernel.character_lib.get_document(xena.id)
        # see tests/src/game1/game.toml
        assert xena_doc.action_points == original_xena_ap - 2.0

    @pytest.mark.asyncio
    async def test_collect_cereals_from_fields_with_some_ready_ploughed_lands(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        harvest_action: HarvestAction,
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        action = harvest_action
        original_xena_ap = xena.action_points

        # ready to harvest
        ploughed_land = place_build_on_character_position(kernel, xena, "PLOUGHED_LAND")
        ploughed_land.seeded_with = "CEREAL"
        ploughed_land.grow_progress = kernel.game.config.grow_progress_4
        kernel.server_db_session.add(ploughed_land)
        kernel.server_db_session.commit()

        ploughed_land2 = place_build_on_character_position(
            kernel, xena, "PLOUGHED_LAND", zone_row_modifier=1
        )
        ploughed_land2.seeded_with = "CEREAL"
        ploughed_land2.grow_progress = kernel.game.config.grow_progress_3
        kernel.server_db_session.add(ploughed_land2)
        kernel.server_db_session.commit()

        # When/Then
        action.check_is_possible(xena)
        await action.check_request_is_possible(
            xena,
            input_=HarvestModel(
                resource_id="CEREAL",
                ap=6.0,
            ),
        )
        await action.perform(
            xena,
            input_=HarvestModel(
                resource_id="CEREAL",
                ap=6.0,
            ),
        )
        assert (
            str(
                kernel.resource_lib.get_one_carried_by(
                    character_id=xena.id,
                    resource_id="CEREAL",
                    empty_object_if_not=True,
                ).quantity
            )
            == "2.0"
        )
        ploughed_land = kernel.build_lib.get_build_doc(ploughed_land.id)
        assert ploughed_land.seeded_with is None
        assert ploughed_land.grow_progress == 0
        ploughed_land2 = kernel.build_lib.get_build_doc(ploughed_land2.id)
        assert ploughed_land2.seeded_with == "CEREAL"
        assert ploughed_land2.grow_progress == kernel.game.config.grow_progress_3
        xena_doc = kernel.character_lib.get_document(xena.id)
        # see tests/src/game1/game.toml
        assert xena_doc.action_points == original_xena_ap - 1.0

    @pytest.mark.asyncio
    async def test_collect_cereals_from_fields_with_no_ready_ploughed_lands(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        harvest_action: HarvestAction,
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        action = harvest_action
        original_xena_ap = xena.action_points

        # ready to harvest
        ploughed_land = place_build_on_character_position(kernel, xena, "PLOUGHED_LAND")
        ploughed_land.seeded_with = "CEREAL"
        ploughed_land.grow_progress = kernel.game.config.grow_progress_3
        kernel.server_db_session.add(ploughed_land)
        kernel.server_db_session.commit()

        ploughed_land2 = place_build_on_character_position(
            kernel, xena, "PLOUGHED_LAND", zone_row_modifier=1
        )
        ploughed_land2.seeded_with = "CEREAL"
        ploughed_land2.grow_progress = kernel.game.config.grow_progress_3
        kernel.server_db_session.add(ploughed_land2)
        kernel.server_db_session.commit()

        # When/Then
        action.check_is_possible(xena)
        with pytest.raises(ImpossibleAction):
            await action.check_request_is_possible(
                xena,
                input_=HarvestModel(
                    resource_id="CEREAL",
                    ap=6.0,
                ),
            )
