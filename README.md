# Holy Quran — Stylometry Tool

Compare Quranic text and Arabic poetry across historical periods using word
frequencies, hierarchical clustering, and principal component analysis.

Live website: https://stylometry-tool-871346202659.europe-west2.run.app

## Run locally

With Python 3.12 or later, from this repository:

```bash
python3 -m venv website/.venv
website/.venv/bin/python -m pip install -r website/requirements.txt
website/.venv/bin/python website/app.py
```

Open http://127.0.0.1:8000. See [the website documentation](website/README.md)
for analysis methods, tests, and Cloud Run deployment instructions.

## Project data

The repository includes the Quran and poetry corpora, source metadata, generated
poetry display indices, Quran source audit, and the explainer video required by
the website. The Quran source attribution is retained in its text file and
[audit notice](quran-audit/NOTICE.txt).

The large original `Arabic_Poetry_Dataset.csv` and local research documents are
not included. The website runs without them. To regenerate the poetry display
indices or source metadata reports, supply the original CSV at the repository
root; see [the display index documentation](poetry-display/README.md).
