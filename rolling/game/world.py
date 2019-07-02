# coding: utf-8
import typing

from rolling.map.type.base import MapTileType
from rolling.map.type.world import WorldMapTileType
from rolling.model.stuff import ZoneGenerationStuff, StuffMaterialType
from rolling.model.world import World, Resource, ResourceType
from rolling.model.zone import ZoneProperties

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class WorldManager:
    def __init__(self, kernel: "Kernel", world: World) -> None:
        self._kernel = kernel
        self._world = world

    @property
    def world(self) -> World:
        return self._world

    def get_generation_stuff_by_zone_type(
        self
    ) -> typing.Dict[typing.Type[MapTileType], typing.List[ZoneGenerationStuff]]:
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
        world_row_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        material_type: StuffMaterialType,
    ) -> typing.List[Resource]:
        # FIXME BS 2019-07-02: for debugging !!!
        return [
            Resource(
                type_=ResourceType.WATER,
                material_type=StuffMaterialType.LIQUID,
                name="Fresh water",
            )
        ]
