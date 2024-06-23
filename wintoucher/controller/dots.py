from dataclasses import dataclass, field
from typing import ClassVar, Dict, Iterable, List, Optional, Type

from wintoucher.data.dot import Dot, FlickDot, PressDot
from wintoucher.gui.dot import DotView, FlickDotView, PressDotView
from wintoucher.util.key import Key


@dataclass
class Dots:
    """
    Controller class to manage dots and their gui views.
    """

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
        """
        Get the last operated dot.
        """
        if self._last_operated_dot not in self.dots:
            self._last_operated_dot = None

        if self._last_operated_dot is None:
            self._last_operated_dot = next(reversed(self.dots))

        return self._last_operated_dot

    @last_operated_dot.setter
    def last_operated_dot(self, value: Dot):
        """
        Set the last operated dot.

        If the dot is not in the list of dots, set it to `None`.
        """
        if value not in self.dots:
            self._last_operated_dot = None
        else:
            self._last_operated_dot = value

    def __len__(self):
        """
        Get the number of dots. Only count non-`None` dots.
        """
        return len(list(filter(None, self.dots)))

    @property
    def current_viewed_dot(self):
        """
        Get the current viewed dot.
        """
        if self._current_viewed_dot not in self.dots:
            self._current_viewed_dot = None
        return self._current_viewed_dot

    @current_viewed_dot.setter
    def current_viewed_dot(self, value: Dot):
        """
        Set the current viewed dot.

        If the dot is not in the list of dots, set it to `None`.
        """
        if value not in self.dots:
            self._current_viewed_dot = None
        else:
            self._current_viewed_dot = value

    def __iter__(self):
        """
        Make the class iterable. Only return non-`None` dots.
        """
        return iter(filter(None, self.dots))

    def add_view(self, dot: Dot):
        """
        Add a view for the given dot.
        """
        view = self.VIEW_TYPES[type(dot)](dot)
        self.views[dot.id] = view

    def add(self, type: str, x: int, y: int):
        """
        Add a dot of the given type at the given coordinates.
        """
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
        """
        Remove the given dot.
        """
        index = self.dots.index(dot)

        self.dots[index] = None
        self.last_operated_dot = None

        self.views[index] = None

    def __getitem__(self, index: int):
        return self.dots[index]

    def get_view_by_dot(self, dot: Dot) -> DotView:
        """
        Get the view for the given dot.
        """
        view = self.views[dot.id]
        assert view is not None
        return view

    def get_dots_by_key(self, key: Key) -> Iterable[Dot]:
        """
        Get all dots with the given key.
        """
        non_null_dots = filter(None, self.dots)
        return filter(lambda dot: dot.key == key, non_null_dots)

    @classmethod
    def __json__(cls):
        return ("dots",)
