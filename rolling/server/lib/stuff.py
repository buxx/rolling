# coding: utf-8
import sqlalchemy
from sqlalchemy import Column
from sqlalchemy.orm import Query
import typing

from rolling.exception import ImpossibleAction
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

    def get_base_query(
        self,
        carried_by_id: typing.Optional[str] = None,
        in_built_id: typing.Optional[int] = None,
        shared_with_affinity_ids: typing.Optional[typing.List[int]] = None,
        exclude_shared_with_affinity: bool = False,
        world_row_i: typing.Optional[int] = None,
        world_col_i: typing.Optional[int] = None,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        stuff_id: typing.Optional[str] = None,
        id_: typing.Optional[int] = None,
        exclude_crafting: bool = False,
        exclude_used_as: bool = False,
        only_columns: typing.Optional[typing.List[Column]] = None,
    ) -> Query:
        if world_row_i is not None or world_col_i is not None:
            assert world_row_i is not None and world_col_i is not None
        if zone_row_i is not None or zone_col_i is not None:
            assert zone_row_i is not None and zone_col_i is not None

        if only_columns is not None:
            query = self._kernel.server_db_session.query(*only_columns)
        else:
            query = self._kernel.server_db_session.query(StuffDocument)

        if shared_with_affinity_ids is not None:
            assert not exclude_shared_with_affinity
            query = query.filter(
                StuffDocument.shared_with_affinity_id.in_(shared_with_affinity_ids)
            )

        if exclude_shared_with_affinity:
            query = query.filter(StuffDocument.shared_with_affinity_id == None)

        query = query.filter(
            # Note: When carried_by_id is None, it exclude carried stuff
            StuffDocument.carried_by_id == carried_by_id,
            StuffDocument.in_built_id == in_built_id,
        )

        if exclude_crafting:
            query = query.filter(StuffDocument.under_construction == False)

        if exclude_used_as:
            query = query.filter(
                StuffDocument.used_as_shield_by_id == None,
                StuffDocument.used_as_armor_by_id == None,
                StuffDocument.used_as_weapon_by_id == None,
            )

        if world_row_i is not None and world_col_i is not None:
            query = query.filter(StuffDocument.world_row_i == world_row_i)
            query = query.filter(StuffDocument.world_col_i == world_col_i)

        if zone_row_i is not None and zone_col_i is not None:
            query = query.filter(StuffDocument.zone_row_i == zone_row_i)
            query = query.filter(StuffDocument.zone_col_i == zone_col_i)

        if stuff_id is not None:
            query = query.filter(StuffDocument.stuff_id == stuff_id)

        if id_ is not None:
            query = query.filter(StuffDocument.id == id_)

        return query

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
            filled_with_resource=stuff_generation_properties.meta.get("filled_with_resource")
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
    def create_document_from_properties(
        cls,
        properties: "StuffProperties",
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
            weight=properties.weight,
            clutter=properties.clutter,
            image=properties.image,
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
        stuff_docs = self.get_base_query(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
        ).all()
        return [self.stuff_model_from_doc(doc) for doc in stuff_docs]

    def count_zone_stuffs(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
    ) -> int:
        return self.get_base_query(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
        ).count()

    def get_stuff(self, stuff_id: int) -> StuffModel:
        doc = self.get_stuff_doc(stuff_id)
        return self.stuff_model_from_doc(doc)

    def stuff_model_from_doc(self, doc: StuffDocument) -> StuffModel:
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(doc.stuff_id)
        return StuffModel(
            id=doc.id,
            name=stuff_properties.name,
            is_bag=stuff_properties.is_bag,
            zone_col_i=doc.zone_col_i,
            zone_row_i=doc.zone_row_i,
            filled_at=float(doc.filled_at) if doc.filled_at else None,
            filled_unity=Unit(doc.filled_unity) if doc.filled_unity else None,
            filled_with_resource=doc.filled_with_resource if doc.filled_with_resource else None,
            weight=float(doc.weight) if doc.weight else None,
            clutter=float(doc.clutter) if doc.clutter else None,
            clutter_capacity=float(stuff_properties.clutter_capacity)
            if stuff_properties.is_bag
            else None,
            image=doc.image if doc.image else None,
            carried_by=doc.carried_by_id,
            stuff_id=doc.stuff_id,
            ap_required=float(doc.ap_required),
            ap_spent=float(doc.ap_spent),
            under_construction=doc.under_construction,
            weapon=stuff_properties.weapon,
            armor=stuff_properties.armor,
            shield=stuff_properties.shield,
            estoc=stuff_properties.estoc,
            blunt=stuff_properties.blunt,
            sharp=stuff_properties.sharp,
            protect_estoc=stuff_properties.protect_estoc,
            protect_blunt=stuff_properties.protect_blunt,
            protect_sharp=stuff_properties.protect_sharp,
            classes=stuff_properties.classes,
        )

    def get_carried_by(
        self,
        character_id: str,
        exclude_crafting: bool = True,
        shared_with_affinity_ids: typing.Optional[typing.List[int]] = None,
        exclude_shared_with_affinity: bool = False,
        stuff_id: typing.Optional[str] = None,
    ) -> typing.List[StuffModel]:
        return [
            self.stuff_model_from_doc(doc)
            for doc in self.get_base_query(
                carried_by_id=character_id,
                exclude_crafting=exclude_crafting,
                stuff_id=stuff_id,
                exclude_shared_with_affinity=exclude_shared_with_affinity,
                shared_with_affinity_ids=shared_with_affinity_ids,
            ).all()
        ]

    def get_stuff_doc(self, stuff_id: int) -> StuffDocument:
        return (
            self._kernel.server_db_session.query(StuffDocument)
            .filter(StuffDocument.id == stuff_id)
            .one()
        )

    def set_carried_by(self, stuff_id: int, character_id: str, commit: bool = True) -> None:
        stuff_doc = self.get_stuff_doc(stuff_id)
        self.set_carried_by__from_doc(stuff_doc, character_id=character_id, commit=commit)

    def set_shared_with_affinity(
        self, stuff_id: int, affinity_id: int, commit: bool = True
    ) -> None:
        stuff_doc = self.get_stuff_doc(stuff_id)
        stuff_doc.shared_with_affinity_id = affinity_id
        if commit:
            self._kernel.server_db_session.commit()

    def unshare_with_affinity(self, stuff_id: int, commit: bool = True) -> None:
        stuff_doc = self.get_stuff_doc(stuff_id)
        stuff_doc.shared_with_affinity_id = None
        if commit:
            self._kernel.server_db_session.commit()

    def set_carried_by__from_doc(
        self, stuff_doc: StuffDocument, character_id: str, commit: bool = True
    ) -> None:
        stuff_doc.carried_by_id = character_id
        stuff_doc.used_as_shield_by_id = None
        stuff_doc.used_as_armor_by_id = None
        stuff_doc.used_as_weapon_by_id = None
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
            try:
                action.check_is_possible(character, stuff)
                actions.extend(action.get_character_actions(character, stuff))
            except ImpossibleAction:
                pass

        return actions

    # FIXME: exclude crafting stuff
    def fill_stuff_with_resource(self, stuff: StuffModel, resource_id: str) -> None:
        doc = self.get_stuff_doc(stuff.id)
        doc.fill(self._kernel, resource_id, at=100.0)

        self._kernel.server_db_session.add(doc)
        self._kernel.server_db_session.commit()

    # FIXME: exclude crafting stuff
    def empty_stuff(self, stuff: StuffModel) -> None:
        doc = self.get_stuff_doc(stuff.id)
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff.stuff_id
        )
        doc.empty(stuff_properties)

        self._kernel.server_db_session.add(doc)
        self._kernel.server_db_session.commit()

    def get_carried_and_used_bags(self, character_id: str) -> typing.List[StuffModel]:
        return [
            self.stuff_model_from_doc(doc)
            for doc in self.get_base_query(carried_by_id=character_id)
            .filter(StuffDocument.used_as_bag_by_id == character_id)
            .all()
        ]

    # FIXME: exclude crafting stuff
    def set_as_used_as_bag(self, character_id: str, stuff_id: int, commit: bool = True) -> None:
        stuff_doc: StuffDocument = self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).one()
        stuff_doc.used_as_bag_by_id = character_id
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    # FIXME: exclude crafting stuff
    def set_as_used_as_weapon(self, character_id: str, stuff_id: int, commit: bool = True) -> None:
        # FIXME BS NOW: replace query by shared query (ready stuff)
        stuff_doc: StuffDocument = self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).one()
        stuff_doc.used_as_weapon_by_id = character_id
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    # FIXME: exclude crafting stuff
    def set_as_used_as_armor(self, character_id: str, stuff_id: int, commit: bool = True) -> None:
        # FIXME BS NOW: replace query by shared query (ready stuff)
        stuff_doc: StuffDocument = self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).one()
        stuff_doc.used_as_armor_by_id = character_id
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    # FIXME: exclude crafting stuff
    def set_as_used_as_shield(self, character_id: str, stuff_id: int, commit: bool = True) -> None:
        # FIXME BS NOW: replace query by shared query (ready stuff)
        stuff_doc: StuffDocument = self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).one()
        stuff_doc.used_as_shield_by_id = character_id
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def unset_as_used_as_bag(self, character_id: str, stuff_id: int, commit: bool = True) -> None:
        stuff_doc: StuffDocument = self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).one()
        stuff_doc.used_as_bag_by_id = None
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def unset_as_used_as_weapon(
        self, character_id: str, stuff_id: int, commit: bool = True
    ) -> None:
        stuff_doc: StuffDocument = self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).one()
        stuff_doc.used_as_weapon_by_id = None
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def unset_as_used_as_shield(
        self, character_id: str, stuff_id: int, commit: bool = True
    ) -> None:
        stuff_doc: StuffDocument = self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).one()
        stuff_doc.used_as_shield_by_id = None
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def unset_as_used_as_armor(self, character_id: str, stuff_id: int, commit: bool = True) -> None:
        stuff_doc: StuffDocument = self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).one()
        stuff_doc.used_as_armor_by_id = None
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def drop(
        self,
        stuff_id: int,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        commit: bool = True,
    ) -> None:
        stuff_doc = self.get_stuff_doc(stuff_id)
        stuff_doc.carried_by_id = None
        self.un_use_stuff_doc(stuff_doc)
        stuff_doc.world_row_i = world_row_i
        stuff_doc.world_col_i = world_col_i
        stuff_doc.zone_row_i = zone_row_i
        stuff_doc.zone_col_i = zone_col_i
        self._kernel.server_db_session.add(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def un_use_stuff_doc(self, doc: StuffDocument) -> None:
        doc.used_as_armor_by_id = None
        doc.used_as_bag_by_id = None
        doc.used_as_shield_by_id = None
        doc.used_as_weapon_by_id = None

    def un_use_stuff(self, stuff_id: int, commit: bool = True) -> None:
        self._kernel.server_db_session.query(StuffDocument).filter(
            StuffDocument.id == stuff_id
        ).update(
            {
                "used_as_armor_by_id": None,
                "used_as_bag_by_id": None,
                "used_as_shield_by_id": None,
                "used_as_weapon_by_id": None,
            }
        )
        if commit:
            self._kernel.server_db_session.commit()

    def destroy(self, stuff_id: int, commit: bool = True) -> None:
        stuff_doc = self.get_stuff_doc(stuff_id)
        self._kernel.server_db_session.delete(stuff_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def get_stuff_count(
        self,
        character_id: str,
        stuff_id: str,
        exclude_crafting: bool = True,
        shared_with_affinity_ids: typing.Optional[typing.List[int]] = None,
        exclude_shared_with_affinity: bool = False,
    ) -> int:
        return self.get_base_query(
            carried_by_id=character_id,
            stuff_id=stuff_id,
            exclude_crafting=exclude_crafting,
            exclude_shared_with_affinity=exclude_shared_with_affinity,
            shared_with_affinity_ids=shared_with_affinity_ids,
        ).count()

    def get_first_carried_stuff(
        self,
        character_id: str,
        stuff_id: str,
        exclude_crafting: bool = True,
        exclude_used_as: bool = True,
    ) -> StuffModel:
        query = self.get_base_query(
            carried_by_id=character_id,
            stuff_id=stuff_id,
            exclude_crafting=exclude_crafting,
            exclude_used_as=exclude_used_as,
        )
        return self.stuff_model_from_doc(query.limit(1).one())

    def get_shared_with_affinity(
        self, character_id: str, affinity_id: int
    ) -> typing.List[StuffModel]:
        return [
            self.stuff_model_from_doc(doc)
            for doc in self.get_base_query(
                carried_by_id=character_id, shared_with_affinity_ids=[affinity_id]
            ).all()
        ]
