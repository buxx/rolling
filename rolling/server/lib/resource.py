# coding: utf-8
import typing

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.elements import and_

from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.resource import ResourceDescriptionModel
from rolling.server.document.character import CharacterDocument
from rolling.server.document.resource import ResourceDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class ResourceLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def add_resource_to_character(
        self,
        character_doc: CharacterDocument,
        resource_id: str,
        quantity: float,
        commit: bool = True,
    ) -> None:
        resource_description: ResourceDescriptionModel = self._kernel.game.config.resources[
            resource_id
        ]
        try:
            resource = (
                self._kernel.server_db_session.query(ResourceDocument)
                .filter(
                    and_(
                        ResourceDocument.carried_by_id == character_doc.id,
                        ResourceDocument.resource_id == resource_id,
                    )
                )
                .one()
            )
        except NoResultFound:
            resource = ResourceDocument(
                resource_id=resource_id,
                carried_by_id=character_doc.id,
                quantity=0.0,
                unit=resource_description.unit.value,
            )

        resource.quantity = float(resource.quantity) + quantity
        self._kernel.server_db_session.add(resource)

        if commit:
            self._kernel.server_db_session.commit()

    def get_carried_by(
        self, character_id: str
    ) -> typing.List[CarriedResourceDescriptionModel]:
        carried = (
            self._kernel.server_db_session.query(ResourceDocument)
            .filter(ResourceDocument.carried_by_id == character_id)
            .all()
        )
        return [self._carried_resource_model_from_doc(doc) for doc in carried]

    def _carried_resource_model_from_doc(
        self, doc: ResourceDocument
    ) -> CarriedResourceDescriptionModel:
        resource_description = self._kernel.game.config.resources[doc.resource_id]
        return CarriedResourceDescriptionModel(
            id=doc.resource_id,
            name=resource_description.name,
            weight=float(doc.quantity) * resource_description.weight,
            material_type=resource_description.material_type,
            unit=resource_description.unit,
            clutter=float(doc.quantity) * resource_description.clutter,
            quantity=float(doc.quantity),
        )
