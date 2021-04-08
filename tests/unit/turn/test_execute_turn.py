# coding: utf-8
from aiohttp.test_utils import TestClient
import logging
import pytest
import serpyco
import unittest
import unittest.mock

from rolling.exception import NoCarriedResource
from rolling.kernel import Kernel
from rolling.model.measure import Unit
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityJoinType
from rolling.server.document.build import BuildDocument
from rolling.server.document.character import CharacterDocument
from rolling.server.document.stuff import StuffDocument
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


@pytest.fixture
def build_a_on(worldmapc_kernel: Kernel) -> BuildDocument:
    build_doc = BuildDocument(
        world_row_i=1,
        world_col_i=1,
        zone_row_i=1,
        zone_col_i=1,
        build_id="TEST_BUILD_3",
        under_construction=False,
        is_on=True,
    )
    worldmapc_kernel.server_db_session.add(build_doc)
    worldmapc_kernel.server_db_session.commit()
    return build_doc


@pytest.fixture
def build_a_off(worldmapc_kernel: Kernel) -> BuildDocument:
    build_doc = BuildDocument(
        world_row_i=1,
        world_col_i=1,
        zone_row_i=1,
        zone_col_i=1,
        build_id="TEST_BUILD_3",
        under_construction=False,
        is_on=False,
    )
    worldmapc_kernel.server_db_session.add(build_doc)
    worldmapc_kernel.server_db_session.commit()
    return build_doc


@pytest.mark.usefixtures("initial_universe_state")
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
        resp = await web.post(f"/affinity/{xena.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"1 prêt(s)" in descr.items[1].text

    # FIXME BS NOW: ajouter test eau zone
    # This test depend on game1 config !
    @pytest.mark.parametrize(
        "before_lp,"
        "before_thirst,"
        "before_bottle_filled,"
        "after_lp,"
        "after_thirst,"
        "after_bottle_filled",
        [
            (1.0, 0.0, 1.0, 1.05, 2.0, 1.0),
            (1.0, 20.0, 1.0, 1.05, 20.0, 0.96),
            (1.0, 90.0, 1.0, 1.05, 42.0, 0.0),
            (1.0, 100.0, 0.04, 1.05, 50.0, 0.0),
            (1.0, 100.0, 0.0, 0.8, 100.0, 0.0),
        ],
    )
    def test_drink__ok__drink_one_bottle(
        self,
        worldmapc_kernel: Kernel,
        turn_lib: TurnLib,
        xena: CharacterDocument,
        before_lp: float,
        before_thirst: float,
        before_bottle_filled: float,
        after_lp: float,
        after_thirst: float,
        after_bottle_filled: float,
    ) -> None:
        # With
        kernel = worldmapc_kernel
        if before_bottle_filled:
            stuff_doc = StuffDocument(
                stuff_id="PLASTIC_BOTTLE_1L",
                filled_value=1.0,
                filled_capacity=1.0,
                filled_unity=Unit.LITTER.value,
                filled_with_resource="FRESH_WATER",
                weight=2000.0,
                clutter=0.5,
                carried_by_id=xena.id,
            )
            kernel.server_db_session.add(stuff_doc)
            kernel.server_db_session.commit()
        xena.thirst = before_thirst
        xena.life_points = before_lp
        kernel.server_db_session.add(xena)
        kernel.server_db_session.commit()

        # When
        turn_lib.execute_turn()

        # Then
        xena = kernel.character_lib.get_document(xena.id)
        assert float(xena.life_points) == after_lp
        assert float(xena.thirst) == after_thirst
        if after_bottle_filled == 0.0:
            pass
        else:
            stuff_doc = kernel.stuff_lib.get_stuff_doc(stuff_doc.id)
            assert float(stuff_doc.filled_value) == after_bottle_filled

    def test_drink__ok__drink_two_bottle(
        self, worldmapc_kernel: Kernel, turn_lib: TurnLib, xena: CharacterDocument
    ) -> None:
        # With
        kernel = worldmapc_kernel
        stuff_doc = StuffDocument(
            stuff_id="PLASTIC_BOTTLE_1L",
            filled_value=1.0,
            filled_capacity=1.0,
            filled_unity=Unit.LITTER.value,
            filled_with_resource="FRESH_WATER",
            weight=2000.0,
            clutter=0.5,
            carried_by_id=xena.id,
        )
        kernel.server_db_session.add(stuff_doc)
        stuff_doc2 = StuffDocument(
            stuff_id="PLASTIC_BOTTLE_1L",
            filled_value=0.5,
            filled_capacity=1.0,
            filled_unity=Unit.LITTER.value,
            filled_with_resource="FRESH_WATER",
            weight=1500.0,
            clutter=0.5,
            carried_by_id=xena.id,
        )
        kernel.server_db_session.add(stuff_doc2)
        kernel.server_db_session.commit()
        xena.thirst = 100.0
        xena.life_points = 1.0
        kernel.server_db_session.add(xena)
        kernel.server_db_session.commit()

        # When
        turn_lib.execute_turn()

        # Then
        xena = kernel.character_lib.get_document(xena.id)
        assert float(xena.life_points) == 1.05
        assert float(xena.thirst) == 25.0
        stuff_doc = kernel.stuff_lib.get_stuff_doc(stuff_doc.id)
        assert stuff_doc.filled_value is None
        stuff_doc2 = kernel.stuff_lib.get_stuff_doc(stuff_doc2.id)
        assert stuff_doc2.filled_value is None

    def test_drink__ok__drink_in_zone(
        self, worldmapc_kernel: Kernel, turn_lib: TurnLib, xena: CharacterDocument
    ) -> None:
        # With
        kernel = worldmapc_kernel
        xena.thirst = 100.0
        xena.life_points = 1.0
        kernel.server_db_session.add(xena)
        kernel.server_db_session.commit()

        # When
        with unittest.mock.patch("rolling.util.is_there_resource_id_in_zone", retur_value=True):
            a = 1
            turn_lib.execute_turn()

        # Then
        xena = kernel.character_lib.get_document(xena.id)
        assert float(xena.life_points) == 1.05
        assert float(xena.thirst) == 20.0

    # This test depend on game1 config !
    @pytest.mark.parametrize(
        "before_lp,"
        "before_hunger,"
        "before_vegetal_food_quantity,"
        "after_lp,"
        "after_hunger,"
        "after_vegetal_food_quantity",
        [
            (1.0, 0.0, 1.0, 1.05, 1.0, 1.0),
            (1.0, 20.0, 1.0, 1.05, 20.0, 0.96),
            (1.0, 90.0, 1.0, 1.05, 66.0, 0.0),
            (1.0, 100.0, 0.04, 1.0, 99.0, 0.0),
            (1.0, 100.0, 0.0, 0.9, 100.0, 0.0),
        ],
    )
    def test_eat__ok__eat_one_resource(
        self,
        worldmapc_kernel: Kernel,
        turn_lib: TurnLib,
        xena: CharacterDocument,
        before_lp: float,
        before_hunger: float,
        before_vegetal_food_quantity: float,
        after_lp: float,
        after_hunger: float,
        after_vegetal_food_quantity: float,
    ) -> None:
        # With
        kernel = worldmapc_kernel
        if before_vegetal_food_quantity:
            kernel.resource_lib.add_resource_to(
                character_id=xena.id,
                resource_id="VEGETAL_FOOD_FRESH",
                quantity=before_vegetal_food_quantity,
            )
        xena.hunger = before_hunger
        xena.life_points = before_lp
        kernel.server_db_session.add(xena)
        kernel.server_db_session.commit()

        # When
        turn_lib.execute_turn()

        # Then
        xena = kernel.character_lib.get_document(xena.id)
        assert float(xena.life_points) == after_lp
        assert xena.hunger == after_hunger
        if after_vegetal_food_quantity == 0.0:
            with pytest.raises(NoCarriedResource):
                kernel.resource_lib.get_one_carried_by(xena.id, resource_id="VEGETAL_FOOD_FRESH")
        else:
            resource = kernel.resource_lib.get_one_carried_by(
                xena.id, resource_id="VEGETAL_FOOD_FRESH"
            )
            assert resource.quantity == after_vegetal_food_quantity

    def test_eat__ok__eat_two_resource(
        self, worldmapc_kernel: Kernel, turn_lib: TurnLib, xena: CharacterDocument
    ) -> None:
        # With
        kernel = worldmapc_kernel
        kernel.resource_lib.add_resource_to(
            character_id=xena.id, resource_id="VEGETAL_FOOD_FRESH", quantity=1.01
        )
        kernel.resource_lib.add_resource_to(
            character_id=xena.id, resource_id="VEGETAL_FOOD_FRESH2", quantity=100.0
        )
        xena.hunger = 100.0
        xena.life_points = 1.0
        kernel.server_db_session.add(xena)
        kernel.server_db_session.commit()

        # When
        turn_lib.execute_turn()

        # Then
        xena = kernel.character_lib.get_document(xena.id)
        assert float(xena.life_points) == 1.05
        assert xena.hunger == 19.75
        with pytest.raises(NoCarriedResource):
            kernel.resource_lib.get_one_carried_by(xena.id, resource_id="VEGETAL_FOOD_FRESH")
        r = kernel.resource_lib.get_one_carried_by(xena.id, resource_id="VEGETAL_FOOD_FRESH2")
        assert r.quantity == 97.8

    def test_eat__ko__eat_resource_but_not_enough(
        self, worldmapc_kernel: Kernel, turn_lib: TurnLib, xena: CharacterDocument
    ) -> None:
        kernel = worldmapc_kernel

        kernel.resource_lib.add_resource_to(
            character_id=xena.id, resource_id="VEGETAL_FOOD_FRESH", quantity=0.5  # not enough
        )
        with unittest.mock.patch(
            "rolling.server.effect.EffectManager.enable_effect"
        ) as fake_enable_effect:
            turn_lib.execute_turn()

        assert kernel.resource_lib.have_resource(
            character_id=xena.id, resource_id="VEGETAL_FOOD_FRESH", quantity=0.46
        )
        assert not fake_enable_effect.called

    def test_turn_build_consume_to_keep_on(
        self, worldmapc_kernel: Kernel, turn_lib: TurnLib, build_a_on: BuildDocument
    ) -> None:
        # Given
        worldmapc_kernel.resource_lib.add_resource_to(
            resource_id="BRANCHES", quantity=10.0, build_id=build_a_on.id
        )
        resources_on_build = worldmapc_kernel.resource_lib.get_stored_in_build(
            build_id=build_a_on.id
        )
        assert resources_on_build
        assert len(resources_on_build) == 1
        assert resources_on_build[0].id == "BRANCHES"
        assert resources_on_build[0].quantity == 10.0
        assert build_a_on.is_on is True

        # When
        turn_lib.execute_turn()

        # Then
        build_a_on = worldmapc_kernel.build_lib.get_build_doc(build_a_on.id)
        resources_on_build = worldmapc_kernel.resource_lib.get_stored_in_build(
            build_id=build_a_on.id
        )
        assert resources_on_build
        assert len(resources_on_build) == 1
        assert resources_on_build[0].id == "BRANCHES"
        assert resources_on_build[0].quantity == 9.99
        assert build_a_on.is_on is True

    def test_turn_build_consume_but_keep_off_because_not_enough(
        self, worldmapc_kernel: Kernel, turn_lib: TurnLib, build_a_on: BuildDocument
    ):
        # Given
        worldmapc_kernel.resource_lib.add_resource_to(
            resource_id="BRANCHES", quantity=0.001, build_id=build_a_on.id  # not enough
        )
        resources_on_build = worldmapc_kernel.resource_lib.get_stored_in_build(
            build_id=build_a_on.id
        )
        assert resources_on_build
        assert len(resources_on_build) == 1
        assert resources_on_build[0].id == "BRANCHES"
        assert resources_on_build[0].quantity == 0.001
        assert build_a_on.is_on is True

        # When
        turn_lib.execute_turn()

        # Then
        build_a_on = worldmapc_kernel.build_lib.get_build_doc(build_a_on.id)
        resources_on_build = worldmapc_kernel.resource_lib.get_stored_in_build(
            build_id=build_a_on.id
        )
        assert resources_on_build
        assert len(resources_on_build) == 1
        assert resources_on_build[0].id == "BRANCHES"
        assert resources_on_build[0].quantity == 0.001
        assert build_a_on.is_on is False

    def test_turn_build_not_consume_because_off(
        self, worldmapc_kernel: Kernel, turn_lib: TurnLib, build_a_off: BuildDocument
    ):
        # Given
        assert not worldmapc_kernel.resource_lib.get_stored_in_build(build_id=build_a_off.id)

        # When
        turn_lib.execute_turn()

        # Then
        assert build_a_off.is_on is False
