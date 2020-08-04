# coding: utf-8
import abc
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.stuff import StuffModel

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
    def _get_footer_links(self, sizing_up_quantity: bool) -> typing.List[Part]:
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

    def _get_choose_something_description(self,) -> Description:
        parts = []
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
            footer_links=self._get_footer_links(False),
            can_be_back_url=True,
        )

    def get_description(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
    ) -> Description:
        if stuff_id is not None:
            stuff = self._get_stuff(stuff_id)
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
                        can_be_back_url=True,
                    )
                stuff_quantity = 1

            for i in range(stuff_quantity):
                self.check_can_transfer_stuff(likes_this_stuff[i].id)
                self._transfer_stuff(likes_this_stuff[i].id)

        if resource_id is not None:
            resource_description = self._kernel.game.config.resources[resource_id]
            carried_resource = self._get_carried_resource(resource_id)

            if resource_quantity is None:
                unit_str = self._kernel.translation.get(resource_description.unit)
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
                                    label=f"Quantité ({unit_str}) ?",
                                    type_=Type.NUMBER,
                                    name=self.resource_quantity_parameter_name,
                                    default_value=str(carried_resource.quantity),
                                )
                            ],
                        )
                    ],
                    can_be_back_url=True,
                )
            self.check_can_transfer_resource(resource_id=resource_id, quantity=resource_quantity)
            self._transfer_resource(resource_id=resource_id, quantity=resource_quantity)

        return self._get_choose_something_description()
