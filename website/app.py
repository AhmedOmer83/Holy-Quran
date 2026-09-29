import json
import os
from threading import Lock
from functools import lru_cache
from flask import Flask, abort, jsonify, request, send_file, send_from_directory
from analysis import ROOT, ERA_DIR, ERAS, FEATURES, catalog, run_experiment, validate
from poetry_examples import reference_example
from text_metadata import text_metadata

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024
# Keep Arabic as UTF-8 instead of expanding each letter to a six-byte escape.
app.json.ensure_ascii = False
MAX_BUFFERED_JSON_BYTES = 32 * 1024 * 1024
analysis_lock = Lock()

@lru_cache(maxsize=24)
def cached_run(payload):
    return run_experiment(json.loads(payload))

@app.get('/')
def index():
    return app.send_static_file('index.html')

@app.get('/media/explainer.mp4')
def explainer_video():
    response = send_file(ROOT / 'القرآن الكريم وتحدي الشعراء ، خوارزمية التجميع الهرمي.mp4', mimetype='video/mp4', conditional=True)
    # Cloud Run rejects non-chunked HTTP/1 responses larger than 32 MiB.
    # Let Gunicorn stream large bodies with chunked transfer encoding while
    # retaining Content-Range for browser playback and seeking.
    if request.method != 'HEAD' and (response.content_length or 0) >= 32 * 1024 * 1024:
        response.headers.pop('Content-Length', None)
    return response

@app.get('/downloads/texts/<filename>')
def download_corpus_text(filename):
    if filename not in {f'{era}.txt' for era in ERAS if era != 'Islamic'}:
        abort(404)
    return send_from_directory(ERA_DIR, filename, as_attachment=True, mimetype='text/plain; charset=utf-8')

@app.get('/api/catalog')
def corpus_catalog():
    return jsonify(eras=catalog(), features=[dict(id=k, name=v[0], description=v[1]) for k,v in FEATURES.items()])

@app.get('/api/text-metadata')
def corpus_text_metadata():
    return jsonify(records=text_metadata())

@app.post('/api/experiment')
def experiment():
    try:
        payload = request.get_json()
        with analysis_lock:
            result = cached_run(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        response = jsonify(result)
        if response.content_length >= MAX_BUFFERED_JSON_BYTES:
            # Gunicorn must use chunked transfer for responses above Cloud Run's
            # buffered-response limit. Preserve the complete experiment/export.
            body = response.get_data()
            response.response = (body[start:start + 65536] for start in range(0, len(body), 65536))
            response.headers.pop('Content-Length', None)
            response.automatically_set_content_length = False
        return response
    except (ValueError, TypeError) as error:
        return jsonify(error=str(error)), 400


@app.post('/api/reference-example')
def corpus_reference_example():
    try:
        payload = request.get_json()
        if not isinstance(payload, dict):
            raise ValueError('Invalid example request.')
        config = validate(payload.get('config'))
        era, feature = payload.get('era'), payload.get('feature')
        if era not in config['eras'] or era in ('Quran', 'Islamic'):
            raise ValueError('Choose a poetry group included in the experiment.')
        if not isinstance(feature, str) or not feature or len(feature) > 200:
            raise ValueError('Invalid example feature.')
        return jsonify(example=reference_example(era, feature, config))
    except (ValueError, TypeError) as error:
        return jsonify(error=str(error)), 400

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8000')), debug=False)
