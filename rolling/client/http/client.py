# coding: utf-8
import typing

import requests
from requests import Response
import serpyco

from guilang.description import Description
from rolling.exception import ClientServerExchangeError
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.stuff import StuffModel
from rolling.model.zone import ZoneMapModel, ZoneRequiredPlayerData
from rolling.model.zone import ZoneTileTypeModel


class HttpClient:
    def __init__(self, server_address: str) -> None:
        self._server_address = server_address
        self._create_character_serializer = serpyco.Serializer(CreateCharacterModel)
        self._character_serializer = serpyco.Serializer(CharacterModel)
        self._characters_serializer = serpyco.Serializer(CharacterModel, many=True)
        self._stuffs_serializer = serpyco.Serializer(StuffModel, many=True)
        self._zone_serializer = serpyco.Serializer(ZoneMapModel)
        self._tiles_serializer = serpyco.Serializer(ZoneTileTypeModel, many=True)
        self._gui_description_serializer = serpyco.Serializer(Description)
        self._zone_required_character_data_serializer = serpyco.Serializer(ZoneRequiredPlayerData)

    @property
    def character_serializer(self) -> serpyco.Serializer:
        return self._character_serializer

    def _check_response(self, response: Response) -> None:
        if response.status_code not in (200, 204):
            raise ClientServerExchangeError(
                f"Server response is {response.status_code},{response.json()}"
            )

    def request_post(self, path: str, data: dict = None) -> Response:
        data = data or {}
        return requests.post(f"{self._server_address}/{path.lstrip('/')}", json=data)

    def get_character(self, character_id: str) -> CharacterModel:
        response = requests.get(
            "{}/character/{}".format(self._server_address, character_id)
        )
        self._check_response(response)
        response_json = response.json()
        return self._character_serializer.load(response_json)

    def get_zone(self, world_row_i: int, world_col_i: int) -> ZoneMapModel:
        response = requests.get(
            "{}/zones/{}/{}".format(self._server_address, world_row_i, world_col_i)
        )
        self._check_response(response)
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
        self._check_response(response)
        response_json = response.json()
        return self._characters_serializer.load(response_json)

    def get_world_source(self) -> str:
        response = requests.get("{}/world/source".format(self._server_address))
        self._check_response(response)
        return response.text

    def get_tile_types(self) -> typing.List[ZoneTileTypeModel]:
        response = requests.get(f"{self._server_address}/zones/tiles")
        self._check_response(response)
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

    def get_create_character_description(self) -> Description:
        response = requests.get(f"{self._server_address}/_describe/character/create")
        self._check_response(response)
        return self._gui_description_serializer.load(response.json())

    def get_character_card_description(self, character_id: str) -> Description:
        response = requests.get(
            f"{self._server_address}/_describe/character/{character_id}/card"
        )
        self._check_response(response)
        return self._gui_description_serializer.load(response.json())

    def get_character_inventory(self, character_id: str) -> Description:
        response = requests.get(
            f"{self._server_address}/_describe/character/{character_id}/inventory"
        )
        self._check_response(response)
        return self._gui_description_serializer.load(response.json())

    def get_character_on_place_actions(self, character_id: str) -> Description:
        response = requests.get(
            f"{self._server_address}/_describe/character/{character_id}/on_place_actions"
        )
        self._check_response(response)
        return self._gui_description_serializer.load(response.json())

    def get_zone_stuffs(
        self, world_row_i: int, world_col_i: int
    ) -> typing.List[StuffModel]:
        response = requests.get(
            "{}/zones/{}/{}/stuff".format(
                self._server_address, world_row_i, world_col_i
            )
        )
        self._check_response(response)
        response_json = response.json()
        return self._stuffs_serializer.load(response_json)

    def get_character_events(self, character_id: str) -> Description:
        response = requests.get(
            f"{self._server_address}/_describe/character/{character_id}/events"
        )
        self._check_response(response)
        return self._gui_description_serializer.load(response.json())

    def get_zone_required_character_data(self, character_id: str) -> ZoneRequiredPlayerData:
        response = requests.get(
            f"{self._server_address}/character/{character_id}/zone_data"
        )
        self._check_response(response)
        return self._zone_required_character_data_serializer.load(response.json())
