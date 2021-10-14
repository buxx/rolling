import typing

from guilang.description import Part
from rolling.model.character import CharacterModel
from rolling.kernel import Kernel
from rolling.server.document.build import BuildDocument


def extract_description_properties(
    parts: typing.List[Part], property_name: str
) -> typing.List[typing.Any]:
    properties = []

    for part in parts:
        if part.items:
            properties.extend(extract_description_properties(part.items, property_name))

        if hasattr(part, property_name):
            properties.append(getattr(part, property_name))

    return properties


def in_one_of(search: str, in_: typing.List[str]) -> bool:
    return any(search in item for item in in_)


def place_build_on_character_position(
    kernel: Kernel,
    character: CharacterModel,
    build_id: str,
) -> BuildDocument:
    return kernel.build_lib.place_build(
        world_row_i=character.world_row_i,
        world_col_i=character.world_col_i,
        zone_row_i=character.zone_row_i,
        zone_col_i=character.zone_col_i,
        build_id=build_id,
    )
