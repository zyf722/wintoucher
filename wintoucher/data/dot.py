import tkinter as tk
from abc import ABC
from dataclasses import dataclass, field
from typing import Optional

from wintoucher.util.key import Key


@dataclass
class Dot(ABC):
    """
    Data class representing a touch dot on the screen.
    """

    id: int
    x: int
    y: int
    key: Optional[Key]

    @classmethod
    def __json__(cls):
        return ("id", "x", "y", "key")


@dataclass
class PressDot(Dot):
    """
    A touch dot that represents a press.
    """

    pass


@dataclass
class FlickDot(Dot):
    """
    A touch dot that represents a flick.
    """

    angle: tk.IntVar = field(default_factory=tk.IntVar)
    distance: tk.IntVar = field(default_factory=tk.IntVar)
    delay: float = 0.005
    delta: int = 10

    def __post_init__(self):
        self.distance.set(100)

    @classmethod
    def __json__(cls):
        return (*super().__json__(), "angle", "distance")
