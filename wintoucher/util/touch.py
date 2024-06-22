import time
from ctypes import (
    Array,
    FormatError,
    Structure,
    byref,
    c_int,
    c_int32,
    c_uint32,
    c_uint64,
    windll,
)
from ctypes.wintypes import DWORD, HANDLE, HWND, POINT, RECT
from dataclasses import dataclass, field, fields
from threading import Lock
from typing import ClassVar, List, Type

# Constants
# For init
TOUCH_FEEDBACK_DEFAULT = 0x00000001
TOUCH_FEEDBACK_INDIRECT = 0x00000002
TOUCH_FEEDBACK_NONE = 0x00000003

# For touchMask
TOUCH_MASK_NONE = 0x00000000  # Default
TOUCH_MASK_CONTACTAREA = 0x00000001
TOUCH_MASK_ORIENTATION = 0x00000002
TOUCH_MASK_PRESSURE = 0x00000004
TOUCH_MASK_ALL = 0x00000007

# For touchFlag
TOUCH_FLAG_NONE = 0x00000000

# For pointerType
PT_POINTER = 0x00000001  # All
PT_TOUCH = 0x00000002
PT_PEN = 0x00000003
PT_MOUSE = 0x00000004

# For pointerFlags
POINTER_FLAG_NONE = 0x00000000  # Default
POINTER_FLAG_NEW = 0x00000001
POINTER_FLAG_INRANGE = 0x00000002
POINTER_FLAG_INCONTACT = 0x00000004
POINTER_FLAG_FIRSTBUTTON = 0x00000010
POINTER_FLAG_SECONDBUTTON = 0x00000020
POINTER_FLAG_THIRDBUTTON = 0x00000040
POINTER_FLAG_FOURTHBUTTON = 0x00000080
POINTER_FLAG_FIFTHBUTTON = 0x00000100
POINTER_FLAG_PRIMARY = 0x00002000
POINTER_FLAG_CONFIDENCE = 0x00004000
POINTER_FLAG_CANCELED = 0x00008000
POINTER_FLAG_DOWN = 0x00010000
POINTER_FLAG_UPDATE = 0x00020000
POINTER_FLAG_UP = 0x00040000
POINTER_FLAG_WHEEL = 0x00080000
POINTER_FLAG_HWHEEL = 0x00100000
POINTER_FLAG_CAPTURECHANGED = 0x00200000

# Default values
MAX_TOUCHES = 256
FINGER_RADIUS = 20
ORIENTATION = 90
PRESSURE = 32000
DELAY = 0.05


def structure(cls: Type):
    """
    Decorator to generate `_fields_` attribute for dataclasses.

    Args:
        cls (Type): Class to decorate. Should be a dataclass and inherit from `ctypes.Structure`.
    """

    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join(f'{field.name}={getattr(self, field.name)!r}' for field in fields(self))})"

    cls._fields_ = [(field.name, field.type) for field in fields(cls)]
    cls.__repr__ = __repr__  # type: ignore
    return cls


# Structs Needed
@structure
@dataclass
class POINTER_INFO(Structure):
    """
    Object for C struct `POINTER_INFO`.

    See:
        https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-pointer_info
    """

    pointerType: c_uint32 = field(default_factory=c_uint32)
    pointerId: c_uint32 = field(default_factory=c_uint32)
    frameId: c_uint32 = field(default_factory=c_uint32)
    pointerFlags: c_int = field(default_factory=c_int)
    sourceDevice: HANDLE = field(default_factory=HANDLE)
    hwndTarget: HWND = field(default_factory=HWND)
    ptPixelLocation: POINT = field(default_factory=POINT)
    ptHimetricLocation: POINT = field(default_factory=POINT)
    ptPixelLocationRaw: POINT = field(default_factory=POINT)
    ptHimetricLocationRaw: POINT = field(default_factory=POINT)
    dwTime: DWORD = field(default_factory=DWORD)
    historyCount: c_uint32 = field(default_factory=c_uint32)
    inputData: c_int32 = field(default_factory=c_int32)
    dwKeyStates: DWORD = field(default_factory=DWORD)
    PerformanceCount: c_uint64 = field(default_factory=c_uint64)
    ButtonChangeType: c_int = field(default_factory=c_int)


@structure
@dataclass
class POINTER_TOUCH_INFO(Structure):
    """
    Object for C struct `POINTER_TOUCH_INFO`.

    See:
        https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-pointer_touch_info
    """

    pointerInfo: POINTER_INFO = field(default_factory=POINTER_INFO)
    touchFlags: c_int = field(default_factory=c_int)
    touchMask: c_int = field(default_factory=c_int)
    rcContact: RECT = field(default_factory=RECT)
    rcContactRaw: RECT = field(default_factory=RECT)
    orientation: c_uint32 = field(default_factory=c_uint32)
    pressure: c_uint32 = field(default_factory=c_uint32)


class TouchError(Exception):
    """
    Exception for touch errors.
    """

    pass


@dataclass
class TouchItem:
    """
    Class to represent a touch item. Should be managed by a `TouchManager`.
    """

    touch_info: POINTER_TOUCH_INFO
    x: int
    y: int
    enabled: bool

    DOWN_STATE: ClassVar[int] = (
        POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
    )

    UPDATE_STATE: ClassVar[int] = (
        POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
    )

    def __init__(self, id: int):
        self.x = 0
        self.y = 0
        self.enabled = False

        self.touch_info = POINTER_TOUCH_INFO(
            pointerInfo=POINTER_INFO(
                pointerType=c_uint32(PT_TOUCH),
                pointerId=c_uint32(id),
            ),
            touchFlags=c_int(TOUCH_FLAG_NONE),
            touchMask=c_int(TOUCH_MASK_ALL),
            orientation=c_uint32(ORIENTATION),
            pressure=c_uint32(PRESSURE),
        )

    def __set_touch_point(self, x: int, y: int):
        """
        Internal method to set the touch point to the given coordinates.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.
        """
        self.touch_info.pointerInfo.ptPixelLocation.x = x
        self.touch_info.pointerInfo.ptPixelLocation.y = y

        self.touch_info.rcContact.top = y - FINGER_RADIUS
        self.touch_info.rcContact.bottom = y + FINGER_RADIUS
        self.touch_info.rcContact.left = x - FINGER_RADIUS
        self.touch_info.rcContact.right = x + FINGER_RADIUS

        self.x = x
        self.y = y

    def down(self, x: int, y: int):
        """
        Set the touch point to the given coordinates and set the touch state to down.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.
        """
        self.__set_touch_point(x, y)
        self.touch_info.pointerInfo.pointerFlags = c_int(TouchItem.DOWN_STATE)
        self.enabled = True

    def move(self, x: int, y: int):
        """
        Move a touch point which is already down to the given coordinates.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.
        """
        self.__set_touch_point(x, y)
        self.touch_info.pointerInfo.pointerFlags = c_int(TouchItem.UPDATE_STATE)

    def up(self):
        """
        Set the touch state to up.
        """
        self.__set_touch_point(self.x, self.y)
        self.touch_info.pointerInfo.pointerFlags = c_int(POINTER_FLAG_UP)

    def update(self):
        """
        Update the touch state to the next state.
        """
        p_info = self.touch_info.pointerInfo
        if p_info.pointerFlags == TouchItem.DOWN_STATE:
            p_info.pointerFlags = c_int(TouchItem.UPDATE_STATE)
        elif p_info.pointerFlags == POINTER_FLAG_UP:
            self.enabled = False


class TouchManager:
    """
    Class to manage touch points.
    """

    touches: List[TouchItem]
    touch_infos: Array
    lock: Lock

    def __init__(self, max_touches: int):
        if max_touches > MAX_TOUCHES:
            raise TouchError("Maximum number of touches cannot exceed 256.")

        self.running = False
        self.touches = []
        self.lock = Lock()
        self.touch_infos = (POINTER_TOUCH_INFO * max_touches)()
        for i in range(max_touches):
            self.touches.append(TouchItem(i))

        if (
            windll.user32.InitializeTouchInjection(
                len(self.touches), TOUCH_FEEDBACK_DEFAULT
            )
            == 0
        ):
            raise TouchError("Failed to initialize touch injection.")

    def down(self, id: int, x: int, y: int):
        """
        Set a touch point to the given coordinates and set the touch state to down.

        Args:
            id (int): Touch point ID.
            x (int): X coordinate.
            y (int): Y coordinate.
        """

        if id >= len(self.touches):
            raise TouchError("Touch ID out of range.")

        with self.lock:
            self.touches[id].down(x, y)

    def move(self, id: int, x: int, y: int):
        """
        Move a touch point which is already down to the given coordinates.

        Args:
            id (int): Touch point ID.
            x (int): X coordinate.
            y (int): Y coordinate.
        """

        if id >= len(self.touches):
            raise TouchError("Touch ID out of range.")

        with self.lock:
            self.touches[id].move(x, y)

    def press(self, id: int, x: int, y: int):
        """
        Higher wrapper for `down` and `move`.

        Args:
            id (int): Touch point ID.
            x (int): X coordinate.
            y (int): Y coordinate.
        """

        if id >= len(self.touches):
            raise TouchError("Touch ID out of range.")

        touch = self.touches[id]
        if touch.enabled:
            touch.move(x, y)
        else:
            touch.down(x, y)

    def up(self, id: int):
        """
        Set a touch point to up.

        Args:
            id (int): Touch point ID.
        """

        if id >= len(self.touches):
            raise TouchError("Touch ID out of range.")

        with self.lock:
            self.touches[id].up()

    def apply_touches(self):
        """
        Apply all touch points to OS.
        """

        with self.lock:
            touches: List[TouchItem] = []

            for touch in self.touches:
                if touch.enabled:
                    self.touch_infos[len(touches)] = touch.touch_info
                    touches.append(touch)

            if len(touches) > 0:
                if (
                    windll.user32.InjectTouchInput(
                        len(touches), byref(self.touch_infos[0])
                    )
                    == 0
                ):
                    for touch_info in self.touch_infos[: len(touches)]:
                        print(touch_info)
                    raise TouchError(
                        f"Failed trying to update {len(touches)} points with Error: {FormatError()}"
                    )

                for touch in touches:
                    touch.update()


if __name__ == "__main__":
    manager = TouchManager(1)

    manager.down(0, x=960, y=640)
    manager.apply_touches()

    time.sleep(0.05)

    for i in range(100):
        print(i)
        manager.apply_touches()
        time.sleep(0.005)

    time.sleep(0.05)

    manager.up(0)
    manager.apply_touches()
