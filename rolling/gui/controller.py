# coding: utf-8
import asyncio
from queue import Queue
import typing

from sqlalchemy.orm.exc import NoResultFound
import urwid

from rolling.client.http.client import HttpClient
from rolling.client.http.zone import ZoneWebSocketClient
from rolling.client.lib.character import CharacterLib
from rolling.client.lib.server import ServerLib
from rolling.client.lib.zone import ZoneLib
from rolling.exception import NotConnectedToServer, ZoneWebsocketJobFinished
from rolling.gui.map.object import Character
from rolling.gui.map.object import DisplayObjectManager
from rolling.gui.map.render import TileMapRenderEngine
from rolling.gui.map.widget import TileMapWidget
from rolling.gui.palette import PaletteGenerator
from rolling.gui.play.character import CreateCharacterBox
from rolling.gui.view import View
from rolling.kernel import Kernel
from rolling.log import gui_logger
from rolling.map.source import ZoneMapSource
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel


class Controller(object):
    def __init__(self, client: HttpClient, kernel: Kernel) -> None:
        self._client = client
        self._asyncio_loop: asyncio.AbstractEventLoop = None
        self._loop = None
        self._kernel = kernel
        self._view = View(self)
        self._palette_generator = PaletteGenerator(self._kernel)
        self._client: typing.Optional[HttpClient] = None
        self._server_lib: typing.Optional[ServerLib] = None
        self._character_lib: typing.Optional[CharacterLib] = None
        self._zone_lib: typing.Optional[ZoneLib] = None
        self._server_address: typing.Optional[str] = None
        self._player_character: typing.Optional[CharacterModel] = None
        self._received_zone_queue = Queue()
        self._to_send_zone_queue = Queue()
        self._zone_websocket_event = asyncio.Event()
        self._display_objects_manager = DisplayObjectManager([])

        self._kernel.init_client_db_session()

    @property
    def kernel(self) -> Kernel:
        return self._kernel

    @property
    def loop(self):
        return self._loop

    @property
    def player_character(self) -> CharacterModel:
        if self._player_character is None:
            raise NotConnectedToServer(
                "You try to use property set when connected to a server"
            )

        return self._player_character

    def main(self) -> None:
        self._asyncio_loop = asyncio.get_event_loop()
        self._loop = urwid.MainLoop(
            self._view,
            palette=self._palette_generator.create_palette(),
            event_loop=urwid.AsyncioEventLoop(loop=self._asyncio_loop),
        )
        self._loop.screen.set_terminal_properties(colors=256)

        self._asyncio_loop.create_task(self._get_zone_websocket_jobs())
        self._loop.run()

    async def _get_zone_websocket_jobs(self):
        zone_websocket_client = ZoneWebSocketClient(
            self,
            zone_lib=self._zone_lib,
            client_getter=lambda: self._client,
            received_zone_queue=self._received_zone_queue,
        )

        def capture_errors(decorated_function):
            async def wrapper(*args, **kwargs):
                try:
                    return await decorated_function(*args, **kwargs)
                except Exception as exc:
                    gui_logger.exception(str(exc))
                    # TODO: stop application

            return wrapper

        @capture_errors
        async def read():
            while True:
                gui_logger.info("Waiting for open a zone websocket connection")
                await self._zone_websocket_event.wait()
                gui_logger.info("Starting zone websocket listening")
                await zone_websocket_client.make_connection(
                    self._player_character.world_row_i,
                    self._player_character.world_col_i,
                )
                await zone_websocket_client.listen()
                gui_logger.info("Zone websocket job finished")

        @capture_errors
        async def write():
            while True:
                gui_logger.info("Waiting for an object to send to zone websocket")
                # FIXME BS 2019-01-14: this is blocking, see https://stackoverflow.com/questions/26413613/asyncio-is-it-possible-to-cancel-a-future-been-run-by-an-executor
                # to make it unblocking
                event = await self._asyncio_loop.run_in_executor(
                    None, self._to_send_zone_queue.get
                )
                await zone_websocket_client.send_event(event)

        return await asyncio.gather(read(), write())

    def _choose_server(self, server_address: str) -> None:
        # FIXME BS 2019-01-09: https must be available
        self._client = HttpClient("http://{}".format(server_address))
        self._server_lib = ServerLib(self._kernel, self._client)
        self._character_lib = CharacterLib(self.kernel, self._client)
        self._zone_lib = ZoneLib(self._kernel, self._client)
        self._server_address = server_address

        try:
            character_id = self._server_lib.get_current_character_id(server_address)
            self._choose_character(character_id)
        except NoResultFound:
            self._view.main_content_container.original_widget = CreateCharacterBox(
                callback=self._create_character
            )

    def _create_character(self, create_character_model: CreateCharacterModel) -> None:
        character_model = self._client.create_character(create_character_model)
        self._server_lib.save_character_id(self._server_address, character_model.id)
        self._choose_character(character_model.id)

    def _choose_character(self, character_id: str) -> None:
        # Prepare display objects
        self._player_character = self._character_lib.get_player_character(character_id)
        self._display_objects_manager.initialize()
        self._display_objects_manager.add_object(
            Character(
                self._player_character.zone_row_i, self._player_character.zone_col_i
            )
        )
        self._display_objects_manager.refresh_indexes()

        # Prepare map
        zone_map = self._zone_lib.get_zone(
            self._player_character.world_row_i, self._player_character.world_col_i
        )
        zone_map_source = ZoneMapSource(self._kernel, raw_source=zone_map.raw_source)
        tile_map_render_engine = TileMapRenderEngine(
            zone_map_source, display_objects_manager=self._display_objects_manager
        )
        tile_map_widget = TileMapWidget(self, tile_map_render_engine)

        # Establish web socket connection
        self._zone_websocket_event.set()

        # Setup main widget as zone map
        self._view.main_content_container.original_widget = tile_map_widget
