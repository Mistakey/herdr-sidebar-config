"""Windows platform layer: byte-range locks, named pipes, and localhost UDP.

Herdr on Windows writes ``HERDR_SOCKET_PATH`` as a small text file and listens
on the named pipe ``\\\\.\\pipe\\`` followed by that full path. Pipe I/O is
overlapped so every step has the same bounded timeout as the POSIX socket.
"""
import _winapi
import msvcrt
import os
from pathlib import Path
import socket
import subprocess
import time

ERROR_BROKEN_PIPE = 109
ERROR_PIPE_BUSY = 231
ERROR_IO_PENDING = 997
ERROR_MORE_DATA = 234
WAIT_TIMEOUT = 258
POLL = 0.01


class Lock:
    """Locks one byte at offset zero; the handle's close releases it."""

    def __init__(self, path):
        self._fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_BINARY, 0o666)

    def acquire(self, blocking=True):
        while True:
            os.lseek(self._fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
                return True
            except OSError:
                if not blocking:
                    return False
            # msvcrt's own blocking mode gives up after ten seconds.
            time.sleep(POLL)

    def release(self):
        os.lseek(self._fd, 0, os.SEEK_SET)
        msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.close()


class _Pipe:
    def __init__(self, name, timeout):
        self._timeout = timeout
        deadline = time.monotonic() + timeout
        while True:
            try:
                self._handle = _winapi.CreateFile(
                    name, _winapi.GENERIC_READ | _winapi.GENERIC_WRITE, 0, _winapi.NULL,
                    _winapi.OPEN_EXISTING, _winapi.FILE_FLAG_OVERLAPPED, _winapi.NULL)
                return
            except OSError as error:
                if error.winerror != ERROR_PIPE_BUSY:
                    raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Herdr's API pipe stayed busy.")
            try:
                _winapi.WaitNamedPipe(name, max(1, int(remaining * 1000)))
            except OSError:
                pass  # Timed out or vanished; the next attempt says which.

    def _finish(self, overlapped, pending):
        if pending:
            result = _winapi.WaitForMultipleObjects([overlapped.event], False,
                                                    int(self._timeout * 1000))
            if result == WAIT_TIMEOUT:
                overlapped.cancel()
                try:
                    overlapped.GetOverlappedResult(True)
                except OSError:
                    pass
                raise TimeoutError("Herdr did not answer in time.")
        return overlapped.GetOverlappedResult(True)

    def sendall(self, data):
        view = memoryview(data)
        while view:
            overlapped, error = _winapi.WriteFile(self._handle, view, overlapped=True)
            written, _ = self._finish(overlapped, error == ERROR_IO_PENDING)
            view = view[written:]

    def recv(self, size):
        try:
            overlapped, error = _winapi.ReadFile(self._handle, size, overlapped=True)
            self._finish(overlapped, error == ERROR_IO_PENDING)
        except BrokenPipeError:
            return b""
        except OSError as error:
            if error.winerror == ERROR_BROKEN_PIPE:
                return b""
            raise
        return overlapped.getbuffer()

    def close(self):
        if self._handle is not None:
            _winapi.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def connect(path, timeout):
    return _Pipe("\\\\.\\pipe\\" + str(path), timeout)


def _port_file(state):
    return Path(state) / "deadline.port"


class WakeListener:
    """A localhost UDP socket whose port is published in the state directory.

    Any local process could send to it; a wake only triggers a state reread,
    so a forged datagram is harmless.
    """

    def __init__(self, state):
        self._file = _port_file(state)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._socket.bind(("127.0.0.1", 0))
            temporary = self._file.with_suffix(".tmp")
            temporary.write_text(str(self._socket.getsockname()[1]), encoding="utf-8")
            temporary.replace(self._file)
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
            self._file.unlink(missing_ok=True)
            self._socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def wake(state):
    try:
        port = int(_port_file(state).read_text(encoding="utf-8"))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.sendto(b"refresh", ("127.0.0.1", port))
    except (OSError, ValueError):
        pass  # A starting scheduler reads the newest state after binding.


def spawn_detached(argv, log):
    # Only the log handle is inherited: holding Herdr's output pipes would keep
    # the hook "running" and occupy one of Herdr's concurrent plugin slots.
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    with open(log, "a", encoding="utf-8") as stream:
        return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                creationflags=flags, close_fds=True)
