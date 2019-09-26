# coding: utf-8
from sqlalchemy.ext.declarative import declarative_base

from hapic import Hapic

hapic = Hapic(async_=True)
ServerSideDocument = declarative_base()
ClientSideDocument = declarative_base()
