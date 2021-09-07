# coding: utf-8
from enum import Enum


class TransportType(Enum):
    WALKING = "WALKING"
    BOAT = "BOAT"


class FromType(Enum):
    HIMSELF = "HIMSELF"
    BUILD = "BUILD"
    STUFF = "STUFF"


class RiskType(Enum):
    NONE = "NONE"
