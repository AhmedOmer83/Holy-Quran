"""Build reproducible display-only matches from the supplied poetry CSV.

Run locally from website: ../../.venv/bin/python build_poetry_display.py
Historical TXT files and CSV period assignments are never changed.
"""
from collections import defaultdict
from bisect import bisect_left
import csv
import gzip
import hashlib
import json

from analysis import ROOT, ERA_DIR, ERAS, corpus_tokens, normalize, quran_comparison_text
from poetry_examples import DISPLAY_DIR


def matched_passages(tokens, anchors):
    normalized = [normalize(token, False) for token in tokens]
    text = ' '.join(token for token in normalized if token)
    starts, ends, position = [], [], 0
    for token in normalized:
        starts.append(position)
        ends.append(position + len(token))
        if token:
            position += len(token) + 1
    found = {}
    for start in range(len(text) - 23):
        if start and text[start-1] != ' ':
            continue
        for key, display, row in anchors.get(text[start:start+24], ()):
            end = start + len(key)
            if not text.startswith(key, start) or (end < len(text) and text[end] != ' '):
                continue
            a, b = bisect_left(starts, start), bisect_left(ends, end)
            if a == len(starts) or b == len(ends) or starts[a] != start or ends[b] != end:
                continue
            # Avoid changing word segmentation or sampling boundaries.
            if len(display.split()) != b + 1 - a:
                continue
            identity = (start, end, display)
            if identity not in found:
                found[identity] = dict(start_word=a, end_word=b+1, text=display, csv_rows=[])
            found[identity]['csv_rows'].append(row)
    matches = sorted(found.items(), key=lambda item: (item[0][0], -item[0][1], item[0][2]))
    # Competing source spellings are ambiguous: exclude every conflicting
    # passage, rather than silently choosing one CSV row as authoritative.
    active, ambiguous = [], set()
    for i, ((start, end, display), _) in enumerate(matches):
        active = [j for j in active if matches[j][0][1] > start]
        for j in active:
            other_start, other_end, other = matches[j][0]
            overlap_end = min(end, other_end)
            if display[:overlap_end-start] != other[start-other_start:overlap_end-other_start]:
                ambiguous.update((i, j))
        active.append(i)
    passages, last_end = [], -1
    for i, ((start, end, _), passage) in enumerate(matches):
        if i not in ambiguous and start >= last_end:
            passages.append(passage)
            last_end = end
    return passages, len(ambiguous)


def attach_poets(passages, row_poets):
    for passage in passages:
        passage['poets'] = sorted({row_poets[row] for row in passage['csv_rows'] if row_poets[row]})


def main():
    source = ROOT / 'Arabic_Poetry_Dataset.csv'
    anchors = defaultdict(list)
    row_poets = {}
    with source.open(encoding='utf-8-sig', newline='') as stream:
        for row, poem in enumerate(csv.DictReader(stream), 2):
            row_poets[row] = ' '.join(poem['poet_name'].split())
            display = normalize(poem['poem_text'], False)
            key = quran_comparison_text(display)
            if len(key.replace(' ', '')) >= 24:
                anchors[key[:24]].append((key, display, row))
    DISPLAY_DIR.mkdir(exist_ok=True)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    report = {}
    for era in ERAS:
        if era in ('Quran', 'Islamic'):
            continue
        path = ERA_DIR / f'{era}.txt'
        tokens = corpus_tokens(path)
        passages, ambiguous = matched_passages(tokens, anchors)
        attach_poets(passages, row_poets)
        index = dict(version=2, analysis_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                     display_source_sha256=source_hash, passages=passages)
        payload = json.dumps(index, ensure_ascii=False, separators=(',', ':')).encode()
        (DISPLAY_DIR / f'{era}.json.gz').write_bytes(gzip.compress(payload, mtime=0))
        covered = sum(p['end_word']-p['start_word'] for p in passages)
        report[era] = dict(source_words=len(tokens), matched_words=covered,
                           coverage_percent=round(100*covered/len(tokens), 2),
                           passages=len(passages), ambiguous_passages_excluded=ambiguous)
        print(era, report[era], flush=True)
    (DISPLAY_DIR / 'coverage.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
