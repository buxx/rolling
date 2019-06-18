# coding: utf-8
import typing

import sqlalchemy

from rolling.model.stuff import StuffModel
from rolling.model.stuff import Unit
from rolling.server.document.stuff import StuffDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.stuff import ZoneGenerationStuff


class StuffLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    @classmethod
    def create_document_from_generation_properties(
        cls,
        stuff_generation_properties: "ZoneGenerationStuff",
        stuff_id: str,
        world_col_i: int,
        world_row_i: int,
        zone_col_i: int,
        zone_row_i: int,
    ) -> StuffDocument:
        return StuffDocument(
            stuff_id=stuff_id,
            world_col_i=world_col_i,
            world_row_i=world_row_i,
            zone_col_i=zone_col_i,
            zone_row_i=zone_row_i,
            # properties
            filled_at=stuff_generation_properties.meta.get("filled_at")
            or stuff_generation_properties.stuff.filled_at,
            filled_unity=stuff_generation_properties.stuff.filled_unity,
            weight=stuff_generation_properties.meta.get("weight")
            or stuff_generation_properties.stuff.weight,
            clutter=stuff_generation_properties.meta.get("clutter")
            or stuff_generation_properties.stuff.clutter,
        )

    def add_stuff(self, doc: StuffDocument, commit: bool = True) -> None:
        self._kernel.server_db_session.add(doc)
        if commit:
            self._kernel.server_db_session.commit()

    def get_zone_stuffs(
        self, world_row_i: int, world_col_i: int
    ) -> typing.List[StuffModel]:
        stuff_docs = (
            self._kernel.server_db_session.query(StuffDocument)
            .filter(
                sqlalchemy.and_(
                    StuffDocument.world_row_i == world_row_i,
                    StuffDocument.world_col_i == world_col_i,
                )
            )
            .all()
        )
        return [self._stuff_model_from_doc(doc) for doc in stuff_docs]

    def _stuff_model_from_doc(self, doc: StuffDocument) -> StuffModel:
        stuff_name = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            doc.stuff_id
        ).name
        return StuffModel(
            id=doc.id,
            name=stuff_name,
            zone_col_i=doc.zone_col_i,
            zone_row_i=doc.zone_row_i,
            filled_at=float(doc.filled_at),
            filled_unity=Unit(doc.filled_unity),
            weight=float(doc.weight),
            clutter=float(doc.clutter),
        )
