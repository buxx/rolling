# coding: utf-8
import dataclasses

import serpyco


@dataclasses.dataclass
class AnimatedCorpseModel:
    id: int
    type_: str  # AnimatedCorpseType

    world_col_i: int
    world_row_i: int
    zone_col_i: int
    zone_row_i: int


@dataclasses.dataclass
class GetAnimatedCorpsesQuery:
    world_row_i: int = serpyco.number_field(cast_on_load=True)
    world_col_i: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class GetAnimatedCorpsePath:
    animated_corpse_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class SignalNewAnimatedCorpsePath:
    animated_corpse_id: int = serpyco.number_field(cast_on_load=True)
