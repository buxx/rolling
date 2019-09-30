# coding: utf-8
import typing

from rolling.model.character import CharacterModel
from rolling.server.document.build import BuildDocument
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class BuildLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def place_start_build(
        self,
        world_col_i: int,
        world_row_i: int,
        zone_col_i: int,
        zone_row_i: int,
        build_id: str,
        commit: bool = True,
    ) -> None:
        build_doc = BuildDocument(
            world_row_i=world_col_i,
            world_col_i=world_row_i,
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

        if build_doc.under_construction:
            bring_resources_action_description = self._kernel.game.config.actions[
                ActionType.BRING_RESOURCE_ON_BUILD
            ][0]
            bring_resources_action = self._kernel.action_factory.get_with_build_action(
                bring_resources_action_description
            )
            actions.extend(bring_resources_action.get_character_actions(character, build_id=build_id))

        return actions
