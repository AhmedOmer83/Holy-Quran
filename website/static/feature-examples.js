'use strict';

// Read the actual matrix used for distances, independently of quote coverage.
function featureGroupEvidence(experiment, feature, era) {
  const column = experiment.feature_names.indexOf(feature);
  const rates = experiment.samples.flatMap((sample, index) => sample.era === era ? [experiment.feature_matrix[index][column]] : []);
  return {samples:rates.length, present:rates.filter(rate => rate > 0).length,
    rate:rates.length ? rates.reduce((sum, rate) => sum + rate, 0) / rates.length * 10000 : 0};
}

// Match the normalized sample text used by the experiment, including spaces
// inside character n-grams and whole-token boundaries for word features.
function* featureOccurrences(sample, feature, kind) {
  const text = sample.text || '';
  if (!feature) return;
  if (kind === 'length') {
    for (const match of text.matchAll(/\S+/gu)) {
      if (Math.min([...match[0]].length, 15) === Number(feature)) {
        yield {start:match.index, end:match.index + match[0].length};
      }
    }
    return;
  }
  const wholeWords = ['words', 'wordgrams', 'function'].includes(kind);
  for (let start = text.indexOf(feature); start !== -1; start = text.indexOf(feature, start + 1)) {
    const end = start + feature.length;
    if (wholeWords && ((start > 0 && text[start - 1] !== ' ') || (end < text.length && text[end] !== ' '))) continue;
    yield {start, end};
  }
}

function* displayOccurrences(sample, feature, kind) {
  for (const occurrence of featureOccurrences(sample, feature, kind)) {
    const span = sample.display_spans === undefined ? null :
      sample.display_spans.find(s => s.start <= occurrence.start && s.end >= occurrence.end);
    if (sample.display_spans !== undefined && !span) continue;
    yield {...occurrence, span};
  }
}

function featureExamples(experiment, feature) {
  // One source-backed example per selected group, without a three-card cap.
  // Search later samples too, so a missing early match never hides an era.
  // Identical excerpts in different corpora still represent different groups.
  return experiment.config.eras.flatMap(era => {
    for (const sample of experiment.samples.filter(sample => sample.era === era)) {
      const occurrence = displayOccurrences(sample, feature, experiment.config.feature).next();
      if (occurrence.done) continue;
      const {start, end, span} = occurrence.value;
      const text = sample.display_text ?? sample.text;
      const left = Math.max(span?.start ?? 0, start > 70 ? text.lastIndexOf(' ', start - 70) + 1 : 0);
      const nextSpace = text.indexOf(' ', end + 70);
      const right = Math.min(span?.end ?? text.length, nextSpace === -1 ? text.length : nextSpace);
      return [{sample, start, end, displaySpan:span,
        analysisMatch:sample.text.slice(start, end),
        before:(left ? '… ' : '') + text.slice(left, start),
        match:text.slice(start, end),
        after:text.slice(end, right) + (right < text.length ? ' …' : '')}];
    }
    return [];
  });
}
