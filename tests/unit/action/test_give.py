# coding: utf-8
import pytest

from rolling.action.base import ActionDescriptionModel
from rolling.action.give import GiveToCharacterAction
from rolling.action.give import GiveToModel
from rolling.exception import ImpossibleAction
from rolling.exception import WrongInputError
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType


@pytest.fixture
def give_action(worldmapc_kernel: Kernel) -> GiveToCharacterAction:
    return GiveToCharacterAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            id="GIVE_TO_CHARACTER",
            action_type=ActionType.GIVE_TO_CHARACTER,
            base_cost=0.0,
            properties={},
        ),
    )


class TestGiveAction:
    async def test_unit__list_give__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        give_action: GiveToCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        description = await give_action.perform(xena, arthur, GiveToModel())
        item_label_and_urls = [(i.label, i.form_action) for i in description.items]

        assert (
            "Bouclier de bois",
            "/character/xena/with-character-action/GIVE_TO_CHARACTER/arthur/GIVE_TO_CHARACTER"
            f"?give_stuff_id={worldmapc_xena_wood_shield.id}",
        ) in item_label_and_urls
        assert (
            "Bouclier de bois",
            "/character/xena/with-character-action/GIVE_TO_CHARACTER/arthur/GIVE_TO_CHARACTER"
            f"?give_stuff_id={worldmapc_xena_wood_shield2.id}",
        ) not in item_label_and_urls  # not in because links merged
        assert (
            "Veste de cuir",
            "/character/xena/with-character-action/GIVE_TO_CHARACTER/arthur/GIVE_TO_CHARACTER"
            f"?give_stuff_id={worldmapc_xena_leather_jacket.id}",
        ) in item_label_and_urls
        assert (
            "Bois",
            "/character/xena/with-character-action/GIVE_TO_CHARACTER/arthur/GIVE_TO_CHARACTER"
            "?give_resource_id=WOOD",
        ) in item_label_and_urls

    async def test_unit__list_give_one_then_one_shield__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        give_action: GiveToCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        arthur = worldmapc_arthur_model
        xena = worldmapc_xena_model

        description = await give_action.perform(
            xena, arthur, GiveToModel(give_stuff_id=worldmapc_xena_wood_shield.id)
        )
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "give_stuff_quantity"
        assert description.items[0].form_action == (
            "/character/xena/with-character-action/GIVE_TO_CHARACTER/arthur/GIVE_TO_CHARACTER"
            "?give_stuff_id=1"
        )

        await give_action.perform(
            xena,
            arthur,
            GiveToModel(
                give_stuff_id=worldmapc_xena_wood_shield.id, give_stuff_quantity=1
            ),
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield.id).carried_by_id
            == arthur.id
        )
        assert (
            not kernel.stuff_lib.get_stuff_doc(
                worldmapc_xena_wood_shield2.id
            ).carried_by_id
            == arthur.id
        )

        await give_action.perform(
            xena,
            arthur,
            GiveToModel(
                give_stuff_id=worldmapc_xena_wood_shield.id, give_stuff_quantity=1
            ),
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield.id).carried_by_id
            == arthur.id
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield2.id).carried_by_id
            == arthur.id
        )

    async def test_unit__list_give_two_shields__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        give_action: GiveToCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        description = await give_action.perform(
            xena, arthur, GiveToModel(give_stuff_id=worldmapc_xena_wood_shield.id)
        )
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "give_stuff_quantity"
        assert description.items[0].form_action == (
            "/character/xena/with-character-action/GIVE_TO_CHARACTER/arthur/GIVE_TO_CHARACTER"
            "?give_stuff_id=1"
        )

        await give_action.perform(
            xena,
            arthur,
            GiveToModel(
                give_stuff_id=worldmapc_xena_wood_shield.id, give_stuff_quantity=2
            ),
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield.id).carried_by_id
            == arthur.id
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_wood_shield2.id).carried_by_id
            == arthur.id
        )

    async def test_unit__list_give_one_jacket__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        give_action: GiveToCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        await give_action.perform(
            xena, arthur, GiveToModel(give_stuff_id=worldmapc_xena_leather_jacket.id)
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(
                worldmapc_xena_leather_jacket.id
            ).carried_by_id
            == arthur.id
        )

    async def test_unit__list_give_wood__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood: None,
        give_action: GiveToCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        description = await give_action.perform(
            xena, arthur, GiveToModel(give_resource_id="WOOD")
        )
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "give_resource_quantity"
        assert description.items[0].form_action == (
            "/character/xena/with-character-action/GIVE_TO_CHARACTER/arthur/GIVE_TO_CHARACTER"
            "?give_resource_id=WOOD"
        )

        await give_action.perform(
            xena,
            arthur,
            GiveToModel(give_resource_id="WOOD", give_resource_quantity="0.1"),
        )
        assert kernel.resource_lib.have_resource(
            character_id=arthur.id, resource_id="WOOD", quantity=0.1
        )
        assert kernel.resource_lib.have_resource(
            character_id=xena.id, resource_id="WOOD", quantity=0.1
        )

        await give_action.perform(
            xena,
            arthur,
            GiveToModel(give_resource_id="WOOD", give_resource_quantity="0.1"),
        )
        assert kernel.resource_lib.have_resource(
            character_id=arthur.id, resource_id="WOOD", quantity=0.2
        )
        assert not kernel.resource_lib.have_resource(
            character_id=xena.id, resource_id="WOOD"
        )

    def test_unit__list_give_wood__err__require_more(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood: None,
        give_action: GiveToCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        with pytest.raises(WrongInputError):
            give_action.check_request_is_possible(
                xena,
                arthur,
                GiveToModel(
                    give_resource_id="WOOD",
                    give_resource_quantity="0.21",  # 0.2 in fixtures
                ),
            )

    def test_unit__list_give_shield__err__require_more(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        give_action: GiveToCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        with pytest.raises(WrongInputError):
            give_action.check_request_is_possible(
                xena,
                arthur,
                GiveToModel(
                    give_stuff_id=worldmapc_xena_wood_shield.id, give_stuff_quantity=2
                ),
            )

    def test_unit__list_give_shield__err__dont_have(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        give_action: GiveToCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        with pytest.raises(ImpossibleAction):
            give_action.check_request_is_possible(
                xena, arthur, GiveToModel(give_stuff_id=42, give_stuff_quantity=1)
            )
