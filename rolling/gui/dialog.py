# coding: utf-8
import typing
import urwid

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller
    from rolling.kernel import Kernel


class FullContentDialog(urwid.WidgetWrap):
    def __init__(
        self, title: str, text: str, get_buttons: typing.Callable[[], typing.List[urwid.Button]]
    ):
        title_widget = urwid.Text(title)
        text_widget = urwid.Text(text)
        buttons = get_buttons()
        pile = urwid.Pile([title_widget, text_widget] + buttons)
        fill = urwid.Filler(pile)

        super().__init__(urwid.AttrWrap(fill, ""))


class SimpleDialog(FullContentDialog):
    def __init__(
        self,
        kernel: "Kernel",
        controller: "Controller",
        original_widget: urwid.Widget,
        title: str,
        text: typing.Optional[str] = None,
        go_back: bool = False,
    ) -> None:
        self._kernel = kernel
        self._controller = controller
        self._original_widget = original_widget
        self._go_back = go_back
        super().__init__(title=title, text=text or "", get_buttons=self._get_buttons)

    def _get_buttons(self) -> typing.List[urwid.Button]:
        if not self._go_back:
            return []

        def cancel(*args, **kwargs):
            self._controller.view.main_content_container.original_widget = self._original_widget

        return [urwid.Button("Fermer", on_press=cancel)]
