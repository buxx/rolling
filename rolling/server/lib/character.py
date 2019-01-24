# coding: utf-8
import typing
import uuid

from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.server.document.character import CharacterDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class CharacterLib(object):
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def create(self, create_character_model: CreateCharacterModel) -> str:
        character = CharacterDocument()
        character.id = uuid.uuid4().hex
        character.name = create_character_model.name

        # Place on zone
        world_row_i, world_col_i = self._kernel.get_start_world_coordinates()
        zone_row_i, zone_col_i = self._kernel.get_start_zone_coordinates(
            world_row_i, world_col_i
        )

        character.world_row_i = world_row_i
        character.world_col_i = world_col_i
        character.zone_row_i = zone_row_i
        character.zone_col_i = zone_col_i

        self._kernel.server_db_session.add(character)
        self._kernel.server_db_session.commit()
        return character.id

    def _get_document(self, id_: str) -> CharacterDocument:
        return (
            self._kernel.server_db_session.query(CharacterDocument)
            .filter(CharacterDocument.id == id_)
            .one()
        )

    def get(self, id_: str) -> CharacterModel:
        character_document = self._get_document(id_)
        return CharacterModel(
            id=character_document.id,
            name=character_document.name,
            world_col_i=character_document.world_col_i,
            world_row_i=character_document.world_row_i,
            zone_col_i=character_document.zone_col_i,
            zone_row_i=character_document.zone_row_i,
        )

    def move_on_zone(
        self, character: CharacterModel, to_row_i: int, to_col_i: int
    ) -> None:
        character_document = self._get_document(character.id)
        character_document.zone_row_i = to_row_i
        character_document.zone_col_i = to_col_i
        self._kernel.server_db_session.add(character_document)
        self._kernel.server_db_session.commit()
