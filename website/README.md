# Stylometry Tool — Quran & Poetry

A local website for comparing Quranic text with Arabic poetry through linguistic features, clustering, and PCA. Results are calculated from the selected Arabic corpora; the interface reports the observed separation for each experiment.

## Run locally

From this `website` directory (Python 3.12 or later):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open **http://127.0.0.1:8000**. Stop with Ctrl+C. To change the port: `PORT=8001 .venv/bin/python app.py`.

In the existing project environment you can also run, from `Holy_Quran`:

```bash
.venv/bin/python 'Holy Quran Exp/website/app.py'
```

No Node build, external fonts, CDN, API keys or internet connection is required after installing dependencies. The server binds to localhost only. Corpus files are read in place and never modified. Restart after editing corpus files because completed experiments and the catalog are cached in memory.

## Deploy to Google Cloud Run

Live website: https://stylometry-tool-871346202659.europe-west2.run.app

The production container uses Gunicorn and includes the corpus files, poet metadata, and explainer video.

API JSON uses UTF-8 for Arabic text to keep large corpus selections compact. Experiment responses of 32 MiB or more use chunked transfer, so Cloud Run can deliver complete results and exports when all periods are selected.

Run from the parent `Holy Quran Exp` directory:

```bash
gcloud run deploy stylometry-tool \
  --source=. \
  --project=stylometry-509416 \
  --region=europe-west2 \
  --allow-unauthenticated \
  --service-account=stylometry-runtime@stylometry-509416.iam.gserviceaccount.com \
  --cpu=1 --memory=2Gi --concurrency=4 --timeout=300 \
  --min-instances=0 --max-instances=3 --port=8080
```

This publishes a public HTTPS website in London with up to three instances and no minimum running instances. Google Cloud usage is billed to the project. The runtime service account has no project roles; the application reads its bundled files. `.gcloudignore` and `.dockerignore` exclude local environments, Git history, test artifacts, and unrelated source documents.

For a local production-server check, install `requirements-production.txt`, then run `gunicorn --config gunicorn.conf.py app:app` from this directory. It listens on port 8080, or the port supplied through `PORT`.

## Included

- A bilingual research-use statement at the end of the page, above the footer, with an APA 7 software reference template and an in-text citation. The author is Ahmed Ibrahim Ahmed Omer. The reference uses `n.d.` and a public-URL placeholder until a release date and public address are supplied; replace these and add a version number when available.


- Bilingual contact details for Dr Ahmed Ibrahim Ahmed Omer, University of York, UK, with both email addresses.

- An Arabic explainer video above the experiment lab, with playback controls and fullscreen support. The local MP4 is served from the project root with byte-range support for seeking. Responses of 32 MiB or more omit Content-Length so Gunicorn uses chunked streaming, avoiding Cloud Run's non-streaming response size limit.

- English and Arabic interfaces, selected from the language menu in the header. Arabic uses a right-to-left layout and translates controls, results, chart labels, methodology, and validation messages. The choice is remembered in the browser. Switching languages preserves the current experiment and does not recalculate it; JSON/CSV identifiers stay stable and SVG labels use the selected language.
- A focus-group-versus-other-selected-groups comparison (Quran versus poetry by default) with editable corpus selection, sample length/count, seed, normalization, feature set, distance and linkage.
- Quran and ten selectable poetry categories (Early Islamic is excluded from the website).
- Seven feature sets: most frequent words (the default), word bigram, character 1 gram, character bigram, character trigram, character 5 grams, and character 7 grams. Selecting a set also fixes its n-gram length.
- Equally prominent HC and PCA method cards, with full names and explanations in English and Arabic, let users switch between the two analyses.
- Vertical hierarchical trees with actual merge distances, a PCA projection with the 20 strongest feature vectors, branch purity, sample-level focus-versus-other-groups silhouette, and feature contrasts.
- Side-by-side comparison of seven feature sets using the last completed experiment's settings.
- **Examples are temporarily hidden** (`FEATURE_EXAMPLES_ENABLED = false` in `static/app.js`). The table shows features, rates, and standardized differences only. The quotation support described below is retained for later use. When enabled, each feature row has a “See examples” button that shows one matching passage per selected corpus group from the current experiment's samples, with the matching feature highlighted and its corpus group and sample number shown. All selected groups have a card. Each card reports the group's mean relative frequency per 10,000 feature events and the number of samples containing the feature, directly from the matrix used for distances. It distinguishes a genuinely zero feature frequency from unavailable corrected quotations; quotation coverage never determines these frequencies. Poetry cards show the poet name from the matched CSV records; multiple source attributions are labeled and all distinct names are retained. Matches use the analytical text and respect whole-word boundaries and spaces in character n-grams. Quran and poetry excerpts use corrected `display_text`, with the same character offsets as the historical analytical text. Poetry quotations are restricted to `display_spans` backed by unambiguous, complete poem matches in the supplied CSV; context is clipped to the matched poem and sample boundaries. Unmatched passages are omitted, so some features may have fewer examples. Feature labels retain the form that was counted; highlights show the corresponding corrected source characters. Examples follow the selected corpus order, search later samples when earlier ones have no match, and retain identical passages when they represent different groups. There is no three-example limit. The grid supports both interface languages. When an era has no source-backed example in its samples, its card offers an explicit “Show a reference example outside the analysis samples” action. This searches corrected passages in the same historical era file, excludes poems overlapping any selected chunk, and labels the result as an illustration outside the experiment. The reference retains its poet, source records and file hashes. It never changes samples, feature counts, charts or experiment exports. References are discarded when experiment settings change.
- Downloadable experiment JSON, relative-frequency feature matrix CSV, and vector SVG figures.

Changing the feature set automatically updates the feature differences, charts, metrics, and exports. Source passages stay fixed across feature sets for a controlled comparison; changing the seed draws a new reproducible sample where enough chunks are available.

## Method and limits

Defaults select Quran, Pre-Islamic poetry, and Modern poetry, with the 100 most frequent words, 7,000 source words per sample, and up to 10 samples per category. The Arabic label for Modern is «الشعر الحديث». Changing controls automatically recomputes results; excluded groups are removed from both charts and exports. The comparison focus is automatic: Quran whenever it is included, otherwise the first selected group in the fixed corpus order. There is no focus selector. Select two groups for a pairwise comparison or more groups to compare the focus with the remaining groups pooled together. Pending older responses are discarded.

Era files are divided into full, non-overlapping whitespace-token chunks; incomplete tails are discarded. A deterministic NumPy random stream per era samples these without replacement. If fewer chunks than requested exist, all available full chunks are used and a warning is shown. A category with one full chunk is retained with a warning: it cannot establish within-group cohesion. Zero complete chunks is an error. The random stream depends on the seed and the era's fixed catalog index.

Normalization uses NFKC, removes punctuation, symbols, digits, Arabic diacritics/Quranic marks/tatweel, keeps Arabic-letter tokens, and optionally folds alef variants and alif maqsura. No stemming, morphological parsing, translation or clitic segmentation is applied.

On 2026-09-27, `Quran.txt` was restored from the unmodified [Tanzil Project Simple Clean 1.1 download](https://tanzil.net/download/), retaining its attribution and license notice. All 6,236 verse lines match the official XML export. Corpus loading excludes `#` comment lines so source notices do not enter word counts or sampled passages. The 78,248 whitespace-delimited source tokens, verse order, and 112 prefixed opening basmalas remain unchanged; this is the count for this file and segmentation convention.

Comparisons now reconstruct the Quran's audited historical spelling (أ/إ/آ/ٱ→ا, ى/ئ→ي, ؤ→و, ة→ه) in memory, matching the prior preparation of the poetry. This source-preparation step always applies to Quran comparison text, independently of the optional additional alef/maqsura normalization checkbox. The corrected `Quran.txt` is unchanged. Its corrected spelling is used for examples and source provenance, never for computing the feature matrix. Quran `display_text` and analytical `text` have identical lengths and matching character offsets because these substitutions are one-to-one. Poetry comparisons still read the unchanged historical TXT files. Poetry examples now use source spelling from `Arabic_Poetry_Dataset.csv` through the generated `../poetry-display/` indices; CSV period labels do not change corpus membership. Only complete poems with identical words and spacing after the historical letter substitutions are accepted. Conflicting source spellings are excluded. Display removes diacritics, as for Quran examples. The CSV does not cover the complete poetry corpus: see `../poetry-display/coverage.json` for coverage by era, especially the limited Abbasid and Modern coverage. No spelling is guessed for unmatched text. With the default seed 42, none of the ten Modern samples overlaps the corrected source coverage (also true at 500 and 1,000 words per sample). This is a source-coverage limitation, not exclusion of Modern from analysis. Cards now distinguish zero corrected coverage from an unavailable example of a particular feature; the optional reference action can still provide a matching corrected passage from elsewhere in Modern.txt.

JSON exports distinguish `raw_text` and its source `sha256`, analytical `text` and its `analysis_sha256`, and `display_text` for Quran and poetry. Poetry samples also include `display_spans` with source poet names and CSV record numbers (header is record 1), plus the source CSV SHA-256. Only those spans are source-backed quotations; uncovered parts of the display buffer retain analytical spelling and must not be presented as corrected examples. The `text_preparation` and `normalization` fields document the policy. Text bodies are excluded from tree leaves and projections to avoid duplicating them. The generated poetry display indices are bundled with the application; the full CSV is needed only to rebuild them with `../../.venv/bin/python build_poetry_display.py` from this directory. Indices verify the historical TXT SHA-256 before use and must be rebuilt after corpus edits. The old Quran file, correction lists, and historical sensitivity study remain in `../quran-audit/`, excluded from deployment. `tests/quran_comparison_check.py` verifies that all seven feature sets reproduce the historical feature matrices, clustering and PCA with both checkbox settings. The historical `quran-audit/audit.py` explicitly simulates the earlier corrected-only scenario; it does not represent the current production comparison policy.

Frequent features are selected from pooled token counts without consulting group labels. Frequencies divide by all feature events, not only the retained vocabulary. Character grams preserve ordinary word-boundary spaces, with no punctuation markers; character unigrams exclude spaces. Word grams contain consecutive normalized words. Constant features are dropped. Sparse longer word grams can leave samples with zero retained frequencies: Delta and Euclidean retain these rows with a coverage warning; cosine requires nonzero rows and reports a corrective error. Classic Delta uses the mean absolute distance between relative-frequency vectors standardized with sample standard deviations (`ddof=1`). Cosine and Euclidean use relative frequencies. Ward is allowed only with Euclidean distance. These distances are calculated directly from the selected frequency matrix.

Branch purity measures the proportion of focus-group samples in the smallest subtree containing all focus-group samples. Purity of 100% with at least two samples indicates an exclusive branch. In centroid view, or when only one focus sample is available, this test is marked unavailable: a single era leaf cannot establish sample cohesion. Silhouette uses two labels, the focus group and the pooled remaining selected groups, on sample distances and remains sample-based in centroid view. PCA uses standardized features for Delta and relative frequencies otherwise; the projection does not preserve all clustering distances. The PCA labels show the 20 strongest feature vectors in the first two components (component weights × component standard deviations), uniformly scaled to fit the sample coordinates. The axes use equal visual scales; label guide lines only avoid overlap. Feature-label proximity to a sample is not a contribution score. Exports include exact feature loadings and the display scale.

Feature contrasts are differences in group means divided by the overall sample standard deviation, displayed for the full retained vocabulary in pooled-frequency order (100 most frequent words by default). They are descriptive associations, not causal contributions or significance tests. Positive values indicate higher focus-group frequency; the comparator pools samples from all other selected groups.

Genre, topic, spelling, sampling and corpus composition can affect the observed differences. Repeated samples from an author or corpus are not independent sources. Results describe the selected texts and settings, without selecting parameters to force separation.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v
```

With the server running, the optional browser check requires `pip install playwright` in the same environment and Google Chrome at `/usr/bin/google-chrome`:

```bash
.venv/bin/python tests/browser_check.py
.venv/bin/python tests/language_check.py
.venv/bin/python tests/response_check.py
.venv/bin/python tests/feature_examples_check.py
.venv/bin/python tests/reference_examples_check.py
.venv/bin/python tests/quran_comparison_check.py
```

Tests cover punctuation removal, every character/word n-gram length and combined sets, frequency denominators, hand-calculated Delta, PCA loading alignment, deterministic non-overlapping samples, category caps, short corpora, excluded groups, validation, centroid interpretation, API routes, checkbox changes during pending requests, exports, and mobile overflow. Browser screenshots and downloaded files go to ignored `test-artifacts/`.

Language checks also cover saved preferences, switching during pending requests, translating completed feature comparisons and errors, Arabic SVG export, and RTL layouts at desktop and mobile widths.
