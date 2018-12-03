# coding: utf-8


class RollingError(Exception):
    pass


class SourceLoadError(RollingError):
    pass
