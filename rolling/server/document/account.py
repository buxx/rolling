# coding: utf-8
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey

from rolling.server.extension import ServerSideDocument as Document


class AccountDocument(Document):
    __tablename__ = "account"
    id = Column(String(255), primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_salt = Column(String(32), nullable=False)
    password_hash = Column(String(255), nullable=True)
    email_verified = Column(Boolean(), default=False)
    current_character_id = Column(String(255), nullable=True)
    reset_password_token = Column(String(255), nullable=True)
    reset_password_expire = Column(Integer, nullable=True)


class AccountAuthTokenDocument(Document):
    __tablename__ = "account_token"
    account_id = Column(String(255), ForeignKey("account.id"), nullable=False)
    authentication_token = Column(String(32), primary_key=True)
    authentication_expire = Column(Integer(), nullable=False)
