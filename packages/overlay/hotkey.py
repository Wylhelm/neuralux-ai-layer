"""Global hotkey listener for X11 (Alt+Space).

On Wayland, global grabs are restricted; use a DE keyboard shortcut to launch
`aish overlay` instead. This module is a best-effort X11 implementation.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, Optional


class X11HotkeyListener:
    """Listen for Alt+Space globally using Xlib on X11 sessions."""

    def __init__(self, on_trigger: Callable[[], None], hotkey: str = "<Control>space"):
        self.on_trigger = on_trigger
        self.hotkey = hotkey
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        if os.environ.get("XDG_SESSION_TYPE", "").lower() != "x11":
            # Not X11; do nothing. Caller should document Wayland setup.
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop.clear()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            from Xlib import X, XK, display  # type: ignore
        except Exception:
            # Dependency not available; skip silently.
            return

        try:
            d = display.Display()
            root = d.screen().root
            # Parse hotkey string (very small subset: <Control>space or <Alt>space)
            key_name = "space"
            mod_mask = 0
            hk = self.hotkey.lower()
            if "control" in hk:
                mod_mask |= X.ControlMask
            if "alt" in hk:
                mod_mask |= X.Mod1Mask
            if "space" in hk:
                key_name = "space"
            # Map to keycode
            space_keycode = d.keysym_to_keycode(XK.string_to_keysym(key_name))

            # Attempt a couple of grabs (with/without NumLock/CapsLock)
            for lock_mask in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                try:
                    root.grab_key(space_keycode, mod_mask | lock_mask, True, X.GrabModeAsync, X.GrabModeAsync)
                except Exception:
                    pass

            while not self._stop.is_set():
                if d.pending_events() == 0:
                    d.sync()
                    d.flush()
                e = d.next_event()
                if e.type == X.KeyPress:
                    if e.detail == space_keycode and (e.state & mod_mask):
                        try:
                            self.on_trigger()
                        except Exception:
                            pass
        except Exception:
            # Fail silently to avoid crashing caller.
            pass


