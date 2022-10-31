# coding: utf-8
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import NoResultFound
from aiohttp import web
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
        self,
        character_id: str,
        zone: typing.Optional[bool] = None,
        select=MessageDocument,
    ) -> Query:
        query = self._kernel.server_db_session.query(select).filter(
            MessageDocument.character_id == character_id
        )

        if zone is not None:
            query = query.filter(MessageDocument.zone == zone)

        return query

    def get_character_zone_messages(
        self,
        character_id: str,
        message_count: typing.Optional[int] = None,
        order=MessageDocument.datetime.desc(),
    ) -> typing.List[MessageDocument]:
        query = self._get_character_messages_query(character_id, zone=True).order_by(
            order
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
            MessageDocument.read == False,
            MessageDocument.first_message == conversation_id,
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

    # FIXME : delete this view by conversation reforming
    async def add_zone_message(
        self,
        character_id: str,
        message: str,
        # FIXME BS : rename these param ton world_row_i and world_col_i
        zone_row_i: int,
        zone_col_i: int,
        commit: bool = True,
    ) -> None:
        if not message.strip():
            return

        author_doc = self._kernel.character_lib.get_document(character_id)
        zone_characters = self._kernel.character_lib.get_zone_characters(
            row_i=zone_row_i, col_i=zone_col_i
        )
        active_zone_characters_ids = (
            self._kernel.server_zone_events_manager.get_active_zone_characters_ids(
                author_doc.world_row_i, author_doc.world_col_i
            )
        )
        zone_characters_ids = [c.id for c in zone_characters]
        for zone_character in zone_characters:
            self._kernel.server_db_session.add(
                MessageDocument(
                    text=message,
                    character_id=zone_character.id,
                    author_id=character_id,
                    author_name=author_doc.name,
                    read=author_doc.id == zone_character.id
                    or zone_character.id in active_zone_characters_ids,
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

    # FIXME : delete this view by conversation reforming
    async def add_conversation_message(
        self,
        author_id: str,
        subject: str,
        message: str,
        concerned: typing.List[str],
        conversation_id: typing.Optional[int] = None,
        is_first_message: bool = False,
        filter_by_same_zone_than_author: bool = False,
    ) -> int:
        author_doc = self._kernel.character_lib.get_document(author_id)
        concerned = list(set([author_id] + concerned))
        messages = []
        active_zone_characters_ids = (
            self._kernel.server_zone_events_manager.get_active_zone_characters_ids(
                author_doc.world_row_i, author_doc.world_col_i
            )
        )
        for character_id in set(concerned):
            if filter_by_same_zone_than_author:
                character_doc = self._kernel.character_lib.get_document(character_id)
                if (
                    character_doc.world_row_i != author_doc.world_row_i
                    or character_doc.world_col_i != author_doc.world_col_i
                ):
                    continue

            message_obj = MessageDocument(
                subject=subject,
                text=message,
                character_id=character_id,
                author_id=author_id,
                author_name=author_doc.name,
                read=author_doc.id == character_id
                or character_id in active_zone_characters_ids,
                zone=False,
                concerned=concerned,
                first_message=conversation_id,
                is_first_message=is_first_message,
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

    async def send_character_chat_message(
        self,
        world_row_i: int,
        world_col_i: int,
        message: str,
        character_id: str,
        only_to: typing.Optional[web.WebSocketResponse] = None,
        to_character_ids: typing.Optional[typing.List[str]] = None,
    ) -> None:
        event = WebSocketEvent(
            type=ZoneEventType.NEW_CHAT_MESSAGE,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            data=NewChatMessageData.new_character(
                character_id=character_id,
                message=message,
            ),
        )
        await self._send_chat_message(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            message=message,
            event=event,
            only_to=only_to,
            to_character_ids=to_character_ids,
        )

    async def send_system_chat_message(
        self,
        world_row_i: int,
        world_col_i: int,
        message: str,
        silent: bool,
        only_to: typing.Optional[web.WebSocketResponse] = None,
        to_character_ids: typing.Optional[typing.List[str]] = None,
    ) -> None:
        event = WebSocketEvent(
            type=ZoneEventType.NEW_CHAT_MESSAGE,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            data=NewChatMessageData.new_system(
                message=message,
                silent=silent,
            ),
        )
        await self._send_chat_message(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            event=event,
            only_to=only_to,
            to_character_ids=to_character_ids,
        )

    async def _send_chat_message(
        self,
        world_row_i: int,
        world_col_i: int,
        event: WebSocketEvent,
        only_to: typing.Optional[web.WebSocketResponse] = None,
        to_character_ids: typing.Optional[typing.List[str]] = None,
    ) -> None:
        if only_to is not None:
            await only_to.send_str(
                self._kernel.event_serializer_factory.get_serializer(
                    ZoneEventType.NEW_CHAT_MESSAGE
                ).dump_json(event)
            )
        else:
            await self._kernel.send_to_zone_sockets(
                row_i=world_row_i,
                col_i=world_col_i,
                event=event,
                to_character_ids=to_character_ids,
            )

    async def send_new_message_events(
        self,
        world_row_i: int,
        world_col_i: int,
        author_id: str,
        message: str,
        conversation_id: typing.Optional[int] = None,
        concerned: typing.Optional[typing.List[str]] = None,
    ) -> None:
        event = WebSocketEvent(
            type=ZoneEventType.NEW_CHAT_MESSAGE,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            data=NewChatMessageData(
                character_id=author_id, message=message, conversation_id=conversation_id
            ),
        )

        await self._kernel.server_zone_events_manager.send_to_sockets(
            event,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            character_ids=concerned,
        )

    def get_conversation_first_messages(
        self, character_id: str, with_character_id: typing.Optional[str] = None
    ) -> typing.List[MessageDocument]:
        return self.get_conversation_first_messages_query(
            character_id=character_id, with_character_id=with_character_id
        ).all()

    def get_conversation_first_messages_query(
        self,
        character_id: str,
        with_character_id: typing.Optional[str] = None,
        order_by=MessageDocument.datetime.asc(),
        select=MessageDocument,
    ) -> Query:
        query = (
            self._get_character_messages_query(character_id, zone=False, select=select)
            .filter(MessageDocument.is_first_message == True)
            .order_by(order_by)
        )

        if with_character_id:
            query = query.filter(
                cast(MessageDocument.concerned, String).contains(with_character_id)
            )

        return query

    def get_conversation_messages(
        self,
        character_id: str,
        conversation_id: int,
        message_count: typing.Optional[int] = None,
        order=MessageDocument.datetime.desc(),
    ) -> typing.List[MessageDocument]:
        query = (
            self._get_character_messages_query(character_id, zone=False)
            .filter(MessageDocument.first_message == conversation_id)
            .order_by(order)
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
        # Message for which stay in left zone
        await self.send_system_chat_message(
            world_row_i=from_world_row_i,
            world_col_i=from_world_col_i,
            message=f"{character.name} a quitté la zone",
            silent=False,
        )
        # Message for which are here in arrival zone
        await self.send_system_chat_message(
            world_row_i=to_world_row_i,
            world_col_i=to_world_col_i,
            message=f"{character.name} a rejoint la zone",
            silent=False,
        )

    def get_next_conversation_id(
        self, character_id: str, conversation_id: typing.Optional[int]
    ) -> int:
        query = self.get_conversation_first_messages_query(
            character_id=character_id, order_by=MessageDocument.datetime.asc()
        )

        if conversation_id is not None:
            query = query.filter(MessageDocument.first_message > conversation_id)

        return query.limit(1).one().first_message

    def get_previous_conversation_id(
        self, character_id: str, conversation_id: typing.Optional[int]
    ) -> int:
        query = self.get_conversation_first_messages_query(
            character_id=character_id, order_by=MessageDocument.datetime.desc()
        )

        if conversation_id is not None:
            query = query.filter(MessageDocument.first_message < conversation_id)

        return query.limit(1).one().first_message

    def search_conversation_first_message_for_concerned(
        self, character_id: str, concerned: typing.List[str]
    ) -> typing.Optional[int]:
        for message in self.get_conversation_first_messages(character_id):
            if all([concern in message.concerned for concern in concerned]):
                return message.first_message or message.id
        return None
