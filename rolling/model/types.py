# coding: utf-8
import enum


# FIXME BS NOW: remove and use from config
class MaterialType(enum.Enum):
    LIQUID = "LIQUID"
    SANDY = "SANDY"
    PASTY = "PASTY"
    GAS = "GAS"
    SOLID = "SOLID"
    LITTLE_OBJECT = "LITTLE_OBJECT"
    SMALL_PIECE = "SMALL_PIECE"
