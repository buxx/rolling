# coding: utf-8
import enum


class MaterialType(enum.Enum):
    LIQUID = "LIQUID"
    SANDY = "SANDY"
    PASTY = "PASTY"
    GAS = "GAS"
    SOLID = "SOLID"
    LITTLE_OBJECT = "LITTLE_OBJECT"
    SMALL_PIECE = "SMALL_PIECE"
