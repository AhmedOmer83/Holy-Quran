"""Reproduce the source audit and controlled sensitivity experiment locally."""
import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'website'))
import numpy as np
from scipy.cluster.hierarchy import cophenet
from scipy.stats import spearmanr
import analysis

FOLDS = {'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ة': 'ه', 'ئ': 'ي', 'ؤ': 'و'}
TABLE = str.maketrans(FOLDS)
old_path = OUT / 'Quran.before-2026-09-27.txt'
new_path = analysis.ERA_DIR / 'Quran.txt'
old_lines = old_path.read_text().splitlines()
new_lines = [line for line in new_path.read_text().splitlines() if line and not line.startswith('#')]
assert len(old_lines) == len(new_lines) == 6236
assert [line.translate(TABLE) for line in new_lines] == old_lines
xml = ET.parse(OUT / 'tanzil-simple-clean-1.1.xml').getroot()
verses = [(int(sura.get('index')), sura.get('name'), int(verse.get('index')),
           ' '.join(filter(None, [verse.get('bismillah'), verse.get('text')])))
          for sura in xml for verse in sura]
assert [v[3] for v in verses] == new_lines

pairs, letters = Counter(), Counter()
changes = []
for line_number, (old, new, verse) in enumerate(zip(old_lines, new_lines, verses), 1):
    assert len(old.split()) == len(new.split())
    for word_number, (before, after) in enumerate(zip(old.split(), new.split()), 1):
        if before != after:
            pairs[before, after] += 1
            changes.append([line_number, verse[0], verse[1], verse[2], word_number, before, after])
    letters.update(b for a, b in zip(old, new) if a != b)

def write_csv(name, fields, rows):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)

write_csv('all-corrections.csv', ['line', 'sura', 'sura_name', 'aya', 'word_in_line', 'before', 'after'], changes)
write_csv('distinct-corrections.csv', ['before', 'after', 'occurrences'],
          [[a, b, count] for (a, b), count in pairs.most_common()])
ambiguous = defaultdict(set)
for line in new_lines:
    for word in line.split():
        ambiguous[word.translate(TABLE)].add(word)
ambiguous = {word: sorted(forms) for word, forms in ambiguous.items() if len(forms) > 1}
profiles = {}
for era in analysis.ERAS:
    counts = Counter(' '.join(analysis.corpus_tokens(analysis.ERA_DIR / f'{era}.txt')))
    profiles[era] = {letter: counts[letter] for letter in 'أإآٱىةئؤء'}
summary = dict(
    source_url='https://tanzil.net/pub/download/index.php?quranType=simple-clean&outType=txt&agree=true',
    source_name='Tanzil Project — Simple Clean, version 1.1', retrieved='2026-09-27',
    old_sha256=hashlib.sha256(old_path.read_bytes()).hexdigest(),
    corrected_sha256=hashlib.sha256(new_path.read_bytes()).hexdigest(),
    verses=6236, words_before=sum(len(x.split()) for x in old_lines),
    words_after=sum(len(x.split()) for x in new_lines),
    changed_verses=sum(a != b for a, b in zip(old_lines, new_lines)),
    changed_tokens=len(changes), distinct_corrections=len(pairs),
    restored_letters=dict(letters), legacy_mapping=FOLDS,
    differences_not_explained_by_legacy_mapping=0,
    ambiguous_legacy_forms=ambiguous, current_corpus_letter_profiles=profiles,
    preserved_basmala_prefixes=sum(bool(v.get('bismillah')) for s in xml for v in s),
)
(OUT / 'source-audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')

original_tokens = analysis.corpus_tokens
original_normalize = analysis.normalize
old_tokens = ' '.join(old_lines).split()

def historical_tokens(path):
    return old_tokens if path == new_path else original_tokens(path)

def shared_legacy_normalization(text, fold=True):
    return original_normalize(text, fold).translate(TABLE)

def metrics(result):
    return dict(silhouette=result['silhouette'], branch_purity=result['branch']['purity'],
                branch_separate=result['branch']['separate'], feature_count=result['feature_count'])

rows = []
sets = [('words', 'words', 1), ('word2', 'wordgrams', 2)] + [(f'char{n}', 'chargrams', n) for n in [1, 2, 3, 5, 7]]
for fold in [True, False]:
    for name, feature, ngram in sets:
        config = dict(feature=feature, ngram=ngram, fold=fold)
        with patch('analysis.corpus_tokens', side_effect=historical_tokens):
            before = analysis.run_experiment(config)
        # Reproduce the historical corrected-only scenario explicitly now
        # that the application restores legacy Quran comparison spelling.
        with patch('analysis.quran_comparison_text', side_effect=lambda text: analysis.normalize(text, fold)):
            after = analysis.run_experiment(config)
        with patch('analysis.normalize', side_effect=shared_legacy_normalization):
            harmonized = analysis.run_experiment(config)
        assert [s['id'] for s in before['samples']] == [s['id'] for s in after['samples']]
        assert before['feature_names'] == harmonized['feature_names']
        assert before['feature_matrix'] == harmonized['feature_matrix']
        assert before['linkage'] == harmonized['linkage']
        assert metrics(before) == metrics(harmonized)
        before_names, after_names = before['feature_names'], after['feature_names']
        vocabulary = sorted(set(before_names) | set(after_names))
        def aligned(result):
            index = {word: i for i, word in enumerate(result['feature_names'])}
            matrix = np.array(result['feature_matrix'])
            return np.column_stack([matrix[:, index[word]] if word in index else np.zeros(len(matrix)) for word in vocabulary])
        diff = np.abs(aligned(before) - aligned(after))
        row = dict(feature_set=name, fold=fold, config=after['config'], before=metrics(before),
                   corrected_only=metrics(after), shared_legacy=metrics(harmonized),
                   added_features=sorted(set(after_names) - set(before_names)),
                   removed_features=sorted(set(before_names) - set(after_names)),
                   changed_retained_frequencies=int(np.count_nonzero(diff > 1e-15)),
                   max_absolute_frequency_change=float(diff.max()),
                   changed_normalized_samples=sum(a['text'] != b['text'] for a, b in zip(before['samples'], after['samples'])),
                   tree_cophenetic_spearman=float(spearmanr(cophenet(np.array(before['linkage'])), cophenet(np.array(after['linkage']))).statistic),
                   shared_legacy_exactly_reproduces_baseline=True)
        rows.append(row)
        (OUT / 'sensitivity.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
        print(name, 'fold=', fold, 'silhouette:', round(before['silhouette'], 6), '->', round(after['silhouette'], 6),
              'purity:', before['branch']['purity'], '->', after['branch']['purity'],
              'shared legacy: EXACT', flush=True)

write_csv('sensitivity.csv', ['feature_set', 'fold', 'silhouette_before', 'silhouette_corrected',
                            'purity_before', 'purity_corrected', 'new_features', 'changed_frequencies',
                            'tree_correlation', 'shared_legacy_exact'],
          [[r['feature_set'], r['fold'], r['before']['silhouette'], r['corrected_only']['silhouette'],
            r['before']['branch_purity'], r['corrected_only']['branch_purity'], len(r['added_features']),
            r['changed_retained_frequencies'], r['tree_cophenetic_spearman'], True] for r in rows])
print('Audit and all controlled comparisons complete.', flush=True)
