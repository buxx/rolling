# coding: utf-8
import json
from operator import and_
import sqlalchemy
from sqlalchemy import or_
from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import NoResultFound
import typing

from rolling.model.character import CharacterModel
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityJoinType
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.affinity import MEMBER_STATUS
from rolling.server.document.affinity import WARLORD_STATUS
from rolling.server.document.character import CharacterDocument

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

    def get_multiple(self, affinity_ids: typing.List[int]) -> typing.List[AffinityDocument]:
        return (
            self._kernel.server_db_session.query(AffinityDocument)
            .filter(AffinityDocument.id.in_(affinity_ids))
            .all()
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

    def get_accepted_affinities(
        self, character_id: str, warlord: bool = False
    ) -> typing.List[AffinityRelationDocument]:
        query = self._kernel.server_db_session.query(AffinityRelationDocument).filter(
            AffinityRelationDocument.character_id == character_id,
            AffinityRelationDocument.accepted == True,
        )

        if warlord:
            query = query.filter(
                AffinityRelationDocument.status_id.in_((CHIEF_STATUS[0], WARLORD_STATUS[0]))
            )

        return query.all()

    def get_with_relations(
        self,
        character_id: str,
        active: typing.Optional[bool] = None,
        request: typing.Optional[bool] = None,
    ) -> typing.List[AffinityRelationDocument]:
        query = self._kernel.server_db_session.query(AffinityRelationDocument).filter(
            AffinityRelationDocument.character_id == character_id
        )

        if active is not None:
            query = query.filter(AffinityRelationDocument.accepted == active)

        if request is not None:
            query = query.filter(AffinityRelationDocument.request == request)

        return query.all()

    def get_affinities_without_relations(
        self,
        character_id: str,
        with_alive_character_in_world_row_i: typing.Optional[int] = None,
        with_alive_character_in_world_col_i: typing.Optional[int] = None,
    ) -> typing.List[AffinityDocument]:
        current_character_affinity_ids = [
            r[0]
            for r in self._kernel.server_db_session.query(AffinityRelationDocument.affinity_id)
            .filter(
                AffinityRelationDocument.character_id == character_id,
                AffinityRelationDocument.accepted == True,
            )
            .all()
        ]

        query = self._kernel.server_db_session.query(AffinityRelationDocument.affinity_id).filter(
            AffinityRelationDocument.affinity_id.notin_(current_character_affinity_ids)
        )

        if (
            with_alive_character_in_world_row_i is not None
            and with_alive_character_in_world_col_i is not None
        ):
            here_alive_character_affinity_ids = [
                r.affinity_id
                for r in self.get_zone_relations(
                    row_i=with_alive_character_in_world_row_i,
                    col_i=with_alive_character_in_world_col_i,
                    character_is_alive=True,
                    exclude_character_ids=[character_id],
                )
            ]
            query = query.filter(
                AffinityRelationDocument.affinity_id.in_(here_alive_character_affinity_ids)
            )

        affinity_ids = [r.affinity_id for r in query.all()]
        return (
            self._kernel.server_db_session.query(AffinityDocument)
            .filter(AffinityDocument.id.in_(affinity_ids))
            .all()
        )

    def members_query(
        self,
        affinity_id: int,
        fighter: typing.Optional[bool] = None,
        world_row_i: typing.Optional[int] = None,
        world_col_i: typing.Optional[int] = None,
        exclude_character_ids: typing.Optional[typing.List[str]] = None,
    ) -> Query:
        if not fighter:
            query = self._kernel.server_db_session.query(AffinityRelationDocument).filter(
                AffinityRelationDocument.affinity_id == affinity_id,
                AffinityRelationDocument.accepted == True,
            )
        else:
            query = self._kernel.server_db_session.query(AffinityRelationDocument).filter(
                AffinityRelationDocument.affinity_id == affinity_id,
                AffinityRelationDocument.fighter == True,
            )

        if world_row_i is not None and world_col_i is not None:
            zone_character_ids = [
                r[0]
                for r in self._kernel.character_lib.alive_query_ids.filter(
                    CharacterDocument.world_row_i == world_row_i,
                    CharacterDocument.world_col_i == world_col_i,
                ).all()
            ]
            query = query.filter(AffinityRelationDocument.character_id.in_(zone_character_ids))

        if exclude_character_ids:
            query = query.filter(
                AffinityRelationDocument.character_id.notin_(exclude_character_ids)
            )

        return query

    def count_members(
        self,
        affinity_id: int,
        fighter: typing.Optional[bool] = None,
        world_row_i: typing.Optional[int] = None,
        world_col_i: typing.Optional[int] = None,
        exclude_character_ids: typing.Optional[typing.List[str]] = None,
    ) -> int:
        return self.members_query(
            affinity_id,
            fighter=fighter,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            exclude_character_ids=exclude_character_ids,
        ).count()

    def get_members_ids(
        self,
        affinity_id: int,
        fighter: typing.Optional[bool] = None,
        world_row_i: typing.Optional[int] = None,
        world_col_i: typing.Optional[int] = None,
        exclude_character_ids: typing.Optional[typing.List[str]] = None,
    ) -> typing.List[str]:
        return [
            r[0]
            for r in self.members_query(
                affinity_id,
                fighter=fighter,
                world_row_i=world_row_i,
                world_col_i=world_col_i,
                exclude_character_ids=exclude_character_ids,
            )
            .with_entities(AffinityRelationDocument.character_id)
            .all()
        ]

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

    def get_affinity_fighter_ids(self, affinity_id: int) -> typing.List[str]:
        return [
            r[0]
            for r in (
                self._kernel.server_db_session.query(AffinityRelationDocument.character_id)
                .filter(
                    AffinityRelationDocument.affinity_id == affinity_id,
                    AffinityRelationDocument.fighter == True,
                )
                .all()
            )
        ]

    def count_ready_fighter(self, affinity_id: int, world_row_i: int, world_col_i: int) -> int:
        affinity_fighter_ids = self.get_affinity_fighter_ids(affinity_id)
        if not affinity_fighter_ids:
            return 0

        return self._kernel.character_lib.get_ready_to_fight_count(
            affinity_fighter_ids, world_row_i=world_row_i, world_col_i=world_col_i
        )

    def get_ready_fighters(
        self, affinity_id: int, world_row_i: int, world_col_i: int
    ) -> typing.List[CharacterModel]:
        affinity_fighter_ids = self.get_affinity_fighter_ids(affinity_id)
        return self._kernel.character_lib.get_ready_to_fights(
            affinity_fighter_ids, world_row_i=world_row_i, world_col_i=world_col_i
        )

    def have_active_or_fighter_relation_with(
        self, character_id: str, affinity_ids: typing.List[int]
    ) -> bool:
        return bool(
            self._kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.affinity_id.in_(affinity_ids),
                AffinityRelationDocument.character_id == character_id,
                sqlalchemy.or_(
                    AffinityRelationDocument.accepted == True,
                    AffinityRelationDocument.fighter == True,
                ),
            )
            .count()
        )

    def get_active_relation(self, character_id: str, affinity_id: int) -> AffinityRelationDocument:
        return (
            self._kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.character_id == character_id,
                AffinityRelationDocument.affinity_id == affinity_id,
                AffinityRelationDocument.accepted == True,
            )
            .one()
        )

    def character_is_in_affinity(self, character_id: str, affinity_id: int) -> bool:
        return bool(
            self._kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.character_id == character_id,
                AffinityRelationDocument.affinity_id == affinity_id,
                AffinityRelationDocument.accepted == True,
            )
            .count()
        )

    def get_chief_or_warlord_of_affinity(
        self,
        affinity_id: int,
        row_i: typing.Optional[int] = None,
        col_i: typing.Optional[int] = None,
    ) -> typing.List[CharacterModel]:
        query = self._kernel.server_db_session.query(AffinityRelationDocument.character_id).filter(
            AffinityRelationDocument.affinity_id == affinity_id,
            AffinityRelationDocument.status_id.in_((CHIEF_STATUS[0], WARLORD_STATUS[0])),
            AffinityRelationDocument.accepted == True,
        )

        if row_i is not None and col_i is not None:
            here_ids = self._kernel.character_lib.get_zone_character_ids(row_i, col_i)
            query = query.filter(AffinityRelationDocument.character_id.in_(here_ids))

        return [self._kernel.character_lib.get(r[0]) for r in query.all()]

    def get_zone_relations(
        self,
        row_i: int,
        col_i: int,
        accepted: typing.Optional[bool] = None,
        affinity_ids: typing.Optional[typing.List[int]] = None,
        exclude_character_ids: typing.Optional[typing.List[str]] = None,
        character_is_alive: typing.Optional[bool] = True,
    ) -> typing.List[AffinityRelationDocument]:
        here_ids = self._kernel.character_lib.get_zone_character_ids(
            row_i, col_i, alive=character_is_alive
        )
        query = self._kernel.server_db_session.query(AffinityRelationDocument).filter(
            AffinityRelationDocument.character_id.in_(here_ids)
        )

        if accepted is not None:
            query = query.filter(AffinityRelationDocument.accepted == accepted)

        if affinity_ids is not None:
            query = query.filter(AffinityRelationDocument.affinity_id.in_(affinity_ids))

        if exclude_character_ids is not None:
            query = query.filter(
                AffinityRelationDocument.character_id.notin_(exclude_character_ids)
            )

        return query.all()

    def count_things_shared_with_affinity(self, character_id: str, affinity_id: int) -> int:
        return (
            self._kernel.resource_lib.get_base_query(
                carried_by_id=character_id, shared_with_affinity_ids=[affinity_id]
            ).count()
            + self._kernel.stuff_lib.get_base_query(
                carried_by_id=character_id, shared_with_affinity_ids=[affinity_id]
            ).count()
        )

    def get_rel_str(self, relation: AffinityRelationDocument) -> str:
        rel_str = ""

        if relation.accepted:
            rel_str = dict(json.loads(relation.affinity.statuses))[relation.status_id]
        elif relation.rejected:
            rel_str = "Quitté"
        elif relation.disallowed:
            rel_str = "Exclu"
        elif relation.request:
            rel_str = "Demandé"
        elif not relation.accepted and not relation.request and not relation.fighter:
            rel_str = "Plus de lien"

        if relation.fighter:
            if rel_str:
                rel_str = f"{rel_str}, Combattant"
            else:
                rel_str = "Combattant"

        return rel_str
