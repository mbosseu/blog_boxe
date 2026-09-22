import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
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

    def test_groq_research_and_structured_writing_are_separate_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'data').mkdir()
            (root / 'data/news_candidates.json').write_text('{"items": []}', encoding='utf-8')
            (root / 'data/news_articles.json').write_text('{"items": []}', encoding='utf-8')
            def research_response(label):
                return SimpleNamespace(
                    output_text=label,
                    model_dump=lambda: {'output': [{'content': [{'annotations': [
                        {'url': 'https://example.org/source', 'title': 'Source'}
                    ]}]}]},
                )
            writing_response = SimpleNamespace(output_text='{"action":"skip","reason":"preuves insuffisantes","draft":null}')
            responses = unittest.mock.Mock()
            responses.create.side_effect = [research_response('Rapport documenté'), writing_response]
            client = SimpleNamespace(responses=responses)
            now = datetime(2026, 9, 21, 8, tzinfo=timezone.utc)

            dossier = cloud_editor.research(client, root, now)
            proposal = cloud_editor.propose(client, root, now, dossier)

            self.assertIn('https://example.org/source', dossier)
            self.assertEqual(proposal['action'], 'skip')
            research_calls = responses.create.call_args_list[:1]
            writing_call = responses.create.call_args_list[1]
            self.assertEqual(len(research_calls), 1)
            for research_call in research_calls:
                self.assertEqual(research_call.kwargs['tools'], [{'type': 'browser_search'}])
                self.assertEqual(research_call.kwargs['tool_choice'], 'required')
                self.assertNotIn('text', research_call.kwargs)
            self.assertIn('text', writing_call.kwargs)
            self.assertNotIn('tools', writing_call.kwargs)


if __name__ == '__main__':
    unittest.main()
