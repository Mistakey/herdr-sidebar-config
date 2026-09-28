"""The platform layer: the only module that chooses an operating system.

Callers use these names and never branch on the platform themselves:

- ``Lock(path)``: an inter-process lock; ``acquire(blocking)``, ``release()``,
  and ``with Lock(path):`` for a blocking critical section.
- ``connect(path, timeout)``: a Herdr API connection with ``sendall`` and
  ``recv``; every step raises ``TimeoutError`` past ``timeout`` seconds.
- ``WakeListener(state)`` / ``wake(state)``: the scheduler's wake channel. A
  wake carries no data; it only makes the scheduler reread its state.
- ``spawn_detached(argv, log)``: start a process that outlives the hook and
  holds none of Herdr's output pipes.
- ``terminal()``: a context manager yielding the popup's terminal with
  ``size()``, ``clear()``, ``draw(y, x, text, style)``, ``refresh()``, and
  ``key()``. Styles are ``None``, ``"bold"``, or ``"reverse"``; keys are
  ``"up"``, ``"down"``, ``"left"``, ``"right"``, ``"enter"``, ``"escape"``,
  ``"backspace"``, ``"resize"``, or one typed character.
- ``entry(name)``: this platform's manifest id for a logical action or pane.
"""
import os
import sys

if os.name == "nt":
    from host_windows import Lock, WakeListener, connect, spawn_detached, terminal, wake
    PLATFORM = "windows"
else:
    from host_posix import Lock, WakeListener, connect, spawn_detached, terminal, wake
    PLATFORM = "macos" if sys.platform == "darwin" else "linux"

# Herdr rejects duplicate action/pane ids even when their platforms differ, so
# Windows declares its own. Keep this map and herdr-plugin.toml in step.
_POSIX = {"settings": "settings", "refresh": "refresh", "clear": "clear"}
ENTRIES = {"linux": _POSIX, "macos": _POSIX,
           "windows": {name: name + "-windows" for name in _POSIX}}


def entry(name):
    return ENTRIES[PLATFORM][name]


__all__ = ["ENTRIES", "PLATFORM", "Lock", "WakeListener", "connect", "entry",
           "spawn_detached", "terminal", "wake"]
