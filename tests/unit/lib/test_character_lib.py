# coding: utf-8
import pytest
from rolling.availability import Availability

from rolling.kernel import Kernel
from rolling.model.ability import AbilityDescription
from rolling.model.character import CharacterModel
from rolling.model.measure import Unit
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

    worldmapc_kernel.character_lib.ensure_skills_for_character(arthur.id)
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
        jose_ = worldmapc_kernel.character_lib.get(jose.id)
        inventory = character_lib.get_inventory(jose_)
        assert 0 == inventory.clutter
        assert 0 == inventory.weight
        assert not inventory.stuff

        empty_plastic_bottle.carried_by_id = jose.id
        worldmapc_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose_)
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
        jose_ = worldmapc_kernel.character_lib.get(jose.id)
        inventory = character_lib.get_inventory(jose_)
        assert 0 == inventory.clutter
        assert 0 == inventory.weight
        assert not inventory.stuff

        half_filled_plastic_bottle.carried_by_id = jose.id
        worldmapc_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose_)
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
        jose_ = worldmapc_kernel.character_lib.get(jose.id)
        inventory = character_lib.get_inventory(jose_)
        assert 0 == inventory.clutter
        assert 0 == inventory.weight
        assert not inventory.stuff

        half_filled_plastic_bottle.carried_by_id = jose.id
        empty_plastic_bottle.carried_by_id = jose.id
        worldmapc_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose_)
        assert 2.0 == inventory.clutter
        assert 0.50 == inventory.weight
        assert inventory.stuff
        assert 2 == len(inventory.stuff)
        assert "Plastic bottle" == inventory.stuff[0].name
        assert "Plastic bottle" == inventory.stuff[1].name

    def test_have_abilities(
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
        abilities_availability = Availability.new(kernel, xena).abilities()
        abilities = abilities_availability.abilities
        origins = abilities_availability.origins

        # Then
        assert abilities
        assert len(abilities) == 3
        assert "BLACKSMITH" in [a.id for a in abilities]
        assert "HUNT_SMALL_GAME" in [a.id for a in abilities]
        assert "FIGHT" in [a.id for a in abilities]
