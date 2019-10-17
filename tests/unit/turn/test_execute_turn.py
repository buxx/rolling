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
    worldmapc_kernel: Kernel,
    worldmapc_with_zones_server_character_lib: CharacterLib,
    worldmapc_with_zones_stuff_lib: StuffLib,
) -> TurnLib:
    return TurnLib(
        worldmapc_kernel,
        character_lib=worldmapc_with_zones_server_character_lib,
        stuff_lib=worldmapc_with_zones_stuff_lib,
        logger=logging.getLogger("tests"),
    )


class TestExecuteTurn:
    def test_alive_since_evolution(
        self,
        worldmapc_kernel: Kernel,
        turn_lib: TurnLib,
        xena: CharacterDocument,
        arthur: CharacterDocument,
    ) -> None:
        session = worldmapc_kernel.server_db_session
        session.refresh(xena)
        session.refresh(arthur)

        assert 0 == xena.alive_since
        assert 0 == arthur.alive_since

        turn_lib.execute_turn()

        session.refresh(xena)
        session.refresh(arthur)

        assert 1 == xena.alive_since
        assert 1 == arthur.alive_since
