import json
import math
import os
import time
import tkinter as tk
from abc import ABC
from dataclasses import dataclass, field
from json import JSONDecoder, JSONEncoder
from math import cos, radians, sin
from threading import Thread
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, ClassVar, Dict, Iterable, List, Optional, Type

from pynput.keyboard import Key as SpecialKey
from pynput.keyboard import KeyCode, Listener

from wintoucher.json import JSONSerializableManager
from wintoucher.touch import MAX_TOUCHES, TouchError, TouchManager
from wintoucher.utils.gui import (
    WITHDRAWN,
    DetailDict,
    TrayIcon,
    create_button,
    create_details,
    create_frame,
    grid_widget,
    toggle_state,
)
from wintoucher.utils.key import Key, is_special_key, is_valid_key, key_to_str


@dataclass
class Dot(ABC):
    id: int
    x: int
    y: int
    key: Optional[Key]

    COLOR: ClassVar[str] = "red"
    RADIUS: ClassVar[int] = 10
    KEY_LABEL_OFFSET_X: ClassVar[int] = 0
    KEY_LABEL_OFFSET_Y: ClassVar[int] = 25

    @property
    def color(self):
        return self.COLOR if self.key else "snow4"

    def draw(self, canvas: tk.Canvas, outlined: bool):
        # Create dot
        canvas.create_oval(
            self.x - self.RADIUS,
            self.y - self.RADIUS,
            self.x + self.RADIUS,
            self.y + self.RADIUS,
            fill=self.color,
            outline="red" if outlined else "",
        )

        # Create key text
        if self.key:
            text = canvas.create_text(
                self.x + self.KEY_LABEL_OFFSET_X,
                self.y + self.KEY_LABEL_OFFSET_Y,
                text=key_to_str(self.key),
                fill="black",
            )
            text_bbox = canvas.bbox(text)

            # Add padding to bbox
            PADDING = (5, 2)
            text_bbox = (
                text_bbox[0] - PADDING[0],
                text_bbox[1] - PADDING[1],
                text_bbox[2] + PADDING[0],
                text_bbox[3] + PADDING[1],
            )

            rect = canvas.create_rectangle(text_bbox, fill="#E1E1E1", outline="#ADADAD")
            canvas.tag_lower(rect, text)

    def detail(self, overlay: "Overlay") -> DetailDict:
        return {
            "Type": {
                "widget_type": ttk.Label,
                "params": {"text": self.__class__.__name__},
            },
            "Key": {
                "widget_type": ttk.Label,
                "params": {"text": key_to_str(self.key)},
            },
        }

    @classmethod
    def __json__(cls):
        return ("id", "x", "y", "key")


@dataclass
class PressDot(Dot):
    COLOR: ClassVar[str] = "green"


@dataclass
class FlickDot(Dot):
    angle: tk.IntVar = field(default_factory=tk.IntVar)
    distance: tk.IntVar = field(default_factory=tk.IntVar)
    delay: float = 0.005
    delta: int = 10
    running: bool = False

    COLOR: ClassVar[str] = "orange"
    KEY_LABEL_OFFSET_Y: ClassVar[int] = 40
    ARROW_LENGTH: ClassVar[int] = 25
    ARROW_WIDTH: ClassVar[int] = 5

    def __post_init__(self):
        self.distance.set(100)

    def draw(self, canvas: tk.Canvas, outlined: bool):
        # Create arrow line
        dx, dy = (
            self.ARROW_LENGTH * cos(radians(self.angle.get())),
            self.ARROW_LENGTH * sin(radians(self.angle.get())),
        )
        canvas.create_line(
            self.x - dx,
            self.y - dy,
            self.x + dx,
            self.y + dy,
            arrow=tk.LAST,
            fill=self.color,
            width=self.ARROW_WIDTH,
        )

        # Create dot
        super().draw(canvas, outlined)

    def detail(self, overlay: "Overlay") -> DetailDict:
        def on_angle_change_factory(var: tk.IntVar):
            def round_var(step: int):
                value = var.get()
                value = round(value / step) * step
                var.set(value)

            def on_angle_change(_=None):
                round_var(1)
                overlay.draw_dots()

            return on_angle_change

        return {
            **super().detail(overlay),
            "Angle": {
                "widget_type": ttk.Spinbox,
                "params": {
                    "from_": 0,
                    "to": 360,
                    "textvariable": self.angle,
                    "state": "readonly",
                    "command": on_angle_change_factory(self.angle),
                },
            },
            "": {
                "widget_type": ttk.Scale,
                "params": {
                    "from_": 0,
                    "to": 360,
                    "variable": self.angle,
                    "orient": tk.HORIZONTAL,
                    "command": on_angle_change_factory(self.angle),
                },
            },
            "Distance": {
                "widget_type": ttk.Spinbox,
                "params": {
                    "from_": 0,
                    "to": 360,
                    "textvariable": self.distance,
                    "state": "readonly",
                    "command": on_angle_change_factory(self.distance),
                },
            },
        }

    def run(self, touch_manager: TouchManager):
        if not self.running:

            def runner():
                self.running = True

                x: float = self.x
                y: float = self.y
                dx = cos(radians(self.angle.get())) * self.delta
                dy = sin(radians(self.angle.get())) * self.delta

                touch_manager.down(self.id, int(x), int(y))
                touch_manager.apply_touches()

                for _ in range(self.distance.get() // self.delta):
                    if not self.running:
                        return
                    x += dx
                    y += dy
                    touch_manager.move(self.id, int(x), int(y))
                    touch_manager.apply_touches()
                    time.sleep(self.delay)

                touch_manager.up(self.id)
                touch_manager.apply_touches()
                self.running = False

            thread = Thread(target=runner)
            thread.start()

    def stop(self):
        self.running = False

    @classmethod
    def __json__(cls):
        return (*super().__json__(), "angle", "distance")


@dataclass
class Dots:
    dots: List[Dot] = field(default_factory=list)
    _last_operated_dot: Optional[Dot] = None
    _current_viewed_dot: Optional[Dot] = None

    DOT_TYPES = {
        "Press": PressDot,
        "Flick": FlickDot,
    }

    @property
    def last_operated_dot(self):
        if self._last_operated_dot not in self.dots:
            self._last_operated_dot = None

        if self._last_operated_dot is None:
            self._last_operated_dot = self.dots[-1]

        return self._last_operated_dot

    @last_operated_dot.setter
    def last_operated_dot(self, value: Dot):
        if value not in self.dots:
            self._last_operated_dot = None
        else:
            self._last_operated_dot = value

    def __len__(self):
        return len(self.dots)

    @property
    def current_viewed_dot(self):
        if self._current_viewed_dot not in self.dots:
            self._current_viewed_dot = None
        return self._current_viewed_dot

    @current_viewed_dot.setter
    def current_viewed_dot(self, value: Dot):
        if value not in self.dots:
            self._current_viewed_dot = None
        else:
            self._current_viewed_dot = value

    def __iter__(self):
        return iter(self.dots)

    def add(self, type: str, x: int, y: int):
        if type not in self.DOT_TYPES:
            raise ValueError(f"Invalid dot type: {type}")

        dot = self.DOT_TYPES[type](len(self.dots), x, y, None)
        self.dots.append(dot)
        self.last_operated_dot = dot

    def remove(self, dot: Dot):
        self.dots.remove(dot)
        self.last_operated_dot = None

    def __getitem__(self, index):
        return self.dots[index]

    def replace(self, original_dot: Dot, new_dot: Dot):
        index = self.dots.index(original_dot)
        self.dots[index] = new_dot

    def get_dots_by_key(self, key: Key) -> Iterable[Dot]:
        return filter(lambda dot: dot.key == key, self.dots)

    @classmethod
    def __json__(cls):
        return ("dots",)


class App:
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
    APP_ICO_NAME = "WinToucher.ico"

    def __init__(self, dots: Dots, max_touches: int = MAX_TOUCHES):
        self.root = tk.Tk()
        self.root.title(f"{self.APP_NAME} - Control Panel")

        self.root.geometry(f"{self.APP_WIDTH}x{self.APP_HEIGHT}")
        self.root.maxsize(self.APP_WIDTH, self.APP_HEIGHT)
        self.root.minsize(self.APP_WIDTH, self.APP_HEIGHT)
        self.root.iconbitmap(self.APP_ICO_NAME)
        self.root.attributes("-topmost", True)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.bind("<Map>", self.unminimize)
        self.root.bind("<Unmap>", self.minimize)

        self.dots = dots
        self.overlay = Overlay(self.root, self.dots, self.update_dot_detail)
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
            values=list(Dots.DOT_TYPES.keys()),
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
        self.touch_manager = TouchManager(max_touches)
        self.touch_task = ""
        self.touch()

        # Tray Icon
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.tray_icon = TrayIcon(self.APP_NAME, self.APP_ICO_NAME)
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
                            dot.run(self.touch_manager)

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
            create_details(
                self.dot_frame, self.dots.current_viewed_dot.detail(self.overlay)
            )

    def run(self):
        self.root.mainloop()


class Overlay(tk.Toplevel):
    UpdateDotCallable = Callable[[], None]

    dots: Dots
    new_dot_type: tk.StringVar
    update_current_dot_detail: UpdateDotCallable
    showing: bool

    def __init__(self, master: tk.Tk, dots: Dots, update_dot_detail: UpdateDotCallable):
        super().__init__(master)
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.5)
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.dots = dots
        self.new_dot_type = tk.StringVar()
        self.update_current_dot_detail = update_dot_detail
        self.showing = False
        self.draw_dots()

        self.canvas.bind("<Button-1>", self.add_dot)
        self.canvas.bind("<Button-3>", self.remove_or_reassign_dot)
        self.canvas.bind("<Double-Button-1>", self.detail_dot)
        self.canvas.bind("<B1-Motion>", self.move_dot)

    def hide(self):
        self.showing = False
        self.withdraw()

    def show(self):
        self.showing = True
        self.deiconify()

    def get_closest_dot(self, x: int, y: int) -> Optional[Dot]:
        if not self.dots or len(self.dots) == 0:
            return None

        def distance(dot: Dot):
            return math.hypot(dot.x - x, dot.y - y)

        closest_dot = min(self.dots, key=distance)
        if distance(closest_dot) > 20:
            return None
        return closest_dot

    def update(self):
        self.update_current_dot_detail()
        self.draw_dots()

    def add_dot(self, event: tk.Event):
        if len(self.dots) == MAX_TOUCHES:
            messagebox.showerror("Error", "Maximum number of dots reached.")
            return
        x, y = event.x, event.y
        closeset_dot = self.get_closest_dot(x, y)
        if closeset_dot is None:
            self.dots.add(self.new_dot_type.get(), x, y)
            self.update()

    def move_dot(self, event: tk.Event):
        x, y = event.x, event.y
        current_dot = self.dots.current_viewed_dot
        if current_dot:
            current_dot.x = x
            current_dot.y = y
            self.update()

    def detail_dot(self, event: tk.Event):
        x, y = event.x, event.y
        closeset_dot = self.get_closest_dot(x, y)
        if closeset_dot:
            self.dots.current_viewed_dot = closeset_dot
            self.update()

    def remove_or_reassign_dot(self, event: tk.Event):
        x, y = event.x, event.y
        closeset_dot = self.get_closest_dot(x, y)
        if closeset_dot:
            if closeset_dot.key is None:
                self.dots.remove(closeset_dot)
                self.dots.current_viewed_dot = None
            else:
                closeset_dot.key = None
                self.dots.last_operated_dot = closeset_dot
            self.update()

    def draw_dots(self):
        self.canvas.delete("all")
        for dot in self.dots:
            dot.draw(self.canvas, outlined=dot == self.dots.current_viewed_dot)


def main():
    app = App(dots=Dots())
    app.run()


if __name__ == "__main__":
    main()
