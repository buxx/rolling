# coding: utf-8
POST_CHARACTER_URL = "/character"
TAKE_STUFF_URL = "/character/{character_id}/take/{stuff_id}"
DESCRIBE_LOOT_AT_STUFF_URL = "/_describe/character/{character_id}/look/{stuff_id}"
DESCRIBE_INVENTORY_STUFF_ACTION = (
    "/_describe/character/{character_id}/inventory_look/{stuff_id}"
)
DESCRIBE_STUFF_FILL_WITH_RESOURCE = (
    "/_describe/character/{character_id}/stuff/{stuff_id}/fill/{resource_type}"
)
DESCRIBE_EMPTY_STUFF = "/_describe/character/{character_id}/stuff/{stuff_id}/empty"
DESCRIBE_DRINK_RESOURCE = (
    "/_describe/character/{character_id}/drink_resource/{resource_type}"
)
DESCRIBE_DRINK_STUFF = "/_describe/character/{character_id}/drink_stuff/{stuff_id}"

CHARACTER_ACTION = (
    "/character/{character_id}/action/{action_type}/{action_description_id}"
)
WITH_STUFF_ACTION = (
    "/character/{character_id}/with-stuff-action/{action_type}/{stuff_id}"
)