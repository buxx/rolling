# coding: utf-8
from rolling.gui.kernel import Kernel
from rolling.map.generator.filler import DummyTileMapFiller
from rolling.map.generator.generator import TileMapGenerator
from rolling.map.type.tile import Sand
from rolling.map.type.world import Sea


class TestTileMapGenerator(object):
    def test_generation(self, worldmapc_kernel: Kernel):
        generator = TileMapGenerator(worldmapc_kernel, filler=DummyTileMapFiller(Sand))
        tile_map_source = generator.generate(
            north_west_type=Sea,
            north_type=Sea,
            north_est_type=Sea,
            west_type=Sea,
            est_type=Sea,
            south_west_type=Sea,
            south_type=Sea,
            south_est_type=Sea,
            generate_type=Sea,
            width=11,
            height=11,
        )

        assert 11 == tile_map_source.geography.width
        assert 11 == tile_map_source.geography.height

        assert """::GEO
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
""" == generator._current_raw_source

