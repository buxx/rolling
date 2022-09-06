import hashlib
import math
from mimetypes import guess_extension
from mimetypes import guess_type
import os
from sqlalchemy.orm.exc import NoResultFound
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import NotEnoughActionPoints
from rolling.server.document.base import ImageDocument

if typing.TYPE_CHECKING:
    from rolling.action.base import WithStuffAction
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel
    from rolling.rolling_types import ActionType


def register_image(kernel: "Kernel", file_path: str) -> int:
    extension = guess_extension(guess_type(file_path)[0])
    with open(file_path, "rb") as file:
        file_bytes = file.read()
        checksum = hashlib.md5(file_bytes).hexdigest()

    try:
        image_id = (
            kernel.server_db_session.query(ImageDocument.id)
            .filter(ImageDocument.checksum == checksum)
            .one()
            .id
        )
    except NoResultFound:
        image_document = ImageDocument(extension=extension, checksum=checksum)
        kernel.server_db_session.add(image_document)
        kernel.server_db_session.commit()
        image_id = image_document.id

    stored_file_path = (
        f"{kernel.game.config.folder_path}/data/images/{image_id}{extension}"
    )
    os.makedirs(f"{kernel.game.config.folder_path}/data/images/", exist_ok=True)
    if not os.path.isfile(stored_file_path):
        with open(stored_file_path, "wb+") as f:
            f.write(file_bytes)

    return image_id


async def with_multiple_carried_stuffs(
    action: "WithStuffAction",
    kernel: "Kernel",
    character: "CharacterModel",
    stuff: "StuffModel",
    input_: typing.Any,
    action_type: "ActionType",
    do_for_one_func: typing.Callable[
        ["CharacterModel", "StuffModel", typing.Any], typing.List["Part"]
    ],
    title: str,
    success_parts: typing.List["Part"],
    redirect: typing.Optional[str] = None,
) -> Description:
    all_carried = kernel.stuff_lib.get_carried_by(
        character.id, stuff_id=stuff.stuff_id, exclude_crafting=False
    )
    if (
        len(all_carried) > 1
        and input_.quantity is None
        and getattr(input_, "quick_action", 0) == 0
    ):
        return Description(
            title=title,
            items=[
                Part(
                    text=f"Vous possedez {len(all_carried)} {stuff.name}, éxécuter cette action sur combien ?"
                ),
                Part(
                    is_form=True,
                    form_action=get_with_stuff_action_url(
                        character_id=character.id,
                        action_type=action_type,
                        stuff_id=stuff.id,
                        query_params=action.input_model_serializer.dump(input_),
                        action_description_id=action.description.id,
                    ),
                    submit_label="Continuer",
                    form_values_in_query=True,
                    items=[
                        Part(
                            label="Quantité",
                            name="quantity",
                            type_=Type.NUMBER,
                            default_value="1",
                            min_value=1.0,
                            max_value=len(all_carried),
                        )
                    ],
                ),
                Part(is_link=True, label=f"Faire ça avec les {len(all_carried)}"),
            ],
        )

    if input_.quantity is not None:
        do_it_count = input_.quantity
    else:
        do_it_count = 1

    parts = []
    for i in range(do_it_count):
        try:
            parts.extend(await do_for_one_func(character, all_carried[i], input_))
        except NotEnoughActionPoints:
            parts.append(Part(text="Plus assez de Points d'Actions !"))

    return Description(title=title, items=parts + success_parts, redirect=redirect)


def get_round_resource_quantity(quantity: float) -> str:
    return str(round(quantity * 0.1, 4))
