from typing import Optional, Union

from pynput.keyboard import Key as SpecialKey
from pynput.keyboard import KeyCode

Key = Union[KeyCode, SpecialKey]

__SPECIAL_KEYS = {
    SpecialKey.alt_l: "L Alt",
    SpecialKey.alt_r: "R Alt",
    SpecialKey.alt_gr: "Alt Gr",
    SpecialKey.backspace: "Backspace",
    SpecialKey.caps_lock: "Caps Lock",
    SpecialKey.delete: "Delete",
    SpecialKey.down: "Down",
    SpecialKey.end: "End",
    SpecialKey.enter: "Enter",
    SpecialKey.esc: "Esc",
    SpecialKey.f1: "F1",
    SpecialKey.f2: "F2",
    SpecialKey.f3: "F3",
    SpecialKey.f4: "F4",
    SpecialKey.f5: "F5",
    SpecialKey.f6: "F6",
    SpecialKey.f7: "F7",
    SpecialKey.f8: "F8",
    SpecialKey.f9: "F9",
    SpecialKey.f10: "F10",
    SpecialKey.f11: "F11",
    SpecialKey.f12: "F12",
    SpecialKey.f13: "F13",
    SpecialKey.f14: "F14",
    SpecialKey.f15: "F15",
    SpecialKey.f16: "F16",
    SpecialKey.f17: "F17",
    SpecialKey.f18: "F18",
    SpecialKey.f19: "F19",
    SpecialKey.f20: "F20",
    SpecialKey.home: "Home",
    SpecialKey.left: "Left",
    SpecialKey.page_down: "Page Down",
    SpecialKey.page_up: "Page Up",
    SpecialKey.right: "Right",
    SpecialKey.shift_l: "L Shift",
    SpecialKey.shift_r: "R Shift",
    SpecialKey.space: "Space",
    SpecialKey.tab: "Tab",
    SpecialKey.up: "Up",
    SpecialKey.insert: "Insert",
    SpecialKey.menu: "Menu",
    SpecialKey.num_lock: "Num Lock",
    SpecialKey.pause: "Pause",
    SpecialKey.print_screen: "Print Screen",
    SpecialKey.scroll_lock: "Scroll Lock",
}


def is_special_key(key: Key):
    """
    Check if a key is a special key.

    Args:
        key (Key): The key to check.

    Returns:
        bool: `True` if the key is a special key, `False` otherwise.
    """
    return key in __SPECIAL_KEYS


def is_valid_key(key: Key):
    """
    Check if a key is a valid key.

    Args:
        key (Key): The key to check.

    Returns:
        bool: `True` if the key is a valid key, `False` otherwise.
    """
    return is_special_key(key) or (isinstance(key, KeyCode) and key.char is not None)


def key_to_str(key: Optional[Key]) -> str:
    """
    Convert a key to a string.

    Args:
        key (Optional[Key]): The key to convert.

    Returns:
        str: The string representation of the key.
    """
    if key is None:
        return ""
    elif isinstance(key, SpecialKey):
        return __SPECIAL_KEYS[key]
    elif isinstance(key, KeyCode):
        assert key.char is not None
        return key.char
