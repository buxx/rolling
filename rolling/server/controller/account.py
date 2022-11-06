# coding: utf-8
from dataclasses import dataclass

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2
from hapic.data import HapicData
from hashlib import sha256
from pathlib import Path
import pkg_resources
import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.exception import AccountError
from rolling.exception import EmailAlreadyUsed
from rolling.exception import EmailWrongFormat
from rolling.exception import NotSamePassword
from rolling.exception import UsernameAlreadyUsed
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
import rrolling

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


@dataclass
class CreateAccountBody:
    username: typing.Optional[str] = None
    email: typing.Optional[str] = None
    raw_password: typing.Optional[str] = None
    raw_password_repeat: typing.Optional[str] = None


@dataclass
class PasswordLostQuery:
    login: typing.Optional[str] = None
    validate: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclass
class GenerateNewPasswordQuery:
    token: str


class AccountController(BaseController):
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    @hapic.with_api_doc()
    @hapic.handle_exception(AccountError, http_code=400)
    @hapic.input_body(CreateAccountBody)
    @hapic.output_body(Description)
    async def create_account(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        if (
            hapic_data.body.username
            and hapic_data.body.email
            and hapic_data.body.raw_password
            and hapic_data.body.raw_password_repeat
        ):
            if "@" not in hapic_data.body.email:
                raise EmailWrongFormat("Email incorrect")
            if (
                hapic_data.body.raw_password.strip()
                != hapic_data.body.raw_password_repeat.strip()
            ):
                raise NotSamePassword(
                    "Les mots de passes saisies ne sont pas indentiques"
                )
            if self._kernel.account_lib.username_exist(
                hapic_data.body.username.strip()
            ):
                raise UsernameAlreadyUsed("Login/pseudo déjà utilisé")
            if self._kernel.account_lib.email_exist(hapic_data.body.email.strip()):
                raise EmailAlreadyUsed("Email déjà utilisé")

            self._kernel.account_lib.create(
                username=hapic_data.body.username.strip(),
                email=hapic_data.body.email.strip(),
                password=hapic_data.body.raw_password.strip(),
            )
            # FIXME: redirect to create character
            return Description(account_created=True)
        elif (
            hapic_data.body.username
            or hapic_data.body.email
            or hapic_data.body.raw_password
            or hapic_data.body.raw_password_repeat
        ):
            raise AccountError("Vous devez saisir toutes les informations")

        return Description(
            title="Créer un compte",
            items=[
                Part(
                    is_form=True,
                    form_action="/account/create",
                    items=[
                        Part(name="username", label="Login/pseudo", type_=Type.STRING),
                        Part(name="email", label="Email", type_=Type.STRING),
                        Part(
                            name="raw_password",
                            label="Mot de passe",
                            type_=Type.STRING,
                            classes=["password"],
                        ),
                        Part(
                            name="raw_password_repeat",
                            label="Répétez le mot de passe",
                            type_=Type.STRING,
                            classes=["password"],
                        ),
                    ],
                )
            ],
            footer_inventory=False,
            footer_actions=False,
            back_to_zone=False,
        )

    @hapic.with_api_doc()
    async def get_current_character_id(self, request: Request) -> Response:
        account = self._kernel.account_lib.get_account_for_id(request["account_id"])
        return Response(body=account.current_character_id or "")

    @hapic.with_api_doc()
    @hapic.handle_exception(AccountError, http_code=400)
    @hapic.input_query(PasswordLostQuery)
    @hapic.output_body(Description)
    async def password_lost(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        if hapic_data.query.validate:
            try:
                self._kernel.account_lib.send_new_password_request(
                    hapic_data.query.login
                )
            except AccountError:
                pass
            return Description(
                title="Nouveau mot de passe envoyé",
                items=[
                    Part(
                        text=(
                            "Si l'identifiant/email que vous avez saisi correspond à "
                            "un utilisateur existant, un email a été envoyé. Pensez à "
                            "bien vérifier votre boite de SPAM."
                        )
                    )
                ],
                back_to_zone=False,
                footer_inventory=False,
                footer_actions=False,
            )

        return Description(
            title="Mot de passe perdu",
            items=[
                Part(
                    is_form=True,
                    form_action="/account/password_lost?validate=1",
                    form_values_in_query=True,
                    items=[
                        Part(
                            name="login",
                            label="Login/Email",
                            default_value=hapic_data.query.login,
                            type_=Type.STRING,
                        )
                    ],
                )
            ],
            footer_inventory=False,
            footer_actions=False,
            back_to_zone=False,
        )

    @hapic.with_api_doc()
    @hapic.input_query(GenerateNewPasswordQuery)
    async def generate_new_password(
        self, request: Request, hapic_data: HapicData
    ) -> Response:
        try:
            new_password = self._kernel.account_lib.generate_new_password(
                hapic_data.query.token
            )
        except AccountError:
            return Response(
                body="Clé invalide: impossible de générer un nouveau mot de passe"
            )
        return Response(body=f"Nouveau mot de passe: {new_password}")

    @hapic.with_api_doc()
    @aiohttp_jinja2.template("account.html")
    async def manage_account(self, request: Request) -> dict:
        message_type = None
        message = None
        account = self._kernel.account_lib.get_account_for_id(request["account_id"])

        if request.method == "POST":
            data = await request.post()

            if data.get("new_email"):
                new_email = data.get("new_email")
                if "@" not in new_email:
                    message_type = "error"
                    message = "Format de l'email incorrect"
                elif self._kernel.account_lib.email_exist(new_email):
                    message_type = "error"
                    message = "Email déjà utilisé"
                else:
                    account.email = new_email
                    self._kernel.server_db_session.add(account)

                    character_doc = self._kernel.character_lib.get_document(
                        account.current_character_id
                    )
                    tracim_account = self._kernel.character_lib.get_tracim_account(
                        account.current_character_id
                    )
                    rrolling.tracim.Dealer(
                        self._kernel.server_config.tracim_config
                    ).set_account_email(
                        tracim_account,
                        rrolling.tracim.AccountId(character_doc.tracim_user_id),
                        rrolling.tracim.Email(new_email),
                    )

                    self._kernel.server_db_session.commit()

                    message_type = "success"
                    message = "Email mis à jour"

            if (
                data.get("current_password")
                and data.get("new_password1")
                and data.get("new_password2")
            ):
                current_password = data.get("current_password")
                new_password1 = data.get("new_password1")
                new_password2 = data.get("new_password2")
                if (
                    sha256(
                        f"{current_password}{account.password_salt}".encode()
                    ).hexdigest()
                    != account.password_hash
                ):
                    message_type = "error"
                    message = "Mot de passe actuel incorrect"
                elif new_password1 != new_password2:
                    message_type = "error"
                    message = "Nouveaux mot de passe différents"
                else:
                    account.password_hash = sha256(
                        f"{new_password1}{account.password_salt}".encode()
                    ).hexdigest()
                    self._kernel.server_db_session.add(account)
                    self._kernel.server_db_session.commit()
                    message_type = "success"
                    message = "Mot de passe modifié"

        characters = self._kernel.character_lib.get_documents_by_account_id(account.id)

        return {
            "account": account,
            "character": self._kernel.character_lib.get(request["account_character_id"])
            if request["account_character_id"]
            else None,
            "message": message,
            "message_type": message_type,
            "characters": characters,
        }

    @hapic.with_api_doc()
    def generate_auth_token(self, request: Request) -> web.Response:
        token = self._kernel.account_lib.generate_new_auth_token(request["account_id"])
        return web.Response(status=200, body=token)

    @hapic.with_api_doc()
    def open_character_rp(self, request: Request) -> web.Response:
        account = self._kernel.account_lib.get_account_for_id(request["account_id"])
        character = self._kernel.character_lib.get_document(
            request.match_info["character_id"]
        )
        tracim_account = self._kernel.character_lib.get_tracim_account(character.id)

        if character.account_id != account.id:
            return web.Response(status=404)

        session_key = rrolling.tracim.Dealer(
            self._kernel.server_config.tracim_config
        ).get_new_session_key(tracim_account)

        response = web.HTTPTemporaryRedirect(self._kernel.server_config.rp_url)
        response.set_cookie(
            "session_key",
            session_key,
            # expires="Sat, 12-Nov-2022 21:45:47 GMT",
            httponly=True,
            path="/",
            samesite="Lax",
        )
        return response

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.post("/account/create", self.create_account),
                web.get("/account/current_character_id", self.get_current_character_id),
                web.post("/account/password_lost", self.password_lost),
                web.get("/account/generate_new_password", self.generate_new_password),
                web.get("/account/manage", self.manage_account),
                web.post("/account/manage", self.manage_account),
                web.get("/account/auth-token", self.generate_auth_token),
                web.get(
                    "/account/character/{character_id}/open-rp", self.open_character_rp
                ),
            ]
        )
