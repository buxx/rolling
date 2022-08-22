import datetime
import typing

import sqlalchemy.exc

from rolling.exception import ImpossibleAction
from rolling.server.document.spawn import SpawnPointDocument
from rolling.server.document.affinity import AffinityDocument


if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel

THREE_WEEKS_IN_SECONDS = 60 * 60 * 24 * 7 * 3


class SpawnPointLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def spawn_point_exist_for_build_id(self, build_id: int) -> bool:
        try:
            self.get_from_build(build_id)
            return True
        except sqlalchemy.exc.NoResultFound:
            return False

    def get_from_build(self, build_id: int) -> SpawnPointDocument:
        self._kernel.server_db_session.query(SpawnPointDocument).filter(
            SpawnPointDocument.build_id == build_id
        ).one()

    def get_from_affinity(self, affinity_id: int) -> SpawnPointDocument:
        return (
            self._kernel.server_db_session.query(SpawnPointDocument)
            .filter(SpawnPointDocument.affinity_id == affinity_id)
            .one()
        )

    def affinity_have_spawn_point(self, affinity_id: int) -> bool:
        try:
            self._kernel.server_db_session.query(SpawnPointDocument).filter(
                SpawnPointDocument.affinity_id == affinity_id
            ).one()
            return True
        except sqlalchemy.exc.NoResultFound:
            return False

    def check_can_create_spawn_point_with_build(
        self, affinity_id: int, build_id: int
    ) -> bool:
        if self.spawn_point_exist_for_build_id(build_id):
            raise ImpossibleAction(
                "Le batiment est déjà utilisé pour un point d'apparition"
            )

        if self.affinity_have_spawn_point(affinity_id):
            raise ImpossibleAction("L'affinité possède déjà un point d'apparition")

        affinity_document = self._kernel.affinity_lib.get_affinity(affinity_id)
        now = datetime.datetime.now()
        if (
            now - affinity_document.creation_datetime
        ).total_seconds() < 60 * 60 * 24 * 7 * 3:
            raise ImpossibleAction("L'affinité doit exister depuis 3 semaines")

    def create_from_build(self, affinity_id: int, build_id: int) -> SpawnPointDocument:
        spawn_point = SpawnPointDocument(
            affinity_id=affinity_id,
            build_id=build_id,
        )
        self._kernel.server_db_session.add(spawn_point)
        self._kernel.server_db_session.commit()

        return spawn_point

    def delete_for_affinity(self, affinity_id: int) -> None:
        try:
            spawn_point = self.get_from_affinity(affinity_id)
            self._kernel.server_db_session.delete(spawn_point)
            self._kernel.server_db_session.commit()
        except sqlalchemy.exc.NoResultFound:
            pass
