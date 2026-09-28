"""POSIX platform layer: flock, Unix sockets, and a new session per worker."""
import fcntl
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import tempfile


class Lock:
    def __init__(self, path):
        self._fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)

    def acquire(self, blocking=True):
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            return False
        return True

    def release(self):
        fcntl.flock(self._fd, fcntl.LOCK_UN)

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.close()


def connect(path, timeout):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(timeout)
        client.connect(path)
    except BaseException:
        client.close()
        raise
    return client


def _address(state):
    key = hashlib.sha256(str(Path(state).resolve()).encode()).hexdigest()[:20]
    return str(Path(tempfile.gettempdir()) / f"hs-{os.getuid()}-{key}.sock")


class WakeListener:
    def __init__(self, state):
        self._path = Path(_address(state))
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            self._path.unlink(missing_ok=True)
            self._socket.bind(str(self._path))
            self._path.chmod(0o600)
        except BaseException:
            self._socket.close()
            raise

    def wait(self, timeout):
        """Return True when woken, False when ``timeout`` seconds passed."""
        self._socket.settimeout(timeout)
        try:
            self._socket.recv(128)
        except socket.timeout:
            return False
        return True

    def close(self):
        if self._socket.fileno() != -1:
            self._path.unlink(missing_ok=True)
            self._socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def wake(state):
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
        try:
            client.setblocking(False)
            client.sendto(b"refresh", _address(state))
        except OSError:
            pass  # A starting scheduler reads the newest state after binding.


def spawn_detached(argv, log):
    with open(log, "a", encoding="utf-8") as stream:
        return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                start_new_session=True)
