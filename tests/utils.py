import typing

from guilang.description import Part


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
