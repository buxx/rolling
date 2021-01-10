# coding: utf-8
import dataclasses

from rolling.server.document.corpse import AnimatedCorpseType


@dataclasses.dataclass
class AnimatedCorpseModel:
    id: int
    type_: AnimatedCorpseType

    world_col_i: int
    world_row_i: int
    zone_col_i: int
    zone_row_i: int
