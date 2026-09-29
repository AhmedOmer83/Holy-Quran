# Arabic poetry source comparison

Checked: 22 September 2026.

## Conclusion

`Arabic_Poetry_Dataset.csv` contains substantial overlap with the website’s poetry TXT files, but it cannot be confirmed as the complete source of those files. Its period assignments also disagree with the existing corpus. The website catalogue was therefore left unchanged, as the requested replacement was conditional on confirming the source.

## Evidence

- The CSV contains 75,022 poem rows across nine period labels.
- 40,050 CSV rows have their complete normalized poem text present in at least one poetry TXT file. This confirms overlap, not identical datasets or extraction history.
- The CSV has no Fatimid or Modern period label, although some poems assigned to other CSV periods occur in those TXT files.
- The opening of `Modern.txt`, “همت الفلك واحتواها الماء”, was not found anywhere in the normalized CSV poem text.
- “تفت فؤادك الأيام فتا” by أبو إسحاق الإلبيري is present in `Andalusian.txt`, but its CSV period is `العصر المملوكي`.
- The existing website catalogue reads `Cross Era Authors Corpus 2000w 2s/metadata.csv`, a smaller sample collection, rather than this new CSV.
- The CSV calls the excluded early Islamic group `العصر الاسلامي` (337 rows). This is distinct from `المخضرمون` (3,290 rows), which is a website category. Any future import must keep that distinction and exclude صدر الإسلام.

## Text comparison

Full CSV poem text was searched in each TXT after NFKC normalization, removal of non-Arabic letters (including whitespace and diacritics), and folding أ/إ/آ/ٱ→ا, ى→ي, ة→ه, ؤ→و, ئ→ي. Matches are contiguous whole-poem normalized strings of at least 24 letters; overlapping matches contribute to coverage only once.

These percentages are conservative full-poem matching coverage, **not** proof that all unmatched text is missing from the CSV. Editorial changes, spelling variants and truncated poems can prevent a match. Short common poems and duplicate entries can match multiple files.

| TXT file | Matching CSV rows | Letters covered by full-poem matches |
|---|---:|---:|
| Abbasid.txt | 2,842 | 2.90% |
| Andalusian.txt | 4,628 | 73.18% |
| Ayyubid.txt | 5,587 | 82.50% |
| Fatimid.txt | 6,765 | 80.01% |
| Mamluk.txt | 6,128 | 62.78% |
| Modern.txt | 384 | 4.23% |
| Mukhadramun.txt | 3,170 | 80.91% |
| Ottoman.txt | 3,973 | 73.59% |
| PreIslamic.txt | 1,861 | 76.95% |
| Umayyad.txt | 5,756 | 88.53% |

The separate audit JSON also includes `Islamic.txt` for source comparison only; it is not being added to the website.

## Reproduction

Run `python3 website/test-artifacts/check_poetry_source.py` from this directory. Detailed matched CSV line numbers (header is line 1) and period cross-counts are in `website/test-artifacts/poetry-source-comparison.json`. CSV row numbers refer to parsed records, not physical lines inside multiline fields.

Source CSV SHA-256: `9deaa44c278fbdc06c87801f578dceeac5fe5542c5a8892110bef739c7c97ed1`.
