"""Combine poetry sample metadata into one catalogue entry per poet."""
import csv
from functools import lru_cache
from pathlib import Path

METADATA_PATH = Path(__file__).resolve().parents[1] / 'Cross Era Authors Corpus 2000w 2s' / 'metadata.csv'
PERIODS = {
    'الجاهلي': ('PreIslamic', 'Pre-Islamic'),
    'صدر الإسلام': ('Mukhadramun', 'Transitional poets'),
    'الأموي': ('Umayyad', 'Umayyad'),
    'العباسي': ('Abbasid', 'Abbasid'),
    'الأندلسي': ('Andalusian', 'Andalusian'),
}


@lru_cache(maxsize=1)
def text_metadata():
    records = {}
    with METADATA_PATH.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            period_ar = row['era_ar'].replace('_', ' ').strip()
            if period_ar in ('القرآن الكريم',) or row['poet_id'] == 'QURAN':
                continue
            period_id, period_name = PERIODS[period_ar]
            author_id = row['poet_id']
            record = records.setdefault(author_id, {
                'id': author_id,
                'period': period_id,
                'period_name': period_name,
                'period_ar': period_ar,
                'author': row['author_ar'].replace('_', ' ').strip(),
                'author_id': author_id,
                'primary_poem_title': row['primary_poem_title'].strip(),
                'poem_titles': [],
            })
            for title in row['poem_titles'].split('|'):
                title = title.strip()
                if title and title not in record['poem_titles']:
                    record['poem_titles'].append(title)
    return list(records.values())
