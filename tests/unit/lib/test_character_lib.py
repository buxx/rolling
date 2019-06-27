# coding: utf-8
import pytest

from rolling.kernel import Kernel
from rolling.model.stuff import Unit
from rolling.server.document.character import CharacterDocument
from rolling.server.document.stuff import StuffDocument
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib


@pytest.fixture
def character_lib(
    worldmapc_with_zones_kernel: Kernel,
    worldmapc_with_zones_server_character_lib: CharacterLib,
    worldmapc_with_zones_stuff_lib: StuffLib,
) -> CharacterLib:
    return CharacterLib(
        worldmapc_with_zones_kernel,
        stuff_lib=worldmapc_with_zones_stuff_lib,
    )


@pytest.fixture
def jose(
    worldmapc_with_zones_kernel: Kernel, default_character_competences: dict
) -> CharacterDocument:
    arthur = CharacterDocument(
        id="jose", name="jose", **default_character_competences
    )

    session = worldmapc_with_zones_kernel.server_db_session
    session.add(arthur)
    session.commit()

    return arthur


@pytest.fixture
def empty_plastic_bottle(
    worldmapc_with_zones_kernel: Kernel, default_character_competences: dict
) -> StuffDocument:
    stuff = StuffDocument(
        stuff_id="PLASTIC_BOTTLE_1L",
        filled_at=0.0,
        filled_unity=Unit.LITTER.value,
        weight=0.0,
        clutter=1.0,
    )

    session = worldmapc_with_zones_kernel.server_db_session
    session.add(stuff)
    session.commit()

    return stuff


@pytest.fixture
def half_filled_plastic_bottle(
    worldmapc_with_zones_kernel: Kernel, default_character_competences: dict
) -> StuffDocument:
    stuff = StuffDocument(
        stuff_id="PLASTIC_BOTTLE_1L",
        filled_at=50.0,
        filled_unity=Unit.LITTER.value,
        weight=0.50,
        clutter=1.0,
    )

    session = worldmapc_with_zones_kernel.server_db_session
    session.add(stuff)
    session.commit()

    return stuff


class TestCharacterLib:
    def test_inventory_one_light_item(
        self,
        worldmapc_with_zones_kernel: Kernel,
        jose: CharacterDocument,
        empty_plastic_bottle: StuffDocument,
        character_lib: CharacterLib,
    ) -> None:
        inventory = character_lib.get_inventory(jose.id)
        assert 0 == inventory.clutter
        assert 0 == inventory.weight
        assert not inventory.stuff

        empty_plastic_bottle.carried_by_id = jose.id
        worldmapc_with_zones_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose.id)
        assert 1.0 == inventory.clutter
        assert 0 == inventory.weight
        assert inventory.stuff
        assert 1 == len(inventory.stuff)
        assert "Plastic bottle" == inventory.stuff[0].name

    def test_inventory_one_weight_item(
        self,
        worldmapc_with_zones_kernel: Kernel,
        jose: CharacterDocument,
        half_filled_plastic_bottle: StuffDocument,
        character_lib: CharacterLib,
    ) -> None:
        inventory = character_lib.get_inventory(jose.id)
        assert 0 == inventory.clutter
        assert 0 == inventory.weight
        assert not inventory.stuff

        half_filled_plastic_bottle.carried_by_id = jose.id
        worldmapc_with_zones_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose.id)
        assert 1.0 == inventory.clutter
        assert 0.50 == inventory.weight
        assert inventory.stuff
        assert 1 == len(inventory.stuff)
        assert "Plastic bottle" == inventory.stuff[0].name

    def test_inventory_one_two_items(
        self,
        worldmapc_with_zones_kernel: Kernel,
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
        worldmapc_with_zones_kernel.server_db_session.commit()

        inventory = character_lib.get_inventory(jose.id)
        assert 2.0 == inventory.clutter
        assert 0.50 == inventory.weight
        assert inventory.stuff
        assert 2 == len(inventory.stuff)
        assert "Plastic bottle" == inventory.stuff[0].name
        assert "Plastic bottle" == inventory.stuff[1].name
