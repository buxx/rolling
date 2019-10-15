# coding: utf-8
import logging

import pytest

from rolling.kernel import Kernel
from rolling.server.document.character import CharacterDocument
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.server.lib.turn import TurnLib


@pytest.fixture
def turn_lib(
    worldmapc_with_zones_kernel: Kernel,
    worldmapc_with_zones_server_character_lib: CharacterLib,
    worldmapc_with_zones_stuff_lib: StuffLib,
) -> TurnLib:
    return TurnLib(
        worldmapc_with_zones_kernel,
        character_lib=worldmapc_with_zones_server_character_lib,
        stuff_lib=worldmapc_with_zones_stuff_lib,
        logger=logging.getLogger("tests"),
    )


@pytest.fixture
def xena(
    worldmapc_with_zones_kernel: Kernel, default_character_competences: dict
) -> CharacterDocument:
    xena = CharacterDocument(id="xena", name="xena", **default_character_competences)
    xena.world_row_i = 1
    xena.world_col_i = 1
    xena.zone_row_i = 10
    xena.zone_col_i = 10

    session = worldmapc_with_zones_kernel.server_db_session
    session.add(xena)
    session.commit()

    return xena


@pytest.fixture
def arthur(
    worldmapc_with_zones_kernel: Kernel, default_character_competences: dict
) -> CharacterDocument:
    arthur = CharacterDocument(id="arthur", name="arthur", **default_character_competences)
    arthur.world_row_i = 1
    arthur.world_col_i = 1
    arthur.zone_row_i = 10
    arthur.zone_col_i = 10

    session = worldmapc_with_zones_kernel.server_db_session
    session.add(arthur)
    session.commit()

    return arthur


class TestExecuteTurn:
    def test_alive_since_evolution(
        self,
        worldmapc_with_zones_kernel: Kernel,
        turn_lib: TurnLib,
        xena: CharacterDocument,
        arthur: CharacterDocument,
    ) -> None:
        session = worldmapc_with_zones_kernel.server_db_session
        session.refresh(xena)
        session.refresh(arthur)

        assert 0 == xena.alive_since
        assert 0 == arthur.alive_since

        turn_lib.execute_turn()

        session.refresh(xena)
        session.refresh(arthur)

        assert 1 == xena.alive_since
        assert 1 == arthur.alive_since
