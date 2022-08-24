# coding: utf-8
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from hashlib import sha256
import random
import smtplib
from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
import string
import time
import typing
import uuid
from uuid import uuid4

from rolling.exception import AccountNotFound
from rolling.server.document.account import AccountDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class AccountLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def get_account_for_token(self, token: str) -> AccountDocument:
        try:
            return (
                self._kernel.server_db_session.query(AccountDocument)
                .filter(AccountDocument.authentication_token == token)
                .filter(AccountDocument.authentication_expire > round(time.time()))
                .one()
            )
        except NoResultFound:
            raise AccountNotFound()

    def get_account_for_credentials(self, login: str, password: str) -> AccountDocument:
        try:
            try_account: AccountDocument = (
                self._kernel.server_db_session.query(AccountDocument)
                .filter(
                    or_(
                        AccountDocument.email == login,
                        AccountDocument.username == login,
                    ),
                )
                .one()
            )
        except NoResultFound:
            raise AccountNotFound()

        if (
            not sha256(f"{password}{try_account.password_salt}".encode()).hexdigest()
            == try_account.password_hash
        ):
            raise AccountNotFound()

        return try_account

    def username_exist(self, username: str) -> bool:
        return bool(
            self._kernel.server_db_session.query(AccountDocument)
            .filter(AccountDocument.username == username)
            .count()
        )

    def email_exist(self, email: str) -> bool:
        return bool(
            self._kernel.server_db_session.query(AccountDocument)
            .filter(AccountDocument.email == email)
            .count()
        )

    def create(
        self, username: str, email: str, password: str, commit: bool = True
    ) -> AccountDocument:
        password_salt = uuid.uuid4().hex[0:32]
        account = AccountDocument(
            id=uuid4().hex,
            username=username,
            email=email,
            password_salt=password_salt,
            password_hash=sha256(f"{password}{password_salt}".encode()).hexdigest(),
        )
        self._kernel.server_db_session.add(account)

        if commit:
            self._kernel.server_db_session.commit()

        return account

    def get_account_for_id(self, account_id: str) -> AccountDocument:
        return (
            self._kernel.server_db_session.query(AccountDocument)
            .filter(AccountDocument.id == account_id)
            .one()
        )

    def get_account_for_username_or_email(
        self, username_or_email: str
    ) -> AccountDocument:
        try:
            return (
                self._kernel.server_db_session.query(AccountDocument)
                .filter(
                    or_(
                        AccountDocument.username == username_or_email,
                        AccountDocument.email == username_or_email,
                    )
                )
                .one()
            )
        except NoResultFound:
            raise AccountNotFound(
                f"Account not found for username_or_email '{username_or_email}'"
            )

    def get_account_for_reset_password_token(self, token: str) -> AccountDocument:
        try:
            return (
                self._kernel.server_db_session.query(AccountDocument)
                .filter(
                    and_(
                        AccountDocument.reset_password_token == token,
                        AccountDocument.reset_password_expire > round(time.time()),
                    )
                )
                .one()
            )
        except NoResultFound:
            raise AccountNotFound(f"Account not found for token '{token}'")

    def send_new_password_request(self, username_or_email: str) -> None:
        account = self.get_account_for_username_or_email(username_or_email)
        account.reset_password_token = uuid.uuid4().hex
        account.reset_password_expire = round(time.time()) + 3600
        self._kernel.server_db_session.add(account)
        self._kernel.server_db_session.commit()

        email = MIMEMultipart()

        # setup the parameters of the message
        email["From"] = self._kernel.server_config.sender_email
        email["To"] = account.email
        email["Subject"] = "Mot de passe perdu pour Rolling"

        generate_new_password_url = (
            f"{self._kernel.server_config.base_url}/account/generate_new_password"
            f"?token={account.reset_password_token}"
        )
        plain_message = f"""Bonjour,
Une demande de mot de passe perdu a été faite pour votre compte pour le jeu Rolling.
Si vous êtes bien l'auteur de cette demande, suivez ce lien: {generate_new_password_url}
"""
        email.attach(MIMEText(plain_message, "plain"))
        server = smtplib.SMTP(
            host=self._kernel.server_config.smtp_server,
            port=int(self._kernel.server_config.smtp_port),
        )
        server.starttls()
        server.login(
            self._kernel.server_config.smtp_user,
            self._kernel.server_config.smtp_password,
        )
        server.sendmail(email["From"], email["To"], email.as_string())
        server.quit()

    def generate_new_password(self, token: str) -> str:
        account = self.get_account_for_reset_password_token(token)
        password = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        account.password_hash = sha256(
            f"{password}{account.password_salt}".encode()
        ).hexdigest()
        # FIXME BS NOW: implement expiration
        account.reset_password_token = None
        self._kernel.server_db_session.add(account)
        self._kernel.server_db_session.commit()
        return password
