# coding: utf-8
from sqlalchemy.orm.exc import NoResultFound

from rolling.client.document.server import ServerDocument
from rolling.client.http.client import HttpClient
from rolling.kernel import Kernel


class ServerLib:
    def __init__(self, kernel: Kernel, client: HttpClient) -> None:
        self._kernel = kernel
        self._client = client

    def get_current_character_id(self, server_address: str) -> str:
        server = (
            self._kernel.client_db_session.query(ServerDocument)
            .filter(ServerDocument.server_address == server_address)
            .one()
        )

        if server.current_character_id:
            return server.current_character_id

        raise NoResultFound()

    def save_character_id(self, server_address: str, character_id: str) -> None:
        try:
            server = (
                self._kernel.client_db_session.query(ServerDocument)
                .filter(ServerDocument.server_address == server_address)
                .one()
            )
        except NoResultFound:
            server = ServerDocument()
            server.server_address = server_address

        server.current_character_id = character_id
        self._kernel.client_db_session.add(server)
        self._kernel.client_db_session.commit()
