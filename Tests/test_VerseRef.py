# SPDX-License-Identifier: MPL-2.0
"""Tests for the VerseRef named tuple and its use by the mapping/passage code.

Run with:
    .venv/bin/python -m unittest discover -s Tests -p test_VerseRef.py
"""
import pickle
import unittest

from BibleOrgSys.Reference.VerseRef import VerseRef
from BibleOrgSys.Reference.BibleVersificationMappings import (
    get_default_mapping_engine, normalize_reference,
)


class VerseRefTests(unittest.TestCase):
    def test_is_still_a_plain_tuple_for_existing_callers(self) -> None:
        ref = VerseRef('GEN', '1', '2', 'a')
        self.assertIsInstance(ref, tuple)
        self.assertEqual(ref, ('GEN', '1', '2', 'a'))
        self.assertEqual(hash(ref), hash(('GEN', '1', '2', 'a')))
        self.assertIn(('GEN', '1', '2', 'a'), {ref})
        self.assertEqual(ref[0], 'GEN')
        BBB, C, V, S = ref
        self.assertEqual((BBB, C, V, S), ('GEN', '1', '2', 'a'))

    def test_named_fields_and_default_suffix(self) -> None:
        ref = VerseRef('PSA', '9', '22')
        self.assertEqual((ref.BBB, ref.C, ref.V, ref.S), ('PSA', '9', '22', None))

    def test_whole_verse(self) -> None:
        self.assertEqual(VerseRef('PSA', '9', '22', 'b').whole_verse(), VerseRef('PSA', '9', '22'))
        whole = VerseRef('PSA', '9', '22')
        self.assertIs(whole.whole_verse(), whole)

    def test_display_forms(self) -> None:
        self.assertEqual(str(VerseRef('GEN', '1', '1')), 'GEN 1:1')
        self.assertEqual(f"{VerseRef('PSA', '9', '22', 'a')}", 'PSA 9:22a')
        self.assertEqual(repr(VerseRef('GEN', '1', '1')), "VerseRef(BBB='GEN', C='1', V='1', S=None)")

    def test_pickles(self) -> None:
        ref = VerseRef('GEN', '1', '2', 'a')
        self.assertEqual(pickle.loads(pickle.dumps(ref)), ref)
        self.assertIsInstance(pickle.loads(pickle.dumps(ref)), VerseRef)


class MappingUsesVerseRefTests(unittest.TestCase):
    def test_normalize_reference_returns_verse_ref(self) -> None:
        ref = normalize_reference(('GEN', 1, 2, ''))
        self.assertIsInstance(ref, VerseRef)
        self.assertEqual(ref, ('GEN', '1', '2', None))

    def test_engine_results_are_verse_refs(self) -> None:
        result = get_default_mapping_engine().convert('eng', 'BOSReference', [('GEN', 31, 55)])
        single = result.require_single()
        self.assertIsInstance(single, VerseRef)
        self.assertEqual((single.BBB, single.C, single.V, single.S), ('GEN', '32', '1', None))
        self.assertTrue(all(isinstance(ref, VerseRef) for ref in result.source_references))

    def test_range_conversion_still_accepts_plain_tuples(self) -> None:
        result = get_default_mapping_engine().convert_range('eng', 'eng', ('GEN', 1, 1), ('GEN', 1, 3))
        self.assertEqual(result.references, (('GEN', '1', '1', None), ('GEN', '1', '2', None), ('GEN', '1', '3', None)))


class AdjacentAddressTests(unittest.TestCase):
    def setUp(self) -> None:
        from BibleOrgSys.Internals.InternalBiblePassages import _is_next_address
        self.follows = _is_next_address

    def test_next_whole_verse(self) -> None:
        self.assertTrue(self.follows(VerseRef('GEN', '1', '5'), VerseRef('GEN', '1', '6')))

    def test_next_segment_of_same_verse(self) -> None:
        self.assertTrue(self.follows(VerseRef('GEN', '1', '5', 'a'), VerseRef('GEN', '1', '5', 'b')))

    def test_rejects_gaps_reordering_and_boundaries(self) -> None:
        for previous, current in (
                (VerseRef('GEN', '1', '5'), VerseRef('GEN', '1', '7')),            # gap
                (VerseRef('GEN', '1', '6'), VerseRef('GEN', '1', '5')),            # reordered
                (VerseRef('GEN', '1', '5'), VerseRef('GEN', '2', '6')),            # new chapter
                (VerseRef('GEN', '1', '5'), VerseRef('EXO', '1', '6')),            # new book
                (VerseRef('GEN', '1', '5', 'a'), VerseRef('GEN', '1', '5', 'c')),  # skipped segment
                (VerseRef('GEN', '1', '5', 'a'), VerseRef('GEN', '1', '6')),       # segment to next verse
                (VerseRef('GEN', '1', '5'), VerseRef('GEN', '1', '5', 'b')),       # whole to segment
                (VerseRef('GEN', '1', '5', 'aa'), VerseRef('GEN', '1', '5', 'ab')),  # multi-letter segments
                ):
            with self.subTest(previous=previous, current=current):
                self.assertFalse(self.follows(previous, current))


if __name__ == '__main__':
    unittest.main()
