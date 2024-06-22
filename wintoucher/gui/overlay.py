import math
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from wintoucher.controller.dots import Dots
from wintoucher.data.dot import Dot
from wintoucher.util.touch import MAX_TOUCHES


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
            view = self.dots.get_view_by_dot(dot)
            view.draw(self.canvas, outlined=(dot == self.dots.current_viewed_dot))
