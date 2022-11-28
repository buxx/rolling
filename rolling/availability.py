import abc
import dataclasses
import typing
from rolling.exception import NotEnoughResource

from rolling.types import WorldPoint
from guilang.description import Part
from rolling.model.ability import AbilityDescription

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.resource import CarriedResourceDescriptionModel
    from rolling.model.stuff import StuffModel
    from rolling.server.document.affinity import AffinityDocument
    from rolling.server.document.build import BuildDocument
    from rolling.types import ResourceId, StuffType


class OriginInterface(abc.ABC):
    @abc.abstractmethod
    def name(self) -> str:
        ...


class Inventory(OriginInterface):
    def name(self):
        return "Inventaire"


class Character(OriginInterface):
    def name(self):
        return "Connaissance"


class Stuff(OriginInterface):
    def __init__(self, stuff: "StuffModel") -> None:
        self._stuff = stuff

    def name(self):
        return f"Objet ({self._stuff})"


class Build(OriginInterface):
    def __init__(self, build_name: str) -> None:
        self._build_name = build_name

    def name(self):
        return f"Bâtiment ({self._build_name})"


class Ground(OriginInterface):
    def __init__(self, affinity: typing.Optional["AffinityDocument"]) -> None:
        self._affinity = affinity

    def name_full(self):
        if self._affinity is not None:
            return f"Stockage au sol ({AffinityDocument.name})"

        return "Stockage au sol"

    def name(self):
        return "Stockage au sol"


@dataclasses.dataclass
class ResourceAvailability:
    resources: typing.List["CarriedResourceDescriptionModel"]
    origins: typing.List[OriginInterface]


@dataclasses.dataclass
class StuffAvailability:
    stuffs: typing.List["StuffModel"]
    origins: typing.List[OriginInterface]


@dataclasses.dataclass
class AbilityAvailability:
    abilities: typing.List["AbilityDescription"]
    origins: typing.List[OriginInterface]


@dataclasses.dataclass
class ResourceReductions:
    reductions: typing.List["ResourceReduction"]

    def resume_parts(self, kernel: "Kernel") -> typing.List[Part]:
        parts = [Part(text="Resources utilisés : ")]

        for reduction in self.reductions:
            resource_description = kernel.game.config.resources[reduction.resource_id]
            unit_str = kernel.translation.get(resource_description.unit, short=True)
            parts.append(
                Part(
                    f"  - {reduction.quantity}{unit_str} "
                    f"{resource_description.name} "
                    f"(depuis {reduction.origin.name()})"
                )
            )

        return parts


@dataclasses.dataclass
class ResourceReduction:
    origin: OriginInterface
    quantity: float
    resource_id: "ResourceId"


class Availability:
    @classmethod
    def new(cls, kernel: "Kernel", character: "CharacterModel") -> "Availability":
        return cls(kernel, character)

    def __init__(self, kernel: "Kernel", character: "CharacterModel") -> None:
        self._kernel = kernel
        self._character = character
        self._world_point = WorldPoint(
            (self._character.world_row_i, self._character.world_col_i)
        )

    def resources(
        self, resource_id: typing.Optional["ResourceId"] = None
    ) -> ResourceAvailability:
        origins = []
        resource_docs = []
        cache = self._kernel.cache(self._world_point)

        protectorate_state = cache.protectorat_state()
        if protectorate_state.allow_ground_resources(self._character):
            origins.append(Ground(protectorate_state.affinity()))
            resource_docs.extend(cache.get_ground_resources())

        resource_docs.extend(cache.get_carried_resources(self._character.id))
        origins.append(Inventory())

        if resource_id is not None:
            resource_docs = [r for r in resource_docs if r.resource_id == resource_id]

        resources = self._kernel.resource_lib.merge_resource_documents(resource_docs)
        return ResourceAvailability(
            resources,
            origins,
        )

    def stuffs(
        self,
        under_construction: typing.Optional[bool] = None,
        stuff_id: typing.Optional["StuffType"] = None,
    ) -> StuffAvailability:
        origins = []
        stuffs = []
        cache = self._kernel.cache(self._world_point)

        protectorate_state = cache.protectorat_state()
        if protectorate_state.allow_ground_stuffs(self._character):
            origins.append(Ground(protectorate_state.affinity()))
            stuffs.extend(cache.get_ground_stuffs())

        stuffs.extend(cache.get_carried_stuffs(self._character.id))
        origins.append(Inventory())

        if under_construction is not None:
            stuffs = [s for s in stuffs if s.under_construction == under_construction]

        if stuff_id is not None:
            stuffs = [s for s in stuffs if s.stuff_id == stuff_id]

        return StuffAvailability(
            stuffs,
            origins,
        )

    def builds(
        self, under_construction: typing.Optional[bool] = None
    ) -> typing.List["BuildDocument"]:
        builds = []
        cache = self._kernel.cache(self._world_point)

        protectorate_state = cache.protectorat_state()
        if protectorate_state.allow_use_builds(self._character):
            builds.extend(cache.get_builds())

        if under_construction is not None:
            builds = [b for b in builds if b.under_construction == under_construction]

        return builds

    def reduce_resource(self, resource_id: str, quantity: float) -> ResourceReductions:
        to_reduce = quantity
        reductions = []
        cache = self._kernel.cache(self._world_point)
        self._kernel.server_db_session.begin_nested()

        protectorate_state = cache.protectorat_state()
        if protectorate_state.allow_ground_resources(self._character):
            resource_docs = cache.get_ground_resources(resource_id=resource_id)
            reduced = self._kernel.resource_lib.reduce_from_docs(
                resource_docs, to_reduce
            )
            to_reduce -= reduced
            reductions.append(
                ResourceReduction(
                    Ground(protectorate_state.affinity()),
                    reduced,
                    resource_id=resource_id,
                )
            )

        if to_reduce:
            resource_docs = cache.get_carried_resources(
                self._character.id, resource_id=resource_id
            )
            reduced = self._kernel.resource_lib.reduce_from_docs(
                resource_docs, to_reduce
            )
            to_reduce -= reduced
            reductions.append(
                ResourceReduction(
                    Ground(protectorate_state.affinity()),
                    reduced,
                    resource_id=resource_id,
                )
            )

        if to_reduce:
            self._kernel.server_db_session.rollback()
            raise NotEnoughResource(
                resource_id,
                required_quantity=quantity,
                available_quantity=quantity - to_reduce,
            )

        self._kernel.server_db_session.commit()
        return ResourceReductions(reductions)

    def take_from_parts(self) -> typing.List[Part]:
        parts = [Part(text="Les ressources et objets seront utilisés depuis :")]
        cache = self._kernel.cache(self._world_point)
        protectorate_state = cache.protectorat_state()

        if protectorate_state.allow_ground_stuffs(self._character):
            parts.append(Part(text=f"  - Stockage au sol"))

        parts.append(Part(text=f"  - Votre inventaire"))

        return parts

    def take_from_one_line_txt(self) -> typing.List[Part]:
        parts = []
        cache = self._kernel.cache(self._world_point)
        protectorate_state = cache.protectorat_state()

        if protectorate_state.allow_ground_stuffs(self._character):
            parts.append("Stockage au sol")

        parts.append("Votre inventaire")

        return ", ".join(parts)

    def abilities(
        self,
    ) -> AbilityAvailability:
        origins = []
        abilities = []

        for ability_id in self._character.ability_ids:
            abilities.append(self._kernel.game.config.abilities[ability_id])
            origins.append(Character())

        for stuff in self.stuffs(under_construction=False).stuffs:
            stuff_properties = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    stuff.stuff_id
                )
            )
            for ability_id in stuff_properties.abilities:
                abilities.append(self._kernel.game.config.abilities[ability_id])
                origins.append(Stuff(stuff))

        for build in self.builds(under_construction=False):
            build_description = self._kernel.game.config.builds[build.build_id]
            if (build_description.abilities_if_is_on and build.is_on) or (
                not build_description.abilities_if_is_on
            ):
                for ability_id in build_description.ability_ids:
                    abilities.append(self._kernel.game.config.abilities[ability_id])
                    origins.append(Build(build_description.name))

        return AbilityAvailability(
            abilities,
            origins,
        )
