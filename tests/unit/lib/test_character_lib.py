# coding: utf-8
import pytest

from rolling.kernel import Kernel
from rolling.model.ability import HaveAbility
from rolling.model.character import CharacterModel
from rolling.model.measure import Unit
from rolling.model.meta import FromType
from rolling.model.meta import RiskType
from rolling.server.document.character import CharacterDocument
from rolling.server.document.stuff import StuffDocument
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from tests.fixtures import create_stuff


@pytest.fixture
def character_lib(
    worldmapc_kernel: Kernel,
    worldmapc_with_zones_server_character_lib: CharacterLib,
    worldmapc_with_zones_stuff_lib: StuffLib,
) -> CharacterLib:
    return CharacterLib(worldmapc_kernel, stuff_lib=worldmapc_with_zones_stuff_lib)


@pytest.fixture
def jose(
    worldmapc_kernel: Kernel, default_character_competences: dict
) -> CharacterDocument:
    arthur = CharacterDocument(id="jose", name="jose", **default_character_competences)

    session = worldmapc_kernel.server_db_session
    session.add(arthur)
    session.commit()

    return arthur


@pytest.fixture
def empty_plastic_bottle(
    worldmapc_kernel: Kernel, default_character_competences: dict
) -> StuffDocument:
    stuff = StuffDocument(
        stuff_id="PLASTIC_BOTTLE_1L",
        filled_value=0.0,
        filled_unity=Unit.LITTER.value,
        weight=0.0,
        clutter=1.0,
    )

    session = worldmapc_kernel.server_db_session
    session.add(stuff)
    session.commit()

    return stuff


@pytest.fixture
def half_filled_plastic_bottle(
    worldmapc_kernel: Kernel, default_character_competences: dict
) -> StuffDocument:
    stuff = StuffDocument(
        stuff_id="PLASTIC_BOTTLE_1L",
        filled_value=50.0,
        filled_unity=Unit.LITTER.value,
        weight=0.50,
        clutter=1.0,
    )

    session = worldmapc_kernel.server_db_session
    session.add(stuff)
    session.commit()

    return stuff


class TestCharacterLib:
    def test_inventory_one_light_item(
        self,
        worldmapc_kernel: Kernel,
        jose: CharacterDocument,
        empty_plastic_bottle: StuffDocument,
        character_lib: CharacterLib,
    ) -> None:
        inventory = character_lib.get_inventory(jose.id)
        assert 0 == inventory.clutter
        assert 0 == inventory.weight
        assert not inventory.stuff

        empty_plastic_bottle.carried_by_id = jose.id
        worldmapc_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose.id)
        assert 1.0 == inventory.clutter
        assert 0 == inventory.weight
        assert inventory.stuff
        assert 1 == len(inventory.stuff)
        assert "Plastic bottle" == inventory.stuff[0].name

    def test_inventory_one_weight_item(
        self,
        worldmapc_kernel: Kernel,
        jose: CharacterDocument,
        half_filled_plastic_bottle: StuffDocument,
        character_lib: CharacterLib,
    ) -> None:
        inventory = character_lib.get_inventory(jose.id)
        assert 0 == inventory.clutter
        assert 0 == inventory.weight
        assert not inventory.stuff

        half_filled_plastic_bottle.carried_by_id = jose.id
        worldmapc_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose.id)
        assert 1.0 == inventory.clutter
        assert 0.50 == inventory.weight
        assert inventory.stuff
        assert 1 == len(inventory.stuff)
        assert "Plastic bottle" == inventory.stuff[0].name

    def test_inventory_one_two_items(
        self,
        worldmapc_kernel: Kernel,
        jose: CharacterDocument,
        empty_plastic_bottle: StuffDocument,
        half_filled_plastic_bottle: StuffDocument,
        character_lib: CharacterLib,
    ) -> None:
        inventory = character_lib.get_inventory(jose.id)
        assert 0 == inventory.clutter
        assert 0 == inventory.weight
        assert not inventory.stuff

        half_filled_plastic_bottle.carried_by_id = jose.id
        empty_plastic_bottle.carried_by_id = jose.id
        worldmapc_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose.id)
        assert 2.0 == inventory.clutter
        assert 0.50 == inventory.weight
        assert inventory.stuff
        assert 2 == len(inventory.stuff)
        assert "Plastic bottle" == inventory.stuff[0].name
        assert "Plastic bottle" == inventory.stuff[1].name

    def test_have_from_of_abilities__around_ground_stuffs(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        # Given
        create_stuff(
            kernel=kernel,
            stuff_id="STONE_HAXE",
            world_row_i=xena.world_row_i,
            world_col_i=xena.world_col_i,
            zone_row_i=xena.zone_row_i,
            zone_col_i=xena.zone_col_i,
        )

        # When
        have_abilities = kernel.character_lib.have_from_of_abilities(
            character=xena,
            abilities=[
                kernel.game.config.abilities["BLACKSMITH"],
                kernel.game.config.abilities["HUNT_SMALL_GAME"],
            ],
        )

        # Then
        assert have_abilities
        assert len(have_abilities) == 2
        assert have_abilities == [
            HaveAbility(
                ability_id="BLACKSMITH", from_=FromType.HIMSELF, risk=RiskType.NONE
            ),
            HaveAbility(
                ability_id="HUNT_SMALL_GAME", from_=FromType.STUFF, risk=RiskType.NONE
            ),
        ]
