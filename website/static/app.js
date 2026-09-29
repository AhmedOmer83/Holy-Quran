'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const colors = ['#286052','#b47c42','#80799e','#799260','#548a9d','#ba6861','#918256','#789b91','#b38fa3','#7386b0','#9e916f','#bf946e'];
let catalog, result, busy = false, activeChart = 'tree';
let revision = 0, pendingRun = false, runTimer;
const names = {}, palette = {};
const defaultEras = ['Quran','PreIslamic','Modern'];
const featureSets = [
  {id:'words',name:'Most frequent words',feature:'words',ngram:1,description:'Relative frequencies of the most frequent Arabic words.'},
  {id:'word2',name:'Word bigram',feature:'wordgrams',ngram:2,description:'Relative frequencies of sequences of two consecutive Arabic words.'},
  {id:'char1',name:'Character 1 gram',feature:'chargrams',ngram:1,description:'Relative frequencies of individual Arabic letters. Spaces are excluded.'},
  {id:'char2',name:'Character bigram',feature:'chargrams',ngram:2,description:'Relative frequencies of overlapping two-character sequences, preserving ordinary word-boundary spaces.'},
  {id:'char3',name:'Character trigram',feature:'chargrams',ngram:3,description:'Relative frequencies of overlapping three-character sequences, preserving ordinary word-boundary spaces.'},
  {id:'char5',name:'Character 5 grams',feature:'chargrams',ngram:5,description:'Relative frequencies of overlapping five-character sequences, preserving ordinary word-boundary spaces.'},
  {id:'char7',name:'Character 7 grams',feature:'chargrams',ngram:7,description:'Relative frequencies of overlapping seven-character sequences, preserving ordinary word-boundary spaces.'},
];
// Keep quotation support available while the interface shows features only.
const FEATURE_EXAMPLES_ENABLED = false;
const fields = ['feature','top','words','samples','seed','distance','linkage','view'];
const messages = new Map();
let comparisonResults = [];
let expandedFeature = null;
const referenceExamples = new Map();
function groupName(id) { return t(names[id] || id); }
function sampleLabel(sample) {
  return `${groupName(sample.era)}${sample.chunk===undefined?'':` · ${String(sample.chunk+1).padStart(2,'0')}`}`;
}
function distanceName(value) { return t({delta:'Classic Delta',cosine:'Cosine',euclidean:'Euclidean'}[value] || value); }
function linkageName(value) { return t({average:'Average',complete:'Complete',single:'Single',ward:'Ward'}[value] || value); }
function setMessage(id, key, params = {}) {
  messages.set(id,{key,params});
  const translatedParams=Object.fromEntries(Object.entries(params).map(([k,v])=>[k,typeof v==='string'?t(v):v]));
  $(id).textContent=translateMessage(t(key,translatedParams));
}
function translateMessage(message) {
  if(language!=='ar')return message;
  if(Object.hasOwn(arabic,message))return t(message);
  let m;
  if((m=message.match(/^(.+): only (\d+) complete non-overlapping chunks available; requested (\d+)\.$/)))return `${groupName(m[1])}: يتوفر ${m[2]} مقطع كامل غير متداخل فقط؛ العدد المطلوب ${m[3]}.`;
  if((m=message.match(/^(.+): one sample cannot establish within-group cohesion; its silhouette contribution is zero\.$/)))return `${groupName(m[1])}: لا تكفي عينة واحدة لإثبات التماسك داخل المجموعة؛ مساهمتها في معامل سيلويت تساوي صفرًا.`;
  if((m=message.match(/^(.+) has no complete chunks at this size\. Reduce words per sample\.$/)))return `${groupName(m[1])}: لا تتوفر مقاطع كاملة بهذا الطول. قلّل عدد الكلمات لكل عينة.`;
  if((m=message.match(/^(\d+) samples contain none of the retained features\./)))return `${m[1]} عينة لا تتضمن أيًا من السمات المختارة. تُدرج صفوف تكراراتها الصفرية في التحليل؛ زِد عدد السمات أو اختر تتابعات أقصر لتوسيع التغطية.`;
  if((m=message.match(/^(\w+) must be an integer between (\d+) and (\d+)\.$/)))return `${settingName(m[1])}: يجب إدخال عدد صحيح بين ${m[2]} و${m[3]}.`;
  if((m=message.match(/^Invalid (\w+)\.$/)))return `قيمة غير صالحة: ${settingName(m[1])}.`;
  return message;
}
function settingName(key) {
  return t({eras:'Include corpus groups',feature:'Feature Set',ngram:'N-gram length',top:'Top features',words:'Words / sample',samples:'Max samples / category',seed:'Random seed',fold:'Normalize alef variants & ى',distance:'Distance',linkage:'Linkage',view:'Tree leaves',target:'Focus group'}[key]||key);
}
function setLanguage(next) {
  language=next==='ar'?'ar':'en';
  try { localStorage.setItem('arabic-stylometry-language',language); } catch (_) {}
  applyStaticLanguage();
  for(const [id,{key,params}] of messages)setMessage(id,key,params);
  if(!catalog)return;
  document.querySelectorAll('[data-era-name]').forEach(el=>el.textContent=groupName(el.dataset.eraName));
  document.querySelectorAll('[name=era]').forEach(el=>{
    const era=catalog.eras.find(e=>e.id===el.value);
    el.closest('label').title=`${era.words.toLocaleString()} ${language==='ar'?'كلمة':'words'} · ${era.file}`;
  });
  [...$('feature').options].forEach(option=>option.textContent=t(featureSets.find(f=>f.id===option.value).name));
  $('feature-help').textContent=t(featureSets.find(f=>f.id===$('feature').value).description);
  $('compare').textContent=t('Compare {count} sets',{count:featureSets.length});
  if(result) {
    render();
  } else {
    $('tree-chart').innerHTML=`<div class="empty">${t($('error').hidden?'Updating the selected texts…':'Adjust the settings to display results.')}</div>`;
  }
  renderComparison();
  setBusy(busy);
}
function config() {
  const c = Object.fromEntries(fields.map(key => [key, $(key).type === 'checkbox' ? $(key).checked : $(key).value]));
  c.fold = true;
  ['top','words','samples','seed'].forEach(k => c[k] = Number(c[k]));
  const selected=featureSets.find(f=>f.id===c.feature);
  c.feature=selected.feature;
  c.ngram=selected.ngram;
  c.eras = [...document.querySelectorAll('[name=era]:checked')].map(e => e.value);
  c.target = c.eras.includes('Quran') ? 'Quran' : c.eras[0];
  return c;
}
function controlsChanged() {
  revision++;
  setMessage('sampling-help', 'Up to 10 seeded, non-overlapping samples per category. Shorter corpora supply fewer samples; incomplete tails are excluded.');
  $('feature-help').textContent = t(featureSets.find(f => f.id === $('feature').value).description);
  const ward = $('linkage').querySelector('[value=ward]');
  ward.disabled = $('distance').value !== 'euclidean';
  if(ward.disabled && $('linkage').value === 'ward')$('linkage').value='average';
  result = null;
  referenceExamples.clear();
  expandedFeature = null;
  comparisonResults = [];
  ['download','svg-export','csv-export','compare'].forEach(k=>$(k).disabled=true);
  ['legend','feature-rows','comparison','methodology','pca-chart','sampling-note'].forEach(k=>$(k).replaceChildren());
  $('tree-chart').innerHTML=`<div class="empty">${t('Updating the selected texts…')}</div>`;
  $('metrics').replaceChildren();
  setMessage('finding', 'Results will reflect the selected corpus groups.');
  setMessage('result-title', 'Updating the experiment…');
  setMessage('result-caption', 'EXPERIMENT RESULTS');
  $('error').hidden=true;
  setMessage('status', 'Settings changed. Updating results…');
  clearTimeout(runTimer);
  runTimer=setTimeout(run,250);
}
function resetExperiment() {
  if(busy)return;
  const c = {feature:'words',top:100,words:7000,samples:10,seed:42,distance:'delta',linkage:'average',view:'samples'};
  fields.forEach(k => $(k).type==='checkbox'?$(k).checked=c[k]:$(k).value=c[k]);
  document.querySelectorAll('[name=era]').forEach(e=>e.checked=defaultEras.includes(e.value));
  controlsChanged();
  run();
}
async function requestExperiment(c) {
  const response = await fetch('/api/experiment', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)});
  let body;
  try {
    body = await response.json();
  } catch (_) {
    throw new Error(t('The server could not return complete results ({status}). Please try again.',{status:response.status}));
  }
  if(!response.ok)throw new Error(body.error || t('Experiment failed ({status}).',{status:response.status}));
  return body;
}
function setBusy(value) {
  busy=value;
  $('results').setAttribute('aria-busy',String(value));
  ['run','reset'].forEach(k=>$(k).disabled=value);
  $('compare').disabled=value||!result;
  $('run').innerHTML=value?t('Computing…'):`${t('Run experiment')} <span>${language==='ar'?'←':'→'}</span>`;
}
async function run() {
  clearTimeout(runTimer);
  if(busy){pendingRun=true;return;}
  pendingRun=false;
  if(document.querySelectorAll('[name=era]:checked').length<2) {
    setMessage('error', 'Choose at least two distinct corpus groups.');
    $('error').hidden=false;
    $('tree-chart').innerHTML=`<div class="empty">${t('Select at least two groups to display results.')}</div>`;
    setMessage('status', 'Choose at least two groups to run the experiment.');
    return;
  }
  if(!$('experiment-form').checkValidity()) {
    setMessage('error', 'Check the settings: sample count must be 2–10 and top features 20–1,000.');
    $('error').hidden=false;
    setMessage('status', 'Adjust the settings to run the experiment.');
    return;
  }
  const requestedRevision=revision;
  setBusy(true); $('error').hidden=true;
  setMessage('status', 'Extracting features and computing HC and PCA…');
  try {
    const next = await requestExperiment(config());
    if(requestedRevision!==revision)return;
    result = next;
    referenceExamples.clear();
    expandedFeature = null;
    render();
    comparisonResults=[];
    $('comparison').replaceChildren();
    setMessage('status', 'Experiment complete. Results reflect the settings recorded below.');
  } catch(error) {
    if(requestedRevision!==revision)return;
    setMessage('error',error.message); $('error').hidden=false;
    $('tree-chart').innerHTML=`<div class="empty">${t('Adjust the settings to display results.')}</div>`;
    setMessage('status', 'Run failed. Adjust the settings and try again.');
  } finally {setBusy(false);if(pendingRun||requestedRevision!==revision)run();}
}
function arabicMethods(r,focus,other) {
  const c=r.config;
  const settings=Object.fromEntries(Object.entries(c).map(([key,value])=>{
    if(key==='eras')value=value.map(groupName);
    else if(key==='target')value=groupName(value);
    else if(key==='feature')value=t(featureSets.find(f=>f.feature===c.feature&&f.ngram===c.ngram)?.name||value);
    else if(key==='distance')value=distanceName(value);
    else if(key==='linkage')value=linkageName(value);
    else if(key==='view')value=t(value==='samples'?'Text samples':'Era centroids');
    else if(key==='fold')value=value?'مفعّل':'معطّل';
    return [settingName(key),value];
  }));
  return `<p><b>المسافة.</b> ${c.distance==='delta'?'دلتا الكلاسيكية هي متوسط الفروق المطلقة بين التكرارات النسبية المعيارية، باستخدام الانحراف المعياري للعينة (درجات الحرية = 1).':`تُحسب مسافة ${distanceName(c.distance)} من التكرارات النسبية للسمات.`} طريقة الربط: ${linkageName(c.linkage)}. تُختار السمات من مجموع التكرارات دون استخدام تسميات المجموعات، وتُستبعد السمات الثابتة.</p>
  <p><b>توحيد النص.</b> توحيد يونيكود بصيغة NFKC، وإزالة الترقيم والرموز والأرقام والتشكيل والعلامات القرآنية والتطويل، والاحتفاظ بالكلمات العربية فقط؛ ${c.fold?'تُوحّد صور الألف والألف المقصورة في المعالجة الإضافية':'لا يُطبّق توحيد إضافي للألف والمقصورة'}. يستخدم القرآن تمثيله القديم للمقارنة: أ/إ/آ/ٱ←ا، ى/ئ←ي، ؤ←و، ة←ه، بما يتسق مع الكتابة الموجودة في ملفات الشعر. تُعرض أمثلة القرآن بكتابتها المصححة، وتُعرض أمثلة الشعر بكتابة المصدر المصححة فقط عند مطابقة القصيدة كاملة، وتُستبعد المقاطع غير المطابقة أو التي تختلف مصادرها في الكتابة. لا يعيد إلغاء الخيار الحروف المدمجة إلى نص المقارنة. تُقسَم تكرارات السمات على جميع مرات ظهور السمات، بما فيها ما يقع خارج المفردات المختارة.</p>
  <p><b>فروق السمات.</b> متوسط ${esc(focus)} ناقص متوسط ${esc(other)}، مقسومًا على الانحراف المعياري عبر جميع العينات المختارة. تعني القيم الموجبة تكرارًا أعلى في عينات ${esc(focus)}. ويُوزن الطرف المقارن بحسب عدد العينات.</p>
  <p><b>نقاء الفرع.</b> نسبة أوراق ${esc(focus)} في أصغر شجرة فرعية تحتوي على جميع أوراق هذه المجموعة. تشير نسبة 100% إلى فرع حصري عند وجود عينتين على الأقل.</p>
  <p><b>معامل سيلويت.</b> يُحسب من مسافات العينات الأصلية باستخدام مجموعتين: ${esc(focus)} و${esc(other)}. تُجمع المجموعات الأخرى في طرف واحد. يتراوح من −1 إلى 1؛ وتشير القيم الأعلى إلى انفصال أقوى. وهو مقياس وصفي وليس اختبار دلالة إحصائية. يظل قائمًا على العينات حتى في عرض المراكز.</p>
  <p><b>تحليل المكونات الرئيسية.</b> إسقاط ثنائي الأبعاد لتكرارات السمات ${c.distance==='delta'?'المعيارية':'النسبية'}، ولا يمثّل مسافات ${distanceName(c.distance)} تمثيلًا تامًا. تستخدم أقوى 20 متجهًا للسمات أوزان المكونات مضروبة في انحرافاتها المعيارية، بمقياس عرض موحّد. خطوط التسميات لتحسين القراءة فقط؛ قارن اتجاهات الأسهم، لا المسافات بين التسميات والعينات.</p>
  <ul>${r.warnings.map(w=>`<li>${esc(translateMessage(w))}</li>`).join('')}</ul>
  <p><b>إعادة الإنتاج.</b> مقاطع كاملة غير متداخلة تُسحب دون إرجاع، باستخدام بذرة عشوائية مستقلة لكل عصر. تتضمن الملفات المصدّرة مسارات المصادر وأرقام المقاطع بدءًا من الصفر وبصمات SHA-256 ومصفوفة التكرارات النسبية وجميع الإعدادات.</p>
  <details><summary>الإعدادات المسجّلة وسجل العينات</summary><pre style="white-space:pre-wrap;font-size:12px">${esc(JSON.stringify(settings,null,2))}</pre><ul>${r.samples.map(s=>`<li>${esc(sampleLabel(s))} — <code dir="ltr">${esc(s.source)}</code>، المقطع ${s.chunk}، ${s.raw_words.toLocaleString()} كلمة مصدرية</li>`).join('')}</ul></details>`;
}
function render() {
  const r=result, c=r.config;
  const selected=featureSets.find(f=>f.feature===c.feature&&f.ngram===c.ngram);
  $('result-caption').textContent=`${t(selected.name).toUpperCase()} · ${distanceName(c.distance)} · ${linkageName(c.linkage)}`;
  const focus=groupName(c.target),others=c.eras.filter(e=>e!==c.target);
  const other=others.length===1?groupName(others[0]):c.target==='Quran'?t('poetry'):t('other selected groups');
  $('result-title').textContent=t('{focus} compared with {other}',{focus,other});
  $('feature-caption').textContent=t('WHAT DISTINGUISHES {focus}?',{focus:focus.toUpperCase()});
  $('feature-title').textContent=t(c.feature==='words'?'{focus} vs {other}: top {count} most frequent words':'{focus} vs {other}: top {count} features',{focus,other,count:r.features.length});
  $('focus-rate').textContent=t('{group} rate',{group:focus});
  $('other-rate').textContent=t('{group} rate',{group:other});
  $('metrics').innerHTML=[[r.sample_count,t('Text samples')],[r.feature_count,t('Features used')],[r.branch.testable?`${Math.round(r.branch.purity*100)}%`:'—',t('{group} branch purity',{group:focus})],[r.silhouette===null?'—':r.silhouette.toFixed(3),t('{focus} / {other} silhouette',{focus,other})]].map(([v,l])=>`<div><strong>${esc(v)}</strong><span>${l}</span></div>`).join('');
  $('legend').innerHTML=c.eras.map(e=>`<span><i style="background:${palette[e]}"></i>${esc(groupName(e))}</span>`).join('');
  $('sampling-note').textContent=r.warnings.filter(w=>w.includes('complete non-overlapping chunks')).map(translateMessage).join(' ');
  drawTree(r); drawPCA(r); chartNote();
  const b=r.branch;
  $('finding').textContent=!b.testable ? (c.view==='centroids' ? t('Centroid view compares the average style of each category. Switch to text samples to test whether {focus} samples form a separate branch.',{focus}) : t('At least two {focus} samples are needed to test whether they form a separate branch.',{focus})) : b.separate ? t('At these settings, all {count} {focus} samples form a separate branch containing no samples from the other selected groups. Compare feature sets to see how consistent this separation is.',{count:b.target_count,focus}) : t('At these settings, {focus} samples do not form an exclusive branch. The smallest branch containing all {count} {focus} samples also contains {others} samples from other groups ({total} total).',{focus,count:b.target_count,others:b.total_count-b.target_count,total:b.total_count});
  const max=Math.max(...r.features.map(f=>Math.abs(f.effect)),.01);
  $('feature-rows').innerHTML=r.features.map((f,index)=>`<tr class="feature-data-row"><td class="arabic" dir="auto">${esc(c.feature==='length'?`${f.name}${f.name==='15'?'+':''} letters`:f.name)}</td><td data-label="${esc(t('{group} rate',{group:focus}))}">${f.focus.toFixed(2)}</td><td data-label="${esc(t('{group} rate',{group:other}))}">${f.other.toFixed(2)}</td><td data-label="${esc(t('Standardized difference'))}"><span class="effect"><span class="effect-track"><i style="width:${Math.abs(f.effect)/max*100}%;background:${f.effect>=0?'#4c8066':'#b08a57'}"></i></span><span class="effect-value">${f.effect>0?'+':''}${f.effect.toFixed(2)}</span></span></td>${FEATURE_EXAMPLES_ENABLED ? `<td><button type="button" class="plain feature-example-toggle" data-feature-index="${index}" aria-expanded="false" aria-controls="feature-examples-${index}">${t('See examples')}</button></td>` : ''}</tr>${FEATURE_EXAMPLES_ENABLED ? `<tr class="feature-examples-row" id="feature-examples-${index}" hidden><td colspan="5"></td></tr>` : ''}`).join('') || `<tr><td colspan="${FEATURE_EXAMPLES_ENABLED ? 5 : 4}">${t('No varying feature differences are available for this selection.')}</td></tr>`;
  if(FEATURE_EXAMPLES_ENABLED && expandedFeature !== null) showFeatureExamples(expandedFeature);
  $('methodology').innerHTML=language==='ar'?arabicMethods(r,focus,other):`<p><b>Distance.</b> ${esc(r.method)} ${esc(c.linkage)} linkage. Features are selected from pooled counts without consulting group labels; constant features are excluded.</p><p><b>Normalization.</b> ${esc(r.normalization)}. Feature frequencies use all feature events as the denominator, including events outside the retained vocabulary.</p><p><b>Feature contrast.</b> ${esc(focus)} mean minus the mean of ${esc(other)}, divided by the sample standard deviation across all selected samples. Positive values mean higher frequency in ${esc(focus)} samples. The comparator is weighted by sample count.</p><p><b>Branch purity.</b> Proportion of ${esc(focus)} leaves in the smallest subtree containing every ${esc(focus)} leaf. 100% indicates an exclusive branch when at least two ${esc(focus)} samples are present.</p><p><b>Silhouette.</b> Calculated on original sample distances using two labels: ${esc(focus)} and ${esc(other)}. All selected groups other than the focus group are pooled for this measure. Ranges from −1 to 1; higher means stronger separation of the focus group from the other selected groups. It is descriptive, not a significance test. Centroid mode retains this sample-based metric.</p><p><b>PCA.</b> Two-component projection of ${c.distance==='delta'?'standardized':'relative'} feature frequencies; it is not an exact rendering of ${esc(c.distance)} distances. The 20 strongest feature vectors use component weights multiplied by component standard deviations, uniformly scaled to fit the sample plot. Label guide lines are only for readability; compare arrow directions, not label-to-sample distances.</p><ul>${r.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul><p><b>Reproducibility.</b> Non-overlapping full chunks sampled without replacement; per-era seeded random streams. Exports include exact source paths, zero-based chunk indices, sample SHA-256 hashes, normalized feature matrix and all parameters.</p><details><summary>Recorded settings & sample manifest</summary><pre style="white-space:pre-wrap;font-size:10px">${esc(JSON.stringify(c,null,2))}</pre><ul>${r.samples.map(s=>`<li>${esc(sampleLabel(s))} — <code>${esc(s.source)}</code>, chunk ${s.chunk}, ${s.raw_words.toLocaleString()} source words</li>`).join('')}</ul></details>`;
  ['download','svg-export','csv-export'].forEach(k=>$(k).disabled=false);
}
function poetCredit(poets) {
  return `<div class="feature-example-poet">${t(poets.length > 1 ? 'Multiple attributions in the source:' : poets.length ? 'Poet:' : 'Poet not identified in the source.')}${poets.length ? ` <bdi lang="ar">${poets.map(esc).join(' / ')}</bdi>` : ''}</div>`;
}
function referenceExampleContent(index, era) {
  if (era === 'Quran') return '';
  const entry = referenceExamples.get(`${index}:${era}`);
  if (entry?.status === 'ready') {
    const e = entry.example;
    return `<div class="feature-reference-example">
      <p class="feature-reference-label">${t('Reference example from this corpus, outside the analysis samples. It is not used in this experiment’s counts or results.')}</p>
      ${poetCredit(e.poets)}
      <p class="feature-example-passage" lang="ar" dir="rtl">${esc(e.before)}<mark>${esc(e.match)}</mark>${esc(e.after)}</p>
    </div>`;
  }
  if (entry?.status === 'empty') return `<p class="feature-reference-label">${t('No matching corrected passage was found outside the selected samples either.')}</p>`;
  return `${entry?.status === 'error' ? `<p role="status">${t('Could not load the reference example. Please try again.')}</p>` : ''}
    <button type="button" class="plain feature-reference-button" data-reference-era="${esc(era)}" data-reference-index="${index}" ${entry?.status === 'loading' ? 'disabled' : ''}>${t(entry?.status === 'loading' ? 'Finding a reference example…' : 'Show a reference example outside the analysis samples')}</button>`;
}
async function loadReferenceExample(index, era) {
  const experiment = result;
  const feature = experiment?.features[index];
  if (!feature || !experiment.config.eras.includes(era)) return;
  const key = `${index}:${era}`;
  if (referenceExamples.get(key)?.status === 'loading') return;
  referenceExamples.set(key, {status:'loading'});
  if (expandedFeature === index) showFeatureExamples(index);
  try {
    const response = await fetch('/api/reference-example', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({config:experiment.config,era,feature:feature.name})});
    if (!response.ok) throw new Error('Reference request failed');
    const data = await response.json();
    if (result !== experiment) return;
    referenceExamples.set(key, {status:data.example ? 'ready' : 'empty', example:data.example});
  } catch (_) {
    if (result !== experiment) return;
    referenceExamples.set(key, {status:'error'});
  }
  if (expandedFeature === index) showFeatureExamples(index);
}
function showFeatureExamples(index) {
  if (!FEATURE_EXAMPLES_ENABLED) return;
  const feature = result?.features[index];
  if(!feature)return;
  const examples = featureExamples(result, feature.name);
  const byEra = new Map(examples.map(example => [example.sample.era, example]));
  const row = $(`feature-examples-${index}`);
  const button = document.querySelector(`[data-feature-index="${index}"]`);
  button.textContent = t('Hide examples');
  button.setAttribute('aria-expanded', 'true');
  row.hidden = false;
  row.firstElementChild.innerHTML = `<div class="feature-examples-heading">${t('Examples of')} <bdi class="feature-example-name" lang="ar">${esc(feature.name)}</bdi></div>
    <p class="feature-examples-note">${t('Matches are found in the historical comparison text. Quran and poetry examples show source spelling, so highlights may differ from feature labels. Poetry examples are limited to passages with a matching corrected source; unmatched passages are omitted.')}</p>
    <p class="feature-examples-note">${t('One example per selected group is shown where a matching source passage is available.')}</p>
    <div class="feature-examples-grid">${result.config.eras.map(era => {
      const example = byEra.get(era);
      const evidence = featureGroupEvidence(result, feature.name, era);
      const frequency = `<p class="feature-analysis-evidence">${t('In the analysis: {rate} per 10,000 feature events; present in {present} of {samples} samples.', {rate:evidence.rate.toFixed(2),present:evidence.present,samples:evidence.samples})}</p>`;
      const noCoveredSamples = era !== 'Quran' && !result.samples.some(s => s.era === era && s.display_spans?.length);
      if (!example) return `<article class="feature-example-card feature-example-unavailable" data-era="${esc(era)}">
        <div class="feature-example-source">${esc(groupName(era))}</div>
        ${frequency}
        ${evidence.present ? `<p class="feature-quotation-status">${t('This feature is counted in the clustering. Only a corrected quotation from these samples is unavailable.')}</p>` : `<p class="feature-quotation-status">${t('This feature has zero frequency in this group’s selected samples. Clustering uses the full selected feature matrix.')}</p>`}
        <p>${t(noCoveredSamples ? 'The corrected source does not cover any of this group’s selected samples. Its historical text is still included in the analysis.' : 'No corrected example of this feature is available in this group’s selected samples.')}</p>
        ${referenceExampleContent(index, era)}
      </article>`;
      const poets = example.displaySpan?.poets ?? [];
      const credit = era === 'Quran' ? '' : poetCredit(poets);
      return `<article class="feature-example-card" data-era="${esc(era)}">
        <div class="feature-example-source">${esc(sampleLabel(example.sample))}</div>
        ${frequency}
        ${credit}
        <p class="feature-example-passage" lang="ar" dir="rtl">${esc(example.before)}<mark>${esc(example.match)}</mark>${esc(example.after)}</p>
      </article>`;
    }).join('')}</div>`;
}
function toggleFeatureExamples(index) {
  const previous = expandedFeature;
  if(previous !== null) {
    $(`feature-examples-${previous}`).hidden = true;
    const button = document.querySelector(`[data-feature-index="${previous}"]`);
    button.textContent = t('See examples');
    button.setAttribute('aria-expanded', 'false');
  }
  expandedFeature = previous === index ? null : index;
  if(FEATURE_EXAMPLES_ENABLED && expandedFeature !== null) showFeatureExamples(expandedFeature);
}
function drawTree(r) {
  const width=Math.max(830,r.leaves.length*24+105),height=640,left=65,right=width-35,top=30,bottom=440;
  let index=0,paths='',labels='';
  const max=Math.max(r.tree.distance,1e-10), step=(right-left)/Math.max(r.leaves.length-1,1);
  function visit(n) {
    const y=bottom-n.distance/max*(bottom-top);
    if(n.leaf) {
      const x=left+index++*step;
      labels+=`<g class="tree-leaf" data-era="${esc(n.leaf.era)}"><circle cx="${x}" cy="${bottom+7}" r="3" fill="${palette[n.leaf.era]}"/><text transform="translate(${x} ${bottom+18}) rotate(65)" fill="${palette[n.leaf.era]}" font-size="11"><title>${esc(n.leaf.source||sampleLabel(n.leaf))}</title>${esc(sampleLabel(n.leaf))}</text></g>`;
      return {x,y,era:n.leaf.era};
    }
    const a=visit(n.children[0]),b=visit(n.children[1]);
    const era=a.era===b.era?a.era:null;
    paths+=`<path d="M${a.x},${a.y}V${y}H${b.x}V${b.y}" stroke="${era?palette[era]:'#aeb7aa'}" stroke-width="${n.id===r.branch.node&&r.branch.testable?2.7:1.35}" fill="none"><title>${t('Merge distance')}: ${n.distance.toFixed(5)}</title></path>`;
    return {x:(a.x+b.x)/2,y,era};
  }
  visit(r.tree);
  let ticks='';
  for(let i=0;i<=4;i++){const y=bottom-i*(bottom-top)/4;ticks+=`<path d="M${left-12} ${y}h5" stroke="#778173"/><text x="${left-17}" y="${y+3}" text-anchor="end" font-size="9" fill="#778173">${(max*i/4).toFixed(3)}</text>`;}
  $('tree-chart').innerHTML=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${t('Vertical hierarchical cluster tree of the selected Arabic texts')}" style="min-width:${width}px;font-family:Arial,sans-serif;background:#fffefa"><title>${t('Hierarchical clustering · {distance} distance · {linkage} linkage',{distance:distanceName(r.config.distance),linkage:linkageName(r.config.linkage)})}</title><path d="M${left-7} ${top}V${bottom}" stroke="#d5d9cf"/>${ticks}${paths}${labels}<text transform="translate(12 ${(top+bottom)/2}) rotate(-90)" text-anchor="middle" font-size="10" fill="#778173">${t('Merge distance')}</text></svg>`;
}
function drawPCA(r) {
  const width=900,height=620,pad=70,features=r.pca_features||[];
  const points=[...r.projection,...features,{x:0,y:0}];
  const xs=points.map(p=>p.x),ys=points.map(p=>p.y),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  // Equal scale on both axes preserves the angles of feature vectors.
  const scale=Math.min((width-2*pad)/(maxX-minX||1),(height-2*pad)/(maxY-minY||1));
  const sx=x=>width/2+(x-(minX+maxX)/2)*scale,sy=y=>height/2-(y-(minY+maxY)/2)*scale;
  let grids='';
  for(let i=0;i<=4;i++){const x=pad+i*(width-2*pad)/4,y=pad+i*(height-2*pad)/4;grids+=`<path d="M${x} ${pad}V${height-pad}M${pad} ${y}H${width-pad}" stroke="#e9ebe2"/>`;}
  const overlap=(a,b)=>a.x<b.x+b.w+4&&a.x+a.w+4>b.x&&a.y<b.y+b.h+4&&a.y+a.h+4>b.y;
  const occupied=r.projection.map(p=>({x:sx(p.x)-7,y:sy(p.y)-7,w:14,h:14}));
  const context=document.createElement('canvas').getContext('2d');context.font='13px Tahoma, Arial, sans-serif';
  let vectors='',labels='';
  for(const f of features) {
    const x=sx(f.x),y=sy(f.y),name=r.config.feature==='length'?`${f.name}${f.name==='15'?'+':''} letters`:f.name;
    const w=Math.min(context.measureText(name).width+12,width-2*pad),h=22;
    let box,bestScore=Infinity;
    for(let radius=16;radius<=180;radius+=20) {
      for(let angle=0;angle<8;angle++) {
        const theta=angle*Math.PI/4;
        const candidate={x:Math.max(35,Math.min(width-w-20,x+Math.cos(theta)*radius-w/2)),y:Math.max(25,Math.min(height-h-40,y+Math.sin(theta)*radius-h/2)),w,h};
        const score=occupied.filter(other=>overlap(candidate,other)).length*1000+radius;
        if(score<bestScore){box=candidate;bestScore=score;}
      }
      if(bestScore<1000)break;
    }
    occupied.push(box);
    vectors+=`<path class="pca-vector" d="M${sx(0)} ${sy(0)}L${x} ${y}" stroke="#a28a64" stroke-opacity=".55" stroke-width="1" marker-end="url(#feature-arrow)" fill="none"/>`;
    labels+=`<g class="pca-feature"><title>${esc(name)} · ${t('PC1 loading')} ${f.loading_x.toFixed(4)}, ${t('PC2 loading')} ${f.loading_y.toFixed(4)}</title><path d="M${x} ${y}L${box.x+w/2} ${box.y+h/2}" stroke="#a28a64" stroke-opacity=".4" fill="none"/><rect x="${box.x}" y="${box.y}" width="${w}" height="${h}" rx="3" fill="#fffefa" fill-opacity=".9"/><text x="${box.x+w/2}" y="${box.y+15}" text-anchor="middle" direction="${r.config.feature==='length'?'ltr':'rtl'}" font-family="Tahoma,Arial,sans-serif" font-size="13" fill="#73562d" xml:space="preserve">${esc(name)}</text></g>`;
  }
  $('pca-chart').innerHTML=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${t('PCA biplot with text samples and feature directions')}" style="font-family:Arial,sans-serif;background:#fffefa"><title>${t('Principal components with the 20 strongest feature vectors')}</title><defs><marker id="feature-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L8 4L0 8" fill="#a28a64"/></marker></defs>${grids}<path d="M${sx(0)} ${pad}V${height-pad}M${pad} ${sy(0)}H${width-pad}" stroke="#cdd3c8" stroke-dasharray="4 4"/>${vectors}${labels}${r.projection.map(p=>`<circle class="pca-sample" data-era="${esc(p.era)}" cx="${sx(p.x)}" cy="${sy(p.y)}" r="${p.era===r.config.target?6:4}" fill="${palette[p.era]}" fill-opacity=".8" stroke="white" stroke-width="1.2"><title>${esc(sampleLabel(p))} · ${groupName(p.era)} · PC1 ${p.x.toFixed(3)}, PC2 ${p.y.toFixed(3)}</title></circle>`).join('')}<text x="${width/2}" y="${height-12}" font-size="11" fill="#647164" text-anchor="middle">PC1 · ${(r.explained[0]*100).toFixed(1)}% ${t('of variance')}</text><text transform="translate(15 ${height/2}) rotate(-90)" text-anchor="middle" font-size="11" fill="#647164">PC2 · ${(r.explained[1]*100).toFixed(1)}% ${t('of variance')}</text></svg>`;
}
function chartNote() {
  $('chart-title').textContent=t(activeChart==='tree'?'Hierarchical clustering (HC)':'Principal component analysis (PCA)');
  $('chart-note').textContent=activeChart==='tree'?t('Branches join similar texts; colors show supplied corpus labels.'):t('Points are text samples; Arabic labels and arrows show the 20 strongest feature directions in PC1 and PC2. Arrows share one display scale; label guide lines improve readability.');
}
function switchChart(which) {
  activeChart=which;
  ['tree','pca'].forEach(k=>{$(`${k}-chart`).hidden=k!==which;$(`${k}-tab`).classList.toggle('active',k===which);$(`${k}-tab`).setAttribute('aria-selected',String(k===which));$(`${k}-tab`).tabIndex=k===which?0:-1;});
  chartNote();
}
function download(content,name,type) {
  const url=URL.createObjectURL(new Blob([content],{type}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function renderComparison() {
  if(!comparisonResults.length){$('comparison').replaceChildren();return;}
  const rows=comparisonResults.map(({feature,r,error})=>{
    if(error)return `<tr><td>${esc(t(feature.name))}</td><td colspan="4">${esc(translateMessage(error))}</td></tr>`;
    return `<tr><td>${esc(t(feature.name))}</td><td>${r.feature_count}</td><td>${r.branch.testable?`${Math.round(r.branch.purity*100)}%`:t('Not testable')}</td><td>${r.silhouette===null?'—':r.silhouette.toFixed(3)}</td><td>${t(r.branch.testable?(r.branch.separate?'Separate':'Mixed'):'Not tested')}</td></tr>`;
  });
  $('comparison').innerHTML=`<div class="table-scroll"><table><thead><tr><th>${t('Feature Set')}</th><th>${t('Features')}</th><th>${t('Purity')}</th><th>${t('Silhouette')}</th><th>${esc(t('{group} branch',{group:groupName(result.config.target)}))}</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}
async function compare() {
  if(!result||busy)return;
  const c={...result.config},requestedRevision=revision;setBusy(true);
  comparisonResults=[];renderComparison();
  try {
    for(const f of featureSets) {
      setMessage('status','Comparing feature sets: {feature}…',{feature:f.name});
      try {
        const r=await requestExperiment({...c,feature:f.feature,ngram:f.ngram});
        if(requestedRevision!==revision)return;
        comparisonResults.push({feature:f,r:{feature_count:r.feature_count,branch:r.branch,silhouette:r.silhouette}});
      }catch(e){if(requestedRevision!==revision)return;comparisonResults.push({feature:f,error:e.message});}
      renderComparison();
    }
    setMessage('status', 'Feature comparison complete. Main tree retains its original feature set.');
  }finally{setBusy(false);if(pendingRun||requestedRevision!==revision)run();}
}
async function init() {
  try {
    const catResponse=await fetch('/api/catalog');
    if(!catResponse.ok)throw new Error('Could not load the local corpus.');
    catalog=await catResponse.json();
    catalog.eras.forEach((e,i)=>{names[e.id]=e.name;palette[e.id]=colors[i];});
    const websiteEras=catalog.eras.filter(e=>e.id!=='Islamic');
    $('era-options').innerHTML=websiteEras.map(e=>`<label class="${e.id==='Mukhadramun'?'era-option-bilingual':''}" title="${e.words.toLocaleString()} ${language==='ar'?'كلمة':'words'} · ${e.file}"><input type="checkbox" name="era" value="${e.id}"><span data-era-name="${e.id}">${esc(groupName(e.id))}</span></label>`).join('');
    $('examples-heading').hidden = !FEATURE_EXAMPLES_ENABLED;
    $('feature-comparison').classList.toggle('features-only', !FEATURE_EXAMPLES_ENABLED);
    $('compare').textContent=t('Compare {count} sets',{count:featureSets.length});
    $('feature').innerHTML=featureSets.map(f=>`<option value="${f.id}">${esc(t(f.name))}</option>`).join('');
    $('experiment-form').addEventListener('submit',e=>{e.preventDefault();run();});
    $('experiment-form').addEventListener('change',controlsChanged);
    $('reset').onclick=resetExperiment;
    $('select-all').onclick=()=>{document.querySelectorAll('[name=era]:not(:disabled)').forEach(e=>e.checked=true);controlsChanged();};
    $('tree-tab').onclick=()=>switchChart('tree');$('pca-tab').onclick=()=>switchChart('pca');
    document.querySelectorAll('[role=tab]').forEach(tab=>tab.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();switchChart(activeChart==='tree'?'pca':'tree');$(`${activeChart}-tab`).focus();}}));
    $('download').onclick=()=>download(JSON.stringify(result,null,2),'quran-stylometry-experiment.json','application/json');
    $('svg-export').onclick=()=>download($(`${activeChart}-chart`).querySelector('svg').outerHTML,`quran-stylometry-${activeChart}.svg`,'image/svg+xml');
    $('csv-export').onclick=()=>{const cell=s=>'"'+String(s).replaceAll('"','""')+'"';const rows=[['sample','era',...result.feature_names],...result.samples.map((s,i)=>[s.id,s.era,...result.feature_matrix[i]])];download('\uFEFF'+rows.map(r=>r.map(cell).join(',')).join('\r\n'),'quran-stylometry-feature-matrix.csv','text/csv;charset=utf-8');};
    $('feature-rows').addEventListener('click', event => {
      const referenceButton = event.target.closest('[data-reference-era]');
      if(referenceButton) { loadReferenceExample(Number(referenceButton.dataset.referenceIndex), referenceButton.dataset.referenceEra); return; }
      const button = event.target.closest('[data-feature-index]');
      if(button) toggleFeatureExamples(Number(button.dataset.featureIndex));
    });
    $('compare').onclick=compare;
    $('language').onchange=()=>setLanguage($('language').value);
    resetExperiment();
  }catch(e){setMessage('status',e.message);setMessage('error',e.message);$('error').hidden=false;}
}
$('language').onchange=()=>setLanguage($('language').value);
init();
