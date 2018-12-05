# coding: utf-8


class RollingError(Exception):
    pass


class SourceLoadError(RollingError):
    pass


class TileTypeNotFound(RollingError):
    pass


class NoDefaultTileType(RollingError):
    pass
