"""Prove numerical equivalence to the archived Quran for all UI feature sets."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analysis

old_tokens = (analysis.ROOT / 'quran-audit/Quran.before-2026-09-27.txt').read_text().split()
original_tokens = analysis.corpus_tokens


def historical_tokens(path):
    return old_tokens if path == analysis.ERA_DIR / 'Quran.txt' else original_tokens(path)


sets = [('words', 1), ('wordgrams', 2)] + [('chargrams', n) for n in [1, 2, 3, 5, 7]]
for feature, ngram in sets:
    with patch('analysis.corpus_tokens', side_effect=historical_tokens):
        baseline = analysis.run_experiment({'feature': feature, 'ngram': ngram})
    for fold in [True, False]:
        current = analysis.run_experiment({'feature': feature, 'ngram': ngram, 'fold': fold})
        for key in ['feature_names', 'feature_matrix', 'features', 'linkage', 'silhouette', 'branch', 'pca_features', 'explained']:
            assert current[key] == baseline[key], (feature, ngram, fold, key)
        assert [(s['id'], s['text']) for s in current['samples']] == [(s['id'], s['text']) for s in baseline['samples']]
        assert [(p['x'], p['y']) for p in current['projection']] == [(p['x'], p['y']) for p in baseline['projection']]
        for sample in current['samples']:
            if sample['era'] == 'Quran':
                assert 'display_text' in sample
                assert analysis.quran_comparison_text(sample['display_text']) == sample['text']
        assert all('display_text' not in leaf for leaf in current['leaves'])
        assert all('display_text' not in point for point in current['projection'])
        assert not any(w.startswith('Source spelling differs:') for w in current['warnings'])
        print(f'{feature}/{ngram}, fold={fold}: frequencies, tree, PCA and metrics exactly match the old Quran.', flush=True)
print('All seven feature sets preserve the historical numerical results.', flush=True)
