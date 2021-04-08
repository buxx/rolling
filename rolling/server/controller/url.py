# coding: utf-8
POST_CHARACTER_URL = "/character"
DESCRIBE_LOOK_AT_STUFF_URL = "/_describe/character/{character_id}/look/{stuff_id}"
DESCRIBE_LOOK_AT_RESOURCE_URL = (
    "/_describe/character/{character_id}/look/{resource_id}/{row_i},{col_i}"
)
DESCRIBE_LOOK_AT_CHARACTER_URL = (
    "/_describe/character/{character_id}/look-character/{with_character_id}"
)
DESCRIBE_INVENTORY_STUFF_ACTION = "/_describe/character/{character_id}/inventory_look/{stuff_id}"
DESCRIBE_INVENTORY_RESOURCE_ACTION = (
    "/_describe/character/{character_id}/resource_look/{resource_id}"
)
DESCRIBE_STUFF_FILL_WITH_RESOURCE = (
    "/_describe/character/{character_id}/stuff/{stuff_id}/fill/{resource_id}"
)
DESCRIBE_EMPTY_STUFF = "/_describe/character/{character_id}/stuff/{stuff_id}/empty"
DESCRIBE_DRINK_RESOURCE = "/_describe/character/{character_id}/drink_resource/{resource_id}"
DESCRIBE_DRINK_STUFF = "/_describe/character/{character_id}/drink_stuff/{stuff_id}"

CHARACTER_ACTION = "/character/{character_id}/action/{action_type}/{action_description_id}"
# TODO BS: {action_type} is useless
WITH_STUFF_ACTION = (
    "/character/{character_id}/with-stuff-action/{action_type}/{stuff_id}/{action_description_id}"
)
WITH_BUILD_ACTION = (
    "/character/{character_id}/with-build-action/{action_type}/{build_id}/{action_description_id}"
)
WITH_RESOURCE_ACTION = (
    "/character/{character_id}/with-resource-action/{action_type}"
    "/{resource_id}/{action_description_id}"
)
WITH_CHARACTER_ACTION = (
    "/character/{character_id}/with-character-action/{action_type}"
    "/{with_character_id}/{action_description_id}"
)
DESCRIBE_BUILD = "/character/{character_id}/build/{build_id}"
