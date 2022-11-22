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
    from rolling.server.lib.fight import FightDetails

DEFAULT_WEAPON_DAMAGE = 0.5


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
        return DEFAULT_WEAPON_DAMAGE

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

    def _does_weapon_over(
        self,
        weapon: "Weapon",
        details: typing.Optional["FightDetails"] = None,
    ) -> typing.Tuple[AroundPercent, AroundPercent, AroundPercent]:
        """Determine if weapon is OVER, In or LESS vs this"""
        estoc_is = in_percent(self.protect_estoc, weapon.estoc, 20)
        blunt_is = in_percent(self.protect_blunt, weapon.blunt, 20)
        sharp_is = in_percent(self.protect_sharp, weapon.sharp, 20)

        if details is not None:
            details.new_debug_story_line("<li>")
            details.new_debug_story_line(
                f"estoc = "
                f"'{self.name}'({self.protect_estoc}) vs "
                f"'{weapon.name}'({weapon.estoc}) "
                f"-> {weapon.name} is {estoc_is.value}"
            )
            details.new_debug_story_line("</li>")
            details.new_debug_story_line("<li>")
            details.new_debug_story_line(
                f"blunt = "
                f"'{self.name}'({self.protect_blunt}) vs "
                f"'{weapon.name}'({weapon.blunt}) "
                f"-> {weapon.name} is  {blunt_is.value}"
            )
            details.new_debug_story_line("</li>")
            details.new_debug_story_line("<li>")
            details.new_debug_story_line(
                f"sharp = "
                f"'{self.name}'({self.protect_sharp}) vs "
                f"'{weapon.name}'({weapon.sharp}) "
                f"-> {weapon.name} is  {sharp_is.value}"
            )
            details.new_debug_story_line("</li>")

        return estoc_is, blunt_is, sharp_is

    def how_much_damages_passes(
        self,
        weapon: "Weapon",
        damage: float,
        details: typing.Optional["FightDetails"] = None,
    ) -> float:
        details.new_debug_story_line("<ul>")
        results = self._does_weapon_over(weapon, details=details)
        details.new_debug_story_line("</ul>")

        if AroundPercent.MORE in results:
            if details is not None:
                details.new_debug_story_line("<li>")
                details.new_debug_story_line(
                    f"damage = {damage} (full damage on armor)"
                )
                details.new_debug_story_line("</li>")

            return damage

        if AroundPercent.IN in results:
            damage_ = damage * (random.randrange(0, 100, 1) / 100)

            if details is not None:
                details.new_debug_story_line("<li>")
                details.new_debug_story_line(
                    f"damage = {damage_} ({damage} * random[0.0, 1.0])"
                )
                details.new_debug_story_line("</li>")

            return damage_

        # LESS
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(f"damage = 0 (can't damage this armor)")
        details.new_debug_story_line("</li>")
        return 0.0
