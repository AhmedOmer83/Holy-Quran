'use strict';
let textMetadataRecords = null;
let textMetadataFailed = false;
const metadataElement = id => document.getElementById(id);
const metadataEscape = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

function renderTextMetadata() {
  const status = metadataElement('metadata-status');
  metadataElement('metadata-retry').hidden = !textMetadataFailed;
  if (!textMetadataRecords) {
    status.textContent = t(textMetadataFailed ? 'Could not load text information. Please try again.' : 'Loading text information…');
    return;
  }
  const periodSelect = metadataElement('metadata-period');
  const selectedPeriod = periodSelect.value;
  const periods = [...new Map(textMetadataRecords.map(record => [record.period, record.period_name])).entries()];
  periodSelect.innerHTML = `<option value="all">${t('All periods')}</option>` + periods.map(([id, name]) => `<option value="${metadataEscape(id)}">${metadataEscape(t(name))}</option>`).join('');
  periodSelect.value = selectedPeriod;
  const filtered = textMetadataRecords.filter(record => selectedPeriod === 'all' || record.period === selectedPeriod);
  status.textContent = t('{count} poets · {periods} periods', {count: filtered.length, periods: new Set(filtered.map(record => record.period)).size});
  const container = metadataElement('metadata-records');
  const expanded = new Set([...container.querySelectorAll('details[open]')].map(node => node.dataset.record));
  if (!filtered.length) {
    container.innerHTML = `<p class="metadata-empty">${t('No texts are available for this period.')}</p>`;
    return;
  }
  container.innerHTML = `<div class="table-scroll metadata-table-scroll" tabindex="0" role="region" aria-label="${t('Text metadata catalogue')}"><table class="metadata-table"><thead><tr><th scope="col">${t('Period')}</th><th scope="col">${t('Author')}</th><th scope="col">${t('Poem titles')}</th></tr></thead><tbody>${filtered.map(record => `<tr>
    <td data-label="${t('Period')}">${metadataEscape(t(record.period_name))}</td>
    <td data-label="${t('Author')}"><span lang="ar" dir="rtl">${metadataEscape(record.author)}</span></td>
    <td data-label="${t('Poem titles')}"><span class="metadata-poem-title" lang="ar" dir="rtl">${metadataEscape(record.primary_poem_title)}</span><details data-record="${metadataEscape(record.id)}" ${expanded.has(record.id) ? 'open' : ''}><summary>${t('All poem titles ({count})', {count: record.poem_titles.length})}</summary><ul lang="ar" dir="rtl">${record.poem_titles.map(title => `<li>${metadataEscape(title)}</li>`).join('')}</ul></details></td>
  </tr>`).join('')}</tbody></table></div>`;
}

async function loadTextMetadata() {
  textMetadataFailed = false;
  renderTextMetadata();
  try {
    const response = await fetch('/api/text-metadata');
    if (!response.ok) throw new Error('Metadata unavailable');
    const data = await response.json();
    textMetadataRecords = data.records;
  } catch (_) {
    textMetadataFailed = true;
  }
  renderTextMetadata();
}

metadataElement('metadata-period').addEventListener('change', renderTextMetadata);
metadataElement('metadata-retry').addEventListener('click', loadTextMetadata);
loadTextMetadata();
