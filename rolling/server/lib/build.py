# coding: utf-8
from sqlalchemy import and_
from sqlalchemy.orm import Query
import typing

from rolling.exception import ImpossibleAction
from rolling.model.character import CharacterModel
from rolling.server.document.build import BuildDocument
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class BuildLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def place_build(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        build_id: str,
        under_construction: bool = True,
        commit: bool = True,
    ) -> BuildDocument:
        build_description = self._kernel.game.config.builds[build_id]

        # If place a floor, replace if one exist
        if build_description.is_floor:
            try:
                existing_floor = self.get_zone_build(
                    world_row_i=world_row_i,
                    world_col_i=world_col_i,
                    zone_row_i=zone_row_i,
                    zone_col_i=zone_col_i,
                    is_floor=True,
                )[0]
                self._kernel.server_db_session.delete(existing_floor)
            except IndexError:
                pass

        build_doc = BuildDocument(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            build_id=build_id,
            under_construction=under_construction,
            is_on=False,
            is_floor=build_description.is_floor,
            is_door=build_description.is_door,
        )
        self._kernel.server_db_session.add(build_doc)

        if commit:
            self._kernel.server_db_session.commit()

        return build_doc

    def get_build_doc(self, build_id: int) -> BuildDocument:
        return (
            self._kernel.server_db_session.query(BuildDocument)
            .filter(BuildDocument.id == build_id)
            .one()
        )

    def get_on_build_actions(
        self, character: CharacterModel, build_id: int
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]

        for action in self._kernel.action_factory.get_all_with_build_actions():
            try:
                action.check_is_possible(character, build_id=build_id)
                actions.extend(action.get_character_actions(character, build_id=build_id))
            except ImpossibleAction:
                pass

        if build_description.is_door and not build_doc.under_construction:
            actions.append(
                CharacterActionLink(
                    name=f"Gestion de cette porte",
                    link=f"/character/{character.id}/door/{build_id}",
                )
            )

        return actions

    def get_zone_build(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        is_floor: typing.Optional[bool] = None,
        is_door: typing.Optional[bool] = None,
    ) -> typing.List[BuildDocument]:
        return self._get_zone_query(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            is_floor=is_floor,
            is_door=is_door,
        ).all()

    def _get_zone_query(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        is_floor: typing.Optional[bool] = None,
        is_door: typing.Optional[bool] = None,
    ) -> Query:
        filters = [
            BuildDocument.world_row_i == world_row_i,
            BuildDocument.world_col_i == world_col_i,
        ]

        if zone_row_i is not None and zone_col_i is not None:
            filters.extend(
                [BuildDocument.zone_row_i == zone_row_i, BuildDocument.zone_col_i == zone_col_i]
            )

        if is_floor is not None:
            filters.append(BuildDocument.is_floor == is_floor)

        if is_door is not None:
            filters.append(BuildDocument.is_door == is_door)

        return self._kernel.server_db_session.query(BuildDocument).filter(and_(*filters)).order_by(BuildDocument.is_floor.desc())

    def count_zone_build(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        is_floor: typing.Optional[bool] = None,
    ) -> int:
        return self._get_zone_query(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            is_floor=is_floor,
        ).count()

    def progress_build(
        self,
        build_id: int,
        real_progress_cost: float,
        consume_resources_percent: float,
        commit: bool = True,
    ) -> None:
        build_doc = self.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]

        for required_resource in build_description.build_require_resources:
            quantity_to_reduce = required_resource.quantity * (consume_resources_percent / 100)
            self._kernel.resource_lib.reduce_stored_in(
                build_id,
                resource_id=required_resource.resource_id,
                quantity=quantity_to_reduce,
                commit=False,
            )

        build_doc.ap_spent = float(build_doc.ap_spent) + real_progress_cost

        if build_doc.ap_spent >= build_description.cost:
            build_doc.under_construction = False
            if build_description.default_is_on:
                build_doc.is_on = True

        self._kernel.server_db_session.add(build_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def get_all(self, is_on: typing.Optional[bool]) -> typing.List[BuildDocument]:
        query = self._kernel.server_db_session.query(BuildDocument)

        if is_on is not None:
            query = query.filter(BuildDocument.is_on == is_on)

        return query.all()

    def is_there_build_here(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        is_floor: typing.Optional[bool] = None,
    ) -> bool:
        return bool(
            self.count_zone_build(
                world_row_i=world_row_i,
                world_col_i=world_col_i,
                zone_row_i=zone_row_i,
                zone_col_i=zone_col_i,
                is_floor=is_floor,
            )
        )
