# coding: utf-8
import typing

from rolling.client.http.client import HttpClient
from rolling.kernel import Kernel
from rolling.map.source import ZoneMapSource
from rolling.model.character import CharacterModel
from rolling.model.zone import ZoneMapModel


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

    def change_character_zone(
        self,
        from_zone: ZoneMapModel,
        to_zone: ZoneMapModel,
        character: CharacterModel,
        world_row_i: int,
        world_col_i: int,
    ) -> None:
        # FIXME BS 2019-03-08 code client request (server side to)
        character.world_row_i = world_row_i
        character.world_col_i = world_col_i

        # Replace character on zone
        to_zone_source = ZoneMapSource(self._kernel, to_zone.raw_source)
        disp_char = character.display_object

        # bottom to top
        if disp_char.row_i == to_zone_source.geography.height - 1:
            disp_char.row_i = 0
        # top to bottom
        elif disp_char.row_i == 0:
            disp_char.row_i = to_zone_source.geography.height - 1
        # left to right
        elif disp_char.col_i == to_zone_source.geography.width - 1:
            disp_char.col_i = 0
        # right to left
        elif disp_char.col_i == 0:
            disp_char.col_i = to_zone_source.geography.width - 1
