# coding: utf-8
import abc
import enum
import random
import typing

from rolling.exception import ComponentNotPrepared
from rolling.exception import NoMetaLine
from rolling.exception import RollingError
from rolling.exception import SourceLoadError
from rolling.map.type.world import WorldMapTileType

if typing.TYPE_CHECKING:
    from rolling.map.source import WorldMapSource
    from rolling.kernel import Kernel


SPAWN_LINE_NAME = "SPAWN"


class SpawnType(enum.Enum):
    RANDOM = "RANDOM"


class WorldMapSpawn(abc.ABC):
    @abc.abstractmethod
    def get_spawn_coordinates(
        self, world_map_source: "WorldMapSource"
    ) -> typing.Tuple[int, int]:
        pass

    @classmethod
    def create_from_raw_line(
        cls, kernel: "Kernel", raw_spawn_line: str
    ) -> "WorldMapSpawn":
        """Create new instance of WorldMapSpawn child based on raw_spawn_line.
        raw_spawn_line example: SPAWN:RANDOM:BEACH,PLAIN,"""
        assert raw_spawn_line.startswith(SPAWN_LINE_NAME)
        spawn_line_value = raw_spawn_line.strip()[6:]
        spawn_type, raw_spawn_values = spawn_line_value.split(":")

        if spawn_type == SpawnType.RANDOM.value:
            spawn_raw_values = [
                v.strip() for v in raw_spawn_values.split(",") if v.strip()
            ]
            spawn_values = [WorldMapTileType.get_for_id(v) for v in spawn_raw_values]
            return RandomWorldMapSpawn(kernel, world_tile_types=spawn_values)


class RandomWorldMapSpawn(WorldMapSpawn):
    def __init__(
        self,
        kernel: "Kernel",
        world_tile_types: typing.List[typing.Type["WorldMapTileType"]],
    ) -> None:
        self._kernel = kernel
        self._world_tile_types: typing.List[
            typing.Type["WorldMapTileType"]
        ] = world_tile_types

    def get_spawn_coordinates(
        self, world_map_source: "WorldMapSource"
    ) -> typing.Tuple[int, int]:
        available_coordinates: typing.List[typing.Tuple[int, int]] = []

        for row_i, rows in enumerate(self._kernel.world_map_source.geography.rows):
            for col_i, world_tile_type in enumerate(rows):
                if world_tile_type in self._world_tile_types:
                    available_coordinates.append((row_i, col_i))

        if not available_coordinates:
            raise RollingError("No matching world tile for find spawn coordinate")

        return random.choice(available_coordinates)


class WorldMapMeta:
    def __init__(self, kernel: "Kernel", raw_lines: typing.List[str]) -> None:
        self._kernel = kernel

        self._spawn: typing.Optional[WorldMapSpawn] = None
        try:
            spawn_line = self._find_line(SPAWN_LINE_NAME, raw_lines)
            self._spawn = WorldMapSpawn.create_from_raw_line(self._kernel, spawn_line)
        except NoMetaLine:
            pass

    @classmethod
    def _find_line(cls, line_name: str, lines: typing.List[str]) -> str:
        for line in lines:
            if line.startswith(line_name):
                return line.strip()

        raise NoMetaLine(f"No line starting with '{line_name}' in '{lines}'")

    @property
    def spawn(self) -> WorldMapSpawn:
        if self._spawn is None:
            raise ComponentNotPrepared(
                "World source map don't contains spawn meta data"
            )

        return self._spawn
