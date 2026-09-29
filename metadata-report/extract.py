import csv, collections, hashlib, json, re, statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'Arabic_Poetry_Dataset.csv'; out=root/'metadata-report'
periods=collections.defaultdict(lambda: {'poems':0,'authors':set(),'words':0,'verses':0})
authors=collections.defaultdict(lambda: {'poems':0,'words':0,'verses':0})
tags=collections.Counter(); meters=collections.Counter(); rhymes=collections.Counter(); forms=collections.Counter(); topics=collections.Counter()
missing=collections.Counter(); exact=collections.Counter(); texts=collections.defaultdict(list); author_periods=collections.defaultdict(set)
word_counts=[]; verse_counts=[]; line_counts=[]; verse_parse_failures=[]; mismatch=[]; records=[]
with source.open(encoding='utf-8-sig',newline='') as f:
 reader=csv.DictReader(f); fields=reader.fieldnames
 for row_number,r in enumerate(reader,2):
  for k,v in r.items():
   if not v.strip(): missing[k]+=1
  period=r['poet_era'].strip(); author=r['poet_name'].strip(); title=r['poem_title'].strip()
  words=len(r['poem_text'].split()); lines=sum(bool(s.strip()) for s in r['poem_text'].splitlines())
  match=re.search(r'\d+',r['poem_count']); verses=int(match[0]) if match else None
  if verses is None: verse_parse_failures.append(row_number)
  word_counts.append(words);line_counts.append(lines)
  if verses is not None:verse_counts.append(verses)
  if verses is not None and lines!=2*verses:mismatch.append(row_number)
  entry=periods[period];entry['poems']+=1;entry['authors'].add(author);entry['words']+=words;entry['verses']+=verses or 0
  entry=authors[(period,author)];entry['poems']+=1;entry['words']+=words;entry['verses']+=verses or 0
  author_periods[author].add(period)
  rt=[x.strip() for x in r['poem_tags'].split(',') if x.strip()]
  tags.update(rt)
  meters.update(x for x in rt if x.startswith('بحر '))
  rhymes.update(x for x in rt if 'قافية' in x)
  forms.update(x for x in rt if x in ('عموديه','تفعيله','نثريه','عمودية','تفعيلة','نثرية','التفعيله'))
  topics.update(x for x in rt if x.startswith('قصائد '))
  exact[tuple(r.values())]+=1
  digest=hashlib.sha256(r['poem_text'].encode()).hexdigest()
  if r['poem_text'].strip():
   texts[digest].append((row_number,author,period,title))
  records.append({'csv_record':row_number,'period':period,'author':author,'title':title,'words':words,'reported_verses':verses,'nonempty_lines':lines,'meters':' | '.join(x for x in rt if x.startswith('بحر ')),'rhyme_tags':' | '.join(x for x in rt if 'قافية' in x),'tags':' | '.join(rt)})
def stats(values):
 return {'total':sum(values),'min':min(values),'median':statistics.median(values),'mean':round(statistics.mean(values),2),'max':max(values)}
def write_csv(filename,rows):
 with (out/filename).open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
period_rows=[dict(period=k,poems=v['poems'],authors=len(v['authors']),words=v['words'],reported_verses=v['verses']) for k,v in periods.items()]
author_rows=[dict(period=p,author=a,poems=v['poems'],words=v['words'],reported_verses=v['verses']) for (p,a),v in sorted(authors.items(),key=lambda item:-item[1]['poems'])]
cross_author=[items for items in texts.values() if len({item[1] for item in items})>1]
summary={'source':source.name,'fields':fields,'rows':len(records),'unique_author_names':len(author_periods),'author_period_pairs':len(authors),'periods':period_rows,'missing':{k:missing[k] for k in fields},'word_counts':stats(word_counts),'reported_verse_counts':stats(verse_counts),'nonempty_line_counts':stats(line_counts),'verse_count_parse_failures':verse_parse_failures,'rows_not_two_lines_per_reported_verse':len(mismatch),'exact_duplicate_rows_beyond_first':sum(n-1 for n in exact.values()),'unique_nonempty_exact_poem_texts':len(texts),'repeated_nonempty_exact_text_rows_beyond_first':sum(len(v)-1 for v in texts.values()),'nonempty_exact_texts_attributed_to_multiple_authors':len(cross_author),'cross_author_examples':cross_author[:5],'authors_in_multiple_periods':{k:sorted(v) for k,v in author_periods.items() if len(v)>1},'top_authors':author_rows[:15],'meter_tags':meters.most_common(),'rhyme_tags':rhymes.most_common(),'form_tags':forms.most_common(),'topic_tags':topics.most_common(),'all_tags':tags.most_common(),'longest_by_words':sorted(records,key=lambda r:-r['words'])[:5],'longest_by_reported_verses':sorted(records,key=lambda r:-(r['reported_verses'] or 0))[:5]}
write_csv('poems.csv',records);write_csv('periods.csv',period_rows);write_csv('authors.csv',author_rows);write_csv('tags.csv',[{'tag':k,'occurrences':v} for k,v in tags.most_common()])
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print('Extracted',len(records),'records into',out)
