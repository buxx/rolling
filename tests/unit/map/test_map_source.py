# coding: utf-8
from rolling.map.source import WorldMapSource
from rolling.map.world import type as world


class TestWorldMapSource(object):
    def test_unit__all__ok__nominal_case(
        self,
        worldmapsourcea_txt: str,
    ):
        source = WorldMapSource(worldmapsourcea_txt)

        # legend
        assert source.legend.get_type_with_str('~') == world.Sea
        assert source.legend.get_type_with_str('ፆ') == world.Jungle
        assert source.legend.get_type_with_str('∩') == world.Hill
        assert source.legend.get_type_with_str('⡩') == world.Beach
        assert source.legend.get_type_with_str('⠃') == world.Plain

        # geography
        assert source.geography
        assert 25 == source.geography.width
        assert 13 == source.geography.height
