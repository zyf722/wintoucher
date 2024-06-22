import json
import os
import tkinter as tk
from json import JSONDecoder, JSONEncoder
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, Type

from pynput.keyboard import Key as SpecialKey
from pynput.keyboard import KeyCode, Listener

from wintoucher.controller.dots import Dots
from wintoucher.data.dot import FlickDot, PressDot
from wintoucher.gui.dot import FlickDotView
from wintoucher.gui.overlay import Overlay
from wintoucher.gui.tkutils import (
    WITHDRAWN,
    create_button,
    create_details,
    create_frame,
    grid_widget,
    toggle_state,
)
from wintoucher.gui.tray import TrayIcon
from wintoucher.util.json import JSONSerializableManager
from wintoucher.util.key import Key, is_special_key, is_valid_key
from wintoucher.util.touch import MAX_TOUCHES, TouchError, TouchManager


class WintoucherApp:
    overlay: "Overlay"
    dots: Dots
    tray_icon: TrayIcon
    touch_manager: TouchManager
    touch_task: str
    touch_update: bool
    keyboard: Listener
    keyboard_listening: bool
    json_encoder: Type[JSONEncoder]
    json_decoder: Type[JSONDecoder]

    APP_WIDTH = 450
    APP_HEIGHT = 375
    APP_NAME = "WinToucher"
    APP_VERSION = "v0.1.0"
    APP_ICO_NAME = "WinToucher.ico"

    def __init__(self, dots: Dots):
        APP_NAME_WITH_VERSION = f"{self.APP_NAME} {self.APP_VERSION}"

        self.root = tk.Tk()
        self.root.title(f"Control Panel - {APP_NAME_WITH_VERSION}")

        self.root.geometry(f"{self.APP_WIDTH}x{self.APP_HEIGHT}")
        self.root.maxsize(self.APP_WIDTH, self.APP_HEIGHT)
        self.root.minsize(self.APP_WIDTH, self.APP_HEIGHT)
        self.root.iconbitmap(self.APP_ICO_NAME)
        self.root.attributes("-topmost", True)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.bind("<Map>", self.unminimize)
        self.root.bind("<Unmap>", self.minimize)

        self.dots = dots
        self.overlay = Overlay(
            master=self.root,
            app_name=APP_NAME_WITH_VERSION,
            app_icon=self.APP_ICO_NAME,
            dots=self.dots,
            update_dot_detail=self.update_dot_detail,
        )
        self.keyboard = Listener(**self.keyboard_handlers())
        self.keyboard.start()
        self.keyboard_listening = False

        # JSON Serialization
        json_manager = JSONSerializableManager()
        json_manager.register(Dots)
        json_manager.register(PressDot)
        json_manager.register(FlickDot)
        json_manager.register_special(SpecialKey, ("name",))
        json_manager.add_decoder(SpecialKey, lambda obj: SpecialKey[obj["name"]])
        json_manager.register_special(KeyCode, ("vk", "char", "is_dead"))
        json_manager.add_decoder(
            KeyCode, lambda x: KeyCode(vk=x["vk"], char=x["char"], is_dead=x["is_dead"])
        )
        json_manager.register_special(tk.IntVar, ("IntVar",))
        json_manager.register_special(tk.StringVar, ("StringVar",))

        def tk_var_encoder(var: tk.Variable):
            return {var.__class__.__name__: var.get()}

        def tk_var_decoder_factory(var_type: Type[tk.Variable]):
            def tk_var_decoder(obj: Dict[str, Any]):
                return var_type(value=obj[var_type.__name__])

            return tk_var_decoder

        json_manager.add_encoder(tk.IntVar, tk_var_encoder)
        json_manager.add_encoder(tk.StringVar, tk_var_encoder)
        json_manager.add_decoder(tk.IntVar, tk_var_decoder_factory(tk.IntVar))
        json_manager.add_decoder(tk.StringVar, tk_var_decoder_factory(tk.StringVar))

        def dots_decoder(obj: Dict[str, Any]):
            dots = Dots()
            dots.dots = obj["dots"]
            for dot in dots:
                dots.add_view(dot)
            return dots

        json_manager.add_decoder(Dots, dots_decoder)

        self.json_encoder = json_manager.build_encoder()
        self.json_decoder = json_manager.build_decoder()

        # Control Frame
        self.control_frame = create_frame(self.root, "Global Control")
        grid_widget(self.control_frame, 0, 0, padx=10, pady=5)

        self.overlay_button = create_button(
            self.control_frame, "Toggle Overlay", self.toggle_overlay
        )
        grid_widget(self.overlay_button, 0, 0)

        self.listen_button = create_button(self.control_frame, "", self.toggle_listen)
        grid_widget(self.listen_button, 0, 1)
        self.toggle_listen(False)

        self.save_button = create_button(
            self.control_frame, "Save Dots", self.save_dots
        )
        grid_widget(self.save_button, 1, 0)

        self.load_button = create_button(
            self.control_frame, "Load Dots", self.load_dots
        )
        grid_widget(self.load_button, 1, 1)

        # Dots Control
        self.dots_frame = create_frame(self.root, "Dots Control")
        grid_widget(self.dots_frame, 1, 0, padx=10, pady=5)

        self.new_dot_type_label = ttk.Label(self.dots_frame, text="New Dot Type")
        grid_widget(self.new_dot_type_label, 0, 0)

        self.new_dot_type_combobox = ttk.Combobox(
            self.dots_frame,
            textvariable=self.overlay.new_dot_type,
            values=list(Dots.TYPES.keys()),
            state="readonly",
            width=5,
        )
        self.new_dot_type_combobox.current(0)
        grid_widget(self.new_dot_type_combobox, 0, 1)

        # Dot Frame
        self.dot_frame = create_frame(self.root, "Dot Detail")
        grid_widget(self.dot_frame, 2, 0, sticky="nsew", padx=10, pady=5)
        self.root.grid_rowconfigure(2, weight=1)

        # Touch
        self.touch_manager = TouchManager(MAX_TOUCHES)
        self.touch_task = ""
        self.touch()

        # Tray Icon
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.tray_icon = TrayIcon(APP_NAME_WITH_VERSION, self.APP_ICO_NAME)
        self.tray_icon.menu_builder.add_item(
            "Show Control Panel",
            lambda icon, item: self.show_from_tray(),
            default=True,
        )
        self.tray_icon.menu_builder.add_item(
            "Keyboard Listening",
            action=lambda icon, item: self.toggle_listen(),
            checked=lambda item: self.keyboard_listening,  # type: ignore
        )
        self.tray_icon.menu_builder.add_item("Exit", lambda icon, item: self.exit())
        self.tray_icon.create_icon()

    def exit(self):
        self.keyboard.stop()
        self.root.after_cancel(self.touch_task)
        self.tray_icon.stop()
        self.overlay.destroy()
        self.root.destroy()

    def hide_to_tray(self):
        self.tray_icon.notify("WinToucher has been hidden to tray.")
        self.overlay.withdraw()
        self.root.withdraw()

    def minimize(self, event: tk.Event):
        self.overlay.withdraw()

    def unminimize(self, event: tk.Event):
        if self.overlay.showing:
            self.overlay.deiconify()

    def show_from_tray(self):
        self.root.deiconify()
        if self.overlay.showing:
            self.overlay.deiconify()

    def save_dots(self):
        if len(self.dots) == 0:
            messagebox.showinfo(
                "Save Dots",
                "No dots to save.",
            )
            return
        path = filedialog.asksaveasfilename(
            title="Save Dots",
            filetypes=(("JSON files", "*.json"),),
            defaultextension="json",
            initialdir=os.getcwd(),
        )
        if path:
            json.dump(
                self.dots,
                open(path, "w", encoding="utf-8"),
                ensure_ascii=False,
                indent=4,
                cls=self.json_encoder,
            )

    def load_dots(self):
        if len(self.dots) > 0:
            if not messagebox.askyesno(
                "Load Dots",
                "Loading dots will overwrite the current dots.\n\nDo you want to continue?",
            ):
                return
        path = filedialog.askopenfilename(
            title="Load Dots",
            filetypes=(("JSON files", "*.json"),),
            initialdir=os.getcwd(),
        )
        if path:
            self.dots = json.load(
                open(path, "r", encoding="utf-8"),
                cls=self.json_decoder,
            )
            self.overlay.dots = self.dots
            self.overlay.update()

    def toggle_listen(self, notify: bool = False):
        if notify:
            self.tray_icon.notify(
                f"Keyboard listening {'resume' if self.keyboard_listening else 'pause'}d."
            )
        self.listen_button.config(
            text=f"{'Resume' if self.keyboard_listening else 'Pause'} Listen (Esc)"
        )

        self.keyboard_listening = not self.keyboard_listening

    def keyboard_handlers(self):
        def prehandler(func: Callable[[Key], None]):
            def wrapped(key: Key, *args, **kwargs):
                if not is_special_key(key):
                    key = self.keyboard.canonical(key)

                if self.keyboard_listening:
                    func(key, *args, **kwargs)

            return wrapped

        @prehandler
        def on_press(key: Key):
            if key == SpecialKey.esc:
                self.toggle_listen()
                return

            if self.overlay.state() == WITHDRAWN:
                # Inject touch
                if self.keyboard_listening and is_valid_key(key):
                    for dot in self.dots.get_dots_by_key(key):
                        if isinstance(dot, PressDot):
                            self.touch_manager.press(dot.id, dot.x, dot.y)
                        elif isinstance(dot, FlickDot):
                            view = self.dots.get_view_by_dot(dot)
                            assert isinstance(view, FlickDotView)
                            view.run(self.touch_manager)

        @prehandler
        def on_release(key: Key):
            if self.overlay.state() == WITHDRAWN:
                for dot in self.dots.get_dots_by_key(key):
                    self.touch_manager.up(dot.id)
            else:
                # Assign key to dot
                if self.dots and is_valid_key(key):
                    for dot in (
                        self.dots.current_viewed_dot,
                        self.dots.last_operated_dot,
                    ):
                        if dot and dot.key is None:
                            dot.key = key
                            self.overlay.update()
                            break

        return {"on_press": on_press, "on_release": on_release}

    def toggle_overlay(self):
        if self.overlay.state() == WITHDRAWN:
            self.overlay.show()
            toggle_state(self.dot_frame)
            toggle_state(self.dots_frame)
        else:
            self.overlay.hide()
            toggle_state(self.dot_frame, "disabled")
            toggle_state(self.dots_frame, "disabled")

    def touch(self):
        if self.overlay.state() == WITHDRAWN:
            try:
                self.touch_manager.apply_touches()
            except TouchError as e:
                messagebox.showerror("Error", e.args[0])
                print(e)
                self.exit()
        self.touch_task = self.root.after(10, self.touch)

    def update_dot_detail(self):
        for widget in self.dot_frame.winfo_children():
            widget.destroy()
        if self.dots.current_viewed_dot:
            view = self.dots.get_view_by_dot(self.dots.current_viewed_dot)
            create_details(self.dot_frame, view.detail(self.overlay.draw_dots))

    def run(self):
        self.root.mainloop()
