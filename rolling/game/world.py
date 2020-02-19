# coding: utf-8
import typing

from rolling.exception import RollingError
from rolling.map.type.base import MapTileType
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.extraction import ExtractableDescriptionModel
from rolling.model.world import Resource
from rolling.model.world import World
from rolling.model.zone import ZoneProperties
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.stuff import ZoneGenerationStuff


class ZoneState:
    def __init__(
        self, kernel: "Kernel", world_row_i: int, world_col_i: int, properties: ZoneProperties
    ) -> None:
        self._kernel = kernel
        self._world_row_i = world_row_i
        self._world_col_i = world_col_i
        self._properties = properties

    def is_there_stuff(self, stuff_id: str) -> bool:
        # TODO BS 2019-09-26: Code real state of stuff/resources (with regeneration, etc)
        return stuff_id in self._properties.stuff_ids

    def is_there_resource(self, stuff_id: str) -> bool:
        # TODO BS 2019-09-26: Code real state of stuff/resources (with regeneration, etc)
        return stuff_id in self._properties.resource_ids


class WorldManager:
    def __init__(self, kernel: "Kernel", world: World) -> None:
        self._kernel = kernel
        self._world = world

    @property
    def world(self) -> World:
        return self._world

    def get_zone_properties(self, zone_type: ZoneMapTileType) -> ZoneProperties:
        for zone_properties in self.world.zones_properties:
            if zone_properties.zone_type == zone_type:
                return zone_properties
        raise RollingError(f"No zone properties for zone {zone_type}")

    def get_generation_stuff_by_zone_type(
        self
    ) -> typing.Dict[typing.Type[MapTileType], typing.List["ZoneGenerationStuff"]]:
        generation_stuff_by_zone_type = {}
        for zone_property in self.world.zones_properties:
            generation_stuff_by_zone_type[
                zone_property.zone_type
            ] = zone_property.generation_info.stuffs
        return generation_stuff_by_zone_type

    def get_zone_properties_by_zone_type(
        self
    ) -> typing.Dict[typing.Type[MapTileType], ZoneProperties]:
        return dict(((zp.zone_type, zp) for zp in self._world.zones_properties))

    def get_resources_at(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        material_type: typing.Optional[str] = None,
    ) -> typing.List[Resource]:
        zone_map = self._kernel.tile_maps_by_position[(world_row_i, world_col_i)]
        resources: typing.List[Resource] = []

        try:
            map_tile_type = zone_map.source.geography.rows[zone_row_i][zone_col_i]
        except IndexError:
            # TODO BS 2019-08-27: maybe raise here
            return []

        map_tile_type = typing.cast(typing.Type[ZoneMapTileType], map_tile_type)
        for extractable_resource in self._kernel.game.config.extractions.get(
            map_tile_type.id, ExtractableDescriptionModel(map_tile_type, resources={})
        ).resources.values():
            resource = self._kernel.game.config.resources[extractable_resource.resource_id]
            if material_type is None or resource.material_type == material_type:
                resources.append(
                    Resource(
                        id=resource.id,
                        material_type=resource.material_type,
                        name=resource.name,
                        weight=resource.weight,
                    )
                )

        return list(set(resources))

    def get_resource_on_or_around(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        material_type: typing.Optional[str] = None,
    ) -> typing.List[Resource]:
        # TODO BS 2019-07-02: factory for types
        inspect_zone_positions = get_on_and_around_coordinates(zone_row_i, zone_col_i)
        resources: typing.List[Resource] = []

        for zone_row_i, zone_col_i in inspect_zone_positions:
            resources.extend(
                self.get_resources_at(
                    world_row_i=world_row_i,
                    world_col_i=world_col_i,
                    zone_row_i=zone_row_i,
                    zone_col_i=zone_col_i,
                    material_type=material_type,
                )
            )

        return list(set(resources))

    def get_zone_state(self, world_row_i: int, world_col_i: int) -> ZoneState:
        zone_type = self._kernel.world_map_source.geography.rows[world_row_i][world_col_i]
        zone_type = typing.cast(ZoneMapTileType, zone_type)
        zone_properties = self.get_zone_properties(zone_type)
        return ZoneState(
            self._kernel,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            properties=zone_properties,
        )

    def is_there_stuff_in_zone(self, world_row_i: int, world_col_i: int, stuff_id: str) -> bool:
        zone_state = self.get_zone_state(world_row_i, world_col_i)
        return zone_state.is_there_stuff(stuff_id)

    def is_there_resource_in_zone(
        self, world_row_i: int, world_col_i: int, resource_id: str
    ) -> bool:
        zone_state = self.get_zone_state(world_row_i, world_col_i)
        return zone_state.is_there_resource(resource_id)
