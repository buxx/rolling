# coding: utf-8
import typing

from sqlalchemy.orm import Query

from rolling.server.document.message import MessageDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class MessageLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def _get_character_messages_query(self, character_id: str, zone: bool = False) -> Query:
        query = self._kernel.server_db_session.query(MessageDocument).filter(
            MessageDocument.character_id == character_id
        )

        if zone:
            query = query.filter(MessageDocument.zone == zone)

        return query

    def get_character_zone_messages(self, character_id: str) -> typing.List[MessageDocument]:
        return (
            self._get_character_messages_query(character_id, zone=True)
            .order_by(MessageDocument.datetime.desc())
            .all()
        )

    def mark_character_zone_messages_as_read(self, character_id: str) -> None:
        self._get_character_messages_query(character_id, zone=True).filter(
            MessageDocument.read == False
        ).update({MessageDocument.read: True})

    def mark_character_conversation_messages_as_read(
        self, character_id: str, conversation_id: int
    ) -> None:
        self._get_character_messages_query(character_id, zone=False).filter(
            MessageDocument.read == False, MessageDocument.first_message == conversation_id
        ).update({MessageDocument.read: True})

    def get_last_character_zone_messages(
        self, character_id: str, zone: bool = False
    ) -> MessageDocument:
        return (
            self._get_character_messages_query(character_id, zone=zone)
            .order_by(MessageDocument.datetime.desc())
            .limit(1)
            .one()
        )

    def add_zone_message(
        self, character_id: str, message: str, zone_row_i: int, zone_col_i: int, commit: bool = True
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
                    read=author_doc.id == zone_character.id,
                    zone=True,
                    zone_row_i=zone_row_i,
                    zone_col_i=zone_col_i,
                    concerned=zone_characters_ids,
                )
            )

        if commit:
            self._kernel.server_db_session.commit()

    def add_conversation_message(
        self,
        author_id: str,
        subject: str,
        message: str,
        concerned: typing.List[str],
        conversation_id: typing.Optional[int] = None,
    ) -> None:
        author_doc = self._kernel.character_lib.get_document(author_id)
        concerned = [author_id] + concerned
        messages = []
        for character_id in set(concerned):
            message_obj = MessageDocument(
                subject=subject,
                text=message,
                character_id=character_id,
                author_id=author_id,
                author_name=author_doc.name,
                read=author_doc.id == character_id,
                zone=False,
                concerned=concerned,
                first_message=conversation_id,
            )
            messages.append(message_obj)
            self._kernel.server_db_session.add(message_obj)

        self._kernel.server_db_session.commit()

        if not conversation_id:
            first_message = messages[0]

            for message in messages:
                message.first_message = first_message.id

            self._kernel.server_db_session.commit()

    def get_conversation_first_messages(self, character_id: str) -> typing.List[MessageDocument]:
        # FIXME BS: order by last message
        return (
            self._get_character_messages_query(character_id, zone=False)
            .group_by(MessageDocument.first_message)
            .order_by(MessageDocument.datetime.desc())
            .all()
        )

    def get_conversation_messages(
        self, character_id: str, conversation_id: int
    ) -> typing.List[MessageDocument]:
        return (
            self._get_character_messages_query(character_id, zone=False)
            .filter(MessageDocument.first_message == conversation_id)
            .order_by(MessageDocument.datetime.desc())
            .all()
        )
