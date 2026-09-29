"""Deterministic, label-blind feature extraction and hierarchical clustering."""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import hashlib
import re
import unicodedata

import numpy as np
from scipy.cluster.hierarchy import linkage, to_tree
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics import silhouette_score
from poetry_examples import poetry_display

ROOT = Path(__file__).resolve().parents[1]
ERA_DIR = ROOT / 'Quran+ Poems by Era '
ERAS = ['Quran', 'PreIslamic', 'Mukhadramun', 'Islamic', 'Umayyad', 'Abbasid', 'Andalusian', 'Fatimid', 'Ayyubid', 'Mamluk', 'Ottoman', 'Modern']
NAMES = ['Quran', 'Pre-Islamic', 'Transitional poets', 'Early Islamic', 'Umayyad', 'Abbasid', 'Andalusian', 'Fatimid', 'Ayyubid', 'Mamluk', 'Ottoman', 'Modern']
FEATURES = {
    'words': ('Most frequent words (MFW)', 'Relative frequencies of the most frequent Arabic word tokens.'),
    'chargrams': ('Character n-grams', 'Choose 1–7 characters or all lengths together. Punctuation is removed; ordinary spaces preserve word boundaries. Unigrams contain letters only.'),
    'wordgrams': ('Word n-grams', 'Choose sequences of 1–5 words or all lengths together, after removing punctuation and normalizing Arabic text.'),
    'characters': ('Individual letters', 'Relative Arabic letter frequencies; spaces are excluded.'),
    'function': ('Function words', 'A fixed, transparent list of standalone particles, pronouns and prepositions. Attached clitics are not segmented.'),
    'length': ('Word lengths', 'Distribution of token lengths, with words of 15 or more letters grouped together.'),
}
FUNCTION_WORDS = 'في من علي الى الي عن ان إن أن إذا اذا ما لا لم لن قد لقد هل بل ثم او أو و ف ب ك ل حتى حتي كل بعض هو هي هم هن نحن انا أنا انت أنت هذا هذه ذلك تلك الذي التي الذين كان كانت ليس علي على به بها له لها بهم لهم فيه فيها بين عند مع بعد قبل إذ اذ'.split()
ARABIC = re.compile(r'[\u0621-\u063a\u0641-\u064a\u066e-\u066f\u0671-\u06d3]+')
DIACRITICS = re.compile(r'[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]')
QURAN_LEGACY_FOLD = str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ة': 'ه', 'ئ': 'ي', 'ؤ': 'و'})


def normalize(text, fold=True):
    text = DIACRITICS.sub('', unicodedata.normalize('NFKC', text))
    text = ''.join(ch if ch.isspace() or unicodedata.category(ch).startswith('L') else ' ' for ch in text)
    if fold:
        text = text.translate(str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي'}))
    return ' '.join(ARABIC.findall(text))


def corpus_tokens(path):
    # Preserve source/license notices in downloaded corpora, but never sample
    # their comment lines as Quranic text or count them as corpus words.
    return ' '.join(line for line in path.read_text(encoding='utf-8-sig').splitlines()
                    if not line.lstrip().startswith('#')).split()


def quran_comparison_text(text):
    """Reproduce the audited historical spelling without altering the source.

    All replacements are one character for one character, preserving offsets
    between the unvocalized display text and the analytical representation.
    """
    return text.translate(QURAN_LEGACY_FOLD)


@lru_cache(maxsize=1)
def catalog():
    entries = []
    for era, name in zip(ERAS, NAMES):
        path = ERA_DIR / f'{era}.txt'
        words = len(corpus_tokens(path))
        entries.append({'id': era, 'name': name, 'words': words, 'file': path.name})
    return entries


def validate(config):
    if not isinstance(config, dict):
        raise ValueError('Experiment settings must be an object.')
    c = dict(eras=['Quran', 'PreIslamic', 'Modern'], feature='words', ngram=1, top=100, words=7000, samples=10, seed=42, fold=True, distance='delta', linkage='average', view='samples', target='Quran')
    allowed_keys = set(c) | {'dataset'}
    if set(config) - allowed_keys:
        raise ValueError('Unknown experiment setting.')
    c.update({k: v for k, v in config.items() if k in c})
    if 'dataset' in config and config['dataset'] != 'eras':
        raise ValueError('Invalid dataset.')
    for key, choices in {'feature': FEATURES, 'distance': ['delta', 'cosine', 'euclidean'], 'linkage': ['average', 'complete', 'single', 'ward'], 'view': ['samples', 'centroids'], 'target': ERAS}.items():
        if not isinstance(c[key], str) or c[key] not in choices:
            raise ValueError(f'Invalid {key}.')
    for key, low, high in [('ngram', 0, 7 if c['feature'] == 'chargrams' else 5), ('top', 20, 1000), ('words', 500, 7000), ('samples', 2, 10), ('seed', 0, 999999)]:
        if type(c[key]) is not int or not low <= c[key] <= high:
            raise ValueError(f'{key} must be an integer between {low} and {high}.')
    if type(c['fold']) is not bool:
        raise ValueError('Normalization must be true or false.')
    if not isinstance(c['eras'], list) or not all(isinstance(e, str) and e in ERAS for e in c['eras']) or len(set(c['eras'])) != len(c['eras']) or len(c['eras']) < 2:
        raise ValueError('Choose at least two distinct corpus groups.')
    if c['linkage'] == 'ward' and c['distance'] != 'euclidean':
        raise ValueError('Ward linkage requires Euclidean distance.')
    c['eras'] = [e for e in ERAS if e in c['eras']]
    if c['target'] not in c['eras']:
        c['target'] = c['eras'][0]
    return c


def documents(c):
    docs, warnings = [], []
    for era in c['eras']:
        path = ERA_DIR / f'{era}.txt'
        tokens = corpus_tokens(path)
        available = len(tokens) // c['words']
        if available == 0:
            raise ValueError(f'{era} has no complete chunks at this size. Reduce words per sample.')
        count = min(available, c['samples'])
        if count < c['samples']:
            warnings.append(f'{era}: only {count} complete non-overlapping chunks available; requested {c["samples"]}.')
        if count == 1:
            warnings.append(f'{era}: one sample cannot establish within-group cohesion; its silhouette contribution is zero.')
        # Independent stream per era keeps its sample selection stable when other eras change.
        rng = np.random.default_rng(np.random.SeedSequence([c['seed'], ERAS.index(era)]))
        indices = sorted(rng.choice(available, count, replace=False).tolist())
        for index in indices:
            sample_tokens = tokens[index*c['words']:(index+1)*c['words']]
            raw = ' '.join(sample_tokens)
            display = normalize(raw, False) if era == 'Quran' else None
            text = quran_comparison_text(display) if era == 'Quran' else normalize(raw, c['fold'])
            doc = dict(id=f'{era}-{index}', label=f'{dict(zip(ERAS, NAMES))[era]} · {index+1:02}', era=era, text=text, raw_text=raw, source=str(path.relative_to(ROOT)), chunk=index, raw_words=c['words'], sha256=hashlib.sha256(raw.encode()).hexdigest(), analysis_sha256=hashlib.sha256(text.encode()).hexdigest())
            if display is not None:
                doc['display_text'] = display
            else:
                doc.update(poetry_display(era, sample_tokens, text, index*c['words'], normalize))
            docs.append(doc)
    if any(not d['text'] for d in docs):
        raise ValueError('A selected sample contains no Arabic tokens.')
    return docs, warnings


def feature_matrix(docs, c):
    counters = []
    ngram_lengths = range(1, 8 if c['feature'] == 'chargrams' else 6) if c['ngram'] == 0 else [c['ngram']]
    for doc in docs:
        text = normalize(doc['text'], c['fold'])
        words = text.split()
        if c['feature'] in ('chargrams', 'wordgrams'):
            counts = Counter()
            for n in ngram_lengths:
                if c['feature'] == 'wordgrams':
                    counts.update(' '.join(words[i:i+n]) for i in range(len(words)-n+1))
                else:
                    counts.update(text[i:i+n] for i in range(len(text)-n+1) if text[i:i+n].strip())
        elif c['feature'] == 'characters':
            counts = Counter(text.replace(' ', ''))
        elif c['feature'] == 'length':
            counts = Counter(str(min(len(w), 15)) for w in words)
        else:
            counts = Counter(words)
        counters.append(counts)
    totals = Counter()
    for counts in counters:
        totals.update(counts)
    if c['feature'] == 'function':
        names = sorted(set(normalize(w, c['fold']) for w in FUNCTION_WORDS))
    elif c['feature'] == 'length':
        names = [str(i) for i in range(1, 16)]
    elif c['feature'] == 'characters':
        names = sorted(totals)
    else:
        ranked = sorted(totals, key=lambda name: (-totals[name], name))
        if c['feature'] in ('chargrams', 'wordgrams') and c['ngram'] == 0:
            # Retain a vocabulary for every length; short grams must not crowd out longer ones.
            size = (lambda name: len(name.split())) if c['feature'] == 'wordgrams' else len
            names = [name for n in ngram_lengths for name in [v for v in ranked if size(v) == n][:c['top']]]
        else:
            names = ranked[:c['top']]
    # Denominator is ALL feature events, not only the retained vocabulary.
    denominators = [max(sum(counts.values()), 1) for counts in counters]
    x = np.array([[counts[name] / denominator for name in names] for counts, denominator in zip(counters, denominators)])
    keep = x.std(axis=0, ddof=1) > 1e-12
    return x[:, keep], [name for name, valid in zip(names, keep) if valid]


def run_experiment(config):
    c = validate(config)
    docs, warnings = documents(c)
    x, names = feature_matrix(docs, c)
    if x.shape[1] < 2:
        raise ValueError('Fewer than two varying features. Choose a different feature set or corpus.')
    empty_count = int(np.count_nonzero(np.linalg.norm(x, axis=1) == 0))
    if empty_count:
        if c['distance'] == 'cosine':
            raise ValueError('Cosine distance is undefined for samples with no selected features. Increase vocabulary size, choose shorter n-grams, or choose Delta/Euclidean distance.')
        warnings.append(f'{empty_count} samples contain none of the retained features. Their zero frequency rows are included; increase top features or choose shorter n-grams for broader coverage.')
    z = (x - x.mean(axis=0)) / x.std(axis=0, ddof=1)
    transformed = z if c['distance'] == 'delta' else x
    metric = {'delta': 'cityblock', 'cosine': 'cosine', 'euclidean': 'euclidean'}[c['distance']]
    sample_dist = pdist(transformed, metric=metric)
    if c['distance'] == 'delta':
        sample_dist /= len(names)
    labels = [d['era'] for d in docs]
    comparison_labels = [label == c['target'] for label in labels]
    silhouette = float(silhouette_score(squareform(sample_dist), comparison_labels, metric='precomputed')) if 1 < len(set(comparison_labels)) < len(docs) else None
    leaves = [{k: v for k, v in d.items() if k not in ('text', 'raw_text') and not k.startswith('display_')} for d in docs]
    tree_x = transformed
    if c['view'] == 'centroids':
        tree_x = np.array([transformed[np.array(labels) == era].mean(axis=0) for era in c['eras']])
        leaves = [dict(id=e, label=dict(zip(ERAS, NAMES))[e], era=e) for e in c['eras']]
        warnings.append('Each tree leaf is an era centroid. A single leaf cannot establish within-era cohesion; switch to sample leaves to test a separate branch.')
    dist = pdist(tree_x, metric=metric)
    if c['distance'] == 'delta':
        dist /= len(names)
    if not np.isfinite(dist).all():
        raise ValueError('Distance is undefined for these features; choose a different feature set.')
    link = linkage(dist, method=c['linkage'])
    tree = to_tree(link)
    target_ids = {i for i, leaf in enumerate(leaves) if leaf['era'] == c['target']}
    nodes = {}
    def pack(node):
        ids = {node.id} if node.is_leaf() else nodes_for(node)
        nodes[node.id] = ids
        if node.is_leaf():
            return dict(id=node.id, distance=0, leaf=leaves[node.id])
        return dict(id=node.id, distance=float(node.dist), children=[pack(node.left), pack(node.right)])
    def nodes_for(node):
        return set(node.pre_order(lambda leaf: leaf.id))
    packed = pack(tree)
    lca_id, members = min(((node, ids) for node, ids in nodes.items() if target_ids <= ids), key=lambda pair: len(pair[1])) if target_ids else (None, set())
    purity = len(target_ids) / len(members) if members else None
    target_mask = np.array(labels) == c['target']
    features = []
    if target_mask.any() and (~target_mask).any():
        effects = z[target_mask].mean(axis=0) - z[~target_mask].mean(axis=0)
        # Keep the selected vocabulary's pooled-frequency order and full size.
        order = range(len(names))
        features = [dict(name=names[i], effect=float(effects[i]), focus=float(x[target_mask, i].mean()*10000), other=float(x[~target_mask, i].mean()*10000)) for i in order]
    centered = tree_x - tree_x.mean(axis=0)
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    coords = u[:, :2] * s[:2]
    explained = (s[:2]**2 / max(float(np.sum(s**2)), 1e-20)).tolist()
    # Feature vectors in the same PC basis as the samples, with one uniform display scale.
    loadings = vt[:2].T * s[:2] / np.sqrt(max(len(leaves)-1, 1))
    strengths = np.linalg.norm(loadings, axis=1)
    strongest = np.argsort(-strengths, kind='stable')[:20]
    strongest = [i for i in strongest if strengths[i] > 1e-12]
    feature_scale = .75 * float(np.max(np.linalg.norm(coords, axis=1))) / max(float(strengths.max()), 1e-20)
    pca_features = [dict(name=names[i], x=float(loadings[i, 0]*feature_scale), y=float(loadings[i, 1]*feature_scale), loading_x=float(loadings[i, 0]), loading_y=float(loadings[i, 1])) for i in strongest]
    warnings.extend(['Clustering measures textual similarity. Genre, topic, spelling and corpus selection can influence group separation.', 'Feature contrasts describe this selected corpus; they are not causal explanations or significance tests. Silhouette compares the focus group with the remaining selected groups pooled together on sample distances, not inferred clusters.'])
    return dict(config=c, sample_count=len(docs), feature_count=len(names), leaves=leaves, tree=packed, linkage=link.tolist(), silhouette=silhouette, branch=dict(purity=purity, target_count=len(target_ids), total_count=len(members), separate=purity == 1 and len(target_ids) > 1, node=lca_id, testable=c['view']=='samples' and len(target_ids)>1), features=features, feature_names=names, feature_matrix=x.tolist(), samples=[dict(id=d.get('id', ''), label=d.get('label', ''), era=d.get('era', ''), source=d.get('source', ''), chunk=d.get('chunk', 0), raw_words=d.get('raw_words', 0), sha256=d.get('sha256', ''), text=d.get('text', ''), raw_text=d.get('raw_text', d.get('text', '')), analysis_sha256=d.get('analysis_sha256', ''), **{k: v for k, v in d.items() if k.startswith('display_')}) for d in docs], projection=[dict(**leaf, x=float(coords[i,0]), y=float(coords[i,1])) for i,leaf in enumerate(leaves)], pca_features=pca_features, pca_feature_scale=feature_scale, explained=explained, warnings=warnings, text_preparation=dict(quran_comparison='historical spelling: أ/إ/آ/ٱ→ا, ى/ئ→ي, ؤ→و, ة→ه', quran_examples='corrected Simple Clean source spelling; character offsets match analysis text', poetry_comparison='unchanged historical TXT corpus', poetry_examples='source spelling from unambiguous full-poem CSV matches only; display_spans limit quotations to covered passages; no guessing for unmatched text', poetry_example_source='Arabic_Poetry_Dataset.csv', source_sha256_field='sha256', analysis_sha256_field='analysis_sha256'), normalization='Quran comparison uses historical spelling (أ/إ/آ/ٱ→ا, ى/ئ→ي, ؤ→و, ة→ه); corrected Quran spelling is used only for examples and source provenance. Poetry analysis retains its supplied historical spelling; poetry examples use source spelling from matching CSV poems only, excluding unmatched or ambiguous passages. NFKC; remove punctuation, symbols, digits, diacritics, Quranic marks and tatweel; Arabic letter tokens; '+('fold alef variants and alif maqsura' if c['fold'] else 'no additional alef/maqsura folding; historical corpus spelling is retained'), method='Classic Delta = mean absolute difference of sample-standardized relative feature frequencies (sample SD, ddof=1).' if c['distance']=='delta' else f'{c["distance"].title()} distance on relative feature frequencies.')
