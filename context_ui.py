"""Read-only, dependency-free saved-context popup; never wake an agent."""
import curses
from datetime import datetime
import os
from pathlib import Path
import textwrap

from conversation_context import CONTROL, read_json
from runtime import PLUGIN_ID, herdr_binary, run_herdr


def open_popup():
    from sidebar import refresh
    refresh()
    binary = herdr_binary()
    snapshot = run_herdr(binary, "api", "snapshot")["result"]["snapshot"]
    tab_id = snapshot.get("focused_tab_id")
    if not tab_id:
        raise RuntimeError("Select a tab before opening saved context.")
    run_herdr(binary, "plugin", "pane", "open", "--plugin", PLUGIN_ID,
              "--entrypoint", "context", "--cwd", str(Path(__file__).resolve().parent),
              "--env", "HERDR_CONTEXT_TAB_ID=" + tab_id)


def lines_for_tab(snapshot, context, tab_id):
    tab = next((t for t in snapshot["tabs"] if t["tab_id"] == tab_id), None)
    if not tab:
        return ["This tab is no longer open."]
    workspace = next((w["label"] for w in snapshot["workspaces"] if w["workspace_id"] == tab["workspace_id"]), "")
    lines = [workspace + " / " + tab["label"], ""]
    agents = {a["pane_id"]: a for a in snapshot["agents"]}
    records = [(pid, rec) for pid, rec in context.get("records", {}).items()
               if rec.get("tab_id") == tab_id and not rec.get("detached")]
    if not records:
        return lines + ["No saved conversation context for this tab."]
    for pane_id, record in records:
        state = "sleeping" if record.get("sleeping") else agents.get(pane_id, {}).get("agent_status", "unknown")
        lines += [record["title"], record["provider"] + " | " + state]
        if record.get("request"):
            lines.append("Request: " + record["request"])
        stamp = record.get("recorded_at")
        if isinstance(stamp, (int, float)):
            lines.append("Recorded: " + datetime.fromtimestamp(stamp).strftime("%Y-%m-%d %H:%M"))
        lines += ["Source: " + record.get("source", "saved conversation"), ""]
    return [CONTROL.sub("", line) for line in lines]


def viewer(screen):
    curses.curs_set(0)
    screen.keypad(True)
    tab_id = os.environ.get("HERDR_CONTEXT_TAB_ID")
    if not tab_id:
        raise RuntimeError("Open context from the sidebar action.")
    snapshot = run_herdr(herdr_binary(), "api", "snapshot")["result"]["snapshot"]
    context = read_json(Path(os.environ["HERDR_PLUGIN_STATE_DIR"]) / "context.json")
    lines = lines_for_tab(snapshot, context, tab_id)
    offset = 0
    while True:
        height, width = screen.getmaxyx()
        wrapped = [part for line in lines for part in (textwrap.wrap(line, max(1, width - 4)) or [""])]
        room = max(1, height - 4)
        offset = min(offset, max(0, len(wrapped) - room))
        screen.erase()
        if height > 2 and width > 4:
            for index, line in enumerate(wrapped[offset:offset + room]):
                screen.addnstr(index + 1, 2, line, width - 4)
            screen.addnstr(height - 2, 2, "Up/Down scroll   Esc close", width - 4)
        screen.refresh()
        key = screen.get_wch()
        if key in ("q", "\x1b"):
            return
        if key == curses.KEY_DOWN:
            offset += 1
        elif key == curses.KEY_UP:
            offset = max(0, offset - 1)
        elif key == curses.KEY_NPAGE:
            offset += room
        elif key == curses.KEY_PPAGE:
            offset = max(0, offset - room)


def main():
    curses.wrapper(viewer)
