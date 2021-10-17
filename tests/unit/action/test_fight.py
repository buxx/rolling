# coding: utf-8
import itertools
import pytest
import random
from sqlalchemy.orm.exc import NoResultFound
import typing
from unittest.mock import patch

from rolling.action.base import ActionDescriptionModel
from rolling.action.fight import AttackCharacterAction
from rolling.action.fight import AttackModel
from rolling.exception import ImpossibleAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.affinity import MEMBER_STATUS
from tests.fixtures import create_stuff


@pytest.fixture
def attack_action(worldmapc_kernel: Kernel) -> AttackCharacterAction:
    return AttackCharacterAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            id="FIGHT",
            action_type=ActionType.ATTACK_CHARACTER,
            base_cost=0.0,
            properties={},
        ),
    )


class TestFightAction:
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

    async def test_unit__fight_description__ok__simple_lonely_opposition(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(lonely=True),
        )
        assert (
            "Engager ce combat implique de vous battre contre EnglandWarlord0 seul à seul"
            == descr.items[0].text
        )

    async def test_unit__fight_description__ok__simple_armies_opposition(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Votre parti est composé de 6 combattat(s) dont 6 en état de combattre"
            == descr.items[0].text
        )
        assert (
            "Le parti adverse compte 6 combattant(s) représenté(s) par le/les afinité(s): England"
            == descr.items[1].text
        )

    async def test_unit__fight_description__ok__armies_opposition_some_less_lp_both(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        for fighter in france_fighters[0:3] + england_fighters[0:3]:
            fighter.life_points = 0.5
            worldmapc_kernel.character_lib.reduce_life_points(fighter.id, 4.5)

        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Votre parti est composé de 6 combattat(s) dont 3 en état de combattre"
            == descr.items[0].text
        )
        assert (
            # Attacker can't know how many defender is not ready for battle
            "Le parti adverse compte 6 combattant(s) représenté(s) par le/les afinité(s): England"
            == descr.items[1].text
        )

    async def test_unit__fight_description__ok__armies_opposition_some_exhausted_both(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        for fighter in france_fighters[0:3] + england_fighters[0:3]:
            fighter.tiredness = 100
            worldmapc_kernel.character_lib.increase_tiredness(fighter.id, 100)

        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Votre parti est composé de 6 combattat(s) dont 3 en état de combattre"
            == descr.items[0].text
        )
        assert (
            # Attacker can't know how many defender is not ready for battle
            "Le parti adverse compte 6 combattant(s) représenté(s) par le/les afinité(s): England"
            == descr.items[1].text
        )

    async def test_unit__fight_description__ok__one_army_vs_2_armies_opposition_but_no_participate(
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
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Votre parti est composé de 6 combattat(s) dont 6 en état de combattre"
            == descr.items[0].text
        )
        assert (
            "Le parti adverse compte 6 combattant(s) représenté(s) par le/les afinité(s): England"
            == descr.items[1].text
        )

    async def test_unit__fight_description__ok__one_army_vs_2_armies_opposition_and_participate(
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
        attack_action: AttackCharacterAction,
    ) -> None:
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, arthur, england_affinity)
        self._active_relation_with(kernel, arthur, burgundian_affinity)

        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Votre parti est composé de 6 combattat(s) dont 6 en état de combattre"
            == descr.items[0].text
        )
        assert (
            "Le parti adverse compte 13 combattant(s) représenté(s) par le/les afinité(s): "
            in descr.items[1].text
        )
        assert (
            "England, Burgundian" in descr.items[1].text
            or "Burgundian, England" in descr.items[1].text
        )

    async def test_unit__fight_description__ok__one_army_vs_2_armies_opposition_and_no_participate_because_link_not_here(
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
        attack_action: AttackCharacterAction,
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

        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Votre parti est composé de 6 combattat(s) dont 6 en état de combattre"
            == descr.items[0].text
        )
        assert (
            "Le parti adverse compte 6 combattant(s) représenté(s) par le/les afinité(s): England"
            == descr.items[1].text
        )

    async def test_unit__fight_description__ok__simple_armies_opposition_with_fighter_direct_conflict(
        self,
        england_affinity: AffinityDocument,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, france_fighters[0], england_affinity)
        self._active_relation_with(kernel, france_fighters[1], england_affinity)

        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert [
            "Vous ne pouvez pas mener cette attaque car certains de vos combattants ont des"
            " liens d'affinités avec un ou des combattants de la défense.",
            "- FranceSoldier0 à cause de son lien avec England",
            "- FranceSoldier1 à cause de son lien avec England",
        ] == [item.text for item in descr.items]

    async def test_unit__fight_description__ok__simple_armies_opposition_with_fighter_indirect_conflict(
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
        attack_action: AttackCharacterAction,
    ) -> None:
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, arthur, england_affinity)
        self._active_relation_with(kernel, arthur, burgundian_affinity)
        self._active_relation_with(kernel, france_fighters[0], burgundian_affinity)
        self._active_relation_with(kernel, france_fighters[1], burgundian_affinity)

        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert [
            "Vous ne pouvez pas mener cette attaque car certains de vos combattants ont des liens"
            " d'affinités avec un ou des combattants de la défense.",
            "- FranceSoldier0 à cause de son lien avec Burgundian",
            "- FranceSoldier1 à cause de son lien avec Burgundian",
        ] == [item.text for item in descr.items]

    async def test_unit__fight_description__ok__one_armies_vs_alone_guy(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        arthur = worldmapc_arthur_model
        descr = await attack_action.perform(
            france_warlord,
            with_character=arthur,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Votre parti est composé de 6 combattat(s) dont 6 en état de combattre"
            == descr.items[0].text
        )
        assert "Le parti adverse compte 1 combattant(s)" == descr.items[1].text

    async def test_unit__fight_description__ok__attack_our_guy(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        arthur = worldmapc_arthur_model
        descr = await attack_action.perform(
            france_warlord,
            with_character=france_fighters[0],
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Vous ne pouvez pas attaquer FranceSoldier0 en tant que France car il/elle est "
            "affilié à France" == descr.items[0].text
        )

    async def test_unit__fight_description__ok__attacker_is_affiliate_in_opposite_army(
        self,
        england_affinity: AffinityDocument,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        england_fighters: typing.List[CharacterModel],
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, france_warlord, england_affinity)

        with pytest.raises(ImpossibleAction) as exc:
            await attack_action.perform(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(lonely=1),
            )
        assert (
            "Vous ne pouvez pas mener cette attaque car parmis les defenseur se trouve des "
            "personnes avec lesquelles vous etes affiliés. Affinités en défense: England, France"
            == str(exc.value)
        )

    async def test_unit__check_request__ok__attack_lonely_but_exhausted(
        self,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        france_warlord_doc = worldmapc_kernel.character_lib.get_document(
            france_warlord.id
        )
        france_warlord.tiredness = 100
        worldmapc_kernel.server_db_session.add(france_warlord_doc)
        worldmapc_kernel.server_db_session.commit()

        with pytest.raises(ImpossibleAction) as exc:
            await attack_action.check_request_is_possible(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(lonely=1),
            )
        assert "FranceWarlord0 n'est pas en mesure de mener cette attaque !" == str(
            exc.value
        )

    async def test_unit__check_request__ok__attack_as_affinity_but_all_exhausted(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        france_warlord_doc = worldmapc_kernel.character_lib.get_document(
            france_warlord.id
        )
        france_warlord_doc.tiredness = 100
        worldmapc_kernel.server_db_session.add(france_warlord_doc)
        worldmapc_kernel.server_db_session.commit()

        for france_fighter in france_fighters:
            france_fighter_doc = worldmapc_kernel.character_lib.get_document(
                france_fighter.id
            )
            france_fighter_doc.tiredness = 100
            worldmapc_kernel.server_db_session.add(france_fighter_doc)

        worldmapc_kernel.server_db_session.commit()

        with pytest.raises(ImpossibleAction) as exc:
            await attack_action.check_request_is_possible(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(as_affinity=france_affinity.id),
            )
        assert "Personne n'est en état de se battre actuellement" == str(exc.value)

    async def test_unit__check_request__ok__attack_as_affinity_but_target_in_affinity(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        self._active_relation_with(worldmapc_kernel, england_warlord, france_affinity)

        with pytest.raises(ImpossibleAction) as exc:
            await attack_action.check_request_is_possible(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(as_affinity=france_affinity.id),
            )
        assert "Vous ne pouvez pas attaquer un membre d'une même affinités" == str(
            exc.value
        )

    async def test_unit__descriptions__ok__root_description(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = await attack_action.perform(
            france_warlord, with_character=england_warlord, input_=AttackModel()
        )
        item_urls = [i.form_action for i in descr.items]
        item_labels = [i.label for i in descr.items]

        assert "Attaquer seul et en mon nom uniquement" in item_labels
        assert (
            "/character/france_warlord0/with-character-action/"
            "ATTACK_CHARACTER/england_warlord0/FIGHT?&lonely=1" in item_urls
        )

        assert "Attaquer en tant que France" in item_labels
        assert (
            "/character/france_warlord0/with-character-action/"
            "ATTACK_CHARACTER/england_warlord0/FIGHT?&as_affinity=1" in item_urls
        )

    async def test_unit__descriptions__ok__attack_lonely(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = await attack_action.perform(
            france_warlord, with_character=england_warlord, input_=AttackModel(lonely=1)
        )
        item_urls = [i.form_action for i in descr.items]
        item_labels = [i.label for i in descr.items]

        assert (
            "/character/france_warlord0/with-character-action"
            "/ATTACK_CHARACTER/england_warlord0/FIGHT?&lonely=1&confirm=1" in item_urls
        )

    @pytest.mark.usefixtures("initial_universe_state")
    async def test_unit__descriptions__ok__confirm_attack_lonely(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = await attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(lonely=1, confirm=1),
        )
        f_warlord_e = list(
            worldmapc_kernel.character_lib.get_last_events(france_warlord.id, 1)
        )
        e_warlord_e = list(
            worldmapc_kernel.character_lib.get_last_events(england_warlord.id, 1)
        )

        assert f_warlord_e
        assert 1 == len(f_warlord_e)
        assert "Vous avez participé à un combat" == f_warlord_e[0].text
        assert not f_warlord_e[0].unread

        assert e_warlord_e
        assert 1 == len(e_warlord_e)
        assert "Vous avez subit une attaque" == e_warlord_e[0].text
        assert e_warlord_e[0].unread

    @pytest.mark.usefixtures("initial_universe_state")
    async def test_unit__descriptions__ok__confirm_attack_lonely_and_dead(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        with patch(
            "rolling.server.lib.fight.FightLib.get_damage", new=lambda *_, **__: 1000.0
        ), patch("random.shuffle", new=lambda l: l), patch(
            "random.randrange", new=lambda *_, **__: 100
        ), patch(
            "rolling.server.lib.fight.FightLib.defenser_evade",
            new=lambda *_, **__: False,
        ):
            await attack_action.perform(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(lonely=1, confirm=1),
            )
            france_warlord_doc = worldmapc_kernel.character_lib.get_document(
                france_warlord.id
            )
            england_warlord_doc = worldmapc_kernel.character_lib.get_document(
                england_warlord.id, dead=True
            )

            assert france_warlord_doc.alive
            assert not england_warlord_doc.alive

    # @pytest.mark.timeout(10.0)
    @pytest.mark.usefixtures("initial_universe_state")
    @pytest.mark.parametrize(
        "seed,frw_weapon,frw_shield,frw_armor,enw_weapon,enw_shield,enw_armor",
        itertools.chain(
            *[
                [
                    (seed, "", "", "", "", "", ""),
                    (seed, "STONE_HAXE", "WOOD_SHIELD", "LEATHER_JACKET", "", "", ""),
                    (seed, "", "", "", "STONE_HAXE", "WOOD_SHIELD", "LEATHER_JACKET"),
                    (
                        seed,
                        "STONE_HAXE",
                        "WOOD_SHIELD",
                        "LEATHER_JACKET",
                        "STONE_HAXE",
                        "WOOD_SHIELD",
                        "LEATHER_JACKET",
                    ),
                ]
                for seed in [random.randint(1, 1000) for _ in range(3)]
            ]
        ),
    )
    async def test_fight_to_death__one_vs_one(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
        seed: int,
        frw_weapon: str,
        frw_shield: str,
        frw_armor: str,
        enw_weapon: str,
        enw_shield: str,
        enw_armor: str,
    ) -> None:
        kernel = worldmapc_kernel
        random.seed(seed)

        if frw_weapon:
            stuff = create_stuff(kernel, frw_weapon)
            kernel.stuff_lib.set_carried_by(stuff.id, france_warlord.id)
            kernel.stuff_lib.set_as_used_as_weapon(france_warlord.id, stuff.id)

        if frw_shield:
            stuff = create_stuff(kernel, frw_shield)
            kernel.stuff_lib.set_carried_by(stuff.id, france_warlord.id)
            kernel.stuff_lib.set_as_used_as_shield(france_warlord.id, stuff.id)

        if frw_armor:
            stuff = create_stuff(kernel, frw_armor)
            kernel.stuff_lib.set_carried_by(stuff.id, france_warlord.id)
            kernel.stuff_lib.set_as_used_as_armor(france_warlord.id, stuff.id)

        if enw_weapon:
            stuff = create_stuff(kernel, enw_weapon)
            kernel.stuff_lib.set_carried_by(stuff.id, england_warlord.id)
            kernel.stuff_lib.set_as_used_as_weapon(england_warlord.id, stuff.id)

        if enw_shield:
            stuff = create_stuff(kernel, enw_shield)
            kernel.stuff_lib.set_carried_by(stuff.id, england_warlord.id)
            kernel.stuff_lib.set_as_used_as_shield(england_warlord.id, stuff.id)

        if enw_armor:
            stuff = create_stuff(kernel, enw_armor)
            kernel.stuff_lib.set_carried_by(stuff.id, england_warlord.id)
            kernel.stuff_lib.set_as_used_as_armor(england_warlord.id, stuff.id)

        while True:
            try:
                france_warlord_doc = worldmapc_kernel.character_lib.get_document(
                    france_warlord.id
                )
                france_warlord = worldmapc_kernel.character_lib.get(france_warlord.id)
                if not france_warlord.is_attack_ready():
                    return
            except NoResultFound:
                worldmapc_kernel.character_lib.get_document(
                    france_warlord.id, dead=True
                )
                return

            try:
                england_warlord_doc = worldmapc_kernel.character_lib.get_document(
                    england_warlord.id
                )
                england_warlord = worldmapc_kernel.character_lib.get(england_warlord.id)
                if not england_warlord.is_attack_ready():
                    return
            except NoResultFound:
                worldmapc_kernel.character_lib.get_document(
                    england_warlord.id, dead=True
                )
                return

            france_warlord_doc.action_points = 24.0
            england_warlord_doc.action_points = 24.0
            france_warlord_doc.tiredness = 0.0
            england_warlord_doc.tiredness = 0.0

            worldmapc_kernel.server_db_session.add(france_warlord_doc)
            worldmapc_kernel.server_db_session.add(england_warlord_doc)
            worldmapc_kernel.server_db_session.commit()

            await attack_action.perform(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(lonely=1, confirm=1),
            )
