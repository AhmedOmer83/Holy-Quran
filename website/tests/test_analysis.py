import sys
import unittest
import unicodedata
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.spatial.distance import pdist
from sklearn.metrics import silhouette_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import normalize, validate, feature_matrix, documents, run_experiment
from app import app

class AnalysisTests(unittest.TestCase):
    def test_arabic_normalization(self):
        self.assertEqual(normalize('إِنَّـا أَعْطَيْنَاكَ ٱلْكَوْثَرَ ١٢٣'), 'انا اعطيناك الكوثر')
        self.assertEqual(normalize('إلى', False), 'إلى')
        self.assertEqual(normalize('إلى'), 'الي')

    def test_frequency_denominator_and_constant_filter(self):
        docs=[{'text':'في في بيت'}, {'text':'في بيت بيت'}]
        x,names=feature_matrix(docs,validate({'feature':'function'}))
        self.assertEqual(names,['في'])
        np.testing.assert_allclose(x[:,0],[2/3,1/3])

    def test_delta_matches_hand_calculated_distance(self):
        fake=[dict(id=str(i),label=str(i),era='Quran' if i<2 else 'PreIslamic',text=t,source='fixture',chunk=i,raw_words=4) for i,t in enumerate(['قال قال قال بيت','قال قال بيت بيت','بيت بيت بيت قال','بيت بيت بيت بيت'])]
        with patch('analysis.documents',return_value=(fake,[])):
            r=run_experiment({'eras':['Quran','PreIslamic'],'feature':'words','distance':'delta','linkage':'average'})
        x=np.array(r['feature_matrix']);z=(x-x.mean(axis=0))/x.std(axis=0,ddof=1)
        expected=pdist(z,'cityblock')/x.shape[1]
        self.assertAlmostEqual(r['linkage'][0][2],expected.min())
        self.assertTrue(r['branch']['separate'])

    def test_sampling_is_reproducible_nonoverlapping_and_group_stable(self):
        c=validate({'eras':['Quran','Islamic'],'words':1000,'samples':5})
        a,_=documents(c);b,_=documents(c)
        self.assertEqual(a,b)
        self.assertEqual(len({d['id'] for d in a}),len(a))
        self.assertTrue(all(d['raw_words']==1000 for d in a))
        c['eras'].append('PreIslamic');d,_=documents(c)
        self.assertEqual([x['sha256'] for x in a if x['era']=='Quran'],[x['sha256'] for x in d if x['era']=='Quran'])
        c['seed']=43;different,_=documents(c)
        self.assertNotEqual([x['sha256'] for x in a],[x['sha256'] for x in different])

    def test_invalid_settings(self):
        for c in [{'linkage':'ward'}, {'eras':['Quran']}, {'samples':10000}, {'samples':11}, {'ngram':6}, {'feature':'wordgrams','ngram':7}, {'feature':'chargrams','ngram':8}, {'feature':[]}, {'target':'Unknown'}, {'fold':'yes'}, {'dataset':'authors'}]:
            with self.subTest(c=c),self.assertRaises(ValueError):validate(c)

    def test_defaults_and_short_category(self):
        c=validate({})
        self.assertEqual((c['feature'],c['words'],c['samples'],c['top']),('words',7000,10,100))
        self.assertEqual(c['eras'],['Quran','PreIslamic','Modern'])
        docs,warnings=documents({**c,'eras':c['eras']+['Islamic']})
        counts=Counter(d['era'] for d in docs)
        self.assertEqual(counts['Islamic'],1)
        self.assertEqual(counts['Quran'],10)
        self.assertTrue(all(d['raw_words']==7000 for d in docs))
        self.assertTrue(any('one sample' in warning for warning in warnings))

    def test_empty_chunks_are_rejected(self):
        with patch('pathlib.Path.read_text',return_value='بيت '*499):
            with self.assertRaisesRegex(ValueError,'no complete chunks'):
                documents(validate({'eras':['Quran','Islamic']}))

    def test_deselected_focus_is_excluded(self):
        r=run_experiment({'eras':['PreIslamic','Islamic'],'target':'Quran','feature':'words'})
        self.assertEqual(r['config']['target'],'PreIslamic')
        self.assertIsNotNone(r['branch']['purity'])
        self.assertTrue(r['branch']['testable'])
        self.assertIsNotNone(r['silhouette'])
        self.assertTrue(r['features'])
        self.assertNotIn('Quran',{sample['era'] for sample in r['samples']})
        self.assertNotIn('Quran',{sample['era'] for sample in r['projection']})

    def test_poetry_focus_controls_contrasts_and_silhouette(self):
        settings=dict(eras=['PreIslamic','Umayyad','Abbasid'],target='Umayyad',words=500,samples=3)
        r=run_experiment(settings)
        x=np.array(r['feature_matrix'])
        z=(x-x.mean(axis=0))/x.std(axis=0,ddof=1)
        mask=np.array([s['era']=='Umayyad' for s in r['samples']])
        self.assertAlmostEqual(r['silhouette'],silhouette_score(z,mask,metric='manhattan'))
        self.assertEqual(r['branch']['target_count'],3)
        for f in r['features']:
            i=r['feature_names'].index(f['name'])
            self.assertAlmostEqual(f['effect'],z[mask,i].mean()-z[~mask,i].mean())
            self.assertAlmostEqual(f['focus'],x[mask,i].mean()*10000)
            self.assertAlmostEqual(f['other'],x[~mask,i].mean()*10000)

    def test_pairwise_focus_reversal_and_feature_refresh(self):
        settings=dict(eras=['PreIslamic','Umayyad'],words=500,samples=3)
        a=run_experiment({**settings,'target':'PreIslamic'})
        b=run_experiment({**settings,'target':'Umayyad'})
        self.assertEqual(a['samples'],b['samples'])
        effects={f['name']:f['effect'] for f in b['features']}
        for f in a['features']:
            self.assertAlmostEqual(f['effect'],-effects[f['name']])
        c=run_experiment({**settings,'feature':'chargrams','ngram':3})
        self.assertEqual(a['samples'],c['samples'])
        self.assertTrue(all(len(f)==3 for f in c['feature_names']))
        self.assertNotEqual(a['feature_names'],c['feature_names'])
        self.assertNotEqual(a['feature_matrix'],c['feature_matrix'])

    def test_ngrams_are_clean_and_cover_every_length(self):
        docs=[{'text':'قال، بيت! في؛ من؟ بحر… قلم · شمس ١٢٣'}, {'text':'شجر نهر ارض نور حجر جبل شجر'}]
        for feature in ['chargrams','wordgrams']:
            length=(lambda name:len(name.split())) if feature=='wordgrams' else len
            limit=7 if feature=='chargrams' else 5
            for n in range(limit+1):
                with self.subTest(feature=feature,n=n):
                    x,names=feature_matrix(docs,validate({'feature':feature,'ngram':n,'top':1000}))
                    self.assertEqual({length(name) for name in names},set(range(1,limit+1)) if n==0 else {n})
                    self.assertTrue(all(ch.isspace() or unicodedata.category(ch).startswith('L') for name in names for ch in name))
                    self.assertTrue(np.isfinite(x).all())
        x,names=feature_matrix([{'text':'قال بيت قال'},{'text':'بيت بيت بيت'}],validate({'feature':'wordgrams','ngram':2}))
        self.assertEqual(set(names),{'قال بيت','بيت قال','بيت بيت'})
        np.testing.assert_allclose(x[0],[0,.5,.5])
        np.testing.assert_allclose(x[1],[1,0,0])

    def test_pca_feature_vectors_match_sample_basis(self):
        r=run_experiment({'eras':['Quran','PreIslamic'],'feature':'words','words':1000,'samples':3})
        x=np.array(r['feature_matrix'])
        z=(x-x.mean(axis=0))/x.std(axis=0,ddof=1)
        coords=np.array([[point['x'],point['y']] for point in r['projection']])
        self.assertGreater(len(r['pca_features']),0)
        for f in r['pca_features']:
            i=r['feature_names'].index(f['name'])
            expected=(z[:,i]@coords)/(len(z)-1)/coords.std(axis=0,ddof=1)
            np.testing.assert_allclose([f['loading_x'],f['loading_y']],expected,atol=1e-12)
            np.testing.assert_allclose([f['x'],f['y']],expected*r['pca_feature_scale'],atol=1e-12)

    def test_silhouette_compares_quran_with_all_poetry(self):
        r=run_experiment({'eras':['Quran','PreIslamic','Umayyad'],'words':1000,'samples':3})
        x=np.array(r['feature_matrix'])
        z=(x-x.mean(axis=0))/x.std(axis=0,ddof=1)
        labels=['Quran' if sample['era']=='Quran' else 'Poetry' for sample in r['samples']]
        expected=silhouette_score(z,labels,metric='manhattan')
        self.assertAlmostEqual(r['silhouette'],expected)

    def test_sparse_wordgrams_allow_zero_rows_except_for_cosine(self):
        config={'eras':['Quran','PreIslamic'],'feature':'wordgrams','ngram':5}
        r=run_experiment(config)
        self.assertTrue(any('zero frequency' in warning for warning in r['warnings']))
        self.assertEqual(len(r['projection']),20)
        self.assertTrue(np.isfinite(r['linkage']).all())
        with self.assertRaisesRegex(ValueError,'Cosine distance is undefined'):
            run_experiment({**config,'distance':'cosine'})

    def test_centroid_branch_is_not_a_sample_separation_claim(self):
        r=run_experiment({'eras':['Quran','PreIslamic'],'view':'centroids','feature':'characters'})
        self.assertFalse(r['branch']['testable'])
        self.assertFalse(r['branch']['separate'])
        self.assertEqual(len(r['leaves']),2)
        self.assertEqual(len(r['samples']),20)

    def test_api_and_source_routes(self):
        client=app.test_client()
        for path in ['/','/api/catalog','/static/app.js','/static/style.css']:
            with self.subTest(path=path), client.get(path) as response:
                self.assertEqual(response.status_code,200)
        self.assertEqual(client.get('/api/story').status_code,404)
        self.assertEqual(client.get('/thesis.pdf').status_code,404)
        self.assertEqual(client.post('/api/experiment',json={'linkage':'ward'}).status_code,400)
        self.assertEqual(client.post('/api/experiment',json={'feature':[]}).status_code,400)
        response=client.post('/api/experiment',json={'feature':'length','eras':['Quran','PreIslamic']})
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json['feature_matrix']),20)

if __name__=='__main__':unittest.main()
