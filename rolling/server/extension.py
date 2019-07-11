# coding: utf-8
from hapic import Hapic
from sqlalchemy.ext.declarative import declarative_base

hapic = Hapic(async_=True)
ServerSideDocument = declarative_base()
ClientSideDocument = declarative_base()
