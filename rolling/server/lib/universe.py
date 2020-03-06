import datetime
import typing

from rolling.server.document.universe import UniverseStateDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class UniverseLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def get_last_state(self) -> UniverseStateDocument:
        return (
            self._kernel.server_db_session.query(UniverseStateDocument)
            .order_by(UniverseStateDocument.turn.desc())
            .limit(1)
            .one()
        )

    def add_new_state(self, commit: bool = True) -> None:
        last_state = self.get_last_state()
        self._kernel.server_db_session.add(
            UniverseStateDocument(turn=last_state.turn + 1, turned_at=datetime.datetime.utcnow())
        )

        if commit:
            self._kernel.server_db_session.commit()
