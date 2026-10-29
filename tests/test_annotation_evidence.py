"""Synthetic source-evidence contracts for supplied AI annotations."""
import json
from pathlib import Path
import tempfile
import unittest

import build_recommendations as builder


class AnnotationEvidenceTests(unittest.TestCase):
    def dish(self, **changes):
        value=dict(dish_name='curry', evidence='The curry was spicy and delicious.',
                   taste_tags=[dict(tag='spicy',evidence='The curry was spicy and delicious.')],
                   sentiment='positive',sentiment_evidence='The curry was spicy and delicious.')
        value.update(changes)
        return value

    def test_retained_dish_and_taste_quotes_must_be_verbatim(self):
        source='The curry was spicy and delicious.'
        good,dropped=builder.validate_dishes([self.dish()],source)
        self.assertEqual(len(good),1);self.assertEqual(dropped,{})
        for change in [dict(evidence='The curry was amazing.'),
                       dict(taste_tags=[dict(tag='sweet',evidence='It was sweet.')])]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                builder.validate_dishes([self.dish(**change)],source)

    def test_restaurant_or_service_opinion_cannot_supply_dish_sentiment(self):
        source='I ordered curry. The staff were excellent.'
        rows,_=builder.validate_dishes([self.dish(evidence='I ordered curry.',taste_tags=[],
            sentiment_evidence='The staff were excellent.')],source)
        self.assertEqual(rows[0]['sentiment'],'neutral')
        self.assertEqual(rows[0]['sentiment_evidence'],[])

    def test_unresolved_failure_cannot_be_silently_exported_as_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'annotations.jsonl'
            p.write_text(json.dumps(dict(review_id='fixture',status='failed',dishes=[]))+'\n')
            with self.assertRaisesRegex(ValueError,'Unresolved extraction failure'):
                builder.read_annotations(p,[dict(review_id='fixture')])

    def test_annotation_ids_must_cover_selected_reviews_exactly_once(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'annotations.jsonl';a=json.dumps(dict(review_id='fixture',dishes=[]))
            p.write_text(a+'\n'+a+'\n')
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                builder.read_annotations(p,[dict(review_id='fixture')])
            p.write_text(a+'\n')
            with self.assertRaisesRegex(ValueError,'missing'):
                builder.read_annotations(p,[dict(review_id='fixture'),dict(review_id='other')])

    def test_one_bad_proposal_does_not_discard_other_evidence_backed_items(self):
        source='The curry was spicy and delicious.'
        rows,dropped=builder.validate_dishes([self.dish(),self.dish(dish_name='invented soup')],source)
        self.assertEqual(len(rows),1)
        self.assertTrue(any(key.startswith('invalid_item:') for key in dropped))


if __name__=='__main__':unittest.main()
