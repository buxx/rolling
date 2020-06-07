#  coding: utf-8
from json import JSONDecodeError

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic.data import HapicData

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.kernel import Kernel
from rolling.model.character import ConversationsQueryModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import GetConversationPathModel
from rolling.server.controller.base import BaseController
from rolling.server.document.character import CharacterDocument
from rolling.server.document.message import MessageDocument
from rolling.server.extension import hapic


class ConversationController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(ConversationsQueryModel)
    @hapic.output_body(Description)
    async def main_page(self, request: Request, hapic_data: HapicData) -> Description:
        messages = self._kernel.message_lib.get_conversation_first_messages(
            hapic_data.path.character_id,
            hapic_data.query.with_character_id,  # FIXME BS NOW: test it
        )
        conversation_parts = []
        for message in messages:
            unread = ""
            if (
                self._kernel.server_db_session.query(MessageDocument.id)
                .filter(
                    MessageDocument.first_message == message.first_message,
                    MessageDocument.read == False,
                    MessageDocument.character_id == hapic_data.path.character_id,
                )
                .count()
            ):
                unread = "*"
            conversation_parts.append(
                Part(
                    is_link=True,
                    form_action=f"/conversation/{hapic_data.path.character_id}/read/{message.first_message}",
                    label=f"{unread}{message.subject}",
                    align="left",
                )
            )

        return Description(
            title="Conversations",
            items=[
                Part(
                    text=(
                        "Les conversations sont les échanges de paroles"
                        " tenus avec d'autres personnages"
                    )
                ),
                Part(
                    is_link=True,
                    label="Démarrer une nouvelle conversation",
                    form_action=f"/conversation/{hapic_data.path.character_id}/start",
                ),
                Part(text="Ci-dessous les conversations précédentes ou en cours"),
            ]
            + conversation_parts,
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(ConversationsQueryModel)
    @hapic.output_body(Description)
    async def start(self, request: Request, hapic_data: HapicData) -> Description:
        character_doc = self._kernel.character_lib.get_document(hapic_data.path.character_id)
        zone_characters = self._kernel.character_lib.get_zone_players(
            row_i=character_doc.world_row_i,
            col_i=character_doc.world_col_i,
            exclude_ids=[hapic_data.path.character_id],
        )

        try:
            data = await request.json()
            if data.get("message"):
                selected_character_ids = [c.id for c in zone_characters if data.get(c.id) == "on"]
                if not selected_character_ids:
                    return Description(
                        title="Démarrer une nouvelle conversation",
                        items=[
                            Part(text="Vous devez choisir au moins un personnage"),
                            Part(
                                is_link=True,
                                label="Retour",
                                form_action=f"/conversation/{hapic_data.path.character_id}/start",
                            ),
                            Part(
                                is_link=True,
                                go_back_zone=True,
                                label="Retourner à l'écran de déplacements",
                            ),
                        ],
                    )

                conversation_id = self._kernel.message_lib.add_conversation_message(
                    author_id=hapic_data.path.character_id,
                    subject=data.get("subject", "Une conversation"),
                    message=data["message"],
                    concerned=selected_character_ids,
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
                        is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"
                    ),
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
                        Part(label="Choisissez un titre", type_=Type.STRING, name="subject"),
                        Part(label="Saisissez votre élocuction", type_=Type.STRING, name="message"),
                    ],
                ),
            ],
            footer_links=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    is_link=True,
                    label="Retourner aux conversations",
                    form_action=f"/conversation/{hapic_data.path.character_id}",
                ),
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
                    items=[Part(label="Ajouter un message", type_=Type.STRING, name="message")],
                ),
                Part(text="Conversation (message le plus récente en haut):"),
            ]
            + message_parts,
            footer_links=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    is_link=True,
                    label="Retourner aux conversations",
                    form_action=f"/conversation/{hapic_data.path.character_id}",
                    classes=["primary"],
                ),
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetConversationPathModel)
    @hapic.output_body(Description)
    async def add(self, request: Request, hapic_data: HapicData) -> Description:
        data = await request.json()
        add_message = data["message"]
        last_message = (
            self._kernel.server_db_session.query(MessageDocument)
            .filter(MessageDocument.first_message == hapic_data.path.conversation_id)
            .order_by(MessageDocument.datetime.desc())
            .limit(1)
            .one()
        )
        self._kernel.message_lib.add_conversation_message(
            author_id=hapic_data.path.character_id,
            conversation_id=hapic_data.path.conversation_id,
            subject=last_message.subject,
            concerned=last_message.concerned,
            message=add_message,
        )

        return Description(
            redirect=f"/conversation/{hapic_data.path.character_id}/read/{hapic_data.path.conversation_id}"
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetConversationPathModel)
    @hapic.output_body(Description)
    async def edit_concerned(self, request: Request, hapic_data: HapicData) -> Description:
        character_doc = self._kernel.character_lib.get_document(hapic_data.path.character_id)
        message = (
            self._kernel.server_db_session.query(MessageDocument)
            .filter(MessageDocument.id == hapic_data.path.conversation_id)
            .one()
        )
        first_message = (
            self._kernel.server_db_session.query(MessageDocument)
            .filter(MessageDocument.id == message.first_message)
            .one()
        )
        last_message = (
            self._kernel.server_db_session.query(MessageDocument)
            .filter(MessageDocument.first_message == message.first_message)
            .order_by(MessageDocument.datetime.desc())
            .limit(1)
            .one()
        )
        zone_characters = self._kernel.character_lib.get_zone_players(
            row_i=character_doc.world_row_i,
            col_i=character_doc.world_col_i,
            exclude_ids=[hapic_data.path.character_id],
        )

        character_parts = []
        for zone_character in zone_characters:
            character_parts.append(
                Part(
                    label=zone_character.name,
                    value="on",
                    is_checkbox=True,
                    name=zone_character.id,
                    checked=zone_character.id in last_message.concerned,
                )
            )

        return Description(
            title=first_message.subject,
            items=[
                Part(
                    text="Vous pouvez ajouter les personnages ci-dessous à la conversation",
                    is_form=True,
                    form_action=f"/conversation/{hapic_data.path.character_id}/edit-concerned/{hapic_data.path.conversation_id}",
                    items=character_parts,
                )
            ],
            footer_links=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    is_link=True,
                    label="Retourner aux conversations",
                    form_action=f"/conversation/{hapic_data.path.character_id}",
                ),
                Part(
                    is_link=True,
                    label="Voir la conversation",
                    form_action=f"/conversation/{hapic_data.path.character_id}/read/{hapic_data.path.conversation_id}",
                    classes=["primary"],
                ),
            ],
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.post("/conversation/{character_id}", self.main_page),
                web.post("/conversation/{character_id}/start", self.start),
                web.post("/conversation/{character_id}/read/{conversation_id}", self.read),
                web.post("/conversation/{character_id}/add/{conversation_id}", self.add),
            ]
        )
