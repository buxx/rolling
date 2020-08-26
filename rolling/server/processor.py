# coding: utf-8
from hapic.processor.serpyco import SerpycoProcessor
import typing

from guilang.description import Description


class RollingSerpycoProcessor(SerpycoProcessor):
    def dump(self, data: typing.Any) -> typing.Any:
        if data.__class__.__name__ == "Description":
            data = typing.cast(Description, data)
            counter = 0
            for item in data.items:
                item.id = counter
                counter += 1
                for form_item in item.items:
                    form_item.id = counter
                    counter += 1

        return super().dump(data)
