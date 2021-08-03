# coding: utf-8
import json

import serpyco
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import base64

from guilang.description import Description
from rolling.exception import AccountNotFound
from rolling.kernel import Kernel
from rolling.server.controller.account import AccountController
from rolling.server.controller.admin import AdminController
from rolling.server.controller.affinity import AffinityController
from rolling.server.controller.build import BuildController
from rolling.server.controller.business import BusinessController
from rolling.server.controller.character import CharacterController
from rolling.server.controller.common import CommonController
from rolling.server.controller.conversation import ConversationController
from rolling.server.controller.corpse import AnimatedCorpseController
from rolling.server.controller.system import SystemController
from rolling.server.controller.world import WorldController
from rolling.server.controller.zone import ZoneController
from rolling.server.lib.character import CharacterLib


def get_application(kernel: Kernel, disable_auth: bool = False) -> Application:
    character_lib = CharacterLib(kernel)
    description_serializer = serpyco.Serializer(Description)

    @middleware
    async def auth(request: Request, handler):
        if disable_auth:
            return await handler(request)

        if (
            request.path
            not in (
                "/account/create",
                "/system/version",
                "/system/describe/infos",
                "/infos",
                "/media",
                "/media_bg",
                "/account/generate_new_password",
                "/account/password_lost",
                "/world/events",
                "/world/source",
            )
            and not request.path.startswith("/ac/")
            and not request.path.startswith("/ws/")
            and not request.path.startswith("/admin")
        ):
            try:
                login, password = (
                    base64.b64decode(request.headers["Authorization"][6:]).decode().split(":")
                )
            except (KeyError, IndexError, ValueError):
                return Response(
                    status=401,
                    headers={"WWW-Authenticate": 'Basic realm="Veuillez vous identifier"'},
                )
            try:
                account = kernel.account_lib.get_account_for_credentials(
                    login=login, password=password
                )
            except AccountNotFound:
                return Response(
                    status=401,
                    headers={"WWW-Authenticate": 'Basic realm="Veuillez vous identifier"'},
                )

            request["account_id"] = account.id
            request["account_character_id"] = account.current_character_id

        return await handler(request)

    @middleware
    async def character_infos(request: Request, handler):
        account_character_id = request.get("account_character_id")

        if not account_character_id:
            return await handler(request)

        response = await handler(request)

        if 'application/json' != response.headers.get("Content-Type"):
            return response

        body_as_json = json.loads(response.body._value)
        try:
            description = description_serializer.load(body_as_json)
        except serpyco.ValidationError:
            return response

        # Description is VERY permissive, consider is not a description if no title
        if not description.title:
            return response

        character = character_lib.get(account_character_id)
        description.character_ap = str(round(character.action_points, 1))

        return Response(body=description_serializer.dump_json(description), status=response.status, content_type='application/json')

    app = web.Application(middlewares=[auth, character_infos])

    # Bind routes
    CommonController(kernel).bind(app)
    CharacterController(kernel).bind(app)
    ZoneController(kernel).bind(app)
    WorldController(kernel).bind(app)
    BuildController(kernel).bind(app)
    ConversationController(kernel).bind(app)
    AffinityController(kernel).bind(app)
    BusinessController(kernel).bind(app)
    BusinessController(kernel).bind(app)
    AdminController(kernel).bind(app)
    SystemController(kernel).bind(app)
    AnimatedCorpseController(kernel).bind(app)
    AccountController(kernel).bind(app)

    return app
