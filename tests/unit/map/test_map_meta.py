from rolling.map.meta import WorldMapSpawn
from rolling.kernel import Kernel


class TestMapMeta:
    def test_spawn_create_from_raw_line(
        self,
        worldmapc_kernel: Kernel,
    ):
        kernel = worldmapc_kernel
        spawn = WorldMapSpawn.create_from_raw_line(
            kernel, raw_spawn_line="SPAWN:POSITION:10.5,42.72"
        )
        assert spawn.get_spawn_coordinates(None) in [(10, 5), (42, 72)]
