# Cross Era Authors Corpus 2000w 2s
For each author, the script counts full 2000-word chunks in the source text and keeps only authors with at least 2 such chunks.
The two samples are then selected by evenly spacing chunk indices across the full text rather than just taking the first two chunks.
In practice, this usually means one sample from the beginning of the author file and one from near the end.
For example, a poet with 2 full chunks gets chunk indices `0` and `1`, a poet with 9 full chunks gets `0` and `8`, and a poet with 36 full chunks gets `0` and `35`.
Each sample is sliced by word position using `start = chunk_idx * 2000` and `end = start + 2000`.

## Size

- Historical author classes: `45`
- Quran class: `1`
- Total classes: `46`
- Samples per historical class: `2`
- Samples for Quran class: `10`
- Documents per copy: `100`
- Words per document: `2000`
- Total words per copy: `200,000`

## Selected Authors

### الجاهلي
- `الأعشى`: `19,238` words
- `عنترة_بن_شداد`: `16,199` words
- `لبيد_بن_ربيعة_العامري`: `10,044` words
- `بشرُ_بنُ_أَبي_خازِم`: `7,347` words
- `النابغة_الذبياني`: `6,755` words
- `امرؤ_القيس`: `5,846` words
- `أبو_طالب`: `5,575` words
- `أوس_بن_حجر`: `5,081` words
- `زهير_بن_أبي_سلمى`: `4,437` words
- `المهلهل_بن_ربيعة_-_الزير`: `4,100` words

### صدر_الإسلام
- `حسان_بن_ثابت`: `18,559` words
- `الحطيئة`: `9,380` words
- `علي_بن_أبي_طالب`: `8,169` words
- `الخنساء`: `8,153` words
- `كعب_بن_زهير`: `6,123` words

### الأموي
- `الفرزدق`: `73,728` words
- `جرير`: `51,963` words
- `عمر_ابن_أبي_ربيعة`: `36,708` words
- `ذو_الرمة`: `26,500` words
- `الأخطل`: `21,573` words
- `كثير_عزة`: `17,615` words
- `الراعي_النميري`: `13,252` words
- `الطرماح`: `12,332` words
- `ابن_مقبل`: `12,301` words
- `النابغة_الشيباني`: `10,853` words

### العباسي
- `ابن_الرومي`: `272,895` words
- `مهيار_الديلمي`: `207,843` words
- `البحتري`: `152,255` words
- `الشريف_الرضي`: `145,839` words
- `الشريف_المرتضى`: `124,058` words
- `أبوالعلاء_المعري`: `103,076` words
- `محيي_الدين_بن_عربي`: `89,051` words
- `ابن_حيوس`: `68,396` words
- `أبو_تمام`: `66,145` words
- `بشار_بن_برد`: `66,125` words

### الأندلسي
- `ابن_نباتة_المصري`: `136,419` words
- `عبد_الغفار_الأخرس`: `107,188` words
- `صفي_الدين_الحلي`: `80,935` words
- `حيدر_بن_سليمان_الحلي`: `72,283` words
- `ابن_دارج_القسطلي`: `58,320` words
- `عبد_الجبار_بن_حمديس`: `57,415` words
- `لسان_الدين_الخطيب`: `46,153` words
- `ابن_شهاب`: `41,275` words
- `الهبل`: `34,541` words
- `ابن_هانئ_الأندلسي`: `34,232` words
