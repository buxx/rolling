import dataclasses
import typing


@dataclasses.dataclass
class CreateCharacterSource:
    name: str
    variant: bool
    identifiers: typing.List[str]


@dataclasses.dataclass
class SpriteSheets:
    create_character: typing.List[CreateCharacterSource]
