# coding: utf-8
import abc
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.stuff import StuffModel
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
