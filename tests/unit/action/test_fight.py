# coding: utf-8
import typing
from unittest.mock import patch

import pytest

from rolling.action.base import ActionDescriptionModel
from rolling.action.fight import AttackCharacterAction
from rolling.action.fight import AttackModel
from rolling.exception import ImpossibleAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.server.document.affinity import MEMBER_STATUS
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.types import ActionType


@pytest.fixture
def attack_action(worldmapc_kernel: Kernel) -> AttackCharacterAction:
    return AttackCharacterAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            id="FIGHT", action_type=ActionType.ATTACK_CHARACTER, base_cost=0.0, properties={}
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

    def test_unit__fight_description__ok__simple_lonely_opposition(
        self,
        france_affinity: AffinityDocument,
        england_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = attack_action.perform(
            france_warlord, with_character=england_warlord, input_=AttackModel(lonely=True)
        )
        assert (
            "Engager ce combat implique de vous battre contre EnglandWarlord0 seul à seul"
            == descr.items[0].text
        )

    def test_unit__fight_description__ok__simple_armies_opposition(
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
        descr = attack_action.perform(
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

    def test_unit__fight_description__ok__armies_opposition_some_less_lp_both(
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

        descr = attack_action.perform(
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

    def test_unit__fight_description__ok__armies_opposition_some_exhausted_both(
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

        descr = attack_action.perform(
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
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = attack_action.perform(
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
        attack_action: AttackCharacterAction,
    ) -> None:
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, arthur, england_affinity)
        self._active_relation_with(kernel, arthur, burgundian_affinity)

        descr = attack_action.perform(
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
            "England, Burgundian" == descr.items[1].text
        )

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

        descr = attack_action.perform(
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

    def test_unit__fight_description__ok__simple_armies_opposition_with_fighter_direct_conflict(
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

        descr = attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Le combat ne peut avoir lieu car des membres de votre parti ont des affinités "
            "avec les defenseurs:" == descr.items[0].text
        )
        assert "- FranceSoldier0, car affilié à: England" == descr.items[1].text
        assert "- FranceSoldier1, car affilié à: England" == descr.items[2].text

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
        attack_action: AttackCharacterAction,
    ) -> None:
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        self._active_relation_with(kernel, arthur, england_affinity)
        self._active_relation_with(kernel, arthur, burgundian_affinity)
        self._active_relation_with(kernel, france_fighters[0], burgundian_affinity)
        self._active_relation_with(kernel, france_fighters[1], burgundian_affinity)

        descr = attack_action.perform(
            france_warlord,
            with_character=england_warlord,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Le combat ne peut avoir lieu car des membres de votre parti ont des affinités "
            "avec les defenseurs:" == descr.items[0].text
        )
        assert "- FranceSoldier0, car affilié à: Burgundian" == descr.items[1].text
        assert "- FranceSoldier1, car affilié à: Burgundian" == descr.items[2].text

    def test_unit__fight_description__ok__one_armies_vs_alone_guy(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        arthur = worldmapc_arthur_model
        descr = attack_action.perform(
            france_warlord,
            with_character=arthur,
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Votre parti est composé de 6 combattat(s) dont 6 en état de combattre"
            == descr.items[0].text
        )
        assert "Le parti adverse compte 1 combattant(s)" == descr.items[1].text

    def test_unit__fight_description__ok__attack_our_guy(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        arthur = worldmapc_arthur_model
        descr = attack_action.perform(
            france_warlord,
            with_character=france_fighters[0],
            input_=AttackModel(as_affinity=france_affinity.id),
        )

        assert (
            "Vous ne pouvez pas attaquer FranceSoldier0 en tant que France car il/elle est "
            "affilié à France" == descr.items[0].text
        )

    def test_unit__fight_description__ok__attacker_is_affiliate_in_opposite_army(
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
            attack_action.perform(
                france_warlord, with_character=england_warlord, input_=AttackModel(lonely=1)
            )
        assert (
            "Vous ne pouvez pas mener cette attaque car parmis les defenseur se trouve des "
            "personnes avec lesquelles vous etes affiliés. Affinités en défense: England, France"
            == str(exc.value)
        )

    def test_unit__check_request__ok__attack_lonely_but_exhausted(
        self,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        france_warlord_doc = worldmapc_kernel.character_lib.get_document(france_warlord.id)
        france_warlord.tiredness = 100
        worldmapc_kernel.server_db_session.add(france_warlord_doc)
        worldmapc_kernel.server_db_session.commit()

        with pytest.raises(ImpossibleAction) as exc:
            attack_action.check_request_is_possible(
                france_warlord, with_character=england_warlord, input_=AttackModel(lonely=1)
            )
        assert "FranceWarlord0 n'est pas en mesure de mener cette attaque !" == str(exc.value)

    def test_unit__check_request__ok__attack_as_affinity_but_all_exhausted(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        france_fighters: typing.List[CharacterModel],
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        france_warlord_doc = worldmapc_kernel.character_lib.get_document(france_warlord.id)
        france_warlord.tiredness = 100
        worldmapc_kernel.server_db_session.add(france_warlord_doc)
        worldmapc_kernel.server_db_session.commit()

        for france_fighter in france_fighters:
            france_fighter_doc = worldmapc_kernel.character_lib.get_document(france_fighter.id)
            france_fighter_doc.tiredness = 100
            worldmapc_kernel.server_db_session.add(france_fighter_doc)

        worldmapc_kernel.server_db_session.commit()

        with pytest.raises(ImpossibleAction) as exc:
            attack_action.check_request_is_possible(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(as_affinity=france_affinity.id),
            )
        assert "Personne n'est en état de se battre actuellement" == str(exc.value)

    def test_unit__check_request__ok__attack_as_affinity_but_target_in_affinity(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        self._active_relation_with(worldmapc_kernel, england_warlord, france_affinity)

        with pytest.raises(ImpossibleAction) as exc:
            attack_action.check_request_is_possible(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(as_affinity=france_affinity.id),
            )
        assert "Vous ne pouvez pas attaquer un membre d'une même affinités" == str(exc.value)

    def test_unit__descriptions__ok__root_description(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = attack_action.perform(
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

    def test_unit__descriptions__ok__attack_lonely(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = attack_action.perform(
            france_warlord, with_character=england_warlord, input_=AttackModel(lonely=1)
        )
        item_urls = [i.form_action for i in descr.items]
        item_labels = [i.label for i in descr.items]

        assert (
            "/character/france_warlord0/with-character-action"
            "/ATTACK_CHARACTER/england_warlord0/FIGHT?&lonely=1&confirm=1" in item_urls
        )

    @pytest.mark.usefixtures("initial_universe_state")
    def test_unit__descriptions__ok__confirm_attack_lonely(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        descr = attack_action.perform(
            france_warlord, with_character=england_warlord, input_=AttackModel(lonely=1, confirm=1)
        )
        f_warlord_e = list(worldmapc_kernel.character_lib.get_last_events(france_warlord.id, 1))
        e_warlord_e = list(worldmapc_kernel.character_lib.get_last_events(england_warlord.id, 1))

        assert f_warlord_e
        assert 1 == len(f_warlord_e)
        assert "Vous avez participé à un combat" == f_warlord_e[0].text
        assert not f_warlord_e[0].unread

        assert e_warlord_e
        assert 1 == len(e_warlord_e)
        assert "Vous avez subit une attaque" == e_warlord_e[0].text
        assert e_warlord_e[0].unread

    @pytest.mark.usefixtures("initial_universe_state")
    def test_unit__descriptions__ok__confirm_attack_lonely_and_dead(
        self,
        france_affinity: AffinityDocument,
        france_warlord: CharacterModel,
        england_warlord: CharacterModel,
        worldmapc_kernel: Kernel,
        attack_action: AttackCharacterAction,
    ) -> None:
        with patch(
            "rolling.server.lib.fight.FightLib.get_damage", new=lambda *_, **__: 1000.0
        ), patch("random.shuffle", new=lambda l: l):
            attack_action.perform(
                france_warlord,
                with_character=england_warlord,
                input_=AttackModel(lonely=1, confirm=1),
            )
            france_warlord_doc = worldmapc_kernel.character_lib.get_document(france_warlord.id)
            england_warlord_doc = worldmapc_kernel.character_lib.get_document(
                england_warlord.id, dead=True
            )

            assert france_warlord_doc.alive
            assert not england_warlord_doc.alive
