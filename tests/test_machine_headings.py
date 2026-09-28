import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from animation import cache_rows
from runtime import remote_machine
from sidebar import desired_rows, heading_remote

ROOT = Path(__file__).resolve().parents[1]
SPACES = [{"workspace_id": "w1", "label": "one"}, {"workspace_id": "w2", "label": "two"}]
PANES = [
    {"pane_id": "p1", "workspace_id": "w1", "tab_id": "t1", "agent": "codex", "agent_status": "working"},
    {"pane_id": "p2", "workspace_id": "w1", "tab_id": "t1"},
    {"pane_id": "p3", "workspace_id": "w2", "tab_id": "t2", "agent": "claude", "agent_status": "idle"},
    {"pane_id": "p4", "workspace_id": "w2", "tab_id": "t2", "agent": "claude", "agent_status": "done"},
    {"pane_id": "p5", "workspace_id": "w2", "tab_id": "t3"},
]
TABS = {"t1": "a", "t2": "b", "t3": "c"}
MACHINE_KEYS = ("hs_machine", "hs_machine_next")


def catalog(*entries):
    return json.dumps({"version": 1, "ssh": list(entries)})


class RemoteMachineTests(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "endpoints.json")
            if text is not None:
                path.write_text(text, encoding="utf-8")
            return remote_machine(path)

    def test_missing_invalid_or_disabled_catalog_means_no_remote(self):
        self.assertIsNone(self.read(None))
        self.assertIsNone(self.read("{not json"))
        self.assertIsNone(self.read('["ssh"]'))
        self.assertIsNone(self.read('{"ssh": "Home"}'))
        self.assertIsNone(self.read(catalog()))
        self.assertIsNone(self.read(catalog({"label": "Home", "enabled": False})))
        self.assertIsNone(self.read(catalog({"label": "", "enabled": True})))

    def test_first_enabled_remote_names_the_boundary(self):
        self.assertEqual(self.read(catalog({"label": "Office", "enabled": False},
                                           {"label": "Home", "enabled": True},
                                           {"label": "Lab", "enabled": True})), "Home")

    def test_catalog_lives_in_the_client_state_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "client", "endpoints.json")
            path.parent.mkdir()
            path.write_text(catalog({"label": "Home", "enabled": True}), encoding="utf-8")
            with patch("runtime.host.state_home", return_value=Path(directory)):
                self.assertEqual(remote_machine(), "Home")

    def test_activity_order_publishes_no_machine_headings(self):
        with patch("sidebar.remote_machine", return_value="Home"):
            self.assertEqual(heading_remote("workspace"), "Home")
            self.assertIsNone(heading_remote("activity"))


class MachineHeadingRowsTests(unittest.TestCase):
    def test_local_heads_first_agent_and_remote_follows_last(self):
        rows = desired_rows(PANES, SPACES, TABS, "text", remote="Home")
        self.assertEqual(rows["p1"]["hs_machine"], "━ Local")
        self.assertEqual(rows["p4"]["hs_machine_next"], "━ Home")
        for pane_id, values in rows.items():
            if pane_id != "p1":
                self.assertIsNone(values["hs_machine"])
            if pane_id != "p4":
                self.assertIsNone(values["hs_machine_next"])

    def test_single_agent_carries_both_headings(self):
        rows = desired_rows(PANES[:2], SPACES, TABS, "text", remote="Home")
        self.assertEqual(rows["p1"]["hs_machine"], "━ Local")
        self.assertEqual(rows["p1"]["hs_machine_next"], "━ Home")

    def test_no_agents_publish_no_headings(self):
        rows = desired_rows([PANES[1], PANES[4]], SPACES, TABS, "text", remote="Home")
        self.assertTrue(all(v[k] is None for v in rows.values() for k in MACHINE_KEYS))

    def test_other_tokens_do_not_change_with_a_remote(self):
        plain = desired_rows(PANES, SPACES, TABS, "text")
        headed = desired_rows(PANES, SPACES, TABS, "text", remote="Home")
        self.assertTrue(all(v[k] is None for v in plain.values() for k in MACHINE_KEYS))
        strip = lambda rows: {p: {k: v for k, v in values.items() if k not in MACHINE_KEYS}
                              for p, values in rows.items()}
        self.assertEqual(strip(plain), strip(headed))

    def test_animation_frames_never_touch_machine_headings(self):
        rows = desired_rows(PANES, SPACES, TABS, "text", remote="Home")
        cached = cache_rows(PANES, rows)
        self.assertTrue(cached)
        self.assertTrue(all(row["token"] in ("hs_working", "hs_working_dim") for row in cached))


class MachineLayoutTests(unittest.TestCase):
    def test_every_row_list_opens_and_closes_with_a_machine_heading(self):
        agents = tomllib.loads((ROOT / "sidebar-layout.toml").read_text(encoding="utf-8"))["ui"]["sidebar"]["agents"]
        for rows in [agents["rows"], *agents["rows_by_agent"].values()]:
            for row, token in ((rows[0], "$hs_machine"), (rows[-1], "$hs_machine_next")):
                self.assertEqual(len(row), 1)
                self.assertEqual(row[0]["token"], token)
                self.assertTrue(row[0]["bold"])
                self.assertEqual(row[0]["fg"], "#F8F8F2")


if __name__ == "__main__":
    unittest.main()
