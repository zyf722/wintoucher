from dataclasses import dataclass, field
from threading import Thread
from typing import Callable, List, Optional, Union

from PIL import Image
from pystray import Icon, Menu, MenuItem  # type: ignore
from pystray._base import Icon as IconType  # type: ignore


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
