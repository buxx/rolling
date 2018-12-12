# coding: utf-8
from rolling.gui.map.render import WorldMapRenderEngine
from rolling.map.source import WorldMapSource
from rolling.map.world import type as world


class TestWorldMapRender(object):
    def test_unit__render__ok__just_space(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3)

        assert [b"~~~~", b"~^^~", b"~~~~"] == engine.rows
        assert [
            [(world.Sea.get_full_id(), 4)],
            [
                (world.Sea.get_full_id(), 1),
                (world.Mountain.get_full_id(), 2),
                (world.Sea.get_full_id(), 1)
            ],
            [(world.Sea.get_full_id(), 4)],
        ] == engine.attributes

    def test_unit__render__ok__just_space_with_horizontal_less_1_offset(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3, offset_horizontal=-1)

        assert [b"~~~ ", b"^^~ ", b"~~~ "] == engine.rows
        assert [
            [(world.Sea.get_full_id(), 3), (None, 1)],
            [
                (world.Mountain.get_full_id(), 2),
                (world.Sea.get_full_id(), 1),
                (None, 1),
            ],
            [(world.Sea.get_full_id(), 3), (None, 1)],
        ] == engine.attributes

    def test_unit__render__ok__just_space_with_horizontal_more_1_offset(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3, offset_horizontal=1)

        assert [b" ~~~", b" ~^^", b" ~~~"] == engine.rows
        assert [
            [(None, 1), (world.Sea.get_full_id(), 3)],
            [
                (None, 1),
                (world.Sea.get_full_id(), 1),
                (world.Mountain.get_full_id(), 2),
            ],
            [(None, 1), (world.Sea.get_full_id(), 3)],
        ] == engine.attributes

    def test_unit__render__ok__just_space_with_horizontal_more_2_offset(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3, offset_horizontal=2)

        assert [b"  ~~", b"  ~^", b"  ~~"] == engine.rows
        assert [
            [(None, 2), (world.Sea.get_full_id(), 2)],
            [
                (None, 2),
                (world.Sea.get_full_id(), 1),
                (world.Mountain.get_full_id(), 1),
            ],
            [(None, 2), (world.Sea.get_full_id(), 2)],
        ] == engine.attributes

    def test_unit__render__ok__just_space_with_horizontal_less_2_offset(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3, offset_horizontal=-2)

        assert [b"~~  ", b"^~  ", b"~~  "] == engine.rows
        assert [
            [(world.Sea.get_full_id(), 2), (None, 2)],
            [
                (world.Mountain.get_full_id(), 1),
                (world.Sea.get_full_id(), 1),
                (None, 2),
            ],
            [(world.Sea.get_full_id(), 2), (None, 2)],
        ] == engine.attributes

    def test_unit__render__ok__just_space_with_vertical_less_1_offset(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3, offset_vertical=-1)

        assert [b"~^^~", b"~~~~", b"    "] == engine.rows
        assert [
            [
                (world.Sea.get_full_id(), 1),
                (world.Mountain.get_full_id(), 2),
                (world.Sea.get_full_id(), 1),
            ],
            [(world.Sea.get_full_id(), 4)],
            [(None, 4)],
        ] == engine.attributes

    def test_unit__render__ok__just_space_with_vertical_more_1_offset(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3, offset_vertical=1)

        assert [b"    ", b"~~~~", b"~^^~"] == engine.rows
        assert [
            [(None, 4)],
            [(world.Sea.get_full_id(), 4)],
            [
                (world.Sea.get_full_id(), 1),
                (world.Mountain.get_full_id(), 2),
                (world.Sea.get_full_id(), 1),
            ],
        ] == engine.attributes

    def test_unit__render__ok__just_space_with_vertical_less_2_offset(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3, offset_vertical=-2)

        assert [b"~~~~", b"    ", b"    "] == engine.rows
        assert [
            [(world.Sea.get_full_id(), 4)],
            [(None, 4)],
            [(None, 4)],
        ] == engine.attributes

    def test_unit__render__ok__just_space_with_vertical_more_2_offset(self, worldmapsourceb_txt: str):
        source = WorldMapSource(worldmapsourceb_txt)
        engine = WorldMapRenderEngine(source)
        engine.render(width=4, height=3, offset_vertical=2)

        assert [b"    ", b"    ", b"~~~~"] == engine.rows
        assert [
            [(None, 4)],
            [(None, 4)],
            [(world.Sea.get_full_id(), 4)],
        ] == engine.attributes

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
