"""Split the word-timed Arabic transcript into short translation intervals."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
cues = []
for line in (here / 'transcript.ar.jsonl').read_text().splitlines():
    segment = json.loads(line)
    words = segment['words']
    group = []
    number = 0

    def emit():
        global number, group
        if not group:
            return
        number += 1
        cues.append(dict(id=f'{segment["id"]}.{number}', segment_id=segment['id'],
                         start=group[0]['start'], end=group[-1]['end'],
                         text=' '.join(w['word'].strip() for w in group)))
        group = []

    for word in words:
        if group and (word['end'] - group[0]['start'] > 5.8 or
                      len(' '.join(w['word'] for w in group)) + len(word['word']) > 78):
            emit()
        group.append(word)
        if word['word'].endswith(('.', '،', '؟', '!')) and group[-1]['end'] - group[0]['start'] >= 1.4:
            emit()
    emit()
    if len(cues) >= 2 and cues[-1]['segment_id'] == cues[-2]['segment_id']:
        tail = cues[-1]
        if tail['end'] - tail['start'] < 1.4 and tail['end'] - cues[-2]['start'] <= 8:
            cues[-2]['end'] = tail['end']
            cues[-2]['text'] += ' ' + tail['text']
            cues.pop()
(here / 'source-cues.ar.json').write_text(json.dumps(cues, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for cue in cues:
    print(f'{cue["id"]} {cue["start"]:.2f}–{cue["end"]:.2f} {cue["text"]}')
