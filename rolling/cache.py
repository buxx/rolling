import typing

from rolling.protectorate import ProtectorateState


if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.resource import CarriedResourceDescriptionModel
    from rolling.model.stuff import StuffModel
    from rolling.server.document.resource import ResourceDocument
    from rolling.server.document.build import BuildDocument
    from rolling.types import CharacterId, WorldPoint
    from rolling.types import ResourceId


class RequestCache:
    """A cache to use on one request for one zone"""

    def __init__(
        self,
        kernel: "Kernel",
        world_point: "WorldPoint",
    ) -> None:
        self._kernel = kernel
        self._ground_resources: typing.Optional[
            typing.List["CarriedResourceDescriptionModel"]
        ] = None
        self._ground_stuffs: typing.Optional[typing.List["StuffModel"]] = None
        self._builds: typing.Optional[typing.List["BuildDocument"]] = None
        self._world_point = world_point
        self._protectorat_state: typing.Optional[ProtectorateState] = None
        self._carried_resources: typing.Dict[
            "CharacterId", typing.List["ResourceDocument"]
        ] = {}
        self._carried_stuffs: typing.Dict["CharacterId", typing.List["StuffModel"]] = {}

    def get_carried_resources(
        self,
        character_id: "CharacterId",
        resource_id: typing.Optional["ResourceId"] = None,
    ) -> typing.List["ResourceDocument"]:
        if character_id not in self._carried_resources:
            self._carried_resources[
                character_id
            ] = self._kernel.resource_lib.get_carried_by_docs(character_id)

        if resource_id is not None:
            return [
                r
                for r in self._carried_resources[character_id]
                if r.resource_id == resource_id
            ]

        return self._carried_resources[character_id]

    def get_carried_stuffs(
        self, character_id: "CharacterId"
    ) -> typing.List["ResourceDocument"]:
        if character_id in self._carried_stuffs:
            return self._carried_stuffs[character_id]

        self._carried_stuffs[character_id] = self._kernel.stuff_lib.get_carried_by(
            character_id
        )
        return self._carried_stuffs[character_id]

    def get_ground_resources(
        self,
        resource_id: typing.Optional["ResourceId"] = None,
    ) -> typing.List["ResourceDocument"]:
        if self._ground_resources is None:
            self._ground_resources = self._kernel.resource_lib.get_ground_resource_docs(
                world_row_i=self._world_point[0],
                world_col_i=self._world_point[1],
            )

        if resource_id is not None:
            return [r for r in self._ground_resources if r.resource_id == resource_id]

        return self._ground_resources

    def get_ground_stuffs(
        self,
    ) -> typing.List["StuffModel"]:
        if self._ground_stuffs is None:
            self._ground_stuffs = self._kernel.stuff_lib.get_zone_stuffs(
                world_row_i=self._world_point[0],
                world_col_i=self._world_point[1],
            )

        return self._ground_stuffs

    def get_builds(
        self,
    ) -> typing.List["StuffModel"]:
        if self._builds is None:
            self._builds = self._kernel.build_lib.get_zone_build(
                world_row_i=self._world_point[0],
                world_col_i=self._world_point[1],
            )

        return self._builds

    def protectorat_state(self) -> ProtectorateState:
        if self._protectorat_state is not None:
            return self._protectorat_state

        self._protectorat_state = self._kernel.protectorate_lib.state(self._world_point)
        return self._protectorat_state
