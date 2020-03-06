import hashlib
from mimetypes import guess_extension
from mimetypes import guess_type
import os
import typing

from sqlalchemy.orm.exc import NoResultFound

from rolling.server.document.base import ImageDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


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
