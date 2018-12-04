# coding: utf-8
from rolling.map.source import WorldMapSource


class Kernel(object):
    def __init__(self, world_map_str: str) -> None:
        self._world_map_source = WorldMapSource(world_map_str)

    @property
    def world_map_source(self) -> WorldMapSource:
        return self._world_map_source
