# coding: utf-8
from decimal import Decimal as D
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import cast
import sqlalchemy.types as types

from rolling.server.extension import ServerSideDocument as Document


class SqliteNumeric(types.TypeDecorator):
    impl = types.String

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(types.VARCHAR(100))

    def process_bind_param(self, value, dialect):
        return str(value)

    def process_result_value(self, value, dialect):
        return D(value)

    def column_expression(self, col):
        return cast(col, Float)


class ImageDocument(Document):
    __tablename__ = "image"
    id = Column(Integer, primary_key=True, autoincrement=True)
    extension = Column(String, nullable=False)
    checksum = Column(String, unique=True)
