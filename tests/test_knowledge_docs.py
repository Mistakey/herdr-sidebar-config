import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.check_knowledge_docs import check_all  # noqa: E402


class KnowledgeDocsTests(unittest.TestCase):
    def test_knowledge_docs_match_the_repository(self):
        failures = check_all()
        self.assertEqual(failures, [], "knowledge docs drifted from the code:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
