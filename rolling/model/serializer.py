# coding: utf-8
import typing

import serpyco

from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.model.event import zone_event_data_types


class ZoneEventSerializerFactory(object):
    serializers: typing.Dict[ZoneEventType, serpyco.Serializer] = {}
    for zone_event_type, zone_event_data_type in zone_event_data_types.items():
        serializers[zone_event_type] = serpyco.Serializer(
            ZoneEvent[zone_event_data_type]
        )

    def get_serializer(self, zone_event_data_type: ZoneEventType) -> serpyco.Serializer:
        return self.serializers[zone_event_data_type]
