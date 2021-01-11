# coding: utf-8
from sqlalchemy.orm import Query
import typing

from rolling.exception import CantMove
from rolling.server.document.corpse import AnimatedCorpseDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class AnimatedCorpseLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def _base_query(self) -> Query:
        return self._kernel.server_db_session.query(AnimatedCorpseDocument)

    def get_all(self) -> typing.List[AnimatedCorpseDocument]:
        return self._base_query().all()

    def get(self, animated_corpse_id: int) -> AnimatedCorpseDocument:
        return self._base_query().filter(AnimatedCorpseDocument.id == animated_corpse_id).one()

    def move(self, animated_corpse: AnimatedCorpseDocument, to_zone_row_i: int, to_zone_col_i: int, commit: bool = True):
        # TODO BS: performance hell here !
        traversable_coordinates = self._kernel.get_traversable_coordinates(
            animated_corpse.world_row_i, animated_corpse.world_col_i
        )
        if (to_zone_row_i, to_zone_col_i) not in traversable_coordinates:
            raise CantMove(f"Can't move to {to_zone_row_i}.{to_zone_col_i}")

        animated_corpse.zone_row_i = to_zone_row_i
        animated_corpse.zone_col_i = to_zone_col_i
        self._kernel.server_db_session.add(animated_corpse)

        if commit:
            self._kernel.server_db_session.commit()
