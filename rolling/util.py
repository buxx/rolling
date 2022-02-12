# coding: utf-8
import dataclasses
import os
from urllib import parse
from urllib.parse import urlencode
from urllib.parse import unquote

from PIL import Image, ImageEnhance
import enum
from os import path
from pathlib import Path
import typing
import shutil

from guilang.description import Description
from guilang.description import Part
from rolling.exception import WrongInputError
from rolling.log import server_logger
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.measure import Unit
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.map.source import ZoneMapSource
    from rolling.model.character import CharacterModel
    from rolling.model.resource import CarriedResourceDescriptionModel
    from rolling.model.stuff import StuffModel


# This constat is used to indicate which code part can be removed when rollgui1 compat is droped
ROLLGUI1_COMPAT = True

ORIGINAL_AVATAR_PATTERN = "character_avatar__original__{avatar_uuid}.png"
ILLUSTRATION_AVATAR_PATTERN = "character_avatar__illustration__{avatar_uuid}.png"
ZONE_THUMB_AVATAR_PATTERN = "character_avatar__zone_thumb__{avatar_uuid}.png"


@dataclasses.dataclass
class EmptyModel:
    pass


def get_on_and_around_coordinates(
    x: int, y: int, distance: int = 1, exclude_on: bool = False
) -> typing.List[typing.Tuple[int, int]]:
    positions = []
    if not exclude_on:
        positions.append((x, y))

    positions.extend(
        [
            (x - distance, y - distance),
            (x, y - distance),
            (x + distance, y - distance),
            (x - distance, y),
            (x + distance, y),
            (x - distance, y + distance),
            (x, y + distance),
            (x + distance, y + distance),
        ]
    )

    return positions


def is_there_resource_id_in_zone(
    kernel: "Kernel", resource_id: str, zone_source: "ZoneMapSource"
) -> bool:
    for row in zone_source.geography.rows:
        for zone_tile_type in row:
            zone_tile_type = typing.cast(typing.Type[ZoneMapTileType], zone_tile_type)

            try:
                productions = kernel.game.world_manager.world.tiles_properties[
                    zone_tile_type
                ].produce
            except KeyError:
                productions = []

            if resource_id in [production.resource.id for production in productions]:
                return True

    return False


def get_stuffs_filled_with_resource_id(
    kernel: "Kernel",
    character_id: str,
    resource_id: str,
    exclude_stuff_ids: typing.Optional[typing.List[int]] = None,
) -> typing.Iterator["StuffModel"]:
    from rolling.server.lib.stuff import StuffLib

    exclude_stuff_ids = exclude_stuff_ids or []

    stuff_lib = StuffLib(kernel=kernel)
    character_stuffs = stuff_lib.get_carried_by(character_id)
    for stuff in character_stuffs:
        if (
            stuff.filled_with_resource == resource_id
            and stuff.id not in exclude_stuff_ids
        ):
            yield stuff


class CornerEnum(enum.Enum):
    TOP = "TOP"
    TOP_RIGHT = "TOP_RIGHT"
    RIGHT = "RIGHT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    BOTTOM = "BOTTOM"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    LEFT = "LEFT"
    TOP_LEFT = "TOP_LEFT"


def get_opposite_zone_place(
    from_: CornerEnum, zone_width: int, zone_height: int
) -> typing.Tuple[int, int]:
    width_part_len = zone_width // 3
    half_width_part_len = width_part_len // 2
    height_part_len = zone_height // 3
    half_height_part_len = height_part_len // 2

    if from_ == CornerEnum.TOP:
        return 0, zone_width // 2

    if from_ == CornerEnum.TOP_RIGHT:
        return (height_part_len * 2) + half_height_part_len, half_width_part_len + 1

    if from_ == CornerEnum.RIGHT:
        return zone_height // 2, zone_width - 1

    if from_ == CornerEnum.BOTTOM_RIGHT:
        return (
            (height_part_len * 2) + half_height_part_len,
            (width_part_len * 2) + half_width_part_len - 1,
        )

    if from_ == CornerEnum.BOTTOM:
        return zone_height - 1, zone_width // 2

    if from_ == CornerEnum.BOTTOM_LEFT:
        return half_height_part_len, ((width_part_len * 2) + half_width_part_len - 1)

    if from_ == CornerEnum.LEFT:
        return zone_height // 2, 0

    if from_ == CornerEnum.TOP_LEFT:
        return half_height_part_len, half_width_part_len + 1

    raise Exception("It is not possible !")


def get_coming_from(
    before_row_i: int, before_col_i: int, after_row_i: int, after_col_i: int
) -> CornerEnum:
    if after_row_i == before_row_i - 1 and after_col_i == before_col_i:
        return CornerEnum.BOTTOM

    if after_row_i == before_row_i - 1 and after_col_i == before_col_i + 1:
        return CornerEnum.TOP_RIGHT

    if after_row_i == before_row_i and after_col_i == before_col_i + 1:
        return CornerEnum.LEFT

    if after_row_i == before_row_i + 1 and after_col_i == before_col_i + 1:
        return CornerEnum.TOP_LEFT

    if after_row_i == before_row_i + 1 and after_col_i == before_col_i:
        return CornerEnum.TOP

    if after_row_i == before_row_i - 1 and after_col_i == before_col_i - 1:
        return CornerEnum.BOTTOM_RIGHT

    if after_row_i == before_row_i and after_col_i == before_col_i - 1:
        return CornerEnum.RIGHT

    if after_row_i == before_row_i + 1 and after_col_i == before_col_i - 1:
        return CornerEnum.BOTTOM_LEFT

    raise Exception("It is not possible !")


def get_corner(
    width: int, height: int, new_row_i: int, new_col_i: int
) -> typing.Optional[CornerEnum]:
    left_col_i_end = width // 3
    right_col_i_start = (width // 3) * 2
    top_row_i_end = height // 3
    bottom_row_i_start = (height // 3) * 2

    more = new_row_i if new_row_i >= 0 else 0

    if new_row_i < top_row_i_end:
        right_col_i = right_col_i_start + more
        left_col_i = left_col_i_end - more
    elif new_row_i >= bottom_row_i_start:
        more = (height // 3) - (new_row_i - bottom_row_i_start + 1)
        more = more if more >= 0 else 0
        right_col_i = right_col_i_start + more
        left_col_i = left_col_i_end - more
    else:
        left_col_i = left_col_i_end
        right_col_i = right_col_i_start

    if new_col_i < left_col_i and new_row_i < top_row_i_end:
        return CornerEnum.TOP_LEFT

    if new_row_i < 0 and left_col_i <= new_col_i < right_col_i:
        return CornerEnum.TOP

    if new_col_i >= right_col_i and new_row_i < top_row_i_end:
        return CornerEnum.TOP_RIGHT

    if new_col_i > (width - 1) and top_row_i_end <= new_row_i < bottom_row_i_start:
        return CornerEnum.RIGHT

    if new_col_i >= right_col_i and new_row_i >= bottom_row_i_start:
        return CornerEnum.BOTTOM_RIGHT

    if new_row_i > (height - 1) and left_col_i_end <= new_col_i < right_col_i_start:
        return CornerEnum.BOTTOM

    if new_col_i < left_col_i and new_row_i >= bottom_row_i_start:
        return CornerEnum.BOTTOM_LEFT

    if new_col_i < 0 and top_row_i_end <= new_row_i < bottom_row_i_start:
        return CornerEnum.LEFT


def filter_action_links(
    links: typing.List[CharacterActionLink],
) -> typing.List[CharacterActionLink]:
    new_links: typing.List[CharacterActionLink] = []
    found_merge_type: typing.List[typing.Any] = []

    for link in links:
        if link.merge_by is None:
            new_links.append(link)
        else:
            if link.merge_by not in found_merge_type:
                new_links.append(link)
                found_merge_type.append(link.merge_by)

    return new_links


def display_g_or_kg(grams: float) -> str:
    if grams < 1000:
        return f"{grams} g"
    return f"{round(grams/1000, 3)} kg"


def quantity_to_str(quantity: float, unit: Unit, kernel: "Kernel") -> str:
    if unit == Unit.GRAM:
        return display_g_or_kg(quantity)
    unit_str = kernel.translation.get(unit)
    quantity = int(quantity) if unit == Unit.UNIT else float(quantity)
    return f"{str(quantity)} {unit_str}"


def is_expect_kg(quantity: float, unit: Unit) -> bool:
    return unit == Unit.GRAM and quantity >= 1000


def adapt_str_quantity(
    quantity: str, unit: Unit, default_unit: Unit, to_str_float: bool = False
) -> str:
    if unit == Unit.GRAM:
        quantity = quantity.lower()
        quantity = quantity.replace(" ", "")
        quantity = quantity.replace(",", ".")
        if quantity.endswith("kg"):
            if not to_str_float:
                return f"{float(quantity[:-2]) * 1000}g"
            return f"{float(quantity[:-2]) * 1000}"
        if quantity.endswith("k"):
            if not to_str_float:
                return f"{float(quantity[:-1]) * 1000}g"
            return f"{float(quantity[:-1]) * 1000}"
        if quantity.endswith("g"):
            if not to_str_float:
                return quantity
            return quantity[:-1]
        if quantity.endswith("l"):
            if not to_str_float:
                return quantity
            return quantity[:-1]
        if default_unit == Unit.KILOGRAM:
            if not to_str_float:
                return f"{float(quantity) * 1000}g"
            return f"{float(quantity) * 1000}"
        return quantity
    return quantity


def str_quantity_unit(quantity: str) -> typing.Optional[Unit]:
    quantity = quantity.lower()
    quantity = quantity.replace(" ", "")
    if quantity.endswith("kg") or quantity.endswith("k"):
        return Unit.KILOGRAM
    if quantity.endswith("g"):
        return Unit.GRAM
    return None


def str_quantity_to_float(quantity: str) -> float:
    quantity = quantity.lower()
    quantity = quantity.replace(" ", "")
    quantity = quantity.replace(",", ".")
    if quantity.endswith("kg"):
        return float(quantity[:-2]) * 1000
    if quantity.endswith("m³"):
        return float(quantity[:-2])
    if quantity.endswith("g") or quantity.endswith("l") or quantity.endswith("u"):
        return float(quantity[:-1])
    return float(quantity)


def get_exception_for_not_enough_ap(
    character: "CharacterModel", cost: float, can_be_back_url: bool = False
) -> WrongInputError:
    return WrongInputError(
        f"{character.name} ne possède plus assez de points d'actions "
        f"({character.action_points} restant et {cost} nécessaires)"
    )


# FIXME BS: replace by iterator on eatable object (to manage all case like invent friends)
def character_can_drink_in_its_zone(
    kernel: "Kernel", character: "CharacterModel"
) -> bool:
    # TODO: consider path finding
    zone_source = kernel.tile_maps_by_position[
        (character.world_row_i, character.world_col_i)
    ].source
    return is_there_resource_id_in_zone(
        kernel, kernel.game.config.fresh_water_resource_id, zone_source
    )


clamp = lambda n, minn, maxn: max(min(maxn, n), minn)


def generate_background_media(media_name: str, folder_path: str) -> None:
    illustration_bg_path = Path(path.join(folder_path, "media", "bg", media_name))
    if not illustration_bg_path.exists():
        Path(folder_path, "media", "bg").mkdir(parents=True, exist_ok=True)
        # Make background illustration
        server_logger.info(f"Generate background image for {media_name}")
        image = Image.open(path.join(folder_path, "media", media_name))
        image = image.convert("RGB")
        alpha = Image.new("L", image.size, 10)
        image.putalpha(alpha)
        image.save(illustration_bg_path)


def generate_avatar_illustration_media(
    source_image_path: str, save_to_path: str
) -> None:
    avatar = Image.open(source_image_path)
    ratio = avatar.height / 300
    avatar.thumbnail((avatar.width * ratio, 300), Image.ANTIALIAS)
    media = Image.new(mode="RGB", size=(768, 300))
    media.paste(avatar, ((768 // 2) - (avatar.width // 2), 0))
    media.save(save_to_path)


def generate_loading_media(source_image_path: str, save_to_path: str) -> None:
    loading = Image.open(source_image_path)
    ratio = loading.width / 768
    loading.thumbnail((768, loading.height * ratio), Image.ANTIALIAS)
    enhancer = ImageEnhance.Brightness(loading)
    loading = enhancer.enhance(0.33)
    loading.save(save_to_path)


def generate_avatar_zone_thumb_media(source_image_path: str, save_to_path: str) -> None:
    avatar = Image.open(source_image_path)
    ratio = avatar.height / 64
    avatar.thumbnail((avatar.width * ratio, 64), Image.ANTIALIAS)
    avatar.save(save_to_path)


def ensure_avatar_medias(kernel: "Kernel", image_source: str, avatar_uuid: str) -> None:
    original_avatar_file_name = ORIGINAL_AVATAR_PATTERN.format(avatar_uuid=avatar_uuid)
    illustration_avatar_file_name = ILLUSTRATION_AVATAR_PATTERN.format(
        avatar_uuid=avatar_uuid
    )
    zone_thumb_avatar_file_name = ZONE_THUMB_AVATAR_PATTERN.format(
        avatar_uuid=avatar_uuid
    )

    source_target = (
        f"{kernel.game.config.folder_path}/media/{original_avatar_file_name}"
    )
    if not os.path.exists(source_target):
        shutil.copy(
            image_source,
            source_target,
        )

    illustration_target = (
        f"{kernel.game.config.folder_path}/media/{illustration_avatar_file_name}"
    )
    if not os.path.exists(illustration_target):
        generate_avatar_illustration_media(
            image_source,
            save_to_path=illustration_target,
        )

    zone_thumb_target = (
        f"{kernel.game.config.folder_path}/media/{zone_thumb_avatar_file_name}"
    )
    if not os.path.exists(zone_thumb_target):
        generate_avatar_zone_thumb_media(
            image_source,
            save_to_path=zone_thumb_target,
        )


@dataclasses.dataclass
class ExpectedQuantityContext:
    display_unit: Unit
    display_unit_name: str
    display_unit_short_name: str
    real_unit: Unit
    default_quantity: str
    carried_quantity_str: str

    @classmethod
    def from_carried_resource(
        cls,
        kernel: "Kernel",
        carried_resource: "CarriedResourceDescriptionModel",
    ) -> "ExpectedQuantityContext":
        expect_kg: bool = is_expect_kg(carried_resource.quantity, carried_resource.unit)
        display_unit = Unit.KILOGRAM if expect_kg else carried_resource.unit
        unit_name = kernel.translation.get(display_unit)
        unit_short_name = kernel.translation.get(display_unit, short=True)
        default_quantity = (
            f"{carried_resource.quantity / 1000} {unit_short_name}"
            if expect_kg
            else f"{carried_resource.quantity} {unit_short_name}"
        )
        carried_quantity_str = quantity_to_str(
            carried_resource.quantity, carried_resource.unit, kernel
        )

        return cls(
            display_unit=display_unit,
            display_unit_name=unit_name,
            display_unit_short_name=unit_short_name,
            real_unit=carried_resource.unit,
            default_quantity=default_quantity,
            carried_quantity_str=carried_quantity_str,
        )

    @property
    def display_kg(self) -> bool:
        return self.display_unit == Unit.KILOGRAM


@dataclasses.dataclass
class InputQuantityContext:
    user_input: str
    user_unit: Unit
    real_quantity: float
    real_unit: Unit

    @classmethod
    def from_carried_resource(
        cls,
        user_input: str,
        carried_resource: "CarriedResourceDescriptionModel",
    ) -> "InputQuantityContext":
        expect_kg: bool = is_expect_kg(carried_resource.quantity, carried_resource.unit)
        default_unit = Unit.KILOGRAM if expect_kg else carried_resource.unit
        user_input = adapt_str_quantity(user_input, carried_resource.unit, default_unit)
        real_quantity = str_quantity_to_float(user_input)
        user_unit = str_quantity_unit(user_input) or default_unit

        return cls(
            user_input=user_input,
            user_unit=user_unit,
            real_quantity=real_quantity,
            real_unit=carried_resource.unit,
        )


def get_health_percent_sentence(percent: int):
    if percent < 10:
        return "Extrêmement abîmé"

    if percent < 25:
        return "Très abîmé"

    if percent < 50:
        return "Bien abîmé"

    if percent < 75:
        return "Abîmé"

    if percent < 90:
        return "Quelque traces d'usures"

    return "Bon état"


def square_walker(
    x: int, y: int
) -> typing.Generator[typing.Tuple[int, int], None, None]:
    yield x, y
    d = 1

    def top_line():
        start_x = 0 - d
        fixed_y = 0 - d
        return [(start_x, fixed_y)] + [
            (start_x + i, fixed_y) for i in range(1, (d * 2) + 1)
        ]

    def right_line():
        fixed_x = 0 + d
        start_y = 0 - d
        return [(fixed_x, start_y + i) for i in range(1, (d * 2) + 1)]

    def bottom_line():
        start_x = 0 + d
        fixed_y = 0 + d
        return [(start_x - i, fixed_y) for i in range(1, (d * 2) + 1)]

    def left_line():
        fixed_x = 0 - d
        start_y = 0 + d
        return [(fixed_x, start_y - i) for i in range(1, (d * 2))]

    while True:
        modifiers = top_line() + right_line() + bottom_line() + left_line()
        for modifier in modifiers:
            yield x + modifier[0], y + modifier[1]
        d += 1


def url_without_zone_coordinates(url: str) -> str:
    parsed_url = parse.urlparse(url)
    query = dict(parse.parse_qsl(parsed_url.query))
    query.pop("row_i", None)
    query.pop("col_i", None)
    query.pop("zone_row_i", None)
    query.pop("zone_col_i", None)
    parsed_url = parsed_url._replace(query=unquote(urlencode(query)))
    url = parsed_url.geturl()
    if "?" not in url:
        url += "?"
    return url
