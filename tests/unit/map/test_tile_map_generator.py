# coding: utf-8
from rolling.gui.kernel import Kernel
from rolling.map.generator.filler import DummyTileMapFiller
from rolling.map.generator.generator import TileMapGenerator
from rolling.map.type.tile import Sand


class TestTileMapGenerator(object):
    def test_dummy_generation(self, worldmapc_kernel: Kernel):
        generator = TileMapGenerator(worldmapc_kernel, filler=DummyTileMapFiller(Sand))
        tile_map_source = generator.generate(
            width=11,
            height=11,
        )

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
