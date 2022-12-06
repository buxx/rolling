# coding: utf-8
import copy
import dataclasses
import json
import typing
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2
from pathlib import Path
import pkg_resources
import serpyco
from hapic import HapicData

from guilang.description import Description
from guilang.description import Part
from rolling.kernel import Kernel
from rolling.model.fight import AttackDescription, DefendDescription
from rolling.model.skill import CharacterSkillModel
from rolling.model.stuff import StuffModel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.model.character import CharacterModel
from rolling.log import server_logger
from rolling.server.lib.fight import FightLib


version = pkg_resources.require("rolling")[0].version


@dataclasses.dataclass
class AvatarIndexPath:
    index: int = serpyco.field(cast_on_load=True)


class SystemController(BaseController):
    def __init__(
        self,
        kernel: Kernel,
        serve_static_files: typing.Optional[str] = None,
    ) -> None:
        self._kernel = kernel
        self._serve_static_files = serve_static_files

    @hapic.with_api_doc()
    async def version(self, request: Request) -> Response:
        return Response(status=200, body=version)

    @aiohttp_jinja2.template("root.html")
    async def root(self, request: Request) -> dict:
        return {"title": self._kernel.server_config.name, "version": version}

    @hapic.with_api_doc()
    @aiohttp_jinja2.template("infos.html")
    async def infos(self, request: Request) -> dict:
        return {"game": self._kernel.game}

    @hapic.with_api_doc()
    @hapic.output_body(Description)
    async def describe_infos(self, request: Request) -> Description:
        return Description(
            title="Informations sur le serveur",
            items=[
                Part(
                    label="Ouvrir la page des informations gameplay (web)",
                    is_link=True,
                    is_web_browser_link=True,
                    # FIXME BS NOW: protocol
                    form_action=f"{self._kernel.server_config.base_url}/infos",
                )
            ],
        )

    @hapic.with_api_doc()
    async def loadings(self, request: Request) -> web.Response:
        return web.json_response(self._kernel.loadings_medias_names)

    @hapic.with_api_doc()
    async def illustrations_names(self, request: Request) -> web.Response:
        illustrations_names = []

        for item in self._kernel.game.config.resources.values():
            illustrations_names.append(item.illustration)

        for item in self._kernel.game.config.builds.values():
            illustrations_names.append(item.illustration)

        for item in self._kernel.game.stuff_manager.items:
            illustrations_names.append(item.illustration)

        for item in self._kernel.game.world_manager.world.zones_properties:
            illustrations_names.append(item.illustration)

        return web.json_response(list(set(filter(bool, illustrations_names))))

    @hapic.with_api_doc()
    @hapic.input_path(AvatarIndexPath)
    async def avatar(self, request: Request, hapic_data: HapicData) -> web.Response:
        index = hapic_data.path.index
        avatar_path = self._kernel.avatars_paths[index]
        with open(avatar_path, "rb") as avatar_file:
            return web.Response(
                body=avatar_file.read(),
                content_type="image/png",
            )

    @hapic.with_api_doc()
    @aiohttp_jinja2.template("fight_simulator.html")
    async def fight_simulator(self, request: Request) -> typing.Dict[str, typing.Any]:
        weapon_descriptions = self._kernel.game.stuff_manager.get_weapon_descriptions()
        armor_descriptions = self._kernel.game.stuff_manager.get_armor_descriptions()
        shield_descriptions = self._kernel.game.stuff_manager.get_shield_descriptions()

        details = []
        debug = False
        post_data = {}
        passes = 1
        if request.method == "POST":
            post_data = await request.post()
            debug = post_data.get("debug", "") == "on"
            passes = int(post_data["passes"])
            character1 = self._generate_character(i=1, data=post_data)
            character2 = self._generate_character(i=2, data=post_data)
            fight_lib = FightLib(self._kernel, dont_touch_db=True)

            for _ in range(passes):
                attackers = AttackDescription(
                    affinity=None,
                    all_fighters=[character1],
                    ready_fighters=[character1] if character1.is_attack_ready else [],
                )
                defensers = DefendDescription(
                    all_fighters=[character2],
                    ready_fighters=[character2] if character2.is_attack_ready else [],
                    affinities=[],
                    helpers={},
                )
                detail = await fight_lib.fight(attackers, defensers)
                details.append(
                    ((copy.deepcopy(character1), copy.deepcopy(character2)), detail)
                )

        return {
            "skills": self._kernel.game.config.skills.values(),
            "weapon_descriptions": weapon_descriptions,
            "armor_descriptions": armor_descriptions,
            "shield_descriptions": shield_descriptions,
            "fight_details": details,
            "debug": debug,
            "post_data": post_data,
            "passes": passes,
        }

    def _generate_character(
        self, i: int, data: typing.Dict[str, str]
    ) -> CharacterModel:
        character = CharacterModel(
            id="n/a",
            name=f"Personnage{i}",
            alive=True,
            background_story="n/a",
            max_life_comp=0.0,
            hunting_and_collecting_comp=0.0,
            find_water_comp=0.0,
            life_points=float(data[f"c{i}_life_points"]),
            action_points=1024.0,
            max_action_points=0.0,
            attack_allowed_loss_rate=0,
            defend_allowed_loss_rate=0,
            skills={},
            knowledges=[],
            ability_ids=[],
            tiredness=0,
            thirst=0.0,
            hunger=0.0,
            spritesheet_filename="",
            spritesheet_set=False,
        )

        for skill in self._kernel.game.config.skills.values():
            skill_value = float(data[f"c{ i }_skill_{ skill.id }"])
            character.skills[skill.id] = CharacterSkillModel(
                id=skill.id,
                name=skill.name,
                value=skill_value,
                counter=-1,
            )

        if main_weapon_stuff_id := data[f"c{i}_primary_weapon"]:
            stuff_description = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    main_weapon_stuff_id
                )
            )
            weapon_doc = self._kernel.stuff_lib.create_document_from_stuff_properties(
                stuff_description,
            )
            weapon_model = self._kernel.stuff_lib.stuff_model_from_doc(weapon_doc)
            character.weapon = weapon_model

        if shield_stuff_id := data[f"c{i}_shield"]:
            stuff_description = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    shield_stuff_id
                )
            )
            shield_doc = self._kernel.stuff_lib.create_document_from_stuff_properties(
                stuff_description,
            )
            shield_model = self._kernel.stuff_lib.stuff_model_from_doc(shield_doc)
            character.shield = shield_model

        if armor_stuff_id := data[f"c{i}_armor"]:
            stuff_description = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    armor_stuff_id
                )
            )
            armor_doc = self._kernel.stuff_lib.create_document_from_stuff_properties(
                stuff_description,
            )
            armor_model = self._kernel.stuff_lib.stuff_model_from_doc(armor_doc)
            character.armor = armor_model

        return character

    def bind(self, app: Application) -> None:
        Path("game/media/bg").mkdir(parents=True, exist_ok=True)
        app.add_routes(
            [
                web.get("/system/version", self.version),
                web.post("/system/describe/infos", self.describe_infos),
                web.get("/infos", self.infos),
                web.get("/avatar/{index}", self.avatar),
                web.get("/system/loadings", self.loadings),
                web.get("/system/illustrations-names", self.illustrations_names),
            ]
        )

        if self._serve_static_files:
            server_logger.info(f"Serve static files from '{self._serve_static_files}'")
            app.add_routes(
                [
                    web.static(
                        "/static",
                        self._serve_static_files,
                        follow_symlinks=True,
                    ),
                ]
            )
        app.add_routes(
            [
                web.get("/", self.root),
                web.get("/simulator/fight", self.fight_simulator),
                web.post("/simulator/fight", self.fight_simulator),
                web.static("/media", "game/media"),
                web.static("/media_bg", "game/media/bg"),
            ]
        )
