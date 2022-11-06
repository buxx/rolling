import configparser
from alembic import context
from rolling.server.extension import ServerSideDocument
from sqlalchemy.engine import create_engine

from rolling.server.document.account import *
from rolling.server.document.action import *
from rolling.server.document.affinity import *
from rolling.server.document.base import *
from rolling.server.document.build import *
from rolling.server.document.business import *
from rolling.server.document.character import *
from rolling.server.document.corpse import *
from rolling.server.document.event import *
from rolling.server.document.knowledge import *
from rolling.server.document.message import *
from rolling.server.document.resource import *
from rolling.server.document.skill import *
from rolling.server.document.stuff import *
from rolling.server.document.universe import *
from rolling.server.document.spawn import *

target_metadata = ServerSideDocument.metadata


def main():
    config = configparser.ConfigParser()
    config.read("./server.ini")

    server_db_user = config["default"]["db_user"]
    server_db_name = config["default"]["db_name"]
    server_db_host = config["default"]["db_address"]
    server_db_password = config["default"]["db_password"]

    engine = create_engine(
        "postgresql+psycopg2://"
        f"{server_db_user}:{server_db_password}@{server_db_host}"
        f"/{server_db_name}"
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


main()
