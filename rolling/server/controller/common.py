# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
import os
from sqlalchemy.orm.exc import NoResultFound

from rolling.kernel import Kernel
from rolling.server.controller.base import BaseController
from rolling.server.document.base import ImageDocument
from rolling.server.extension import hapic


class CommonController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    @hapic.with_api_doc()
    @hapic.handle_exception(NoResultFound, http_code=404)
    async def get_image(self, request: Request):
        image_doc: ImageDocument = self._kernel.server_db_session.query(ImageDocument).filter(
            ImageDocument.id == int(request.match_info.get("image_id"))
        ).one()

        return FileResponse(
            f"{self._kernel.game.config.folder_path}/data/images/"
            f"{image_doc.id}{image_doc.extension}"
        )

    def bind(self, app: Application) -> None:
        app.add_routes([web.get("/image/{image_id:\d+}", self.get_image)])
