import unittest

from preferences import validate, patch
from sidebar import desired_rows


class PaneNameTests(unittest.TestCase):
    def test_default_and_validation(self):
        self.assertIs(validate({})['pane_names'], False)
        with self.assertRaises(ValueError):
            validate({'pane_names': 'true'})
        self.assertIn('pane_names = true', patch('', {'pane_names': True}))

    def test_prefixes_renamed_panes_only(self):
        panes = [
            dict(pane_id='p1', workspace_id='w1', tab_id='t1', agent='codex', agent_status='idle',
                 label='api-fix', terminal_title_stripped='Fix login redirect'),
            dict(pane_id='p2', workspace_id='w1', tab_id='t1', agent='codex', agent_status='idle',
                 terminal_title_stripped='Write tests'),
            dict(pane_id='p3', workspace_id='w1', tab_id='t1', agent='codex', agent_status='idle',
                 label='docs-pass', terminal_title_stripped='docs-pass'),
        ]
        args = (panes, [{'workspace_id': 'w1', 'label': 'Demo'}], {'t1': 'main'})
        off = desired_rows(*args)
        on = desired_rows(*args, pane_names=True)
        self.assertEqual(off['p1']['hs_idle'], '○ Fix login redirect')
        self.assertEqual(on['p1']['hs_idle'], '○ api-fix - Fix login redirect')
        self.assertEqual(on['p2']['hs_idle'], '○ Write tests')
        self.assertEqual(on['p3']['hs_idle'], off['p3']['hs_idle'])
