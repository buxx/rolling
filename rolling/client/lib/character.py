# coding: utf-8
from rolling.client.http.client import HttpClient
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel


class CharacterLib(object):
    def __init__(self, kernel: Kernel, client: HttpClient) -> None:
        self._kernel = kernel
        self._client = client

    def get_player_character(self, character_id: str) -> CharacterModel:
        return self._client.get_character(character_id)
