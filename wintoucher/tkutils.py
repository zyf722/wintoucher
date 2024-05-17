import tkinter as tk
from dataclasses import dataclass, field
from threading import Thread
from tkinter import ttk
from typing import Any, Callable, Dict, List, Literal, Optional, Type, TypedDict, Union

from PIL import Image
from pystray import Icon, Menu, MenuItem  # type: ignore
from pystray._base import Icon as IconType  # type: ignore

WITHDRAWN = "withdrawn"


def create_frame(master: tk.Misc, title: str, padx=10, pady=10, cols=2):
    frame = ttk.Labelframe(master, text=title, padding=(padx, pady))
    for col in range(cols):
        frame.grid_columnconfigure(col, weight=1, minsize=360 // cols)
    return frame


def create_button(master: tk.Misc, text: str, command: Callable):
    button = ttk.Button(
        master,
        text=text,
        command=command,
    )
    return button


def grid_widget(
    widget: tk.Widget,
    row: int,
    col: int,
    sticky: str = "ew",
    padx: int = 5,
    pady: int = 0,
):
    widget.grid(
        row=row,
        column=col,
        sticky=sticky,
        padx=padx,
        pady=pady,
    )


class DetailItem(TypedDict):
    widget_type: Type[tk.Widget]
    params: Dict[str, Any]


DetailDict = Dict[str, DetailItem]


def create_details(master: tk.Misc, details: DetailDict):
    for i, (label_str, widget_item) in enumerate(details.items()):
        label = ttk.Label(master, text=label_str)
        grid_widget(label, i, 0)
        widget = widget_item["widget_type"](master, **widget_item["params"])
        grid_widget(widget, i, 1)


def is_frame(widget: tk.Widget):
    return isinstance(widget, (tk.Frame, tk.LabelFrame, ttk.Frame, ttk.Labelframe))


def toggle_widget(
    widget: tk.Widget,
    state: Optional[Literal["normal", "disabled", "readonly"]] = None,
):
    if state is None:
        state = getattr(widget, "old_state", "normal")
    setattr(widget, "old_state", widget["state"])
    widget.configure(state=state)  # type: ignore


def toggle_state(
    widget: tk.Widget,
    state: Optional[Literal["normal", "disabled", "readonly"]] = None,
):
    if is_frame(widget):
        for child in widget.winfo_children():
            toggle_state(child, state)
    else:
        toggle_widget(widget, state)


@dataclass
class TrayIcon:
    app_name: str
    icon_path: str

    icon: Optional[IconType] = None
    thread: Optional[Thread] = None
    menu_builder: "MenuBuilder" = field(init=False)

    def __post_init__(self):
        self.menu_builder = self.MenuBuilder(self.app_name)

    @dataclass
    class MenuBuilder:
        app_name: str
        menu_items: List[MenuItem] = field(default_factory=list)

        Action = Callable[[IconType, MenuItem], None]

        def __post_init__(self):
            self.menu_items.extend(
                [
                    MenuItem(
                        self.app_name,
                        action=lambda icon, item: None,
                        enabled=False,
                    ),
                    Menu.SEPARATOR,
                ]
            )

        def add_item(
            self,
            text: str,
            action: Action,
            checked: Optional[Union[bool, Callable[[MenuItem], None]]] = None,
            radio: bool = False,
            default: bool = False,
            visible: bool = True,
            enabled: bool = True,
        ):
            self.menu_items.append(
                MenuItem(
                    text,
                    action=lambda icon, item: action(icon, item),
                    checked=checked,
                    radio=radio,
                    default=default,
                    visible=visible,
                    enabled=enabled,
                )
            )

        def build(self):
            return Menu(*self.menu_items)

    def create_icon(self):
        self.icon = Icon(
            self.app_name,
            Image.open(self.icon_path),
            menu=self.menu_builder.build(),
        )
        self.thread = Thread(
            daemon=True,
            target=self.icon.run,
        )
        self.thread.start()

    def stop(self):
        if self.icon is not None and self.thread is not None:
            self.icon.visible = False
            self.icon.stop()

    def notify(self, message: str):
        if self.icon is not None:
            self.icon.notify(message, title=self.app_name)
