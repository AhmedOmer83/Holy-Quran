"""Protect the verified source and keep its attribution outside the samples."""
import sys
import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import ROOT, ERA_DIR, corpus_tokens, catalog, documents, normalize, validate, quran_comparison_text


class QuranSourceTests(unittest.TestCase):
    def test_all_verses_match_official_reference(self):
        source = (ERA_DIR / 'Quran.txt').read_text()
        lines = [line for line in source.splitlines() if line and not line.startswith('#')]
        xml = ET.parse(ROOT / 'quran-audit/tanzil-simple-clean-1.1.xml').getroot()
        reference = [' '.join(filter(None, [verse.get('bismillah'), verse.get('text')]))
                     for sura in xml for verse in sura]
        self.assertEqual(len(lines), 6236)
        self.assertEqual(lines, reference)
        self.assertIn('أولئك على هدى من ربهم وأولئك هم المفلحون', lines)
        self.assertIn('Tanzil Quran Text (Simple Clean, Version 1.1)', source)

    def test_license_notice_does_not_change_sampling(self):
        tokens = corpus_tokens(ERA_DIR / 'Quran.txt')
        self.assertEqual(len(tokens), 78248)
        self.assertEqual(tokens[-3:], ['من', 'الجنة', 'والناس'])
        self.assertNotIn('Tanzil', tokens)
        self.assertEqual(next(e['words'] for e in catalog() if e['id'] == 'Quran'), 78248)
        docs, _ = documents(validate({'eras': ['Quran', 'PreIslamic']}))
        quran = [d for d in docs if d['era'] == 'Quran']
        self.assertEqual(len(quran), 10)
        self.assertTrue(all(len(d['raw_text'].split()) == 7000 for d in quran))

    def test_comments_are_not_corpus_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.txt'
            path.write_text('\ufeffبسم الله\n  # Attribution notice\n\nالرحمن الرحيم\n')
            self.assertEqual(corpus_tokens(path), ['بسم', 'الله', 'الرحمن', 'الرحيم'])

    def test_analytical_normalization_keeps_seated_hamza_and_ta(self):
        self.assertEqual(normalize('أولئك يؤمنون الصلاة على'), 'اولئك يؤمنون الصلاة علي')
        self.assertEqual(normalize('أولئك يؤمنون الصلاة على', False), 'أولئك يؤمنون الصلاة على')

    def test_entire_comparison_text_matches_old_quran(self):
        old = (ROOT / 'quran-audit/Quran.before-2026-09-27.txt').read_text().split()
        corrected = corpus_tokens(ERA_DIR / 'Quran.txt')
        self.assertEqual([quran_comparison_text(word) for word in corrected], old)

    def test_display_and_analysis_are_aligned_with_both_fold_settings(self):
        old = (ROOT / 'quran-audit/Quran.before-2026-09-27.txt').read_text().split()
        for fold in [True, False]:
            for words in [500, 7000]:
                with self.subTest(fold=fold, words=words):
                    docs, _ = documents(validate({'eras': ['Quran', 'PreIslamic'], 'fold': fold, 'words': words}))
                    for doc in docs:
                        if doc['era'] != 'Quran':
                            self.assertIn('display_text', doc)
                            self.assertIn('display_spans', doc)
                            continue
                        expected = ' '.join(old[doc['chunk']*words:(doc['chunk']+1)*words])
                        self.assertEqual(doc['text'], normalize(expected, fold))
                        self.assertEqual(quran_comparison_text(doc['display_text']), doc['text'])
                        self.assertEqual(len(doc['display_text']), len(doc['text']))
                        self.assertEqual(doc['display_text'], doc['raw_text'])
                        self.assertEqual(doc['analysis_sha256'], hashlib.sha256(doc['text'].encode()).hexdigest())
                        self.assertEqual(doc['sha256'], hashlib.sha256(doc['raw_text'].encode()).hexdigest())


if __name__ == '__main__':
    unittest.main()
