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
    """
    Create a labelframe with a title and padding.

    Args:
        master (tk.Misc): The parent widget.
        title (str): The title of the labelframe.
        padx (int, optional): The padding in the x direction. Defaults to `10`.
        pady (int, optional): The padding in the y direction. Defaults to `10`.
        cols (int, optional): The number of columns in the grid. Defaults to `2`.

    Returns:
        ttk.Labelframe: The created labelframe.
    """
    frame = ttk.Labelframe(master, text=title, padding=(padx, pady))
    for col in range(cols):
        frame.grid_columnconfigure(col, weight=1, minsize=360 // cols)
    return frame


def create_button(master: tk.Misc, text: str, command: Callable):
    """
    Create a button with the given text and command.

    Args:
        master (tk.Misc): The parent widget.
        text (str): The text of the button.
        command (Callable): The command to run when the button is clicked.

    Returns:
        ttk.Button: The created button.
    """
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
    """
    Grid a widget with the given row, column, and padding.

    Args:
        widget (tk.Widget): The widget to grid.
        row (int): The row to grid the widget in.
        col (int): The column to grid the widget in.
        sticky (str, optional): The sticky value. Defaults to `"ew"`.
        padx (int, optional): The padding in the x direction. Defaults to `5`.
        pady (int, optional): The padding in the y direction. Defaults to `0`.
    """
    widget.grid(
        row=row,
        column=col,
        sticky=sticky,
        padx=padx,
        pady=pady,
    )


class DetailItem(TypedDict):
    """
    A dictionary representing a detail item, which would be shown in detail view of the control panel.
    """

    widget_type: Type[tk.Widget]
    params: Dict[str, Any]


DetailDict = Dict[str, DetailItem]
"""
A dictionary representing a detail view, which would be shown in the control panel.
"""


def create_details(master: tk.Misc, details: DetailDict):
    """
    Create a detail view with the given details.

    Args:
        master (tk.Misc): The parent widget.
        details (DetailDict): The details to show in the detail view.
    """
    for i, (label_str, widget_item) in enumerate(details.items()):
        label = ttk.Label(master, text=label_str)
        grid_widget(label, i, 0)
        widget = widget_item["widget_type"](master, **widget_item["params"])
        grid_widget(widget, i, 1)


def is_frame(widget: tk.Widget):
    """
    Check if the given widget is a frame.

    Args:
        widget (tk.Widget): The widget to check.

    Returns:
        bool: `True` if the widget is a frame, `False` otherwise.
    """
    return isinstance(widget, (tk.Frame, tk.LabelFrame, ttk.Frame, ttk.Labelframe))


def toggle_widget(
    widget: tk.Widget,
    state: Optional[Literal["normal", "disabled", "readonly"]] = None,
):
    """
    Toggle the state of the given widget.

    Args:
        widget (tk.Widget): The widget to toggle the state of.
        state (Optional[Literal["normal", "disabled", "readonly"]], optional): The state to set the widget to. Defaults to `None`.
    """
    if state is None:
        state = getattr(widget, "old_state", "normal")
    setattr(widget, "old_state", widget["state"])
    widget.configure(state=state)  # type: ignore


def toggle_state(
    widget: tk.Widget,
    state: Optional[Literal["normal", "disabled", "readonly"]] = None,
):
    """
    Toggle the state of the given widget and its children.

    If the widget is a frame, the state of all its children will be toggled as well.

    Args:
        widget (tk.Widget): The widget to toggle the state of.
        state (Optional[Literal["normal", "disabled", "readonly"]], optional): The state to set the widget to. Defaults to `None`.
    """
    if is_frame(widget):
        for child in widget.winfo_children():
            toggle_state(child, state)
    else:
        toggle_widget(widget, state)


@dataclass
class TrayIcon:
    """
    A class to manage a tray icon.
    """

    app_name: str
    icon_path: str

    icon: Optional[IconType] = None
    thread: Optional[Thread] = None
    menu_builder: "MenuBuilder" = field(init=False)

    def __post_init__(self):
        self.menu_builder = self.MenuBuilder(self.app_name)

    @dataclass
    class MenuBuilder:
        """
        Builder class to create a menu for the tray icon.
        """

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
            """
            Add an item to the menu.

            Args:
                text (str): The text of the item.
                action (Action): The action to run when the item is clicked.
                checked (Optional[Union[bool, Callable[[MenuItem], None]]], optional): The checked state of the item. Defaults to `None`.
                radio (bool, optional): Whether the item is a radio item. Defaults to `False`.
                default (bool, optional): Whether the item is the default item. Defaults to `False`.
                visible (bool, optional): Whether the item is visible. Defaults to `True`.
                enabled (bool, optional): Whether the item is enabled. Defaults to `True`.
            """
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
            """
            Build the menu.

            Returns:
                Menu: The built menu.
            """
            return Menu(*self.menu_items)

    def create_icon(self):
        """
        Create the tray icon.

        This will create the icon and start the icon thread.
        """
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
        """
        Stop the tray icon.
        """
        if self.icon is not None and self.thread is not None:
            self.icon.visible = False
            self.icon.stop()

    def notify(self, message: str):
        """
        Notify the user with a message.

        Args:
            message (str): The message to show.
        """
        if self.icon is not None:
            self.icon.notify(message, title=self.app_name)
