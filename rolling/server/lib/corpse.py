# coding: utf-8
import typing

from sqlalchemy.orm import Query

from rolling.server.document.corpse import AnimatedCorpseDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class AnimatedCorpseLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def _base_query(self) -> Query:
        return self._kernel.server_db_session.query(
            AnimatedCorpseDocument
        )

    def get_all(self) -> typing.List[AnimatedCorpseDocument]:
        return self._base_query().all()
