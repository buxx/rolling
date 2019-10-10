# coding: utf-8
import typing

from sqlalchemy import and_

from rolling.model.character import CharacterModel
from rolling.server.document.build import BuildDocument
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class BuildLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def place_start_build(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        build_id: str,
        commit: bool = True,
    ) -> BuildDocument:
        build_doc = BuildDocument(
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            build_id=build_id,
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
        build_doc = self.get_build_doc(build_id)
        actions: typing.List[CharacterActionLink] = []

        for action in self._kernel.action_factory.get_all_with_build_actions():
            actions.extend(action.get_character_actions(character, build_id=build_id))

        return actions

    def get_zone_build(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
    ) -> typing.List[BuildDocument]:
        filters = [
            BuildDocument.world_row_i == world_row_i,
            BuildDocument.world_col_i == world_col_i,
        ]

        if zone_row_i is not None and zone_col_i is not None:
            filters.extend(
                [BuildDocument.zone_row_i == zone_row_i, BuildDocument.zone_col_i == zone_col_i]
            )

        return self._kernel.server_db_session.query(BuildDocument).filter(and_(*filters)).all()

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

        self._kernel.server_db_session.add(build_doc)

        if commit:
            self._kernel.server_db_session.commit()
