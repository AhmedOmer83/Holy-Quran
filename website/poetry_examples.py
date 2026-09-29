"""Source-matched poetry spelling for display, independent of analytical text."""
from bisect import bisect_left
from functools import lru_cache
from pathlib import Path
import gzip
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DISPLAY_DIR = ROOT / 'poetry-display'


@lru_cache(maxsize=12)
def source_index(era):
    path = DISPLAY_DIR / f'{era}.json.gz'
    if not path.exists():
        return None
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        index = json.load(stream)
    source = ROOT / 'Quran+ Poems by Era ' / f'{era}.txt'
    if hashlib.sha256(source.read_bytes()).hexdigest() != index['analysis_source_sha256']:
        raise ValueError(f'{era}: poetry example index is out of date. Rebuild the display sources.')
    index['ends'] = [p['end_word'] for p in index['passages']]
    return index


def poetry_display(era, tokens, text, start_word, normalize):
    """Overlay verified source passages; only covered ranges may be quoted.

    Word positions refer to the unchanged whitespace-token sampling corpus.
    The builder accepts only one-to-one spelling changes, so analytical and
    display character offsets remain identical, with either fold setting.
    """
    index = source_index(era)
    result = dict(display_text=text, display_spans=[], display_source='Arabic_Poetry_Dataset.csv')
    if index is None:
        return result
    result['display_source_sha256'] = index['display_source_sha256']
    normalized = [normalize(token, False) for token in tokens]
    offsets, position = [], 0
    for token in normalized:
        offsets.append(position)
        if token:
            position += len(token) + 1
    pieces = list(text)
    stop_word = start_word + len(tokens)
    first = bisect_left(index['ends'], start_word + 1)
    for passage in index['passages'][first:]:
        if passage['start_word'] >= stop_word:
            break
        begin = max(start_word, passage['start_word'])
        end = min(stop_word, passage['end_word'])
        words = passage['text'].split()
        corrected = ' '.join(words[begin-passage['start_word']:end-passage['start_word']])
        left = offsets[begin-start_word]
        right = left + len(corrected)
        if len(normalize(' '.join(tokens[begin-start_word:end-start_word]), False)) != len(corrected):
            raise ValueError(f'{era}: poetry example alignment has changed. Rebuild the display sources.')
        pieces[left:right] = corrected
        result['display_spans'].append(dict(start=left, end=right, csv_rows=passage['csv_rows'], poets=passage.get('poets', [])))
    result['display_text'] = ''.join(pieces)
    return result


def reference_example(era, feature, config):
    """Find an optional illustration outside the experiment's sampled chunks.

    This reads the verified display index only; it never supplies analysis
    documents, changes sampling, or contributes to feature frequencies.
    """
    from analysis import ERAS, catalog, normalize, quran_comparison_text
    import numpy as np

    index = source_index(era)
    if index is None:
        return None
    words = config['words']
    total = next(entry['words'] for entry in catalog() if entry['id'] == era)
    available = total // words
    rng = np.random.default_rng(np.random.SeedSequence([config['seed'], ERAS.index(era)]))
    selected = set(rng.choice(available, min(available, config['samples']), replace=False).tolist())
    kind = config['feature']
    whole_words = kind in ('words', 'wordgrams', 'function')
    pattern = re.compile((r'(?<!\S)' if whole_words else '') + re.escape(feature) + (r'(?!\S)' if whole_words else ''))
    for passage in index['passages']:
        # Exclude even partially sampled poems so the scope label stays exact.
        chunks = range(passage['start_word']//words, (passage['end_word']-1)//words+1)
        if selected.intersection(chunks):
            continue
        display = passage['text']
        text = normalize(quran_comparison_text(display), config['fold'])
        if kind == 'length':
            match = next((m for m in re.finditer(r'\S+', text) if str(min(len(m[0]), 15)) == feature), None)
        else:
            match = pattern.search(text)
        if match is None:
            continue
        start, end = match.span()
        left = display.rfind(' ', 0, start-70+1)+1 if start > 70 else 0
        right = display.find(' ', end+70)
        if right == -1:
            right = len(display)
        return dict(era=era, scope='outside_analysis_samples',
                    before=('… ' if left else '') + display[left:start], match=display[start:end],
                    after=display[end:right] + (' …' if right < len(display) else ''),
                    analysis_match=text[start:end], poets=passage.get('poets', []),
                    source='Arabic_Poetry_Dataset.csv', source_sha256=index['display_source_sha256'],
                    corpus_source=f'Quran+ Poems by Era /{era}.txt',
                    corpus_sha256=index['analysis_source_sha256'], csv_rows=passage['csv_rows'],
                    start_word=passage['start_word'], end_word=passage['end_word'])
    return None
