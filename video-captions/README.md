# English captions for the methodology video

The full Arabic speech is translated into English. The website plays the original
Arabic recording with a selectable English WebVTT subtitle track. English captions
are shown initially in both the English and Arabic interfaces; the
player's CC menu lets viewers change this. Switching the interface language does
not reset playback.

The download at `../website/media/explainer.en.mp4` has the same Arabic audio and
English captions permanently rendered in an extra 112-pixel black band below the
original image. The original slides and speaker remain fully visible. This is a
captioned translation, with no English dubbing.

## Sources and editing

- `transcript.ar.jsonl`: word-timed Arabic transcript used for the translation.
- `transcript.ar.raw.jsonl`: unmodified initial speech recognition output.
- `review-excerpts.json`: independent short-clip recognition of an unclear
  technical phrase and the ending. The ending contains speech the batched first
  pass omitted; `apply_review.py` replaces that portion with the short-clip results.
- `transcription-info.json`: model and timing information.
- `source-cues.ar.json`: short Arabic intervals prepared from those word timings.
- `translations.en.json`: English translations matched to each Arabic interval.
  An entry can instead be a list of explicitly timed parts when it needs splitting.
- `captions.en.json`: final English timings and wrapped text.
- `caption-info.json`: original video's SHA-256 and caption counts.
- `explainer.en.ass`: rendering instructions for the downloadable movie.
- `../website/static/captions/explainer.en.vtt`: browser subtitle track.
- `../website/static/captions/explainer.en.srt`: subtitles for media players.

Transcription uses the locally cached `Systran/faster-whisper-large-v3` model,
Arabic language, CPU int8, word timestamps, voice-activity detection and beam size 5.
English wording is edited from the Arabic transcript; technical terms and visible
labels are checked against the slides. Recognition mistakes such as العصابة for
Moses's العصا, and obvious misspellings of names and periods, are corrected in the
English translation. The raw machine transcript is retained for comparison.
Quran quotations are translated as spoken; chapter names attributed by the speaker
are retained.
Speech recognition may still miss words; the translation is editable by cue ID.
The video's claims and historical experiment settings are preserved as spoken.

## Rebuild

Caption generation uses Python's standard library; movie rendering also needs
FFmpeg with libass and libx264, and the DejaVu Sans font. No transcription tools or
models are needed to run the website.

```bash
python3 video-captions/prepare_source_cues.py
python3 video-captions/build_captions.py --render
```

These commands run from `Holy Quran Exp`. The build validates completeness,
ordering, non-overlap, video duration, English text, two-line wrapping, and reading
speed before writing subtitles. Rerender after editing the translation.

To transcribe again in a separate environment:

```bash
python3 -m venv /tmp/quran-video-captions-venv
/tmp/quran-video-captions-venv/bin/pip install 'faster-whisper==1.2.1' 'av>=11,<17'
/tmp/quran-video-captions-venv/bin/python video-captions/transcribe.py 'القرآن الكريم وتحدي الشعراء ، خوارزمية التجميع الهرمي.mp4'
```

This requires the cached large-v3 model. To repeat the ending review, first extract
mono 16 kHz audio to `/tmp/quran-explainer-audio.wav`, run `review_excerpts.py` in
the transcription environment, then run `apply_review.py`. See the
[faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper).

## Browser verification

With the project running at http://127.0.0.1:8000:

```bash
../.venv/bin/python website/tests/video_captions_check.py
```

The check decodes the actual WebVTT in Chrome, seeks to captions at the beginning,
middle and end, checks English/Arabic preferences and downloads, and saves a player
screenshot in `website/test-artifacts/english-video-captions.png`.
