# coding: utf-8
import os

import pytest

from rolling.kernel import Kernel
from rolling.map.generator.filler import DummyTileMapFiller
from rolling.map.generator.generator import TileMapGenerator
from rolling.map.source import TileMapSource
from rolling.map.type.tile import SeaWater


@pytest.fixture
def worldmapsourcea_txt() -> str:
    with open(os.path.join("tests", "src", "worldmapa.txt")) as f:
        return f.read()


@pytest.fixture
def worldmapsourceb_txt() -> str:
    with open(os.path.join("tests", "src", "worldmapb.txt")) as f:
        return f.read()


@pytest.fixture
def worldmapsourcec_txt() -> str:
    with open(os.path.join("tests", "src", "worldmapc.txt")) as f:
        return f.read()


@pytest.fixture
def worldmapc_kernel(worldmapsourcec_txt) -> Kernel:
    return Kernel(worldmapsourcec_txt)


@pytest.fixture
def worldmapc_full_sea_tile_map_source(worldmapc_kernel: Kernel) -> TileMapSource:
    generator = TileMapGenerator(worldmapc_kernel, DummyTileMapFiller(SeaWater))
    return generator.generate(11)
