import typing

import pytest

from rolling.kernel import Kernel
from rolling.server.document.build import BuildDocument


class TestFarmingLib:
    def test_build_is_not_seeded(self, worldmapc_kernel: Kernel) -> None:
        assert not worldmapc_kernel.farming_lib.is_seeded(BuildDocument())

    def test_build_is_seeded(self, worldmapc_kernel: Kernel) -> None:
        assert worldmapc_kernel.farming_lib.is_seeded(BuildDocument(seeded_with="toto"))

    def test_seed(self, worldmapc_kernel: Kernel) -> None:
        # Given
        doc = BuildDocument()

        # When
        worldmapc_kernel.farming_lib.seed(doc, resource_id="toto", commit=False)

        # Then
        assert doc.seeded_with == "toto"
        assert doc.grow_progress == 0

    @pytest.mark.parametrize(
        "grow_progress,expected_classes",
        [
            (0, ["GROW_PROGRESS_0", "GROW_PROGRESS_toto_0"]),
            (10_000, ["GROW_PROGRESS_1", "GROW_PROGRESS_toto_1"]),
            (20_000, ["GROW_PROGRESS_2", "GROW_PROGRESS_toto_2"]),
            (40_000, ["GROW_PROGRESS_3", "GROW_PROGRESS_toto_3"]),
            (60_000, ["GROW_PROGRESS_4", "GROW_PROGRESS_toto_4"]),
            (999_000, ["GROW_PROGRESS_4", "GROW_PROGRESS_toto_4"]),
        ]
    )
    def test_get_growing_state_classes(
        self, worldmapc_kernel: Kernel, grow_progress: int, expected_classes: typing.List[str]
    ) -> None:
        # Given
        doc = BuildDocument(seeded_with="toto", grow_progress=grow_progress)

        # When Then
        classes = worldmapc_kernel.farming_lib.get_growing_state_classes(doc)
        for expected_class in expected_classes:
            assert expected_class in classes
