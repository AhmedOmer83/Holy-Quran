"""Video response regression checks for Cloud Run's 32 MiB limit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app, ROOT


class VideoTests(unittest.TestCase):
    route = '/media/explainer.mp4'
    filename = 'القرآن الكريم وتحدي الشعراء ، خوارزمية التجميع الهرمي.mp4'

    def setUp(self):
        self.client = app.test_client()
        self.video = ROOT / self.filename
        self.size = self.video.stat().st_size

    def test_full_and_open_ended_responses_stream(self):
        for headers, status in [({}, 200), ({'Range': 'bytes=0-'}, 206)]:
            with self.subTest(headers=headers), self.client.get(self.route, headers=headers) as response:
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.mimetype, 'video/mp4')
                self.assertTrue(response.is_streamed)
                if self.size >= 32 * 1024 * 1024:
                    self.assertNotIn('Content-Length', response.headers)
                if status == 206:
                    self.assertEqual(response.headers['Content-Range'], f'bytes 0-{self.size - 1}/{self.size}')
                with self.video.open('rb') as source:
                    first_chunk = next(iter(response.response))
                    self.assertEqual(first_chunk, source.read(len(first_chunk)))

    def test_seeking_returns_requested_bytes(self):
        for requested, start, end in [('bytes=0-1023', 0, 1023), ('bytes=1048576-1049599', 1048576, 1049599), ('bytes=-1024', self.size - 1024, self.size - 1)]:
            with self.subTest(requested=requested), self.client.get(self.route, headers={'Range': requested}) as response:
                self.assertEqual(response.status_code, 206)
                self.assertEqual(response.headers['Content-Range'], f'bytes {start}-{end}/{self.size}')
                self.assertEqual(response.content_length, end - start + 1)
                with self.video.open('rb') as source:
                    source.seek(start)
                    self.assertEqual(response.data, source.read(end - start + 1))

    def test_head_and_cache_validation(self):
        with self.client.head(self.route) as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_length, self.size)
            self.assertEqual(response.data, b'')
            etag = response.headers['ETag']
        with self.client.get(self.route, headers={'If-None-Match': etag}) as response:
            self.assertEqual(response.status_code, 304)
            self.assertEqual(response.data, b'')

    def test_unsatisfiable_range(self):
        with self.client.get(self.route, headers={'Range': f'bytes={self.size}-'}) as response:
            self.assertEqual(response.status_code, 416)


class EnglishVideoTests(VideoTests):
    route = '/media/explainer.en.mp4'
    filename = 'website/media/explainer.en.mp4'


if __name__ == '__main__':
    unittest.main()
