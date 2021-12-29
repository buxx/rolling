# coding: utf-8
import dataclasses

from aiohttp.test_utils import TestClient
from collections import defaultdict
import pytest as pytest
import typing
import urllib.parse as urlparse
from urllib.parse import parse_qs

from guilang.description import Description
from guilang.description import Part
from rolling.action.transfer_ground import TransfertGroundCharacterAction
from rolling.action.transfer_ground import TransfertGroundCharacterModel
from rolling.exception import NoCarriedResource
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from rolling.util import get_on_and_around_coordinates
from tests.fixtures import create_stuff


class ButtonNotFound(Exception):
    pass


def extract_resource_button_url(
    description: Description, class_: str, identifier: str
) -> str:
    def extract_button_url_from_part(part: Part, class__: str, identifier_: str) -> str:
        if (
            class__ in part.classes
            and part.form_action
            and identifier_ in part.form_action
        ):
            return part.form_action

        for item_ in part.items:
            try:
                return extract_button_url_from_part(item_, class__, identifier_)
            except ButtonNotFound:
                pass

        raise ButtonNotFound()

    for item in description.items:
        try:
            return extract_button_url_from_part(item, class_, identifier)
        except ButtonNotFound:
            pass

    raise ButtonNotFound()


def extract_stuff_button_url(
    description: Description, class_: str, identifier: int
) -> str:
    def extract_button_url_from_part(part: Part, class__: str, identifier_: int) -> str:
        if (
            class__ in part.classes
            and part.form_action
            and str(identifier_) in part.form_action
        ):
            return part.form_action

        for item_ in part.items:
            try:
                return extract_button_url_from_part(item_, class__, identifier_)
            except ButtonNotFound:
                pass

        raise ButtonNotFound()

    for item in description.items:
        try:
            return extract_button_url_from_part(item, class_, identifier)
        except ButtonNotFound:
            pass

    raise ButtonNotFound()


@pytest.fixture
def action(
    worldmapc_kernel: Kernel,
) -> TransfertGroundCharacterAction:
    return typing.cast(
        TransfertGroundCharacterAction,
        worldmapc_kernel.action_factory.create_action(
            ActionType.TRANSFER_GROUND, "TRANSFER_GROUND"
        ),
    )


@dataclasses.dataclass
class TransferOperation:
    partial_deposit_count: typing.Optional[int] = None
    deposit_count: typing.Optional[int] = None
    partial_take_count: typing.Optional[int] = None
    take_count: typing.Optional[int] = None
    before_carried_quantity: typing.Optional[float] = None
    before_ground_quantity: typing.Optional[float] = None
    after_carried_quantity: typing.Optional[float] = None
    after_ground_quantity: typing.Optional[float] = None


class TestTransfertGround:
    @pytest.mark.parametrize(
        "initial_quantity,transfers",
        [
            (
                0.2,
                [
                    TransferOperation(
                        before_ground_quantity=0.0,
                        before_carried_quantity=0.2,
                        partial_deposit_count=1,
                        after_ground_quantity=0.02,
                        after_carried_quantity=0.18,
                    ),
                    TransferOperation(
                        partial_deposit_count=1,
                        after_ground_quantity=0.04,
                        after_carried_quantity=0.16,
                    ),
                    TransferOperation(
                        partial_take_count=1,
                        after_ground_quantity=0.036,
                        after_carried_quantity=0.164,
                    ),
                    TransferOperation(
                        partial_take_count=1,
                        after_ground_quantity=0.0324,
                        after_carried_quantity=0.1676,
                    ),
                    TransferOperation(
                        partial_take_count=2,
                        after_ground_quantity=0.026,
                        after_carried_quantity=0.174,
                    ),
                ],
            ),
        ],
    )
    async def test_transfer_partial_resource(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        action: TransfertGroundCharacterAction,
        worldmapc_web_app: TestClient,
        initial_quantity: float,
        transfers: typing.List[TransferOperation],
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app
        kernel.resource_lib.add_resource_to("WOOD", initial_quantity, xena.id)

        xena_doc = kernel.character_lib.get_document(xena.id)
        xena_doc.zone_row_i = 100
        xena_doc.zone_col_i = 95
        kernel.server_db_session.add(xena_doc)
        kernel.server_db_session.commit()
        xena = kernel.character_lib.get(xena_doc.id)

        def get_on_ground_quantity(raise_: bool = False) -> float:
            found_on_ground = False
            on_ground_quantities: typing.DefaultDict[str, float] = defaultdict(
                lambda: 0.0
            )
            scan_coordinates: typing.List[
                typing.Tuple[int, int]
            ] = get_on_and_around_coordinates(
                x=xena.zone_row_i, y=xena.zone_col_i, exclude_on=False, distance=1
            )
            for around_row_i, around_col_i in scan_coordinates:
                for resource in kernel.resource_lib.get_ground_resource(
                    world_row_i=xena.world_row_i,
                    world_col_i=xena.world_col_i,
                    zone_row_i=around_row_i,
                    zone_col_i=around_col_i,
                ):
                    if resource.id != "WOOD":
                        continue

                    found_on_ground = True
                    on_ground_quantities[resource.id] += resource.quantity

            if not found_on_ground and raise_:
                raise NoCarriedResource()

            return round(on_ground_quantities.get("WOOD", 0.0), 4)

        def get_carried_quantity(raise_: bool = False) -> float:
            return round(
                kernel.resource_lib.get_one_carried_by(
                    character_id=xena.id,
                    resource_id="WOOD",
                    empty_object_if_not=not raise_,
                ).quantity,
                4,
            )

        parameters = {}
        for transfer in transfers:
            # before deposit
            if transfer.before_ground_quantity is not None:
                if transfer.before_ground_quantity == 0.0:
                    with pytest.raises(NoCarriedResource):
                        get_on_ground_quantity(raise_=True)
                else:
                    assert get_on_ground_quantity() == transfer.before_ground_quantity

            if transfer.before_carried_quantity is not None:
                if transfer.before_carried_quantity == 0.0:
                    with pytest.raises(NoCarriedResource):
                        get_carried_quantity(raise_=True)
                else:
                    assert get_carried_quantity() == transfer.before_carried_quantity

            # Deposit
            response = None
            if transfer.partial_deposit_count:
                description = await action.perform(
                    xena, input_=TransfertGroundCharacterModel(parameters)
                )
                deposit_url = extract_resource_button_url(
                    description, "partial_right", "WOOD"
                )
                for _ in range(transfer.partial_deposit_count):
                    response = await web.post(deposit_url)
                    assert 200 == response.status

            if transfer.deposit_count:
                description = await action.perform(
                    xena, input_=TransfertGroundCharacterModel(parameters)
                )
                deposit_url = extract_resource_button_url(description, "right", "WOOD")
                for _ in range(transfer.deposit_count):
                    response = await web.post(deposit_url)
                    assert 200 == response.status

            # Take
            if transfer.partial_take_count:
                description = await action.perform(
                    xena, input_=TransfertGroundCharacterModel(parameters)
                )
                take_url = extract_resource_button_url(
                    description, "partial_left", "WOOD"
                )
                for _ in range(transfer.partial_take_count):
                    response = await web.post(take_url)
                    assert 200 == response.status

            if transfer.take_count:
                description = await action.perform(
                    xena, input_=TransfertGroundCharacterModel(parameters)
                )
                take_url = extract_resource_button_url(description, "left", "WOOD")
                for _ in range(transfer.take_count):
                    response = await web.post(take_url)
                    assert 200 == response.status

            # Interpretation of redirect url query
            assert response
            json_ = await response.json()
            assert json_.get("redirect")
            parsed_url = urlparse.urlparse(json_["redirect"])
            parameters = {k: float(v[0]) for k, v in parse_qs(parsed_url.query).items()}

            # After
            if transfer.after_ground_quantity is not None:
                if transfer.after_ground_quantity == 0.0:
                    with pytest.raises(NoCarriedResource):
                        get_on_ground_quantity(raise_=True)
                else:
                    assert get_on_ground_quantity() == transfer.after_ground_quantity

            if transfer.after_carried_quantity is not None:
                if transfer.after_carried_quantity == 0.0:
                    with pytest.raises(NoCarriedResource):
                        get_carried_quantity(raise_=True)
                else:
                    assert get_carried_quantity() == transfer.after_carried_quantity

    async def test_transfer_stuff(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        action: TransfertGroundCharacterAction,
        worldmapc_web_app: TestClient,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        xena_doc = kernel.character_lib.get_document(xena.id)
        xena_doc.zone_row_i = 100
        xena_doc.zone_col_i = 95
        kernel.server_db_session.add(xena_doc)
        kernel.server_db_session.commit()
        xena = kernel.character_lib.get(xena_doc.id)

        haxe1 = create_stuff(kernel, "STONE_HAXE")
        haxe2 = create_stuff(kernel, "STONE_HAXE")
        haxe3 = create_stuff(kernel, "STONE_HAXE")
        kernel.stuff_lib.set_as_used_as_weapon(xena.id, haxe1.id)
        kernel.stuff_lib.set_as_used_as_weapon(xena.id, haxe2.id)
        kernel.stuff_lib.set_as_used_as_weapon(xena.id, haxe3.id)

        def get_on_ground_quantity() -> int:
            return kernel.stuff_lib.count_zone_stuffs(
                world_row_i=xena.world_row_i,
                world_col_i=xena.world_col_i,
            )

        def get_carried_quantity() -> int:
            return len(
                kernel.stuff_lib.get_carried_by(
                    character_id=xena.id, stuff_id="STONE_HAXE"
                )
            )

        assert get_on_ground_quantity() == 0
        assert get_carried_quantity() == 3

        description = await action.perform(xena, input_=TransfertGroundCharacterModel())
        deposit_url = extract_stuff_button_url(description, "partial_right", haxe1.id)

        response = await web.post(deposit_url)
        assert 200 == response.status

        assert get_on_ground_quantity() == 1
        assert get_carried_quantity() == 2

        description = await action.perform(xena, input_=TransfertGroundCharacterModel())
        deposit_url = extract_stuff_button_url(description, "right", haxe2.id)

        response = await web.post(deposit_url)
        assert 200 == response.status

        assert get_on_ground_quantity() == 3
        assert get_carried_quantity() == 0

        description = await action.perform(xena, input_=TransfertGroundCharacterModel())
        take_url = extract_stuff_button_url(description, "partial_left", haxe1.id)

        response = await web.post(take_url)
        assert 200 == response.status

        assert get_on_ground_quantity() == 2
        assert get_carried_quantity() == 1

        description = await action.perform(xena, input_=TransfertGroundCharacterModel())
        take_url = extract_stuff_button_url(description, "left", haxe2.id)

        response = await web.post(take_url)
        assert 200 == response.status
        assert get_on_ground_quantity() == 0
        assert get_carried_quantity() == 3
