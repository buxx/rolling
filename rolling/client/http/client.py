# coding: utf-8
import typing

import aiohttp
import requests
from requests import Response
import serpyco

from rolling.exception import ClientServerExchangeError
from rolling.map.source import WorldMapSource
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.zone import ZoneMapModel
from rolling.model.zone import ZoneTileTypeModel


class HttpClient:
    def __init__(self, server_address: str) -> None:
        self._server_address = server_address
        self._create_character_serializer = serpyco.Serializer(CreateCharacterModel)
        self._character_serializer = serpyco.Serializer(CharacterModel)
        self._characters_serializer = serpyco.Serializer(CharacterModel, many=True)
        self._zone_serializer = serpyco.Serializer(ZoneMapModel)
        self._tiles_serializer = serpyco.Serializer(ZoneTileTypeModel, many=True)

    def _check_response(self, response: Response) -> None:
        if response.status_code not in (200, 204):
            raise ClientServerExchangeError(
                f"Server response is {response.status_code},{response.json()}"
            )

    def create_character(
        self, create_character_model: CreateCharacterModel
    ) -> CharacterModel:
        response = requests.post(
            "{}/character".format(self._server_address),
            json=self._create_character_serializer.dump(create_character_model),
        )
        response_json = response.json()
        return self._character_serializer.load(response_json)

    def get_character(self, character_id: str) -> CharacterModel:
        response = requests.get(
            "{}/character/{}".format(self._server_address, character_id)
        )
        response_json = response.json()
        return self._character_serializer.load(response_json)

    def get_zone(self, world_row_i: int, world_col_i: int) -> ZoneMapModel:
        response = requests.get(
            "{}/zones/{}/{}".format(self._server_address, world_row_i, world_col_i)
        )
        response_json = response.json()
        return self._zone_serializer.load(response_json)

    def get_zone_events_url(self, row_i: int, col_i: int) -> str:
        return f"{self._server_address}/zones/{row_i}/{col_i}/events"

    def get_zone_characters(
        self, world_row_i: int, world_col_i: int
    ) -> typing.List[CharacterModel]:
        response = requests.get(
            "{}/zones/{}/{}/characters".format(
                self._server_address, world_row_i, world_col_i
            )
        )
        response_json = response.json()
        return self._characters_serializer.load(response_json)

    def get_world_source(self) -> str:
        response = requests.get("{}/world/source".format(self._server_address))
        return response.text

    def get_tile_types(self) -> typing.List[ZoneTileTypeModel]:
        response = requests.get(f"{self._server_address}/zones/tiles")
        return self._tiles_serializer.load(response.json())

    def move_character(
        self, character_id: str, to_world_row: int, to_world_col: int
    ) -> None:
        self._check_response(
            requests.put(
                f"{self._server_address}/character/{character_id}/move"
                f"?to_world_row={to_world_row}&to_world_col={to_world_col}"
            )
        )
