from rolling.server.document.universe import UniverseStateDocument
import typing

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class UniverseLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def get_last_state(self) -> UniverseStateDocument:
        return (
            self._kernel.server_db_session.query(UniverseStateDocument)
            .order_by(UniverseStateDocument.turn.desc())
            .one()
        )
