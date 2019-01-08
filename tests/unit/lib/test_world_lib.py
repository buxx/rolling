# coding: utf-8
import pytest

from rolling.kernel import Kernel
from rolling.server.lib.world import WorldLib


@pytest.fixture
def tile_lib(worldmapa_kernel: Kernel) -> WorldLib:
    return WorldLib(worldmapa_kernel)


class TestWorldLib(object):
    def test_unit__get_legend__ok(self, tile_lib: WorldLib):
        # Just test no error raised
        tile_lib.get_legend()
