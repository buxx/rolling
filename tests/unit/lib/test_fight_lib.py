# coding: utf-8
import contextlib
import pytest
import typing
from unittest.mock import patch

from rolling.action.utils import AroundPercent
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.fight import AttackDescription
from rolling.model.fight import DefendDescription
from rolling.model.fight import Weapon
from rolling.model.stuff import StuffModel
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.affinity import MEMBER_STATUS


def make_fake_get_attack_weapon(params: typing.Dict[str, Weapon]):
    def fake_get_attack_weapon(
        self, fighter: CharacterModel, against: CharacterModel
    ) -> Weapon:
        return params[fighter.id]

    return fake_get_attack_weapon


def make_fake_get_defense_weapon(params: typing.Dict[str, Weapon]):
    def fake_get_defense_weapon(
        self, opponent: CharacterModel, from_: CharacterModel, attacked_with: Weapon
    ) -> Weapon:
        return params[opponent.id]

    return fake_get_defense_weapon


def make_fake_defenser_evade(params: typing.Dict[str, bool]):
    def fake_defenser_evade(
        self,
        opponent: CharacterModel,
        from_: CharacterModel,
        weapon: Weapon,
        defenser_weapon: Weapon,
    ) -> bool:
        return params[opponent.id]

    return fake_defenser_evade


def make_fake_opponent_equipment_protect(
    params: typing.Dict[str, typing.Tuple[Weapon, float]]
):
    def fake_opponent_equipment_protect(
        self,
        opponent: CharacterModel,
        from_: CharacterModel,
        weapon: Weapon,
        damage: float,
    ) -> typing.Tuple[Weapon, float]:
        weapon, damages = params[opponent.id]
        if damages is None:
            damages = damage
        return weapon, damages

    return fake_opponent_equipment_protect


def make_fake_get_damage(params: typing.Dict[str, float]):
    def fake_get_damage(self, fighter: CharacterModel, weapon: Weapon) -> float:
        return params[fighter.id]

    return fake_get_damage


@contextlib.contextmanager
def patch_fight(
    weapons: typing.Dict[str, Weapon],
    defense: typing.Dict[str, Weapon],
    evades: typing.Dict[str, bool],
    protect: typing.Dict[str, typing.Tuple[Weapon, float]],
    damages: typing.Dict[str, float],
):
    with patch(
        "rolling.server.lib.fight.FightLib.get_attack_weapon",
        new=make_fake_get_attack_weapon(weapons),
    ), patch(
        "rolling.server.lib.fight.FightLib.get_defense_weapon",
        new=make_fake_get_defense_weapon(defense),
    ), patch(
        "rolling.server.lib.fight.FightLib.defenser_evade",
        new=make_fake_defenser_evade(evades),
    ), patch(
        "rolling.server.lib.fight.FightLib.opponent_equipment_protect",
        new=make_fake_opponent_equipment_protect(protect),
    ), patch(
        "rolling.server.lib.fight.FightLib.get_damage",
        new=make_fake_get_damage(damages),
    ), patch(
        "random.shuffle", new=lambda l: l
    ), patch(
        "random.choice", new=lambda l: l[0]
    ):
        yield


class TestFightLib:
    def test_unit__fight_description__ok__simple_lonely_opposition(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        assert set([a.name for a in defense.affinities]) == {england_affinity.name}
        assert set([f.id for f in defense.all_fighters]) == {england_warlord.id}
        assert set([f.id for f in defense.ready_fighters]) == {england_warlord.id}

        assert france_affinity.name == attack.affinity.name
        assert {france_warlord.id} == set([f.id for f in attack.all_fighters])
        assert {france_warlord.id} == set([f.id for f in attack.ready_fighters])

    def test_unit__fight_description__ok__simple_armies_opposition(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
    ) -> None:
        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        assert set([a.name for a in defense.affinities]) == {england_affinity.name}
        assert set([f.id for f in defense.all_fighters]) == set(all_england_fighter_ids)
        assert set([f.id for f in defense.ready_fighters]) == set(
            all_england_fighter_ids
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set(all_france_fighter_ids) == set([f.id for f in attack.ready_fighters])

    def test_unit__fight_description__ok__simple_armies_with_some_les_lp(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
    ) -> None:
        for fighter in france_fighters[0:3] + england_fighters[0:3]:
            fighter.life_points = 0.5
            worldmapc_kernel.character_lib.reduce_life_points(fighter.id, 4.5)

        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        ready_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters[3:]
        ]
        assert set([a.name for a in defense.affinities]) == {england_affinity.name}
        assert set([f.id for f in defense.all_fighters]) == set(all_england_fighter_ids)
        assert set([f.id for f in defense.ready_fighters]) == set(
            ready_england_fighter_ids
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        ready_france_fighter_ids = [france_warlord.id] + [
            f.id for f in france_fighters[3:]
        ]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set(ready_france_fighter_ids) == set(
            [f.id for f in attack.ready_fighters]
        )

    def test_unit__fight_description__ok__simple_armies_with_some_exhausted(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
    ) -> None:
        for fighter in france_fighters[0:3] + england_fighters[0:3]:
            fighter.tiredness = 100
            worldmapc_kernel.character_lib.increase_tiredness(fighter.id, 100)

        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        ready_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters[3:]
        ]
        assert set([a.name for a in defense.affinities]) == {england_affinity.name}
        assert set([f.id for f in defense.all_fighters]) == set(all_england_fighter_ids)
        assert set([f.id for f in defense.ready_fighters]) == set(
            ready_england_fighter_ids
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        ready_france_fighter_ids = [france_warlord.id] + [
            f.id for f in france_fighters[3:]
        ]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set(ready_france_fighter_ids) == set(
            [f.id for f in attack.ready_fighters]
        )

    def test_unit__fight_description__ok__simple_armies_with_some_no_more_ap(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
    ) -> None:
        for fighter in france_fighters[0:3] + england_fighters[0:3]:
            fighter.action_points = 0.0
            worldmapc_kernel.character_lib.reduce_action_points(fighter.id, 24)

        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        # no more ap permit to defend
        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        assert set([a.name for a in defense.affinities]) == {england_affinity.name}
        assert set([f.id for f in defense.all_fighters]) == set(all_england_fighter_ids)
        assert set([f.id for f in defense.ready_fighters]) == set(
            all_england_fighter_ids
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        ready_france_fighter_ids = [france_warlord.id] + [
            f.id for f in france_fighters[3:]
        ]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set(ready_france_fighter_ids) == set(
            [f.id for f in attack.ready_fighters]
        )

    def test_unit__fight_description__ok__one_army_vs_2_armies_opposition_but_no_participate(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        burgundian_warlord: CharacterModel,
        burgundian_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
    ) -> None:
        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        # In this test only england defend because there is no relation between
        # england and burgundian
        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        assert set([a.name for a in defense.affinities]) == {england_affinity.name}
        assert set([f.id for f in defense.all_fighters]) == set(all_england_fighter_ids)
        assert set([f.id for f in defense.ready_fighters]) == set(
            all_england_fighter_ids
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set(all_france_fighter_ids) == set([f.id for f in attack.ready_fighters])

    def test_unit__fight_description__ok__one_army_vs_2_armies_opposition_and_participate(
        self,
        worldmapc_arthur_model: CharacterModel,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        burgundian_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        burgundian_warlord: CharacterModel,
        burgundian_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
    ) -> None:
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, arthur, england_affinity)
        self._active_relation_with(kernel, arthur, burgundian_affinity)

        # In this test only england defend because arthur accepted by england and burgundian
        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        all_burgundian_fighter_ids = [burgundian_warlord.id] + [
            f.id for f in burgundian_fighters
        ]
        assert set([a.name for a in defense.affinities]) == {
            england_affinity.name,
            burgundian_affinity.name,
        }
        assert set([f.id for f in defense.all_fighters]) == set(
            all_england_fighter_ids + all_burgundian_fighter_ids + [arthur.id]
        )
        assert set([f.id for f in defense.ready_fighters]) == set(
            all_england_fighter_ids + all_burgundian_fighter_ids + [arthur.id]
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set(all_france_fighter_ids) == set([f.id for f in attack.ready_fighters])

    def test_unit__fight_description__ok__one_army_vs_2_armies_opposition_and_no_participate_because_link_not_here(
        self,
        worldmapc_arthur_model: CharacterModel,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        burgundian_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        burgundian_warlord: CharacterModel,
        burgundian_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
    ) -> None:
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, arthur, england_affinity)
        self._active_relation_with(kernel, arthur, burgundian_affinity)
        arthur_doc = worldmapc_kernel.character_lib.get_document(arthur.id)
        arthur_doc.world_row_i = 42  # armies are at 1
        arthur_doc.world_col_i = 42  # armies are at 1
        worldmapc_kernel.server_db_session.add(arthur_doc)
        worldmapc_kernel.server_db_session.commit()

        # In this test only england defend because arthur accepted by england and burgundian
        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        assert set([a.name for a in defense.affinities]) == {england_affinity.name}
        assert set([f.id for f in defense.all_fighters]) == set(all_england_fighter_ids)
        assert set([f.id for f in defense.ready_fighters]) == set(
            all_england_fighter_ids
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set(all_france_fighter_ids) == set([f.id for f in attack.ready_fighters])

    def test_unit__fight_description__ok__simple_armies_opposition_with_fighter_direct_conflict(
        self,
        england_affinity: AffinityDocument,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
    ) -> None:
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, france_fighters[0], england_affinity)
        self._active_relation_with(kernel, france_fighters[1], england_affinity)

        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord,
            world_row_i=1,
            world_col_i=1,
            attacker_affinity=france_affinity,
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert set([a.name for a in defense.affinities]) == {
            england_affinity.name,
            france_affinity.name,
        }
        assert set([f.id for f in defense.all_fighters]) == set(
            all_england_fighter_ids + all_france_fighter_ids
        )
        assert set([f.id for f in defense.ready_fighters]) == set(
            all_england_fighter_ids + all_france_fighter_ids
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set() == set([f.id for f in attack.ready_fighters])
        # assert set(all_france_fighter_ids) == set([f.id for f in attack.in_conflicts])
        assert france_fighters[0].id in defense.helpers
        assert france_fighters[1].id in defense.helpers
        assert france_fighters[2].id not in defense.helpers
        assert france_fighters[3].id not in defense.helpers
        assert france_fighters[4].id not in defense.helpers

    def test_unit__fight_description__ok__simple_armies_opposition_with_fighter_indirect_conflict(
        self,
        worldmapc_arthur_model: CharacterModel,
        england_affinity: AffinityDocument,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
        burgundian_affinity: AffinityDocument,
        burgundian_warlord: CharacterModel,
        burgundian_fighters: typing.List[CharacterModel],
    ) -> None:
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, arthur, england_affinity)
        self._active_relation_with(kernel, arthur, burgundian_affinity)
        self._active_relation_with(kernel, france_fighters[0], burgundian_affinity)
        self._active_relation_with(kernel, france_fighters[1], burgundian_affinity)

        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=england_warlord,
            world_row_i=1,
            world_col_i=1,
            attacker_affinity=france_affinity,
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        all_england_fighter_ids = [england_warlord.id] + [
            f.id for f in england_fighters
        ]
        all_burgundian_fighter_ids = [burgundian_warlord.id] + [
            f.id for f in burgundian_fighters
        ]
        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert set([a.name for a in defense.affinities]) == {
            england_affinity.name,
            burgundian_affinity.name,
            france_affinity.name,
        }
        assert set([f.id for f in defense.all_fighters]) == set(
            all_england_fighter_ids
            + all_burgundian_fighter_ids
            + all_france_fighter_ids
            + [arthur.id]
        )
        assert set([f.id for f in defense.ready_fighters]) == set(
            all_england_fighter_ids
            + all_burgundian_fighter_ids
            + all_france_fighter_ids
            + [arthur.id]
        )

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert france_affinity.name == attack.affinity.name
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set() == set([f.id for f in attack.ready_fighters])
        # assert set(all_france_fighter_ids) == set([f.id for f in attack.in_conflicts])
        assert france_fighters[0].id in defense.helpers
        assert france_fighters[1].id in defense.helpers
        assert france_fighters[2].id not in defense.helpers
        assert france_fighters[3].id not in defense.helpers
        assert france_fighters[4].id not in defense.helpers

    def test_unit__fight_description__ok__one_armies_vs_alone_guy(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        arthur = worldmapc_arthur_model
        defense = worldmapc_kernel.fight_lib.get_defense_description(
            origin_target=arthur, world_row_i=1, world_col_i=1
        )
        attack = worldmapc_kernel.fight_lib.get_attack_description(
            target=defense, attacker=france_affinity, world_row_i=1, world_col_i=1
        )

        assert not defense.affinities
        assert not defense.helpers
        assert {arthur.id} == set([f.id for f in defense.all_fighters])
        assert {arthur.id} == set([f.id for f in defense.ready_fighters])

        all_france_fighter_ids = [france_warlord.id] + [f.id for f in france_fighters]
        assert france_affinity.id == attack.affinity.id
        assert set(all_france_fighter_ids) == set([f.id for f in attack.all_fighters])
        assert set(all_france_fighter_ids) == set([f.id for f in attack.ready_fighters])

    def _active_relation_with(
        self, kernel: Kernel, character: CharacterModel, affinity: AffinityDocument
    ) -> None:
        kernel.server_db_session.add(
            AffinityRelationDocument(
                affinity_id=affinity.id,
                character_id=character.id,
                accepted=True,
                fighter=True,
                status_id=MEMBER_STATUS[0],
            )
        )
        kernel.server_db_session.commit()

    @pytest.mark.parametrize(
        "weapons,defense,evades,protect,damages,story,injury",
        [
            (
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                },
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                },
                {"france_warlord0": True, "england_warlord0": True},
                {
                    "france_warlord0": (Weapon(name="Peau nue"), 1.0),
                    "england_warlord0": (Weapon(name="Peau nue"), 0.8),
                },
                {"france_warlord0": 0.8, "england_warlord0": 1.0},
                [
                    "Un affrontement débute: 1 combattant(s) se lance(nt) à l'assault de 1 combattant(s).",
                    "FranceWarlord0 attaque EnglandWarlord0 avec Main nue mais EnglandWarlord0 parvient à esquiver.",
                    "EnglandWarlord0 attaque FranceWarlord0 avec Main nue mais FranceWarlord0 parvient à esquiver.",
                ],
                {"england_warlord0": 0.0, "france_warlord0": 0.0},
            ),
            (
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                },
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                },
                {"france_warlord0": False, "england_warlord0": False},
                {
                    "france_warlord0": (Weapon(name="Peau nue"), 0.0),
                    "england_warlord0": (Weapon(name="Peau nue"), 0.7),
                },
                {"france_warlord0": 0.8, "england_warlord0": 1.0},
                [
                    "Un affrontement débute: 1 combattant(s) se lance(nt) à l'assault de 1 combattant(s).",
                    "FranceWarlord0 attaque EnglandWarlord0 avec Main nue. Peau nue à en partie protégé EnglandWarlord0.",
                    "EnglandWarlord0 attaque FranceWarlord0 avec Main nue. Peau nue à protégé FranceWarlord0.",
                ],
                {"england_warlord0": 0.7, "france_warlord0": 0.0},
            ),
            (
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                },
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                },
                {"france_warlord0": False, "england_warlord0": False},
                {
                    "france_warlord0": (Weapon(name="Peau nue"), 0.0),
                    "england_warlord0": (Weapon(name="Peau nue"), 100.0),
                },
                {"france_warlord0": 100.0, "england_warlord0": 1.0},
                [
                    "Un affrontement débute: 1 combattant(s) se lance(nt) à l'assault de 1 combattant(s).",
                    "FranceWarlord0 attaque EnglandWarlord0 avec Main nue. Peau nue n'a en rien protégé EnglandWarlord0. Le coup à été fatal pour EnglandWarlord0.",
                ],
                {"england_warlord0": 100.0, "france_warlord0": 0.0},
            ),
        ],
    )
    def test_unit__fight__ok__one_vs_one(
        self,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        weapons: typing.Dict[str, Weapon],
        defense: typing.Dict[str, Weapon],
        evades: typing.Dict[str, bool],
        protect: typing.Dict[str, typing.Tuple[Weapon, float]],
        damages: typing.Dict[str, float],
        story: typing.List[str],
        injury: typing.Dict[str, float],
    ) -> None:
        expected_life_points = {}
        for character_id, damage in injury.items():
            character_doc = worldmapc_kernel.character_lib.get_document(character_id)
            expected_life_points[character_id] = (
                float(character_doc.life_points) - damage
            )

        with patch_fight(
            weapons=weapons,
            defense=defense,
            evades=evades,
            protect=protect,
            damages=damages,
        ):
            produced_story = worldmapc_kernel.fight_lib.fight(
                attack=AttackDescription(
                    all_fighters=[france_warlord], ready_fighters=[france_warlord]
                ),
                defense=DefendDescription(
                    all_fighters=[england_warlord],
                    ready_fighters=[england_warlord],
                    affinities=[],
                ),
            )

        assert story == produced_story

        for character_id, expected_life_point in expected_life_points.items():
            character_doc = worldmapc_kernel.character_lib.get_document(character_id)
            assert expected_life_point == float(character_doc.life_points)

    @pytest.mark.parametrize(
        "weapons,defense,evades,protect,damages,story",
        [
            (
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "france_soldier0": Weapon(name="Main nue"),
                    "france_soldier1": Weapon(name="Main nue"),
                    "france_soldier2": Weapon(name="Main nue"),
                    "france_soldier3": Weapon(name="Main nue"),
                    "france_soldier4": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                },
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "france_soldier0": Weapon(name="Main nue"),
                    "france_soldier1": Weapon(name="Main nue"),
                    "france_soldier2": Weapon(name="Main nue"),
                    "france_soldier3": Weapon(name="Main nue"),
                    "france_soldier4": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                },
                {"france_warlord0": True, "england_warlord0": False},
                {
                    "france_warlord0": (Weapon(name="Peau nue"), None),
                    "france_soldier0": (Weapon(name="Peau nue"), None),
                    "france_soldier1": (Weapon(name="Peau nue"), None),
                    "france_soldier2": (Weapon(name="Peau nue"), None),
                    "france_soldier3": (Weapon(name="Peau nue"), None),
                    "france_soldier4": (Weapon(name="Peau nue"), None),
                    "england_warlord0": (Weapon(name="Peau nue"), None),
                },
                {
                    "france_warlord0": 0.5,
                    "france_soldier0": 0.5,
                    "france_soldier1": 0.5,
                    "france_soldier2": 0.5,
                    "france_soldier3": 100.0,  # kill england_warlord0
                    "france_soldier4": 0.5,
                    "england_warlord0": 0.5,
                },
                [
                    "Un affrontement débute: 6 combattant(s) (France) se lance(nt) à l'assault de 1 combattant(s).",
                    "FranceWarlord0 attaque EnglandWarlord0 avec Main nue. Peau nue n'a en rien protégé EnglandWarlord0.",
                    "EnglandWarlord0 attaque FranceWarlord0 avec Main nue mais FranceWarlord0 parvient à esquiver.",
                    "FranceSoldier0 attaque EnglandWarlord0 avec Main nue. Peau nue n'a en rien protégé EnglandWarlord0.",
                    "FranceSoldier1 attaque EnglandWarlord0 avec Main nue. Peau nue n'a en rien protégé EnglandWarlord0.",
                    "FranceSoldier2 attaque EnglandWarlord0 avec Main nue. Peau nue n'a en rien protégé EnglandWarlord0.",
                    "FranceSoldier3 attaque EnglandWarlord0 avec Main nue. Peau nue n'a en rien protégé EnglandWarlord0. Le coup à été fatal pour EnglandWarlord0.",
                ],
            )
        ],
    )
    def test_unit__fight__ok__army_vs_one(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        weapons: typing.Dict[str, Weapon],
        defense: typing.Dict[str, Weapon],
        evades: typing.Dict[str, bool],
        protect: typing.Dict[str, typing.Tuple[Weapon, float]],
        damages: typing.Dict[str, float],
        story: typing.List[str],
    ) -> None:
        with patch_fight(
            weapons=weapons,
            defense=defense,
            evades=evades,
            protect=protect,
            damages=damages,
        ):
            produced_story = worldmapc_kernel.fight_lib.fight(
                attack=AttackDescription(
                    all_fighters=[france_warlord] + france_fighters,
                    ready_fighters=[france_warlord] + france_fighters,
                    affinity=france_affinity,
                ),
                defense=DefendDescription(
                    all_fighters=[england_warlord],
                    ready_fighters=[england_warlord],
                    affinities=[],
                ),
            )

        assert story == produced_story

    @pytest.mark.parametrize(
        "weapons,defense,evades,protect,damages,not_ready,story",
        [
            (
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "france_soldier0": Weapon(name="Main nue"),
                    "france_soldier1": Weapon(name="Main nue"),
                    "france_soldier2": Weapon(name="Main nue"),
                    "france_soldier3": Weapon(name="Main nue"),
                    "france_soldier4": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                    "england_soldier0": Weapon(name="Main nue"),
                    "england_soldier1": Weapon(name="Main nue"),
                    "england_soldier2": Weapon(name="Main nue"),
                    "england_soldier3": Weapon(name="Main nue"),
                    "england_soldier4": Weapon(name="Main nue"),
                },
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "france_soldier0": Weapon(name="Main nue"),
                    "france_soldier1": Weapon(name="Main nue"),
                    "france_soldier2": Weapon(name="Main nue"),
                    "france_soldier3": Weapon(name="Main nue"),
                    "france_soldier4": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                    "england_soldier0": Weapon(name="Main nue"),
                    "england_soldier1": Weapon(name="Main nue"),
                    "england_soldier2": Weapon(name="Main nue"),
                    "england_soldier3": Weapon(name="Main nue"),
                    "england_soldier4": Weapon(name="Main nue"),
                },
                {
                    "france_warlord0": True,
                    "france_soldier0": True,
                    "france_soldier1": False,
                    "france_soldier2": False,
                    "france_soldier3": False,
                    "france_soldier4": True,
                    "england_warlord0": False,
                    "england_soldier0": True,
                    "england_soldier1": False,
                    "england_soldier2": False,
                    "england_soldier3": False,
                    "england_soldier4": True,
                },
                {
                    "france_warlord0": (Weapon(name="Peau nue"), None),
                    "france_soldier0": (Weapon(name="Peau nue"), None),
                    "france_soldier1": (Weapon(name="Peau nue"), None),
                    "france_soldier2": (Weapon(name="Peau nue"), None),
                    "france_soldier3": (Weapon(name="Peau nue"), None),
                    "france_soldier4": (Weapon(name="Peau nue"), None),
                    "england_warlord0": (Weapon(name="Peau nue"), None),
                    "england_soldier0": (Weapon(name="Peau nue"), None),
                    "england_soldier1": (Weapon(name="Peau nue"), None),
                    "england_soldier2": (Weapon(name="Peau nue"), None),
                    "england_soldier3": (Weapon(name="Peau nue"), None),
                    "england_soldier4": (Weapon(name="Peau nue"), None),
                },
                {
                    "france_warlord0": 0.5,
                    "france_soldier0": 0.5,
                    "france_soldier1": 0.5,
                    "france_soldier2": 0.5,
                    "france_soldier3": 100.0,  # make a kill
                    "france_soldier4": 0.5,
                    "england_warlord0": 1.0,
                    "england_soldier0": 0.7,
                    "england_soldier1": 100.0,  # make a kill
                    "england_soldier2": 0.0,
                    "england_soldier3": 0.8,
                    "england_soldier4": 1.0,
                },
                [],
                [
                    "Un affrontement débute: 6 combattant(s) (France) se lance(nt) à l'assault de 6 combattant(s) (England).",
                    "FranceWarlord0 attaque EnglandWarlord0 avec Main nue. Peau nue n'a en rien protégé EnglandWarlord0.",
                    "EnglandWarlord0 attaque FranceWarlord0 avec Main nue mais FranceWarlord0 parvient à esquiver.",
                    "FranceSoldier0 attaque EnglandSoldier0 avec Main nue mais EnglandSoldier0 parvient à esquiver.",
                    "EnglandSoldier0 attaque FranceSoldier0 avec Main nue mais FranceSoldier0 parvient à esquiver.",
                    "FranceSoldier1 attaque EnglandSoldier1 avec Main nue. Peau nue n'a en rien protégé EnglandSoldier1.",
                    "EnglandSoldier1 attaque FranceSoldier1 avec Main nue. Peau nue n'a en rien protégé FranceSoldier1. Le coup à été fatal pour FranceSoldier1.",
                    "FranceSoldier2 attaque EnglandSoldier2 avec Main nue. Peau nue n'a en rien protégé EnglandSoldier2.",
                    "EnglandSoldier2 attaque FranceSoldier2 avec Main nue. Peau nue à protégé FranceSoldier2.",
                    "FranceSoldier3 attaque EnglandSoldier3 avec Main nue. Peau nue n'a en rien protégé EnglandSoldier3. Le coup à été fatal pour EnglandSoldier3.",
                    "FranceSoldier4 attaque EnglandSoldier4 avec Main nue mais EnglandSoldier4 parvient à esquiver.",
                    "EnglandSoldier4 attaque FranceSoldier4 avec Main nue mais FranceSoldier4 parvient à esquiver.",
                ],
            ),
            (
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "france_soldier4": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                    "england_soldier4": Weapon(name="Main nue"),
                },
                {
                    "france_warlord0": Weapon(name="Main nue"),
                    "france_soldier4": Weapon(name="Main nue"),
                    "england_warlord0": Weapon(name="Main nue"),
                    "england_soldier4": Weapon(name="Main nue"),
                },
                {
                    "france_warlord0": True,
                    "france_soldier4": True,
                    "england_warlord0": False,
                    "england_soldier4": True,
                },
                {
                    "france_warlord0": (Weapon(name="Peau nue"), None),
                    "france_soldier4": (Weapon(name="Peau nue"), None),
                    "england_warlord0": (Weapon(name="Peau nue"), None),
                    "england_soldier4": (Weapon(name="Peau nue"), None),
                },
                {
                    "france_warlord0": 0.5,
                    "france_soldier4": 0.5,
                    "england_warlord0": 1.0,
                    "england_soldier4": 1.0,
                },
                [
                    "france_soldier0",
                    "france_soldier1",
                    "france_soldier2",
                    "france_soldier3",
                    "england_soldier0",
                    "england_soldier1",
                    "england_soldier2",
                    "england_soldier3",
                ],
                [
                    "Un affrontement débute: 2 combattant(s) (France) se lance(nt) à l'assault de 6 combattant(s) (England).",
                    "4 combattant(s) du parti attaqué ne sont pas en état de se battre.",
                    "FranceWarlord0 attaque EnglandWarlord0 avec Main nue. Peau nue n'a en rien protégé EnglandWarlord0.",
                    "EnglandWarlord0 attaque FranceWarlord0 avec Main nue mais FranceWarlord0 parvient à esquiver.",
                    "FranceSoldier4 attaque EnglandSoldier4 avec Main nue mais EnglandSoldier4 parvient à esquiver.",
                    "EnglandSoldier4 attaque FranceSoldier4 avec Main nue mais FranceSoldier4 parvient à esquiver.",
                ],
            ),
            (
                {},
                {},
                {},
                {},
                {},
                [
                    "england_warlord0",
                    "england_soldier0",
                    "england_soldier1",
                    "england_soldier2",
                    "england_soldier3",
                    "england_soldier4",
                ],
                [
                    "Un affrontement débute: 6 combattant(s) (France) se lance(nt) à l'assault de 6 combattant(s) (England).",
                    "Aucun des combattants du parti attaqué n'est en état de se battre. Ils sont à la mercie des attaquants.",
                ],
            ),
        ],
    )
    def test_unit__fight__ok__army_vs_army(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_affinity: AffinityDocument,
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
        weapons: typing.Dict[str, Weapon],
        defense: typing.Dict[str, Weapon],
        evades: typing.Dict[str, bool],
        protect: typing.Dict[str, typing.Tuple[Weapon, float]],
        damages: typing.Dict[str, float],
        not_ready: typing.List[str],
        story: typing.List[str],
    ) -> None:
        with patch_fight(
            weapons=weapons,
            defense=defense,
            evades=evades,
            protect=protect,
            damages=damages,
        ):
            produced_story = worldmapc_kernel.fight_lib.fight(
                attack=AttackDescription(
                    all_fighters=[france_warlord] + france_fighters,
                    ready_fighters=(
                        [france_warlord] if france_warlord.id not in not_ready else []
                    )
                    + ([f for f in france_fighters if f.id not in not_ready]),
                    affinity=france_affinity,
                ),
                defense=DefendDescription(
                    all_fighters=[england_warlord] + england_fighters,
                    ready_fighters=(
                        [england_warlord] if england_warlord.id not in not_ready else []
                    )
                    + ([f for f in england_fighters if f.id not in not_ready]),
                    affinities=[england_affinity],
                ),
            )

        assert story == produced_story

    def test_unit__get_attack_weapon__ok__no_weapon(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel

        weapon = kernel.fight_lib.get_attack_weapon(xena, arthur)
        assert weapon.name == "Main nue"

    def test_unit__get_attack_weapon__ok__haxe(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_xena_haxe_weapon: StuffModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        # need to rebuild model (haxe fixture add it after)
        xena = worldmapc_kernel.character_lib.get(worldmapc_xena_model.id)
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        haxe = worldmapc_xena_haxe_weapon

        weapon = kernel.fight_lib.get_attack_weapon(xena, arthur)
        assert weapon.name == "Hache de pierre"
        assert weapon.sharp == haxe.sharp
        assert weapon.blunt == haxe.blunt
        assert weapon.estoc == haxe.estoc

    @pytest.mark.parametrize(
        "around,damages,expected_damages",
        [
            (AroundPercent.LESS, 5.0, 0.0),
            (
                AroundPercent.IN,
                5.0,
                4.0,
            ),  # 4.0 is obtain by patch of random.randrange (80%)
            (AroundPercent.MORE, 5.0, 5.0),
        ],
    )
    def test_unit__opponent_equipment_protect__ok__haxe__vs__leather_jacket(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_xena_haxe_weapon: StuffModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_arthur_leather_jacket_armor: StuffModel,
        worldmapc_kernel: Kernel,
        around: AroundPercent,
        damages: float,
        expected_damages: float,
    ) -> None:
        # need to rebuild model (haxe fixture add it after)
        xena = worldmapc_kernel.character_lib.get(worldmapc_xena_model.id)
        arthur = worldmapc_kernel.character_lib.get(worldmapc_arthur_model.id)
        kernel = worldmapc_kernel
        haxe = worldmapc_xena_haxe_weapon

        with patch(
            "rolling.model.fight.Weapon._get_around_percent_absorb",
            new=lambda *_, **__: (around, around, around),
        ), patch("random.randrange", new=lambda *_, **__: 80):
            armor, damages = kernel.fight_lib.opponent_equipment_protect(
                arthur, from_=xena, weapon=Weapon("haxe", haxe), damage=damages
            )
            assert damages == expected_damages
