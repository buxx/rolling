# coding: utf-8
import dataclasses
import random
import typing

from rolling.action.utils import AroundPercent
from rolling.action.utils import in_percent
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
from rolling.server.document.affinity import AffinityDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


@dataclasses.dataclass
class DefendDescription:
    affinities: typing.List[AffinityDocument]
    all_fighters: typing.List[CharacterModel]
    ready_fighters: typing.List[CharacterModel]
    helpers: typing.Dict[str, typing.List[AffinityDocument]] = dataclasses.field(
        default_factory=dict
    )

    def reduce_fighters(self, fighters: typing.List[CharacterModel]) -> None:
        to_remove = [f.id for f in fighters]
        for fighter in list(self.all_fighters):
            if fighter.id in to_remove:
                self.all_fighters.remove(fighter)
        for fighter in list(self.ready_fighters):
            if fighter.id in to_remove:
                self.ready_fighters.remove(fighter)

    def reduce_affinities(self, affinities: typing.List[AffinityDocument]) -> None:
        to_remove = [a.id for a in affinities]
        for affinity in list(self.affinities):
            if affinity.id in to_remove:
                self.affinities.remove(affinity)


@dataclasses.dataclass
class AttackDescription:
    all_fighters: typing.List[CharacterModel]
    ready_fighters: typing.List[CharacterModel]
    affinity: typing.Optional[AffinityDocument] = None


class Weapon:
    def __init__(self, name: str, stuff: typing.Optional[StuffModel] = None) -> None:
        self.name = name
        self.stuff = stuff

    @property
    def base_damage(self) -> float:
        if self.stuff:
            return self.stuff.damages
        return 0.5

    @property
    def sharp(self) -> int:
        if self.stuff:
            return self.stuff.sharp
        return 0

    @property
    def estoc(self) -> int:
        if self.stuff:
            return self.stuff.estoc
        return 0

    @property
    def blunt(self) -> int:
        if self.stuff:
            return self.stuff.blunt
        return 1

    @property
    def protect_sharp(self) -> int:
        if self.stuff:
            return self.stuff.protect_sharp
        return 0

    @property
    def protect_estoc(self) -> int:
        if self.stuff:
            return self.stuff.protect_estoc
        return 0

    @property
    def protect_blunt(self) -> int:
        if self.stuff:
            return self.stuff.protect_blunt
        return 0

    def get_bonus_with_skills(self, kernel: "Kernel") -> typing.List[str]:
        if self.stuff:
            stuff_properties = kernel.game.stuff_manager.get_stuff_properties_by_id(
                self.stuff.stuff_id
            )
            return stuff_properties.skills_bonus
        return []

    def _get_around_percent_absorb(
        self, weapon: "Weapon"
    ) -> typing.Tuple[AroundPercent, AroundPercent, AroundPercent]:
        estoc_is = in_percent(self.protect_estoc, weapon.estoc, 20)
        blunt_is = in_percent(self.protect_blunt, weapon.blunt, 20)
        sharp_is = in_percent(self.protect_sharp, weapon.sharp, 20)
        return estoc_is, blunt_is, sharp_is

    def how_much_absorb(self, weapon: "Weapon", damage: float) -> float:
        results = self._get_around_percent_absorb(weapon)

        if AroundPercent.MORE in results:
            return damage

        if AroundPercent.IN in results:
            return damage * (random.randrange(0, 100, 1) / 100)

        # LESS
        return 0.0
