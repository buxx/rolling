# coding: utf-8
from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import NoResultFound
import typing

from rolling.model.character import CharacterModel
from rolling.server.document.character import CharacterDocument
from rolling.server.document.message import MessageDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class MessageLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def _get_character_messages_query(
        self, character_id: str, zone: typing.Optional[bool] = None
    ) -> Query:
        query = self._kernel.server_db_session.query(MessageDocument).filter(
            MessageDocument.character_id == character_id
        )

        if zone is not None:
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
        zone_characters = self._kernel.character_lib.get_zone_characters(
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
    ) -> int:
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
            return first_message.id
        return conversation_id

    def get_conversation_first_messages(
        self, character_id: str, with_character_id: typing.Optional[str] = None
    ) -> typing.List[MessageDocument]:
        query = (
            self._get_character_messages_query(character_id, zone=False)
            .group_by(MessageDocument.first_message)
            .order_by(MessageDocument.datetime.asc())
        )

        if with_character_id:
            query = query.filter(MessageDocument.concerned.contains(with_character_id))

        return query.all()

    def get_conversation_messages(
        self, character_id: str, conversation_id: int
    ) -> typing.List[MessageDocument]:
        return (
            self._get_character_messages_query(character_id, zone=False)
            .filter(MessageDocument.first_message == conversation_id)
            .order_by(MessageDocument.datetime.desc())
            .all()
        )

    def send_messages_due_to_move(
        self,
        character: CharacterModel,
        from_world_row_i: int,
        from_world_col_i: int,
        to_world_row_i: int,
        to_world_col_i: int,
    ) -> None:
        # Zone message
        try:
            last_character_message = self._kernel.message_lib.get_last_character_zone_messages(
                character_id=character.id, zone=True
            )
            if not last_character_message.is_outzone_message:
                self._kernel.server_db_session.add(
                    MessageDocument(
                        text="Vous avez changé de zone",
                        character_id=character.id,
                        author_id=character.id,
                        author_name=character.name,
                        read=True,
                        zone_row_i=character.zone_row_i,
                        zone_col_i=character.zone_col_i,
                        concerned=[character.id],
                        is_outzone_message=True,
                        zone=True,
                        subject=last_character_message.subject,
                    )
                )
        except NoResultFound:
            pass

        # TODO BS: limit active conversations ?
        # conversations
        for (message_id, concerned, subject) in (
            self._kernel.server_db_session.query(
                MessageDocument.first_message, MessageDocument.concerned, MessageDocument.subject
            )
            .filter(MessageDocument.concerned.contains(character.id))
            .group_by(MessageDocument.first_message)
            .all()
        ):
            left_names = []
            for (before_character_id, before_character_name) in (
                self._kernel.server_db_session.query(CharacterDocument.id, CharacterDocument.name)
                .filter(
                    CharacterDocument.world_row_i == from_world_row_i,
                    CharacterDocument.world_col_i == from_world_col_i,
                    CharacterDocument.id.in_(set(concerned) - {character.id}),
                )
                .order_by(CharacterDocument.name)
                .all()
            ):
                left_names.append(before_character_name)
                self._kernel.server_db_session.add(
                    MessageDocument(
                        text=f"{character.name} n'est plus là pour parler",
                        character_id=before_character_id,
                        author_id=character.id,
                        author_name=character.name,
                        read=True,
                        concerned=concerned,
                        is_outzone_message=True,
                        zone=False,
                        first_message=message_id,
                        subject=subject,
                    )
                )

            if left_names:
                left_names_str = ", ".join(left_names)
                self._kernel.server_db_session.add(
                    MessageDocument(
                        text=f"Vous etes partis et ne pouvez plus parler avec {left_names_str}",
                        character_id=character.id,
                        author_id=character.id,
                        author_name=character.name,
                        read=True,
                        concerned=concerned,
                        is_outzone_message=True,
                        zone=False,
                        first_message=message_id,
                        subject=subject,
                    )
                )

            after_names = []
            for (after_character_id, after_character_name) in (
                self._kernel.server_db_session.query(CharacterDocument.id, CharacterDocument.name)
                .filter(
                    CharacterDocument.world_row_i == to_world_row_i,
                    CharacterDocument.world_col_i == to_world_col_i,
                    CharacterDocument.id.in_(set(concerned) - {character.id}),
                )
                .order_by(CharacterDocument.name)
                .all()
            ):
                after_names.append(after_character_name)
                self._kernel.server_db_session.add(
                    MessageDocument(
                        text=f"{character.name} vous à rejoin",
                        character_id=after_character_id,
                        author_id=character.id,
                        author_name=character.name,
                        read=True,
                        concerned=concerned,
                        is_outzone_message=True,
                        zone=False,
                        first_message=message_id,
                        subject=subject,
                    )
                )

            if after_names:
                after_names_str = ", ".join(after_names)
                self._kernel.server_db_session.add(
                    MessageDocument(
                        text=f"Vous avez rejoins {after_names_str}",
                        character_id=character.id,
                        author_id=character.id,
                        author_name=character.name,
                        read=True,
                        concerned=concerned,
                        is_outzone_message=True,
                        zone=False,
                        first_message=message_id,
                        subject=subject,
                    )
                )
