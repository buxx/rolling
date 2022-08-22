import datetime
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text


from rolling.server.extension import ServerSideDocument as Document


class SpawnPointDocument(Document):
    __tablename__ = "spawn"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # FIXME BS NOW : when build is destroy, delete spawn point
    build_id = Column(Integer(), ForeignKey("build.id"), nullable=False)
    # FIXME BS NOW : when build is destroy, delete spawn point
    affinity_id = Column(Integer(), ForeignKey("affinity.id"), nullable=False)
