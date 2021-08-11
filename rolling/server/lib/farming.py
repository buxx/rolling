import typing

from rolling.server.document.build import BuildDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class FarmingLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def is_seeded(self, build: BuildDocument) -> None:
        return build.seeded_with is not None

    def seed(self, build: BuildDocument, resource_id: str, commit: bool = True) -> None:
        build.seeded_with = resource_id
        build.grow_progress = 0
        self._kernel.server_db_session.add(build)
        if commit:
            self._kernel.server_db_session.commit()

    def get_growing_state_classes(self, build: BuildDocument) -> typing.List[str]:
        if not build.seeded_with:
            return []

        resource_id = build.seeded_with
        grow_state = 0
        if build.grow_progress >= self._kernel.game.config.grow_progress_1:
            grow_state = 1
        if build.grow_progress >= self._kernel.game.config.grow_progress_2:
            grow_state = 2
        if build.grow_progress >= self._kernel.game.config.grow_progress_3:
            grow_state = 3
        if build.grow_progress >= self._kernel.game.config.grow_progress_4:
            grow_state = 4

        return [
            "PLOUGHED_LAND",
            f"GROW_PROGRESS_{grow_state}",
            f"GROW_PROGRESS_{resource_id}_{grow_state}",
        ]
