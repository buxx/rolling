# coding: utf-8
import aiohttp
import requests
import serpyco

from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel


class HttpClient(object):
    def __init__(self, server_address: str) -> None:
        self._server_address = server_address
        self._create_character_serializer = serpyco.Serializer(CreateCharacterModel)
        self._character_serializer = serpyco.Serializer(CharacterModel)

    def create_character(
        self, create_character_model: CreateCharacterModel
    ) -> CharacterModel:
        response = requests.post(
            "{}/character".format(self._server_address),
            json=self._create_character_serializer.dump(create_character_model),
        )
        response_json = response.json()
        return self._character_serializer.load(response_json)
