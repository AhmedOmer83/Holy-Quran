"""Create an Arabic source transcript locally; not required by the website.

Install faster-whisper in a separate environment, then run this script with
the source video (or a mono 16 kHz WAV) as its argument.
"""
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from faster_whisper import BatchedInferencePipeline, WhisperModel

output = Path(__file__).resolve().parent
started = time.monotonic()
model = WhisperModel('large-v3', device='cpu', compute_type='int8', cpu_threads=8,
                     local_files_only=True)
pipeline = BatchedInferencePipeline(model=model)
segments, info = pipeline.transcribe(
    sys.argv[1], language='ar', task='transcribe', beam_size=5, batch_size=4,
    word_timestamps=True, vad_filter=True,
    initial_prompt='شرح مقارنة أسلوب القرآن الكريم بالشعر العربي عبر العصور باستخدام '
                   'خوارزمية التجميع الهرمي، ستايلومتري، تكرار الكلمات والحروف، '
                   'العصر الجاهلي والأموي والعباسي والحديث، دلتا، بايثون، آر.',
)
with (output / 'transcript.ar.jsonl').open('w', encoding='utf-8') as file:
    for segment in segments:
        file.write(json.dumps(asdict(segment), ensure_ascii=False) + '\n')
        file.flush()
        print(f'{segment.id}: {segment.start:.2f}–{segment.end:.2f} {segment.text}', flush=True)
(output / 'transcription-info.json').write_text(json.dumps({
    'model': 'Systran/faster-whisper-large-v3',
    'language': info.language, 'task': 'transcribe', 'compute_type': 'int8',
    'duration': info.duration, 'duration_after_vad': info.duration_after_vad,
    'elapsed_seconds': round(time.monotonic() - started, 2),
}, indent=2), encoding='utf-8')
print('Transcription complete.', flush=True)
