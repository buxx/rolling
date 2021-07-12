# coding: utf-8
import contextlib
import pathlib
import typing
from threading import Lock

from sqlalchemy import and_

from rolling.exception import NotEnoughResource
from rolling.map.source import ZoneMap
from rolling.map.type.base import MapTileType
from rolling.map.type.property.traversable import traversable_properties
from rolling.map.type.world import WorldMapTileType
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.zone import ZoneMapModel
from rolling.model.zone import ZoneTileTypeModel
from rolling.server.document.resource import ZoneResourceDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class ZoneLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel
        self._locks: typing.Dict[typing.Tuple[int, int], Lock] = {}

    @contextlib.contextmanager
    def lock(self, world_row_i: int, world_col_i: int) -> Lock:
        try:
            lock = self._locks[(world_row_i, world_col_i)]
        except KeyError:
            lock = Lock()
            self._locks[(world_row_i, world_col_i)] = lock

        try:
            lock.acquire()
            yield
        finally:
            lock.release()

    def get_all_tiles(self) -> typing.List[ZoneTileTypeModel]:
        tiles: typing.List[ZoneTileTypeModel] = []

        for tile_id, tile_class in ZoneMapTileType.get_all().items():
            tiles.append(
                ZoneTileTypeModel(
                    id=tile_id,
                    char=self._kernel.tile_map_legend.get_str_with_type(tile_class),
                    traversable=traversable_properties[tile_class],
                    foreground_color=tile_class.foreground_color,
                    background_color=tile_class.background_color,
                    mono=tile_class.mono,
                    foreground_high_color=tile_class.foreground_high_color,
                    background_high_color=tile_class.background_high_color,
                )
            )

        return tiles

    def get_zone(self, row_i: int, col_i: int) -> ZoneMapModel:
        return ZoneMapModel(raw_source=self._kernel.get_tile_map(row_i, col_i).source.raw_source)

    def get_zone_ressource_doc(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        resource_id: str,
    ) -> ZoneResourceDocument:
        return (
            self._kernel.server_db_session.query(ZoneResourceDocument)
            .filter(
                and_(
                    ZoneResourceDocument.world_row_i == world_row_i,
                    ZoneResourceDocument.world_col_i == world_col_i,
                    ZoneResourceDocument.zone_row_i == zone_row_i,
                    ZoneResourceDocument.zone_col_i == zone_col_i,
                    ZoneResourceDocument.resource_id == resource_id,
                )
            )
            .one()
        )

    def create_zone_ressource_doc(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        resource_id: str,
        quantity: float,
        destroy_when_empty: bool,
    ) -> ZoneResourceDocument:
        zone_resource_document = ZoneResourceDocument(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            resource_id=resource_id,
            quantity=quantity,
            destroy_tile_when_empty=destroy_when_empty,
        )
        self._kernel.server_db_session.add(zone_resource_document)
        self._kernel.server_db_session.commit()
        return zone_resource_document

    def reduce_resource_quantity(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        resource_id: str,
        quantity: float,
        allow_reduce_more_than_possible: bool,
        commit: bool = True,
    ) -> None:
        zone_resource_doc = self.get_zone_ressource_doc(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            resource_id=resource_id,
        )

        if quantity > zone_resource_doc.quantity and not allow_reduce_more_than_possible:
            raise NotEnoughResource(
                resource_id=resource_id,
                available_quantity=zone_resource_doc.quantity,
                required_quantity=quantity,
            )

        zone_resource_doc.quantity = zone_resource_doc.quantity - quantity
        if zone_resource_doc.quantity < 0 or not round(zone_resource_doc.quantity, 3):
            self._kernel.server_db_session.delete(zone_resource_doc)

            if zone_resource_doc.destroy_tile_when_empty:
                self.destroy_tile(
                    world_row_i=world_row_i,
                    world_col_i=world_col_i,
                    zone_row_i=zone_row_i,
                    zone_col_i=zone_col_i,
                )

        if commit:
            self._kernel.server_db_session.commit()

    def destroy_tile(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
    ) -> None:
        with self.lock(world_row_i, world_col_i):
            zone_type: typing.Type[WorldMapTileType] = (
                self._kernel.world_map_source.geography.rows[world_row_i][world_col_i]
            )
            zone_map: ZoneMap = self._kernel.tile_maps_by_position[(world_row_i, world_col_i)]
            zone_file_path = pathlib.Path(
                self._kernel.zone_maps_folder + f"/{world_row_i}-{world_col_i}.txt"
            )

            with open(zone_file_path) as zone_file:
                zone_raw = zone_file.read()

            zone_raw_by_lines = zone_raw.splitlines()
            # FIXME BS NOW: zones txt file start with ::GEO ... this is dangerous :s
            line = zone_raw_by_lines[zone_row_i + 1]
            line_as_char_list = list(line)
            line_as_char_list[zone_col_i] = zone_map.source.geography.legend.get_str_with_type(
                ZoneMapTileType.get_for_id(zone_type.default_tile_id)
            )
            line_rewrote = "".join(line_as_char_list)
            # FIXME BS NOW: zones txt file start with ::GEO ... this is dangerous :s
            zone_raw_by_lines[zone_row_i + 1] = line_rewrote

            with open(zone_file_path, "w") as zone_file:
                zone_file.write("\n".join(zone_raw_by_lines))

            self._kernel.load_zone_from_file_path(str(zone_file_path))
