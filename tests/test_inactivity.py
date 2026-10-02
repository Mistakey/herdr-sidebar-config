import json
import unittest

from inactivity import update_inactivity


def agent(workspace="w1", status="idle", pane="p1"):
    return {"workspace_id": workspace, "pane_id": f"{workspace}:{pane}",
            "agent": "codex", "agent_status": status,
            "agent_session": {"kind": "id", "value": "session-1"}}


class InactivityTests(unittest.TestCase):
    def test_ten_minute_boundary_and_no_further_timer_after_dimming(self):
        initial = update_inactivity(["w1"], [agent()], now=1000)
        self.assertEqual(initial.next_deadline, 1600)
        before = update_inactivity(["w1"], [agent()], initial.state, now=1599.9)
        self.assertFalse(before.inactive_ids)
        after = update_inactivity(["w1"], [agent()], before.state, now=1600)
        self.assertEqual(after.inactive_ids, {"w1"})
        self.assertIsNone(after.next_deadline)

    def test_any_working_agent_wakes_workspace_and_next_quiet_period_is_new(self):
        quiet = update_inactivity(["w1"], [agent()], now=1000)
        working = update_inactivity(
            ["w1"], [agent(), agent(status="working", pane="p2")], quiet.state, now=1700
        )
        self.assertFalse(working.inactive_ids)
        self.assertEqual(working.state["quiet_since"], {})
        self.assertIsNone(working.next_deadline)
        stopped = update_inactivity(["w1"], [agent(status="done")], working.state, now=1710)
        self.assertEqual(stopped.next_deadline, 2310)

    def test_focus_title_changes_and_json_restart_preserve_quiet_start(self):
        initial = update_inactivity(["w1"], [agent()], now=1000)
        restarted_state = json.loads(json.dumps(initial.state))
        pane = {**agent(), "focused": True, "terminal_title": "New title"}
        updated = update_inactivity(["w1"], [pane], restarted_state, now=1400)
        self.assertEqual(updated.state["quiet_since"], {"w1": 1000})
        self.assertEqual(updated.next_deadline, 1600)
        self.assertEqual(initial.state["observed_at"], 1000)

    def test_empty_and_blocked_workspaces_are_quiet_and_removed_ones_are_cleared(self):
        initial = update_inactivity(["w1", "w2"], [agent(status="blocked")], now=1000)
        self.assertEqual(initial.state["quiet_since"], {"w1": 1000, "w2": 1000})
        updated = update_inactivity(["w2", "w3"], [], initial.state, now=1200)
        self.assertEqual(updated.state["quiet_since"], {"w2": 1000, "w3": 1200})
        self.assertEqual(updated.next_deadline, 1600)
        next_period = update_inactivity(["w2", "w3"], [], updated.state, now=1600)
        self.assertEqual(next_period.inactive_ids, {"w2"})
        self.assertEqual(next_period.next_deadline, 1800)

    def test_backwards_clock_restarts_quiet_period(self):
        initial = update_inactivity(["w1"], [], now=1000)
        rolled_back = update_inactivity(["w1"], [], initial.state, now=900)
        self.assertEqual(rolled_back.state["quiet_since"], {"w1": 900})
        self.assertEqual(rolled_back.next_deadline, 1500)

    def test_untrusted_or_corrupt_saved_state_starts_fresh(self):
        for previous in [
            None,
            [],
            {"quiet_since": {"w1": 1}},
            {"version": 1, "observed_at": 100, "quiet_since": {"w1": "bad"}},
            {"version": 1, "observed_at": 100, "quiet_since": {"w1": 200}},
            {"version": 1, "observed_at": 100, "quiet_since": {"w1": float("nan")}},
        ]:
            with self.subTest(previous=previous):
                result = update_inactivity(["w1"], [], previous, now=1000)
                self.assertEqual(result.next_deadline, 1600)

    def test_empty_snapshot_needs_no_timer(self):
        result = update_inactivity([], [], now=1000)
        self.assertEqual(result.state["quiet_since"], {})
        self.assertFalse(result.inactive_ids)
        self.assertIsNone(result.next_deadline)

    def test_idle_pane_fades_within_working_workspace_and_wakes_independently(self):
        panes = [agent(), agent(status="working", pane="p2")]
        initial = update_inactivity(["w1"], panes, now=1000)
        self.assertEqual(initial.next_deadline, 1600)
        self.assertFalse(initial.inactive_ids)
        panes[0].update(focused=True, terminal_title="Renamed")
        before = update_inactivity(["w1"], panes, json.loads(json.dumps(initial.state)), now=1599)
        self.assertFalse(before.inactive_pane_ids)
        faded = update_inactivity(["w1"], panes, before.state, now=1600)
        self.assertEqual(faded.inactive_pane_ids, {"w1:p1"})
        self.assertFalse(faded.inactive_ids)
        self.assertIsNone(faded.next_deadline)
        panes[0]["agent_status"] = "working"
        awake = update_inactivity(["w1"], panes, faded.state, now=1601)
        self.assertFalse(awake.inactive_pane_ids)
        self.assertEqual(awake.state["pane_quiet_since"], {})
        panes[0]["agent_status"] = "idle"
        self.assertEqual(update_inactivity(["w1"], panes, awake.state, now=1602).next_deadline, 2202)

    def test_blocked_and_unseen_done_panes_keep_attention_in_busy_workspace(self):
        panes = [agent(status="working"), agent(status="blocked", pane="p2"),
                 agent(status="done", pane="p3"), agent(status="unknown", pane="p4")]
        first = update_inactivity(["w1"], panes, now=1000)
        result = update_inactivity(["w1"], panes, first.state, now=1600)
        self.assertEqual(result.inactive_pane_ids, {"w1:p4"})
        self.assertIsNone(result.next_deadline)

    def test_closed_released_or_replaced_agents_do_not_inherit_quiet_age(self):
        panes = [agent(), agent(status="working", pane="p2")]
        first = update_inactivity(["w1"], panes, now=1000)
        replacements = [dict(panes[0], agent="claude"),
                        dict(panes[0], terminal_id="new-terminal"),
                        dict(panes[0], agent_session={"kind": "id", "value": "new-session"})]
        for replacement in replacements:
            with self.subTest(replacement=replacement):
                result = update_inactivity(["w1"], [replacement, panes[1]], first.state, now=1600)
                self.assertFalse(result.inactive_pane_ids)
                self.assertEqual(result.next_deadline, 2200)
        for current in [[panes[1]], [dict(panes[0], agent=None), panes[1]], []]:
            self.assertEqual(update_inactivity(["w1"], current, first.state, now=1600).state["pane_quiet_since"], {})

    def test_pane_timers_reset_on_backwards_clock_and_invalid_records(self):
        panes = [agent(), agent(status="working", pane="p2")]
        first = update_inactivity(["w1"], panes, now=1000)
        rolled_back = update_inactivity(["w1"], panes, first.state, now=900)
        self.assertEqual(rolled_back.next_deadline, 1500)
        self.assertFalse(rolled_back.inactive_pane_ids)
        identity = first.state["pane_quiet_since"]["w1:p1"]["identity"]
        for record in [None, [], {"since": float("nan"), "identity": identity},
                       {"since": 1100, "identity": identity}]:
            with self.subTest(record=record):
                old = dict(first.state, pane_quiet_since={"w1:p1": record})
                self.assertEqual(update_inactivity(["w1"], panes, old, now=1200).next_deadline, 1800)
