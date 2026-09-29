import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app
from text_metadata import METADATA_PATH, text_metadata


class TextMetadataTests(unittest.TestCase):
    def test_one_entry_per_poet_preserves_titles_from_every_sample(self):
        with METADATA_PATH.open(encoding='utf-8-sig', newline='') as stream:
            rows = [row for row in csv.DictReader(stream)
                    if row['poet_id'] != 'QURAN' and row['era_ar'].replace('_', ' ').strip() != 'القرآن الكريم']
        records = text_metadata()
        self.assertEqual(len(records), len({row['poet_id'] for row in rows}))
        for record in records:
            samples = [row for row in rows if row['poet_id'] == record['author_id']]
            with self.subTest(author=record['author']):
                self.assertTrue(samples)
                self.assertEqual(record['author'], samples[0]['author_ar'].replace('_', ' '))
                self.assertEqual(record['period_ar'], samples[0]['era_ar'].replace('_', ' '))
                expected = {title.strip() for row in samples for title in row['poem_titles'].split('|')}
                self.assertEqual(set(record['poem_titles']), expected)
                self.assertEqual(len(record['poem_titles']), len(expected))
                self.assertEqual(record['primary_poem_title'], samples[0]['primary_poem_title'])

    def test_overlapping_titles_are_merged_in_source_order(self):
        rows = [
            dict(era_ar='الجاهلي', poet_id='1', author_ar='شاعر_أول', primary_poem_title='قصيدة أ', poem_titles='قصيدة أ | قصيدة ب'),
            dict(era_ar='الجاهلي', poet_id='1', author_ar='شاعر_أول', primary_poem_title='قصيدة ب', poem_titles='قصيدة ب | قصيدة ج | قصيدة أ'),
            dict(era_ar='الجاهلي', poet_id='2', author_ar='شاعر_ثان', primary_poem_title='قصيدة أ', poem_titles='قصيدة أ'),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.csv'
            with path.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0])
                writer.writeheader()
                writer.writerows(rows)
            text_metadata.cache_clear()
            try:
                with patch('text_metadata.METADATA_PATH', path):
                    records = text_metadata()
                self.assertEqual(len(records), 2)
                self.assertEqual(records[0]['poem_titles'], ['قصيدة أ', 'قصيدة ب', 'قصيدة ج'])
                self.assertEqual(records[1]['poem_titles'], ['قصيدة أ'])
            finally:
                text_metadata.cache_clear()

    def test_api_contains_only_unique_poets_in_all_periods(self):
        response = app.test_client().get('/api/text-metadata')
        self.assertEqual(response.status_code, 200)
        records = response.get_json()['records']
        self.assertEqual(len(records), 45)
        self.assertEqual(len({record['author_id'] for record in records}), 45)
        self.assertEqual({record['period'] for record in records}, {'PreIslamic', 'Mukhadramun', 'Umayyad', 'Abbasid', 'Andalusian'})
        self.assertTrue(all(record['author'] and record['poem_titles'] for record in records))


if __name__ == '__main__':
    unittest.main()
