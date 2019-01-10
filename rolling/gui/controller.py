# coding: utf-8
import asyncio
import typing

from sqlalchemy.orm.exc import NoResultFound
import urwid

from rolling.client.http.client import HttpClient
from rolling.client.lib.server import ServerLib
from rolling.gui.palette import PaletteGenerator
from rolling.gui.play.character import CreateCharacterBox
from rolling.gui.view import View
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel


class Controller(object):
    def __init__(self, client: HttpClient, kernel: Kernel) -> None:
        self._client = client
        self._loop = None
        self._kernel = kernel
        self._view = View(self)
        self._palette_generator = PaletteGenerator(self._kernel)
        self._client: typing.Optional[HttpClient] = None
        self._server_lib: typing.Optional[ServerLib] = None
        self._server_address: typing.Optional[str] = None
        self._character: typing.Optional[CharacterModel] = None

        self._kernel.init_client_db_session()

    @property
    def kernel(self) -> Kernel:
        return self._kernel

    @property
    def loop(self):
        return self._loop

    def main(self) -> None:
        self._loop = urwid.MainLoop(
            self._view, palette=self._palette_generator.create_palette()
        )
        self._loop.screen.set_terminal_properties(colors=256)
        self._loop.run()

    def _choose_server(self, server_address: str) -> None:
        # FIXME BS 2019-01-09: https must be available
        self._client = HttpClient("http://{}".format(server_address))
        self._server_lib = ServerLib(self._kernel, self._client)
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
        pass
