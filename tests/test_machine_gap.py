import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime import remote_machine
from sidebar import BLANK, desired_rows, machine_boundary

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

    def test_gap_needs_workspace_order_and_a_remote(self):
        with patch("sidebar.remote_machine", return_value="Home"):
            self.assertTrue(machine_boundary("workspace"))
            self.assertFalse(machine_boundary("activity"))
        with patch("sidebar.remote_machine", return_value=None):
            self.assertFalse(machine_boundary("workspace"))


class MachineGapRowsTests(unittest.TestCase):
    def test_last_agent_gets_a_gap_before_the_next_machine(self):
        plain = desired_rows(PANES, SPACES, TABS, "text")
        divided = desired_rows(PANES, SPACES, TABS, "text", divide_machines=True)
        self.assertIsNone(plain["p4"]["hs_gap"])
        self.assertEqual(divided["p4"]["hs_gap"], BLANK)

    def test_no_agents_publish_no_gap(self):
        rows = desired_rows([PANES[1], PANES[4]], SPACES, TABS, "text", divide_machines=True)
        self.assertTrue(all(v["hs_gap"] is None for v in rows.values()))

    def test_only_the_last_agent_changes(self):
        plain = desired_rows(PANES, SPACES, TABS, "text")
        divided = desired_rows(PANES, SPACES, TABS, "text", divide_machines=True)
        plain["p4"]["hs_gap"] = BLANK
        self.assertEqual(plain, divided)

    def test_inactive_last_group_keeps_its_gap(self):
        rows = desired_rows(PANES, SPACES, TABS, "text", inactive_ids={"w2"}, divide_machines=True)
        self.assertEqual(rows["p4"]["hs_gap"], BLANK)


if __name__ == "__main__":
    unittest.main()
