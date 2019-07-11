# coding: utf-8
import json
import typing

import serpyco
import urwid

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.client.http.client import HttpClient
from rolling.exception import ClientServerExchangeError
from rolling.exception import RollingError
from rolling.gui.image.widget import ImageWidget
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
    def __init__(self, widgets, as_list: bool = False):
        pile = urwid.Pile(widgets)

        if as_list:
            widget = urwid.ListBox(widgets)
        else:
            widget = urwid.Filler(pile)
        super().__init__(urwid.AttrWrap(widget, ""))


class Generator:
    def __init__(
        self, kernel: Kernel, http_client: HttpClient, controller: "Controller"
    ) -> None:
        self._kernel = kernel
        self._http_client = http_client
        self._controller = controller
        self._serializer = serpyco.Serializer(Description)

    def generate_widget(
        self,
        description: Description,
        success_callback: typing.Optional[typing.Callable[[object], None]] = None,
        success_serializer: typing.Optional[serpyco.Serializer] = None,
    ) -> urwid.Widget:
        fields = Fields()

        def generate_for_items(items: typing.List[Part]):
            widgets_ = []
            for item in items:
                if item.text and item.label and not item.type_:
                    widgets_.append(urwid.Text(f"{item.label}: {item.text}"))
                elif (
                    item.text and not item.label and not item.type_ and not item.is_link
                ):
                    widgets_.append(urwid.Text(item.text))
                elif item.text and item.is_link:
                    widgets_.append(
                        urwid.Button(
                            item.text,
                            on_press=lambda button, url: self.follow_link(url),
                            user_data=item.form_action,
                        )
                    )
                elif item.label and item.go_back_zone:
                    widgets_.append(
                        urwid.Button(
                            item.label,
                            on_press=lambda *_, **__: self._controller.display_zone(),
                        )
                    )
                elif item.type_:
                    if item.type_ in (Type.STRING, Type.TEXT, Type.NUMBER):
                        widget = urwid.Edit(item.label + ": ")
                        widgets_.append(widget)
                        fields.add(item.name, widget, item.type_)

                if item.items:
                    widgets_.extend(generate_for_items(item.items))

                if item.is_form:
                    if success_callback is None or success_serializer is None:
                        raise RollingError(
                            "success_callback and success_serializer must be set for forms"
                        )

                    widgets_.append(
                        urwid.Button(
                            "Validate",
                            # TODO BS 2019-07-04: manage one form at once
                            # (see user_data usage previously)
                            on_press=lambda *_, **__: self.validate_form(
                                widgets, fields, success_callback, success_serializer
                            ),
                        )
                    )
                    fields.post_to = item.form_action
            return widgets_

        widgets = []

        if description.is_long_text:
            widgets.append(urwid.Text(description.title))
            for part in description.items:
                widgets.append(urwid.Text(part.text))
            return DescriptionWidget(widgets, as_list=True)

        if description.title:
            widgets.append(urwid.Text(description.title))
        widgets.extend(generate_for_items(description.items))

        description_widget = DescriptionWidget(widgets)

        if description.image:

            def callback():
                self._controller.view.main_content_container.original_widget = (
                    description_widget
                )

            # TODO BS 2019-06-30: Manage download media from server
            return ImageWidget("game/media/" + description.image, callback=callback)

        return description_widget

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

    def follow_link(self, url: str) -> None:
        response = self._http_client.request_post(url)
        if response.status_code in (200, 204):

            try:
                response_json = response.json()
            # TODO BS 2019-06-30: Ensure always a json response (except 204)
            except json.decoder.JSONDecodeError:
                self._controller.display_zone()
                return

            description = self._serializer.load(response_json)
            new_main_widget = self.generate_widget(description)
            self._controller.view.main_content_container.original_widget = (
                new_main_widget
            )

        else:
            error_message = response.json().get("message")
            error_detail = response.json()["details"].get("traceback")
            gui_logger.error(error_message)
            raise ClientServerExchangeError(
                f"Error when communicate with server: {error_message} ({error_detail})"
            )
