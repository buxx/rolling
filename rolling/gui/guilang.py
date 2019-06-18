# coding: utf-8
import typing

import serpyco
import urwid

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.client.http.client import HttpClient
from rolling.exception import ClientServerExchangeError
from rolling.exception import RollingError
from rolling.kernel import Kernel
from rolling.log import gui_logger

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller


class Fields:
    def __init__(self) -> None:
        self._fields: typing.Dict[str, typing.Tuple[urwid.Widget, Type]] = {}
        self._post_to: typing.Optional[str] = None

    @property
    def post_to(self) -> str:
        if self._post_to is None:
            raise RollingError("No url provided")
        return self._post_to

    @post_to.setter
    def post_to(self, value: str) -> None:
        self._post_to = value

    def add(self, name: str, widget: urwid.Widget, type: Type) -> None:
        self._fields[name] = widget, type

    def get_as_dict(self) -> dict:
        dict_ = {}
        for field_name, (field, field_type) in self._fields.items():
            value = field.edit_text.strip()
            if value and field_type == Type.STRING:
                dict_[field_name] = field.edit_text
            elif value and field_type == Type.TEXT:
                dict_[field_name] = field.edit_text
            elif value and field_type == Type.NUMBER:
                dict_[field_name] = float(field.edit_text)
            elif field_type == Type.STRING:
                dict_[field_name] = ""
            elif field_type == Type.TEXT:
                dict_[field_name] = ""
            elif field_type == Type.NUMBER:
                dict_[field_name] = 0.0
            else:
                raise NotImplementedError(f"Unknown {field_type}")

        return dict_


class DescriptionWidget(urwid.WidgetWrap):
    def __init__(self, widgets):
        pile = urwid.Pile(widgets)
        fill = urwid.Filler(pile)
        super().__init__(urwid.AttrWrap(fill, ""))


class Generator:
    def __init__(
        self, kernel: Kernel, http_client: HttpClient, controller: "Controller"
    ) -> None:
        self._kernel = kernel
        self._http_client = http_client
        self._controller = controller

    def generate_widget(
        self,
        description: Description,
        success_callback: typing.Callable[[object], None],
        success_serializer: serpyco.Serializer,
    ) -> urwid.Widget:
        fields = Fields()
        widgets = []

        if description.title:
            widgets.append(urwid.Text(description.title))

        def generate_for_items(items: typing.List[Part]):
            widgets_ = []
            for item in items:
                if item.text:
                    widgets_.append(urwid.Text(item.text))
                if item.type_:
                    if item.type_ in (Type.STRING, Type.TEXT, Type.NUMBER):
                        widget = urwid.Edit(item.label + ": ")
                        widgets_.append(widget)
                        fields.add(item.name, widget, item.type_)
                elif item.label:
                    widgets_.append(urwid.Text(item.label))
                if item.items:
                    widgets_.extend(generate_for_items(item.items))
                if item.is_form:
                    widgets_.append(
                        urwid.Button(
                            "Validate",
                            on_press=lambda *_, **__: self.validate_form(
                                widgets, fields, success_callback, success_serializer
                            ),
                        )
                    )
                    fields.post_to = item.form_action
            return widgets_

        widgets.extend(generate_for_items(description.items))
        return DescriptionWidget(widgets)

    def validate_form(
        self,
        widgets,
        fields: Fields,
        success_callback: typing.Callable[[object], None],
        success_serializer: serpyco.Serializer,
    ) -> None:
        data = fields.get_as_dict()
        response = self._http_client.request_post(fields.post_to, data)
        if response.status_code == 400:
            error_message = "!! " + response.json().get("message")

            widgets = list(widgets)  # work with a new list
            widgets.append(urwid.Text(error_message))

            self._controller.view.main_content_container.original_widget = DescriptionWidget(
                widgets
            )
        elif response.status_code == 200:
            success_callback(success_serializer.load(response.json()))
        else:
            error_message = response.json().get("message")
            gui_logger.error(error_message)
            raise ClientServerExchangeError(
                f"Error when communicate with server: {error_message}"
            )
