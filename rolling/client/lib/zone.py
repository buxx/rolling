# coding: utf-8
from sqlalchemy.orm.exc import NoResultFound
import typing

from rolling.client.document.server import ServerDocument
from rolling.client.http.client import HttpClient
from rolling.exception import TileTypeNotFound
from rolling.kernel import Kernel
from rolling.map.type.base import MapTileType
from rolling.model.character import CharacterModel
from rolling.model.zone import ZoneMapModel
from rolling.model.zone import ZoneTileTypeModel


class ZoneLib:
    def __init__(self, kernel: Kernel, client: HttpClient) -> None:
        self._kernel = kernel
        self._client = client
        self._tile_types = self._client.get_tile_types()
        self._tile_types_by_ids = {tt.id: tt for tt in self._tile_types}

    def get_zone(self, world_row_i: int, world_col_i: int) -> ZoneMapModel:
        return self._client.get_zone(world_row_i, world_col_i)

    def get_zone_tile_type_model(
        self, tile_type: typing.Type[MapTileType]
    ) -> ZoneTileTypeModel:
        try:
            return self._tile_types_by_ids[tile_type.id]
        except KeyError:
            existing_ids = '"' + '", "'.join(self._tile_types_by_ids.keys()) + '"'
            raise TileTypeNotFound(
                f'There is no tile type with id "{tile_type.id}" (from: {existing_ids})'
            )
