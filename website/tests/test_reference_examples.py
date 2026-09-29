"""Regression for Modern's uncovered default samples and optional references."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import documents, normalize, quran_comparison_text, validate
from app import app
from poetry_examples import reference_example, source_index


class ReferenceExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = validate(dict(eras=['Quran', 'Modern']))
        docs, _ = documents(cls.config)
        cls.modern = [d for d in docs if d['era'] == 'Modern']

    def test_default_modern_absence_is_source_coverage_not_missing_analysis(self):
        self.assertEqual(len(self.modern), 10)
        self.assertTrue(all(d['text'] and not d['display_spans'] for d in self.modern))
        self.assertTrue(any('من' in d['text'].split() for d in self.modern))

    def test_reference_is_corrected_attributed_and_outside_sampled_chunks(self):
        with patch('analysis.documents', side_effect=AssertionError('Must not resample')):
            example = reference_example('Modern', 'من', self.config)
        self.assertEqual(example['scope'], 'outside_analysis_samples')
        self.assertEqual(example['analysis_match'], 'من')
        self.assertTrue(example['poets'])
        for sample in self.modern:
            left = sample['chunk'] * self.config['words']
            right = left + self.config['words']
            self.assertTrue(example['end_word'] <= left or example['start_word'] >= right)
        passage = next(p for p in source_index('Modern')['passages'] if p['start_word'] == example['start_word'])
        self.assertEqual(example['poets'], passage['poets'])
        self.assertEqual(example['csv_rows'], passage['csv_rows'])
        quote = (example['before'] + example['match'] + example['after']).removeprefix('… ').removesuffix(' …')
        self.assertIn(quote, passage['text'])

    def test_seven_feature_sets_and_both_fold_settings_match_historical_text(self):
        passage = source_index('Modern')['passages'][0]
        text = quran_comparison_text(passage['text'])
        tokens = text.split()
        sets = [('words', 1, tokens[0]), ('wordgrams', 2, ' '.join(tokens[:2]))]
        sets += [('chargrams', n, text[:n]) for n in [1, 2, 3, 5, 7]]
        for fold in [False, True]:
            for kind, n, feature in sets:
                with self.subTest(kind=kind, n=n, fold=fold):
                    example = reference_example('Modern', feature, {**self.config, 'feature':kind, 'ngram':n, 'fold':fold})
                    self.assertIsNotNone(example)
                    self.assertEqual(example['analysis_match'], feature)
                    self.assertEqual(normalize(quran_comparison_text(example['match']), fold), feature.strip())

    def test_whole_word_boundaries_and_empty_results(self):
        fixture = dict(passages=[dict(start_word=0, end_word=2, text='وقال أولئك', poets=['شاعر'], csv_rows=[2])],
                       display_source_sha256='csv', analysis_source_sha256='txt')
        with patch('poetry_examples.source_index', return_value=fixture):
            self.assertIsNone(reference_example('Modern', 'قال', self.config))
            self.assertEqual(reference_example('Modern', 'اوليك', self.config)['match'], 'أولئك')
            self.assertIsNone(reference_example('Modern', 'لفظةغيرموجودة', self.config))

    def test_api_validates_selection_and_keeps_reference_separate(self):
        client = app.test_client()
        payload = dict(config=self.config, era='Modern', feature='من')
        response = client.post('/api/reference-example', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json), {'example'})
        self.assertEqual(response.json['example']['scope'], 'outside_analysis_samples')
        for bad in [None, [], {**payload, 'era':'Abbasid'}, {**payload, 'era':'Quran'},
                    {**payload, 'era':'../Modern'}, {**payload, 'feature':[]}, {**payload, 'config':None}]:
            with self.subTest(payload=bad):
                self.assertEqual(client.post('/api/reference-example', json=bad).status_code, 400 if bad is not None else 415)
        self.assertIsNone(client.post('/api/reference-example', json={**payload, 'feature':'لفظةغيرموجودة'}).json['example'])


if __name__ == '__main__':
    unittest.main()
