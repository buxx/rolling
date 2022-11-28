import typing

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.server.document.affinity import AffinityDocument
    from rolling.types import CharacterId


class ProtectorateState:
    @classmethod
    def none(cls, kernel: "Kernel") -> "ProtectorateState":
        return cls(kernel, None)

    @classmethod
    def protected_by(
        cls, kernel: "Kernel", affinity: "AffinityDocument"
    ) -> "ProtectorateState":
        return cls(kernel, affinity)

    def __init__(
        self, kernel: "Kernel", affinity: typing.Optional["AffinityDocument"]
    ) -> None:
        self._kernel = kernel
        self._affinity = affinity

    def _character_in_affinity_or_no_affinity(
        self, character_id: "CharacterId"
    ) -> bool:
        if self._affinity is not None:
            return self._kernel.affinity_lib.character_is_in_affinity(
                character_id, self._affinity.id
            )

        return True

    def affinity(self) -> typing.Optional["AffinityDocument"]:
        return self._affinity

    def allow_ground_resources(self, character_id: "CharacterId") -> bool:
        return self._character_in_affinity_or_no_affinity(character_id)

    def allow_ground_stuffs(self, character_id: "CharacterId") -> bool:
        return self._character_in_affinity_or_no_affinity(character_id)

    def allow_use_builds(self, character_id: "CharacterId") -> bool:
        return self._character_in_affinity_or_no_affinity(character_id)
