"""Large corpus selections must survive Cloud Run's buffered-response limit."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app, MAX_BUFFERED_JSON_BYTES, cached_run
from analysis import ERAS


class ExperimentResponseTests(unittest.TestCase):
    def test_select_all_keeps_complete_results_below_buffered_limit(self):
        config = {'eras': [era for era in ERAS if era != 'Islamic']}
        try:
            with app.test_client().post('/api/experiment', json=config) as response:
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                self.assertEqual(result['config']['eras'], config['eras'])
                self.assertEqual(result['sample_count'], 110)
                self.assertEqual(len(result['projection']), 110)
                self.assertEqual(len(result['feature_matrix']), 110)
                self.assertTrue(all(s['raw_text'] and s['text'] for s in result['samples']))
                # Reproduce the old transport failure with the very same result.
                old_size = len(json.dumps(result, ensure_ascii=True).encode('utf-8'))
                self.assertGreater(old_size, MAX_BUFFERED_JSON_BYTES)
                self.assertLess(len(response.data), MAX_BUFFERED_JSON_BYTES)
                self.assertEqual(json.loads(response.data), result)
        finally:
            cached_run.cache_clear()

    def test_oversized_json_streams_without_losing_unicode_or_numeric_data(self):
        result = {'samples': [{'text': 'الشعر الحديث ' * 12000}], 'feature_matrix': [[0.25, 0.75]]}
        with patch('app.cached_run', return_value=result), patch('app.MAX_BUFFERED_JSON_BYTES', 1024):
            with app.test_client().post('/api/experiment', json={}) as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, 'application/json')
                self.assertTrue(response.is_streamed)
                self.assertNotIn('Content-Length', response.headers)
                chunks = list(response.response)
                self.assertGreater(len(chunks), 1)
                self.assertLessEqual(max(map(len, chunks)), 65536)
                self.assertEqual(json.loads(b''.join(chunks)), result)

    def test_validation_errors_remain_json(self):
        with app.test_client().post('/api/experiment', json={'eras': ['Quran']}) as response:
            self.assertEqual(response.status_code, 400)
            self.assertIn('at least two', response.get_json()['error'])


if __name__ == '__main__':
    unittest.main()
