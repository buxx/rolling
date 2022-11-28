import datetime
import json
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query
import typing

from rolling.log import server_logger
from rolling.model.build import ZoneBuildModelContainer
from rolling.model.event import NewBuildData
from rolling.model.event import WebSocketEvent
from rolling.model.event import ZoneEventType
from rolling.model.meta import TransportType
from rolling.server.document.build import DOOR_MODE__CLOSED
from rolling.server.document.build import DOOR_MODE__CLOSED_EXCEPT_FOR
from rolling.server.document.build import DOOR_TYPE__SIMPLE
from rolling.server.document.build import DoorDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class DoorLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def get_door_relations_query(self, build_id: int) -> Query:
        query = self._kernel.server_db_session.query(DoorDocument).filter(
            DoorDocument.build_id == build_id,
        )

        return query

    def get_character_relations_query(self, character_id: str) -> Query:
        query = self._kernel.server_db_session.query(DoorDocument).filter(
            DoorDocument.character_id == character_id,
        )

        return query

    def get_character_with_door_relation_query(
        self, character_id: str, build_id: int
    ) -> Query:
        return self._kernel.server_db_session.query(DoorDocument).filter(
            DoorDocument.character_id == character_id,
            DoorDocument.build_id == build_id,
        )

    def get_character_with_door_relation(
        self, character_id: str, build_id: int
    ) -> DoorDocument:
        return self.get_character_with_door_relation_query(
            character_id=character_id,
            build_id=build_id,
        ).one()

    def get_relation_description(self, character_id: str, build_id: int) -> str:
        relation: typing.Optional[DoorDocument] = None
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        try:
            relation = self.get_character_with_door_relation(
                character_id=character_id, build_id=build_id
            )
        except NoResultFound:
            pass

        if relation is None:
            return "Vous ne vous préoccupez pas de cette porte pour le moment."

        if build_description.door_type == DOOR_TYPE__SIMPLE:
            if relation.mode == DOOR_MODE__CLOSED:
                return "Vous gardez cette porte close pour quiconque"
            elif relation.mode == DOOR_MODE__CLOSED_EXCEPT_FOR:
                affinity_ids = json.loads(relation.affinity_ids)
                affinity_names = self._kernel.affinity_lib.get_affinity_names(
                    affinity_ids=affinity_ids,
                    ignore_not_found=True,
                )
                return (
                    "Vous gardez cette porte close pour les personnes étrangères à : "
                    f"{', '.join(affinity_names)}."
                )
            else:
                raise NotImplementedError()
        else:
            raise NotImplementedError()

    def get_is_access_locked_for_rule(
        self,
        build_id: int,
        character_id: str,
    ) -> typing.Optional[DoorDocument]:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        rules: typing.List[DoorDocument] = (
            self.get_door_relations_query(build_id)
            .order_by(DoorDocument.updated_datetime.asc())
            .all()
        )
        character_affinity_ids = [
            affinity.id
            for affinity in self._kernel.affinity_lib.get_accepted_affinities_docs(
                character_id=character_id,
            )
        ]

        if build_doc.under_construction:
            return None

        if build_description.door_type == DOOR_TYPE__SIMPLE:
            for rule in rules:
                # Ignore rule if character is not in zone or vulnerable
                rule_character = self._kernel.character_lib.get(
                    rule.character_id, dead=None
                )
                rule_character_is_here = (
                    build_doc.world_row_i == rule_character.world_row_i
                    and build_doc.world_col_i == rule_character.world_col_i
                )
                if (
                    not rule_character_is_here
                    or not rule_character.alive
                    or rule_character.vulnerable
                ):
                    continue

                # If door is simply closed and character_id is not the author, door is closed
                if rule.mode == DOOR_MODE__CLOSED:
                    if rule.character_id == character_id:
                        return None
                    return rule

                # If door is closed for non affinities members ...
                elif rule.mode == DOOR_MODE__CLOSED_EXCEPT_FOR:
                    rule_affinity_ids = json.loads(rule.affinity_ids)
                    for character_affinity_id in character_affinity_ids:
                        if character_affinity_id in rule_affinity_ids:
                            # character is in allowed affinities
                            return None
                    # character is not in allowed affinities
                    return rule
                else:
                    raise NotImplementedError()
        else:
            raise NotImplementedError()

        return None

    def is_access_locked_for(
        self,
        build_id: int,
        character_id: str,
    ) -> bool:
        return (
            self.get_is_access_locked_for_rule(
                build_id=build_id, character_id=character_id
            )
            is not None
        )

    def get_is_access_locked_for_description(
        self,
        build_id: int,
        character_id: str,
    ) -> str:
        rule = self.get_is_access_locked_for_rule(
            build_id=build_id, character_id=character_id
        )

        if rule is None:
            return "Cette porte ne vous est pas fermé"

        rule_character = self._kernel.character_lib.get(rule.character_id)
        return f"Cette porte vous est fermé par {rule_character.name}"

    def update(
        self,
        character_id: str,
        build_id: int,
        new_mode: typing.Optional[str] = None,
        new_affinity_ids: typing.Optional[typing.List[int]] = None,
        commit: bool = True,
    ) -> None:
        try:
            relation = self.get_character_with_door_relation(
                character_id=character_id, build_id=build_id
            )
        except NoResultFound:
            # Door character rule is waiting if door is locked
            relation = DoorDocument(
                character_id=character_id,
                build_id=build_id,
            )

        if new_mode is not None:
            relation.mode = new_mode

        if new_affinity_ids is not None:
            relation.affinity_ids = json.dumps(new_affinity_ids)

        relation.updated_datetime = datetime.datetime.utcnow()
        self._kernel.server_db_session.add(relation)
        if commit:
            self._kernel.server_db_session.commit()

    async def trigger_character_enter_in_zone(
        self,
        character_id: str,
        world_row_i: int,
        world_col_i: int,
        commit: bool = True,
    ) -> None:
        """When character enter in zone, update door rules to indicate character want to apply
        again his rules. Current zone websocket clients must receive new version of door builds"""
        rule: DoorDocument
        for rule in self.get_character_relations_query(character_id=character_id):
            build_doc = self._kernel.build_lib.get_build_doc(rule.build_id)
            # Manage only rule on same zone
            if (
                build_doc.world_row_i == world_row_i
                and build_doc.world_col_i == world_col_i
            ):
                # Update updated_datetime field permit to indicate character want to apply his rule
                # but other characters rules are now prior
                rule.updated_datetime = datetime.datetime.utcnow()
                self._kernel.server_db_session.add(rule)

        if commit:
            self._kernel.server_db_session.commit()

        await self.compute_and_send_builds_to_current_sockets(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
        )

    async def trigger_character_left_zone(
        self,
        character_id: str,
        world_row_i: int,
        world_col_i: int,
    ) -> None:
        """When character left zone, his door rules don't apply anymore. Current zone websocket
        clients must receive new version of door builds"""
        await self.compute_and_send_builds_to_current_sockets(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
        )

    async def trigger_character_change_rule(
        self, character_id: str, build_id: int
    ) -> None:
        """When character change door rule, clients must receive new version of door builds"""
        character_doc = self._kernel.character_lib.get_document(id_=character_id)
        # TODO: Optimisation could be filter of door_id ...
        await self.compute_and_send_builds_to_current_sockets(
            world_row_i=character_doc.world_row_i,
            world_col_i=character_doc.world_col_i,
        )

    async def compute_and_send_builds_to_current_sockets(
        self, world_row_i: int, world_col_i: int
    ) -> None:
        door_builds = self._kernel.build_lib.get_zone_build(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            is_door=True,
        )
        for socket in self._kernel.server_zone_events_manager.get_sockets(
            row_i=world_row_i,
            col_i=world_col_i,
        ):
            character_id = (
                self._kernel.server_zone_events_manager.get_character_id_for_socket(
                    socket
                )
            )
            for door_build in door_builds:
                build_description = self._kernel.game.config.builds[door_build.build_id]
                build_container = ZoneBuildModelContainer(
                    doc=door_build, desc=build_description
                )
                build_container.traversable = {
                    TransportType.WALKING: not self._kernel.door_lib.is_access_locked_for(
                        build_id=door_build.id,
                        character_id=character_id,
                    )
                }
                event = WebSocketEvent(
                    type=ZoneEventType.NEW_BUILD,
                    world_row_i=world_row_i,
                    world_col_i=world_col_i,
                    data=NewBuildData(build=build_container),
                )
                event_str = self._kernel.event_serializer_factory.get_serializer(
                    event.type
                ).dump_json(event)
                try:
                    await socket.send_str(event_str)
                except ConnectionResetError as exc:
                    server_logger.debug(exc)
                except Exception:
                    server_logger.exception(
                        "Error when compute and send builds to current sockets"
                    )

    def delete(self, character_id: str, build_id: int) -> None:
        try:
            relation = self.get_character_with_door_relation_query(
                character_id=character_id, build_id=build_id
            ).one()
            self._kernel.server_db_session.delete(relation)
            self._kernel.server_db_session.commit()
        except NoResultFound:
            pass
