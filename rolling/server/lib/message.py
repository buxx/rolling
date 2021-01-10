# coding: utf-8
from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import NoResultFound
import typing

from rolling.log import server_logger
from rolling.model.character import CharacterModel
from rolling.model.event import NewChatMessageData
from rolling.model.event import WebSocketEvent
from rolling.model.event import ZoneEventType
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

    def get_character_zone_messages(self, character_id: str,  message_count: typing.Optional[int] = None) -> typing.List[MessageDocument]:
        query = (
            self._get_character_messages_query(character_id, zone=True)
            .order_by(MessageDocument.datetime.desc())
        )
        if message_count is not None:
            query = query.limit(message_count)
        return query.all()

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

    async def add_zone_message(
        self, character_id: str, message: str, zone_row_i: int, zone_col_i: int, commit: bool = True
    ) -> None:
        if not message.strip():
            return

        author_doc = self._kernel.character_lib.get_document(character_id)
        zone_characters = self._kernel.character_lib.get_zone_characters(
            row_i=zone_row_i, col_i=zone_col_i
        )
        active_zone_characters_ids = self._kernel.server_zone_events_manager.get_active_zone_characters_ids(
            author_doc.world_row_i, author_doc.world_col_i
        )
        zone_characters_ids = [c.id for c in zone_characters]
        for zone_character in zone_characters:
            self._kernel.server_db_session.add(
                MessageDocument(
                    text=message,
                    character_id=zone_character.id,
                    author_id=character_id,
                    author_name=author_doc.name,
                    read=author_doc.id == zone_character.id or zone_character.id in active_zone_characters_ids,
                    zone=True,
                    zone_row_i=zone_row_i,
                    zone_col_i=zone_col_i,
                    concerned=zone_characters_ids,
                )
            )

        if commit:
            self._kernel.server_db_session.commit()

        await self.send_new_message_events(
            world_row_i=author_doc.world_row_i,
            world_col_i=author_doc.world_col_i,
            author_id=character_id,
            message=f"{author_doc.name}: {message}",
        )

    def get_last_conversation_message(self, conversation_id: int) -> MessageDocument:
        return (
            self._kernel.server_db_session.query(MessageDocument)
                .filter(MessageDocument.first_message == conversation_id)
                .order_by(MessageDocument.datetime.desc())
                .limit(1)
                .one()
        )

    async def add_conversation_message(
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
        active_zone_characters_ids = self._kernel.server_zone_events_manager.get_active_zone_characters_ids(
            author_doc.world_row_i, author_doc.world_col_i
        )
        for character_id in set(concerned):
            message_obj = MessageDocument(
                subject=subject,
                text=message,
                character_id=character_id,
                author_id=author_id,
                author_name=author_doc.name,
                read=author_doc.id == character_id or character_id in active_zone_characters_ids,
                zone=False,
                concerned=concerned,
                first_message=conversation_id,
            )
            messages.append(message_obj)
            self._kernel.server_db_session.add(message_obj)

        self._kernel.server_db_session.commit()

        if not conversation_id:
            first_message = messages[0]

            for message_ in messages:
                message_.first_message = first_message.id

            self._kernel.server_db_session.commit()
            conversation_id = first_message.id

        await self.send_new_message_events(
            world_row_i=author_doc.world_row_i,
            world_col_i=author_doc.world_col_i,
            author_id=author_id,
            message=f"{author_doc.name}: {message}",
            conversation_id=conversation_id,
            concerned=concerned,
        )

        return conversation_id

    async def send_new_message_events(
        self,
        world_row_i: int,
        world_col_i: int,
        author_id: str,
        message: str,
        conversation_id: typing.Optional[int] = None,
        concerned: typing.Optional[typing.List[str]] = None,
    ) -> None:
        event_str = self._kernel.event_serializer_factory.get_serializer(
            ZoneEventType.NEW_CHAT_MESSAGE).dump_json(
            WebSocketEvent(
                type=ZoneEventType.NEW_CHAT_MESSAGE,
                world_row_i=world_row_i,
                world_col_i=world_col_i,
                data=NewChatMessageData(
                    character_id=author_id,
                    message=message,
                    conversation_id=conversation_id,
                )
            )
        )
        for socket in self._kernel.server_zone_events_manager.get_sockets(world_row_i, world_col_i):
            if concerned is None or self._kernel.server_zone_events_manager.get_character_id_for_socket(socket) in concerned:
                server_logger.debug(f"Send event on socket: {event_str}")
                try:
                    await socket.send_to_zone_str(event_str)
                except Exception as exc:
                    server_logger.exception(exc)

    def get_conversation_first_messages(
        self, character_id: str, with_character_id: typing.Optional[str] = None
    ) -> typing.List[MessageDocument]:
        return self.get_conversation_first_messages_query(
            character_id=character_id,
            with_character_id=with_character_id
        ).all()

    def get_conversation_first_messages_query(
        self, character_id: str,
        with_character_id: typing.Optional[str] = None,
        order_by=MessageDocument.datetime.asc(),
    ) -> Query:
        query = (
            self._get_character_messages_query(character_id, zone=False)
            .group_by(MessageDocument.first_message)
            .order_by(order_by)
        )

        if with_character_id:
            query = query.filter(MessageDocument.concerned.contains(with_character_id))

        return query

    def get_conversation_messages(
        self, character_id: str, conversation_id: int,  message_count: typing.Optional[int] = None
    ) -> typing.List[MessageDocument]:
        query = (
            self._get_character_messages_query(character_id, zone=False)
            .filter(MessageDocument.first_message == conversation_id)
            .order_by(MessageDocument.datetime.desc())
        )
        if message_count is not None:
            query = query.limit(message_count)
        return query.all()

    async def send_messages_due_to_move(
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

        from_character_ids = self._kernel.character_lib.get_zone_character_ids(
            row_i=from_world_row_i,
            col_i=from_world_col_i,
            alive=True,
        )
        await self.send_new_message_events(
            world_row_i=from_world_row_i,
            world_col_i=from_world_col_i,
            author_id=character.id,
            message=f"{character.name} a quitté la zone",
            concerned=from_character_ids,
        )

        to_character_ids = self._kernel.character_lib.get_zone_character_ids(
            row_i=to_world_row_i,
            col_i=to_world_col_i,
            alive=True,
        )
        await self.send_new_message_events(
            world_row_i=to_world_row_i,
            world_col_i=to_world_col_i,
            author_id=character.id,
            message=f"{character.name} a rejoins la zone",
            concerned=to_character_ids,
        )

        # TODO BS: limit active conversations ?
        # conversations
        for (message_id, concerned, subject) in (
            self._kernel.server_db_session.query(
                MessageDocument.first_message, MessageDocument.concerned, MessageDocument.subject
            )
            .filter(MessageDocument.concerned.contains(character.id))
            .filter(MessageDocument.first_message != None)
            .group_by(MessageDocument.first_message)
            .all()
        ):
            left_names = []
            new_concerned = list(set(concerned) - {character.id})
            message = f"{character.name} n'est plus là pour parler"
            for (before_character_id, before_character_name) in (
                self._kernel.server_db_session.query(CharacterDocument.id, CharacterDocument.name)
                .filter(
                    CharacterDocument.world_row_i == from_world_row_i,
                    CharacterDocument.world_col_i == from_world_col_i,
                    CharacterDocument.id.in_(new_concerned),
                )
                .order_by(CharacterDocument.name)
                .all()
            ):
                left_names.append(before_character_name)
                self._kernel.server_db_session.add(
                    MessageDocument(
                        text=message,
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

            await self.send_new_message_events(
                world_row_i=from_world_row_i,
                world_col_i=from_world_col_i,
                author_id=character.id,
                message=message,
                conversation_id=message_id,
                concerned=concerned,
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
            message = f"{character.name} vous à rejoin"
            new_concerned = list(set(concerned) - {character.id})
            for (after_character_id, after_character_name) in (
                self._kernel.server_db_session.query(CharacterDocument.id, CharacterDocument.name)
                .filter(
                    CharacterDocument.world_row_i == to_world_row_i,
                    CharacterDocument.world_col_i == to_world_col_i,
                    CharacterDocument.id.in_(new_concerned),
                )
                .order_by(CharacterDocument.name)
                .all()
            ):
                after_names.append(after_character_name)
                self._kernel.server_db_session.add(
                    MessageDocument(
                        text=message,
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

            await self.send_new_message_events(
                world_row_i=to_world_row_i,
                world_col_i=to_world_col_i,
                author_id=character.id,
                message=message,
                conversation_id=message_id,
                concerned=new_concerned,
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

    def get_next_conversation_id(self, character_id: str, conversation_id: typing.Optional[int]) -> int:
        query = self.get_conversation_first_messages_query(
            character_id=character_id,
            order_by=MessageDocument.datetime.asc(),
        )

        if conversation_id is not None:
            query = query.filter(MessageDocument.first_message > conversation_id)

        return query.limit(1).one().first_message

    def get_previous_conversation_id(self, character_id: str, conversation_id: typing.Optional[int]) -> int:
        query = self.get_conversation_first_messages_query(
            character_id=character_id,
            order_by=MessageDocument.datetime.desc(),
        )

        if conversation_id is not None:
            query = query.filter(MessageDocument.first_message < conversation_id)

        return query.limit(1).one().first_message
