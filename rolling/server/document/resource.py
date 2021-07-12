# coding: utf-8
from sqlalchemy import Column, UniqueConstraint, Boolean
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String

from rolling.model.measure import Unit
from rolling.server.extension import ServerSideDocument as Document


# FIXME BS: id, unit pas utilisés
class ResourceDocument(Document):
    __tablename__ = "resource"
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(255), nullable=False)
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)

    # properties
    unit = Column(Enum(*[u.value for u in Unit], name="resource__unit"), nullable=True)
    quantity = Column(Numeric(12, 6, asdecimal=False), nullable=False)

    # relations
    carried_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    in_built_id = Column(Integer, ForeignKey("build.id"), nullable=True)
    shared_with_affinity_id = Column(Integer, ForeignKey("affinity.id"), nullable=True)


class ZoneResourceDocument(Document):
    __tablename__ = "zone_resource"
    __table_args__ = (
        UniqueConstraint(
            'world_col_i',
            'world_row_i',
            'zone_col_i',
            'zone_row_i',
            'resource_id',
            name='zone_resource_unique'
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    world_col_i = Column(Integer, nullable=False)
    world_row_i = Column(Integer, nullable=False)
    zone_col_i = Column(Integer, nullable=False)
    zone_row_i = Column(Integer, nullable=False)
    resource_id = Column(String(255), nullable=False)

    # properties
    quantity = Column(Numeric(24, 6, asdecimal=False), nullable=False)
    destroy_tile_when_empty = Column(Boolean(), nullable=False)


# FIXME BS NOW floor:
# * FAIT commande d'init des ressources par rapport aux tuiles
# * FAIT (a tester) collect: reduction zone ress et remplacement de la tuile lorsque vide
# * event: tuile remplacement
# * FAIT constructions : que sur tuile qui authorise (et suppression de la tuile)
