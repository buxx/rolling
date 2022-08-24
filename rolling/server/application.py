# coding: utf-8
import typing
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import base64
import json
import serpyco

from guilang.description import Description
from rolling.exception import AccountNotFound
from rolling.exception import ComponentNotPrepared
from rolling.kernel import Kernel
from rolling.log import server_logger
from rolling.server.controller.account import AccountController
from rolling.server.controller.admin import AdminController
from rolling.server.controller.affinity import AffinityController
from rolling.server.controller.build import BuildController
from rolling.server.controller.business import BusinessController
from rolling.server.controller.character import CharacterController
from rolling.server.controller.common import CommonController
from rolling.server.controller.conversation import ConversationController
from rolling.server.controller.corpse import AnimatedCorpseController
from rolling.server.controller.spawn import SpawnPointController
from rolling.server.controller.system import SystemController
from rolling.server.controller.world import WorldController
from rolling.server.controller.zone import ZoneController
from rolling.server.event import ThereIsAroundProcessor
from rolling.server.lib.character import CharacterLib

HEADER_NAME__DISABLE_AUTH_TOKEN = "DISABLE_AUTH_TOKEN"


def get_application(
    kernel: Kernel,
    disable_auth: bool = False,
    serve_static_files: typing.Optional[str] = None,
) -> Application:
    character_lib = CharacterLib(kernel)
    description_serializer = serpyco.Serializer(Description)

    @middleware
    async def auth(request: Request, handler):
        request_disable_auth = False
        try:
            request_disable_auth = (
                request.headers[HEADER_NAME__DISABLE_AUTH_TOKEN]
                == kernel.server_config.disable_auth_token
            )
        except KeyError:
            pass

        if disable_auth or request_disable_auth:
            return await handler(request)

        if (
            request.path
            not in (
                "/",
                "/favicon.ico",
                "/account/create",
                "/system/version",
                "/system/describe/infos",
                "/system/loadings",
                "/system/illustrations-names",
                "/infos",
                "/media",
                "/media_bg",
                "/account/generate_new_password",
                "/account/password_lost",
                "/world/events",
                "/world/source",
                "/zones/tiles",
            )
            and not request.path.startswith("/ac/")
            and not request.path.startswith("/ws/")
            and not request.path.startswith("/admin")
            and not request.path.startswith("/avatar")
            and not request.path.startswith("/media")
            and not request.path.startswith("/static")
        ):
            response_401 = Response(
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="Veuillez vous identifier"'},
                body="__AUTH_REQUIRED__",
            )

            if "Authorization" in request.headers:
                if request.headers["Authorization"].lower().startswith("basic"):
                    try:
                        login, password = (
                            base64.b64decode(request.headers["Authorization"][6:])
                            .decode()
                            .split(":")
                        )
                    except (KeyError, IndexError, ValueError):
                        return response_401
                    try:
                        account = kernel.account_lib.get_account_for_credentials(
                            login=login, password=password
                        )
                    except AccountNotFound:
                        return response_401
                elif request.headers["Authorization"].lower().startswith("token"):
                    try:
                        token = request.headers["Authorization"][6:]
                    except (KeyError, IndexError, ValueError):
                        return response_401

                    try:
                        account = kernel.account_lib.get_account_for_token(token)
                    except AccountNotFound:
                        return response_401
                else:
                    return response_401

            request["account_id"] = account.id
            request["account_character_id"] = account.current_character_id

        return await handler(request)

    @middleware
    async def character_infos(request: Request, handler):
        account_character_id = request.get("account_character_id")

        if not account_character_id:
            return await handler(request)

        response = await handler(request)

        if "application/json" != response.headers.get("Content-Type"):
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

        return Response(
            body=description_serializer.dump_json(description),
            status=response.status,
            content_type="application/json",
        )

    @middleware
    async def quick_actions(request: Request, handler):
        account_character_id = request.get("account_character_id")
        response = await handler(request)

        action_uuid = request.query.get("action_uuid", None)
        is_quick_action = request.query.get("quick_action", "0") == "1"
        disable_resend_quick_actions = (
            request.query.get("disable_resend_quick_actions", "0") == "1"
        )
        explode_take = request.query.get("explode_take", "0") == "1"
        if (
            account_character_id
            and is_quick_action
            and not disable_resend_quick_actions
        ):
            character_doc = kernel.character_lib.get_document(account_character_id)
            character_socket = kernel.server_zone_events_manager.get_character_socket(
                account_character_id,
            )
            if character_socket is not None:
                await ThereIsAroundProcessor(
                    kernel=kernel,
                    zone_events_manager=kernel.server_zone_events_manager,
                ).send_around(
                    row_i=character_doc.zone_row_i,
                    col_i=character_doc.zone_col_i,
                    character_id=character_doc.id,
                    sender_socket=character_socket,
                    explode_take=explode_take,
                )

        if action_uuid is not None:
            body_as_json = json.loads(response.body._value)
            try:
                description = description_serializer.load(body_as_json)
            except serpyco.ValidationError:
                return response

            # Description is VERY permissive, consider is not a description if no title
            if not description.title:
                return response

            description.action_uuid = action_uuid
            return Response(
                body=description_serializer.dump_json(description),
                status=response.status,
                content_type="application/json",
            )

        return response

    @middleware
    async def rollback_session(request: Request, handler):
        try:
            return await handler(request)
        except Exception as exc:
            try:
                server_logger.warning("Error happen over web handler, rollback session")
                kernel.server_db_session.rollback()
            except ComponentNotPrepared:
                server_logger.error(
                    f"Trying to rollback session on error but session not prepared !"
                )
            raise exc

    @middleware
    async def allow_origin(request: Request, handler):
        response = await handler(request)
        response.headers[
            "Access-Control-Allow-Origin"
        ] = kernel.server_config.allow_origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    app = web.Application(
        middlewares=[
            auth,
            character_infos,
            rollback_session,
            quick_actions,
            allow_origin,
        ]
    )

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
    SystemController(
        kernel,
        serve_static_files=serve_static_files,
    ).bind(app)
    AnimatedCorpseController(kernel).bind(app)
    AccountController(kernel).bind(app)
    SpawnPointController(kernel).bind(app)

    return app
