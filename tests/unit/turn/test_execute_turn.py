# coding: utf-8
import logging

import pytest

from rolling.kernel import Kernel
from rolling.server.document.character import CharacterDocument
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.turn import TurnLib


@pytest.fixture
def turn_lib(worldmapc_with_zones_kernel: Kernel, worldmapc_with_zones_server_character_lib: CharacterLib) -> TurnLib:
    return TurnLib(worldmapc_with_zones_kernel, character_lib=worldmapc_with_zones_server_character_lib, logger=logging.getLogger('tests'))


@pytest.fixture
def xena(worldmapc_with_zones_kernel: Kernel) -> CharacterDocument:
    xena = CharacterDocument(
        id="xena",
        name="xena",
    )

    session = worldmapc_with_zones_kernel.server_db_session
    session.add(xena)
    session.commit()

    return xena


@pytest.fixture
def arthur(worldmapc_with_zones_kernel: Kernel) -> CharacterDocument:
    arthur = CharacterDocument(
        id="arthur",
        name="arthur",
    )

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
