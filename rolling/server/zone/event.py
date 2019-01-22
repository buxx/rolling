# coding: utf-8
import abc
import typing

import serpyco

from rolling.log import server_logger
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.model.event import zone_event_data_types

if typing.TYPE_CHECKING:
    from rolling.server.zone.websocket import ZoneEventsManager


class EventProcessor(metaclass=abc.ABCMeta):
    def __init__(self, zone_events_manager: "ZoneEventsManager") -> None:
        self._zone_events_manager = zone_events_manager

    @abc.abstractmethod
    async def process(self, row_i: int, col_i: int, event: ZoneEvent) -> None:
        pass


class PlayerMoveProcessor(EventProcessor):
    async def process(self, row_i: int, col_i: int, event: ZoneEvent) -> None:
        for socket in self._zone_events_manager.get_sockets(row_i, col_i):
            # TODO BS 2019-01-22: Prepare all these serializer to improve performances
            data_type = zone_event_data_types[event.type]
            serializer = serpyco.Serializer(ZoneEvent[data_type])

            event_str = serializer.dump_json(event)
            server_logger.debug(f"Send event on socket: {event_str}")
            await socket.send_str(event_str)


class EventProcessorFactory(object):
    def __init__(self, zone_events_manager: "ZoneEventsManager") -> None:
        self._processors: typing.Dict[ZoneEventType, EventProcessor] = {}

        for zone_event_type, processor_type in [
            (ZoneEventType.PLAYER_MOVE, PlayerMoveProcessor)
        ]:
            self._processors[zone_event_type] = processor_type(zone_events_manager)

    def get_processor(self, zone_event_type: ZoneEventType) -> EventProcessor:
        return self._processors[zone_event_type]
