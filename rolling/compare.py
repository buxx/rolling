import collections
import typing
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class GroundResourceCompare:
    def __init__(
        self,
        kernel: "Kernel",
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
    ) -> None:
        self._kernel = kernel
        self._world_row_i = world_row_i
        self._world_col_i = world_col_i
        self._zone_row_i = zone_row_i
        self._zone_col_i = zone_col_i
        self._snapshot_resources: typing.DefaultDict[
            typing.Tuple[int, int], typing.List[str]
        ] = collections.defaultdict(list)

    def _get_now_resources(
        self,
    ) -> typing.Generator[typing.Tuple[typing.Tuple[int, int], str], None, None]:
        around_character = get_on_and_around_coordinates(
            x=self._zone_row_i, y=self._zone_col_i
        )
        for around_row_i, around_col_i in around_character:
            for resource_on_ground in self._kernel.resource_lib.get_ground_resource(
                world_row_i=self._world_row_i,
                world_col_i=self._world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            ):
                yield (around_row_i, around_col_i), resource_on_ground.id

    def snapshot(self) -> "GroundResourceCompare":
        self._snapshot_resources.clear()

        for (row_i, col_i), resource_id in self._get_now_resources():
            self._snapshot_resources[(row_i, col_i)].append(resource_id)

        return self

    def get_new(self) -> typing.Dict[typing.Tuple[int, int], typing.List[str]]:
        new_resources: typing.DefaultDict[
            typing.Tuple[int, int], typing.List[str]
        ] = collections.defaultdict(list)

        for (row_i, col_i), resource_id in self._get_now_resources():
            if resource_id not in self._snapshot_resources[(row_i, col_i)]:
                new_resources[(row_i, col_i)].append(resource_id)

        return new_resources

    def get_missing(self) -> typing.Dict[typing.Tuple[int, int], typing.List[str]]:
        missing_resources: typing.DefaultDict[
            typing.Tuple[int, int], typing.List[str]
        ] = collections.defaultdict(list)

        now_resources: typing.DefaultDict[
            typing.Tuple[int, int], typing.List[str]
        ] = collections.defaultdict(list)
        for (row_i, col_i), resource_id in self._get_now_resources():
            now_resources[(row_i, col_i)].append(resource_id)

        for (row_i, col_i), resource_ids in self._snapshot_resources.items():
            for resource_id in resource_ids:
                if resource_id not in now_resources[(row_i, col_i)]:
                    missing_resources[(row_i, col_i)].append(resource_id)

        return missing_resources
