"""Replace the first pass's incomplete ending with short-clip recognition."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
path = here / 'transcript.ar.jsonl'
raw = here / 'transcript.ar.raw.jsonl'
if not raw.exists():
    raw.write_bytes(path.read_bytes())
segments = [json.loads(line) for line in raw.read_text().splitlines()]
review = [s for s in json.loads((here / 'review-excerpts.json').read_text()) if s['start'] >= 915.3]
assert review and review[-1]['end'] > 950
segments = [s for s in segments if s['end'] < 915.3]
for segment in review:
    segment['id'] = len(segments) + 1
    segment['start'] = round(segment['start'], 3)
    segment['end'] = round(segment['end'], 3)
    for word in segment['words']:
        word['start'] = round(word['start'], 3)
        word['end'] = round(word['end'], 3)
    segments.append(segment)
path.write_text(''.join(json.dumps(s, ensure_ascii=False) + '\n' for s in segments), encoding='utf-8')
print(f'Applied short-clip ending review: {len(segments)} segments.')
