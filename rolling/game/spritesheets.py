import dataclasses
import typing


@dataclasses.dataclass
class CreateCharacterSource:
    name: str
    group_by_variant: bool
    identifiers: typing.List[str]
    default_value: str
    allowed_variants: typing.Optional[typing.List[str]] = None
    default_variant: typing.Optional[str] = None
    build_value_names_with_levels: typing.Optional[int] = None
    take_variant_from: typing.Optional[str] = None
    dont_wrap: bool = False
    permit_none: bool = False
    extract_body_type_from: typing.List[int] = None

    def parent_base_name(self) -> typing.List[str]:
        names = self.parent_identifiers()
        return "::".join(names[0].split("::")[:-1])

    def parent_identifiers(self) -> typing.List[str]:
        names = []

        for identifier in self.identifiers:
            names.append(identifier[:-3])

        return names

    def values(
        self, all_identifiers: typing.List[str]
    ) -> typing.List[typing.Tuple[str, str]]:
        values_ = {}

        for identifier in self.possibles(all_identifiers):
            splitted_identifier = identifier.split("::")

            if self.build_value_names_with_levels is not None:
                name = "-".join(
                    [splitted_identifier[i] for i in self.build_value_names_with_levels]
                )
            else:
                if self.group_by_variant:
                    name = splitted_identifier[-2]
                else:
                    name = splitted_identifier[-1]

            if self.group_by_variant:
                values_["::".join(identifier.split("::")[0:-1] + ["*"])] = name
            else:
                values_[identifier] = name

        # reduce by value to avoid duplicate choices
        values__ = {}
        for key, value in values_.items():
            if value not in values__.values():
                values__[key] = value

        return values__

    def possibles(self, all_identifiers: typing.List[str]) -> typing.List[str]:
        parent_prefixes = []
        names = []

        for identifier in self.identifiers:
            parent_prefixes.append(identifier[:-1])

        for identifier in all_identifiers:
            if any(
                identifier.startswith(parent_prefix)
                for parent_prefix in parent_prefixes
            ):
                names.append(identifier)

        return names

    def variants(self, all_identifiers: typing.List[str]) -> typing.List[str]:
        possibles = self.possibles(all_identifiers)
        names = list(set(possible.split("::")[-1] for possible in possibles))
        return names


@dataclasses.dataclass
class SpriteSheets:
    create_character: typing.List[CreateCharacterSource]
