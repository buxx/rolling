# coding: utf-8
import typing

import sqlalchemy

from rolling.model.character import CharacterModel
from rolling.model.measure import Unit
from rolling.model.stuff import StuffModel
from rolling.model.stuff import StuffProperties
from rolling.server.action import ActionFactory
from rolling.server.document.stuff import StuffDocument
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.stuff import ZoneGenerationStuff


class StuffLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel
        self._action_factory = ActionFactory(kernel)

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
            filled_with_resource=stuff_generation_properties.meta.get(
                "filled_with_resource"
            )
            or stuff_generation_properties.stuff.filled_with_resource,
            filled_unity=stuff_generation_properties.stuff.filled_unity,
            weight=stuff_generation_properties.meta.get("weight")
            or stuff_generation_properties.stuff.weight,
            filled_capacity=stuff_generation_properties.stuff.filled_capacity,
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
            filled_with_resource=properties.filled_with_resource,
            filled_capacity=properties.filled_capacity,
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
            filled_with_resource=doc.filled_with_resource
            if doc.filled_with_resource
            else None,
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
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff.stuff_id
        )

        for description in stuff_properties.descriptions:
            action = self._action_factory.get_with_stuff_action(description)
            actions.extend(action.get_character_actions(character, stuff))

        return actions

    def fill_stuff_with_resource(self, stuff: StuffModel, resource_type: str) -> None:
        doc = self.get_stuff_doc(stuff.id)
        doc.fill(resource_type, at=100.0)

        self._kernel.server_db_session.add(doc)
        self._kernel.server_db_session.commit()

    def empty_stuff(self, stuff: StuffModel) -> None:
        doc = self.get_stuff_doc(stuff.id)
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff.stuff_id
        )
        doc.empty(stuff_properties)

        self._kernel.server_db_session.add(doc)
        self._kernel.server_db_session.commit()
