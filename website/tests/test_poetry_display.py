"""Keep source quotations authentic and display changes out of the analysis."""
import hashlib
import csv
import sys
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import (ROOT, ERA_DIR, ERAS, corpus_tokens, documents, normalize,
                      quran_comparison_text, run_experiment, validate)
from build_poetry_display import matched_passages, attach_poets
from poetry_examples import poetry_display, source_index


def anchors_for(*poems):
    anchors = defaultdict(list)
    for row, display in enumerate(poems, 2):
        key = quran_comparison_text(display)
        anchors[key[:24]].append((key, display, row))
    return anchors


class PoetryDisplayTests(unittest.TestCase):
    def test_attribution_keeps_all_distinct_source_poets(self):
        passages = [dict(csv_rows=[2, 3, 4, 5]), dict(csv_rows=[5])]
        attach_poets(passages, {2: 'شاعر أول', 3: 'شاعر أول', 4: 'شاعر آخر', 5: ''})
        self.assertEqual(set(passages[0]['poets']), {'شاعر أول', 'شاعر آخر'})
        self.assertEqual(passages[1]['poets'], [])

    def test_all_indexed_poets_match_their_source_records(self):
        with (ROOT / 'Arabic_Poetry_Dataset.csv').open(encoding='utf-8-sig', newline='') as stream:
            poets = {i: ' '.join(row['poet_name'].split()) for i, row in enumerate(csv.DictReader(stream), 2)}
        for era in ERAS:
            if era in ('Quran', 'Islamic'):
                continue
            for passage in source_index(era)['passages']:
                self.assertEqual(passage['poets'], sorted({poets[i] for i in passage['csv_rows'] if poets[i]}))

    def test_full_poems_only_and_ambiguous_spellings_are_excluded(self):
        poem = 'ألا يا أيها القلب الحزين على فراق أحبتي'
        words = quran_comparison_text(poem).split()
        found, ambiguous = matched_passages(words, anchors_for(poem, poem))
        self.assertEqual(ambiguous, 0)
        self.assertEqual(found, [dict(start_word=0, end_word=len(words), text=poem, csv_rows=[2, 3])])
        self.assertEqual(matched_passages(words[:-1], anchors_for(poem))[0], [])
        alternative = poem.replace('على', 'علي')
        self.assertEqual(matched_passages(words, anchors_for(poem, alternative)), ([], 2))

    def test_sample_boundaries_and_uncovered_text(self):
        poem = 'ألا يا أيها القلب الحزين على فراق أحبتي'
        old = quran_comparison_text(poem).split()
        index = dict(ends=[len(old)+1], display_source_sha256='fixture', passages=[
            dict(start_word=1, end_word=len(old)+1, text=poem, csv_rows=[7], poets=['شاعر المثال'])])
        # A sample cuts into a poem and ends in text absent from the source.
        tokens = old[2:] + ['غريب']
        text = ' '.join(tokens)
        with patch('poetry_examples.source_index', return_value=index):
            result = poetry_display('PreIslamic', tokens, text, 3, normalize)
        corrected = ' '.join(poem.split()[2:])
        self.assertEqual(result['display_text'], corrected + ' غريب')
        self.assertEqual(result['display_spans'], [dict(start=0, end=len(corrected), csv_rows=[7], poets=['شاعر المثال'])])
        with patch('poetry_examples.source_index', return_value=None):
            self.assertEqual(poetry_display('PreIslamic', tokens, text, 3, normalize)['display_spans'], [])

    def test_all_eras_preserve_historical_samples_and_align_source_text(self):
        for fold in [False, True]:
            config = validate(dict(eras=[e for e in ERAS if e != 'Islamic'], words=500, samples=3, fold=fold))
            docs, _ = documents(config)
            tokens = {e: corpus_tokens(ERA_DIR / f'{e}.txt') for e in config['eras'] if e != 'Quran'}
            for doc in docs:
                if doc['era'] == 'Quran':
                    continue
                with self.subTest(era=doc['era'], fold=fold):
                    start = doc['chunk'] * config['words']
                    raw = ' '.join(tokens[doc['era']][start:start+config['words']])
                    self.assertEqual(doc['raw_text'], raw)
                    self.assertEqual(doc['text'], normalize(raw, fold))
                    self.assertEqual(doc['sha256'], hashlib.sha256(raw.encode()).hexdigest())
                    self.assertEqual(len(doc['text']), len(doc['display_text']))
                    self.assertEqual(quran_comparison_text(doc['text']), quran_comparison_text(doc['display_text']))
                    index = source_index(doc['era'])
                    for span in doc['display_spans']:
                        quote = doc['display_text'][span['start']:span['end']]
                        self.assertTrue(any(quote in p['text'] and span['csv_rows'] == p['csv_rows']
                                            and span['poets'] == p['poets'] for p in index['passages']))

    def test_seven_feature_sets_and_both_fold_settings_ignore_display(self):
        sets = [('words', 1), ('wordgrams', 2)] + [('chargrams', n) for n in [1, 2, 3, 5, 7]]
        for fold in [False, True]:
            for feature, ngram in sets:
                with self.subTest(fold=fold, feature=feature, ngram=ngram):
                    config = dict(eras=['Quran', 'PreIslamic', 'Abbasid', 'Modern'], words=500,
                                  samples=2, feature=feature, ngram=ngram, fold=fold)
                    current = run_experiment(config)
                    # Adversarial display text must never affect any computation.
                    with patch('analysis.poetry_display', return_value=dict(display_text='نص مختلف تماما', display_spans=[])):
                        changed = run_experiment(config)
                    for key in ['feature_names', 'feature_matrix', 'features', 'linkage', 'silhouette',
                                'branch', 'pca_features', 'explained', 'projection']:
                        self.assertEqual(current[key], changed[key], key)
                    self.assertTrue(all(not any(k.startswith('display_') for k in leaf) for leaf in current['leaves']))


if __name__ == '__main__':
    unittest.main()
