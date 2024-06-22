from dataclasses import dataclass, field
from typing import ClassVar, Dict, Iterable, List, Optional, Type

from wintoucher.data.dot import Dot, FlickDot, PressDot
from wintoucher.gui.dot import DotView, FlickDotView, PressDotView
from wintoucher.util.key import Key


@dataclass
class Dots:
    dots: List[Optional[Dot]] = field(default_factory=list)
    views: Dict[int, Optional[DotView]] = field(default_factory=dict)
    _last_operated_dot: Optional[Dot] = None
    _current_viewed_dot: Optional[Dot] = None

    TYPES: ClassVar[Dict[str, Type[Dot]]] = {
        "Press": PressDot,
        "Flick": FlickDot,
    }

    VIEW_TYPES: ClassVar[Dict[Type[Dot], Type[DotView]]] = {
        PressDot: PressDotView,
        FlickDot: FlickDotView,
    }

    @property
    def last_operated_dot(self):
        if self._last_operated_dot not in self.dots:
            self._last_operated_dot = None

        if self._last_operated_dot is None:
            self._last_operated_dot = next(reversed(self.dots))

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
        return iter(filter(None, self.dots))

    def add_view(self, dot: Dot):
        view = self.VIEW_TYPES[type(dot)](dot)
        self.views[dot.id] = view

    def add(self, type: str, x: int, y: int):
        if type not in self.TYPES:
            raise ValueError(f"Invalid dot type: {type}")

        dot_type = self.TYPES[type]

        next_id = 0
        for dot in self.dots:
            if dot is None:
                break
            next_id += 1

        new_dot = dot_type(id=next_id, x=x, y=y, key=None)
        self.dots.append(new_dot)
        self.last_operated_dot = new_dot
        self.add_view(new_dot)

    def remove(self, dot: Dot):
        index = self.dots.index(dot)

        self.dots[index] = None
        self.last_operated_dot = None

        self.views[index] = None

    def __getitem__(self, index):
        return self.dots[index]

    def get_view_by_dot(self, dot: Dot) -> DotView:
        view = self.views[dot.id]
        assert view is not None
        return view

    def get_dots_by_key(self, key: Key) -> Iterable[Dot]:
        non_null_dots = filter(None, self.dots)
        return filter(lambda dot: dot.key == key, non_null_dots)

    @classmethod
    def __json__(cls):
        return ("dots",)
