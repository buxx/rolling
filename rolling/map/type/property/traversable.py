# coding: utf-8
from rolling.map.type import zone
from rolling.model.meta import TransportType

# FIXME BS 2019-03-06: transport types are str because serpyco bug, see
# rolling.model.zone.ZoneTileTypeModel
traversable_properties = {
    zone.Nothing: {TransportType.WALKING.value: False},
    zone.Sand: {TransportType.WALKING.value: True},
    zone.DryBush: {TransportType.WALKING.value: True},
    zone.Rock: {TransportType.WALKING.value: False},
    zone.RockyGround: {TransportType.WALKING.value: True},
    zone.SeaWater: {TransportType.WALKING.value: False},
    zone.HighGrass: {TransportType.WALKING.value: True},
    zone.Dirt: {TransportType.WALKING.value: True},
    zone.LeafTree: {TransportType.WALKING.value: True},
    zone.TropicalTree: {TransportType.WALKING.value: True},
    zone.DeadTree: {TransportType.WALKING.value: True},
    zone.FreshWater: {TransportType.WALKING.value: True},
    zone.ShortGrass: {TransportType.WALKING.value: True},
}
