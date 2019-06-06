# coding: utf-8
import logging
from logging import Logger
import typing

from rolling.kernel import Kernel
from rolling.log import server_logger
from rolling.server.lib.character import CharacterLib


class TurnLib:
    def __init__(
        self,
        kernel: Kernel,
        character_lib: CharacterLib,
        logger: typing.Optional[Logger] = None,
    ) -> None:
        self._kernel = kernel
        self._character_lib = character_lib
        self._logger = logger or server_logger

    def execute_turn(self) -> None:
        self._increment_age()

    def _increment_age(self) -> None:
        # In future, increment role play age
        charchter_count = self._character_lib.get_all_character_count()
        self._logger.info(f"Compute age of {charchter_count} characters")

        for character_id in self._character_lib.get_all_character_ids():
            character_document = self._character_lib.get_document(character_id)
            self._logger.debug(
                f'Compute age of "{character_document.name}" ({character_document.id})'
            )
            character_document.alive_since += 1
            self._character_lib.update(character_document)
