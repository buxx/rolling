# coding: utf-8
from rolling.gui.map.render import WorldMapRenderEngine
from rolling.map.source import WorldMapSource


class TestWorldMapRender(object):
    def test_unit__render__ok__just_space(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3)

        assert [b"~~~~", b"~^^~", b"~~~~"] == engine.rows

    def test_unit__render__ok__height_more_one(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=4)

        assert [b"    ", b"~~~~", b"~^^~", b"~~~~"] == engine.rows

    def test_unit__render__ok__height_less_one(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=2)

        assert [b"~~~~", b"~^^~"] == engine.rows

    def test_unit__render__ok__height_more_two(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=5)

        assert [b"    ", b"~~~~", b"~^^~", b"~~~~", b"    "] == engine.rows

    def test_unit__render__ok__height_less_two(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=1)

        assert [b"~~~~"] == engine.rows

    def test_unit__render__ok__height_more_three(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=6)

        assert [b"    ", b"~~~~", b"~^^~", b"~~~~", b"    ", b"    "] == engine.rows

    def test_unit__render__ok__width_more_one(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=5, height=3)

        assert [b" ~~~~", b" ~^^~", b" ~~~~"] == engine.rows

    def test_unit__render__ok__width_less_one(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=3, height=3)

        assert [b"~~~", b"~^^", b"~~~"] == engine.rows

    def test_unit__render__ok__width_more_two(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=6, height=3)

        assert [b" ~~~~ ", b" ~^^~ ", b" ~~~~ "] == engine.rows

    def test_unit__render__ok__width_less_two(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=2, height=3)

        assert [b"~~", b"~^", b"~~"] == engine.rows

    def test_unit__render__ok__width_more_three(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=7, height=3)

        assert [b" ~~~~  ", b" ~^^~  ", b" ~~~~  "] == engine.rows
