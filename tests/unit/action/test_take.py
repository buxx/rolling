# coding: utf-8
import pytest
import typing

from rolling.action.base import ActionDescriptionModel
from rolling.action.take_character import TakeFromCharacterAction
from rolling.action.take_character import TakeFromModel
from rolling.exception import WrongInputError
from rolling.action.take_resource import TakeResourceAction, TakeResourceModel
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityJoinType
from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.affinity import MEMBER_STATUS


@pytest.fixture
def take_from_character_action(worldmapc_kernel: Kernel) -> TakeFromCharacterAction:
    return TakeFromCharacterAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            id="TAKE_FROM_CHARACTER",
            action_type=ActionType.TAKE_FROM_CHARACTER,
            base_cost=0.0,
            properties={},
        ),
    )


@pytest.fixture
def take_resource_action(worldmapc_kernel: Kernel) -> TakeResourceAction:
    return TakeResourceAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            id="TAKE_RESOURCE",
            action_type=ActionType.TAKE_RESOURCE,
            base_cost=0.0,
            properties={},
        ),
    )


ModifierType = typing.Callable[
    ["TestTakeAction", Kernel, CharacterModel, CharacterModel], CharacterModel
]


class TestTakeFromCharacterAction:
    def _apply_low_lp(
        self, kernel: Kernel, xena: CharacterModel, arthur: CharacterModel
    ) -> CharacterModel:
        doc = kernel.character_lib.get_document(xena.id)
        doc.life_points = 0.1
        kernel.server_db_session.add(doc)
        kernel.server_db_session.commit()
        return kernel.character_lib.get(xena.id)

    def _apply_shares(
        self, kernel: Kernel, xena: CharacterModel, arthur: CharacterModel
    ) -> CharacterModel:
        affinity_doc = kernel.affinity_lib.create(
            "MyAffinity",
            join_type=AffinityJoinType.ACCEPT_ALL,
            direction_type=AffinityDirectionType.ONE_DIRECTOR,
        )
        kernel.affinity_lib.join(
            xena.id, affinity_doc.id, accepted=True, status_id=MEMBER_STATUS[0]
        )
        kernel.affinity_lib.join(
            arthur.id, affinity_doc.id, accepted=True, status_id=CHIEF_STATUS[0]
        )

        for stuff in kernel.stuff_lib.get_carried_by(xena.id):
            kernel.stuff_lib.set_shared_with_affinity(stuff.id, affinity_doc.id)

        for carried_resource in kernel.resource_lib.get_carried_by(xena.id):
            kernel.resource_lib.reduce_carried_by(
                character_id=xena.id,
                resource_id=carried_resource.id,
                quantity=carried_resource.quantity,
                exclude_shared_with_affinity=True,
            )
            kernel.resource_lib.add_resource_to(
                character_id=xena.id,
                resource_id=carried_resource.id,
                quantity=carried_resource.quantity,
                shared_with_affinity_id=affinity_doc.id,
            )

        return xena

    def test_unit__take_is_possible__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        take_from_character_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # set xena LP very low to be vulnerable
        xena = self._apply_low_lp(kernel, xena, arthur)

        take_from_character_action.check_is_possible(arthur, xena)

    def test_unit__take_is_possible__err_xena_not_vulnerable(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        take_from_character_action: TakeFromCharacterAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        with pytest.raises(WrongInputError) as caught:
            take_from_character_action.check_is_possible(arthur, xena)

        assert str(caught.value) == "arthur ne peut contraindre xena"

    @pytest.mark.parametrize("modifier", [_apply_low_lp, _apply_shares])
    def test_unit__list_take__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        take_from_character_action: TakeFromCharacterAction,
        modifier: ModifierType,
    ) -> None:
        kernel = worldmapc_kernel
        xena = modifier(self, kernel, worldmapc_xena_model, worldmapc_arthur_model)
        arthur = worldmapc_arthur_model

        description = take_from_character_action.perform(arthur, xena, TakeFromModel())
        item_label_and_urls = [(i.label, i.form_action) for i in description.items]

        assert (
            "Bouclier de bois",
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            f"?take_stuff_id={worldmapc_xena_wood_shield.id}",
        ) in item_label_and_urls
        assert (
            "Bouclier de bois",
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            f"?take_stuff_id={worldmapc_xena_wood_shield2.id}",
        ) not in item_label_and_urls  # not in because links merged
        assert (
            "Veste de cuir",
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            f"?take_stuff_id={worldmapc_xena_leather_jacket.id}",
        ) in item_label_and_urls
        assert (
            "Bois",
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            "?take_resource_id=WOOD",
        ) in item_label_and_urls

    @pytest.mark.parametrize("modifier", [_apply_low_lp, _apply_shares])
    def test_unit__list_take_one_then_one_shield__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        take_from_character_action: TakeFromCharacterAction,
        modifier: ModifierType,
    ) -> None:
        kernel = worldmapc_kernel
        xena = modifier(self, kernel, worldmapc_xena_model, worldmapc_arthur_model)
        arthur = worldmapc_arthur_model

        description = take_from_character_action.perform(
            arthur, xena, TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id)
        )
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "take_stuff_quantity"
        assert description.items[0].form_action == (
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            "?take_stuff_id=1"
        )

        take_from_character_action.perform(
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

        take_from_character_action.perform(
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

    @pytest.mark.parametrize("modifier", [_apply_low_lp, _apply_shares])
    def test_unit__list_take_two_shields__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_xena_wood_shield2: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        take_from_character_action: TakeFromCharacterAction,
        modifier: ModifierType,
    ) -> None:
        kernel = worldmapc_kernel
        xena = modifier(self, kernel, worldmapc_xena_model, worldmapc_arthur_model)
        arthur = worldmapc_arthur_model

        description = take_from_character_action.perform(
            arthur, xena, TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id)
        )
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "take_stuff_quantity"
        assert description.items[0].form_action == (
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            "?take_stuff_id=1"
        )

        take_from_character_action.perform(
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

    @pytest.mark.parametrize("modifier", [_apply_low_lp, _apply_shares])
    def test_unit__list_take_one_jacket__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood: None,
        take_from_character_action: TakeFromCharacterAction,
        modifier: ModifierType,
    ) -> None:
        kernel = worldmapc_kernel
        xena = modifier(self, kernel, worldmapc_xena_model, worldmapc_arthur_model)
        arthur = worldmapc_arthur_model

        take_from_character_action.perform(
            arthur, xena, TakeFromModel(take_stuff_id=worldmapc_xena_leather_jacket.id)
        )
        assert (
            kernel.stuff_lib.get_stuff_doc(worldmapc_xena_leather_jacket.id).carried_by_id
            == arthur.id
        )

    @pytest.mark.parametrize("modifier", [_apply_low_lp, _apply_shares])
    def test_unit__list_take_wood__ok(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood: None,
        take_from_character_action: TakeFromCharacterAction,
        modifier: ModifierType,
    ) -> None:
        kernel = worldmapc_kernel
        xena = modifier(self, kernel, worldmapc_xena_model, worldmapc_arthur_model)
        arthur = worldmapc_arthur_model

        description = take_from_character_action.perform(arthur, xena, TakeFromModel(take_resource_id="WOOD"))
        assert description.items[0].is_form
        assert description.items[0].items[0].name == "take_resource_quantity"
        assert description.items[0].form_action == (
            "/character/arthur/with-character-action/TAKE_FROM_CHARACTER/xena/TAKE_FROM_CHARACTER"
            "?take_resource_id=WOOD"
        )

        take_from_character_action.perform(
            arthur, xena, TakeFromModel(take_resource_id="WOOD", take_resource_quantity="0.1")
        )
        assert kernel.resource_lib.have_resource(
            character_id=arthur.id, resource_id="WOOD", quantity=0.1
        )
        assert kernel.resource_lib.have_resource(
            character_id=xena.id, resource_id="WOOD", quantity=0.1
        )

        take_from_character_action.perform(
            arthur, xena, TakeFromModel(take_resource_id="WOOD", take_resource_quantity="0.1")
        )
        assert kernel.resource_lib.have_resource(
            character_id=arthur.id, resource_id="WOOD", quantity=0.2
        )
        assert not kernel.resource_lib.have_resource(character_id=xena.id, resource_id="WOOD")

    @pytest.mark.parametrize("modifier", [_apply_low_lp, _apply_shares])
    def test_unit__list_take_wood__err__require_more(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood: None,
        take_from_character_action: TakeFromCharacterAction,
        modifier: ModifierType,
    ) -> None:
        kernel = worldmapc_kernel
        xena = modifier(self, kernel, worldmapc_xena_model, worldmapc_arthur_model)
        arthur = worldmapc_arthur_model

        with pytest.raises(WrongInputError):
            take_from_character_action.check_request_is_possible(
                arthur,
                xena,
                TakeFromModel(
                    take_resource_id="WOOD", take_resource_quantity="0.21"  # 0.2 in fixtures
                ),
            )

    @pytest.mark.parametrize("modifier", [_apply_low_lp, _apply_shares])
    def test_unit__list_take_shield__err__require_more(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_xena_wood_shield: StuffModel,
        take_from_character_action: TakeFromCharacterAction,
        modifier: ModifierType,
    ) -> None:
        kernel = worldmapc_kernel
        xena = modifier(self, kernel, worldmapc_xena_model, worldmapc_arthur_model)
        arthur = worldmapc_arthur_model

        with pytest.raises(WrongInputError):
            take_from_character_action.check_request_is_possible(
                arthur,
                xena,
                TakeFromModel(take_stuff_id=worldmapc_xena_wood_shield.id, take_stuff_quantity=2),
            )

    @pytest.mark.parametrize("modifier", [_apply_low_lp, _apply_shares])
    def test_unit__list_take_shield__err__dont_have(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        take_from_character_action: TakeFromCharacterAction,
        modifier: ModifierType,
    ) -> None:
        kernel = worldmapc_kernel
        xena = modifier(self, kernel, worldmapc_xena_model, worldmapc_arthur_model)
        arthur = worldmapc_arthur_model

        with pytest.raises(WrongInputError):
            take_from_character_action.check_request_is_possible(
                arthur, xena, TakeFromModel(take_stuff_id=42, take_stuff_quantity=1)
            )

    def test_take_more_than_ground_is_working(
        self,
        take_resource_action: TakeResourceAction,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        kernel.resource_lib.add_resource_to(
            resource_id="WOOD",
            ground=True,
            quantity=1.0,
            world_row_i=xena.world_row_i,
            world_col_i=xena.world_col_i,
            zone_row_i=xena.zone_row_i,
            zone_col_i=xena.zone_col_i,
        )

        # When
        take_resource_action.perform(
            character=xena,
            resource_id="WOOD",
            input_=TakeResourceModel(
                quantity="1.1"
            )
        )

        # Then
        assert kernel.resource_lib.get_one_carried_by(
            character_id=xena.id,
            resource_id="WOOD",
        ).quantity == 1.0
