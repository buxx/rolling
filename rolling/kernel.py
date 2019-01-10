# coding: utf-8
import glob
import ntpath
import os
import typing

from sqlalchemy.engine import Engine
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from rolling.exception import NoZoneMapError
from rolling.exception import RollingError
from rolling.log import kernel_logger
from rolling.map.legend import ZoneMapLegend
from rolling.map.source import WorldMapSource
from rolling.map.source import ZoneMap
from rolling.map.source import ZoneMapSource
from rolling.map.type.zone import ZoneMapTileType
from rolling.server.extension import ClientSideDocument
from rolling.server.extension import ServerSideDocument


class Kernel(object):
    def __init__(
        self, world_map_str: str, tile_maps_folder: typing.Optional[str] = None
    ) -> None:
        self._world_map_source = WorldMapSource(self, world_map_str)
        self._tile_map_legend: typing.Optional[ZoneMapLegend] = None
        self._tile_maps_by_position: typing.Dict[typing.Tuple[int, int], ZoneMap] = {}

        # Database stuffs
        self._client_db_session: typing.Optional[Session] = None
        self._client_db_engine: typing.Optional[Engine] = None

        self._server_db_session: typing.Optional[Session] = None
        self._server_db_engine: typing.Optional[Engine] = None

        # Generate tile maps if tile map folder given
        if tile_maps_folder is not None:
            for tile_map_source_file_path in glob.glob(
                os.path.join(tile_maps_folder, "*.txt")
            ):
                tile_map_source_file_name = ntpath.basename(tile_map_source_file_path)
                row_i, col_i = map(
                    int, tile_map_source_file_name.replace(".txt", "").split("-")
                )
                kernel_logger.debug(
                    'Load tile map "{}"'.format(tile_map_source_file_name)
                )

                with open(tile_map_source_file_path, "r") as f:
                    tile_map_source_raw = f.read()

                self._tile_maps_by_position[(row_i, col_i)] = ZoneMap(
                    row_i, col_i, ZoneMapSource(self, tile_map_source_raw)
                )

    @property
    def world_map_source(self) -> WorldMapSource:
        return self._world_map_source

    @property
    def tile_map_legend(self) -> ZoneMapLegend:
        if self._tile_map_legend is None:
            # TODO BS 2018-12-20: Consider it can be an external source
            self._tile_map_legend = ZoneMapLegend(
                {
                    " ": "NOTHING",
                    "⡩": "SAND",
                    "⁘": "SHORT_GRASS",
                    "ൖ": "DRY_BUSH",
                    "#": "ROCK",
                    "⑉": "ROCKY_GROUND",
                    "~": "SEA_WATER",
                },
                ZoneMapTileType,
            )

        return self._tile_map_legend

    @property
    def client_db_session(self) -> Session:
        if self._client_db_session is None:
            raise RollingError("client_db_session is not created yet")

        return self._client_db_session

    @property
    def server_db_session(self) -> Session:
        if self._server_db_session is None:
            raise RollingError("server_db_session is not created yet")

        return self._server_db_session

    def get_tile_map(self, row_i: int, col_i: int) -> ZoneMap:
        try:
            return self._tile_maps_by_position[(row_i, col_i)]
        except KeyError:
            raise NoZoneMapError("No zone map for {},{} position".format(row_i, col_i))

    def init_client_db_session(self) -> None:
        kernel_logger.info('Initialize database connection to "client.db"')
        self._client_db_engine = create_engine("sqlite:///client.db")
        self._client_db_session = sessionmaker(bind=self._client_db_engine)()
        ClientSideDocument.metadata.create_all(self._client_db_engine)

    def init_server_db_session(self) -> None:
        kernel_logger.info('Initialize database connection to "server.db"')
        self._server_db_engine = create_engine("sqlite:///server.db")
        self._server_db_session = sessionmaker(bind=self._server_db_engine)()
        ServerSideDocument.metadata.create_all(self._server_db_engine)
