import typing
import pytest
from rolling.action.base import ActionDescriptionModel

from rolling.kernel import Kernel
from rolling.action.mix import MixResourceModel, MixResourcesAction
from rolling.rolling_types import ActionType
from rolling.model.character import CharacterModel
from rolling.util import Quantity
from rolling.exception import WrongInputError
from tests.utils import find_part


@pytest.fixture
def mix_action(worldmapc_kernel: Kernel) -> MixResourcesAction:
    return MixResourcesAction(
        worldmapc_kernel,
        description=ActionDescriptionModel(
            id="ACTION_ID",
            action_type=ActionType.MIX_RESOURCES,
            base_cost=0.0,
            properties={},
        ),
    )


class TestMixAction:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mix_id,stocks,expected",
        [
            # not enough
            ("MIX1", {"FRESH_WATER": 0.01, "SOIL": 0.75}, 0.0),
            # enough for 1
            ("MIX1", {"FRESH_WATER": 0.25, "SOIL": 0.75}, 1.0),
            # enough for 2
            ("MIX1", {"FRESH_WATER": 0.50, "SOIL": 1.5}, 2.0),
            # enough for 2 (much more water than soil)
            ("MIX1", {"FRESH_WATER": 1.0, "SOIL": 1.5}, 2.0),
            # not enough
            ("MIX2", {"FRESH_WATER": 0.0, "STONE": 1.0}, 0.0),
            # enough for 1
            ("MIX2", {"FRESH_WATER": 1.0, "STONE": 1.0}, 1.0),
            # enough for 2
            ("MIX2", {"FRESH_WATER": 2.0, "STONE": 2.0}, 2.0),
            # enough for 1 (much more water than stone)
            ("MIX2", {"FRESH_WATER": 10.0, "STONE": 1.0}, 1.0),
            # enough for 2 (not enough AP)
            ("MIX2", {"FRESH_WATER": 100.0, "STONE": 100.0}, 2.0),
            # Test display as grams
            ("MIX3", {"RES1": 1.0, "RES2": 1.0}, 1.0),
            # Test display as kilo grams
            ("MIX3", {"RES1": 2500.0, "RES2": 2500.0}, 2.5),
        ],
    )
    async def test_production_capacities(
        self,
        worldmapc_kernel: Kernel,
        mix_action: MixResourcesAction,
        worldmapc_xena_model: CharacterModel,
        mix_id: str,
        stocks: typing.Dict[str, float],
        expected: float,
    ) -> None:
        # Given
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        action = mix_action

        for resource_id, quantity in stocks.items():
            kernel.resource_lib.add_resource_to(
                resource_id=resource_id,
                quantity=quantity,
                character_id=xena.id,
            )

        # When
        description = await action.perform(
            xena,
            resource_id=resource_id,
            input_=MixResourceModel(resource_mix_id=mix_id),
        )

        # Then
        name_input = find_part(description.items, name="quantity")
        assert name_input is not None
        assert name_input.min_value == 0.0
        assert name_input.max_value == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mix_id,stocks_before,produce,stocks_after,cost",
        [
            # Success MIX1
            (
                "MIX1",
                {"FRESH_WATER": 0.25, "SOIL": 0.75},
                "1.0l",
                {"FRESH_WATER": 0.0, "SOIL": 0.0, "WET_SOIL": 1.0},
                0.01 * 1.0,
            ),
            # Success MIX2
            (
                "MIX2",
                {"FRESH_WATER": 1.0, "STONE": 1.0},
                "1.0l",
                {"FRESH_WATER": 0.0, "STONE": 0.0, "WET_SOIL": 1.0},
                10.0 * 1.0,
            ),
            # Not enough AP (MIX2 cost is 10.0)
            (
                "MIX2",
                {"FRESH_WATER": 10.0, "STONE": 10.0},
                "10.0l",
                {"FRESH_WATER": 10.0, "STONE": 10.0, "WET_SOIL": 0.0},
                10.0 * 10.0,
            ),
            # Not enough resource (0.0)
            (
                "MIX1",
                {"FRESH_WATER": 0.10, "SOIL": 0.75},
                "1.0l",
                None,
                0.01 * 1.0,
            ),
            # Not enough resource (no row)
            (
                "MIX1",
                {"SOIL": 0.75},
                "1.0l",
                None,
                0.01 * 1.0,
            ),
            # Test Kg conversions
            (
                "MIX3",
                {"RES1": 1000.0, "RES2": 1000.0},
                "1.0kg",
                {"RES1": 0.0, "RES2": 0.0, "RES3": 1000.0},
                0.001 * 1000.0,
            ),
            (
                "MIX3",
                {"RES1": 1000.0, "RES2": 1000.0},
                "1000.0g",
                {"RES1": 0.0, "RES2": 0.0, "RES3": 1000.0},
                0.001 * 1000.0,
            ),
        ],
    )
    async def test_produce(
        self,
        worldmapc_kernel: Kernel,
        mix_action: MixResourcesAction,
        worldmapc_xena_model: CharacterModel,
        mix_id: str,
        stocks_before: typing.Dict[str, float],
        produce: float,
        stocks_after: typing.Optional[typing.Dict[str, float]],
        cost: float,
    ) -> None:
        # Given
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        action = mix_action

        for resource_id, quantity in stocks_before.items():
            kernel.resource_lib.add_resource_to(
                resource_id=resource_id,
                quantity=quantity,
                character_id=xena.id,
            )

        # When
        input_ = MixResourceModel(
            resource_mix_id=mix_id,
            quantity=Quantity(produce),
        )
        if stocks_after is None:
            with pytest.raises(WrongInputError):
                await action.check_request_is_possible(
                    xena,
                    resource_id=resource_id,
                    input_=input_,
                )
        else:
            await action.check_request_is_possible(
                xena,
                resource_id=resource_id,
                input_=input_,
            )
        await action.perform(
            xena,
            resource_id=resource_id,
            input_=input_,
        )
        assert action.get_cost(xena, resource_id=resource_id, input_=input_) == cost

        # Then
        if stocks_after is not None:
            for resource_id, quantity in stocks_after.items():
                character_quantity = kernel.resource_lib.get_one_carried_by(
                    character_id=xena.id,
                    resource_id=resource_id,
                    empty_object_if_not=True,
                ).quantity
                assert (
                    character_quantity == quantity
                ), f"{resource_id} resources must be equal"
