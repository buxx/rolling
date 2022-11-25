# coding: utf-8
import dataclasses
import random
import typing

from rolling.model.character import CharacterModel
from rolling.model.character import FIGHT_AP_CONSUME
from rolling.model.character import FIGHT_TIREDNESS_INCREASE
from rolling.model.fight import AttackDescription
from rolling.model.fight import DEFAULT_WEAPON_DAMAGE
from rolling.model.fight import DefendDescription
from rolling.model.fight import Weapon
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.character import CharacterDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel

EVADE_SKILL_ID = "agility"
PROBABILITY_TO_EVADE_MULTIPLIER = 6
PROBABILITY_TO_EVADE_MAXIMUM_PROBABILITY = 80  # percent
PROBABILITY_TO_EVADE_START_PROBABILITY = 15  # percent


@dataclasses.dataclass
class FightDetails:
    story: typing.List[str]
    debug_story: typing.List[str]
    groups: typing.List[typing.List[CharacterModel]]

    @classmethod
    def new(cls, groups: typing.List[typing.List[CharacterModel]]) -> "FightDetails":
        return cls(story=[], debug_story=[], groups=groups)

    def new_story_line(self, line: str) -> None:
        self.story.append(line)
        self.debug_story.append(line)

    def new_debug_story_line(self, line: str) -> None:
        self.debug_story.append(line)


class FightLib:
    def __init__(self, kernel: "Kernel", dont_touch_db: bool = False) -> None:
        self._kernel = kernel
        self._dont_touch_db = dont_touch_db

    def get_defense_description(
        self,
        origin_target: CharacterModel,
        world_row_i: int,
        world_col_i: int,
        attacker_affinity: typing.Optional[AffinityDocument] = None,
    ) -> DefendDescription:
        helpers: typing.Dict[str, typing.List[int]] = {}

        def search_fighters_for(fighter_id, helping: bool = False):
            all_fighter_ids_ = []
            all_affinity_ids_ = []
            for affinity_relation in self._kernel.affinity_lib.get_accepted_affinities(
                fighter_id
            ):
                all_affinity_fighter_ids = (
                    self._kernel.affinity_lib.get_affinity_fighter_ids(
                        affinity_id=affinity_relation.affinity_id
                    )
                )
                here_affinity_fighter_ids = [
                    r[0]
                    for r in self._kernel.character_lib.alive_query.filter(
                        CharacterDocument.id.in_(all_affinity_fighter_ids),
                        CharacterDocument.world_row_i == world_row_i,
                        CharacterDocument.world_col_i == world_col_i,
                    )
                    .with_entities(CharacterDocument.id)
                    .all()
                ]
                if here_affinity_fighter_ids:
                    all_affinity_ids_.append(affinity_relation.affinity_id)

                all_fighter_ids_.extend(here_affinity_fighter_ids)

                if (
                    helping
                    and attacker_affinity
                    and affinity_relation.affinity_id != attacker_affinity.id
                ):
                    for here_affinity_fighter_id in here_affinity_fighter_ids:
                        helpers.setdefault(here_affinity_fighter_id, []).append(
                            affinity_relation.affinity_id
                        )

            return list(set(all_fighter_ids_)), list(set(all_affinity_ids_))

        all_fighter_ids, all_affinity_ids = search_fighters_for(origin_target.id)
        same = False
        while not same:
            copy_ = list(all_fighter_ids)
            for fighter_id_ in all_fighter_ids:
                new_fighter_list, new_affinity_list = search_fighters_for(
                    fighter_id_, helping=True
                )
                all_fighter_ids.extend(new_fighter_list)
                all_fighter_ids = list(set(all_fighter_ids))
                all_affinity_ids.extend(new_affinity_list)
                all_affinity_ids = list(set(all_affinity_ids))
            if set(copy_) == set(all_fighter_ids):
                same = True

        all_fighters = self._kernel.character_lib.get_multiple(
            character_ids=all_fighter_ids
        )
        all_affinities = self._kernel.affinity_lib.get_multiple(
            affinity_ids=all_affinity_ids
        )
        affinities_by_ids = {a.id: a for a in all_affinities}
        all_fighters += (
            [origin_target] if origin_target.id not in all_fighter_ids else []
        )
        return DefendDescription(
            all_fighters=all_fighters,
            ready_fighters=[f for f in all_fighters if f.is_defend_ready],
            affinities=all_affinities,
            helpers={
                f_id: [affinities_by_ids[a_id] for a_id in set(helpers[f_id])]
                for f_id in helpers
            },
        )

    def get_attack_description(
        self,
        target: DefendDescription,
        attacker: AffinityDocument,
        world_row_i: int,
        world_col_i: int,
    ) -> AttackDescription:
        all_affinity_fighter_ids = self._kernel.affinity_lib.get_affinity_fighter_ids(
            affinity_id=attacker.id
        )
        here_affinity_fighter_ids = [
            r[0]
            for r in self._kernel.character_lib.alive_query.filter(
                CharacterDocument.id.in_(all_affinity_fighter_ids),
                CharacterDocument.world_row_i == world_row_i,
                CharacterDocument.world_col_i == world_col_i,
            )
            .with_entities(CharacterDocument.id)
            .all()
        ]
        all_fighters = self._kernel.character_lib.get_multiple(
            character_ids=here_affinity_fighter_ids
        )
        target_fighter_ids = [f.id for f in target.all_fighters]
        return AttackDescription(
            affinity=attacker,
            all_fighters=all_fighters,
            ready_fighters=[
                f
                for f in all_fighters
                if f.is_attack_ready and f.id not in target_fighter_ids
            ],
        )

    def get_fight_groups(
        self, attack: AttackDescription, defense: DefendDescription
    ) -> typing.List[typing.List[CharacterModel]]:
        groups: typing.List[typing.List[CharacterModel]] = []
        available_defensers = list(defense.ready_fighters)
        attackers_without_target = list(attack.ready_fighters)

        for attacker in attack.ready_fighters:
            if not available_defensers:
                break
            attacker_target = random.choice(available_defensers)
            available_defensers.remove(attacker_target)
            attackers_without_target.remove(attacker)
            groups.append([attacker, attacker_target])

        for attacker_without_target in attackers_without_target:
            attacker_target = random.choice(defense.ready_fighters)
            target_group = next(g for g in groups if attacker_target in g)
            target_group.append(attacker_without_target)

        for available_defenser in available_defensers:
            random.choice(groups).append(available_defenser)

        return groups

    async def fight(
        self, attack: AttackDescription, defense: DefendDescription
    ) -> FightDetails:
        if len(defense.ready_fighters) == 0:
            details = FightDetails.new([])
            details.new_story_line(
                "<p>"
                f"Aucun des combattants du parti attaqué n'est en état de se battre. Ils sont à la "
                f"mercie des attaquants."
                "</p>"
            )
            return details

        if len(attack.ready_fighters) == 0:
            details = FightDetails.new([])
            details.new_story_line(
                "<p>" f"Aucun des attaquants n'est en état de se battre.</p>"
            )
            return details

        groups = self.get_fight_groups(attack, defense)
        details = FightDetails.new(groups)
        attack_affinity_str = f" ({attack.affinity.name})" if attack.affinity else ""
        defense_affinities_str = (
            f" (" + ", ".join([a.name for a in defense.affinities]) + ")"
            if defense.affinities
            else ""
        )
        details.new_story_line("<h2>⚔⚔⚔ Déroulement du combat ⚔⚔⚔</h2>")
        details.new_story_line(
            "<p>"
            f"Un affrontement débute: {len(attack.ready_fighters)} "
            f"combattant(s){attack_affinity_str} "
            f"se lance(nt) à l'assault de {len(defense.all_fighters)} "
            f"combattant(s){defense_affinities_str}."
            "</p>"
        )

        if len(defense.ready_fighters) < len(defense.all_fighters):
            no_ready_to_fight_len = len(defense.all_fighters) - len(
                defense.ready_fighters
            )
            details.new_story_line(
                "<p>"
                f"{no_ready_to_fight_len} combattant(s) du parti attaqué ne sont pas en "
                f"état de se battre."
                "</p>"
            )

        async def get_alive_opponent_in_group(
            group_: typing.List[CharacterModel], for_: CharacterModel
        ) -> CharacterModel:
            is_attacker = for_ in attack.all_fighters
            group__ = list(group_)
            random.shuffle(group__)
            for fighter_ in group__:
                if fighter_.life_points < 0:
                    continue

                if fighter_ != for_:
                    if is_attacker:
                        if fighter_ in defense.all_fighters:
                            return fighter_
                    else:
                        if fighter_ in attack.all_fighters:
                            return fighter_

        details.new_story_line("Groupe(s) de combat : ")
        details.new_story_line("<ul>")
        for i, group in enumerate(groups):
            attackers = [f for f in group if f in attack.all_fighters]
            defensers = [f for f in group if f in defense.all_fighters]
            details.new_story_line("<li>")
            details.new_story_line(f"Groupe {i+1}")
            details.new_story_line("<ul>")
            details.new_story_line(
                "<li>" f"Attaquants : {', '.join([f.name for f in attackers])}" "</li>"
            )
            details.new_story_line(
                "<li>" f"Défenseurs : {', '.join([f.name for f in defensers])}" "</li>"
            )
            details.new_story_line("</ul>")
            details.new_story_line("</li>")

        details.new_story_line("</ul>")

        # start the battle ...
        for i, group in enumerate(groups):
            details.new_story_line(f"<h3>⚔⚔ Combat dans le groupe {i+1} ⚔⚔</h3>")

            details.new_story_line("<ul>")

            random.shuffle(group)
            for fighter in group:
                if fighter.life_points < 0:
                    details.new_story_line("<li>")
                    details.new_story_line(f"{fighter.name} est hors de combat")
                    details.new_story_line("</li>")
                    details.new_story_line("</ul>")
                    continue

                opponent = await get_alive_opponent_in_group(group, for_=fighter)
                if not opponent:
                    details.new_story_line("<li>")
                    details.new_story_line(f"{fighter.name} n'a pas d'opposant")
                    details.new_story_line("</li>")
                    details.new_story_line("</ul>")
                    continue

                attacker_weapon = self.get_attack_weapon(fighter, against=opponent)
                defenser_weapon = self.get_defense_weapon(
                    opponent, from_=fighter, attacked_with=attacker_weapon
                )
                defenser_shield = self.get_defense_shield(
                    opponent, from_=fighter, attacked_with=attacker_weapon
                )

                if self.defenser_evade(
                    opponent,
                    attacker=fighter,
                    weapon=attacker_weapon,
                    defenser_weapon=defenser_weapon,
                    defenser_shield=defenser_shield,
                    details=details,
                ):
                    details.new_story_line(
                        "<li>"
                        f"🛡🛡 {fighter.name} attaque {opponent.name} avec {attacker_weapon.name} mais "
                        f"{opponent.name} parvient à esquiver."
                        "</li>"
                    )
                # elif defenser_shield is not None and self.defenser_shield_protect(
                #     opponent,
                #     attacker=fighter,
                #     weapon=attacker_weapon,
                #     defenser_shield=defenser_shield,
                #     details=details,
                # ):
                #     details.new_story_line(
                #         "<li>"
                #         f"🛡🛡 {fighter.name} attaque {opponent.name} avec {attacker_weapon.name} mais "
                #         f"{opponent.name} parvient à se protéger ({defenser_shield.name})."
                #         "</li>"
                #     )
                else:
                    details.new_story_line(
                        "<li>"
                        f"⚔ <b>{fighter.name} attaque {opponent.name} avec {attacker_weapon.name}</b>"
                        "</li>"
                    )
                    damage = self.get_damage(
                        fighter, weapon=attacker_weapon, details=details
                    )
                    opponent_equipment, pass_damages = self.opponent_equipment_passes(
                        opponent,
                        from_=fighter,
                        weapon=attacker_weapon,
                        damage=damage,
                        details=details,
                    )
                    if damage and pass_damages == damage:
                        details.new_story_line("<li>")
                        details.new_story_line(
                            f"💥 <b>{opponent_equipment.name} n'a en rien protégé {opponent.name}</b>"
                        )
                        details.new_story_line("</li>")
                    elif pass_damages and pass_damages < damage:
                        details.new_story_line("<li>")
                        details.new_story_line(
                            f"💥🛡 <b>{opponent_equipment.name} à en partie protégé {opponent.name}</b>"
                        )
                        details.new_story_line("</li>")
                    else:
                        details.new_story_line("<li>")
                        details.new_story_line(
                            f"🛡🛡 <b>{opponent_equipment.name} à protégé {opponent.name}</b>"
                        )
                        details.new_story_line("</li>")

                    self.apply_damage_on_equipment(
                        opponent,
                        equipment=opponent_equipment,
                        dont_touch_db=self._dont_touch_db,
                    )
                    self.apply_damage_on_character(
                        opponent,
                        damages=pass_damages,
                        dont_touch_db=self._dont_touch_db,
                    )

                    if opponent.life_points < 0:
                        details.new_story_line("<li>")
                        details.new_story_line(
                            f"💀 <b>Le coup à été fatal pour {opponent.name}</b>"
                        )
                        details.new_story_line("</li>")

                    if not self._dont_touch_db:
                        # FIXME BS NOW: write test about this
                        self.increase_attacker_skills(fighter, attacker_weapon)

                if not self._dont_touch_db:
                    await self._kernel.character_lib.reduce_action_points(
                        fighter.id, FIGHT_AP_CONSUME
                    )
                    # self._kernel.character_lib.increase_tiredness(
                    #     fighter.id, FIGHT_TIREDNESS_INCREASE
                    # )

            details.new_story_line("</ul>")

        return details

    def get_attack_weapon(
        self, fighter: CharacterModel, against: CharacterModel
    ) -> Weapon:
        if fighter.weapon:
            return Weapon(name=fighter.weapon.name, stuff=fighter.weapon)
        return Weapon(name="Main nue")

    def get_defense_weapon(
        self, opponent: CharacterModel, from_: CharacterModel, attacked_with: Weapon
    ) -> Weapon:
        if opponent.weapon:
            return Weapon(name=opponent.weapon.name, stuff=opponent.weapon)
        return Weapon(name="Main nue")

    def get_defense_shield(
        self, opponent: CharacterModel, from_: CharacterModel, attacked_with: Weapon
    ) -> typing.Optional[Weapon]:
        if opponent.shield:
            return Weapon(name=opponent.shield.name, stuff=opponent.shield)
        return None

    def opponent_equipment_passes(
        self,
        opponent: CharacterModel,
        from_: CharacterModel,
        weapon: Weapon,
        damage: float,
        details: FightDetails,
    ) -> typing.Tuple[Weapon, float]:
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(f"Calcul de defense")

        details.new_debug_story_line("<ul>")
        if opponent.armor:
            armor = Weapon(name=opponent.armor.name, stuff=opponent.armor)
            details.new_debug_story_line("<li>")
            details.new_debug_story_line(f"armor is {armor.name}")
            details.new_debug_story_line("<ul>")
            passes = armor.how_much_damages_passes(weapon, damage, details=details)
            details.new_debug_story_line("</ul>")
            details.new_debug_story_line("</li>")
            details.new_debug_story_line("</ul>")
            return armor, passes

        details.new_debug_story_line("<li>")
        details.new_debug_story_line(f"no armor")
        details.new_debug_story_line("</li>")
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(f"<b>damage = {damage}</b>")
        details.new_debug_story_line("</li>")

        details.new_debug_story_line("</ul>")
        details.new_debug_story_line("</li>")
        return Weapon(name="Peau nue"), damage

    def defenser_evade(
        self,
        evader: CharacterModel,
        attacker: CharacterModel,
        weapon: Weapon,
        defenser_weapon: Weapon,
        # TODO : have a shield reduce chance to evade
        defenser_shield: Weapon,
        details: FightDetails,
    ) -> bool:
        probability_to_evade0 = PROBABILITY_TO_EVADE_START_PROBABILITY  # percent
        evader_evade_skill_value = evader.get_skill_value(EVADE_SKILL_ID)
        attacker_evade_skill_value = attacker.get_skill_value(EVADE_SKILL_ID)
        probability_to_evade1 = (
            probability_to_evade0
            + (evader_evade_skill_value - attacker_evade_skill_value)
            * PROBABILITY_TO_EVADE_MULTIPLIER
        )
        probability_to_evade2 = min(
            PROBABILITY_TO_EVADE_MAXIMUM_PROBABILITY, probability_to_evade1
        )
        rand_value = random.randint(0, 100)
        evade = bool(rand_value < probability_to_evade2)

        details.new_debug_story_line("<li>")
        details.new_debug_story_line(
            f"{attacker.name} attaque {evader.name} : calcul d'esquive"
        )
        details.new_debug_story_line("<ul>")
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(f"random = [0, 100] -> {rand_value}")
        details.new_debug_story_line("</li>")
        details.new_debug_story_line(
            "<li>"
            f"probability_to_evade = {PROBABILITY_TO_EVADE_START_PROBABILITY} + "
            f"'({evader.name}'.{EVADE_SKILL_ID}({evader_evade_skill_value}) - "
            f"'{attacker.name}'.{EVADE_SKILL_ID}({attacker_evade_skill_value})) * "
            f"{PROBABILITY_TO_EVADE_MULTIPLIER}"
            f" -> {probability_to_evade1}"
            "</li>"
        )
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(
            f"probability_to_evade = min({PROBABILITY_TO_EVADE_MAXIMUM_PROBABILITY}, {probability_to_evade1}) -> {probability_to_evade2}"
        )
        details.new_debug_story_line("</li>")
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(
            f"evade if random({rand_value}) &lt; probability_to_evade({probability_to_evade2}) -> {evade}"
        )
        details.new_debug_story_line("</li>")

        details.new_debug_story_line("</ul>")
        details.new_debug_story_line("</li>")
        return evade

    def get_damage(
        self, fighter: CharacterModel, weapon: Weapon, details: FightDetails
    ) -> float:
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(f"Calcul de dommages")
        details.new_debug_story_line("<ul>")

        random_ = random.randrange(8, 12, 1) / 10
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(f"random_ = [8, 12] / 10 -> {random_}")
        details.new_debug_story_line("</li>")
        force_weapon_multiplier = fighter.force_weapon_multiplier(details=details)
        weapon_damage = max(weapon.base_damage, DEFAULT_WEAPON_DAMAGE)
        details.new_debug_story_line("<li>")
        details.new_debug_story_line(
            f"weapon_damage = max(weapon.base_damage({weapon.base_damage}), {DEFAULT_WEAPON_DAMAGE}) -> {weapon_damage}"
        )
        details.new_debug_story_line("</li>")
        with_weapon_coeff = fighter.get_with_weapon_coeff(
            weapon, self._kernel, details=details
        )

        damages = (
            force_weapon_multiplier * weapon_damage * with_weapon_coeff
        ) * random_
        damages = round(damages, 2)

        details.new_debug_story_line("<li>")
        details.new_debug_story_line(
            f"    damages = (force_weapon_multiplier({force_weapon_multiplier}) * "
            f"weapon_damage({weapon_damage}) * "
            f"with_weapon_coeff({with_weapon_coeff})) * random_({random_}) -> {damages}"
        )
        details.new_debug_story_line("</li>")

        details.new_debug_story_line("</ul>")
        details.new_debug_story_line("</li>")

        return damages

    def apply_damage_on_equipment(
        self, opponent: CharacterModel, equipment: Weapon, dont_touch_db: bool = False
    ) -> None:
        # Use updated stuff model infos
        pass  # TODO: Code it; display state

    def apply_damage_on_character(
        self, opponent: CharacterModel, damages: float, dont_touch_db: bool = False
    ) -> None:
        if not dont_touch_db:
            new_life_points = self._kernel.character_lib.reduce_life_points(
                opponent.id, value=damages
            )
            opponent.life_points = new_life_points
        else:
            opponent.life_points -= damages

    def increase_attacker_skills(self, fighter: CharacterModel, weapon: Weapon) -> None:
        for skill_id in weapon.get_bonus_with_skills(self._kernel):
            self._kernel.character_lib.increase_skill(fighter.id, skill_id, 1)
