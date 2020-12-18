# coding: utf-8
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
PROBABILITY_TO_EVADE_MAXIMUM_PROBABILITY = 90  # percent
PROBABILITY_TO_EVADE_START_PROBABILITY = 50  # percent


class FightLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

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
            for affinity_relation in self._kernel.affinity_lib.get_accepted_affinities(fighter_id):
                all_affinity_fighter_ids = self._kernel.affinity_lib.get_affinity_fighter_ids(
                    affinity_id=affinity_relation.affinity_id
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
                new_fighter_list, new_affinity_list = search_fighters_for(fighter_id_, helping=True)
                all_fighter_ids.extend(new_fighter_list)
                all_fighter_ids = list(set(all_fighter_ids))
                all_affinity_ids.extend(new_affinity_list)
                all_affinity_ids = list(set(all_affinity_ids))
            if set(copy_) == set(all_fighter_ids):
                same = True

        all_fighters = self._kernel.character_lib.get_multiple(character_ids=all_fighter_ids)
        all_affinities = self._kernel.affinity_lib.get_multiple(affinity_ids=all_affinity_ids)
        affinities_by_ids = {a.id: a for a in all_affinities}
        all_fighters += [origin_target] if origin_target.id not in all_fighter_ids else []
        return DefendDescription(
            all_fighters=all_fighters,
            ready_fighters=[f for f in all_fighters if f.is_defend_ready()],
            affinities=all_affinities,
            helpers={
                f_id: [affinities_by_ids[a_id] for a_id in set(helpers[f_id])] for f_id in helpers
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
                f for f in all_fighters if f.is_attack_ready() and f.id not in target_fighter_ids
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

    def fight(self, attack: AttackDescription, defense: DefendDescription) -> typing.List[str]:
        story: typing.List[str] = []
        attack_affinity_str = f" ({attack.affinity.name})" if attack.affinity else ""
        defense_affinities_str = (
            f" (" + ", ".join([a.name for a in defense.affinities]) + ")"
            if defense.affinities
            else ""
        )

        story.append(
            f"Un affrontement débute: {len(attack.ready_fighters)} "
            f"combattant(s){attack_affinity_str} "
            f"se lance(nt) à l'assault de {len(defense.all_fighters)} "
            f"combattant(s){defense_affinities_str}."
        )

        if len(defense.ready_fighters) == 0:
            story.append(
                f"Aucun des combattants du parti attaqué n'est en état de se battre. Ils sont à la "
                f"mercie des attaquants."
            )
            return story
        elif len(defense.ready_fighters) < len(defense.all_fighters):
            no_ready_to_fight_len = len(defense.all_fighters) - len(defense.ready_fighters)
            story.append(
                f"{no_ready_to_fight_len} combattant(s) du parti attaqué ne sont pas en "
                f"état de se battre."
            )

        def get_alive_opponent_in_group(
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

        # start the battle ...
        groups = self.get_fight_groups(attack, defense)
        for group in groups:
            random.shuffle(group)
            for fighter in group:
                if fighter.life_points < 0:
                    continue

                story_sentences: typing.List[str] = []
                opponent = get_alive_opponent_in_group(group, for_=fighter)
                if not opponent:
                    continue

                attacker_weapon = self.get_attack_weapon(fighter, against=opponent)
                defenser_weapon = self.get_defense_weapon(
                    opponent, from_=fighter, attacked_with=attacker_weapon
                )

                if self.defenser_evade(
                    opponent, from_=fighter, weapon=attacker_weapon, defenser_weapon=defenser_weapon
                ):
                    story_sentences.append(
                        f"{fighter.name} attaque {opponent.name} avec {attacker_weapon.name} mais "
                        f"{opponent.name} parvient à esquiver."
                    )
                else:
                    story_sentences.append(
                        f"{fighter.name} attaque {opponent.name} avec {attacker_weapon.name}."
                    )
                    damage = self.get_damage(fighter, weapon=attacker_weapon)
                    opponent_equipment, pass_damages = self.opponent_equipment_protect(
                        opponent, from_=fighter, weapon=attacker_weapon, damage=damage
                    )
                    if damage and pass_damages == damage:
                        story_sentences.append(
                            f"{opponent_equipment.name} n'a en rien protégé {opponent.name}."
                        )
                    elif pass_damages and pass_damages < damage:
                        story_sentences.append(
                            f"{opponent_equipment.name} à en partie protégé {opponent.name}."
                        )
                    else:
                        story_sentences.append(
                            f"{opponent_equipment.name} à protégé {opponent.name}."
                        )

                    self.apply_damage_on_equipment(opponent, equipment=opponent_equipment)
                    self.apply_damage_on_character(opponent, damages=pass_damages)

                    if opponent.life_points < 0:
                        story_sentences.append(f"Le coup à été fatal pour {opponent.name}.")

                    # FIXME BS NOW: write test about this
                    self.increase_attacker_skills(fighter, attacker_weapon)

                story.append(" ".join(story_sentences))
                self._kernel.character_lib.reduce_action_points(fighter.id, FIGHT_AP_CONSUME)
                self._kernel.character_lib.increase_tiredness(fighter.id, FIGHT_TIREDNESS_INCREASE)

        return story

    def get_attack_weapon(self, fighter: CharacterModel, against: CharacterModel) -> Weapon:
        if fighter.weapon:
            return Weapon(name=fighter.weapon.name, stuff=fighter.weapon)
        return Weapon(name="Main nue")

    def get_defense_weapon(
        self, opponent: CharacterModel, from_: CharacterModel, attacked_with: Weapon
    ) -> Weapon:
        # TODO BS: optimize weapon choice against attacked_with
        if opponent.shield:
            return Weapon(name=opponent.shield.name, stuff=opponent.shield)
        if opponent.weapon:
            return Weapon(name=opponent.weapon.name, stuff=opponent.weapon)
        return Weapon(name="Main nue")

    def opponent_equipment_protect(
        self, opponent: CharacterModel, from_: CharacterModel, weapon: Weapon, damage: float
    ) -> typing.Tuple[Weapon, float]:
        if opponent.armor:
            armor = Weapon(name=opponent.armor.name, stuff=opponent.armor)
            return armor, armor.how_much_absorb(weapon, damage)
        return Weapon(name="Peau nue"), damage * (random.randrange(0, 100, 1) / 100)

    def defenser_evade(
        self,
        opponent: CharacterModel,
        from_: CharacterModel,
        weapon: Weapon,
        defenser_weapon: Weapon,
    ) -> bool:
        probability_to_evade = PROBABILITY_TO_EVADE_START_PROBABILITY  # percent
        probability_to_evade += (
            opponent.get_skill_value(EVADE_SKILL_ID) - from_.get_skill_value(EVADE_SKILL_ID)
        ) * PROBABILITY_TO_EVADE_MULTIPLIER
        probability_to_evade = min(PROBABILITY_TO_EVADE_MAXIMUM_PROBABILITY, probability_to_evade)

        return bool(random.randint(0, 100) < probability_to_evade)

    def get_damage(self, fighter: CharacterModel, weapon: Weapon) -> float:
        damages = (
            fighter.force_weapon_multiplier
            * max(weapon.base_damage, DEFAULT_WEAPON_DAMAGE)
            * fighter.get_with_weapon_coeff(weapon, self._kernel)
        ) * (random.randrange(8, 12, 1) / 10)
        return round(damages, 2)

    def apply_damage_on_equipment(self, opponent: CharacterModel, equipment: Weapon) -> None:
        # Use updated stuff model infos
        pass  # TODO: Code it; display state

    def apply_damage_on_character(self, opponent: CharacterModel, damages: float) -> None:
        new_life_points = self._kernel.character_lib.reduce_life_points(opponent.id, value=damages)
        opponent.life_points = new_life_points

    def increase_attacker_skills(self, fighter: CharacterModel, weapon: Weapon) -> None:
        for skill_id in weapon.get_bonus_with_skills(self._kernel):
            self._kernel.character_lib.increase_skill(fighter.id, skill_id, 1)
