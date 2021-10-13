# coding: utf-8
from aiohttp.test_utils import TestClient
import pytest
import serpyco
import urllib

from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityJoinType
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.affinity import MEMBER_STATUS
from rolling.server.document.affinity import WARLORD_STATUS
from rolling.server.document.affinity import affinity_join_str
from rolling.server.document.affinity import statuses
from tests.utils import extract_description_properties
from tests.utils import in_one_of


class TestAffinity:
    async def test_unit__create_affinity__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        #  reation page affinity
        resp = await web.post(f"/affinity/{xena.id}/new")
        descr = descr_serializer.load(await resp.json())
        assert descr.items[0].is_form
        assert "/affinity/xena/new" == descr.items[0].form_action
        assert "name" == descr.items[0].items[0].name

        # create affinity
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        affinity = kernel.server_db_session.query(AffinityDocument).one()
        assert "MyAffinity" == affinity.name
        assert "ONE_CHIEF_ACCEPT" == affinity.join_type
        assert "ONE_DIRECTOR" == affinity.direction_type
        assert (
            "["
            '["CHIEF_STATUS", "Chef"], '
            '["MEMBER_STATUS", "Membre"], '
            '["WARLORD_STATUS", "Seigneur de guerre"]'
            "]" == affinity.statuses
        )

        rel = kernel.server_db_session.query(AffinityRelationDocument).one()
        assert rel.accepted
        assert "xena" == rel.character_id
        assert not rel.disallowed
        assert rel.fighter
        assert not rel.rejected
        assert "CHIEF_STATUS" == rel.status_id

        # list affinity
        resp = await web.post(f"/affinity/{xena.id}")
        descr = descr_serializer.load(await resp.json())
        form_actions = extract_description_properties(descr.items, "form_action")
        assert "/affinity/xena/see/1" in form_actions
        assert "/affinity/xena/new" in form_actions
        labels = extract_description_properties(descr.items, "label")
        assert "MyAffinity (Chef, Combattant) 1|1" in labels

        # see affinity
        resp = await web.post(f"/affinity/{xena.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        texts = extract_description_properties(descr.items, "text")
        assert in_one_of("1 membre(s) dont 1 prêt(s) à se battre", texts)
        assert in_one_of(
            "Vous êtes membre de cette affinité et vous portez le status de Chef (Vous vous battez pour elle)",
            texts,
        )
        form_actions = extract_description_properties(descr.items, "form_action")
        assert "/affinity/xena/manage/1" in form_actions
        assert "/affinity/xena/edit-relation/1" in form_actions

    @pytest.mark.parametrize(
        "request_,fighter", [(False, True), (True, True), (True, False)]
    )
    async def test_unit__join_affinity__ok__as_non_member(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        request_: bool,
        fighter: bool,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel

        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})

        # list unknowns
        resp = await web.post(f"/affinity/{arthur.id}/list")
        descr = descr_serializer.load(await resp.json())
        labels = extract_description_properties(descr.items, "label")
        assert "MyAffinity" in labels
        assert "/affinity/arthur/see/1" == descr.items[1].form_action

        # display edit relation
        resp = await web.post(f"/affinity/{arthur.id}/edit-relation/{1}")
        descr = descr_serializer.load(await resp.json())

        assert (
            "/affinity/arthur/edit-relation/1?request=1" == descr.items[0].form_action
        )
        assert (
            "/affinity/arthur/edit-relation/1?request=1&fighter=1"
            == descr.items[1].form_action
        )
        assert (
            "/affinity/arthur/edit-relation/1?request=0&fighter=1"
            == descr.items[2].form_action
        )

        # make a request
        await web.post(
            f"/affinity/arthur/edit-relation/1?request={int(request_)}&fighter={int(fighter)}"
        )
        assert 2 == kernel.server_db_session.query(AffinityRelationDocument).count()
        rel = (
            kernel.server_db_session.query(AffinityRelationDocument)
            .filter(AffinityRelationDocument.character_id == "arthur")
            .one()
        )
        assert bool(request_) == rel.request
        assert not rel.accepted
        assert "arthur" == rel.character_id
        assert not rel.disallowed
        assert bool(fighter) == rel.fighter
        assert not rel.rejected
        assert "MEMBER_STATUS" == rel.status_id if request_ else not rel.status_id

        # edit relation page
        resp = await web.post(f"/affinity/{arthur.id}/edit-relation/{1}")
        descr = descr_serializer.load(await resp.json())
        if not request_ and fighter:
            assert "Exprimer le souhait de devenir membre" == descr.items[0].label
            assert (
                "/affinity/arthur/edit-relation/1?request=1"
                == descr.items[0].form_action
            )
            assert "Ne plus se battre pour cette affinité" == descr.items[1].label
            assert (
                "/affinity/arthur/edit-relation/1?fighter=0"
                == descr.items[1].form_action
            )
        elif request_ and fighter:
            assert "Ne plus demander à être membre" == descr.items[0].label
            assert (
                "/affinity/arthur/edit-relation/1?request=0"
                == descr.items[0].form_action
            )
            assert "Ne plus se battre pour cette affinité" == descr.items[1].label
            assert (
                "/affinity/arthur/edit-relation/1?fighter=0"
                == descr.items[1].form_action
            )
        elif request_ and not fighter:
            assert "Ne plus demander à être membre" == descr.items[0].label
            assert (
                "/affinity/arthur/edit-relation/1?request=0"
                == descr.items[0].form_action
            )
            assert "Me battre pour cette affinité" == descr.items[1].label
            assert (
                "/affinity/arthur/edit-relation/1?fighter=1"
                == descr.items[1].form_action
            )

        # list affinities
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        form_actions = extract_description_properties(descr.items, "form_action")
        assert "/affinity/arthur/see/1" in form_actions

        expected_str = ""
        if fighter and request_:
            expected_str = " (Demandé, Combattant)"
        if fighter and not request_:
            expected_str = " (Combattant)"
        if not fighter and request_:
            expected_str = " (Demandé)"
        labels = extract_description_properties(descr.items, "label")
        assert f"MyAffinity{expected_str} 1|1" in labels

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"{1 if not fighter else 2} prêt(s)" in descr.items[1].text
        form_actions = extract_description_properties(descr.items, "form_action")
        assert "/affinity/arthur/edit-relation/1" in form_actions

        if request_:
            # accept him
            rel.accepted = True
            rel.status_id = "MEMBER_STATUS"
            kernel.server_db_session.commit()

            # list affinities
            resp = await web.post(f"/affinity/{arthur.id}")
            descr = descr_serializer.load(await resp.json())
            expected_str = ""
            if fighter:
                expected_str = " (Membre, Combattant)"
            if not fighter:
                expected_str = " (Membre)"
            labels = extract_description_properties(descr.items, "label")
            assert f"MyAffinity{expected_str} 2|2" in labels

            # see affinity
            resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
            descr = descr_serializer.load(await resp.json())
            assert "MyAffinity" == descr.title
            assert "2 membre(s)" in descr.items[1].text
            assert f"{1 if not fighter else 2} prêt(s)" in descr.items[1].text

    @pytest.mark.parametrize(
        "disallowed,rejected", [(False, True), (True, False), (True, True)]
    )
    async def test_unit__join_affinity__ok__as_old_member(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        disallowed: bool,
        rejected: bool,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel

        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        affinity: AffinityDocument = kernel.server_db_session.query(
            AffinityDocument
        ).one()
        affinity.join_type = AffinityJoinType.ACCEPT_ALL.value
        kernel.server_db_session.add(affinity)
        kernel.server_db_session.add(
            AffinityRelationDocument(
                character_id=arthur.id,
                affinity_id=affinity.id,
                disallowed=disallowed,
                rejected=rejected,
            )
        )
        kernel.server_db_session.commit()

        # make a join request
        resp = await web.post(
            f"/affinity/{arthur.id}/edit-relation/{affinity.id}?request=1"
        )
        assert 200 == resp.status

        arthur_relation: AffinityRelationDocument = (
            kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.affinity_id == affinity.id,
                AffinityRelationDocument.character_id == arthur.id,
            )
            .one()
        )
        assert not arthur_relation.accepted

    @pytest.mark.parametrize("fighter", [True, False])
    async def test_unit__reject_affinity__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        fighter: bool,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        await web.post(
            f"/affinity/arthur/edit-relation/1?request=1&fighter={int(fighter)}"
        )

        # disallow
        resp = await web.post(
            f"/affinity/arthur/edit-relation/1?rejected=1&fighter={int(fighter)}"
        )
        descr = descr_serializer.load(await resp.json())
        assert "Vous avez déclaré avoir abandonné MyAffinity" == descr.title
        rel = (
            kernel.server_db_session.query(AffinityRelationDocument)
            .filter(AffinityRelationDocument.character_id == "arthur")
            .one()
        )
        assert not rel.accepted
        assert rel.rejected
        assert not rel.disallowed

        # display main
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        if fighter:
            expected_str = " (Quitté, Combattant)"
        else:
            expected_str = " (Quitté)"
        labels = extract_description_properties(descr.items, "label")
        assert f"MyAffinity{expected_str} 1|1" in labels

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"{2 if fighter else 1} prêt(s)" in descr.items[1].text
        form_actions = extract_description_properties(descr.items, "form_action")
        assert "/affinity/arthur/edit-relation/1" in form_actions

    @pytest.mark.parametrize("fighter", [True, False])
    async def test_unit__discard_request__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        fighter: bool,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        await web.post(
            f"/affinity/arthur/edit-relation/1?request=1&fighter={int(fighter)}"
        )

        # discard
        resp = await web.post(
            f"/affinity/arthur/edit-relation/1?request=0&fighter={int(fighter)}"
        )
        descr = descr_serializer.load(await resp.json())
        assert "Vous ne demandez plus à être membre de MyAffinity" == descr.title

        # display main
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        form_actions = extract_description_properties(descr.items, "form_action")
        assert "/affinity/arthur/see/1" in form_actions
        if fighter:
            expected_str = " (Combattant)"
        else:
            expected_str = " (Plus de lien)"
        labels = extract_description_properties(descr.items, "label")
        assert f"MyAffinity{expected_str} 1|1" in labels

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"{2 if fighter else 1} prêt(s)" in descr.items[1].text
        form_actions = extract_description_properties(descr.items, "form_action")
        assert "/affinity/arthur/edit-relation/1" in form_actions

        # re do request
        resp = await web.post(
            f"/affinity/arthur/edit-relation/1?request=1&fighter={int(fighter)}"
        )
        descr = descr_serializer.load(await resp.json())
        assert "Requete pour etre membre de MyAffinity exprimé" == descr.title

        # list affinities
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        form_actions = extract_description_properties(descr.items, "form_action")
        assert "/affinity/arthur/see/1" in form_actions
        if fighter:
            expected_str = " (Demandé, Combattant)"
        else:
            expected_str = " (Demandé)"
        labels = extract_description_properties(descr.items, "label")
        assert f"MyAffinity{expected_str} 1|1" in labels

    async def test_unit__only_fight_for_ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})

        resp = await web.post(f"/affinity/arthur/edit-relation/1?fighter=1")
        descr = descr_serializer.load(await resp.json())
        assert "Vous vous battez désormais pour MyAffinity" == descr.title

        # display main
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        labels = extract_description_properties(descr.items, "label")
        assert f"MyAffinity (Combattant) 1|1" in labels

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"2 prêt(s)" in descr.items[1].text

        resp = await web.post(f"/affinity/arthur/edit-relation/1?fighter=0")
        descr = descr_serializer.load(await resp.json())
        assert (
            "Vous ne combatrez désormais plus lorsqu'un membre de MyAffinity sera attaqué"
            == descr.title
        )

        # display main
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"1 prêt(s)" in descr.items[1].text

    async def test_unit__manage_ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})

        affinity: AffinityDocument = kernel.server_db_session.query(
            AffinityDocument
        ).one()
        assert affinity.join_type == AffinityJoinType.ONE_CHIEF_ACCEPT.value
        assert affinity.direction_type == AffinityDirectionType.ONE_DIRECTOR.value

        # display manage page
        resp = await web.post(f"/affinity/{xena.id}/manage/{affinity.id}")
        descr = descr_serializer.load(await resp.json())

        assert "/affinity/xena/manage/1" == descr.items[0].form_action
        assert descr.items[0].items[0].choices
        assert (
            affinity_join_str[AffinityJoinType.ONE_CHIEF_ACCEPT]
            == descr.items[0].items[0].value
        )
        for choice in [
            affinity_join_str[AffinityJoinType.ACCEPT_ALL],
            affinity_join_str[AffinityJoinType.ONE_CHIEF_ACCEPT],
            affinity_join_str[AffinityJoinType.HALF_STATUS_ACCEPT],
        ]:
            assert choice in descr.items[0].items[0].choices

        # change to accept all
        resp = await web.post(
            f"/affinity/{xena.id}/manage/{affinity.id}"
            f"?join_type={urllib.parse.quote(affinity_join_str[AffinityJoinType.ACCEPT_ALL])}"
        )
        resp = await web.post(f"/affinity/{xena.id}/manage/{affinity.id}")
        descr = descr_serializer.load(await resp.json())

        affinity: AffinityDocument = kernel.server_db_session.query(
            AffinityDocument
        ).one()
        assert affinity.join_type == AffinityJoinType.ACCEPT_ALL.value
        assert affinity.direction_type == AffinityDirectionType.ONE_DIRECTOR.value
        assert (
            affinity_join_str[AffinityJoinType.ACCEPT_ALL]
            == descr.items[0].items[0].value
        )

        # change to one chief accept
        resp = await web.post(
            f"/affinity/{xena.id}/manage/{affinity.id}"
            f"?join_type={urllib.parse.quote(affinity_join_str[AffinityJoinType.ONE_CHIEF_ACCEPT])}"
        )
        resp = await web.post(f"/affinity/{xena.id}/manage/{affinity.id}")
        descr = descr_serializer.load(await resp.json())

        affinity: AffinityDocument = kernel.server_db_session.query(
            AffinityDocument
        ).one()
        assert affinity.join_type == AffinityJoinType.ONE_CHIEF_ACCEPT.value
        assert affinity.direction_type == AffinityDirectionType.ONE_DIRECTOR.value
        assert (
            affinity_join_str[AffinityJoinType.ONE_CHIEF_ACCEPT]
            == descr.items[0].items[0].value
        )

    async def test_unit__manage_ok__to_accept_all_with_requests(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})

        affinity: AffinityDocument = kernel.server_db_session.query(
            AffinityDocument
        ).one()
        assert affinity.join_type == AffinityJoinType.ONE_CHIEF_ACCEPT.value
        assert affinity.direction_type == AffinityDirectionType.ONE_DIRECTOR.value

        # display manage page
        resp = await web.post(f"/affinity/{xena.id}/manage/{affinity.id}")
        descr = descr_serializer.load(await resp.json())

        # Insert one pending request
        kernel.server_db_session.add(
            AffinityRelationDocument(
                character_id=arthur.id, affinity_id=affinity.id, request=True
            )
        )
        kernel.server_db_session.commit()

        resp = await web.post(
            f"/affinity/{xena.id}/manage/{affinity.id}"
            f"?join_type={urllib.parse.quote(affinity_join_str[AffinityJoinType.ACCEPT_ALL])}"
        )
        descr = descr_serializer.load(await resp.json())

        item_urls = [i.form_action for i in descr.items]
        confirm_url = (
            f"/affinity/xena/manage/1"
            f"?join_type={urllib.parse.quote(affinity_join_str[AffinityJoinType.ACCEPT_ALL])}&confirm=1"
        )
        assert confirm_url in item_urls
        assert "/affinity/xena/manage/1" in item_urls

        resp = await web.post(confirm_url)
        arthur_relation = (
            kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.character_id == arthur.id,
                AffinityRelationDocument.affinity_id == affinity.id,
            )
            .one()
        )
        assert arthur_relation.accepted

    @pytest.mark.parametrize("accept", [True, False])
    async def test_unit__join_with_type_one_chief_ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        accept: bool,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        affinity: AffinityDocument = kernel.server_db_session.query(
            AffinityDocument
        ).one()
        affinity.direction_type = AffinityDirectionType.ONE_DIRECTOR.value
        kernel.server_db_session.add(affinity)
        kernel.server_db_session.commit()

        # manage page display "0" requests
        resp = await web.post(f"/affinity/{xena.id}/manage/{affinity.id}")
        descr = descr_serializer.load(await resp.json())

        item_urls = [i.form_action for i in descr.items]
        item_labels = [i.label for i in descr.items]
        assert "/affinity/xena/manage-requests/1" in item_urls
        assert "Il y a actuellement 0 demande(s) d'adhésion" in item_labels
        # no signal to vote for xena
        character_model = kernel.character_lib.get(
            xena.id, compute_unvote_affinity_relation=True
        )
        assert not character_model.unvote_affinity_relation

        # make an request for arthur
        kernel.server_db_session.add(
            AffinityRelationDocument(
                character_id=arthur.id,
                affinity_id=affinity.id,
                request=True,
                accepted=False,
            )
        )
        kernel.server_db_session.commit()

        # manage page display "1" requests
        resp = await web.post(f"/affinity/{xena.id}/manage/{affinity.id}")
        descr = descr_serializer.load(await resp.json())

        item_urls = [i.form_action for i in descr.items]
        item_labels = [i.label for i in descr.items]
        assert "/affinity/xena/manage-requests/1" in item_urls
        assert "Il y a actuellement 1 demande(s) d'adhésion" in item_labels
        # have signal to vote for xena
        character_model = kernel.character_lib.get(
            xena.id, compute_unvote_affinity_relation=True
        )
        assert character_model.unvote_affinity_relation

        # on affinity list, affinity is blinking
        resp = await web.post(f"/affinity/{xena.id}")
        descr = descr_serializer.load(await resp.json())
        labels = extract_description_properties(descr.items, "label")
        assert "MyAffinity (Chef, Combattant) 1|1" in labels
        # on see affinity, link blinking
        resp = await web.post(f"/affinity/{xena.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "*Gérer cette affinité" in [i.label for i in descr.items]

        # display manage requests
        resp = await web.post(f"/affinity/{xena.id}/manage-requests/{affinity.id}")
        descr = descr_serializer.load(await resp.json())

        assert (
            f"/affinity/{xena.id}/manage-requests/{affinity.id}"
            == descr.items[0].form_action
        )
        assert arthur.id == descr.items[0].items[1].name
        assert ["Ne rien décider", "Accepter", "Refuser"] == descr.items[0].items[
            1
        ].choices

        # Accept arthur
        resp = await web.post(
            f"/affinity/{xena.id}/manage-requests/{affinity.id}",
            json={arthur.id: "Accepter" if accept else "Refuser"},
        )
        assert 200 == resp.status

        # manage page display "0" requests
        resp = await web.post(f"/affinity/{xena.id}/manage/{affinity.id}")
        descr = descr_serializer.load(await resp.json())
        item_labels = [i.label for i in descr.items]
        assert "Il y a actuellement 0 demande(s) d'adhésion" in item_labels

        # display manage requests: no more requests
        resp = await web.post(f"/affinity/{xena.id}/manage-requests/{affinity.id}")
        descr = descr_serializer.load(await resp.json())
        assert not descr.items[0].items

        arthur_relation: AffinityRelationDocument = (
            kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.affinity_id == affinity.id,
                AffinityRelationDocument.character_id == arthur.id,
            )
            .one()
        )
        assert accept == arthur_relation.accepted
        assert not arthur_relation.request

    @pytest.mark.parametrize("to_status_str", [CHIEF_STATUS[1], WARLORD_STATUS[1]])
    async def test_unit__change_member_status__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        to_status_str: str,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        affinity: AffinityDocument = kernel.server_db_session.query(
            AffinityDocument
        ).one()
        affinity.direction_type = AffinityDirectionType.ONE_DIRECTOR.value
        kernel.server_db_session.add(affinity)
        kernel.server_db_session.add(
            AffinityRelationDocument(
                character_id=arthur.id,
                affinity_id=affinity.id,
                accepted=True,
                status_id=MEMBER_STATUS[0],
            )
        )
        kernel.server_db_session.commit()

        # display manage relation page
        resp = await web.post(
            f"/affinity/{xena.id}/manage-relations/{affinity.id}/{arthur.id}"
        )
        assert 200 == resp.status
        descr = descr_serializer.load(await resp.json())

        item_urls = [i.form_action for i in descr.items]
        assert (
            f"/affinity/{xena.id}/manage-relations/{affinity.id}/{arthur.id}?disallowed=1"
            in item_urls
        )
        assert descr.items[1].is_form
        assert "status" == descr.items[1].items[0].name
        assert ["Chef", "Membre", "Seigneur de guerre"] == descr.items[1].items[
            0
        ].choices
        assert "Membre" == descr.items[1].items[0].value

        # change status
        resp = await web.post(
            f"/affinity/{xena.id}/manage-relations/{affinity.id}/{arthur.id}",
            json={"status": to_status_str},
        )
        assert 200 == resp.status
        descr = descr_serializer.load(await resp.json())
        assert to_status_str == descr.items[1].items[0].value

        arthur_relation: AffinityRelationDocument = (
            kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.character_id == arthur.id,
                AffinityRelationDocument.affinity_id == affinity.id,
            )
            .one()
        )
        statuses_dict = dict(statuses)
        expected = list(statuses_dict.keys())[
            list(statuses_dict.values()).index(to_status_str)
        ]
        assert arthur_relation.status_id == expected

    async def test_unit__disallow_member__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        affinity: AffinityDocument = kernel.server_db_session.query(
            AffinityDocument
        ).one()
        affinity.direction_type = AffinityDirectionType.ONE_DIRECTOR.value
        kernel.server_db_session.add(affinity)
        kernel.server_db_session.add(
            AffinityRelationDocument(
                character_id=arthur.id,
                affinity_id=affinity.id,
                accepted=True,
                status_id=MEMBER_STATUS[0],
            )
        )
        kernel.server_db_session.commit()

        # disallow arthur
        resp = await web.post(
            f"/affinity/{xena.id}/manage-relations/{affinity.id}/{arthur.id}?disallowed=1"
        )
        assert 200 == resp.status
        arthur_relation: AffinityRelationDocument = (
            kernel.server_db_session.query(AffinityRelationDocument)
            .filter(
                AffinityRelationDocument.character_id == arthur.id,
                AffinityRelationDocument.affinity_id == affinity.id,
            )
            .one()
        )
        assert not arthur_relation.accepted
        assert arthur_relation.disallowed
