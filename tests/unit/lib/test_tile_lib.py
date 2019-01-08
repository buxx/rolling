# coding: utf-8
import pytest

from rolling.kernel import Kernel
from rolling.server.lib.zone import ZoneLib


@pytest.fixture
def tile_lib(worldmapa_kernel: Kernel) -> ZoneLib:
    return ZoneLib(worldmapa_kernel)


class TestTileLib(object):
    def test_unit__get_all_tiles__ok(self, tile_lib: ZoneLib):
        # Just test no error raised
        tile_lib.get_all_tiles()
