# coding: utf-8
import dataclasses

import abc
from collections import defaultdict
import math
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.stuff import StuffModel
from rolling.server.util import get_round_resource_quantity
from rolling.util import ExpectedQuantityContext
from rolling.util import InputQuantityContext

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class TransferStuffOrResources(abc.ABC):
    stuff_quantity_parameter_name = "stuff_quantity"
    resource_quantity_parameter_name = "resource_quantity"

    @property
    @abc.abstractmethod
    def _kernel(self) -> "Kernel":
        pass

    @abc.abstractmethod
    def _get_available_stuffs(self) -> typing.List[StuffModel]:
        pass

    @abc.abstractmethod
    def _get_available_resources(self) -> typing.List[CarriedResourceDescriptionModel]:
        pass

    @abc.abstractmethod
    def _get_url(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
    ) -> str:
        pass

    @abc.abstractmethod
    def _get_title(
        self, stuff_id: typing.Optional[int] = None, resource_id: typing.Optional[str] = None
    ) -> str:
        pass

    @abc.abstractmethod
    def _get_footer_character_id(self, sizing_up_quantity: bool) -> typing.Optional[str]:
        pass

    def _get_footer_links(self, sizing_up_quantity: bool) -> typing.List[Part]:
        return []

    @abc.abstractmethod
    def _get_footer_affinity_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        pass

    @abc.abstractmethod
    def _get_footer_build_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        pass

    @abc.abstractmethod
    def _get_stuff(self, stuff_id: int) -> StuffModel:
        pass

    @abc.abstractmethod
    def _get_likes_this_stuff(self, stuff_id: str) -> typing.List[StuffModel]:
        pass

    @abc.abstractmethod
    def _transfer_stuff(self, stuff_id: int) -> None:
        pass

    @abc.abstractmethod
    def _get_carried_resource(self, resource_id: str) -> CarriedResourceDescriptionModel:
        pass

    @abc.abstractmethod
    def check_can_transfer_stuff(self, stuff_id: int, quantity: int = 1) -> None:
        pass

    @abc.abstractmethod
    def check_can_transfer_resource(self, resource_id: str, quantity: float) -> None:
        pass

    @abc.abstractmethod
    def _transfer_resource(self, resource_id: str, quantity: float) -> None:
        pass

    def _get_stuff_name(self, stuff: StuffModel) -> str:
        return stuff.name

    def _get_resource_name(self, resource: CarriedResourceDescriptionModel) -> str:
        return resource.name

    def _get_choose_something_description(
        self,
        can_be_back_url: bool = False,
        text_parts: typing.Optional[typing.List[Part]] = None,
    ) -> Description:
        text_parts = text_parts or []
        parts = text_parts
        carried_stuffs = self._get_available_stuffs()
        carried_resources = self._get_available_resources()

        displayed_stuff_ids: typing.List[str] = []
        for carried_stuff in carried_stuffs:
            if carried_stuff.stuff_id not in displayed_stuff_ids:
                parts.append(
                    Part(
                        is_link=True,
                        label=self._get_stuff_name(carried_stuff),
                        form_action=self._get_url(stuff_id=carried_stuff.id),
                    )
                )
                displayed_stuff_ids.append(carried_stuff.stuff_id)

        for carried_resource in carried_resources:
            parts.append(
                Part(
                    is_link=True,
                    label=self._get_resource_name(carried_resource),
                    form_action=self._get_url(resource_id=carried_resource.id),
                )
            )

        return Description(
            title=self._get_title(),
            items=parts,
            footer_with_character_id=self._get_footer_character_id(False),
            footer_with_affinity_id=self._get_footer_affinity_id(False),
            footer_with_build_id=self._get_footer_build_id(False),
            footer_links=self._get_footer_links(False),
            can_be_back_url=can_be_back_url,
        )

    def get_description(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[str] = None,
    ) -> Description:
        can_be_back_url = True
        text_parts: typing.List[Part] = []

        if stuff_id is not None:
            stuff = self._get_stuff(stuff_id)
            stuff_description = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                stuff.stuff_id
            )
            likes_this_stuff = self._get_likes_this_stuff(stuff.stuff_id)

            if stuff_quantity is None:
                if len(likes_this_stuff) > 1:
                    return Description(
                        title=self._get_title(stuff_id=stuff_id),
                        items=[
                            Part(
                                is_form=True,
                                form_values_in_query=True,
                                form_action=self._get_url(stuff_id=stuff_id),
                                submit_label="Valider",
                                items=[
                                    Part(
                                        label="Quantité ?",
                                        type_=Type.NUMBER,
                                        name=self.stuff_quantity_parameter_name,
                                        default_value=str(len(likes_this_stuff)),
                                    )
                                ],
                            )
                        ],
                        footer_with_character_id=self._get_footer_character_id(False),
                        footer_with_affinity_id=self._get_footer_affinity_id(False),
                        footer_with_build_id=self._get_footer_build_id(False),
                        footer_links=self._get_footer_links(False),
                        can_be_back_url=True,
                    )
                stuff_quantity = 1

            for i in range(stuff_quantity):
                can_be_back_url = False
                self.check_can_transfer_stuff(likes_this_stuff[i].id)
                self._transfer_stuff(likes_this_stuff[i].id)

            text_parts.append(
                Part(text=(f"Vous avez transféré {stuff_quantity} {stuff_description.name}"))
            )

        if resource_id is not None:
            resource_description = self._kernel.game.config.resources[resource_id]
            carried_resource = self._get_carried_resource(resource_id)
            expected_quantity_context = ExpectedQuantityContext.from_carried_resource(
                self._kernel, carried_resource
            )

            if resource_quantity is None:
                return Description(
                    title=self._get_title(resource_id=resource_id),
                    items=[
                        Part(
                            is_form=True,
                            form_values_in_query=True,
                            form_action=self._get_url(resource_id=resource_id),
                            submit_label="Valider",
                            items=[
                                Part(
                                    label=f"Quantité ({expected_quantity_context.display_unit_name}) ?",
                                    type_=Type.NUMBER,
                                    name=self.resource_quantity_parameter_name,
                                    default_value=expected_quantity_context.default_quantity,
                                )
                            ],
                        )
                    ],
                    footer_with_character_id=self._get_footer_character_id(False),
                    footer_with_affinity_id=self._get_footer_affinity_id(False),
                    footer_with_build_id=self._get_footer_build_id(False),
                    footer_links=self._get_footer_links(False),
                    can_be_back_url=True,
                )

            user_input_context = InputQuantityContext.from_carried_resource(
                user_input=resource_quantity,
                carried_resource=carried_resource,
            )
            self.check_can_transfer_resource(
                resource_id=resource_id, quantity=user_input_context.real_quantity
            )
            self._transfer_resource(
                resource_id=resource_id, quantity=user_input_context.real_quantity
            )
            can_be_back_url = False

            user_unit_str = self._kernel.translation.get(user_input_context.user_unit)
            text_parts.append(
                Part(
                    text=(
                        f"Vous avez transféré {user_input_context.user_input} {user_unit_str} "
                        f"{resource_description.name}"
                    )
                )
            )

        return self._get_choose_something_description(
            can_be_back_url=can_be_back_url, text_parts=text_parts
        )


@dataclasses.dataclass
class StuffLine:
    stuff: StuffModel
    movable: bool


@dataclasses.dataclass
class ResourceLine:
    resource: CarriedResourceDescriptionModel
    movable: bool


class BiDirectionalTransferByUrl(abc.ABC):
    @property
    @abc.abstractmethod
    def _kernel(self) -> "Kernel":
        pass

    @abc.abstractmethod
    def _get_default_left_partial_quantity(self, resource_id: str) -> typing.Optional[float]:
        pass

    @abc.abstractmethod
    def _get_default_right_partial_quantity(self, resource_id: str) -> typing.Optional[float]:
        pass

    @abc.abstractmethod
    def _get_title(self) -> str:
        pass

    @abc.abstractmethod
    def _get_left_title(self) -> str:
        pass

    @abc.abstractmethod
    def _get_right_title(self) -> str:
        pass

    @abc.abstractmethod
    def _get_left_stuffs(self) -> typing.List[StuffLine]:
        pass

    @abc.abstractmethod
    def _get_right_stuffs(self) -> typing.List[StuffLine]:
        pass

    @abc.abstractmethod
    def _get_left_resources(self) -> typing.List[ResourceLine]:
        pass

    @abc.abstractmethod
    def _get_right_resources(self) -> typing.List[ResourceLine]:
        pass

    @abc.abstractmethod
    def _get_move_stuff_right_url(
        self,
        stuff_id: int,
        stuff_quantity: typing.Optional[int] = None,
        partial_quantities: typing.Optional[typing.Dict[str, float]] = None,
    ) -> str:
        pass

    @abc.abstractmethod
    def _get_move_stuff_left_url(
        self,
        stuff_id: int,
        stuff_quantity: typing.Optional[int] = None,
        partial_quantities: typing.Optional[typing.Dict[str, float]] = None,
    ) -> str:
        pass

    @abc.abstractmethod
    def _get_move_resource_right_url(
        self,
        resource_id: str,
        resource_quantity: typing.Optional[str] = None,
        partial_quantities: typing.Optional[typing.Dict[str, float]] = None,
    ) -> str:
        pass

    @abc.abstractmethod
    def _get_move_resource_left_url(
        self,
        resource_id: str,
        resource_quantity: typing.Optional[str] = None,
        partial_quantities: typing.Optional[typing.Dict[str, float]] = None,
    ) -> str:
        pass

    def get_description(self) -> Description:
        title = self._get_title()
        left_title = self._get_left_title()
        right_title = self._get_right_title()

        left_stuff_lines = self._get_left_stuffs()
        right_stuff_lines = self._get_right_stuffs()
        left_resource_lines = self._get_left_resources()
        right_resource_lines = self._get_right_resources()

        partial_quantities: typing.Dict[str, float] = {}
        for left_resource_line in left_resource_lines:
            partial_quantities[
                f"left_{left_resource_line.resource.id}"
            ] = self._get_default_left_partial_quantity(left_resource_line.resource.id) or str(
                get_round_resource_quantity(left_resource_line.resource.quantity)
            )
        for right_resource_line in right_resource_lines:
            partial_quantities[
                f"right_{right_resource_line.resource.id}"
            ] = self._get_default_right_partial_quantity(right_resource_line.resource.id) or str(
                get_round_resource_quantity(right_resource_line.resource.quantity)
            )

        left_parts_column = Part(
            is_column=True,
            colspan=1,
            items=[
                Part(text=left_title, classes=["h2"]),
                Part(text="Objets", classes=["h3"]),
            ],
        )
        right_parts_column = Part(
            is_column=True,
            colspan=1,
            items=[Part(text=right_title, classes=["h2"]), Part(text="Objets", classes=["h3"])],
        )

        left_parts_column.items.extend(
            self._create_stuff_parts(
                stuff_lines=left_stuff_lines,
                generate_url_func=self._get_move_stuff_right_url,
                side="left",
                link_class_suffix="right",
                partial_quantities=partial_quantities,
            )
        )
        right_parts_column.items.extend(
            self._create_stuff_parts(
                stuff_lines=right_stuff_lines,
                generate_url_func=self._get_move_stuff_left_url,
                side="right",
                link_class_suffix="left",
                partial_quantities=partial_quantities,
            )
        )

        left_parts_column.items.append(Part(text="Ressources", classes=["h3"]))
        left_parts_column.items.extend(
            self._create_resource_parts(
                resource_lines=left_resource_lines,
                generate_url_func=self._get_move_resource_right_url,
                side="left",
                link_class_suffix="right",
                partial_quantities=partial_quantities,
            )
        )
        right_parts_column.items.append(Part(text="Ressources", classes=["h3"]))
        right_parts_column.items.extend(
            self._create_resource_parts(
                resource_lines=right_resource_lines,
                generate_url_func=self._get_move_resource_left_url,
                side="right",
                link_class_suffix="left",
                partial_quantities=partial_quantities,
            )
        )

        return Description(
            title=title,
            items=[
                Part(
                    columns=2,
                    items=[
                        left_parts_column,
                        right_parts_column,
                    ],
                )
            ],
        )

    def _create_stuff_parts(
        self,
        stuff_lines: typing.List[StuffLine],
        generate_url_func: typing.Callable[
            [int, typing.Optional[int], typing.Optional[typing.Dict[str, float]]], str
        ],
        side: str,
        link_class_suffix: str,
        partial_quantities: typing.Dict[str, float],
    ) -> typing.List[Part]:
        assert side in ("left", "right")
        assert link_class_suffix in ("left", "right")
        parts: typing.List[Part] = []

        displayed_stuff_ids: typing.Set[str] = set()
        stuff_count: typing.Dict[str, int] = defaultdict(lambda: 0)

        for stuff_line in stuff_lines:
            stuff_count[stuff_line.stuff.stuff_id] += 1

        for stuff_line in stuff_lines:
            if (
                stuff_line.stuff.stuff_id in displayed_stuff_ids
                and not stuff_line.stuff.under_construction
            ):
                continue
            displayed_stuff_ids.add(stuff_line.stuff.stuff_id)
            if not stuff_line.stuff.under_construction:
                stuff_name = (
                    f"{stuff_count[stuff_line.stuff.stuff_id]} {stuff_line.stuff.get_name()}"
                )
            else:
                stuff_name = stuff_line.stuff.get_name()

            if not stuff_line.movable:
                parts.append(Part(text=stuff_name))
            else:
                partial_url = generate_url_func(
                    stuff_line.stuff.id,
                    1,
                    partial_quantities,
                )
                all_url = generate_url_func(
                    stuff_line.stuff.id,
                    stuff_count[stuff_line.stuff.stuff_id]
                    if not stuff_line.stuff.under_construction
                    else 1,
                    partial_quantities,
                )

                button_part = Part(
                    is_column=True,
                    colspan=8,
                    items=[
                        Part(
                            label=stuff_name,
                            is_link=True,
                            form_action=generate_url_func(
                                stuff_line.stuff.id,
                                None,
                                partial_quantities,
                            ),
                        )
                    ],
                )

                partial_part = Part(
                    is_column=True,
                    items=[
                        Part(
                            label=partial_url,
                            is_link=True,
                            form_action=partial_url,
                            classes=[f"partial_{link_class_suffix}"],
                        )
                    ],
                )

                complete_part = Part(
                    is_column=True,
                    items=[
                        Part(
                            label=all_url,
                            is_link=True,
                            form_action=all_url,
                            classes=[link_class_suffix],
                        )
                    ],
                )

                if link_class_suffix == "left":
                    items = [complete_part, partial_part, button_part]
                else:
                    items = [button_part, partial_part, complete_part]

                parts.append(
                    Part(
                        columns=10,
                        items=items,
                    )
                )

        return parts

    def _create_resource_parts(
        self,
        resource_lines: typing.List[ResourceLine],
        generate_url_func: typing.Callable[
            [str, typing.Optional[str], typing.Optional[typing.Dict[str, float]]], str
        ],
        side: str,
        link_class_suffix: str,
        partial_quantities: typing.Dict[str, float],
    ) -> typing.List[Part]:
        assert side in ("left", "right")
        assert link_class_suffix in ("left", "right")
        parts: typing.List[Part] = []
        resource_quantities: typing.Dict[str, float] = defaultdict(lambda: 0.0)
        not_movable_resource_quantities: typing.Dict[str, float] = defaultdict(lambda: 0.0)

        for resource_line in resource_lines:
            if resource_line.movable:
                resource_quantities[resource_line.resource.id] += resource_line.resource.quantity
            else:
                not_movable_resource_quantities[
                    resource_line.resource.id
                ] += resource_line.resource.quantity

        for resource_id, resource_quantity in resource_quantities.items():
            resource_description = self._kernel.game.config.resources[resource_id]
            unit_str = self._kernel.translation.get(resource_description.unit, short=True)
            text = f"{resource_quantity}{unit_str} {resource_description.name}"
            partial_quantity = partial_quantities[f"{side}_{resource_id}"]
            # Exclude default quantity of this resource to permit new calculate
            this_partial_quantities = {
                k: v
                for k, v in partial_quantities.items()
                if k != f"{link_class_suffix}_{resource_id}"
            }
            partial_url = generate_url_func(
                resource_id,
                f"{partial_quantity}{unit_str}",
                this_partial_quantities,
            )
            all_url = generate_url_func(
                resource_id,
                f"{resource_quantity}{unit_str}",
                this_partial_quantities,
            )
            partial_part = Part(
                is_column=True,
                colspan=1,
                items=[
                    Part(
                        label=partial_url,
                        is_link=True,
                        form_action=partial_url,
                        classes=[f"partial_{link_class_suffix}"],
                    )
                ],
            )
            complete_part = Part(
                is_column=True,
                colspan=1,
                items=[
                    Part(
                        label=all_url,
                        is_link=True,
                        form_action=all_url,
                        classes=[link_class_suffix],
                    )
                ],
            )
            button_part = Part(
                is_column=True,
                colspan=8,
                items=[
                    Part(
                        label=text,
                        is_link=True,
                        form_action=generate_url_func(
                            resource_id,
                            None,
                            this_partial_quantities,
                        ),
                    )
                ],
            )
            if link_class_suffix == "left":
                items = [complete_part, partial_part, button_part]
            else:
                items = [button_part, partial_part, complete_part]

            parts.append(
                Part(
                    columns=10,
                    items=items,
                )
            )

        for resource_id, resource_quantity in not_movable_resource_quantities.items():
            resource_description = self._kernel.game.config.resources[resource_id]
            unit_str = self._kernel.translation.get(resource_description.unit, short=True)
            text = f"{resource_quantity}{unit_str}"
            parts.append(Part(text=text))

        return parts
