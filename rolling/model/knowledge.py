# coding: utf-8
import dataclasses
import typing

DEFAULT_INSTRUCTOR_COEFF = 2.0


@dataclasses.dataclass
class KnowledgeDescription:
    id: str
    name: str
    ap_required: float
    instructor_coeff: float
    abilities: typing.List[str]
