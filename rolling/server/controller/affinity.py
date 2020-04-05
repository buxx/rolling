#  coding: utf-8
import json
from json import JSONDecodeError
import typing
import urllib

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic import HapicData

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.exception import RollingError
from rolling.kernel import Kernel
from rolling.model.character import GetAffinityPathModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import ManageAffinityQueryModel
from rolling.model.character import ModifyAffinityRelationQueryModel
from rolling.server.controller.base import BaseController
from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityJoinType
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.affinity import affinity_join_str
from rolling.server.extension import hapic


class AffinityController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def main_page(self, request: Request, hapic_data: HapicData) -> Description:
        affiliated_parts = []
        for relation, affinity in self._kernel.affinity_lib.get_with_relation(
            character_id=hapic_data.path.character_id
        ):
            rel_str = ""
            if relation.accepted:
                rel_str = dict(json.loads(affinity.statuses))[relation.status_id]
            elif relation.rejected:
                rel_str = "Quitté"
            elif relation.disallowed:
                rel_str = "Exclu"
            elif relation.request:
                rel_str = "Demandé"
            elif not relation.accepted and not relation.request and not relation.fighter:
                rel_str = "Plus de lien"
            if relation.fighter:
                if rel_str:
                    rel_str = f"{rel_str}, Combattant"
                else:
                    rel_str = "Combattant"
            rel_str = f"({rel_str})" if rel_str else ""
            affiliated_parts.append(
                Part(
                    is_link=True,
                    form_action=f"/affinity/{hapic_data.path.character_id}/see/{affinity.id}",
                    label=f"{affinity.name} {rel_str}",
                )
            )

        return Description(
            title="Affinités",
            items=[
                Part(
                    text="Les affinités permettent d'exprimer à quelles communautés se rattache "
                    "votre personnage."
                ),
                Part(
                    label="Créer une affinité",
                    is_link=True,
                    form_action=f"/affinity/{hapic_data.path.character_id}/new",
                ),
                Part(
                    label="Rejoindre une affinité",
                    is_link=True,
                    form_action=f"/affinity/{hapic_data.path.character_id}/list",
                ),
                Part(text="Ci-dessous les affinités avec lesquelles vous etes affiliés"),
            ]
            + affiliated_parts,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def list(self, request: Request, hapic_data: HapicData) -> Description:
        non_affiliated_parts = []
        for affinity in self._kernel.affinity_lib.get_without_relation(
            character_id=hapic_data.path.character_id
        ):
            non_affiliated_parts.append(
                Part(
                    is_link=True,
                    form_action=f"/affinity/{hapic_data.path.character_id}/see/{affinity.id}",
                    label=affinity.name,
                )
            )

        return Description(
            title="Affinités existantes",
            items=[
                Part(text="Ci-dessous, les affinités pour lesquelles vous n'avez aucune relation.")
            ]
            + non_affiliated_parts,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def new(self, request: Request, hapic_data: HapicData) -> Description:
        try:
            data = await request.json()
        except JSONDecodeError:
            data = {}

        if data.get("name"):
            affinity_doc = self._kernel.affinity_lib.create(
                name=data["name"],
                join_type=AffinityJoinType.ONE_CHIEF_ACCEPT,
                direction_type=AffinityDirectionType.ONE_DIRECTOR,
                commit=True,
            )
            self._kernel.affinity_lib.join(
                character_id=hapic_data.path.character_id,
                affinity_id=affinity_doc.id,
                accepted=True,
                status_id=CHIEF_STATUS[0],
                fighter=True,
                commit=True,
            )
            return Description(
                title="Affinités créée",
                items=[Part(text="Et vous en êtes le chef"), Part(is_link=True, go_back_zone=True)],
            )

        return Description(
            title="Créer une affinité",
            items=[
                Part(
                    is_form=True,
                    form_action=f"/affinity/{hapic_data.path.character_id}/new",
                    items=[Part(label="Nom", name="name", type_=Type.STRING)],
                )
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetAffinityPathModel)
    @hapic.output_body(Description)
    async def see(self, request: Request, hapic_data: HapicData) -> Description:
        affinity = self._kernel.affinity_lib.get_affinity(hapic_data.path.affinity_id)
        relation = self._kernel.affinity_lib.get_character_relation(
            affinity_id=hapic_data.path.affinity_id, character_id=hapic_data.path.character_id
        )
        member_count = self._kernel.affinity_lib.count_members(hapic_data.path.affinity_id)
        fighter_count = self._kernel.affinity_lib.count_members(
            hapic_data.path.affinity_id, fighter=True
        )

        parts = []
        edit_relation_url = (
            f"/affinity/{hapic_data.path.character_id}/edit-relation/{hapic_data.path.affinity_id}"
        )
        if relation:
            fighter_str = ""
            if relation.fighter:
                fighter_str = " (Vous vous battez pour elle)"

            status_str = (
                dict(json.loads(affinity.statuses))[relation.status_id]
                if relation.status_id
                else ""
            )
            if relation.accepted:
                parts.append(
                    Part(
                        label=(
                            f"Vous êtes membre de cette affinité et vous portez le status "
                            f"de {status_str}{fighter_str}"
                        ),
                        is_link=True,
                        form_action=edit_relation_url,
                    )
                )
            elif relation.request:
                parts.append(
                    Part(
                        label=f"Vous avez demandé à être membre de cette affinité{fighter_str}",
                        is_link=True,
                        form_action=edit_relation_url,
                    )
                )
            elif relation.rejected:
                parts.append(
                    Part(
                        label=f"Vous avez renié cette affinité{fighter_str}",
                        is_link=True,
                        form_action=edit_relation_url,
                    )
                )
            elif relation.disallowed:
                parts.append(
                    Part(
                        label=f"Vous avez été rejeté de cette affinité{fighter_str}",
                        is_link=True,
                        form_action=edit_relation_url,
                    )
                )
            elif relation.fighter:
                parts.append(
                    Part(
                        label="Vous combattez pour cette affinité",
                        is_link=True,
                        form_action=edit_relation_url,
                    )
                )
            else:
                parts.append(
                    Part(
                        label="Vous n'avez plus aucune relation avec cette affinité",
                        is_link=True,
                        form_action=edit_relation_url,
                    )
                )
        else:
            parts.append(
                Part(
                    label="Vous n'avez aucune relation avec cette affinité",
                    is_link=True,
                    form_action=edit_relation_url,
                )
            )

        # can access management page ?
        if affinity.direction_type == AffinityDirectionType.ONE_DIRECTOR.value:
            if relation and relation.status_id == CHIEF_STATUS[0]:
                parts.append(
                    Part(
                        label="Gérer cette affinité",
                        is_link=True,
                        form_action=f"/affinity/{hapic_data.path.character_id}/manage/{affinity.id}",
                    )
                )

        return Description(
            title=affinity.name,
            items=[
                Part(text=affinity.description),
                Part(
                    text=f"D'après les dires, cette affinité compte {member_count} membre(s) "
                    f"dont {fighter_count} prêt(s) à se battre. Pour plus de renseignements "
                    f"sur ces personnes dans la zone où se trouve votre personnage, "
                    f"rendez-vous sur la page de la zone."
                ),
            ]
            + parts,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetAffinityPathModel)
    @hapic.input_query(ModifyAffinityRelationQueryModel)
    @hapic.output_body(Description)
    async def edit_relation(self, request: Request, hapic_data: HapicData) -> Description:
        affinity = self._kernel.affinity_lib.get_affinity(hapic_data.path.affinity_id)
        relation = self._kernel.affinity_lib.get_character_relation(
            affinity_id=hapic_data.path.affinity_id, character_id=hapic_data.path.character_id
        )

        if (
            hapic_data.query.request is not None
            or hapic_data.query.rejected is not None
            or hapic_data.query.fighter is not None
        ):
            title = "ERROR"
            return_ = False
            if hapic_data.query.request and relation:
                title = f"Requete pour etre membre de {affinity.name} exprimé"
                if affinity.join_type == AffinityJoinType.ACCEPT_ALL and not (
                    relation.disallowed or relation.rejected
                ):
                    relation.accepted = True
                else:
                    relation.request = True
                return_ = True
            elif hapic_data.query.request == 0 and relation:
                title = f"Vous ne demandez plus à être membre de {affinity.name}"
                relation.request = False
                return_ = True
            elif hapic_data.query.request and not relation:
                title = f"Requete pour etre membre de {affinity.name} exprimé"
                self._kernel.affinity_lib.join(
                    character_id=hapic_data.path.character_id,
                    affinity_id=hapic_data.path.affinity_id,
                    accepted=True if affinity.join_type == AffinityJoinType.ACCEPT_ALL else False,
                    fighter=True if hapic_data.query.fighter else False,
                    request=True,
                )
                return_ = True
            elif hapic_data.query.rejected and not relation:
                pass  # should not be here
            elif hapic_data.query.rejected and relation:
                title = f"Vous avez déclaré avoir abandonné {affinity.name}"
                relation.accepted = False
                relation.request = False
                relation.rejected = True
                return_ = True
            elif hapic_data.query.fighter and not relation:
                title = f"Vous vous battez désormais pour {affinity.name}"
                self._kernel.affinity_lib.join(
                    character_id=hapic_data.path.character_id,
                    affinity_id=hapic_data.path.affinity_id,
                    accepted=True if affinity.join_type == AffinityJoinType.ACCEPT_ALL else False,
                    fighter=True,
                    request=False,
                )
                return_ = True
            elif hapic_data.query.fighter and relation:
                title = (
                    f"Vous combatrez désormais dès lors qu'un membre de"
                    f" {affinity.name} sera attaqué"
                )
                relation.fighter = True
                return_ = True
            elif hapic_data.query.fighter == 0:
                title = (
                    f"Vous ne combatrez désormais plus lorsqu'un membre de"
                    f" {affinity.name} sera attaqué"
                )
                relation.fighter = False
                return_ = True

            if return_:
                self._kernel.server_db_session.commit()
                return Description(title=title, items=[Part(is_link=True, go_back_zone=True)])

        items = []

        # FIXME BS: Must be in presence of director to request become member
        if not relation:
            items.extend(
                [
                    Part(
                        is_link=True,
                        form_action=(
                            f"/affinity/{hapic_data.path.character_id}"
                            f"/edit-relation/{hapic_data.path.affinity_id}"
                            f"?request=1"
                        ),
                        label="Exprimer le souhait de devenir membre",
                    ),
                    Part(
                        is_link=True,
                        form_action=(
                            f"/affinity/{hapic_data.path.character_id}"
                            f"/edit-relation/{hapic_data.path.affinity_id}"
                            f"?request=1&fighter=1"
                        ),
                        label="Exprimer le souhait de devenir membre et de me battre avec eux",
                    ),
                    Part(
                        is_link=True,
                        form_action=(
                            f"/affinity/{hapic_data.path.character_id}"
                            f"/edit-relation/{hapic_data.path.affinity_id}"
                            f"?request=0&fighter=1"
                        ),
                        label="Exprimer le souhait de me battre pour eux",
                    ),
                ]
            )
        else:
            if not relation.request:
                if not relation.fighter:
                    items.append(
                        Part(
                            is_link=True,
                            form_action=(
                                f"/affinity/{hapic_data.path.character_id}"
                                f"/edit-relation/{hapic_data.path.affinity_id}"
                                f"?request=1&fighter=1"
                            ),
                            label="Exprimer le souhait de devenir membre et de me battre pour elle",
                        )
                    )
                else:
                    items.append(
                        Part(
                            is_link=True,
                            form_action=(
                                f"/affinity/{hapic_data.path.character_id}"
                                f"/edit-relation/{hapic_data.path.affinity_id}"
                                f"?request=1"
                            ),
                            label="Exprimer le souhait de devenir membre",
                        )
                    )
            else:
                items.append(
                    Part(
                        is_link=True,
                        form_action=(
                            f"/affinity/{hapic_data.path.character_id}"
                            f"/edit-relation/{hapic_data.path.affinity_id}"
                            f"?request=0"
                        ),
                        label="Ne plus demander à être membre",
                    )
                )
            if relation.accepted:
                items.append(
                    Part(
                        is_link=True,
                        form_action=(
                            f"/affinity/{hapic_data.path.character_id}"
                            f"/edit-relation/{hapic_data.path.affinity_id}"
                            f"?rejected=1"
                        ),
                        label="Quitter cette affinité",
                    )
                )
            if relation.fighter:
                items.append(
                    Part(
                        is_link=True,
                        form_action=(
                            f"/affinity/{hapic_data.path.character_id}"
                            f"/edit-relation/{hapic_data.path.affinity_id}"
                            f"?fighter=0"
                        ),
                        label="Ne plus se battre pour cette affinité",
                    )
                )
            else:
                items.append(
                    Part(
                        is_link=True,
                        form_action=(
                            f"/affinity/{hapic_data.path.character_id}"
                            f"/edit-relation/{hapic_data.path.affinity_id}"
                            f"?fighter=1"
                        ),
                        label="Me battre pour cette affinité",
                    )
                )

        return Description(title=affinity.name, items=items)

    @hapic.with_api_doc()
    @hapic.input_path(GetAffinityPathModel)
    @hapic.input_query(ManageAffinityQueryModel)
    @hapic.output_body(Description)
    async def manage(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO BS: only chief (or ability) can display this
        affinity = self._kernel.affinity_lib.get_affinity(hapic_data.path.affinity_id)
        relation = self._kernel.affinity_lib.get_character_relation(
            affinity_id=hapic_data.path.affinity_id, character_id=hapic_data.path.character_id
        )

        if hapic_data.query.join_type == affinity_join_str[AffinityJoinType.ACCEPT_ALL]:
            request_relations = (
                self._kernel.server_db_session.query(AffinityRelationDocument)
                .filter(
                    AffinityRelationDocument.request == True,
                    AffinityRelationDocument.accepted == False,
                    AffinityRelationDocument.affinity_id == affinity.id,
                )
                .all()
            )
            if len(request_relations) and not hapic_data.query.confirm:
                return Description(
                    title=affinity.name,
                    items=[
                        Part(
                            text=f'Choisir "{hapic_data.query.join_type}" '
                            f"acceptera automatiquement {len(request_relations)} demande(s) "
                            f"en attente"
                        ),
                        Part(
                            label="Confirmer",
                            is_link=True,
                            form_action=f"/affinity/{hapic_data.path.character_id}"
                            f"/manage/{affinity.id}"
                            f"?join_type={urllib.parse.quote(hapic_data.query.join_type)}"
                            f"&confirm=1",
                        ),
                        Part(
                            label="Annuler",
                            is_link=True,
                            form_action=f"/affinity/{hapic_data.path.character_id}"
                            f"/manage/{affinity.id}",
                        ),
                    ],
                )

        # proceed submited data
        if hapic_data.query.join_type is not None:
            join_type = list(affinity_join_str.keys())[
                list(affinity_join_str.values()).index(hapic_data.query.join_type)
            ]

            # TODO BS: code it
            if join_type not in [AffinityJoinType.ACCEPT_ALL, AffinityJoinType.ONE_CHIEF_ACCEPT]:
                raise RollingError("Cette fonctionnalite n'est pas encore disponible")

            if join_type == AffinityJoinType.ACCEPT_ALL:
                self._kernel.server_db_session.query(AffinityRelationDocument).filter(
                    AffinityRelationDocument.request == True,
                    AffinityRelationDocument.accepted == False,
                    AffinityRelationDocument.affinity_id == affinity.id,
                ).update({"accepted": True, "request": False})

            affinity.join_type = join_type.value
            self._kernel.server_db_session.add(affinity)
            self._kernel.server_db_session.commit()
            return Description(
                redirect=f"/affinity/{hapic_data.path.character_id}/manage/{affinity.id}"
            )

        join_values = [
            affinity_join_str[AffinityJoinType.ACCEPT_ALL],
            affinity_join_str[AffinityJoinType.ONE_CHIEF_ACCEPT],
            affinity_join_str[AffinityJoinType.HALF_STATUS_ACCEPT],
        ]

        request_count = (
            self._kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.affinity_id == affinity.id,
                AffinityRelationDocument.accepted == False,
                AffinityRelationDocument.request == True,
            )
            .count()
        )
        parts = [
            Part(
                label=f"Il y a actuellement {request_count} demande(s) d'adhésion",
                is_link=bool(request_count),
                form_action=(
                    f"/affinity/{hapic_data.path.character_id}/manage-requests/{affinity.id}"
                ),
            )
        ]

        return Description(
            title=f"Administration de {affinity.name}",
            items=[
                Part(
                    is_form=True,
                    form_values_in_query=True,
                    submit_label="Enregistrer",
                    form_action=f"/affinity/{hapic_data.path.character_id}/manage/{affinity.id}",
                    items=[
                        Part(
                            label="Mode d'admission des nouveaux membres",
                            choices=join_values,
                            name="join_type",
                            value=affinity_join_str[AffinityJoinType(affinity.join_type)],
                        )
                    ],
                )
            ]
            + parts,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetAffinityPathModel)
    @hapic.output_body(Description)
    async def manage_requests(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO BS: only chief (or ability) can display this
        affinity = self._kernel.affinity_lib.get_affinity(hapic_data.path.affinity_id)
        relation = self._kernel.affinity_lib.get_character_relation(
            affinity_id=hapic_data.path.affinity_id, character_id=hapic_data.path.character_id
        )
        requests: typing.List[AffinityRelationDocument] = self._kernel.server_db_session.query(
            AffinityRelationDocument
        ).filter(
            AffinityRelationDocument.affinity_id == affinity.id,
            AffinityRelationDocument.accepted == False,
            AffinityRelationDocument.request == True,
        ).all()

        data = {}
        try:
            data = await request.json()
        except JSONDecodeError:
            pass

        request: AffinityRelationDocument
        if data:
            for request in list(requests):
                choose = data.get(request.character_id)
                if choose:
                    if choose == "Accepter":
                        request.accepted = True
                        request.request = False
                    elif choose == "Refuser":
                        request.accepted = False
                        request.request = False
                        request.disallowed = True

                    self._kernel.server_db_session.add(request)
                    self._kernel.server_db_session.commit()
                    requests.remove(request)

        form_parts = []
        for request in requests:
            character = self._kernel.character_lib.get_document(request.character_id)
            form_parts.append(
                Part(
                    label=f"{character.name}",
                    name=character.id,
                    choices=["Ne rien décider", "Accepter", "Refuser"],
                    value="Ne rien décider",
                )
            )

        return Description(
            title=f"Demande(s) d'adhésion pour {affinity.name}",
            items=[
                Part(
                    is_form=True,
                    submit_label="Enregistrer",
                    form_action=(
                        f"/affinity/{hapic_data.path.character_id}"
                        f"/manage-requests/{affinity.id}"
                    ),
                    items=form_parts,
                )
            ],
        )

    def bind(self, app: Application) -> None:
        url_base = "/affinity/{character_id}"
        app.add_routes(
            [
                web.post(url_base, self.main_page),
                web.post(url_base + "/new", self.new),
                web.post(url_base + "/list", self.list),
                web.post(url_base + "/see/{affinity_id}", self.see),
                web.post(url_base + "/edit-relation/{affinity_id}", self.edit_relation),
                web.post(url_base + "/manage/{affinity_id}", self.manage),
                web.post(url_base + "/manage-requests/{affinity_id}", self.manage_requests),
            ]
        )
