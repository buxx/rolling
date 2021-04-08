# coding: utf-8
import pytest
import typing

from rolling.game.world import WorldManager
from rolling.kernel import Kernel


# NOTE: test are based on tile_clutter_capacity config
class TestWorldManager:
    def _find_available_place_where_drop(
        self,
        world_manager: WorldManager,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
        stuff_id: typing.Optional[str] = None,
    ) -> typing.List[typing.Tuple[typing.Tuple[int, int], typing.Optional[float]]]:
        return world_manager.find_available_place_where_drop(
            resource_id=resource_id,
            resource_quantity=resource_quantity,
            stuff_id=stuff_id,
            world_row_i=1,
            world_col_i=1,
            start_from_zone_row_i=69,
            start_from_zone_col_i=40,
            allow_fallback_on_start_coordinates=False,
        )

    @pytest.mark.parametrize(
        "resource_id,quantity,expected",
        [
            ("WOOD", 0.005, [((69, 40), 0.005)]),
            ("WOOD", 0.05, [((69, 40), 0.02), ((69, 41), 0.02), ((68, 42), 0.01)]),
        ],
    )
    def test_find_available_place_where_drop_when_place_resource_on_full_free_space(
        self,
        worldmapc_kernel: Kernel,
        resource_id: str,
        quantity: float,
        expected: typing.List[typing.Tuple[typing.Tuple[int, int], typing.Optional[float]]],
    ) -> None:
        # Given
        kernel = worldmapc_kernel

        # When
        places = self._find_available_place_where_drop(
            kernel.game.world_manager, resource_id=resource_id, resource_quantity=quantity
        )

        # Then
        assert places == expected

    @pytest.mark.parametrize(
        "resource_id,quantity,expected",
        [
            ("WOOD", 0.005, [((69, 40), 0.002), ((69, 41), 0.003)]),
            (
                "WOOD",
                0.05,
                [((69, 40), 0.002), ((69, 41), 0.02), ((68, 42), 0.02), ((70, 41), 0.008)],
            ),
        ],
    )
    def test_find_available_place_where_drop_when_place_resource_on_occupied_space(
        self,
        worldmapc_kernel: Kernel,
        resource_id: str,
        quantity: float,
        expected: typing.List[typing.Tuple[typing.Tuple[int, int], typing.Optional[float]]],
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        kernel.resource_lib.add_resource_to(
            resource_id="STONE",
            quantity=9,
            ground=True,
            world_row_i=1,
            world_col_i=1,
            zone_row_i=69,
            zone_col_i=40,
        )

        # When
        places = self._find_available_place_where_drop(
            kernel.game.world_manager, resource_id=resource_id, resource_quantity=quantity
        )

        # Then
        assert places == expected

    @pytest.mark.parametrize(
        "resource_id,quantity,expected",
        [
            ("WOOD", 0.005, [((69, 40), 0.005)]),
            ("WOOD", 0.05, [((69, 40), 0.02), ((68, 39), 0.02), ((70, 41), 0.01)]),
        ],
    )
    def test_find_available_place_where_drop_when_place_resource_on_walled_space(
        self,
        worldmapc_kernel: Kernel,
        resource_id: str,
        quantity: float,
        expected: typing.List[typing.Tuple[typing.Tuple[int, int], typing.Optional[float]]],
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=69,
            zone_col_i=41,
            build_id="STONE_WALL",
            under_construction=False,
        )

        # When
        places = self._find_available_place_where_drop(
            kernel.game.world_manager, resource_id=resource_id, resource_quantity=quantity
        )

        # Then
        assert places == expected

    def test_find_available_place_where_drop_when_place_stuff_on_full_free_space(
        self, worldmapc_kernel: Kernel
    ) -> None:
        # Given
        kernel = worldmapc_kernel

        # When
        places = self._find_available_place_where_drop(
            kernel.game.world_manager, stuff_id="STONE_HAXE"
        )

        # Then
        assert places == [((69, 40), 1.0)]

    def test_find_available_place_where_drop_when_place_stuff_on_occupied_space(
        self, worldmapc_kernel: Kernel
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        kernel.resource_lib.add_resource_to(
            resource_id="STONE",
            quantity=9,
            ground=True,
            world_row_i=1,
            world_col_i=1,
            zone_row_i=69,
            zone_col_i=40,
        )

        # When
        places = self._find_available_place_where_drop(
            kernel.game.world_manager, stuff_id="STONE_HAXE"
        )

        # Then
        assert places == [((69, 40), 1.0)]

    def test_find_available_place_where_drop_when_place_stuff_on_walled_space(
        self, worldmapc_kernel: Kernel
    ) -> None:
        # Given
        kernel = worldmapc_kernel
        kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=69,
            zone_col_i=41,
            build_id="STONE_WALL",
            under_construction=False,
        )

        # When
        places = self._find_available_place_where_drop(
            kernel.game.world_manager, stuff_id="STONE_HAXE"
        )

        # Then
        assert places == [((69, 40), 1.0)]
