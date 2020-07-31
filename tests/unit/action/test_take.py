# coding: utf-8
import pytest

from rolling.action.base import ActionDescriptionModel
from rolling.action.take import TakeFromCharacterAction
from rolling.action.take import TakeFromModel
from rolling.exception import ImpossibleAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType


@pytest.fixture
def take_action(worldmapc_kernel: Kernel) -> TakeFromCharacterAction:
    return TakeFromCharacterAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            id="TAKE_FROM_CHARACTER",
            action_type=ActionType.TAKE_FROM_CHARACTER,
            base_cost=0.0,
            properties={},
        ),
    )


class TestTakeAction:
    def _apply_low_lp(self, kernel: Kernel, character: CharacterModel) -> CharacterModel:
        doc = kernel.character_lib.get_document(character.id)
        doc.life_points = 0.1
        kernel.server_db_session.add(doc)
        kernel.server_db_session.commit()
        return kernel.character_lib.get(character.id)

    def test_unit__take_is_possible__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # set xena LP very low to be vulnerable
        xena = self._apply_low_lp(kernel, xena)

        take_action.check_is_possible(arthur, xena)

    def test_unit__take_is_possible__err_xena_not_vulnerable(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        with pytest.raises(ImpossibleAction) as caught:
            take_action.check_is_possible(arthur, xena)

        assert str(caught.value) == "xena est en capacité de se defendre"

    def test_unit__list_take__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = self._apply_low_lp(kernel, worldmapc_xena_model)
        arthur = worldmapc_arthur_model

        description = take_action.perform(arthur, xena, TakeFromModel())
        item_label_and_urls = [(i.label, i.form_action) for i in description.items]

        assert (
            "Prendre Bouclier de bois",
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            f"?take_stuff_id={worldmapc_xena_wood_shield.id}",
        ) in item_label_and_urls
        assert (
            "Prendre Bouclier de bois",
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            f"?take_stuff_id={worldmapc_xena_wood_shield2.id}",
        ) not in item_label_and_urls  # not in because links merged
        assert (
            "Prendre Veste de cuir",
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            f"?take_stuff_id={worldmapc_xena_leather_jacket.id}",
        ) in item_label_and_urls
        assert (
            "Prendre Bois",
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            "?take_resource_id=WOOD",
        ) in item_label_and_urls

    def test_unit__list_take_one_then_one_shield__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = self._apply_low_lp(kernel, worldmapc_xena_model)
        arthur = worldmapc_arthur_model

        description = take_action.perform(
            arthur, xena, TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id)
        )
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "take_stuff_quantity"
        assert description.items[0].form_action == (
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            "?take_stuff_id=1"
        )

        take_action.perform(
            arthur,
            xena,
            TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id, take_stuff_quantity=1),
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield.id).carried_by_id == arthur.id
        )
        assert (
            not kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield2.id).carried_by_id
            == arthur.id
        )

        take_action.perform(
            arthur,
            xena,
            TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id, take_stuff_quantity=1),
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield.id).carried_by_id == arthur.id
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield2.id).carried_by_id
            == arthur.id
        )

    def test_unit__list_take_two_shields__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = self._apply_low_lp(kernel, worldmapc_xena_model)
        arthur = worldmapc_arthur_model

        description = take_action.perform(
            arthur, xena, TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id)
        )
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "take_stuff_quantity"
        assert description.items[0].form_action == (
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            "?take_stuff_id=1"
        )

        take_action.perform(
            arthur,
            xena,
            TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id, take_stuff_quantity=2),
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield.id).carried_by_id == arthur.id
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield2.id).carried_by_id
            == arthur.id
        )

    def test_unit__list_take_one_jacket__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = self._apply_low_lp(kernel, worldmapc_xena_model)
        arthur = worldmapc_arthur_model

        take_action.perform(
            arthur, xena, TakeFromModel(take_stuff_id=worldmapc_xena_leather_jacket.id)
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_leather_jacket.id).carried_by_id
            == arthur.id
        )

    def test_unit__list_take_wood__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood: None,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = self._apply_low_lp(kernel, worldmapc_xena_model)
        arthur = worldmapc_arthur_model

        description = take_action.perform(arthur, xena, TakeFromModel(take_resource_id="WOOD"))
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "take_resource_quantity"
        assert description.items[0].form_action == (
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            "?take_resource_id=WOOD"
        )

        take_action.perform(
            arthur, xena, TakeFromModel(take_resource_id="WOOD", take_resource_quantity=0.1)
        )
        assert kernel.resource_lib.have_resource(arthur.id, resource_id="WOOD", quantity=0.1)
        assert kernel.resource_lib.have_resource(xena.id, resource_id="WOOD", quantity=0.1)

        take_action.perform(
            arthur, xena, TakeFromModel(take_resource_id="WOOD", take_resource_quantity=0.1)
        )
        assert kernel.resource_lib.have_resource(arthur.id, resource_id="WOOD", quantity=0.2)
        assert not kernel.resource_lib.have_resource(xena.id, resource_id="WOOD")

    def test_unit__list_take_wood__err__require_more(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood: None,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = self._apply_low_lp(kernel, worldmapc_xena_model)
        arthur = worldmapc_arthur_model

        with pytest.raises(ImpossibleAction):
            take_action.check_request_is_possible(
                arthur,
                xena,
                TakeFromModel(
                    take_resource_id="WOOD", take_resource_quantity=0.21  # 0.2 in fixtures
                ),
            )

    def test_unit__list_take_shield__err__require_more(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = self._apply_low_lp(kernel, worldmapc_xena_model)
        arthur = worldmapc_arthur_model

        with pytest.raises(ImpossibleAction):
            take_action.check_request_is_possible(
                arthur,
                xena,
                TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id, take_stuff_quantity=2),
            )

    def test_unit__list_take_shield__err__dont_have(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        take_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = self._apply_low_lp(kernel, worldmapc_xena_model)
        arthur = worldmapc_arthur_model

        with pytest.raises(ImpossibleAction):
            take_action.check_request_is_possible(
                arthur, xena, TakeFromModel(take_stuff_id=42, take_stuff_quantity=1)
            )
