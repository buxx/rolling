# coding: utf-8
from aiohttp.test_utils import TestClient
import pytest
import serpyco

from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityRelationDocument


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
        assert '[["CHIEF_STATUS", "Chef"], ["MEMBER_STATUS", "Membre"]]' == affinity.statuses

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
        assert "/affinity/xena/see/1" == descr.items[-1].form_action
        assert "MyAffinity (Chef, Combattant)" == descr.items[-1].label

        # see affinity
        resp = await web.post(f"/affinity/{xena.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert "1 prêt(s)" in descr.items[1].text
        assert "/affinity/xena/edit-relation/1" == descr.items[2].form_action
        assert (
            "Vous êtes membre de cette affinité et vous portez le status de Chef (Vous vous battez pour elle)"
            == descr.items[2].label
        )

    @pytest.mark.parametrize("request_,fighter", [(False, True), (True, True), (True, False)])
    async def test_unit__join_affinity__ok__as_non_member(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arhur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        request_: bool,
        fighter: bool,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arhur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})

        # list unknowns
        resp = await web.post(f"/affinity/{arthur.id}/list")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.items[1].label
        assert "/affinity/arthur/see/1" == descr.items[1].form_action

        # display edit relation
        resp = await web.post(f"/affinity/{arthur.id}/edit-relation/{1}")
        descr = descr_serializer.load(await resp.json())

        assert "/affinity/arthur/edit-relation/1?request=1" == descr.items[0].form_action
        assert "/affinity/arthur/edit-relation/1?request=1&fighter=1" == descr.items[1].form_action
        assert "/affinity/arthur/edit-relation/1?request=0&fighter=1" == descr.items[2].form_action

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
            assert "/affinity/arthur/edit-relation/1?request=1" == descr.items[0].form_action
            assert "Ne plus se battre pour cette affinité" == descr.items[1].label
            assert "/affinity/arthur/edit-relation/1?fighter=0" == descr.items[1].form_action
        elif request_ and fighter:
            assert "Ne plus demander à être membre" == descr.items[0].label
            assert "/affinity/arthur/edit-relation/1?request=0" == descr.items[0].form_action
            assert "Ne plus se battre pour cette affinité" == descr.items[1].label
            assert "/affinity/arthur/edit-relation/1?fighter=0" == descr.items[1].form_action
        elif request_ and not fighter:
            assert "Ne plus demander à être membre" == descr.items[0].label
            assert "/affinity/arthur/edit-relation/1?request=0" == descr.items[0].form_action
            assert "Me battre pour cette affinité" == descr.items[1].label
            assert "/affinity/arthur/edit-relation/1?fighter=1" == descr.items[1].form_action

        # list affinities
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        assert "/affinity/arthur/see/1" == descr.items[-1].form_action
        expected_str = ""
        if fighter and request_:
            expected_str = " (Demandé, Combattant)"
        if fighter and not request_:
            expected_str = " (Combattant)"
        if not fighter and request_:
            expected_str = " (Demandé)"
        assert f"MyAffinity{expected_str}" == descr.items[-1].label

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"{1 if not fighter else 2} prêt(s)" in descr.items[1].text
        assert "/affinity/arthur/edit-relation/1" == descr.items[2].form_action
        expected_str = ""
        if fighter and request_:
            expected_str = (
                "Vous avez demandé à être membre de cette affinité (Vous vous battez pour elle)"
            )
        if fighter and not request_:
            expected_str = "Vous combattez pour cette affinité"
        if not fighter and request_:
            expected_str = "Vous avez demandé à être membre de cette affinité"
        assert expected_str == descr.items[2].label

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
            assert f"MyAffinity{expected_str}" == descr.items[-1].label

            # see affinity
            resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
            descr = descr_serializer.load(await resp.json())
            assert "MyAffinity" == descr.title
            assert "2 membre(s)" in descr.items[1].text
            assert f"{1 if not fighter else 2} prêt(s)" in descr.items[1].text
            expected_str = ""
            if fighter:
                expected_str = "Vous êtes membre de cette affinité et vous portez le status de Membre (Vous vous battez pour elle)"
            if not fighter:
                expected_str = (
                    "Vous êtes membre de cette affinité et vous portez le status de Membre"
                )
            assert expected_str == descr.items[2].label

    @pytest.mark.parametrize("fighter", [True, False])
    async def test_unit__reject_affinity__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arhur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        fighter: bool,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arhur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        await web.post(f"/affinity/arthur/edit-relation/1?request=1&fighter={int(fighter)}")

        # disallow
        resp = await web.post(f"/affinity/arthur/edit-relation/1?rejected=1&fighter={int(fighter)}")
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
        assert "/affinity/arthur/see/1" == descr.items[-1].form_action
        if fighter:
            expected_str = " (Quitté, Combattant)"
        else:
            expected_str = " (Quitté)"
        assert f"MyAffinity{expected_str}" == descr.items[-1].label

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"{2 if fighter else 1} prêt(s)" in descr.items[1].text
        assert "/affinity/arthur/edit-relation/1" == descr.items[2].form_action
        if fighter:
            expected_str = "Vous avez renié cette affinité (Vous vous battez pour elle)"
        else:
            expected_str = "Vous avez renié cette affinité"
        assert expected_str == descr.items[2].label

    @pytest.mark.parametrize("fighter", [True, False])
    async def test_unit__discard_request__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arhur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        fighter: bool,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arhur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})
        await web.post(f"/affinity/arthur/edit-relation/1?request=1&fighter={int(fighter)}")

        # discard
        resp = await web.post(f"/affinity/arthur/edit-relation/1?request=0&fighter={int(fighter)}")
        descr = descr_serializer.load(await resp.json())
        assert "Vous ne demandez plus à être membre de MyAffinity" == descr.title

        # display main
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        assert "/affinity/arthur/see/1" == descr.items[-1].form_action
        if fighter:
            expected_str = " (Combattant)"
        else:
            expected_str = " (Plus de lien)"
        assert f"MyAffinity{expected_str}" == descr.items[-1].label

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"{2 if fighter else 1} prêt(s)" in descr.items[1].text
        assert "/affinity/arthur/edit-relation/1" == descr.items[2].form_action
        if fighter:
            expected_str = "Vous combattez pour cette affinité"
        else:
            expected_str = "Vous n'avez plus aucune relation avec cette affinité"
        assert expected_str == descr.items[2].label

        # re do request
        resp = await web.post(f"/affinity/arthur/edit-relation/1?request=1&fighter={int(fighter)}")
        descr = descr_serializer.load(await resp.json())
        assert "Requete pour etre membre de MyAffinity exprimé" == descr.title

        # list affinities
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        assert "/affinity/arthur/see/1" == descr.items[-1].form_action
        if fighter:
            expected_str = " (Demandé, Combattant)"
        else:
            expected_str = " (Demandé)"
        assert f"MyAffinity{expected_str}" == descr.items[-1].label

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        if fighter:
            expected_str = (
                "Vous avez demandé à être membre de cette affinité (Vous vous battez pour elle)"
            )
        else:
            expected_str = "Vous avez demandé à être membre de cette affinité"
        assert expected_str == descr.items[2].label

    async def test_unit__only_fight_for_ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arhur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arhur_model
        kernel = worldmapc_kernel
        await web.post(f"/affinity/{xena.id}/new", json={"name": "MyAffinity"})

        resp = await web.post(f"/affinity/arthur/edit-relation/1?fighter=1")
        descr = descr_serializer.load(await resp.json())
        assert "Vous vous battez désormais pour MyAffinity" == descr.title

        # display main
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        assert "/affinity/arthur/see/1" == descr.items[-1].form_action
        assert f"MyAffinity (Combattant)" == descr.items[-1].label

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"2 prêt(s)" in descr.items[1].text
        assert "/affinity/arthur/edit-relation/1" == descr.items[2].form_action
        assert "Vous combattez pour cette affinité" == descr.items[2].label

        resp = await web.post(f"/affinity/arthur/edit-relation/1?fighter=0")
        descr = descr_serializer.load(await resp.json())
        assert (
            "Vous ne combatrez désormais plus lorsqu'un membre de MyAffinity sera attaqué"
            == descr.title
        )

        # display main
        resp = await web.post(f"/affinity/{arthur.id}")
        descr = descr_serializer.load(await resp.json())
        assert "/affinity/arthur/see/1" == descr.items[-1].form_action
        assert f"MyAffinity (Plus de lien)" == descr.items[-1].label

        # see affinity
        resp = await web.post(f"/affinity/{arthur.id}/see/{1}")
        descr = descr_serializer.load(await resp.json())
        assert "MyAffinity" == descr.title
        assert "1 membre(s)" in descr.items[1].text
        assert f"1 prêt(s)" in descr.items[1].text
        assert "/affinity/arthur/edit-relation/1" == descr.items[2].form_action
        assert "Vous n'avez plus aucune relation avec cette affinité" == descr.items[2].label
