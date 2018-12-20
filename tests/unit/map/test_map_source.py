# coding: utf-8
from rolling.map.source import WorldMapSource
from rolling.map.type import world


class TestWorldMapSource(object):
    def test_unit__all__ok__nominal_case(self, worldmapsourcea_txt: str):
        source = WorldMapSource(None, worldmapsourcea_txt)

        # legend
        assert source.legend.get_type_with_str("~") == world.Sea
        assert source.legend.get_type_with_str("ፆ") == world.Jungle
        assert source.legend.get_type_with_str("∩") == world.Hill
        assert source.legend.get_type_with_str("⡩") == world.Beach
        assert source.legend.get_type_with_str("⠃") == world.Plain
        assert world.Sea == source.legend.get_default_type()

        # geography
        assert source.geography
        assert 25 == source.geography.width
        assert 13 == source.geography.height
