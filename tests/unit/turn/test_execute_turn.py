# coding: utf-8
import logging

from aiohttp.test_utils import TestClient
import pytest
import serpyco

from rolling.kernel import Kernel
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityJoinType
from rolling.server.document.character import CharacterDocument
from rolling.server.document.universe import UniverseStateDocument
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
    @pytest.mark.usefixtures("initial_universe_state")
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

    @pytest.mark.usefixtures("initial_universe_state")
    async def test_unit__character_die__ok__affinity_relations_discard(
        self,
        worldmapc_kernel: Kernel,
        turn_lib: TurnLib,
        xena: CharacterDocument,
        arthur: CharacterDocument,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
    ) -> None:
        session = worldmapc_kernel.server_db_session
        session.refresh(xena)
        session.refresh(arthur)
        web = worldmapc_web_app
        kernel = worldmapc_kernel

        # fixtures
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        affinity: AffinityDocument = kernel.server_db_session.query(AffinityDocument).one()
        affinity.join_type = AffinityJoinType.ACCEPT_ALL.value
        kernel.server_db_session.add(affinity)
        kernel.server_db_session.commit()
        resp = await web.post(
            f"/affinity/{arthur.id}/edit-relation/{affinity.id}?request=1&fighter=1"
        )
        assert 200 == resp.status

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "2 membre(s)" in descr.items[1].text
        assert f"2 prêt(s)" in descr.items[1].text

        # make turn kill arthur
        arthur_doc = kernel.character_lib.get_document(arthur.id)
        arthur_doc.life_points = 0
        kernel.server_db_session.add(arthur_doc)
        kernel.server_db_session.commit()
        turn_lib.execute_turn()

        arthur_doc = kernel.character_lib.get_document(arthur.id, dead=True)
        assert not arthur_doc.alive

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"1 prêt(s)" in descr.items[1].text

    @pytest.mark.usefixtures("initial_universe_state")
    @pytest.mark.parametrize(
        "feel_thirsty,feel_hungry,before_lp,after_lp",
        [(False, False, 1.0, 2.0), (True, False, 1.0, 1.0), (False, True, 1.0, 1.0)],
    )
    def test_lp_up__ok__natural_needs(
        self,
        worldmapc_kernel: Kernel,
        turn_lib: TurnLib,
        xena: CharacterDocument,
        feel_thirsty: bool,
        feel_hungry: bool,
        before_lp: float,
        after_lp: float,
    ) -> None:
        kernel = worldmapc_kernel

        xena.life_points = before_lp
        xena.feel_thirsty = feel_thirsty
        xena.feel_hungry = feel_hungry
        kernel.character_lib.update(xena)

        turn_lib.execute_turn()

        xena = kernel.character_lib.get_document(xena.id)
        assert xena.life_points == after_lp
