# coding: utf-8
import typing

from rolling.exception import RollingError
from rolling.map.source import ZoneMap
from rolling.map.type.base import MapTileType
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.stuff import StuffModel
from rolling.model.world import World
from rolling.model.zone import ZoneMapTileProduction
from rolling.model.zone import ZoneProperties
from rolling.model.zone import ZoneTileProperties
from rolling.util import get_on_and_around_coordinates, square_walker

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.stuff import ZoneGenerationStuff


class ZoneState:
    def __init__(
        self,
        kernel: "Kernel",
        world_row_i: int,
        world_col_i: int,
        properties: ZoneProperties,
        zone_map: ZoneMap,
    ) -> None:
        self._kernel = kernel
        self._world_row_i = world_row_i
        self._world_col_i = world_col_i
        self._properties = properties
        self._zone_map = zone_map

    @property
    def zone_map(self) -> ZoneMap:
        return self._zone_map

    def is_there_stuff(self, stuff_id: str) -> bool:
        # TODO BS 2019-09-26: Code real state of stuff/resources (with regeneration, etc)
        return stuff_id in self._properties.stuff_ids

    def is_there_resource(
        self,
        resource_id: str,
        check_from_absolute: bool = True,
        check_from_tiles: bool = True,
    ) -> bool:
        assert check_from_absolute or check_from_tiles

        # TODO BS 2019-09-26: Code real state of stuff/resources (with regeneration, etc)
        if check_from_absolute:
            return resource_id in self._properties.resource_ids

        if check_from_tiles:
            for (
                zone_tile_type
            ) in self._zone_map.source.geography.tile_type_positions.keys():
                tiles_properties = (
                    self._kernel.game.world_manager.world.tiles_properties
                )
                try:
                    zone_tile_properties: ZoneTileProperties = tiles_properties[
                        zone_tile_type
                    ]
                except KeyError:
                    continue

                for tile_produce in zone_tile_properties.produce:
                    if resource_id == tile_produce.resource.id:
                        return True
            return False

        raise Exception("should not be here")

    def reduce_resource(
        self, resource_id: str, quantity: float, commit: bool = True
    ) -> None:
        pass  # TODO: code resource stock

    def reduce_resource_from_tile(
        self,
        resource_id: str,
        quantity: float,
        tile_row_i: int,
        tile_col_i: int,
        commit: bool = True,
    ) -> None:
        pass  # TODO: code resource stock

    def reduce_stuff(self, stuff_id: str, quantity: float, commit: bool = True) -> None:
        pass  # TODO: code resource stock


class WorldManager:
    def __init__(self, kernel: "Kernel", world: World) -> None:
        self._kernel = kernel
        self._world = world

    @property
    def world(self) -> World:
        return self._world

    def get_zone_properties_by_coordinates(
        self, world_row_i: int, world_col_i: int
    ) -> ZoneProperties:
        zone_type = self._kernel.world_map_source.geography.rows[world_row_i][
            world_col_i
        ]
        zone_type = typing.cast(ZoneMapTileType, zone_type)
        return self.get_zone_properties(zone_type)

    def get_zone_properties(self, zone_type: ZoneMapTileType) -> ZoneProperties:
        for zone_properties in self.world.zones_properties:
            if zone_properties.zone_type == zone_type:
                return zone_properties
        raise RollingError(f"No zone properties for zone {zone_type}")

    def get_generation_stuff_by_zone_type(
        self,
    ) -> typing.Dict[typing.Type[MapTileType], typing.List["ZoneGenerationStuff"]]:
        generation_stuff_by_zone_type = {}
        for zone_property in self.world.zones_properties:
            generation_stuff_by_zone_type[
                zone_property.zone_type
            ] = zone_property.generation_info.stuffs
        return generation_stuff_by_zone_type

    def get_zone_properties_by_zone_type(
        self,
    ) -> typing.Dict[typing.Type[MapTileType], ZoneProperties]:
        return dict(((zp.zone_type, zp) for zp in self._world.zones_properties))

    def get_resources_at(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        material_type: typing.Optional[str] = None,
    ) -> typing.List[ZoneMapTileProduction]:
        zone_map = self._kernel.tile_maps_by_position[(world_row_i, world_col_i)]

        try:
            zone_tile_type = typing.cast(
                typing.Type[ZoneMapTileType],
                zone_map.source.geography.rows[zone_row_i][zone_col_i],
            )
        except IndexError:
            return []

        try:
            productions = self._world.tiles_properties[zone_tile_type].produce
        except KeyError:
            return []

        if material_type is not None:
            return [
                production
                for production in productions
                if production.resource.material_type == material_type
            ]

        return productions

    def get_resource_on_or_around(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        material_type: typing.Optional[str] = None,
    ) -> typing.List[ZoneMapTileProduction]:
        inspect_zone_positions = get_on_and_around_coordinates(zone_row_i, zone_col_i)
        productions: typing.List[ZoneMapTileProduction] = []

        for zone_row_i, zone_col_i in inspect_zone_positions:
            productions.extend(
                self.get_resources_at(
                    world_row_i=world_row_i,
                    world_col_i=world_col_i,
                    zone_row_i=zone_row_i,
                    zone_col_i=zone_col_i,
                    material_type=material_type,
                )
            )

        return list(set(productions))

    def get_zone_state(self, world_row_i: int, world_col_i: int) -> ZoneState:
        zone_type = self._kernel.world_map_source.geography.rows[world_row_i][
            world_col_i
        ]
        zone_type = typing.cast(ZoneMapTileType, zone_type)
        zone_properties = self.get_zone_properties(zone_type)
        zone_map = self._kernel.tile_maps_by_position[(world_row_i, world_col_i)]
        return ZoneState(
            self._kernel,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            properties=zone_properties,
            zone_map=zone_map,
        )

    def find_available_place_where_drop(
        self,
        world_row_i: int,
        world_col_i: int,
        start_from_zone_row_i: int,
        start_from_zone_col_i: int,
        allow_fallback_on_start_coordinates: bool,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
        stuff_id: typing.Optional[int] = None,
        strict_place: bool = True,
    ) -> typing.List[typing.Tuple[typing.Tuple[int, int], typing.Optional[float]]]:
        assert (resource_id is not None and resource_quantity is not None) or stuff_id
        stuff: typing.Optional[StuffModel] = None
        if stuff_id is not None:
            stuff = self._kernel.stuff_lib.get_stuff_doc(stuff_id)

        if stuff is not None:
            clutter_ref = 1.0
            clutter_to_place = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    stuff.stuff_id
                ).clutter
            )
            clutter_in_one_tile = True
        else:
            clutter_ref = self._kernel.game.config.resources[resource_id].clutter
            clutter_to_place = clutter_ref * resource_quantity
            clutter_in_one_tile = False

        # FIXME BS NOW: get_traversable_coordinates return an enormous list Oo
        zone_traversable_tiles = self._kernel.get_traversable_coordinates(
            world_row_i, world_col_i
        )
        available_places: typing.List[typing.Tuple[typing.Tuple[int, int], float]] = []

        walker = square_walker(start_from_zone_row_i, start_from_zone_col_i)
        max_counter = 0
        while clutter_to_place:
            max_counter += 1

            # Protection against infinite loop
            if max_counter > 200:
                return available_places

            # Pick up on tile
            test_tile_row_i, test_tile_col_i = next(walker)

            # Accept this tile only if can be walked
            if (test_tile_row_i, test_tile_col_i) not in zone_traversable_tiles:
                continue

            # Compute available space on this tile
            tile_used_clutter = 0.0

            continue_ = False
            for tile_stuff in self._kernel.stuff_lib.get_zone_stuffs(
                world_row_i=world_row_i,
                world_col_i=world_col_i,
                zone_row_i=test_tile_row_i,
                zone_col_i=test_tile_col_i,
            ):
                if strict_place:
                    # In strict mode a stuff take all the place
                    continue_ = True
                    continue

                stuff_properties = (
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                        tile_stuff.stuff_id
                    )
                )
                tile_used_clutter += stuff_properties.clutter

            if continue_:
                continue

            for carried_resource in self._kernel.resource_lib.get_ground_resource(
                world_row_i=world_row_i,
                world_col_i=world_col_i,
                zone_row_i=test_tile_row_i,
                zone_col_i=test_tile_col_i,
            ):
                if strict_place and stuff is not None:
                    # In strict mode, a resource here exclude this tile for a stuff deposit
                    continue_ = True
                    continue

                if (
                    strict_place
                    and resource_id is not None
                    and carried_resource.id != resource_id
                ):
                    # In strict mode, a different resource here exclude this tile for a resource deposit
                    continue_ = True
                    continue

                resource_description = self._kernel.game.config.resources[
                    carried_resource.id
                ]
                tile_used_clutter += (
                    resource_description.clutter * carried_resource.quantity
                )

            if continue_:
                continue

            # Continue with this tile only if there is enough clutter here
            tile_left_clutter = max(
                self._kernel.game.config.tile_clutter_capacity - tile_used_clutter, 0.0
            )
            if not tile_left_clutter:
                continue
            if clutter_in_one_tile and tile_left_clutter < clutter_to_place:
                continue

            # there is space here for place
            if clutter_in_one_tile:
                clutter_to_place = 0
                available_places.append(((test_tile_row_i, test_tile_col_i), 1.0))
            else:
                if clutter_to_place > tile_left_clutter:
                    place_clutter = tile_left_clutter
                else:
                    place_clutter = clutter_to_place

                clutter_to_place -= place_clutter
                available_places.append(
                    ((test_tile_row_i, test_tile_col_i), place_clutter / clutter_ref)
                )

        return available_places
