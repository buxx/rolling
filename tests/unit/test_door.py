from aiohttp.test_utils import TestClient
import pytest
import typing
import unittest.mock

from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.character import MINIMUM_BEFORE_EXHAUSTED
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityJoinType
from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.affinity import MEMBER_STATUS
from rolling.server.document.build import BuildDocument
from rolling.server.document.build import DOOR_MODE_LABELS
from rolling.server.document.build import DOOR_MODE__CLOSED
from rolling.server.document.build import DOOR_MODE__CLOSED_EXCEPT_FOR
from rolling.server.document.build import DoorDocument


@pytest.fixture
def websocket_prepare_mock() -> typing.Generator[unittest.mock.AsyncMock, None, None]:
    with unittest.mock.patch("aiohttp.web_ws.WebSocketResponse.prepare") as mock_:
        yield mock_


@pytest.fixture
def zone_event_manager_listen_mock() -> typing.Generator[
    unittest.mock.AsyncMock, None, None
]:
    with unittest.mock.patch(
        "rolling.server.zone.websocket.ZoneEventsManager._listen"
    ) as mock_:
        yield mock_


@pytest.fixture
def zone_event_manager_close_mock() -> typing.Generator[
    unittest.mock.AsyncMock, None, None
]:
    with unittest.mock.patch(
        "rolling.server.zone.websocket.ZoneEventsManager.close_websocket"
    ) as mock_:
        yield mock_


@pytest.fixture
def socket_send_str_mock() -> typing.Generator[unittest.mock.AsyncMock, None, None]:
    with unittest.mock.patch("aiohttp.web_ws.WebSocketResponse.send_str") as mock_:
        yield mock_


@pytest.mark.usefixtures("disable_tracim")
class TestDoor:
    def _place_door(self, kernel: Kernel) -> DoorDocument:
        build = kernel.build_lib.place_build(
            world_row_i=1,
            world_col_i=1,
            zone_row_i=10,
            zone_col_i=10,
            build_id="DOOR",
            under_construction=False,
        )
        return build

    def _create_rule(
        self,
        kernel: Kernel,
        author: CharacterModel,
        door: BuildDocument,
        mode: str,
        affinity_ids: typing.Optional[typing.List[int]],
    ) -> None:
        kernel.door_lib.update(
            character_id=author.id,
            build_id=door.id,
            new_mode=mode,
            new_affinity_ids=affinity_ids,
        )

    def test_one_rule_lock__author_here__stranger_cant(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # Given
        door = self._place_door(kernel)
        self._create_rule(
            kernel, author=xena, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )

        # When
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

    def test_one_rule_lock_except__author_here__stranger_cant_but_member_can(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_franck_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        franck = worldmapc_franck_model

        # Given
        aff = kernel.affinity_lib.create(
            name="aff1",
            join_type=AffinityJoinType.ACCEPT_ALL,
            direction_type=AffinityDirectionType.ONE_DIRECTOR,
        )
        kernel.affinity_lib.join(
            character_id=xena.id,
            affinity_id=aff.id,
            accepted=True,
            request=False,
            status_id=CHIEF_STATUS[0],
        )
        kernel.affinity_lib.join(
            character_id=franck.id,
            affinity_id=aff.id,
            accepted=True,
            request=False,
            status_id=MEMBER_STATUS[0],
        )
        door = self._place_door(kernel)
        self._create_rule(
            kernel,
            author=xena,
            door=door,
            mode=DOOR_MODE__CLOSED_EXCEPT_FOR,
            affinity_ids=[aff.id],
        )

        # When
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=franck.id
        )

    def test_two_rule_lock__author_here_and_first_can__stranger_second_cant(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # Given
        door = self._place_door(kernel)
        self._create_rule(
            kernel, author=xena, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )
        self._create_rule(
            kernel, author=arthur, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )

        # When
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

    @pytest.mark.asyncio
    async def test_two_rule_lock__author_first_travel__stranger_second_can(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # Given
        door = self._place_door(kernel)
        self._create_rule(
            kernel, author=xena, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )
        self._create_rule(
            kernel, author=arthur, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )

        # When/Then 1
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

        # Given 2
        await kernel.character_lib.move(
            character=xena,
            to_world_row=2,
            to_world_col=2,
        )

        # When/Then 2
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

        # Given 2
        await kernel.character_lib.move(
            character=xena,
            to_world_row=1,
            to_world_col=1,
        )

        # When/Then 3
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

    @pytest.mark.asyncio
    async def test_one_rule_lock__author_first_travel__stranger_second_can(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # Given
        door = self._place_door(kernel)
        self._create_rule(
            kernel, author=xena, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )

        # When/Then 1
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

        # Given 2
        await kernel.character_lib.move(
            character=xena,
            to_world_row=2,
            to_world_col=2,
        )

        # When/Then 2
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

        # Given 2
        await kernel.character_lib.move(
            character=xena,
            to_world_row=1,
            to_world_col=1,
        )

        # When/Then 3
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

    @pytest.mark.asyncio
    async def test_one_rule_lock__author_dead__stranger_can(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # Given
        door = self._place_door(kernel)
        self._create_rule(
            kernel, author=xena, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )

        # When/Then 1
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

        # Given 2
        kernel.character_lib.kill(character_id=xena.id)

        # When/Then 2
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

    @pytest.mark.asyncio
    async def test_one_rule_lock__author_vulnerable__stranger_can(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # Given
        door = self._place_door(kernel)
        self._create_rule(
            kernel, author=xena, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )

        # When/Then 1
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=xena.id
        )
        assert kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

        # Given 2
        xena_doc = kernel.character_lib.get_document(xena.id)
        xena_doc.tiredness = MINIMUM_BEFORE_EXHAUSTED + 1
        kernel.server_db_session.add(xena_doc)
        kernel.server_db_session.commit()
        xena = kernel.character_lib.get(id_=xena.id)
        assert xena.vulnerable

        # When/Then 2
        assert not kernel.door_lib.is_access_locked_for(
            build_id=door.id, character_id=arthur.id
        )

    @pytest.mark.usefixtures("websocket_prepare_mock")
    @pytest.mark.usefixtures("zone_event_manager_listen_mock")
    @pytest.mark.usefixtures("zone_event_manager_close_mock")
    @pytest.mark.asyncio
    async def test_events_when_door_author_left_when_back_in_zone(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
        socket_send_str_mock: unittest.mock.AsyncMock,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        request_mock = unittest.mock.AsyncMock()

        # Given
        door = self._place_door(kernel)
        self._create_rule(
            kernel, author=xena, door=door, mode=DOOR_MODE__CLOSED, affinity_ids=[]
        )
        _ = await kernel.server_zone_events_manager.get_new_socket(
            request=request_mock,
            row_i=1,
            col_i=1,
            character_id=arthur.id,
        )

        # When
        await kernel.character_lib.move(
            character=xena,
            to_world_row=1,
            to_world_col=2,
        )

        # Then
        socket_send_str_mock.assert_awaited()
        events_str_list = [arg[0][0] for arg in socket_send_str_mock.await_args_list]
        assert any(["NEW_BUILD" in event_str for event_str in events_str_list])
        assert any(['{"WALKING":true}' in event_str for event_str in events_str_list])

        # When
        socket_send_str_mock.reset_mock()
        await kernel.character_lib.move(
            character=xena,
            to_world_row=1,
            to_world_col=1,
        )

        # Then
        socket_send_str_mock.assert_awaited()
        events_str_list = [arg[0][0] for arg in socket_send_str_mock.await_args_list]
        assert any(["NEW_BUILD" in event_str for event_str in events_str_list])
        assert any(['{"WALKING":false}' in event_str for event_str in events_str_list])

    @pytest.mark.usefixtures("websocket_prepare_mock")
    @pytest.mark.usefixtures("zone_event_manager_listen_mock")
    @pytest.mark.usefixtures("zone_event_manager_close_mock")
    @pytest.mark.asyncio
    async def test_events_when_door_author_update_rule(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_kernel: Kernel,
        socket_send_str_mock: unittest.mock.AsyncMock,
        worldmapc_web_app: TestClient,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        request_mock = unittest.mock.AsyncMock()
        web = worldmapc_web_app

        # Given
        door = self._place_door(kernel)
        _ = await kernel.server_zone_events_manager.get_new_socket(
            request=request_mock,
            row_i=1,
            col_i=1,
            character_id=arthur.id,
        )

        # When
        response = await web.post(
            f"/character/{xena.id}/door/{door.id}?mode={DOOR_MODE_LABELS[DOOR_MODE__CLOSED]}"
        )
        assert response.status == 200

        # Then
        socket_send_str_mock.assert_awaited()
        events_str_list = [arg[0][0] for arg in socket_send_str_mock.await_args_list]
        assert any(["NEW_BUILD" in event_str for event_str in events_str_list])
        assert any(['{"WALKING":false}' in event_str for event_str in events_str_list])
