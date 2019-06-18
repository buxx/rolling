# coding: utf-8
import typing

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
