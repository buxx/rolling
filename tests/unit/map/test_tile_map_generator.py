# coding: utf-8
from rolling.kernel import Kernel
from rolling.map.generator.filler import DummyFillerFactory
from rolling.map.generator.filler import DummyTileMapFiller
from rolling.map.generator.generator import FromWorldMapGenerator
from rolling.map.generator.generator import TileMapGenerator
from rolling.map.source import WorldMapSource
from rolling.map.type.tile import Sand


class TestTileMapGenerator(object):
    def test_dummy_generation(self, worldmapc_kernel: Kernel):
        generator = TileMapGenerator(worldmapc_kernel, filler=DummyTileMapFiller(Sand))
        tile_map_source = generator.generate(width=11, height=11)

        assert 11 == tile_map_source.geography.width
        assert 11 == tile_map_source.geography.height

        assert (
            """::GEO
   ⡩⡩⡩⡩⡩   
  ⡩⡩⡩⡩⡩⡩⡩  
 ⡩⡩⡩⡩⡩⡩⡩⡩⡩ 
⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩
⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩
⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩
⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩
⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩⡩
 ⡩⡩⡩⡩⡩⡩⡩⡩⡩ 
  ⡩⡩⡩⡩⡩⡩⡩  
   ⡩⡩⡩⡩⡩   
"""
            == generator._current_raw_source
        )


class TestFromWorldMapGenerator(object):
    def test_dummy_generation(self, worldmapc_kernel: Kernel, worldmapsourcec_txt: str):
        world_map_source = WorldMapSource(worldmapc_kernel, worldmapsourcec_txt)
        generator = FromWorldMapGenerator(
            worldmapc_kernel,
            world_map_source,
            filler_factory=DummyFillerFactory(),
            default_map_width=11,
        )

        tile_maps = generator.generate()
        assert 20 == len(tile_maps)
