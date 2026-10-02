"""Ensure the deployed subtitle track is complete and has usable cue timings."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app


def seconds(value):
    hours, minutes, secs = value.split(':')
    return int(hours) * 3600 + int(minutes) * 60 + float(secs)


class CaptionTests(unittest.TestCase):
    def test_browser_track_is_complete_and_readable(self):
        with app.test_client().get('/static/captions/explainer.en.vtt') as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/vtt')
            text = response.get_data(as_text=True)
        self.assertTrue(text.startswith('WEBVTT\n\n'))
        cues = []
        for block in text.split('\n\n')[1:]:
            if not block.strip():
                continue
            lines = block.strip().splitlines()
            self.assertIn(len(lines), (3, 4))
            match = re.fullmatch(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> '
                                 r'(\d{2}:\d{2}:\d{2}\.\d{3})', lines[1])
            self.assertIsNotNone(match)
            cues.append((lines[0], *match.groups(), '\n'.join(lines[2:])))
        self.assertGreater(len(cues), 100)
        self.assertEqual([int(c[0]) for c in cues], list(range(1, len(cues) + 1)))
        self.assertLess(seconds(cues[0][1]), 2)
        self.assertGreater(seconds(cues[-1][2]), 940)
        previous = 0
        for _, start, end, caption in cues:
            start, end = seconds(start), seconds(end)
            self.assertGreaterEqual(start, previous)
            self.assertGreater(end, start)
            self.assertLessEqual(end, 954.5)
            self.assertLessEqual(end - start, 10)
            self.assertLessEqual(len(caption.replace('\n', ' ')) / (end - start), 32)
            self.assertLessEqual(len(caption.splitlines()), 2)
            self.assertTrue(all(len(line) <= 52 for line in caption.splitlines()))
            self.assertIsNone(re.search(r'[\u0600-\u06ff]', caption))
            previous = end

    def test_download_subtitles_match_the_browser_track(self):
        client = app.test_client()
        with client.get('/static/captions/explainer.en.vtt') as response:
            vtt = response.get_data(as_text=True)
        with client.get('/static/captions/explainer.en.srt') as response:
            self.assertEqual(response.status_code, 200)
            srt = response.get_data(as_text=True)
        converted = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', vtt.removeprefix('WEBVTT\n\n'))
        self.assertEqual(srt, converted)


if __name__ == '__main__':
    unittest.main()
