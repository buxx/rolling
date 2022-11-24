import pytest

from rolling.action.base import ActionDescriptionModel
from rolling.action.seed import SeedAction
from rolling.action.seed import SeedModel
from rolling.exception import ImpossibleAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.event import ZoneEventType
from rolling.rolling_types import ActionType


@pytest.fixture
def seed_action(worldmapc_kernel: Kernel) -> SeedAction:
    return SeedAction(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="ACTION_ID",
            action_type=ActionType.SEED,
            base_cost=0.0,
            properties={
                "build_id": "PLOUGHED_LAND",
                "resource_id": "CEREAL",
                "consume": 0.1,
            },
        ),
    )


@pytest.mark.usefixtures("disable_tracim")
class TestSeedAction:
    @pytest.mark.asyncio
    async def test_check_request_is_possible_without_coordinates__cant_because_no_resource(
        self,
        worldmapc_kernel: Kernel,
        seed_action: SeedAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        xena = worldmapc_xena_model

        with pytest.raises(ImpossibleAction):
            await seed_action.check_request_is_possible(
                character=xena,
                input_=SeedModel(),
            )

    @pytest.mark.asyncio
    async def test_event_perform_success(
        self,
        worldmapc_kernel: Kernel,
        seed_action: SeedAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=1,
            zone_col_i=1,
            build_id="PLOUGHED_LAND",
            under_construction=False,
        )
        kernel.resource_lib.add_resource_to(
            character_id=xena.id,
            resource_id="CEREAL",
            quantity=0.1,
        )

        # When
        zone_events, sender_events = await seed_action.perform_from_event(
            character=xena,
            input_=SeedModel(
                row_i=1,
                col_i=1,
            ),
        )

        # Then
        assert len(zone_events) == 1
        assert zone_events[0].type == ZoneEventType.NEW_BUILD
        assert len(sender_events) == 1
        assert sender_events[0].type == ZoneEventType.NEW_RESUME_TEXT

    @pytest.mark.asyncio
    async def test_event_perform__not_enough_cereal(
        self,
        worldmapc_kernel: Kernel,
        seed_action: SeedAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=1,
            zone_col_i=1,
            build_id="PLOUGHED_LAND",
            under_construction=False,
        )
        kernel.resource_lib.add_resource_to(
            character_id=xena.id,
            resource_id="CEREAL",
            quantity=0.09,
        )

        # When
        with pytest.raises(ImpossibleAction):
            await seed_action.perform_from_event(
                character=xena,
                input_=SeedModel(
                    row_i=1,
                    col_i=1,
                ),
            )

    @pytest.mark.asyncio
    async def test_event_perform__already_seeded_build(
        self,
        worldmapc_kernel: Kernel,
        seed_action: SeedAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        doc = kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=1,
            zone_col_i=1,
            build_id="PLOUGHED_LAND",
            under_construction=False,
        )
        doc.seeded_with = "CEREAL"
        kernel.server_db_session.add(doc)
        kernel.server_db_session.commit()
        kernel.resource_lib.add_resource_to(
            character_id=xena.id,
            resource_id="CEREAL",
            quantity=0.1,
        )

        # When
        with pytest.raises(ImpossibleAction):
            await seed_action.perform_from_event(
                character=xena,
                input_=SeedModel(
                    row_i=1,
                    col_i=1,
                ),
            )

    @pytest.mark.asyncio
    async def test_event_perform__no_build(
        self,
        worldmapc_kernel: Kernel,
        seed_action: SeedAction,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        kernel.resource_lib.add_resource_to(
            character_id=xena.id,
            resource_id="CEREAL",
            quantity=0.1,
        )

        # When
        with pytest.raises(ImpossibleAction):
            await seed_action.perform_from_event(
                character=xena,
                input_=SeedModel(
                    row_i=1,
                    col_i=1,
                ),
            )
