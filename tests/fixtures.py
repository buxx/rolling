# coding: utf-8
import datetime
import os
import typing

from aiohttp import web
from aiohttp.test_utils import TestClient
from aiohttp.web_exceptions import HTTPNotFound
from hapic.ext.aiohttp.context import AiohttpContext
from hapic.processor.serpyco import SerpycoProcessor
import pytest
import serpyco

from guilang.description import Description
from rolling.gui.map.object import DisplayObjectManager
from rolling.gui.map.render import TileMapRenderEngine
from rolling.gui.map.render import WorldMapRenderEngine
from rolling.kernel import Kernel
from rolling.map.generator.filler.dummy import DummyTileMapFiller
from rolling.map.generator.generator import TileMapGenerator
from rolling.map.source import WorldMapSource
from rolling.map.source import ZoneMapSource
from rolling.map.type.zone import SeaWater
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
from rolling.server.application import get_application
from rolling.server.document.affinity import MEMBER_STATUS
from rolling.server.document.affinity import WARLORD_STATUS
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.character import CharacterDocument
from rolling.server.document.universe import UniverseStateDocument
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.server.lib.universe import UniverseLib
from rolling.server.run import ErrorBuilder


@pytest.fixture
def worldmapsourcea_txt() -> str:
    with open(os.path.join("tests", "src", "worldmapa.txt")) as f:
        return f.read()


@pytest.fixture
def tilemapsourcea_txt() -> str:
    with open(os.path.join("tests", "src", "tilemapa.txt")) as f:
        return f.read()


@pytest.fixture
def worldmapsourceb_txt() -> str:
    with open(os.path.join("tests", "src", "worldmapb.txt")) as f:
        return f.read()


@pytest.fixture
def worldmapsourceb2_txt() -> str:
    with open(os.path.join("tests", "src", "worldmapb2.txt")) as f:
        return f.read()


@pytest.fixture
def worldmapsourcec_txt() -> str:
    with open(os.path.join("tests", "src", "worldmapc.txt")) as f:
        return f.read()


@pytest.fixture
def worldmapa_kernel(worldmapsourcea_txt, loop) -> Kernel:
    return Kernel(worldmapsourcea_txt, loop=loop)


@pytest.fixture
def worldmapb_kernel(worldmapsourceb2_txt, loop) -> Kernel:
    return Kernel(worldmapsourceb2_txt, loop=loop)


@pytest.fixture
def worldmapb2_kernel(worldmapsourceb2_txt, loop) -> Kernel:
    return Kernel(worldmapsourceb2_txt, loop=loop)


@pytest.fixture
def worldmapc_kernel(worldmapsourcec_txt, tmp_path, loop) -> Kernel:
    server_db_path = tmp_path / "server.db"
    kernel = Kernel(
        worldmapsourcec_txt,
        tile_maps_folder="tests/src/worldmapc_zones",
        game_config_folder="tests/src/game1",
        server_db_path=server_db_path,
        loop=loop,
    )
    kernel.init_server_db_session()
    return kernel


@pytest.fixture
def worldmapc_with_zones_server_character_lib(worldmapc_kernel: Kernel) -> CharacterLib:
    return CharacterLib(worldmapc_kernel)


@pytest.fixture
def worldmapc_full_sea_tile_map_source(worldmapc_kernel: Kernel) -> ZoneMapSource:
    generator = TileMapGenerator(worldmapc_kernel, DummyTileMapFiller(SeaWater))
    return generator.generate(11)


@pytest.fixture
def display_object_manager__empty() -> DisplayObjectManager:
    return DisplayObjectManager([])


@pytest.fixture
def worldmapa_render_engine(
    worldmapsourcea_txt: str,
    display_object_manager__empty: DisplayObjectManager,
    worldmapa_kernel: Kernel,
) -> WorldMapRenderEngine:
    return WorldMapRenderEngine(
        world_map_source=WorldMapSource(kernel=worldmapa_kernel, raw_source=worldmapsourceb_txt),
        display_objects_manager=display_object_manager__empty,
    )


@pytest.fixture
def tilemapa_render_engine(
    tilemapsourcea_txt: str,
    display_object_manager__empty: DisplayObjectManager,
    worldmapb_kernel: Kernel,
) -> TileMapRenderEngine:
    return TileMapRenderEngine(
        world_map_source=ZoneMapSource(kernel=worldmapb_kernel, raw_source=tilemapsourcea_txt),
        display_objects_manager=display_object_manager__empty,
    )


@pytest.fixture
def worldmapb_render_engine(
    worldmapsourceb_txt: str,
    display_object_manager__empty: DisplayObjectManager,
    worldmapb_kernel: Kernel,
) -> WorldMapRenderEngine:
    return WorldMapRenderEngine(
        world_map_source=WorldMapSource(kernel=worldmapb_kernel, raw_source=worldmapsourceb_txt),
        display_objects_manager=display_object_manager__empty,
    )


@pytest.fixture
def worldmapb2_render_engine(
    worldmapsourceb2_txt: str,
    display_object_manager__empty: DisplayObjectManager,
    worldmapb2_kernel: Kernel,
) -> WorldMapRenderEngine:
    return WorldMapRenderEngine(
        world_map_source=WorldMapSource(kernel=worldmapb2_kernel, raw_source=worldmapsourceb2_txt),
        display_objects_manager=display_object_manager__empty,
    )


@pytest.fixture
def worldmapc_with_zones_stuff_lib(worldmapc_kernel: Kernel) -> StuffLib:
    return StuffLib(worldmapc_kernel)


_default_character_competences = {
    "background_story": "",
    "max_life_comp": 5.0,
    "life_points": 5.0,
    "hunting_and_collecting_comp": 2.0,
    "find_water_comp": 1.0,
    "action_points": 24.0,
    "attack_allowed_loss_rate": 30.0,
    "defend_allowed_loss_rate": 30.0,
}


@pytest.fixture
def default_character_competences() -> dict:
    return _default_character_competences


@pytest.fixture
def xena(worldmapc_kernel: Kernel, default_character_competences: dict) -> CharacterDocument:
    xena = CharacterDocument(id="xena", name="xena", **default_character_competences)
    xena.world_row_i = 1
    xena.world_col_i = 1
    xena.zone_row_i = 10
    xena.zone_col_i = 10

    session = worldmapc_kernel.server_db_session
    session.add(xena)
    session.commit()

    return xena


@pytest.fixture
def worldmapc_xena_model(xena: CharacterDocument, worldmapc_kernel: Kernel) -> CharacterModel:
    character_lib = CharacterLib(worldmapc_kernel)
    return character_lib.document_to_model(xena)


@pytest.fixture
def arthur(worldmapc_kernel: Kernel, default_character_competences: dict) -> CharacterDocument:
    arthur = CharacterDocument(id="arthur", name="arthur", **default_character_competences)
    arthur.world_row_i = 1
    arthur.world_col_i = 1
    arthur.zone_row_i = 10
    arthur.zone_col_i = 10

    session = worldmapc_kernel.server_db_session
    session.add(arthur)
    session.commit()

    return arthur


@pytest.fixture
def franck(worldmapc_kernel: Kernel, default_character_competences: dict) -> CharacterDocument:
    franck = CharacterDocument(id="franck", name="franck", **default_character_competences)
    franck.world_row_i = 1
    franck.world_col_i = 1
    franck.zone_row_i = 11
    franck.zone_col_i = 11

    session = worldmapc_kernel.server_db_session
    session.add(franck)
    session.commit()

    return franck


@pytest.fixture
def worldmapc_arthur_model(arthur: CharacterDocument, worldmapc_kernel: Kernel) -> CharacterModel:
    character_lib = CharacterLib(worldmapc_kernel)
    return character_lib.document_to_model(arthur)


@pytest.fixture
def worldmapc_franck_model(franck: CharacterDocument, worldmapc_kernel: Kernel) -> CharacterModel:
    character_lib = CharacterLib(worldmapc_kernel)
    return character_lib.document_to_model(franck)


@pytest.fixture
def universe_lib(worldmapc_kernel: Kernel) -> UniverseLib:
    return UniverseLib(worldmapc_kernel)


@pytest.fixture
def initial_universe_state(
    worldmapc_kernel: Kernel, universe_lib: UniverseLib
) -> UniverseStateDocument:
    doc = UniverseStateDocument(turn=1, turned_at=datetime.datetime.utcnow())
    worldmapc_kernel.server_db_session.add(doc)
    return doc


@pytest.fixture
def worldmapc_web_app(worldmapc_kernel: Kernel, loop, aiohttp_client) -> TestClient:
    app = get_application(worldmapc_kernel)
    context = AiohttpContext(app, debug=True, default_error_builder=ErrorBuilder())
    context.handle_exception(HTTPNotFound, http_code=404)
    context.handle_exception(Exception, http_code=500)
    hapic.reset_context()
    hapic.set_processor_class(SerpycoProcessor)
    hapic.set_context(context)
    return loop.run_until_complete(aiohttp_client(app))


description_serializer = serpyco.Serializer(Description)


@pytest.fixture(scope="session")
def descr_serializer() -> serpyco.Serializer:
    return description_serializer


@pytest.fixture
def france_affinity(worldmapc_kernel: Kernel) -> AffinityDocument:
    doc = AffinityDocument(name="France")
    worldmapc_kernel.server_db_session.add(doc)
    worldmapc_kernel.server_db_session.commit()
    return doc


@pytest.fixture
def england_affinity(worldmapc_kernel: Kernel) -> AffinityDocument:
    doc = AffinityDocument(name="England")
    worldmapc_kernel.server_db_session.add(doc)
    worldmapc_kernel.server_db_session.commit()
    return doc


@pytest.fixture
def burgundian_affinity(worldmapc_kernel: Kernel) -> AffinityDocument:
    doc = AffinityDocument(name="Burgundian")
    worldmapc_kernel.server_db_session.add(doc)
    worldmapc_kernel.server_db_session.commit()
    return doc


def _create_soldiers(
    kernel: Kernel, affinity: AffinityDocument, count: int, warlord: bool = False
) -> typing.List[CharacterModel]:
    models = []
    name = "soldier" if not warlord else "warlord"
    for i in range(count):
        doc = CharacterDocument(
            id=f"{affinity.name.lower()}_{name}{i}",
            name=f"{affinity.name}{name.capitalize()}{i}",
            **_default_character_competences,
        )
        doc.world_row_i = 1
        doc.world_col_i = 1
        doc.zone_row_i = 10
        doc.zone_col_i = 10

        kernel.server_db_session.add(doc)
        kernel.server_db_session.commit()
        kernel.server_db_session.add(
            AffinityRelationDocument(
                affinity_id=affinity.id,
                character_id=doc.id,
                accepted=True,
                fighter=True,
                status_id=MEMBER_STATUS[0] if not warlord else WARLORD_STATUS[0],
            )
        )
        models.append(kernel.character_lib.document_to_model(doc))

    kernel.server_db_session.commit()
    return models


@pytest.fixture
def france_fighters(
    worldmapc_kernel: Kernel, france_affinity: AffinityDocument
) -> typing.List[CharacterModel]:
    return _create_soldiers(worldmapc_kernel, france_affinity, 5)


@pytest.fixture
def england_fighters(
    worldmapc_kernel: Kernel, england_affinity: AffinityDocument
) -> typing.List[CharacterModel]:
    return _create_soldiers(worldmapc_kernel, england_affinity, 5)


@pytest.fixture
def burgundian_fighters(
    worldmapc_kernel: Kernel, burgundian_affinity: AffinityDocument
) -> typing.List[CharacterModel]:
    return _create_soldiers(worldmapc_kernel, burgundian_affinity, 5)


@pytest.fixture
def france_warlord(worldmapc_kernel: Kernel, france_affinity: AffinityDocument) -> CharacterModel:
    return _create_soldiers(worldmapc_kernel, france_affinity, 1, warlord=True)[0]


@pytest.fixture
def england_warlord(worldmapc_kernel: Kernel, england_affinity: AffinityDocument) -> CharacterModel:
    return _create_soldiers(worldmapc_kernel, england_affinity, 1, warlord=True)[0]


@pytest.fixture
def burgundian_warlord(
    worldmapc_kernel: Kernel, burgundian_affinity: AffinityDocument
) -> CharacterModel:
    return _create_soldiers(worldmapc_kernel, burgundian_affinity, 1, warlord=True)[0]


def _create_stuff(kernel: Kernel, stuff_id: str) -> StuffModel:
    haxe_properties = kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
    haxe_doc = kernel.stuff_lib.create_document_from_stuff_properties(
        haxe_properties, world_row_i=0, world_col_i=0, zone_row_i=0, zone_col_i=0
    )
    kernel.stuff_lib.add_stuff(haxe_doc)
    return kernel.stuff_lib.get_stuff(haxe_doc.id)


@pytest.fixture
def worldmapc_xena_haxe(
    worldmapc_xena_model: CharacterModel, worldmapc_kernel: Kernel
) -> StuffModel:
    xena = worldmapc_xena_model
    kernel = worldmapc_kernel

    haxe = _create_stuff(kernel, "STONE_HAXE")
    kernel.stuff_lib.set_carried_by(haxe.id, xena.id)
    return haxe


@pytest.fixture
def worldmapc_xena_leather_jacket(
    worldmapc_xena_model: CharacterModel, worldmapc_kernel: Kernel
) -> StuffModel:
    xena = worldmapc_xena_model
    kernel = worldmapc_kernel

    haxe = _create_stuff(kernel, "LEATHER_JACKET")
    kernel.stuff_lib.set_carried_by(haxe.id, xena.id)
    return haxe


@pytest.fixture
def worldmapc_xena_wood_shield(
    worldmapc_xena_model: CharacterModel, worldmapc_kernel: Kernel
) -> StuffModel:
    xena = worldmapc_xena_model
    kernel = worldmapc_kernel

    shield = _create_stuff(kernel, "WOOD_SHIELD")
    kernel.stuff_lib.set_carried_by(shield.id, xena.id)
    return shield


@pytest.fixture
def worldmapc_xena_haxe_weapon(
    worldmapc_xena_model: CharacterModel, worldmapc_kernel: Kernel, worldmapc_xena_haxe: StuffModel
) -> StuffModel:
    xena = worldmapc_xena_model
    kernel = worldmapc_kernel
    haxe = worldmapc_xena_haxe

    kernel.stuff_lib.set_as_used_as_weapon(xena.id, haxe.id)
    return haxe


@pytest.fixture
def worldmapc_arthur_leather_jacket(
    worldmapc_arthur_model: CharacterModel, worldmapc_kernel: Kernel
) -> StuffModel:
    arthur = worldmapc_arthur_model
    kernel = worldmapc_kernel

    jacket = _create_stuff(kernel, "LEATHER_JACKET")
    kernel.stuff_lib.set_carried_by(jacket.id, arthur.id)
    return jacket


@pytest.fixture
def worldmapc_arthur_leather_jacket_armor(
    worldmapc_arthur_model: CharacterModel,
    worldmapc_kernel: Kernel,
    worldmapc_arthur_leather_jacket: StuffModel,
) -> StuffModel:
    arthur = worldmapc_arthur_model
    kernel = worldmapc_kernel
    leather_jacket = worldmapc_arthur_leather_jacket

    kernel.stuff_lib.set_as_used_as_armor(arthur.id, leather_jacket.id)
    return leather_jacket
