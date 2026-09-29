# Metadata extracted from Arabic_Poetry_Dataset.csv

The requested “Arabic_Poetry_Database” was interpreted as the available local file `Arabic_Poetry_Dataset.csv`. These are dataset descriptions, not independently verified historical attributions. No website content was changed.

## Available fields

| Field | Meaning |
|---|---|
| poet_name | Author name as supplied |
| poet_era | Period label as supplied |
| poem_title | Poem title or opening line |
| poem_text | Arabic poem text |
| poem_tags | Comma-separated category, form, metre and rhyme labels |
| poem_count | Reported number of verses (أبيات), not number of poems |

## Coverage

- 75,022 records; 755 distinct author-name strings; 9 supplied period labels.
- 74,009 records contain nonblank poem text.
- 7,725,077 whitespace-separated tokens, before deduplication.
- 819,596 reported verses across 74,010 records with numeric verse counts.
- Excluding `العصر الاسلامي` (the early Islamic category excluded from the website) leaves 74,685 records and 733 distinct author-name strings across eight labels. `المخضرمون` remains included.

| Supplied period | Records | Author names | Tokens | Reported verses |
|---|---:|---:|---:|---:|
| العصر الجاهلي | 2,350 | 236 | 177,807 | 18,870 |
| المخضرمون | 3,290 | 61 | 223,778 | 23,613 |
| العصر الاسلامي | 337 | 22 | 16,686 | 1,712 |
| العصر الاموي | 7,330 | 88 | 550,067 | 56,658 |
| العصر الايوبي | 8,189 | 85 | 1,095,456 | 115,364 |
| العصر العثماني | 7,545 | 44 | 1,004,732 | 106,667 |
| العصر الأندلسي | 6,171 | 42 | 919,247 | 97,196 |
| العصر المملوكي | 13,085 | 39 | 1,308,135 | 136,953 |
| العصر العباسي | 26,725 | 138 | 2,429,169 | 262,563 |

## Authors with the most records

| Author | Supplied period | Records |
|---|---|---:|
| ابن الرومي | العصر العباسي | 2,020 |
| ابن نباته المصري | العصر المملوكي | 1,727 |
| أبو العلاء المعري | العصر العباسي | 1,611 |
| ابن الوردي | العصر المملوكي | 1,233 |
| ابو نواس | العصر العباسي | 1,175 |
| الشريف العقيلي | العصر المملوكي | 983 |
| عبد الغني النابلسي | العصر العثماني | 967 |
| البحتري | العصر العباسي | 932 |
| محيي الدين بن عربي | العصر الايوبي | 922 |
| صفي الدين الحلي | العصر المملوكي | 899 |

## Poem lengths

Whitespace-token count per record: median 38, mean 102.97, maximum 21,413. These statistics include blank texts as zero and do not remove duplicate records.
Reported verse count: median 4, mean 11.07, maximum 2,367. Records without numeric counts are excluded from these statistics.

## Tags

Counts preserve the supplied tags exactly. They are not independently derived from metre scanning or rhyme analysis. Different labels such as full and shortened metres remain separate. “Short poems” is a length label, while “praise” is a theme, so the category tags mix different kinds of information.

### Most common metre tags

| Tag | Occurrences |
|---|---:|
| بحر الطويل | 18,982 |
| بحر الكامل | 9,745 |
| بحر البسيط | 9,435 |
| بحر الوافر | 6,410 |
| بحر الخفيف | 5,259 |
| بحر السريع | 4,389 |
| بحر المتقارب | 3,302 |
| بحر الرجز | 2,580 |
| بحر مجزوء الكامل | 2,332 |
| بحر المنسرح | 2,142 |

### Most common rhyme tags

| Tag | Occurrences |
|---|---:|
| قافية الراء (ر) | 10,551 |
| قافية اللام (ل) | 7,641 |
| قافية الياء (ي) | 7,473 |
| قافية الباء (ب) | 7,005 |
| قافية الميم (م) | 6,777 |
| قافية الدال (د) | 6,499 |
| قافية النون (ن) | 5,532 |
| قافية القاف (ق) | 3,151 |
| قافية العين (ع) | 2,801 |
| قافية الفاء (ف) | 1,989 |

### Most common category tags

| Tag | Occurrences |
|---|---:|
| قصائد قصيره | 27,170 |
| قصائد عامه | 15,526 |
| قصائد مدح | 6,995 |
| قصائد رومنسيه | 6,211 |
| قصائد هجاء | 3,804 |
| قصائد حزينه | 2,739 |
| قصائد عتاب | 2,547 |
| قصائد رثاء | 2,141 |
| قصائد غزل | 1,727 |
| قصائد دينية | 1,437 |

### Form tags

| Tag | Occurrences |
|---|---:|
| عموديه | 74,003 |
| نثريه | 5 |
| التفعيله | 1 |

## Quality checks

- 1,013 records have blank poem text; 2 have blank titles; 32 have blank tags.
- 1,012 reported verse counts are the literal placeholder `NULL`, rather than numbers.
- 133 rows repeat all six source fields exactly (additional copies beyond the first).
- 370 nonblank text records repeat an already occurring exact poem text; 73,639 distinct nonblank text strings remain. This uses exact original text, without spelling or diacritic normalization.
- 129 distinct nonblank text strings are assigned to more than one author name. This flags attribution for review; it does not determine which attribution is correct.
- 1,030 numeric-count records do not have exactly two nonempty text lines per reported verse. Formatting conventions can explain this, so it is not automatically a counting error.
- All exact author-name strings occur in one supplied period each. Spelling variants and aliases have not been reconciled into historical identities.
- Period labels disagree with the website corpus in some cases, as documented in `../poetry-source-comparison.md`. There are no Fatimid or Modern period labels in this CSV.

## What can be reported

- Corpus size and coverage by period, author, metre, rhyme and category.
- Author representation, length distributions and imbalance between groups.
- Missing text, repeated records and shared text attributions.
- Period-by-metre, author-by-theme and other cross-tabulations from `poems.csv`.
- Further text-derived measures such as vocabulary size and word frequencies, with an explicit Arabic normalization method. These are possible follow-up analyses, not measurements included in this report.

The six source fields do not provide birth/death dates, poem composition dates, geographic origin, source URLs, editions, manuscript references or confidence ratings. Those cannot be reliably reported from this file alone.

## Files

- `poems.csv`: one row per source record, excluding full poem text; includes author, period, title, length, metre, rhyme and tags.
- `periods.csv`: period totals.
- `authors.csv`: author-period totals, ordered by record count.
- `tags.csv`: frequencies of all supplied tags.
- `summary.json`: structured statistics and selected attribution examples.
- `extract.py`: reproduces the CSV and JSON extractions using Python’s standard library.

`csv_record` is the parsed source record position, with the header counted as record 1; it is not a physical line number because poem texts contain line breaks. CSV exports use UTF-8 with a BOM for spreadsheet compatibility.
