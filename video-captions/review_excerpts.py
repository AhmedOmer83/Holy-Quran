"""Independent short-clip recognition of uncertain phrases and the ending."""
import json
import wave
from dataclasses import asdict
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

here = Path(__file__).resolve().parent
with wave.open('/tmp/quran-explainer-audio.wav') as file:
    audio = np.frombuffer(file.readframes(file.getnframes()), dtype=np.int16).astype(np.float32) / 32768
model = WhisperModel('large-v3', device='cpu', compute_type='int8', cpu_threads=8,
                     local_files_only=True)
review = []
for start, end in [(582, 597), (915.3, 929), (929, 942.5), (942.5, 954.4)]:
    segments, _ = model.transcribe(
        audio[round(start*16000):round(end*16000)], language='ar', task='transcribe',
        beam_size=5, word_timestamps=True, condition_on_previous_text=False,
        initial_prompt='شرح القرآن الكريم والشعر، الكلمات والحروف، نموذج الكلمات. '
                       'وما علمناه الشعر وما ينبغي له إن هو إلا ذكر وقرآن مبين. '
                       'وما هو بقول شاعر قليلا ما تؤمنون. أم يقولون شاعر نتربص به ريب المنون.',
    )
    for segment in segments:
        data = asdict(segment)
        data['start'] += start
        data['end'] += start
        for word in data['words']:
            word['start'] += start
            word['end'] += start
        review.append(data)
        print(f'{data["start"]:.2f}–{data["end"]:.2f} {data["text"]}', flush=True)
    (here/'review-excerpts.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
