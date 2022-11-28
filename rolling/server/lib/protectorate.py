import typing
from rolling.protectorate import ProtectorateState
from rolling.server.document.affinity import AffinityProtectorate
import sqlalchemy.orm
from rolling.types import WorldPoint

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class ProtectorateLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def state(self, world_point: WorldPoint) -> ProtectorateState:
        here_affinity_ids = (
            r.affinity_id
            for r in self._kernel.affinity_lib.get_zone_relations(
                row_i=world_point[0],
                col_i=world_point[1],
                accepted=True,
                character_is_alive=True,
            )
        )
        if not here_affinity_ids:
            return ProtectorateState.none(self._kernel)

        protectorate_documents = self.query(
            world_point=world_point,
            affinity_ids=here_affinity_ids,
        ).all()
        if not protectorate_documents:
            return ProtectorateState.none(self._kernel)

        protectorate_document: AffinityProtectorate = sorted(
            protectorate_documents, lambda p: p.updated_datetime
        )[-1]
        affinity_document = self._kernel.affinity_lib.get_affinity(
            protectorate_document.affinity_id
        )
        return ProtectorateState.protected_by(self._kernel, affinity_document)

    def query(
        self, world_point: WorldPoint, affinity_ids: typing.Optional[int]
    ) -> sqlalchemy.orm.Query:
        query = self._kernel.server_db_session.query(AffinityProtectorate).filter(
            AffinityProtectorate.world_row_i == world_point[0],
            AffinityProtectorate.world_col_i == world_point[1],
        )

        if affinity_ids is not None:
            query = query.filter(AffinityProtectorate.affinity_id.in_(affinity_ids))

        return query
