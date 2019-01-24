# coding: utf-8
import abc
import typing

import serpyco

from rolling.log import server_logger
from rolling.model.event import PlayerMoveData
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.model.event import zone_event_data_types
from rolling.server.lib.character import CharacterLib

if typing.TYPE_CHECKING:
    from rolling.server.zone.websocket import ZoneEventsManager
    from rolling.kernel import Kernel


class EventProcessor(metaclass=abc.ABCMeta):
    def __init__(
        self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager"
    ) -> None:
        self._zone_events_manager = zone_events_manager
        self._kernel = kernel

    async def process(self, row_i: int, col_i: int, event: ZoneEvent) -> None:
        self._check(row_i, col_i, event)
        await self._process(row_i, col_i, event)

    def _check(self, row_i: int, col_i: int, event: ZoneEvent) -> None:
        pass

    @abc.abstractmethod
    async def _process(self, row_i: int, col_i: int, event: ZoneEvent) -> None:
        pass


class PlayerMoveProcessor(EventProcessor):
    def __init__(
        self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager"
    ) -> None:
        super().__init__(kernel, zone_events_manager)
        self._character_lib = CharacterLib(self._kernel)

    async def _process(
        self, row_i: int, col_i: int, event: ZoneEvent[PlayerMoveData]
    ) -> None:
        # TODO BS 2019-01-23: Check what move is possible (tile can be a rock, or water ...)
        # TODO BS 2019-01-23: Check given character id is authenticated used (security)

        character = self._character_lib.get(event.data.character_id)
        self._character_lib.move_on_zone(
            character, to_row_i=event.data.to_row_i, to_col_i=event.data.to_col_i
        )

        for socket in self._zone_events_manager.get_sockets(row_i, col_i):
            # TODO BS 2019-01-22: Prepare all these serializer to improve performances
            data_type = zone_event_data_types[event.type]
            serializer = serpyco.Serializer(ZoneEvent[data_type])

            event_str = serializer.dump_json(event)
            server_logger.debug(f"Send event on socket: {event_str}")
            await socket.send_str(event_str)


class EventProcessorFactory(object):
    def __init__(
        self, kernel: "Kernel", zone_events_manager: "ZoneEventsManager"
    ) -> None:
        self._processors: typing.Dict[ZoneEventType, EventProcessor] = {}

        for zone_event_type, processor_type in [
            (ZoneEventType.PLAYER_MOVE, PlayerMoveProcessor)
        ]:
            self._processors[zone_event_type] = processor_type(
                kernel, zone_events_manager
            )

    def get_processor(self, zone_event_type: ZoneEventType) -> EventProcessor:
        return self._processors[zone_event_type]
