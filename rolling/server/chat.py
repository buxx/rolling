import typing

from rolling.model.event import NewChatMessageData, WebSocketEvent, ZoneEventType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class LiveChatOperator:
    """Class to instantiate and use to deal with received chat messages"""

    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    async def received_message(self, character_id: str, message: str) -> None:
        """Broadcast received character message on correct roads"""
        world_row_i, world_col_i = self._kernel.character_lib.get_world_coordinates(
            character_id
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
