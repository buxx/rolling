# coding: utf-8
import typing

import sqlalchemy

from rolling.model.action import ActionType
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
from rolling.model.stuff import StuffProperties
from rolling.model.stuff import Unit
from rolling.server.document.stuff import StuffDocument
from rolling.server.lib.action import CharacterAction

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
            # FIXME BS 2019-06-30: forgott to add new filed, refacto
            image=stuff_generation_properties.stuff.image,
        )

    @classmethod
    def create_document_from_stuff_properties(
        cls,
        properties: StuffProperties,
        world_col_i: typing.Optional[int] = None,
        world_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        zone_row_i: typing.Optional[int] = None,
    ) -> StuffDocument:
        return StuffDocument(
            stuff_id=properties.id,
            world_col_i=world_col_i,
            world_row_i=world_row_i,
            zone_col_i=zone_col_i,
            zone_row_i=zone_row_i,
            # properties
            filled_at=properties.filled_at,
            filled_unity=properties.filled_unity,
            clutter=properties.clutter,
            weight=properties.weight,
            # FIXME BS 2019-06-30: forgott to add new filed, refacto
            image=properties.image,
        )

    def add_stuff(self, doc: StuffDocument, commit: bool = True) -> None:
        self._kernel.server_db_session.add(doc)
        if commit:
            self._kernel.server_db_session.commit()

    def get_zone_stuffs(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
    ) -> typing.List[StuffModel]:
        filters = [
            StuffDocument.carried_by_id == None,
            StuffDocument.world_row_i == world_row_i,
            StuffDocument.world_col_i == world_col_i,
        ]

        if zone_row_i and zone_col_i:
            filters.extend(
                [
                    StuffDocument.zone_row_i == zone_row_i,
                    StuffDocument.zone_col_i == zone_col_i,
                ]
            )

        stuff_docs = (
            self._kernel.server_db_session.query(StuffDocument)
            .filter(sqlalchemy.and_(*filters))
            .all()
        )
        return [self._stuff_model_from_doc(doc) for doc in stuff_docs]

    def get_stuff(self, stuff_id: int) -> StuffModel:
        doc = self.get_stuff_doc(stuff_id)
        return self._stuff_model_from_doc(doc)

    def _stuff_model_from_doc(self, doc: StuffDocument) -> StuffModel:
        stuff_name = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            doc.stuff_id
        ).name
        return StuffModel(
            id=doc.id,
            name=stuff_name,
            zone_col_i=doc.zone_col_i,
            zone_row_i=doc.zone_row_i,
            filled_at=float(doc.filled_at) if doc.filled_at else None,
            filled_unity=Unit(doc.filled_unity) if doc.filled_unity else None,
            weight=float(doc.weight) if doc.weight else None,
            clutter=float(doc.clutter) if doc.clutter else None,
            image=doc.image if doc.image else None,
            carried_by=doc.carried_by_id,
            stuff_id=doc.stuff_id,
        )

    def get_carried_by(self, character_id: str) -> typing.List[StuffModel]:
        carried = (
            self._kernel.server_db_session.query(StuffDocument)
            .filter(StuffDocument.carried_by_id == character_id)
            .all()
        )
        return [self._stuff_model_from_doc(doc) for doc in carried]

    def get_stuff_doc(self, stuff_id: int) -> StuffDocument:
        return (
            self._kernel.server_db_session.query(StuffDocument)
            .filter(StuffDocument.id == stuff_id)
            .one()
        )

    def set_carried_by(
        self, stuff_id: int, character_id: str, commit: bool = True
    ) -> None:
        stuff_doc = self.get_stuff_doc(stuff_id)
        stuff_doc.carried_by_id = character_id
        if commit:
            self._kernel.server_db_session.commit()

    def get_carrying_actions(
        self, character: CharacterModel, stuff: StuffModel
    ) -> typing.List[CharacterAction]:
        actions: typing.List[CharacterAction] = []
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff.stuff_id
        )

        for action in stuff_properties.actions:
            # TODO BS 2019-07-02: Write a factory
            if action.type_ == ActionType.FILL:
                for fill_acceptable_type in action.fill_acceptable_types:
                    for (
                        resource
                    ) in self._kernel.game.world_manager.get_resource_on_or_around(
                        world_row_row_i=character.world_col_i,
                        world_col_i=character.world_col_i,
                        zone_row_i=character.zone_row_i,
                        zone_col_i=character.zone_col_i,
                        material_type=fill_acceptable_type,
                    ):
                        actions.append(
                            CharacterAction(
                                name=f"Fill {stuff.name} with {resource.name}",
                                # FIXME BS 2019-07-02: code it
                                link="FIXME: TODO",
                            )
                        )

        return actions
