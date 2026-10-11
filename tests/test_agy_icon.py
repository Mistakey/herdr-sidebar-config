import unittest
from runtime import logo_for
from configuration import GHOSTTY_MAPPING, ghostty_mapping


class AgyIconTests(unittest.TestCase):
    def test_agy_font_and_text(self):
        self.assertEqual(logo_for('agy', 'font'), '\ue1a9')
        self.assertEqual(logo_for('agy', 'text'), 'AGY')

    def test_upgrade_mapping_without_duplicates(self):
        for last in ('E1A8', 'E1A9', 'E1AA', 'E1AB'):
            old = f'font-codepoint-map = U+E1A0-U+{last}=Herdr Sidebar Logos\n'
            updated = ghostty_mapping(old)
            self.assertEqual(updated.count('font-codepoint-map'), 1)
            self.assertIn(GHOSTTY_MAPPING, updated)
            self.assertEqual(ghostty_mapping(updated), updated)
