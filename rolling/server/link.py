# coding: utf-8
import dataclasses
import typing


@dataclasses.dataclass
class CharacterActionLink:
    name: str
    link: str
    cost: typing.Optional[float] = None

    def get_as_str(self) -> str:
        if self.cost is None:
            return self.name
        return f"{self.name} ({self.cost} action points)"
