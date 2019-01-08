# coding: utf-8
from rolling.map.type import tile
from rolling.model.meta import TransportType

traversable_properties = {
    tile.Nothing: {},
    tile.Sand: {TransportType.WALKING: True},
    tile.DryBush: {TransportType.WALKING: True},
    tile.Rock: {TransportType.WALKING: False},
    tile.RockyGround: {TransportType.WALKING: True},
    tile.SeaWater: {TransportType.WALKING: False},
    tile.ShortGrass: {TransportType.WALKING: True},
}
