# coding: utf-8
import typing

from rolling.map.type.base import MapTileType
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.resource import resource_type_materials
from rolling.model.types import MaterialType
from rolling.model.world import Resource
from rolling.model.world import World
from rolling.model.zone import ZoneProperties
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.stuff import ZoneGenerationStuff


class WorldManager:
    def __init__(self, kernel: "Kernel", world: World) -> None:
        self._kernel = kernel
        self._world = world

    @property
    def world(self) -> World:
        return self._world

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

    def get_resource_on_or_around(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        material_type: MaterialType,
    ) -> typing.List[Resource]:
        # TODO BS 2019-07-02: factory for types
        inspect_zone_positions = get_on_and_around_coordinates(zone_row_i, zone_col_i)
        zone_map = self._kernel.tile_maps_by_position[(world_row_i, world_col_i)]
        resources: typing.List[Resource] = []

        for zone_row_i, zone_col_i in inspect_zone_positions:
            try:
                map_tile_type = zone_map.source.geography.rows[zone_row_i][zone_col_i]
            except KeyError:
                continue

            map_tile_type = typing.cast(ZoneMapTileType, map_tile_type)

            for resource_type in map_tile_type.extractable():
                resource_material_type = resource_type_materials[resource_type]

                if resource_material_type == material_type:
                    resources.append(
                        Resource(
                            type_=resource_type,
                            material_type=resource_material_type,
                            # TODO BS 2019-07-03: real name some were
                            name=str(resource_type),
                        )
                    )

        return list(set(resources))
