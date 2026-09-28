"""Small Herdr CLI and icon helpers. No third-party runtime dependencies."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import host

PLUGIN_ID = "testy-cool.herdr-sidebar"
FONT_FAMILY = "Herdr Sidebar Logos"
PUA_LOGOS = {name: chr(0xE1A0 + index) for index, name in enumerate(
    ("claude", "codex", "opencode", "omp", "cline", "mastracode", "kimi", "kilo", "maki", "agy")
)}
TEXT_LOGOS = {"claude": "C", "codex": "AI", "opencode": "OC", "omp": "OMP",
              "cline": "CL", "mastracode": "MC", "kimi": "KIM", "kilo": "KIL", "maki": "MAK", "agy": "AGY"}


def herdr_binary():
    value = os.environ.get("HERDR_BIN_PATH", "herdr").removesuffix(" (deleted)")
    return value if shutil.which(value) else shutil.which("herdr") or value


def run_herdr(herdr, *args):
    try:
        result = subprocess.run([herdr, *args], capture_output=True, encoding="utf-8",
                                errors="replace", timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Could not run Herdr: {error}") from error
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Herdr command failed")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def icon_mode():
    config_dir = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    path = Path(config_dir) / "config.toml" if config_dir else None
    config = tomllib.loads(path.read_text(encoding="utf-8")) if path and path.exists() else {}
    mode = config.get("icons", "auto")
    if mode not in {"auto", "font", "text"}:
        raise RuntimeError("icons must be 'auto', 'font', or 'text' in the plugin config.toml")
    if mode != "auto":
        return mode
    return "font" if host.font_available(FONT_FAMILY) else "text"


def logo_for(agent, mode):
    return (PUA_LOGOS if mode == "font" else TEXT_LOGOS).get(agent, "◇")


def remote_machine(path=None):
    """Name of the first enabled remote in this client's machine catalog.

    Machine names exist only in the viewing client's catalog; a missing or
    unreadable catalog means no remote, never an error.
    """
    path = path or host.state_home() / "client" / "endpoints.json"
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    remotes = catalog.get("ssh") if isinstance(catalog, dict) else None
    for remote in remotes if isinstance(remotes, list) else []:
        if isinstance(remote, dict) and remote.get("enabled") is True:
            label = remote.get("label")
            return label if isinstance(label, str) and label.strip() else None
    return None
