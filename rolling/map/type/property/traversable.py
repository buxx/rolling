# coding: utf-8
from rolling.map.type import zone
from rolling.model.meta import TransportType

traversable_properties = {
    zone.Nothing: {},
    zone.Sand: {TransportType.WALKING: True},
    zone.DryBush: {TransportType.WALKING: True},
    zone.Rock: {TransportType.WALKING: False},
    zone.RockyGround: {TransportType.WALKING: True},
    zone.SeaWater: {TransportType.WALKING: False},
    zone.ShortGrass: {TransportType.WALKING: True},
}
