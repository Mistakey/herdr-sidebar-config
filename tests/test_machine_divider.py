import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from animation import cache_rows
from runtime import remote_machine
from sidebar import MACHINE_RULE, desired_rows, machine_boundary

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

    def test_divider_needs_workspace_order_and_a_remote(self):
        with patch("sidebar.remote_machine", return_value="Home"):
            self.assertTrue(machine_boundary("workspace"))
            self.assertFalse(machine_boundary("activity"))
        with patch("sidebar.remote_machine", return_value=None):
            self.assertFalse(machine_boundary("workspace"))


class MachineDividerRowsTests(unittest.TestCase):
    def test_divider_follows_only_the_last_agent(self):
        rows = desired_rows(PANES, SPACES, TABS, "text", divide_machines=True)
        self.assertEqual({p for p, v in rows.items() if v["hs_machine_rule"]}, {"p4"})
        self.assertEqual(rows["p4"]["hs_machine_rule"], MACHINE_RULE)

    def test_no_agents_publish_no_divider(self):
        rows = desired_rows([PANES[1], PANES[4]], SPACES, TABS, "text", divide_machines=True)
        self.assertTrue(all(v["hs_machine_rule"] is None for v in rows.values()))

    def test_other_tokens_do_not_change_with_a_divider(self):
        plain = desired_rows(PANES, SPACES, TABS, "text")
        divided = desired_rows(PANES, SPACES, TABS, "text", divide_machines=True)
        self.assertTrue(all(v["hs_machine_rule"] is None for v in plain.values()))
        strip = lambda rows: {p: {k: v for k, v in values.items() if k != "hs_machine_rule"}
                              for p, values in rows.items()}
        self.assertEqual(strip(plain), strip(divided))

    def test_animation_frames_never_touch_the_divider(self):
        rows = desired_rows(PANES, SPACES, TABS, "text", divide_machines=True)
        cached = cache_rows(PANES, rows)
        self.assertTrue(cached)
        self.assertTrue(all(row["token"] in ("hs_working", "hs_working_dim") for row in cached))


class MachineLayoutTests(unittest.TestCase):
    def test_every_row_list_closes_with_a_dim_divider(self):
        agents = tomllib.loads((ROOT / "sidebar-layout.toml").read_text(encoding="utf-8"))["ui"]["sidebar"]["agents"]
        for rows in [agents["rows"], *agents["rows_by_agent"].values()]:
            self.assertEqual(rows[-1], [{"token": "$hs_machine_rule", "dim": True, "fg": "#A8ADB9"}])
            tokens = {item["token"] for row in rows for item in row}
            self.assertFalse(tokens & {"$hs_machine", "$hs_machine_next"})


if __name__ == "__main__":
    unittest.main()
