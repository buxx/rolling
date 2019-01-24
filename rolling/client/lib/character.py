# coding: utf-8
import typing

from rolling.client.http.client import HttpClient
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel


class CharacterLib(object):
    def __init__(self, kernel: Kernel, client: HttpClient) -> None:
        self._kernel = kernel
        self._client = client

    def get_player_character(self, character_id: str) -> CharacterModel:
        return self._client.get_character(character_id)

    def get_zone_characters(
        self,
        world_row_i: int,
        world_col_i: int,
        excluded_character_ids: typing.List[str] = None,
    ) -> typing.List[CharacterModel]:
        return [
            c
            for c in self._client.get_zone_characters(world_row_i, world_col_i)
            if c.id not in excluded_character_ids
        ]
