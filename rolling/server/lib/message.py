# coding: utf-8
import typing

from sqlalchemy.orm import Query

from rolling.server.document.message import MessageDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class MessageLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def _get_character_zone_messages_query(self, character_id: str, zone: bool = False) -> Query:
        query = self._kernel.server_db_session.query(MessageDocument).filter(
            MessageDocument.character_id == character_id
        )

        if zone:
            query.filter(MessageDocument.zone_row_i != None, MessageDocument.zone_col_i != None)

        return query

    def get_character_zone_messages(
        self, character_id: str, zone: bool = False
    ) -> typing.List[MessageDocument]:
        return (
            self._get_character_zone_messages_query(character_id, zone=zone)
            .order_by(MessageDocument.datetime.desc())
            .all()
        )

    def mark_character_zone_messages_as_read(self, character_id: str, zone: bool = False) -> None:
        self._get_character_zone_messages_query(character_id, zone=zone).filter(
            MessageDocument.read == False
        ).update({MessageDocument.read: True})

    def get_last_character_zone_messages(
        self, character_id: str, zone: bool = False
    ) -> MessageDocument:
        return (
            self._get_character_zone_messages_query(character_id, zone=zone)
            .order_by(MessageDocument.datetime.desc())
            .limit(1)
            .one()
        )

    def add_message(
        self,
        character_id: str,
        message: str,
        zone_row_i: int,
        zone_col_i: int,
        commit: bool = True,
        is_outzone_message: bool = False,
    ) -> None:
        author_doc = self._kernel.character_lib.get_document(character_id)
        zone_characters = self._kernel.character_lib.get_zone_players(
            row_i=zone_row_i, col_i=zone_col_i
        )
        zone_characters_ids = [c.id for c in zone_characters]
        for zone_character in zone_characters:
            self._kernel.server_db_session.add(
                MessageDocument(
                    text=message,
                    character_id=zone_character.id,
                    author_id=character_id,
                    author_name=author_doc.name,
                    read=False,
                    zone_row_i=zone_row_i,
                    zone_col_i=zone_col_i,
                    concerned=zone_characters_ids,
                )
            )

        if commit:
            self._kernel.server_db_session.commit()
