# coding: utf-8
import abc
import typing

from rolling.log import gui_logger
from rolling.model.event import PlayerMoveData
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.gui.controller import Controller


class EventProcessor(metaclass=abc.ABCMeta):
    def __init__(self, kernel: "Kernel", controller: "Controller") -> None:
        self._kernel = kernel
        self._controller = controller

    async def process(self, event: ZoneEvent) -> None:
        self._check(event)
        await self._process(event)

    def _check(self, event: ZoneEvent) -> None:
        pass

    @abc.abstractmethod
    async def _process(self, event: ZoneEvent) -> None:
        pass


class PlayerMoveProcessor(EventProcessor):
    async def _process(self, event: ZoneEvent[PlayerMoveData]) -> None:
        gui_logger.debug(
            f"Receive {event.type} event for character {event.data.character_id}"
        )

        if self._controller.player_character.id == event.data.character_id:
            gui_logger.debug(f"Move event of current player character: ignore")
            return

        try:
            character_display_object = self._controller._display_objects_manager.objects_by_ids[
                event.data.character_id
            ]
            character_display_object.row_i = event.data.to_row_i
            character_display_object.col_i = event.data.to_col_i
            self._controller._display_objects_manager.refresh_indexes()
        except KeyError:
            # FIXME BS 2019-01-23: character can be added just yet. This must be avoided when
            # new character event will be managed
            pass


class EventProcessorFactory:
    def __init__(self, kernel: "Kernel", controller: "Controller") -> None:
        self._processors: typing.Dict[ZoneEventType, EventProcessor] = {}

        for zone_event_type, processor_type in [
            (ZoneEventType.PLAYER_MOVE, PlayerMoveProcessor)
        ]:
            self._processors[zone_event_type] = processor_type(kernel, controller)

    def get_processor(self, zone_event_type: ZoneEventType) -> EventProcessor:
        return self._processors[zone_event_type]
