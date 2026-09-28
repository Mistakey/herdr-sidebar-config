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
"""
import os

if os.name == "nt":
    from host_windows import Lock, WakeListener, connect, spawn_detached, wake
else:
    from host_posix import Lock, WakeListener, connect, spawn_detached, wake

__all__ = ["Lock", "WakeListener", "connect", "spawn_detached", "wake"]
