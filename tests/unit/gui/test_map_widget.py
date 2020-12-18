# coding: utf-8
import aioresponses as aioresponses
import pytest
from unittest.mock import MagicMock

from rolling.client.http.client import HttpClient
from rolling.client.lib.zone import ZoneLib as ClientZoneLib
from rolling.gui.controller import Controller
from rolling.gui.map.object import CurrentPlayer
from rolling.gui.map.object import DisplayObjectManager
from rolling.gui.map.render import TileMapRenderEngine
from rolling.gui.map.widget import TileMapWidget
from rolling.kernel import Kernel
from rolling.map.source import ZoneMapSource
from rolling.model.character import CharacterModel
from rolling.server.lib.zone import ZoneLib as ServerZoneLib


@pytest.fixture
def tilemapa_source(tilemapsourcea_txt: str, worldmapb_kernel: Kernel) -> ZoneMapSource:
    return ZoneMapSource(worldmapb_kernel, tilemapsourcea_txt)


@pytest.fixture
def zone_map_widget(
    tilemapa_render_engine: TileMapRenderEngine,
    controller: Controller,
    tilemapa_source: ZoneMapSource,
) -> TileMapWidget:
    return TileMapWidget(
        controller=controller, render_engine=tilemapa_render_engine, zone_map_source=tilemapa_source
    )


@pytest.fixture
def aioresponses_mock() -> aioresponses:
    with aioresponses.aioresponses() as aiohttp_mock:
        yield aiohttp_mock


@pytest.fixture
def worldmapb_server_zone_lib(worldmapb_kernel: Kernel) -> ServerZoneLib:
    return ServerZoneLib(worldmapb_kernel)


@pytest.fixture
def http_client(
    aioresponses_mock: aioresponses, worldmapb_server_zone_lib: ServerZoneLib
) -> HttpClient:
    client = HttpClient(server_address="http://127.0.0.1")

    def _get_tile_types():
        return worldmapb_server_zone_lib.get_all_tiles()

    client.get_tile_types = _get_tile_types
    return client


@pytest.fixture
def worldmapb_client_zone_lib(worldmapb_kernel: Kernel, http_client: HttpClient) -> ClientZoneLib:
    return ClientZoneLib(worldmapb_kernel, http_client)


@pytest.fixture
def controller(
    worldmapb_kernel: Kernel,
    http_client: HttpClient,
    worldmapb_client_zone_lib: ClientZoneLib,
    franck_model: CharacterModel,
    display_object_manager__empty: DisplayObjectManager,
) -> Controller:
    controller = Controller(
        client=http_client,
        kernel=worldmapb_kernel,
        display_object_manager=display_object_manager__empty,
    )
    controller._zone_lib = worldmapb_client_zone_lib
    controller._loop = MagicMock()
    controller._player_character = franck_model
    return controller


@pytest.fixture
def franck_model(default_character_competences: dict) -> CharacterModel:
    return CharacterModel(
        id="abc", name="franck", **default_character_competences, skills={}, knowledges=[]
    )


class TestZoneMapWidget:
    def test_unit__center_on_player__ok__nominal_case(
        self,
        tilemapa_render_engine: TileMapRenderEngine,
        zone_map_widget: TileMapWidget,
        franck_model: CharacterModel,
    ) -> None:
        columns = 9
        rows = 6
        player = CurrentPlayer(character=franck_model, col_i=4, row_i=4)

        # Set player on map
        tilemapa_render_engine.display_objects_manager.add_object(player)
        tilemapa_render_engine.display_objects_manager.refresh_indexes()

        zone_map_widget.render((columns, rows))  # Default focus on player

        # Grab rows and decode them to readable thing
        str_rows = [r.decode() for r in tilemapa_render_engine.rows]

        assert [
            "      ⡩⡩⡩",
            "     ⡩⡩⡩⡩",
            "    ⡩⡩⡩⡩⡩",
            "   ⡩ጰ⡩⡩⡩⡩",
            "  ⡩⡩⡩⡩ʛ⡩⡩",
            " ⡩⡩⡩⡩⡩⡩⡩⡩",
        ] == str_rows
