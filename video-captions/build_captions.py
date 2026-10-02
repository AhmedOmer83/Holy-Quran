"""Build browser/download subtitles and a readable English-captioned movie.

Uses only the standard library and FFmpeg, after the translations are authored.
Run with --render to also produce website/media/explainer.en.mp4.
"""
import argparse
import hashlib
import json
import re
import subprocess
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT / 'القرآن الكريم وتحدي الشعراء ، خوارزمية التجميع الهرمي.mp4'
DEST = ROOT / 'website/static/captions'


def timestamp(seconds, separator='.'):
    total = round(seconds * 1000)
    hours, rest = divmod(total, 3600000)
    minutes, rest = divmod(rest, 60000)
    secs, millis = divmod(rest, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02}{separator}{millis:03}'


def ass_timestamp(seconds):
    total = round(seconds * 100)
    hours, rest = divmod(total, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, centis = divmod(rest, 100)
    return f'{hours}:{minutes:02}:{secs:02}.{centis:02}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args()
    transcript = [json.loads(line) for line in (HERE / 'transcript.ar.jsonl').read_text().splitlines()]
    source_cues = json.loads((HERE / 'source-cues.ar.json').read_text())
    translations = json.loads((HERE / 'translations.en.json').read_text())
    assert set(translations) == {cue['id'] for cue in source_cues}, 'Every source cue needs a translation.'
    assert {cue['segment_id'] for cue in source_cues} == {segment['id'] for segment in transcript}
    duration = float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(SOURCE),
    ], text=True).strip())
    cues = []
    for source in source_cues:
        parts = translations[source['id']]
        if isinstance(parts, str):
            parts = [dict(start=source['start'], end=source['end'], text=parts)]
        for part in parts:
            text = part['text'].strip()
            assert text and not re.search(r'[\u0600-\u06ff<>]', text), text
            start, end = part['start'], part['end']
            assert source['start'] - .15 <= start < end <= source['end'] + .15, part
            assert end <= duration and end - start <= 10, part
            lines = textwrap.wrap(text, width=52, break_long_words=False, break_on_hyphens=False)
            assert len(lines) <= 2, f'Split this caption: {text}'
            assert len(text) / (end - start) <= 32, f'Caption is too fast: {part}'
            if cues:
                assert start >= cues[-1]['end'] - .01, f'Overlapping captions: {part}'
            cues.append(dict(source_id=source['id'], start=start, end=end, text='\n'.join(lines)))
    DEST.mkdir(parents=True, exist_ok=True)
    blocks = ['WEBVTT\n']
    srt = []
    for number, cue in enumerate(cues, 1):
        blocks.append(f'{number}\n{timestamp(cue["start"])} --> {timestamp(cue["end"])}\n{cue["text"]}\n')
        srt.append(f'{number}\n{timestamp(cue["start"], ",")} --> {timestamp(cue["end"], ",")}\n{cue["text"]}\n')
    (DEST / 'explainer.en.vtt').write_text('\n'.join(blocks), encoding='utf-8')
    (DEST / 'explainer.en.srt').write_text('\n'.join(srt), encoding='utf-8')
    (HERE / 'captions.en.json').write_text(json.dumps(cues, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Put the captions in an added band below the original image, so they never
    # cover the slides, software demonstration, or speaker's face.
    ass = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 832
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: English,DejaVu Sans,32,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,40,40,18,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    for cue in cues:
        text = cue['text'].replace('\n', r'\N')
        assert not any(char in text for char in '{}'), text
        ass += f'Dialogue: 0,{ass_timestamp(cue["start"])},{ass_timestamp(cue["end"])},English,,0,0,0,,{text}\n'
    (HERE / 'explainer.en.ass').write_text(ass, encoding='utf-8')
    (HERE / 'caption-info.json').write_text(json.dumps(dict(
        source_video=SOURCE.name, source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        duration_seconds=duration, source_segments=len(transcript), english_cues=len(cues),
        source_language='ar', caption_language='en',
        translation='English translation edited from the local Arabic speech transcript.',
        audio='Original Arabic audio retained.',
    ), indent=2) + '\n', encoding='utf-8')
    print(f'Built {len(cues)} English cues across {duration:.2f} seconds.', flush=True)
    if args.render:
        movie = ROOT / 'website/media/explainer.en.mp4'
        movie.parent.mkdir(parents=True, exist_ok=True)
        # A fixed relative filter path avoids FFmpeg escaping of the Arabic
        # source filename and project directory names.
        subprocess.run([
            'ffmpeg', '-nostdin', '-hide_banner', '-y', '-i', str(SOURCE),
            '-vf', 'pad=iw:ih+112:0:0:black,ass=explainer.en.ass',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-threads', '4',
            '-c:a', 'copy', '-movflags', '+faststart',
            '-metadata', 'title=Quran methodology — English captions',
            str(movie),
        ], cwd=HERE, check=True)


if __name__ == '__main__':
    main()
