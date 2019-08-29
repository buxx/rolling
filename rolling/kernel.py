# coding: utf-8
from asyncio import AbstractEventLoop
import glob
import ntpath
import os
import typing

from sqlalchemy.engine import Engine
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from rolling.exception import ComponentNotPrepared
from rolling.exception import NoZoneMapError
from rolling.exception import RollingError
from rolling.game.base import Game
from rolling.log import kernel_logger
from rolling.map.legend import WorldMapLegend
from rolling.map.legend import ZoneMapLegend
from rolling.map.source import WorldMapSource
from rolling.map.source import ZoneMap
from rolling.map.source import ZoneMapSource
from rolling.map.type.world import Sea
from rolling.map.type.world import WorldMapTileType
from rolling.map.type.zone import ZoneMapTileType
from rolling.server.effect import EffectManager
from rolling.server.extension import ClientSideDocument
from rolling.server.extension import ServerSideDocument
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.server.zone.websocket import ZoneEventsManager
from rolling.trad import GlobalTranslation


class Kernel:
    def __init__(
        self,
        world_map_str: str = None,
        loop: AbstractEventLoop = None,
        tile_maps_folder: typing.Optional[str] = None,
        game_config_folder: typing.Optional[str] = None,
        client_db_path: str = "client.db",
        server_db_path: str = "server.db",
    ) -> None:
        self._tile_map_legend: typing.Optional[ZoneMapLegend] = None
        self._world_map_legend: typing.Optional[WorldMapLegend] = None
        self._world_map_source: typing.Optional[WorldMapSource] = WorldMapSource(
            self, world_map_str
        ) if world_map_str else None
        # TODO: rename in zone
        self._tile_maps_by_position: typing.Optional[
            typing.Dict[typing.Tuple[int, int], ZoneMap]
        ] = None
        self._game: typing.Optional[Game] = None

        # Database stuffs
        self._client_db_path = client_db_path
        self._server_db_path = server_db_path

        self._client_db_session: typing.Optional[Session] = None
        self._client_db_engine: typing.Optional[Engine] = None

        self._server_db_session: typing.Optional[Session] = None
        self._server_db_engine: typing.Optional[Engine] = None

        # Zone websocket
        self._server_zone_events_manager = ZoneEventsManager(self, loop=loop)

        # Generate tile maps if tile map folder given
        if tile_maps_folder is not None:
            self._tile_maps_by_position: typing.Dict[
                typing.Tuple[int, int], ZoneMap
            ] = {}

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

        # Generate game info if config given
        if game_config_folder is not None:
            self._game = Game(self, game_config_folder)

        # FIXME BS 2019-07-28: use these everywhere
        self._stuff_lib: typing.Optional["StuffLib"] = None
        self._character_lib: typing.Optional["CharacterLib"] = None
        self._effect_manager: typing.Optional["EffectManager"] = None
        self._translation = GlobalTranslation()

    @property
    def stuff_lib(self) -> StuffLib:
        if self._stuff_lib is None:
            self._stuff_lib = StuffLib(self)
        return self._stuff_lib

    @property
    def translation(self) -> GlobalTranslation:
        return self._translation

    @property
    def character_lib(self) -> CharacterLib:
        if self._character_lib is None:
            self._character_lib = CharacterLib(self, stuff_lib=self.stuff_lib)
        return self._character_lib

    @property
    def effect_manager(self) -> EffectManager:
        if self._effect_manager is None:
            self._effect_manager = EffectManager(self)
        return self._effect_manager

    @property
    def game(self) -> Game:
        if self._game is None:
            raise ComponentNotPrepared(
                "self._game must be prepared before usage: provide game config folder parameter"
            )
        return self._game

    @property
    def server_zone_events_manager(self) -> ZoneEventsManager:
        if self._server_zone_events_manager is None:
            raise ComponentNotPrepared(
                "self._server_zone_events_manager must be prepared before usage"
            )

        return self._server_zone_events_manager

    @property
    def world_map_source(self) -> WorldMapSource:
        if self._world_map_source is None:
            raise ComponentNotPrepared(
                "self._world_map_source must be prepared before usage"
            )

        return self._world_map_source

    @world_map_source.setter
    def world_map_source(self, value: WorldMapSource) -> None:
        self._world_map_source = value

    @property
    def tile_maps_by_position(self) -> typing.Dict[typing.Tuple[int, int], ZoneMap]:
        if self._world_map_source is None:
            raise ComponentNotPrepared(
                "self._tile_maps_by_position must be prepared before usage"
            )

        return self._tile_maps_by_position

    @property
    def world_map_legend(self) -> WorldMapLegend:
        if self._world_map_legend is None:
            # TODO BS 2018-12-20: Consider it can be an external source
            self._world_map_legend = WorldMapLegend(
                {
                    "~": "SEA",
                    "^": "MOUNTAIN",
                    "ፆ": "JUNGLE",
                    "∩": "HILL",
                    "⡩": "BEACH",
                    "⠃": "PLAIN",
                },
                WorldMapTileType,
                default_type=Sea,
            )

        return self._world_map_legend

    @property
    def tile_map_legend(self) -> ZoneMapLegend:
        if self._tile_map_legend is None:
            # TODO BS 2018-12-20: Consider it can be an external source
            self._tile_map_legend = ZoneMapLegend(
                {
                    " ": "NOTHING",
                    "⡩": "SAND",
                    "܄": "SHORT_GRASS",
                    "ʛ": "DRY_BUSH",
                    "#": "ROCK",
                    "፨": "ROCKY_GROUND",
                    "؛": "HIGH_GRASS",
                    "~": "SEA_WATER",
                    "⁖": "DIRT",
                    "߉": "LEAF_TREE",
                    "ፆ": "TROPICAL_TREE",
                    "آ": "DEAD_TREE",
                    "ގ": "FRESH_WATER",
                },
                ZoneMapTileType,
            )

        return self._tile_map_legend

    @property
    def client_db_session(self) -> Session:
        if self._client_db_session is None:
            raise ComponentNotPrepared("client_db_session is not created yet")

        return self._client_db_session

    @property
    def server_db_session(self) -> Session:
        if self._server_db_session is None:
            raise ComponentNotPrepared("server_db_session is not created yet")

        return self._server_db_session

    def get_tile_map(self, row_i: int, col_i: int) -> ZoneMap:
        try:
            return self.tile_maps_by_position[(row_i, col_i)]
        except KeyError:
            raise NoZoneMapError("No zone map for {},{} position".format(row_i, col_i))

    def init_client_db_session(self) -> None:
        kernel_logger.info('Initialize database connection to "client.db"')
        self._client_db_engine = create_engine(f"sqlite:///{self._client_db_path}")
        self._client_db_session = sessionmaker(bind=self._client_db_engine)()
        ClientSideDocument.metadata.create_all(self._client_db_engine)

    def init_server_db_session(self) -> None:
        kernel_logger.info('Initialize database connection to "server.db"')
        self._server_db_engine = create_engine(f"sqlite:///{self._server_db_path}")
        self._server_db_session = sessionmaker(bind=self._server_db_engine)()
        ServerSideDocument.metadata.create_all(self._server_db_engine)
