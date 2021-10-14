# coding: utf-8
from os import path
import toml
import typing

from rolling.action.base import ActionDescriptionModel
from rolling.action.utils import fill_base_action_properties
from rolling.exception import ConfigurationError
from rolling.game.stuff import StuffManager
from rolling.game.world import WorldManager
from rolling.map.type.world import WorldMapTileType
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.ability import AbilityDescription
from rolling.model.build import BuildBuildRequireResourceDescription
from rolling.model.build import BuildDescription
from rolling.model.build import BuildPowerOnRequireResourceDescription
from rolling.model.build import BuildTurnRequireResourceDescription
from rolling.model.effect import CharacterEffectDescriptionModel
from rolling.model.knowledge import DEFAULT_INSTRUCTOR_COEFF
from rolling.model.knowledge import KnowledgeDescription
from rolling.model.material import MaterialDescriptionModel
from rolling.model.measure import Unit
from rolling.model.meta import TransportType
from rolling.model.mix import RequiredResourceForMix
from rolling.model.mix import ResourceMixDescription
from rolling.model.resource import ResourceDescriptionModel
from rolling.model.skill import DEFAULT_MAXIMUM_SKILL
from rolling.model.skill import SkillDescription
from rolling.model.stuff import StuffProperties
from rolling.model.stuff import ZoneGenerationStuff
from rolling.model.world import World
from rolling.model.zone import GenerationInfo
from rolling.model.zone import ZoneMapTileProduction
from rolling.model.zone import ZoneProperties
from rolling.model.zone import ZoneResource
from rolling.model.zone import ZoneStuff
from rolling.model.zone import ZoneTileProperties
from rolling.rolling_types import ActionType
from rolling.server.action import ActionFactory
from rolling.util import generate_background_media

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class GameConfig:
    def __init__(self, kernel: "Kernel", config_dict: dict, folder_path: str) -> None:
        self._folder_path = folder_path
        self._kernel = kernel

        self.action_points_per_tick: float = config_dict["action_points_per_tick"]
        self.life_point_points_per_tick: float = config_dict[
            "life_point_points_per_tick"
        ]
        self.thirst_change_per_tick: float = config_dict[
            "thirst_change_per_tick"
        ]  # percent
        self.thirst_life_point_loss_per_tick: float = config_dict[
            "thirst_life_point_loss_per_tick"
        ]
        self.hunger_change_per_tick: float = config_dict[
            "hunger_change_per_tick"
        ]  # percent
        self.hunger_life_point_loss_per_tick: float = config_dict[
            "hunger_life_point_loss_per_tick"
        ]
        self.tick_every: int = config_dict["tick_every"]  # seconds
        self.default_maximum_ap: float = config_dict["default_maximum_ap"]
        self.reduce_tiredness_per_tick: int = config_dict["reduce_tiredness_per_tick"]
        self.start_thirst: float = config_dict["start_thirst"]
        self.start_hunger: float = config_dict["start_hunger"]
        self.start_action_points: float = config_dict["start_action_points"]
        self.start_hunger_life_point_loss: float = config_dict[
            "start_hunger_life_point_loss"
        ]
        self.start_thirst_life_point_loss: float = config_dict[
            "start_thirst_life_point_loss"
        ]
        self.limit_hunger_increase_life_point: float = config_dict[
            "limit_hunger_increase_life_point"
        ]
        self.limit_thirst_increase_life_point: float = config_dict[
            "limit_thirst_increase_life_point"
        ]
        self.limit_hunger_reduce_tiredness: float = config_dict[
            "limit_hunger_reduce_tiredness"
        ]
        self.limit_thirst_reduce_tiredness: float = config_dict[
            "limit_thirst_reduce_tiredness"
        ]
        self.stop_auto_drink_thirst: float = config_dict["stop_auto_drink_thirst"]
        self.stop_auto_eat_hunger: float = config_dict["stop_auto_eat_hunger"]
        self.limit_warning_drink_left_tick: int = config_dict[
            "limit_warning_drink_left_tick"
        ]
        self.limit_warning_eat_left_tick: int = config_dict[
            "limit_warning_eat_left_tick"
        ]

        self.less_than_is_health2: float = config_dict["less_than_is_health2"]
        self.less_than_is_health3: float = config_dict["less_than_is_health3"]
        self.less_than_is_health4: float = config_dict["less_than_is_health4"]

        self.grow_progress_1: int = int(config_dict["grow_progress_1"])
        self.grow_progress_2: int = int(config_dict["grow_progress_2"])
        self.grow_progress_3: int = int(config_dict["grow_progress_3"])
        self.grow_progress_4: int = int(config_dict["grow_progress_4"])

        self.create_character_event_title: str = config_dict[
            "create_character_event_title"
        ]
        self.create_character_event_story_image: str = config_dict.get(
            "create_character_event_story_image"
        )
        self.create_character_event_story_text: str = config_dict[
            "create_character_event_story_text"
        ]
        self.fresh_water_resource_id: str = config_dict["fresh_water_resource_id"]
        self.liquid_material_id: str = config_dict["liquid_material_id"]
        self.fill_with_material_ids: typing.List[str] = config_dict[
            "fill_with_material_ids"
        ]
        self.default_weight_capacity: float = config_dict["default_weight_capacity"]
        self.default_clutter_capacity: float = config_dict["default_clutter_capacity"]
        self.cheats: typing.Dict[str, typing.List[str]] = config_dict.get("cheats")
        self.create_character_skills: typing.List[str] = config_dict[
            "create_character_skills"
        ]
        self.create_character_knowledges: typing.List[str] = config_dict[
            "create_character_knowledges"
        ]
        self.create_character_knowledges_count: int = config_dict[
            "create_character_knowledges_count"
        ]
        self.create_character_max_points: float = config_dict[
            "create_character_max_points"
        ]
        # FIXME BS NOW: passer les écrans en heure (en fonction de tick_every)
        self.max_action_propose_turns: int = config_dict["max_action_propose_turns"]
        self.tile_clutter_capacity: float = config_dict["tile_clutter_capacity"]
        self.destroy_robustness_per_ap: int = config_dict["destroy_robustness_per_ap"]

        self._character_effects: typing.Dict[
            str, CharacterEffectDescriptionModel
        ] = self._create_character_effects(config_dict)
        self._materials: typing.Dict[
            str, MaterialDescriptionModel
        ] = self._create_materials(config_dict)
        self._resources: typing.Dict[
            str, ResourceDescriptionModel
        ] = self._create_resources(config_dict)
        self._abilities: typing.Dict[str, AbilityDescription] = self._create_ablilities(
            config_dict
        )
        self._builds: typing.Dict[str, BuildDescription] = self._create_builds(
            config_dict
        )
        self._action_descriptions: typing.Dict[
            ActionType, typing.List[ActionDescriptionModel]
        ] = self._create_actions(config_dict)
        self._fill_resource_actions(config_dict)
        self._skills: typing.Dict[str, SkillDescription] = self._create_skills(
            config_dict
        )
        self._knowledge: typing.Dict[
            str, KnowledgeDescription
        ] = self._create_knowledges(config_dict)
        self._resource_mixs: typing.Dict[
            str, ResourceMixDescription
        ] = self._create_resource_mixs(config_dict)

    @property
    def folder_path(self) -> str:
        return self._folder_path

    @property
    def materials(self) -> typing.Dict[str, MaterialDescriptionModel]:
        return self._materials

    @property
    def character_effects(self) -> typing.Dict[str, CharacterEffectDescriptionModel]:
        return self._character_effects

    @property
    def resources(self) -> typing.Dict[str, ResourceDescriptionModel]:
        return self._resources

    @property
    def resource_mixs(self) -> typing.Dict[str, ResourceMixDescription]:
        return self._resource_mixs

    @property
    def actions(self) -> typing.Dict[ActionType, typing.List[ActionDescriptionModel]]:
        return self._action_descriptions

    @property
    def abilities(self) -> typing.Dict[str, AbilityDescription]:
        return self._abilities

    @property
    def builds(self) -> typing.Dict[str, BuildDescription]:
        return self._builds

    @property
    def skills(self) -> typing.Dict[str, SkillDescription]:
        return self._skills

    @property
    def knowledge(self) -> typing.Dict[str, KnowledgeDescription]:
        return self._knowledge

    def _create_character_effects(
        self, config_raw: dict
    ) -> typing.Dict[str, CharacterEffectDescriptionModel]:
        effects: typing.Dict[str, CharacterEffectDescriptionModel] = {}

        for effect_id, effect_raw in config_raw.get("character_effects", {}).items():
            effects[effect_id] = CharacterEffectDescriptionModel(
                id=effect_id,
                attributes_to_false=effect_raw.get("attributes_to_false", []),
                attributes_to_true=effect_raw.get("attributes_to_true", []),
                factors=dict([(a, f) for a, f in effect_raw.get("factors", [])]),
            )

        return effects

    def _create_materials(
        self, config_dict: dict
    ) -> typing.Dict[str, MaterialDescriptionModel]:
        materials: typing.Dict[str, MaterialDescriptionModel] = {}

        for material_id, material_raw in config_dict.get("materials", {}).items():
            materials[material_id] = MaterialDescriptionModel(
                id=material_id, name=material_raw["name"]
            )

        return materials

    def _create_resources(
        self, config_dict: dict
    ) -> typing.Dict[str, ResourceDescriptionModel]:
        resources: typing.Dict[str, ResourceDescriptionModel] = {}

        for resource_id, resource_raw in config_dict.get("resources", {}).items():

            illustration = resource_raw.get("illustration", None)
            if illustration:
                generate_background_media(illustration, self._folder_path)

            resources[resource_id] = ResourceDescriptionModel(
                id=resource_id,
                weight=resource_raw["weight"],
                name=resource_raw["name"],
                material_type=resource_raw["material"],
                unit=Unit(resource_raw["unit"]),
                clutter=resource_raw["clutter"],
                descriptions=[],  # filled after
                illustration=illustration,
                grow_speed=resource_raw.get("grow_speed", None),
                harvest_cost_per_tile=resource_raw.get("harvest_cost_per_tile", None),
                harvest_production_per_tile=resource_raw.get(
                    "harvest_production_per_tile", None
                ),
                drop_to_nowhere=resource_raw.get("drop_to_nowhere", False),
            )

        return resources

    def _create_resource_mixs(
        self, config_dict: dict
    ) -> typing.Dict[str, ResourceMixDescription]:
        resource_mixs: typing.Dict[str, ResourceMixDescription] = {}

        for mix_id, mix_raw in config_dict.get("resource_mix", {}).items():
            required_resources: typing.List[RequiredResourceForMix] = []
            for required_resource_raw in mix_raw["require"]:
                required_resources.append(
                    RequiredResourceForMix(
                        resource=self.resources[required_resource_raw["resource_id"]],
                        coeff=required_resource_raw["coeff"],
                    )
                )
            properties = {}
            fill_base_action_properties(
                RequiredResourceForMix, self, properties, mix_raw
            )

            resource_mixs[mix_id] = ResourceMixDescription(
                id=mix_id,
                required_resources=required_resources,
                produce_resource=self.resources[mix_raw["produce"]],
                cost=mix_raw["cost"],
                properties=properties,
            )

        return resource_mixs

    def _create_actions(
        self, config_raw: dict
    ) -> typing.Dict[ActionType, typing.List[ActionDescriptionModel]]:
        actions: typing.Dict[ActionType, typing.List[ActionDescriptionModel]] = {}

        for action_description_id, action_description_raw in config_raw.get(
            "ACTIONS", {}
        ).items():
            for action_raw in action_description_raw["actions"]:
                action_type = ActionType(action_raw)
                action_class = ActionFactory.actions[action_type]
                actions.setdefault(action_type, []).append(
                    ActionDescriptionModel(
                        id=action_description_id,
                        action_type=action_type,
                        base_cost=action_description_raw["cost"],
                        properties=action_class.get_properties_from_config(
                            game_config=self, action_config_raw=action_description_raw
                        ),
                        name=action_description_raw.get("name"),
                    )
                )

        return actions

    def _fill_resource_actions(self, config_raw: dict) -> None:
        for resource_description in self.resources.values():
            for action_type_id in config_raw["resources"][resource_description.id][
                "actions"
            ]:
                resource_description.descriptions.extend(
                    self.actions[ActionType(action_type_id)]
                )

    def get_resource_mixs_with(
        self, required_resource_ids: typing.List[str]
    ) -> typing.List[ResourceMixDescription]:
        resource_mixs: typing.List[ResourceMixDescription] = []

        for resource_mix_description in self.resource_mixs.values():
            all_in = True

            for required_resource_id in required_resource_ids:
                if (
                    required_resource_id
                    not in resource_mix_description.required_resources_ids
                ):
                    all_in = False

            if all_in:
                resource_mixs.append(resource_mix_description)

        return resource_mixs

    def _create_ablilities(
        self, config_dict: dict
    ) -> typing.Dict[str, AbilityDescription]:
        ablilities: typing.Dict[str, AbilityDescription] = {}

        for ability_id, ability_raw in config_dict.get("ability", {}).items():
            ablilities[ability_id] = AbilityDescription(
                id=ability_id, name=ability_raw["name"]
            )

        return ablilities

    def _create_builds(self, config_dict: dict) -> typing.Dict[str, BuildDescription]:
        builds: typing.Dict[str, BuildDescription] = {}

        for build_id, build_raw in config_dict.get("build", {}).items():
            illustration = build_raw.get("illustration", None)
            if illustration:
                generate_background_media(illustration, self._folder_path)

            builds[build_id] = BuildDescription(
                id=build_id,
                name=build_raw["name"],
                char=build_raw["char"],
                cost=build_raw["cost"],
                building_char=build_raw["building_char"],
                ability_ids=build_raw.get("abilities", []),
                build_require_resources=[
                    BuildBuildRequireResourceDescription(
                        resource_id=r["resource"], quantity=r["quantity"]
                    )
                    for r in build_raw.get("build_require_resources", [])
                ],
                turn_require_resources=[
                    BuildTurnRequireResourceDescription(
                        resource_id=r["resource"], quantity=r["quantity"]
                    )
                    for r in build_raw.get("turn_require_resources", [])
                ],
                power_on_require_resources=[
                    BuildPowerOnRequireResourceDescription(
                        resource_id=r["resource"], quantity=r["quantity"]
                    )
                    for r in build_raw.get("power_on_require_resources", [])
                ],
                classes=build_raw.get("classes", []),
                many=build_raw.get("many", False),
                traversable={
                    TransportType(k): v
                    for k, v in build_raw.get("traversable", {}).items()
                },
                illustration=illustration,
                default_is_on=build_raw.get("default_is_on", True),
                abilities_if_is_on=build_raw.get("abilities_if_is_on", False),
                allow_deposit=build_raw.get("allow_deposit", False),
                allow_deposit_limited=build_raw.get("allow_deposit_limited", False),
                group_name=build_raw.get("group_name", None),
                description=build_raw.get("description", None),
                is_floor=build_raw.get("is_floor", False),
                is_door=bool(build_raw.get("door", None)),
                door_type=build_raw.get("door", None),
                robustness=build_raw.get("robustness"),
            )

        return builds

    def _create_skills(self, config_raw: dict) -> typing.Dict[str, SkillDescription]:
        return {
            skill_id: SkillDescription(
                id=skill_id,
                name=skill_raw["name"],
                default=skill_raw["default"],
                maximum=skill_raw.get("maximum", DEFAULT_MAXIMUM_SKILL),
            )
            for skill_id, skill_raw in config_raw.get("skill", {}).items()
        }

    def _create_knowledges(
        self, config_raw: dict
    ) -> typing.Dict[str, KnowledgeDescription]:
        return {
            knowledge_id: KnowledgeDescription(
                id=knowledge_id,
                name=knowledge_raw["name"],
                ap_required=int(knowledge_raw["ap_required"]),
                instructor_coeff=knowledge_raw.get(
                    "instructor_coeff", DEFAULT_INSTRUCTOR_COEFF
                ),
                abilities=knowledge_raw.get("abilities", []),
                requires=knowledge_raw.get("requires", []),
            )
            for knowledge_id, knowledge_raw in config_raw.get("knowledge", {}).items()
        }


class Game:
    def __init__(self, kernel: "Kernel", config_folder: str) -> None:
        self._kernel = kernel
        self._config = GameConfig(
            self._kernel,
            toml.load(path.join(config_folder, "game.toml")),
            folder_path=config_folder,
        )
        self._stuff = self._create_stuff_manager(
            path.join(config_folder, "stuff.toml"), config=self._config
        )
        self._world = self._create_world_manager(path.join(config_folder, "world.toml"))

    @property
    def config(self) -> GameConfig:
        return self._config

    @property
    def stuff_manager(self) -> StuffManager:
        return self._stuff

    @property
    def world_manager(self) -> WorldManager:
        return self._world

    def _create_stuff_manager(
        self, stuff_file_path: str, config: GameConfig
    ) -> StuffManager:
        items: typing.List[StuffProperties] = []
        raw_stuffs = toml.load(stuff_file_path)

        for stuff_id, stuff_info in raw_stuffs.items():
            full_info = dict(stuff_info)
            full_info.update({"id": stuff_id})
            full_info["material_type"] = full_info.get("material_type", None)

            full_info["descriptions"]: typing.List[ActionDescriptionModel] = []
            for action_type_id in full_info.get("actions", []):
                descriptions = config.actions.get(ActionType(action_type_id), [])
                full_info["descriptions"].extend(descriptions)

            if "actions" in full_info:
                del full_info["actions"]

            illustration: str = full_info.get("illustration", None)
            if illustration:
                generate_background_media(illustration, self._config.folder_path)

            items.append(StuffProperties(**full_info))

        return StuffManager(self._kernel, items)

    def _create_world_manager(self, world_file_path: str) -> WorldManager:
        raw_world = toml.load(world_file_path)
        zones_properties: typing.List[ZoneProperties] = []
        tiles_properties: typing.Dict[
            typing.Type[ZoneMapTileType], ZoneTileProperties
        ] = {}

        for zone_type_str, zone_data in raw_world.get("ZONE_PROPERTIES", {}).items():
            move_cost: float = zone_data["move_cost"]
            generation_info = self._get_generation_info(zone_data)
            resources = list(self._get_zone_resources(zone_data))
            stuffs = list(self._get_zone_stuffs(zone_data))

            world_map_tile_type = WorldMapTileType.get_for_id(zone_type_str)

            illustration = zone_data.get("illustration", None)
            if illustration:
                generate_background_media(illustration, self.config.folder_path)

            zones_properties.append(
                ZoneProperties(
                    world_map_tile_type,
                    generation_info=generation_info,
                    move_cost=move_cost,
                    resources=resources,
                    stuffs=stuffs,
                    description=zone_data.get("description", ""),
                    require_transport_type=world_map_tile_type.require_transport_type,
                    illustration=illustration,
                )
            )

        for tile_type_id, tile_properties_raw in raw_world.get("TILES", {}).items():
            tile_type = ZoneMapTileType.get_all()[tile_type_id]
            tiles_properties[tile_type] = ZoneTileProperties(
                tile_type=tile_type,
                produce=[
                    ZoneMapTileProduction(
                        resource=self.config.resources[produce_raw["resource"]],
                        start_capacity=produce_raw.get("start_capacity", 0.0),
                        regeneration=produce_raw.get("regeneration", 0.0),
                        destroy_when_empty=produce_raw.get("destroy_when_empty", False),
                        infinite=produce_raw.get("infinite", False),
                        extract_cost_per_unit=produce_raw["extract_cost_per_unit"],
                    )
                    for produce_raw in tile_properties_raw["produce"]
                ],
            )

        return WorldManager(
            self._kernel,
            World(zones_properties=zones_properties, tiles_properties=tiles_properties),
        )

    def _get_generation_info(self, zone_data: dict) -> GenerationInfo:
        generation_data = zone_data["GENERATION"]
        count: int = generation_data["count"]

        stuffs: typing.List[ZoneGenerationStuff] = []
        for stuff_id, stuff_generation_info in generation_data.get("STUFF", {}).items():
            probability = stuff_generation_info["probability"]
            meta = dict(
                [
                    item
                    for item in stuff_generation_info.items()
                    if item[0] not in ["probability"]
                ]
            )
            stuff = self._stuff.get_stuff_properties_by_id(stuff_id)
            stuffs.append(
                ZoneGenerationStuff(stuff=stuff, probability=probability, meta=meta)
            )

        return GenerationInfo(count=count, stuffs=stuffs)

    def _get_zone_resources(self, zone_data: dict) -> typing.Iterator[ZoneResource]:
        for resource_id, resource_raw in zone_data.get("RESOURCES", {}).items():
            yield ZoneResource(
                resource_id=resource_id,
                probability=resource_raw["probability"],
                maximum=resource_raw["maximum"],
                regeneration=resource_raw["regeneration"],
            )

    def _get_zone_stuffs(self, zone_data: dict) -> typing.Iterator[ZoneStuff]:
        for resource_id, resource_raw in zone_data.get("STUFFS", {}).items():
            yield ZoneStuff(
                stuff_id=resource_id,
                probability=resource_raw["probability"],
                maximum=resource_raw["maximum"],
                regeneration=resource_raw["regeneration"],
            )

    def get_drink_water_action_description(self) -> ActionDescriptionModel:
        for action_description in self.config.actions[ActionType.DRINK_RESOURCE]:
            if "FRESH_WATER" in [
                r.id for r in action_description.properties.get("accept_resources", [])
            ]:
                return action_description
        raise ConfigurationError("Unable to find drink water action")
