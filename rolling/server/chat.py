import collections
import time
import typing

from rolling.model.event import NewChatMessageData, WebSocketEvent, ZoneEventType
from rolling.types import (
    CachedMessage,
    MessageAge,
    MessageAuthorId,
    MessageContent,
    MessageTimestamp,
    WorldPoint,
)

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class State:
    def __init__(self, max_age: MessageAge) -> None:
        self._max_age = max_age
        self._messages: typing.DefaultDict[
            WorldPoint,
            typing.List[CachedMessage],
        ] = collections.defaultdict(list)

    def add_message(
        self,
        world_point: WorldPoint,
        author_id: MessageAuthorId,
        message: MessageContent,
    ) -> None:
        self._messages[world_point].append(
            CachedMessage(time.time(), author_id, message)
        )

    def messages(self, world_point: WorldPoint) -> typing.List[CachedMessage]:
        """Return not too old messages for world point and drop older"""
        now = int(time.time())
        zone_messages = self._messages[world_point]
        zone_messages = [
            message
            for message in zone_messages
            if (now - message.timestamp) < self._max_age
        ]
        return zone_messages


class LiveChatOperator:
    """Class to instantiate and use to deal with received chat messages"""

    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    async def received_message(self, character_id: str, message: str) -> None:
        """Broadcast received character message on correct roads"""
        world_row_i, world_col_i = self._kernel.character_lib.get_world_coordinates(
            character_id
        )

        self._kernel.chat_state.add_message(
            WorldPoint((world_row_i, world_col_i)),
            character_id,
            message,
        )

        event = WebSocketEvent(
            type=ZoneEventType.NEW_CHAT_MESSAGE,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            data=NewChatMessageData.new_character(
                character_id=character_id,
                message=message,
            ),
        )
        await self._kernel.server_zone_events_manager.send_to_sockets(
            event,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
        )
