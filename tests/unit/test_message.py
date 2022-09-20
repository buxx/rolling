# coding: utf-8
from aiohttp.test_utils import TestClient
import serpyco
import typing
import pytest

from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.server.document.message import MessageDocument
from tests.fixtures import description_serializer


class TestMessage:
    async def _assert_messages(
        self,
        web: TestClient,
        character_id: str,
        message_count: int = 0,
        row_i: int = 0,
        col_i: int = 0,
        assert_messages: typing.Optional[typing.List[str]] = None,
    ) -> None:
        assert_messages = assert_messages or []
        resp = await web.post(
            f"/zones/{row_i}/{col_i}/messages?character_id={character_id}"
        )
        descr = description_serializer.load(await resp.json())

        assert 3 + message_count == len(descr.items)
        assert descr.items[1].is_form
        assert (
            f"/zones/{row_i}/{col_i}/messages/add"
            f"?character_id={character_id}" == descr.items[1].form_action
        )
        assert descr.items[1].items
        assert "message" == descr.items[1].items[0].name

        messages = [item.text for item in descr.items[3:]]
        for assert_message in assert_messages:
            assert assert_message in messages

    async def test_unit__empty_zone_messages__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        await self._assert_messages(
            web,
            xena.id,
            message_count=0,
            row_i=xena.world_row_i,
            col_i=xena.world_col_i,
        )

    async def _post_zone_message(
        self,
        web: TestClient,
        character_id: str,
        message: str,
        row_i: int = 0,
        col_i: int = 0,
        resp_code: int = 200,
    ) -> None:
        resp = await web.post(
            f"/zones/{row_i}/{col_i}/messages/add?character_id={character_id}",
            json={"message": message},
        )
        text = await resp.text()
        assert resp_code == resp.status

    async def test_unit__zone_messages__ok__nominal_case(
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
        assert xena.world_row_i == arthur.world_row_i
        assert xena.world_col_i == arthur.world_col_i

        # no message at startup
        await self._assert_messages(
            web,
            xena.id,
            message_count=0,
            row_i=xena.world_row_i,
            col_i=xena.world_col_i,
        )
        # send message, visible for xena and arthur
        await self._post_zone_message(
            web, xena.id, "hello", row_i=xena.world_row_i, col_i=xena.world_col_i
        )
        await self._assert_messages(
            web,
            xena.id,
            message_count=1,
            row_i=xena.world_row_i,
            col_i=xena.world_col_i,
            assert_messages=[f"{xena.name}: hello"],
        )
        await self._assert_messages(
            web,
            arthur.id,
            message_count=1,
            row_i=xena.world_row_i,
            col_i=xena.world_col_i,
            assert_messages=[f"{xena.name}: hello"],
        )
        await self._post_zone_message(
            web,
            arthur.id,
            "hello xena !",
            row_i=arthur.world_row_i,
            col_i=arthur.world_col_i,
        )
        await self._assert_messages(
            web,
            xena.id,
            message_count=2,
            row_i=xena.world_row_i,
            col_i=xena.world_col_i,
            assert_messages=[f"{xena.name}: hello", f"{arthur.name}: hello xena !"],
        )
        await self._assert_messages(
            web,
            arthur.id,
            message_count=2,
            row_i=xena.world_row_i,
            col_i=xena.world_col_i,
            assert_messages=[f"{xena.name}: hello", f"{arthur.name}: hello xena !"],
        )

        # Move xena, arthur don' see new xena message
        xena_doc = await kernel.character_lib.move(
            character=xena, to_world_row=0, to_world_col=0
        )
        await self._assert_messages(
            web,
            xena.id,
            message_count=3,
            row_i=xena_doc.world_row_i,
            col_i=xena_doc.world_col_i,
            assert_messages=[
                f"{xena.name}: hello",
                f"{arthur.name}: hello xena !",
                "Vous avez changé de zone",
            ],
        )
        await self._assert_messages(
            web,
            arthur.id,
            message_count=2,
            row_i=xena_doc.world_row_i,
            col_i=xena_doc.world_col_i,
            assert_messages=[f"{xena.name}: hello", f"{arthur.name}: hello xena !"],
        )
        await self._post_zone_message(
            web,
            xena.id,
            "some here ?",
            row_i=xena_doc.world_row_i,
            col_i=xena_doc.world_col_i,
        )
        await self._assert_messages(
            web,
            xena.id,
            message_count=4,
            row_i=xena_doc.world_row_i,
            col_i=xena_doc.world_col_i,
            assert_messages=[
                f"{xena.name}: hello",
                f"{arthur.name}: hello xena !",
                "Vous avez changé de zone",
                f"{xena.name}: some here ?",
            ],
        )
        await self._assert_messages(
            web,
            arthur.id,
            message_count=2,
            row_i=arthur.world_row_i,
            col_i=arthur.world_col_i,
        )

    async def _assert_conversations(
        self,
        web: TestClient,
        character: CharacterModel,
        count: int,
        resp_code: int = 200,
    ) -> None:
        resp = await web.post(f"/conversation/{character.id}")
        text = await resp.text()
        assert resp_code == resp.status
        descr = description_serializer.load(await resp.json())
        assert f"/conversation/{character.id}/start" == descr.items[1].form_action
        assert 3 + count == len(descr.items)

    async def _create_conversation(
        self,
        web: TestClient,
        author: CharacterModel,
        with_: typing.List[CharacterModel],
        available: typing.List[CharacterModel],
        subject: str,
        message: str,
    ) -> None:
        resp = await web.post(f"/conversation/{author.id}/start")
        text = await resp.text()
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        assert descr.items[1].is_form
        assert f"/conversation/{author.id}/start" == descr.items[1].form_action
        checkbox_names = [i.name for i in descr.items[1].items if i.is_checkbox]
        for character_available in available:
            assert character_available.id in checkbox_names

        data = {"subject": subject, "message": message}
        for with_character in with_:
            data[with_character.id] = "on"

        resp = await web.post(f"/conversation/{author.id}/start", json=data)
        text = await resp.text()
        assert 200 == resp.status

    async def _assert_conversation(
        self,
        web: TestClient,
        character: CharacterModel,
        conversation_id: int,
        between: typing.List[CharacterModel],
        message_count: int,
        messages: typing.List[str],
    ) -> None:
        resp = await web.post(f"/conversation/{character.id}/read/{conversation_id}")
        text = await resp.text()
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        for between_character in between:
            assert between_character.name in descr.items[1].text

        assert 4 + message_count == len(descr.items)
        messages_ = [i.text for i in descr.items[4:]]
        for message in messages:
            assert message in messages_

    async def _add_conversation_message(
        self,
        web: TestClient,
        character: CharacterModel,
        conversation_id: int,
        message: str,
    ) -> None:
        resp = await web.post(
            f"/conversation/{character.id}/add/{conversation_id}",
            json={"message": message},
        )
        text = await resp.text()
        assert 200 == resp.status

    @pytest.mark.skip(reason="Conversations have been moved on web")
    async def test_unit__conversation__ok__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_franck_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        franck = worldmapc_franck_model
        kernel = worldmapc_kernel
        assert xena.world_row_i == arthur.world_row_i == franck.world_row_i
        assert xena.world_col_i == arthur.world_col_i == franck.world_col_i

        await self._assert_conversations(web, xena, count=0)
        await self._assert_conversations(web, arthur, count=0)
        await self._assert_conversations(web, franck, count=0)

        await self._create_conversation(
            web,
            author=xena,
            with_=[arthur],
            subject="hello",
            message="coucou",
            available=[arthur, franck],
        )
        c = kernel.server_db_session.query(MessageDocument).limit(1).one()
        await self._assert_conversations(web, xena, count=1)
        await self._assert_conversations(web, arthur, count=1)
        await self._assert_conversations(web, franck, count=0)
        await self._assert_conversation(
            web,
            xena,
            c.id,
            message_count=1,
            messages=[f"{xena.name}: coucou"],
            between=[xena, arthur],
        )
        await self._assert_conversation(
            web,
            arthur,
            c.id,
            message_count=1,
            messages=[f"{xena.name}: coucou"],
            between=[xena, arthur],
        )

        await self._add_conversation_message(web, arthur, c.id, message="ca va bien ?")
        await self._assert_conversations(web, xena, count=1)
        await self._assert_conversations(web, arthur, count=1)
        await self._assert_conversations(web, franck, count=0)
        await self._assert_conversation(
            web,
            xena,
            c.id,
            message_count=2,
            messages=[f"{xena.name}: coucou", f"{arthur.name}: ca va bien ?"],
            between=[xena, arthur],
        )
        await self._assert_conversation(
            web,
            arthur,
            c.id,
            message_count=2,
            messages=[f"{xena.name}: coucou", f"{arthur.name}: ca va bien ?"],
            between=[xena, arthur],
        )

    # TODO BS: exclude "left" messages when it is a following group
    @pytest.mark.xfail(reason="FIXME : find why is flaky !")
    async def test_unit__conversation__ok__people_left(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_franck_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        franck = worldmapc_franck_model
        kernel = worldmapc_kernel
        assert xena.world_row_i == arthur.world_row_i == franck.world_row_i
        assert xena.world_col_i == arthur.world_col_i == franck.world_col_i

        await self._create_conversation(
            web,
            author=xena,
            with_=[arthur, franck],
            subject="hello",
            message="coucou",
            available=[arthur, franck],
        )
        c = kernel.server_db_session.query(MessageDocument).limit(1).one()
        await kernel.character_lib.move(arthur, to_world_row=0, to_world_col=0)

        await self._assert_conversation(
            web,
            xena,
            c.id,
            message_count=2,
            messages=[
                f"{xena.name}: coucou",
                f"{arthur.name} n'est plus là pour parler",
            ],
            between=[xena, arthur, franck],
        )
        await self._assert_conversation(
            web,
            franck,
            c.id,
            message_count=2,
            messages=[
                f"{xena.name}: coucou",
                f"{arthur.name} n'est plus là pour parler",
            ],
            between=[xena, arthur, franck],
        )
        await self._assert_conversation(
            web,
            arthur,
            c.id,
            message_count=2,
            messages=[
                f"{xena.name}: coucou",
                f"Vous etes partis et ne pouvez plus parler avec {franck.name}, {xena.name}",
            ],
            between=[xena, arthur, franck],
        )

        await kernel.character_lib.move(franck, to_world_row=0, to_world_col=0)
        await self._assert_conversation(
            web,
            xena,
            c.id,
            message_count=3,
            messages=[
                f"{xena.name}: coucou",
                f"{arthur.name} n'est plus là pour parler",
                f"{franck.name} n'est plus là pour parler",
            ],
            between=[xena, arthur, franck],
        )
        a = 1
        await self._assert_conversation(
            web,
            franck,
            c.id,
            message_count=4,
            messages=[
                f"{xena.name}: coucou",
                f"{arthur.name} n'est plus là pour parler",
                f"Vous etes partis et ne pouvez plus parler avec " f"{xena.name}",
                f"Vous avez rejoins {arthur.name}",
            ],
            between=[xena, arthur, franck],
        )
        await self._assert_conversation(
            web,
            arthur,
            c.id,
            message_count=3,
            messages=[
                f"{xena.name}: coucou",
                f"Vous etes partis et ne pouvez plus parler avec {franck.name}, {xena.name}",
                f"{franck.name} vous à rejoin",
            ],
            between=[xena, arthur, franck],
        )
