import hashlib
from mimetypes import guess_extension
from mimetypes import guess_type
import os
import typing

from sqlalchemy.orm.exc import NoResultFound

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import get_with_stuff_action_url
from rolling.server.document.base import ImageDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel
    from rolling.action.base import WithStuffAction
    from rolling.types import ActionType


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

    stored_file_path = f"{kernel.game.config.folder_path}/data/images/{image_id}{extension}"
    os.makedirs(f"{kernel.game.config.folder_path}/data/images/", exist_ok=True)
    if not os.path.isfile(stored_file_path):
        with open(stored_file_path, "wb+") as f:
            f.write(file_bytes)

    return image_id


def with_multiple_carried_stuffs(
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
) -> Description:
    all_carried = kernel.stuff_lib.get_carried_by(character.id, stuff_id=stuff.stuff_id)
    if len(all_carried) > 1 and input_.quantity is None:
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
                            label="Quantité", name="quantity", type_=Type.NUMBER, default_value="1"
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
        parts.extend(do_for_one_func(character, all_carried[i], input_))

    return Description(title=title, items=parts + success_parts)
