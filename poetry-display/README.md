# Poetry spelling for examples

These generated indices supply display text only. Analytical sampling, corpus
membership, feature counts, clustering, and PCA still use the historical TXT
files in `../Quran+ Poems by Era `.

The source is the supplied `../Arabic_Poetry_Dataset.csv`, SHA-256
`9deaa44c278fbdc06c87801f578dceeac5fe5542c5a8892110bef739c7c97ed1`.
The CSV is a partial matching source, not a complete corrected edition of the
historical corpus. Its period assignments are not used to reassign poems.

Each indexed passage is a complete poem of at least 24 Arabic letters that
matches a historical passage after normalization and the audited one-to-one
letter substitutions. Word boundaries must agree. Display preserves source
spelling without diacritics. Overlapping sources with conflicting spellings
are excluded; duplicate identical records retain their CSV record numbers.
Record 1 is the header, irrespective of embedded newlines in CSV fields. Each passage also retains all distinct poet names from its matching records; conflicting attributions are displayed explicitly rather than choosing an author arbitrarily. Names travel with each sampled display span and are included in JSON exports.

The application clips examples to the matched poem and selected sample. It
omits unmatched passages instead of guessing spelling. `coverage.json` records
coverage by whitespace-delimited source words; coverage is especially limited
for Abbasid (2.42%) and Modern (4.17%). This does not remove words from analysis.

Each compressed index records the SHA-256 of its historical TXT and source CSV.
The application rejects an index whose historical file hash has changed.
Rebuild locally from `../website`:

```bash
../../.venv/bin/python build_poetry_display.py
```

Restart the local application after rebuilding, because indices and completed
experiments are cached. The generated indices can be bundled with the app
without including the full CSV. No server deployment is performed by the builder.
