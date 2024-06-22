import time
import tkinter as tk
from abc import ABC
from dataclasses import dataclass
from math import cos, radians, sin
from threading import Thread
from tkinter import ttk
from typing import Callable, ClassVar

from wintoucher.data.dot import Dot, FlickDot
from wintoucher.gui.tkutils import DetailDict
from wintoucher.util.key import key_to_str
from wintoucher.util.touch import TouchManager


@dataclass
class DotView(ABC):
    dot: Dot

    COLOR: ClassVar[str] = "red"
    RADIUS: ClassVar[int] = 10
    KEY_LABEL_OFFSET_X: ClassVar[int] = 0
    KEY_LABEL_OFFSET_Y: ClassVar[int] = 25

    @property
    def color(self):
        return self.COLOR if self.dot.key else "snow4"

    def draw(self, canvas: tk.Canvas, outlined: bool):
        # Create dot
        canvas.create_oval(
            self.dot.x - self.RADIUS,
            self.dot.y - self.RADIUS,
            self.dot.x + self.RADIUS,
            self.dot.y + self.RADIUS,
            fill=self.color,
            outline="red" if outlined else "",
        )

        # Create key text
        if self.dot.key:
            text = canvas.create_text(
                self.dot.x + self.KEY_LABEL_OFFSET_X,
                self.dot.y + self.KEY_LABEL_OFFSET_Y,
                text=key_to_str(self.dot.key),
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

    def detail(self, draw_dots: Callable[[], None]) -> DetailDict:
        return {
            "Type": {
                "widget_type": ttk.Label,
                "params": {"text": self.dot.__class__.__name__},
            },
            "Key": {
                "widget_type": ttk.Label,
                "params": {"text": key_to_str(self.dot.key)},
            },
        }


@dataclass
class PressDotView(DotView):
    COLOR: ClassVar[str] = "green"


@dataclass
class FlickDotView(DotView):
    dot: FlickDot
    COLOR: ClassVar[str] = "orange"
    KEY_LABEL_OFFSET_Y: ClassVar[int] = 40
    ARROW_LENGTH: ClassVar[int] = 25
    ARROW_WIDTH: ClassVar[int] = 5
    running: bool = False

    def draw(self, canvas: tk.Canvas, outlined: bool):
        # Create arrow line
        dx, dy = (
            self.ARROW_LENGTH * cos(radians(self.dot.angle.get())),
            self.ARROW_LENGTH * sin(radians(self.dot.angle.get())),
        )
        canvas.create_line(
            self.dot.x - dx,
            self.dot.y - dy,
            self.dot.x + dx,
            self.dot.y + dy,
            arrow=tk.LAST,
            fill=self.color,
            width=self.ARROW_WIDTH,
        )

        # Create dot
        super().draw(canvas, outlined)

    def detail(self, draw_dots: Callable[[], None]) -> DetailDict:
        def on_angle_change_factory(var: tk.IntVar):
            def round_var(step: int):
                value = var.get()
                value = round(value / step) * step
                var.set(value)

            def on_angle_change(_=None):
                round_var(1)
                draw_dots()

            return on_angle_change

        return {
            **super().detail(draw_dots),
            "Angle": {
                "widget_type": ttk.Spinbox,
                "params": {
                    "from_": 0,
                    "to": 360,
                    "textvariable": self.dot.angle,
                    "state": "readonly",
                    "command": on_angle_change_factory(self.dot.angle),
                },
            },
            "": {
                "widget_type": ttk.Scale,
                "params": {
                    "from_": 0,
                    "to": 360,
                    "variable": self.dot.angle,
                    "orient": tk.HORIZONTAL,
                    "command": on_angle_change_factory(self.dot.angle),
                },
            },
            "Distance": {
                "widget_type": ttk.Spinbox,
                "params": {
                    "from_": 0,
                    "to": 360,
                    "textvariable": self.dot.distance,
                    "state": "readonly",
                    "command": on_angle_change_factory(self.dot.distance),
                },
            },
        }

    def run(self, touch_manager: TouchManager):
        if not self.running:

            def runner():
                self.running = True

                x: float = self.dot.x
                y: float = self.dot.y
                dx = cos(radians(self.dot.angle.get())) * self.dot.delta
                dy = sin(radians(self.dot.angle.get())) * self.dot.delta

                touch_manager.down(self.dot.id, int(x), int(y))
                touch_manager.apply_touches()

                for _ in range(self.dot.distance.get() // self.dot.delta):
                    if not self.running:
                        return
                    x += dx
                    y += dy
                    touch_manager.move(self.dot.id, int(x), int(y))
                    touch_manager.apply_touches()
                    time.sleep(self.dot.delay)

                touch_manager.up(self.dot.id)
                touch_manager.apply_touches()
                self.running = False

            thread = Thread(target=runner)
            thread.start()

    def stop(self):
        self.running = False
