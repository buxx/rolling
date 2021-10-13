# coding: utf-8
from sqlalchemy import Column
from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.elements import and_
from sqlalchemy.sql.elements import or_
import typing

from rolling.exception import ImpossibleAction
from rolling.exception import NoCarriedResource
from rolling.exception import NotEnoughResource
from rolling.log import server_logger
from rolling.model.character import CharacterModel
from rolling.model.measure import Unit
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.resource import ResourceDescriptionModel
from rolling.server.action import ActionFactory
from rolling.server.document.resource import ResourceDocument
from rolling.server.link import CharacterActionLink
from rolling.server.util import get_round_resource_quantity

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class ResourceLib:
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
        resource_id: typing.Optional[str] = None,
        only_columns: typing.Optional[typing.List[Column]] = None,
    ) -> Query:
        if world_row_i is not None or world_col_i is not None:
            assert world_row_i is not None and world_col_i is not None
        if zone_row_i is not None or zone_col_i is not None:
            assert zone_row_i is not None and zone_col_i is not None

        if only_columns is not None:
            query = self._kernel.server_db_session.query(*only_columns)
        else:
            query = self._kernel.server_db_session.query(ResourceDocument)

        if shared_with_affinity_ids is not None:
            assert not exclude_shared_with_affinity
            query = query.filter(
                ResourceDocument.shared_with_affinity_id.in_(shared_with_affinity_ids)
            )

        if exclude_shared_with_affinity:
            query = query.filter(ResourceDocument.shared_with_affinity_id == None)

        # NOTE: it is important to let == None for carried_by_id and in_built_id
        # because query without them indicate ground resources
        query = query.filter(
            ResourceDocument.carried_by_id == carried_by_id,
            ResourceDocument.in_built_id == in_built_id,
        )

        if world_row_i is not None and world_col_i is not None:
            query = query.filter(ResourceDocument.world_row_i == world_row_i)
            query = query.filter(ResourceDocument.world_col_i == world_col_i)

        if zone_row_i is not None and zone_col_i is not None:
            query = query.filter(ResourceDocument.zone_row_i == zone_row_i)
            query = query.filter(ResourceDocument.zone_col_i == zone_col_i)

        if resource_id is not None:
            query = query.filter(ResourceDocument.resource_id == resource_id)

        return query

    def add_resource_to(
        self,
        resource_id: str,
        quantity: float,
        character_id: typing.Optional[str] = None,
        build_id: typing.Optional[int] = None,
        ground: bool = False,
        world_row_i: typing.Optional[int] = None,
        world_col_i: typing.Optional[int] = None,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        shared_with_affinity_id: typing.Optional[int] = None,
        exclude_shared_with_affinity: bool = False,
        commit: bool = True,
    ) -> None:
        server_logger.debug(
            f"add_resource_to ("
            f"resource_id:{resource_id} "
            f"quantity:{quantity} "
            f"character_id:{character_id} "
            f"build_id:{build_id} "
            f"ground:{ground} "
            f"world_row_i:{world_row_i} "
            f"world_col_i:{world_col_i} "
            f"zone_row_i:{zone_row_i} "
            f"zone_col_i:{zone_col_i} "
            f"shared_with_affinity_id:{shared_with_affinity_id} "
            f"exclude_shared_with_affinity:{exclude_shared_with_affinity} "
            f")"
        )

        assert character_id or build_id or ground
        assert (
            world_row_i is not None
            and world_col_i is not None
            and zone_row_i is not None
            and zone_col_i is not None
            if ground
            else True
        )

        resource_description: ResourceDescriptionModel = (
            self._kernel.game.config.resources[resource_id]
        )
        if character_id:
            filters = [
                ResourceDocument.carried_by_id == character_id,
                ResourceDocument.resource_id == resource_id,
            ]
        elif build_id:
            filters = [
                ResourceDocument.in_built_id == build_id,
                ResourceDocument.resource_id == resource_id,
            ]
        elif ground:
            filters = [
                ResourceDocument.carried_by_id == None,
                ResourceDocument.in_built_id == None,
                ResourceDocument.resource_id == resource_id,
                ResourceDocument.world_row_i == world_row_i,
                ResourceDocument.world_col_i == world_col_i,
                ResourceDocument.zone_row_i == zone_row_i,
                ResourceDocument.zone_col_i == zone_col_i,
            ]
        else:
            raise NotImplementedError()

        if ground and resource_description.drop_to_nowhere:
            return

        if exclude_shared_with_affinity:
            assert shared_with_affinity_id is None
            filters.append(ResourceDocument.shared_with_affinity_id == None)

        if shared_with_affinity_id is not None:
            filters.append(
                ResourceDocument.shared_with_affinity_id == shared_with_affinity_id
            )

        try:
            resource = (
                self._kernel.server_db_session.query(ResourceDocument)
                .filter(*filters)
                .one()
            )
        except NoResultFound:
            resource = ResourceDocument(
                resource_id=resource_id,
                carried_by_id=character_id if not ground else None,
                in_built_id=build_id if not ground else None,
                quantity=0.0,
                unit=resource_description.unit.value,
                world_row_i=world_row_i,
                world_col_i=world_col_i,
                zone_row_i=zone_row_i,
                zone_col_i=zone_col_i,
                shared_with_affinity_id=shared_with_affinity_id,
            )

        resource.quantity = float(resource.quantity) + quantity
        self._kernel.server_db_session.add(resource)

        if commit:
            self._kernel.server_db_session.commit()

    def get_carried_by(
        self,
        character_id: str,
        exclude_shared_with_affinity: bool = False,
        shared_with_affinity_ids: typing.Optional[typing.List[int]] = None,
    ) -> typing.List[CarriedResourceDescriptionModel]:
        resource_docs: typing.List[ResourceDocument] = self.get_base_query(
            carried_by_id=character_id,
            exclude_shared_with_affinity=exclude_shared_with_affinity,
            shared_with_affinity_ids=shared_with_affinity_ids,
        ).all()

        resource_docs_by_resource_id = {}
        for resource_doc in resource_docs:
            resource_docs_by_resource_id.setdefault(
                resource_doc.resource_id, []
            ).append(resource_doc)

        carried_models = []
        for resource_docs_ in resource_docs_by_resource_id.values():
            carried_models.append(self._carried_resource_model_from_doc(resource_docs_))
        return carried_models

    def get_ground_resource(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
    ) -> typing.List[CarriedResourceDescriptionModel]:
        carried = self.get_base_query(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
        ).all()
        return [self._carried_resource_model_from_doc([doc]) for doc in carried]

    def count_ground_resource(
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

    def get_one_carried_by(
        self,
        character_id: str,
        resource_id: str,
        shared_with_affinity_ids: typing.Optional[typing.List[int]] = None,
        exclude_shared_with_affinity: bool = False,
        empty_object_if_not: bool = False,
    ) -> CarriedResourceDescriptionModel:
        docs = self.get_base_query(
            carried_by_id=character_id,
            resource_id=resource_id,
            exclude_shared_with_affinity=exclude_shared_with_affinity,
            shared_with_affinity_ids=shared_with_affinity_ids,
        ).all()
        try:
            return self._carried_resource_model_from_doc(docs)
        except NoCarriedResource:
            if not empty_object_if_not:
                raise

            resource_description = self._kernel.game.config.resources[resource_id]
            return CarriedResourceDescriptionModel(
                id=resource_id,
                name=resource_description.name,
                weight=0.0,
                material_type=resource_description.material_type,
                unit=resource_description.unit,
                clutter=0.0,
                quantity=0.0,
                descriptions=resource_description.descriptions,
                illustration=resource_description.illustration,
                grow_speed=resource_description.grow_speed,
                drop_to_nowhere=resource_description.drop_to_nowhere,
            )

    def _carried_resource_model_from_doc(
        self,
        docs: typing.List[ResourceDocument],
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
    ) -> CarriedResourceDescriptionModel:
        if not docs:
            raise NoCarriedResource()

        resource_description = self._kernel.game.config.resources[docs[0].resource_id]
        quantity = sum([float(doc.quantity) for doc in docs])
        clutter = quantity * resource_description.clutter

        if resource_description.unit in (Unit.UNIT, Unit.CUBIC, Unit.LITTER):
            weight = quantity * resource_description.weight
        elif resource_description.unit in (Unit.GRAM,):
            weight = quantity
        else:
            raise NotImplementedError()

        return CarriedResourceDescriptionModel(
            id=docs[0].resource_id,
            name=resource_description.name,
            weight=weight,
            material_type=resource_description.material_type,
            unit=resource_description.unit,
            clutter=clutter,
            quantity=quantity,
            descriptions=resource_description.descriptions,
            ground_row_i=docs[0].zone_row_i,
            ground_col_i=docs[0].zone_col_i,
            illustration=resource_description.illustration,
            grow_speed=resource_description.grow_speed,
            drop_to_nowhere=resource_description.drop_to_nowhere,
        )

    def have_resource(
        self,
        resource_id: str,
        character_id: typing.Optional[str] = None,
        build_id: typing.Optional[int] = None,
        quantity: typing.Optional[float] = None,
        exclude_shared_with_affinity: bool = False,
        shared_with_affinity_ids: typing.Optional[typing.List[int]] = None,
    ) -> bool:
        assert character_id is not None or build_id is not None
        resource_docs = self.get_base_query(
            carried_by_id=character_id,
            in_built_id=build_id,
            resource_id=resource_id,
            exclude_shared_with_affinity=exclude_shared_with_affinity,
            shared_with_affinity_ids=shared_with_affinity_ids,
        ).all()

        if not resource_docs:
            return False

        if quantity is not None:
            total_quantity = sum(float(d.quantity) for d in resource_docs)
            return total_quantity >= quantity

        return True

    def reduce_carried_by(
        self,
        character_id: str,
        resource_id: str,
        quantity: float,
        exclude_shared_with_affinity: bool = False,
        shared_with_affinity_ids: typing.Optional[typing.List[int]] = None,
        commit: bool = True,
        force_before_raise: bool = False,
    ) -> None:
        server_logger.debug(
            f"reduce_carried_by ("
            f"character_id:{character_id} "
            f"resource_id:{resource_id} "
            f"quantity:{quantity} "
            f"exclude_shared_with_affinity:{exclude_shared_with_affinity} "
            f"shared_with_affinity_ids:{shared_with_affinity_ids} "
            f")"
        )

        if exclude_shared_with_affinity:
            assert shared_with_affinity_ids is None

        filters = [
            ResourceDocument.carried_by_id == character_id,
            ResourceDocument.resource_id == resource_id,
        ]

        if exclude_shared_with_affinity:
            filters.append(ResourceDocument.shared_with_affinity_id == None)

        if shared_with_affinity_ids:
            filters.append(
                ResourceDocument.shared_with_affinity_id.in_(shared_with_affinity_ids)
            )

        self._reduce(
            resource_id,
            and_(*filters),
            quantity=quantity,
            commit=commit,
            force_before_raise=force_before_raise,
        )

        carried = self._kernel.resource_lib.get_one_carried_by(
            character_id=character_id,
            resource_id=resource_id,
            empty_object_if_not=True,
        )
        if not carried.quantity:
            resource_docs = (
                self._kernel.server_db_session.query(ResourceDocument)
                .filter(and_(*filters))
                .all()
            )
            for resource_doc in resource_docs:
                self._kernel.server_db_session.delete(resource_doc)
        if commit:
            self._kernel.server_db_session.commit()

    def reduce_on_ground(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        resource_id: str,
        quantity: float,
        commit: bool = True,
    ) -> None:
        filter_ = and_(
            ResourceDocument.carried_by_id == None,
            ResourceDocument.in_built_id == None,
            ResourceDocument.carried_by_id == None,
            ResourceDocument.resource_id == resource_id,
            ResourceDocument.world_row_i == world_row_i,
            ResourceDocument.world_col_i == world_col_i,
            ResourceDocument.zone_row_i == zone_row_i,
            ResourceDocument.zone_col_i == zone_col_i,
        )
        self._reduce(resource_id, filter_, quantity=quantity, commit=commit)

    def reduce_stored_in(
        self, build_id: int, resource_id: str, quantity: float, commit: bool = True
    ) -> None:
        filter_ = and_(
            ResourceDocument.in_built_id == build_id,
            ResourceDocument.resource_id == resource_id,
        )
        self._reduce(resource_id, filter_, quantity=quantity, commit=commit)

    def reduce(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_coordinates: typing.List[typing.Tuple[int, int]],
        resource_id: str,
        quantity: float,
        commit: bool = True,
        force_before_raise: bool = False,
    ) -> float:
        zone_coordinates_filters = [
            and_(
                ResourceDocument.zone_row_i == zone_row_i,
                ResourceDocument.zone_col_i == zone_col_i,
            )
            for zone_row_i, zone_col_i in zone_coordinates
        ]
        filter_ = and_(
            ResourceDocument.resource_id == resource_id,
            ResourceDocument.world_row_i == world_row_i,
            ResourceDocument.world_col_i == world_col_i,
            or_(*zone_coordinates_filters),
        )
        return self._reduce(
            resource_id,
            filter_,
            quantity=quantity,
            commit=commit,
            force_before_raise=force_before_raise,
        )

    def _reduce(
        self,
        resource_id: str,
        filter_,
        quantity: float,
        commit: bool = True,
        force_before_raise: bool = False,
    ) -> float:
        resource_docs = (
            self._kernel.server_db_session.query(ResourceDocument).filter(filter_).all()
        )

        if not resource_docs:
            raise NoCarriedResource()

        raise_not_enough = False
        total_quantity = sum([float(d.quantity) for d in resource_docs])
        # test if float is equal ... to prevent float round errors
        total_quantity_str = get_round_resource_quantity(total_quantity)
        quantity_str = get_round_resource_quantity(quantity)
        if total_quantity < quantity and total_quantity_str != quantity_str:
            raise_exception = NotEnoughResource(
                resource_id=resource_id,
                required_quantity=quantity,
                available_quantity=total_quantity,
            )
            if force_before_raise:
                raise_not_enough = True
            else:
                raise raise_exception

        to_reduce = quantity
        reduced_quantity = 0.0

        for resource_doc in resource_docs:
            if to_reduce <= 0:
                break

            if float(resource_doc.quantity) < to_reduce:
                to_reduce -= float(resource_doc.quantity)
                reduced_quantity += float(resource_doc.quantity)
                self._kernel.server_db_session.delete(resource_doc)
            elif float(resource_doc.quantity) == to_reduce:
                reduced_quantity += to_reduce
                to_reduce = 0.0
                self._kernel.server_db_session.delete(resource_doc)
            else:
                resource_doc.quantity = float(resource_doc.quantity) - to_reduce
                reduced_quantity += to_reduce
                self._kernel.server_db_session.add(resource_doc)

        if commit:
            self._kernel.server_db_session.commit()

        if raise_not_enough:
            raise raise_exception

        return reduced_quantity

    def drop(
        self,
        character_id: str,
        resource_id: str,
        quantity: float,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        commit: bool = True,
    ) -> None:
        server_logger.debug(
            f"drop resource ("
            f"character_id:{character_id} "
            f"resource_id:{resource_id} "
            f"quantity:{quantity} "
            f"world_row_i:{world_row_i} "
            f"world_col_i:{world_col_i} "
            f"zone_row_i:{zone_row_i} "
            f"zone_col_i:{zone_col_i} "
            f")"
        )
        self.reduce_carried_by(character_id, resource_id, quantity, commit=commit)
        self.add_resource_to(
            ground=True,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            commit=commit,
            quantity=quantity,
            resource_id=resource_id,
        )

    def get_carrying_actions(
        self,
        character: CharacterModel,
        resource_id: str,
        for_actions_page: bool = False,
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []
        resource_description = self._kernel.game.config.resources[resource_id]

        for description in resource_description.descriptions:
            action = self._action_factory.get_with_resource_action(description)
            if for_actions_page and action.exclude_from_actions_page:
                continue

            try:
                action.check_is_possible(character, resource_id=resource_id)
                actions.extend(action.get_character_actions(character, resource_id))
            except ImpossibleAction:
                pass

        return actions

    def get_stored_in_build(
        self, build_id: int
    ) -> typing.List[CarriedResourceDescriptionModel]:
        carried = self.get_base_query(in_built_id=build_id).all()
        return [self._carried_resource_model_from_doc([doc]) for doc in carried]

    def get_one_stored_in_build(
        self, build_id: int, resource_id: str
    ) -> CarriedResourceDescriptionModel:
        carried = self.get_base_query(
            in_built_id=build_id, resource_id=resource_id
        ).one()
        return self._carried_resource_model_from_doc([carried])

    def get_shared_with_affinity(
        self, character_id: str, affinity_id: int
    ) -> typing.List[CarriedResourceDescriptionModel]:
        return [
            self._carried_resource_model_from_doc([doc])
            for doc in self.get_base_query(
                carried_by_id=character_id, shared_with_affinity_ids=[affinity_id]
            ).all()
        ]

    def get_one_stored_in_build(
        self,
        build_id: int,
        resource_id: str,
        quantity: typing.Optional[float] = None,
    ) -> CarriedResourceDescriptionModel:
        query = self.get_base_query(in_built_id=build_id, resource_id=resource_id)

        if quantity is not None:
            query = query.filter(ResourceDocument.quantity >= quantity)

        return self._carried_resource_model_from_doc([query.one()])
