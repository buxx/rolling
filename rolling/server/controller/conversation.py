#  coding: utf-8
import json
import typing
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2
from hapic.data import HapicData
from json import JSONDecodeError

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.kernel import Kernel
from rolling.model.character import (
    ConversationsQueryModel,
    GetConversationQueryModel,
    PostConversationBodyModel,
    PostSetupConversationQueryModel,
)
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import GetConversationPathModel
from rolling.server.controller.base import BaseController
from rolling.server.document.character import CharacterDocument
from rolling.server.document.message import MessageDocument
from rolling.server.extension import hapic
from rolling.util import ORIGINAL_AVATAR_PATTERN, ZONE_THUMB_AVATAR_PATTERN


class ConversationController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(ConversationsQueryModel)
    @hapic.output_body(Description)
    async def main_page(self, request: Request, hapic_data: HapicData) -> Description:
        # messages = self._kernel.message_lib.get_conversation_first_messages(
        #     hapic_data.path.character_id,
        #     hapic_data.query.with_character_id,  # FIXME BS NOW: test it
        # )
        # conversation_parts = []
        # for message in messages:
        #     unread = ""
        #     if (
        #         self._kernel.server_db_session.query(MessageDocument.id)
        #         .filter(
        #             MessageDocument.first_message == message.first_message,
        #             MessageDocument.read == False,
        #             MessageDocument.character_id == hapic_data.path.character_id,
        #         )
        #         .count()
        #     ):
        #         unread = "*"
        #     conversation_parts.append(
        #         Part(
        #             is_link=True,
        #             form_action=f"/conversation/{hapic_data.path.character_id}/read/{message.first_message}",
        #             label=f"{unread}{message.subject}",
        #             align="left",
        #         )
        #     )

        return Description(
            title="Conversations",
            items=[
                #     Part(
                #         text=(
                #             "Les conversations sont les échanges de paroles"
                #             " tenus avec d'autres personnages"
                #         )
                #     ),
                #     Part(
                #         is_link=True,
                #         label="Démarrer une nouvelle conversation",
                #         form_action=f"/conversation/{hapic_data.path.character_id}/start",
                #     ),
                #     Part(text="Ci-dessous les conversations précédentes ou en cours"),
                # ]
                # + conversation_parts,*
                Part(
                    is_link=True,
                    label="Afficher les conversations (web)",
                    form_action=f"{self._kernel.server_config.base_url}/conversation/{hapic_data.path.character_id}/web",
                    is_web_browser_link=True,
                )
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @aiohttp_jinja2.template("discussions.html")
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(GetConversationQueryModel)
    @hapic.input_body(PostConversationBodyModel)
    async def main_page_web(self, request: Request, hapic_data: HapicData) -> dict:
        character_id: str = hapic_data.path.character_id
        if character_id != request["account_character_id"]:
            raise web.HTTPForbidden()
        conversation_id: typing.Optional[int] = hapic_data.query.conversation_id
        posted_message: typing.Optional[str] = hapic_data.body.message

        conversation: typing.Optional[MessageDocument] = None
        conversation_messages: typing.List[MessageDocument] = []

        if conversation_id is not None:
            conversation_messages = self._kernel.message_lib.get_conversation_messages(
                character_id,
                conversation_id=conversation_id,
                order=MessageDocument.datetime.asc(),
            )
            conversation = conversation_messages[0]

        if posted_message and conversation_id:
            await self._kernel.message_lib.add_conversation_message(
                character_id,
                subject=conversation.subject,
                message=posted_message,
                # FIXME BS NOW : concerned : ça devrait être que les présents ?!
                concerned=conversation.concerned,
                conversation_id=conversation_id,
                filter_by_same_zone_than_author=True,
            )
            # Reload messages (because just added one)
            conversation_messages = self._kernel.message_lib.get_conversation_messages(
                character_id,
                conversation_id=conversation_id,
                order=MessageDocument.datetime.asc(),
            )

        topics = self._kernel.message_lib.get_conversation_first_messages(character_id)

        all_character_ids = list(
            set().union(*[message.concerned for message in topics])
        )
        characters_by_ids = {
            character_id: self._kernel.character_lib.get_document(
                character_id, dead=None
            )
            for character_id in all_character_ids
        }

        # Avatar thumbs
        character_avatar_thumbs_by_ids = {}
        for character in characters_by_ids.values():
            if character.avatar_uuid and character.avatar_is_validated:
                character_avatar_thumbs_by_ids[
                    character.id
                ] = ZONE_THUMB_AVATAR_PATTERN.format(avatar_uuid=character.avatar_uuid)
            else:
                character_avatar_thumbs_by_ids[
                    character.id
                ] = ZONE_THUMB_AVATAR_PATTERN.format(avatar_uuid="0000")

        # Avatars
        character_avatars_by_ids = {}
        for character in characters_by_ids.values():
            if character.avatar_uuid and character.avatar_is_validated:
                character_avatars_by_ids[character.id] = ORIGINAL_AVATAR_PATTERN.format(
                    avatar_uuid=character.avatar_uuid
                )
            else:
                character_avatars_by_ids[character.id] = ORIGINAL_AVATAR_PATTERN.format(
                    avatar_uuid="0000"
                )

        return {
            "characters_by_ids": characters_by_ids,
            "topics": topics,
            "character_id": character_id,
            "conversation": conversation,
            "conversation_messages": conversation_messages,
            "character_avatar_thumbs_by_ids": character_avatar_thumbs_by_ids,
            "character_avatars_by_ids": character_avatars_by_ids,
        }

    @hapic.with_api_doc()
    @aiohttp_jinja2.template("discussions.html")
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(PostSetupConversationQueryModel, as_list=["character_id"])
    async def setup_web(self, request: Request, hapic_data: HapicData) -> Response:
        character_id: str = hapic_data.path.character_id
        if character_id != request["account_character_id"]:
            raise web.HTTPForbidden()
        concerned: typing.List[str] = list(
            set(hapic_data.query.character_id + [character_id])
        )
        concerned_character_docs = {
            character_id_: self._kernel.character_lib.get_document(character_id_)
            for character_id_ in concerned
        }

        if not concerned:
            raise web.HTTPBadRequest(body="Aucun personnage n'a été sélectionné")

        existing_topic_id: typing.Optional[
            int
        ] = self._kernel.message_lib.search_conversation_first_message_for_concerned(
            character_id, concerned=list(set(concerned + [character_id]))
        )

        if existing_topic_id is not None:
            return web.HTTPFound(
                f"/conversation/{character_id}/web?conversation_id={existing_topic_id}"
            )

        new_topic_id = await self._kernel.message_lib.add_conversation_message(
            author_id=character_id,
            subject=", ".join(
                [
                    concerned_character_docs[character_id_].name
                    for character_id_ in concerned
                ]
            ),
            is_first_message=True,
            message="",
            concerned=concerned,
        )

        return web.HTTPFound(
            f"/conversation/{character_id}/web?conversation_id={new_topic_id}"
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(ConversationsQueryModel)
    @hapic.output_body(Description)
    async def start(self, request: Request, hapic_data: HapicData) -> Description:
        character_doc = self._kernel.character_lib.get_document(
            hapic_data.path.character_id
        )
        zone_characters = self._kernel.character_lib.get_zone_characters(
            row_i=character_doc.world_row_i,
            col_i=character_doc.world_col_i,
            exclude_ids=[hapic_data.path.character_id],
        )

        try:
            data = await request.json()
            if data.get("message"):
                selected_character_ids = [
                    c.id for c in zone_characters if data.get(c.id) == "on"
                ]
                if not selected_character_ids:
                    return Description(
                        title="Démarrer une nouvelle conversation",
                        items=[Part(text="Vous devez choisir au moins un personnage")],
                    )

                conversation_id = (
                    await self._kernel.message_lib.add_conversation_message(
                        author_id=hapic_data.path.character_id,
                        subject=data.get("subject", "Une conversation"),
                        message=data["message"],
                        concerned=selected_character_ids,
                        is_first_message=True,
                    )
                )
                return Description(
                    redirect=f"/conversation/{hapic_data.path.character_id}/read/{conversation_id}"
                )

        except JSONDecodeError:
            pass  # no json (i guess)

        if not zone_characters:
            return Description(
                title="Démarrer une nouvelle conversation",
                items=[
                    Part(text="Il n'y a personne ici avec qui converser"),
                    Part(
                        is_link=True,
                        label="Retourner aux conversations",
                        form_action=f"/conversation/{hapic_data.path.character_id}",
                    ),
                ],
            )

        character_parts = []
        for zone_character in zone_characters:
            character_parts.append(
                Part(
                    label=zone_character.name,
                    value="on",
                    is_checkbox=True,
                    name=zone_character.id,
                    # FIXME BS NOW: test it
                    checked=zone_character.id == hapic_data.query.with_character_id,
                )
            )

        return Description(
            title="Démarrer une nouvelle conversation",
            items=[
                Part(
                    text="Vous devez choisir les personnages avec qui entretenir cette conversation"
                ),
                Part(
                    is_form=True,
                    form_action=f"/conversation/{hapic_data.path.character_id}/start",
                    items=character_parts
                    + [
                        Part(
                            label="Choisissez un titre",
                            type_=Type.STRING,
                            name="subject",
                        ),
                        Part(
                            label="Saisissez votre élocuction",
                            type_=Type.STRING,
                            name="message",
                        ),
                    ],
                ),
            ],
            footer_links=[
                Part(
                    is_link=True,
                    label="Retourner aux conversations",
                    form_action=f"/conversation/{hapic_data.path.character_id}",
                )
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetConversationPathModel)
    @hapic.output_body(Description)
    async def read(self, request: Request, hapic_data: HapicData) -> Description:
        messages = self._kernel.message_lib.get_conversation_messages(
            character_id=hapic_data.path.character_id,
            conversation_id=hapic_data.path.conversation_id,
        )
        concerned_ids = set()
        for message in messages:
            concerned_ids |= set(message.concerned)
        concerned_names = [
            r[0]
            for r in self._kernel.server_db_session.query(CharacterDocument.name)
            .filter(CharacterDocument.id.in_(concerned_ids))
            .all()
        ]

        message_parts = []
        for message in messages:
            text = (
                f"{message.author_name}: {message.text}"
                if not message.is_outzone_message
                else message.text
            )
            message_parts.append(Part(text=text))

        self._kernel.message_lib.mark_character_conversation_messages_as_read(
            character_id=hapic_data.path.character_id,
            conversation_id=hapic_data.path.conversation_id,
        )
        self._kernel.server_db_session.commit()
        return Description(
            title=messages[-1].subject,
            items=[
                Part(text="Cette conversation concerne les personnages suivants"),
                Part(text=", ".join(concerned_names)),
                Part(
                    is_form=True,
                    form_action=f"/conversation/{hapic_data.path.character_id}/add/{hapic_data.path.conversation_id}",
                    items=[
                        Part(
                            label="Ajouter un message",
                            type_=Type.STRING,
                            name="message",
                        )
                    ],
                ),
                Part(text="Conversation (message le plus récente en haut):"),
            ]
            + message_parts,
            footer_links=[
                Part(
                    is_link=True,
                    label="Retourner aux conversations",
                    form_action=f"/conversation/{hapic_data.path.character_id}",
                    classes=["primary"],
                )
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetConversationPathModel)
    @hapic.output_body(Description)
    async def add(self, request: Request, hapic_data: HapicData) -> Description:
        data = await request.json()
        add_message = data["message"]
        last_message = self._kernel.message_lib.get_last_conversation_message(
            hapic_data.path.conversation_id
        )
        await self._kernel.message_lib.add_conversation_message(
            author_id=hapic_data.path.character_id,
            conversation_id=hapic_data.path.conversation_id,
            subject=last_message.subject,
            concerned=last_message.concerned,
            message=add_message,
        )

        return Description(
            redirect=f"/conversation/{hapic_data.path.character_id}/read/{hapic_data.path.conversation_id}"
        )

    # @hapic.with_api_doc()
    # @hapic.input_path(GetConversationPathModel)
    # @hapic.output_body(Description)
    # async def edit_concerned(self, request: Request, hapic_data: HapicData) -> Description:
    #     character_doc = self._kernel.character_lib.get_document(hapic_data.path.character_id)
    #     message = (
    #         self._kernel.server_db_session.query(MessageDocument)
    #         .filter(MessageDocument.id == hapic_data.path.conversation_id)
    #         .one()
    #     )
    #     first_message = (
    #         self._kernel.server_db_session.query(MessageDocument)
    #         .filter(MessageDocument.id == message.first_message)
    #         .one()
    #     )
    #     last_message = (
    #         self._kernel.server_db_session.query(MessageDocument)
    #         .filter(MessageDocument.first_message == message.first_message)
    #         .order_by(MessageDocument.datetime.desc())
    #         .limit(1)
    #         .one()
    #     )
    #     zone_characters = self._kernel.character_lib.get_zone_characters(
    #         row_i=character_doc.world_row_i,
    #         col_i=character_doc.world_col_i,
    #         exclude_ids=[hapic_data.path.character_id],
    #     )
    #
    #     character_parts = []
    #     for zone_character in zone_characters:
    #         character_parts.append(
    #             Part(
    #                 label=zone_character.name,
    #                 value="on",
    #                 is_checkbox=True,
    #                 name=zone_character.id,
    #                 checked=zone_character.id in last_message.concerned,
    #             )
    #         )
    #
    #     return Description(
    #         title=first_message.subject,
    #         items=[
    #             Part(
    #                 text="Vous pouvez ajouter les personnages ci-dessous à la conversation",
    #                 is_form=True,
    #                 form_action=f"/conversation/{hapic_data.path.character_id}/edit-concerned/{hapic_data.path.conversation_id}",
    #                 items=character_parts,
    #             )
    #         ],
    #         footer_links=[
    #
    #             Part(
    #                 is_link=True,
    #                 label="Retourner aux conversations",
    #                 form_action=f"/conversation/{hapic_data.path.character_id}",
    #             ),
    #             Part(
    #                 is_link=True,
    #                 label="Voir la conversation",
    #                 form_action=f"/conversation/{hapic_data.path.character_id}/read/{hapic_data.path.conversation_id}",
    #                 classes=["primary"],
    #             ),
    #         ],
    #     )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.post("/conversation/{character_id}", self.main_page),
                web.get("/conversation/{character_id}/web", self.main_page_web),
                web.post("/conversation/{character_id}/web", self.main_page_web),
                web.get("/conversation/{character_id}/web/setup", self.setup_web),
                web.post("/conversation/{character_id}/start", self.start),
                web.post(
                    "/conversation/{character_id}/read/{conversation_id}", self.read
                ),
                web.post(
                    "/conversation/{character_id}/add/{conversation_id}", self.add
                ),
            ]
        )
