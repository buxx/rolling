# coding: utf-8
from sqlalchemy.orm.exc import NoResultFound

from rolling.client.document.server import ServerDocument
from rolling.client.http.client import HttpClient
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.zone import ZoneMapModel


class ZoneLib(object):
    def __init__(self, kernel: Kernel, client: HttpClient) -> None:
        self._kernel = kernel
        self._client = client

    def get_zone(self, world_row_i: int, world_col_i: int) -> ZoneMapModel:
        return self._client.get_zone(world_row_i, world_col_i)
