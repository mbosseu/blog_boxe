import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import cloud_editor


class CloudEditorTests(unittest.TestCase):
    def test_skip_response_can_use_null_draft(self):
        draft_schema = cloud_editor.article_schema()['properties']['draft']
        self.assertEqual(draft_schema['anyOf'][1], {'type': 'null'})

    def test_daily_quota_stops_before_creating_api_client(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'data').mkdir()
            (root / 'data/news_articles.json').write_text(json.dumps({'items': [
                {'published_at': '2026-09-20T06:00:00+00:00'}
            ]}), encoding='utf-8')
            with patch.object(cloud_editor, 'OpenAI') as client:
                result = cloud_editor.run(root, datetime(2026, 9, 20, 12, tzinfo=timezone.utc))
            self.assertEqual(result, 0)
            client.assert_not_called()


if __name__ == '__main__':
    unittest.main()
