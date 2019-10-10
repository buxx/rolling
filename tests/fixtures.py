# coding: utf-8
import os

import pytest

from rolling.gui.map.object import DisplayObjectManager
from rolling.gui.map.render import TileMapRenderEngine
from rolling.gui.map.render import WorldMapRenderEngine
from rolling.kernel import Kernel
from rolling.map.generator.filler.dummy import DummyTileMapFiller
from rolling.map.generator.generator import TileMapGenerator
from rolling.map.source import WorldMapSource
from rolling.map.source import ZoneMapSource
from rolling.map.type.zone import SeaWater
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib


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
def worldmapa_kernel(worldmapsourcea_txt) -> Kernel:
    return Kernel(worldmapsourcea_txt)


@pytest.fixture
def worldmapb_kernel(worldmapsourceb2_txt) -> Kernel:
    return Kernel(worldmapsourceb2_txt)


@pytest.fixture
def worldmapb2_kernel(worldmapsourceb2_txt) -> Kernel:
    return Kernel(worldmapsourceb2_txt)


@pytest.fixture
def worldmapc_kernel(worldmapsourcec_txt) -> Kernel:
    return Kernel(worldmapsourcec_txt)


@pytest.fixture
def worldmapc_with_zones_kernel(worldmapsourcec_txt, tmp_path) -> Kernel:
    server_db_path = tmp_path / "server.db"
    kernel = Kernel(
        worldmapsourcec_txt,
        tile_maps_folder="tests/src/worldmapc_zones",
        game_config_folder="tests/src/game1",
        server_db_path=server_db_path,
    )
    kernel.init_server_db_session()
    return kernel


@pytest.fixture
def worldmapc_with_zones_server_character_lib(worldmapc_with_zones_kernel: Kernel) -> CharacterLib:
    return CharacterLib(worldmapc_with_zones_kernel)


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
def worldmapc_with_zones_stuff_lib(worldmapc_with_zones_kernel: Kernel) -> StuffLib:
    return StuffLib(worldmapc_with_zones_kernel)


@pytest.fixture
def default_character_competences() -> dict:
    return {
        "background_story": "",
        "max_life_comp": 5.0,
        "hunting_and_collecting_comp": 2.0,
        "find_water_comp": 1.0,
    }
