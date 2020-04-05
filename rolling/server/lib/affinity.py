# coding: utf-8
import typing

from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import NoResultFound

from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.affinity import MEMBER_STATUS
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityJoinType
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.message import MessageDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class AffinityLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def create(
        self,
        name: str,
        join_type: AffinityJoinType,
        direction_type: AffinityDirectionType,
        commit: bool = True,
    ) -> AffinityDocument:
        doc = AffinityDocument(
            name=name,
            description="",
            join_type=join_type.value,
            direction_type=direction_type.value,
        )
        self._kernel.server_db_session.add(doc)

        if commit:
            self._kernel.server_db_session.commit()

        return doc

    def join(
        self,
        character_id: str,
        affinity_id: int,
        accepted: bool = False,
        fighter: bool = False,
        request: bool = True,
        status_id: str = MEMBER_STATUS[0],
        commit=True,
    ) -> AffinityRelationDocument:
        doc = AffinityRelationDocument(
            character_id=character_id,
            affinity_id=affinity_id,
            accepted=accepted,
            status_id=status_id if request else None,
            fighter=fighter,
            request=request,
        )
        self._kernel.server_db_session.add(doc)

        if commit:
            self._kernel.server_db_session.commit()

        return doc

    def get_affinity(self, affinity_id: int) -> AffinityDocument:
        return (
            self._kernel.server_db_session.query(AffinityDocument)
            .filter(AffinityDocument.id == affinity_id)
            .one()
        )

    def get_character_relation(
        self, affinity_id: int, character_id: str
    ) -> typing.Optional[AffinityRelationDocument]:
        try:
            return (
                self._kernel.server_db_session.query(AffinityRelationDocument)
                .filter(
                    AffinityRelationDocument.affinity_id == affinity_id,
                    AffinityRelationDocument.character_id == character_id,
                )
                .one()
            )
        except NoResultFound:
            return None

    def get_with_relation(
        self, character_id: str
    ) -> typing.Generator[typing.Tuple[AffinityRelationDocument, AffinityDocument], None, None]:
        for relation in (
            self._kernel.server_db_session.query(AffinityRelationDocument)
            .filter(AffinityRelationDocument.character_id == character_id)
            .all()
        ):
            yield relation, self._kernel.server_db_session.query(AffinityDocument).filter(
                AffinityDocument.id == relation.affinity_id
            ).one()

    def get_without_relation(self, character_id: str) -> typing.List[AffinityDocument]:
        character_affinity_ids = (
            self._kernel.server_db_session.query(AffinityRelationDocument.affinity_id)
            .filter(AffinityRelationDocument.character_id == character_id)
            .all()
        ) or []
        character_affinity_ids = character_affinity_ids[0] if character_affinity_ids else []

        return (
            self._kernel.server_db_session.query(AffinityDocument)
            .filter(AffinityDocument.id.notin_(character_affinity_ids))
            .all()
        )

    def count_members(self, affinity_id: int, fighter: typing.Optional[bool] = None) -> int:
        if not fighter:
            return (
                self._kernel.server_db_session.query(AffinityRelationDocument)
                .filter(
                    AffinityRelationDocument.affinity_id == affinity_id,
                    AffinityRelationDocument.accepted == True,
                )
                .count()
            )

        return (
            self._kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.affinity_id == affinity_id,
                AffinityRelationDocument.fighter == True,
            )
            .count()
        )

    def there_is_unvote_relation(
        self, affinity: AffinityDocument, relation: AffinityRelationDocument
    ) -> bool:
        if affinity.direction_type == AffinityDirectionType.ONE_DIRECTOR.value:
            if relation.status_id == CHIEF_STATUS[0]:
                if (
                    self._kernel.server_db_session.query(AffinityRelationDocument)
                    .filter(
                        AffinityRelationDocument.affinity_id == affinity.id,
                        AffinityRelationDocument.accepted == False,
                        AffinityRelationDocument.request == True,
                    )
                    .count()
                ):
                    return True
        return False
