# SPDX-License-Identifier: MPL-2.0
"""Offline tests for relationship-preserving versification conversion.

The pure mapping engine needs only Python. Wrapper tests additionally require
BOS's normal installed dependencies; run this suite with .venv/bin/python to
exercise them. Existing historical count-system tests remain separate.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from BibleOrgSys.Reference.BibleVersificationMappings import (
    AmbiguousMappingError, InvalidReferenceError, MappingStatus, MultipleReferencesError,
    PartialMappingError, UnsupportedMappingError, UnknownVersificationSystemError,
    VersificationMappingEngine, get_default_mapping_engine, normalize_reference,
)


def ref(book='GEN', chapter=1, verse=1, suffix=None):
    return book, str(chapter), str(verse), suffix


def definition(**changes):
    return {'maxVerses': {'GEN': [6, 4], 'EXO': [6]}, **changes}


def engine(source=None, target=None, reference=None):
    systems = {'a': source if source is not None else definition(identityBooks={'GEN': 'GEN', 'EXO': 'EXO'})}
    if target is not None:
        systems['b'] = target
    return VersificationMappingEngine(reference or definition(), systems)


class RelationshipTests(unittest.TestCase):
    def test_identity_is_opt_in(self):
        result = engine(definition()).convert('a', 'BOSReference', [ref()])
        self.assertEqual(result.status, MappingStatus.UNSUPPORTED)
        self.assertEqual(result.references, ())
        self.assertEqual(engine().convert('a', 'BOSReference', [ref()]).require_single(), ref())

    def test_equal_ranges_expand_positionally(self):
        e = engine(definition(mappedVerses={'GEN 1:1-3': 'EXO 1:2-4'}))
        for v in range(1, 4):
            self.assertEqual(e.convert('a', 'BOSReference', [ref(verse=v)]).require_single(), ref('EXO', 1, v + 1))
            self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO', 1, v + 1)]).require_single(), ref(verse=v))

    def test_explicit_rules_replace_forward_identity(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, mappedVerses={'GEN 1:1': 'GEN 1:2'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).require_single(), ref(verse=2))
        self.assertEqual(e.convert('BOSReference', 'a', [ref()]).status, MappingStatus.UNSUPPORTED)

    def test_reverse_includes_implicit_identity_collision(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, mappedVerses={'GEN 1:1': 'GEN 1:2'}))
        result = e.convert('BOSReference', 'a', [ref(verse=2)])
        self.assertEqual(result.status, MappingStatus.AMBIGUOUS)
        self.assertEqual(set(result.alternatives), {(ref(),), (ref(verse=2),)})
        self.assertEqual(result.references, ())
        with self.assertRaises(AmbiguousMappingError) as error:
            result.require_single()
        self.assertIs(error.exception.result, result)

    def test_intentional_split_is_an_exact_group_not_alternatives(self):
        e = engine(definition(groupMappings=[{'source': 'GEN 1:1', 'target': 'EXO 1:1-2'}]))
        result = e.convert('a', 'BOSReference', [ref()])
        self.assertEqual(result.status, MappingStatus.EXACT)
        self.assertEqual(result.references, (ref('EXO'), ref('EXO', 1, 2)))
        self.assertEqual(result.alternatives, ())
        with self.assertRaises(MultipleReferencesError):
            result.require_single()

    def test_whole_split_group_can_be_inverted(self):
        e = engine(definition(groupMappings=[{'source': 'GEN 1:1', 'target': 'EXO 1:1-2'}]))
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO'), ref('EXO', 1, 2)]).require_single(), ref())
        result = e.convert('BOSReference', 'a', [ref('EXO')])
        self.assertEqual(result.status, MappingStatus.PARTIAL)
        self.assertEqual(result.references, ())
        with self.assertRaises(PartialMappingError):
            result.require_single()

    def test_whole_many_to_one_group_maps_without_guessing_parts(self):
        e = engine(definition(groupMappings=[{'source': 'GEN 1:1-2', 'target': 'EXO 1:1'}]))
        self.assertEqual(e.convert('a', 'BOSReference', [ref(), ref(verse=2)]).require_single(), ref('EXO'))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.PARTIAL)
        reverse = e.convert('BOSReference', 'a', [ref('EXO')])
        self.assertEqual(reverse.references, (ref(), ref(verse=2)))

    def test_many_to_many_group_is_not_a_cartesian_product(self):
        e = engine(definition(groupMappings=[{'source': 'GEN 1:1-2', 'target': 'EXO 1:1-3'}]))
        self.assertEqual(e.convert('a', 'BOSReference', [ref(), ref(verse=2)]).references,
                         (ref('EXO'), ref('EXO', 1, 2), ref('EXO', 1, 3)))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.PARTIAL)

    def test_unreviewed_unequal_ranges_do_not_become_verified_groups(self):
        e = engine(definition(identityBooks={'GEN': 'GEN', 'EXO': 'EXO'},
                              mappedVerses={'GEN 1:1-3': 'EXO 1:1'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref(), ref(verse=2), ref(verse=3)]).status,
                         MappingStatus.UNSUPPORTED)
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO')]).status, MappingStatus.UNSUPPORTED)

    def test_conflicting_overlap_returns_alternatives(self):
        e = engine(definition(mappedVerses={'GEN 1:1-2': 'EXO 1:1-2', 'GEN 1:2': 'EXO 1:3'}))
        result = e.convert('a', 'BOSReference', [ref(verse=2)])
        self.assertEqual(result.status, MappingStatus.AMBIGUOUS)
        self.assertEqual(set(result.alternatives), {(ref('EXO', 1, 2),), (ref('EXO', 1, 3),)})

    def test_duplicate_relationship_does_not_create_false_ambiguity(self):
        e = engine(definition(mappedVerses={'GEN 1:1-2': 'EXO 1:1-2', 'GEN 1:2': 'EXO 1:2'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref(verse=2)]).require_single(), ref('EXO', 1, 2))

    def test_multiple_exact_covers_preserve_distinct_groups(self):
        e = engine(definition(mappedVerses={'GEN 1:1-2': 'EXO 1:1-2'},
                              groupMappings=[{'source': 'GEN 1:1-2', 'target': 'EXO 1:3'}]))
        result = e.convert('a', 'BOSReference', [ref(), ref(verse=2)])
        self.assertEqual(result.status, MappingStatus.AMBIGUOUS)
        self.assertEqual(set(result.alternatives), {(ref('EXO'), ref('EXO', 1, 2)), (ref('EXO', 1, 3),)})

    def test_cross_system_composes_exact_groups(self):
        e = engine(definition(groupMappings=[{'source': 'GEN 1:1', 'target': 'EXO 1:1-2'}]),
                   definition(groupMappings=[{'source': 'GEN 2:1', 'target': 'EXO 1:1-2'}]))
        result = e.convert('a', 'b', [ref()])
        self.assertEqual(result.require_single(), ref('GEN', 2, 1))
        self.assertTrue(any(p.startswith('a:') for p in result.provenance))
        self.assertTrue(any(p.startswith('b:') for p in result.provenance))

    def test_cross_system_preserves_ambiguous_intermediate_even_if_outputs_converge(self):
        e = engine(definition(mappedVerses={'GEN 1:1-2': 'EXO 1:1-2', 'GEN 1:2': 'EXO 1:3'}),
                   definition(mappedVerses={'GEN 1:1-2': 'EXO 1:1-2', 'GEN 1:2': 'EXO 1:3'}))
        result = e.convert('a', 'b', [ref(verse=2)])
        self.assertEqual(result.status, MappingStatus.AMBIGUOUS)
        self.assertEqual(result.alternatives, ((ref(verse=2),),))

    def test_failed_alternative_cannot_be_filtered_into_an_exact_answer(self):
        e = engine(definition(mappedVerses={'GEN 1:1-2': 'EXO 1:1-2', 'GEN 1:2': 'EXO 1:3'}),
                   definition(mappedVerses={'GEN 2:1': 'EXO 1:2'}))
        result = e.convert('a', 'b', [ref(verse=2)])
        self.assertEqual(result.status, MappingStatus.PARTIAL)
        self.assertEqual(result.references, ())
        self.assertEqual(result.alternatives, ((ref('GEN', 2, 1),),))

    def test_partially_mapped_passage_never_silently_drops_missing_references(self):
        e = engine(definition(mappedVerses={'GEN 1:1': 'EXO 1:1'}))
        result = e.convert('a', 'BOSReference', [ref(), ref(verse=2)])
        self.assertEqual(result.status, MappingStatus.PARTIAL)
        self.assertEqual(result.references, ())
        self.assertTrue(result.diagnostics)

    def test_reordering_and_discontinuous_output_preserve_input_passage_order(self):
        e = engine(definition(mappedVerses={'GEN 1:1': 'EXO 1:4', 'GEN 1:2': 'EXO 1:1'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref(), ref(verse=2)]).references,
                         (ref('EXO', 1, 4), ref('EXO')))

    def test_duplicate_inputs_are_stably_deduplicated(self):
        self.assertEqual(engine().convert('a', 'BOSReference', [ref(), ref(), ref(verse=2)]).references,
                         (ref(), ref(verse=2)))

    def test_same_system_validates_identity_without_a_reference_round_trip(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, mappedVerses={'GEN 1:1': 'GEN 1:2'}))
        self.assertEqual(e.convert('a', 'a', [ref()]).references, (ref(),))

    def test_results_and_definition_inputs_are_isolated(self):
        d = definition(identityBooks={'GEN': 'GEN'})
        e = engine(d)
        d['identityBooks'].clear()
        result = e.convert('a', 'BOSReference', [ref()])
        self.assertEqual(result.require_single(), ref())
        with self.assertRaises(FrozenInstanceError):
            result.status = MappingStatus.UNSUPPORTED

    def test_same_system_identity_still_validates_native_addresses(self):
        e = engine(definition(excludedVerses=['GEN 1:2']))
        for reference, code in ((ref(verse=9), 'OUTSIDE_SYSTEM'), (ref(verse=0), 'UNDECLARED_TITLE'),
                                (ref(suffix='a'), 'UNDECLARED_SEGMENT'), (ref(verse=2), 'EXCLUDED_VERSE')):
            with self.subTest(reference=reference):
                result = e.convert('a', 'a', [reference])
                self.assertNotEqual(result.status, MappingStatus.EXACT)
                self.assertIn(code, [d.code for d in result.diagnostics])

    def test_complete_group_expansion_on_either_leg_and_cascading_groups(self):
        e = engine(definition(groupMappings=[{'source':['GEN 1:1','GEN 2:2'], 'target':'GEN 1:1'},
                                             {'source':'GEN 1:3', 'target':'GEN 1:2'}]),
                   definition(groupMappings=[{'source':['GEN 1:4','GEN 2:1'], 'target':'GEN 1:1-2'}]))
        result = e.convert_passage('a','b',[ref('GEN',2,2)])
        self.assertEqual(result.status, MappingStatus.EXACT)
        self.assertTrue(result.is_expanded)
        self.assertEqual(result.requested_references, (ref('GEN',2,2),))
        self.assertEqual(result.source_references, (ref(),ref('GEN',2,2),ref(verse=3)))
        self.assertEqual(result.references, (ref(verse=4),ref('GEN',2,1)))
        self.assertEqual(e.convert('a','b',[ref('GEN',2,2)]).status, MappingStatus.PARTIAL)

    def test_expansion_never_unions_competing_groups_or_fills_unmapped_gaps(self):
        e = engine(definition(groupMappings=[{'source':'GEN 1:1-2','target':'GEN 1:1'},
                                             {'source':'GEN 1:1-3','target':'GEN 1:2'}]))
        result = e.convert_passage('a','BOSReference',[ref()])
        self.assertEqual(result.status, MappingStatus.AMBIGUOUS)
        self.assertFalse(result.references)
        e = engine(definition(mappedVerses={'GEN 1:1':'GEN 1:1'}))
        self.assertEqual(e.convert_passage('a','BOSReference',[ref(),ref(verse=2)]).status, MappingStatus.PARTIAL)

    def test_expansion_respects_merged_domains_and_explicit_suffixes(self):
        e = engine(definition(identityBooks={'GEN':'GEN'},mergedVerses=['GEN 1:1-2']))
        for source,target in (('a','BOSReference'),('BOSReference','a')):
            result = e.convert_passage(source,target,[ref(verse=2)])
            self.assertEqual(result.status, MappingStatus.EXACT)
            self.assertEqual(result.source_references, (ref(),ref(verse=2)))
        e = engine(definition(partialVerses={'GEN 1:1':['a','b']},
            groupMappings=[{'source':['GEN 1:1a','GEN 1:1b'],'target':'GEN 1:2'}]))
        result = e.convert_passage('a','BOSReference',[ref(suffix='b')])
        self.assertEqual(result.source_references, (ref(suffix='a'),ref(suffix='b')))
        self.assertEqual(result.references, (ref(verse=2),))
        self.assertNotEqual(e.convert_passage('a','BOSReference',[ref()]).status, MappingStatus.EXACT)

    def test_many_alternatives_are_bounded_but_never_reported_exact(self):
        # Two choices per verse yield 128 complete passage interpretations.
        d = {'maxVerses': {'GEN': [7]},
             'mappedVerses': {'GEN 1:1-7': 'EXO 1:1-7'},
             'groupMappings': [{'source': f'GEN 1:{v}', 'target': f'EXO 1:{v+7}'} for v in range(1, 8)]}
        e = engine(d, reference={'maxVerses': {'EXO': [14]}})
        result = e.convert('a', 'BOSReference', [ref(verse=v) for v in range(1, 8)])
        self.assertEqual(result.status, MappingStatus.AMBIGUOUS)
        self.assertEqual(len(result.alternatives), 64)
        self.assertIn('ALTERNATIVE_LIMIT', {d.code for d in result.diagnostics})

    def test_range_crossing_chapters_is_mapped_as_one_passage(self):
        e = engine()
        result = e.convert_range('a', 'BOSReference', ref(verse=6), ref('GEN', 2, 2))
        self.assertEqual(result.references, (ref(verse=6), ref('GEN', 2, 1), ref('GEN', 2, 2)))

    def test_range_preserves_group_boundaries(self):
        e = engine(definition(groupMappings=[{'source': 'GEN 1:1-2', 'target': 'EXO 1:1'}]))
        self.assertEqual(e.convert_range('a', 'BOSReference', ref(), ref(verse=2)).require_single(), ref('EXO'))

    def test_range_does_not_silently_skip_excluded_verses(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, excludedVerses=['GEN 1:2']))
        self.assertEqual(e.convert_range('a', 'BOSReference', ref(), ref(verse=3)).status, MappingStatus.UNSUPPORTED)

    def test_invalid_and_underspecified_ranges_are_explicit(self):
        for start, end in [(ref(verse=3), ref()), (ref(), ref('EXO')), (ref(), ref(suffix='b')),
                           (ref(), ref(verse=99)), (ref(), ('GEN', True, 1))]:
            with self.subTest(start=start, end=end):
                self.assertEqual(engine().convert_range('a', 'BOSReference', start, end).status, MappingStatus.INVALID)


class InvalidAndIncompleteDataTests(unittest.TestCase):
    def test_reversed_source_range_blocks_whole_chapter_and_reverse_destination(self):
        e = engine(definition(identityBooks={'GEN': 'GEN', 'EXO': 'EXO'},
                              mappedVerses={'GEN 1:5-2': 'EXO 1:1'}))
        for verse in range(1, 7):
            self.assertEqual(e.convert('a', 'BOSReference', [ref(verse=verse)]).status, MappingStatus.UNSUPPORTED)
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO')]).status, MappingStatus.UNSUPPORTED)
        self.assertEqual(e.convert('a', 'BOSReference', [ref('GEN', 2, 1)]).require_single(), ref('GEN', 2, 1))

    def test_reversed_destination_blocks_inverse_chapter(self):
        e = engine(definition(identityBooks={'GEN': 'GEN', 'EXO': 'EXO'},
                              mappedVerses={'GEN 1:1': 'EXO 1:5-2'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO', 1, 6)]).status, MappingStatus.UNSUPPORTED)

    def test_malformed_scopes_also_block_otherwise_valid_inverse_identities(self):
        e = engine(definition(identityBooks={'GEN': 'GEN', 'EXO': 'EXO'},
                              mappedVerses={'GEN 1:5-2': 'EXO 1:1'}))
        self.assertEqual(e.convert('BOSReference', 'a', [ref(verse=3)]).status, MappingStatus.UNSUPPORTED)
        e = engine(definition(identityBooks={'GEN': 'GEN', 'EXO': 'EXO'},
                              mappedVerses={'GEN 1:1': 'EXO 1:5-2'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref('EXO', 1, 3)]).status, MappingStatus.UNSUPPORTED)

    def test_quarantine_propagates_through_connected_alternatives(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'},
                              mappedVerses={'GEN 1:6-7': 'EXO 1:1-2', 'GEN 1:1': 'EXO 1:1'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)

    def test_non_string_rule_is_quarantined_without_a_parser_crash(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, mappedVerses={'GEN 1:1': None}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)
        self.assertEqual(e.convert('BOSReference', 'a', [ref()]).status, MappingStatus.UNSUPPORTED)

    def test_bad_source_segment_cannot_hide_behind_a_whole_verse_rule(self):
        e = engine(definition(mappedVerses={'GEN 1:1': 'EXO 1:1', 'GEN 1:1a': 'EXO 1:2'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)

    def test_out_of_bounds_rule_is_blocked_in_both_directions(self):
        e = engine(definition(identityBooks={'EXO': 'EXO'}, mappedVerses={'GEN 1:6-7': 'EXO 1:1-2'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref(verse=6)]).status, MappingStatus.UNSUPPORTED)
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO')]).status, MappingStatus.UNSUPPORTED)

    def test_missing_destination_book_does_not_return_unchanged_source(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, mappedVerses={'GEN 1:1': 'MAT 1:1'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)

    def test_excluded_verses_are_explicit(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, excludedVerses=['GEN 1:2']))
        result = e.convert('a', 'BOSReference', [ref(verse=2)])
        self.assertEqual(result.status, MappingStatus.UNSUPPORTED)
        self.assertIn('EXCLUDED_VERSE', {d.code for d in result.diagnostics})
        self.assertEqual(e.convert('BOSReference', 'a', [ref(verse=2)]).status, MappingStatus.UNSUPPORTED)

    def test_explicit_rule_cannot_reintroduce_excluded_verse(self):
        e = engine(definition(mappedVerses={'GEN 1:2': 'EXO 1:1'}, excludedVerses=['GEN 1:2']))
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO')]).status, MappingStatus.UNSUPPORTED)

    def test_source_and_target_merged_verses_require_complete_groups(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, mergedVerses=['GEN 1:1-2']))
        for source, target in [('a', 'BOSReference'), ('BOSReference', 'a')]:
            with self.subTest(source=source):
                self.assertEqual(e.convert(source, target, [ref()]).status, MappingStatus.PARTIAL)
                self.assertEqual(e.convert(source, target, [ref(), ref(verse=2)]).references, (ref(), ref(verse=2)))

    def test_merged_reference_is_also_respected(self):
        e = engine(reference=definition(mergedVerses=['GEN 1:1-2']))
        for source, target in [('a', 'BOSReference'), ('BOSReference', 'a')]:
            self.assertEqual(e.convert(source, target, [ref()]).status, MappingStatus.PARTIAL)

    def test_known_title_is_supported_but_arbitrary_zero_is_not(self):
        e = engine(definition(verseZeroReferences=['GEN 1:0'], mappedVerses={'GEN 1:0': 'EXO 1:1'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref(verse=0)]).require_single(), ref('EXO'))
        self.assertEqual(e.convert('a', 'BOSReference', [ref('GEN', 2, 0)]).status, MappingStatus.UNSUPPORTED)

    def test_valid_suffixes_remain_suffixes(self):
        e = engine(definition(partialVerses={'GEN 1:1': ['a', 'b']}, mappedVerses={'GEN 1:1a': 'EXO 1:1b'}),
                   reference=definition(partialVerses={'EXO 1:1': ['a', 'b']}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref(suffix='a')]).require_single(), ref('EXO', 1, 1, 'b'))
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO', 1, 1, 'b')]).require_single(), ref(suffix='a'))

    def test_arbitrary_suffix_is_not_copied_through_a_whole_verse_mapping(self):
        self.assertEqual(engine().convert('a', 'BOSReference', [ref(suffix='a')]).status, MappingStatus.UNSUPPORTED)

    def test_undeclared_target_suffix_quarantines_whole_verse_inverse(self):
        e = engine(definition(identityBooks={'EXO': 'EXO'}, mappedVerses={'GEN 1:1': 'EXO 1:1a'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO')]).status, MappingStatus.UNSUPPORTED)

    def test_segment_mapping_does_not_imply_whole_verse_identity(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, partialVerses={'GEN 1:1': ['a']},
                              mappedVerses={'GEN 1:1a': 'EXO 1:1'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)

    def test_segment_range_is_not_guessed(self):
        e = engine(definition(identityBooks={'GEN': 'GEN'}, mappedVerses={'GEN 1:1a-1c': 'EXO 1:1-3'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)

    def test_restriction_blocks_cross_book_rule_in_reverse(self):
        e = engine(definition(unsupportedBooks={'GEN': 'Different textual tradition'},
                              mappedVerses={'GEN 1:1': 'EXO 1:1'}))
        self.assertEqual(e.convert('BOSReference', 'a', [ref('EXO')]).status, MappingStatus.UNSUPPORTED)

    def test_unresolved_inheritance_cannot_silently_be_ignored(self):
        e = engine(definition(basedOn='parent', identityBooks={'GEN': 'GEN'}))
        self.assertEqual(e.convert('a', 'BOSReference', [ref()]).status, MappingStatus.UNSUPPORTED)
        self.assertEqual(e.capabilities('a')['status'], 'unsupported')

    def test_invalid_inputs_return_diagnostics_and_raise_in_strict_mode(self):
        for refs in [[], [ref('XXX')], [ref(verse=7)], [('GEN', True, 1)], [('GEN', -1, 1)],
                     [('GEN', 0, 1)], [('GEN', '1', '1-2')], [('GEN', 1, 1, 'A')], None,
                     [ref(), ref(suffix='a')]]:
            with self.subTest(refs=refs):
                result = engine().convert('a', 'BOSReference', refs)
                self.assertEqual(result.status, MappingStatus.INVALID)
                with self.assertRaises(InvalidReferenceError):
                    result.require_single()

    def test_unknown_profile_has_no_identity_fallback(self):
        result = engine().convert('no-such-system', 'BOSReference', [ref()])
        self.assertEqual(result.status, MappingStatus.UNSUPPORTED)
        with self.assertRaises(UnsupportedMappingError):
            result.require_single()

    def test_normalization_accepts_ints_and_empty_suffixes(self):
        self.assertEqual(normalize_reference(('GEN', 1, 2, '')), ref(verse=2))
        self.assertEqual(normalize_reference(('GEN', '01', '002')), ref(verse=2))


class BundledMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = get_default_mapping_engine()

    def test_genesis_boundary_and_inverse(self):
        self.assertEqual(self.engine.convert('eng', 'BOSReference', [ref('GEN', 31, 55)]).require_single(), ref('GEN', 32, 1))
        self.assertEqual(self.engine.convert('BOSReference', 'eng', [ref('GEN', 32, 1)]).require_single(), ref('GEN', 31, 55))

    def test_psalm_title_and_cross_system_conversion(self):
        self.assertEqual(self.engine.convert('eng', 'BOSReference', [ref('PSA', 3, 0)]).require_single(), ref('PSA', 3, 1))
        self.assertEqual(self.engine.convert('eng', 'lxx', [ref('PSA', 3, 0)]).require_single(), ref('PSA', 3, 1))

    def test_lxx_daniel_crosses_book_codes(self):
        self.assertEqual(self.engine.convert('lxx', 'BOSReference', [ref('DNG', 2, 1)]).require_single(), ref('DAN', 2, 1))
        result = self.engine.convert('BOSReference', 'lxx', [ref('DAN', 2, 1)])
        self.assertIn((ref('DNG', 2, 1),), result.alternatives or (result.references,))

    def test_combined_lxx_ezra_uses_source_identity(self):
        self.assertEqual(self.engine.convert('lxx', 'BOSReference', [ref('EZN', 1, 1)]).require_single(), ref('EZR', 1, 1))
        self.assertEqual(self.engine.convert('lxx', 'BOSReference', [ref('EZN', 11, 1)]).require_single(), ref('NEH', 1, 1))

    def test_lxx_reordered_exodus(self):
        self.assertEqual(self.engine.convert('lxx', 'BOSReference', [ref('EXO', 36, 9)]).require_single(), ref('EXO', 39, 2))

    def test_deuterocanonical_identity_within_documented_delta_definition(self):
        self.assertEqual(self.engine.convert('lxx', 'BOSReference', [ref('WIS')]).require_single(), ref('WIS'))

    def test_latin_native_extension_is_explicitly_supported(self):
        self.assertEqual(self.engine.convert('vul', 'BOSReference', [ref('LAO')]).require_single(), ref('LAO'))
        self.assertEqual(self.engine.convert('BOSReference', 'vul', [ref('LAO')]).require_single(), ref('LAO'))
        self.assertEqual(self.engine.convert('eng', 'BOSReference', [ref('LAO')]).status, MappingStatus.UNSUPPORTED)

    def test_vulgate_textual_traditions_remain_unsupported_in_both_directions(self):
        for book in ('TOB', 'JDT', 'SIR'):
            for source, target in [('vul', 'BOSReference'), ('BOSReference', 'vul'), ('eng', 'vul')]:
                with self.subTest(book=book, source=source):
                    self.assertEqual(self.engine.convert(source, target, [ref(book)]).status, MappingStatus.UNSUPPORTED)

    def test_real_russian_overlap_is_ambiguous_not_a_split(self):
        result = self.engine.convert('rsc', 'BOSReference', [ref('PSA', 9, 22)])
        self.assertEqual(result.status, MappingStatus.AMBIGUOUS)
        self.assertEqual(set(result.alternatives), {(ref('PSA', 10, 0),), (ref('PSA', 10, 1),)})

    def test_cross_system_ambiguity_does_not_prevent_native_identity(self):
        self.assertEqual(self.engine.convert('rsc', 'rsc', [ref('PSA', 9, 22)]).references, (ref('PSA', 9, 22),))

    def test_unresolved_additions_and_ethiopian_books_are_explicit(self):
        for source, target, reference in [('org', 'BOSReference', ref('PAZ')), ('eng', 'BOSReference', ref('ESG')),
                                         ('vul', 'BOSReference', ref('DNG', 3, 52)),
                                         ('ethiopian_custom', 'BOSReference', ref('GEN')),
                                         ('BOSReference', 'org', ref('DNG')),
                                         ('BOSReference', 'BOSReference', ref('EZ6'))]:
            with self.subTest(source=source, reference=reference):
                result = self.engine.convert(source, target, [reference])
                self.assertEqual(result.status, MappingStatus.UNSUPPORTED)
                self.assertTrue(result.diagnostics)

    def test_historical_system_names_are_not_unverified_aliases(self):
        for legacy in ('Original', 'KJV', 'Septuagint', 'Vulgate', 'BibMaxRef'):
            with self.subTest(legacy=legacy):
                self.assertEqual(self.engine.convert(legacy, 'eng', [ref()]).status, MappingStatus.UNSUPPORTED)

    def test_explicit_composition_agrees_on_exact_passages(self):
        for source, target, reference in [('eng', 'lxx', ref('GEN', 31, 55)),
                                         ('lxx', 'eng', ref('DNG', 2, 1)), ('vul', 'eng', ref('GEN'))]:
            first = self.engine.convert(source, 'BOSReference', [reference])
            self.assertEqual(first.status, MappingStatus.EXACT)
            second = self.engine.convert('BOSReference', target, first.references)
            combined = self.engine.convert(source, target, [reference])
            self.assertEqual((combined.status, combined.references, combined.alternatives),
                             (second.status, second.references, second.alternatives))

    def test_reference_identity_and_result_provenance(self):
        result = self.engine.convert('BOSReference', 'BOSReference', [ref()])
        self.assertEqual(result.require_single(), ref())
        self.assertEqual(result.reference_version, '1-draft')
        self.assertRegex(result.data_revision, r'^519af776ab65d89a51e37f750779250f940459ef\+bos-supplement-2\.[0-9a-f]{64}$')
        self.assertEqual(result.mapping_policy_version, '3')


@unittest.skipUnless(importlib.util.find_spec('bos_books_codes_py') and importlib.util.find_spec('bible_organisational_system'),
                     'BOS wrapper tests require its installed native dependencies; use .venv/bin/python.')
class PublicAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem, BibleVersificationSystems
        cls.system = staticmethod(BibleVersificationSystem)
        cls.registry = BibleVersificationSystems().loadData()

    def test_registry_contains_new_and_historical_names(self):
        for name in ('BOSReference', 'org', 'eng', 'lxx', 'vul', 'rsc', 'rso', 'ethiopian_custom', 'KJV', 'Original'):
            self.assertIn(name, self.registry)
        self.assertEqual(set(self.registry.getVersificationSystem('eng')), {'CV', 'omitted', 'combined', 'reordered'})

    def test_registry_also_registers_mappings_when_loading_xml(self):
        from BibleOrgSys import BibleOrgSysGlobals
        from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystems
        registry = BibleVersificationSystems().loadData(BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH / 'VersificationSystems')
        self.assertIn('eng', registry)
        self.assertIn('KJV', registry)

    def test_registry_also_registers_mappings_from_json_without_pickle_or_xml(self):
        from BibleOrgSys import BibleOrgSysGlobals
        from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystems
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            filename = 'BibleVersificationSystems_Tables.json'
            shutil.copyfile(BibleOrgSysGlobals.BOS_DERIVED_DATAFILES_FOLDERPATH / filename, data / filename)
            with patch.object(BibleOrgSysGlobals, 'BOS_DATAFILES_FOLDERPATH', data), \
                 patch.object(BibleOrgSysGlobals, 'BOS_DERIVED_DATAFILES_FOLDERPATH', data):
                registry = BibleVersificationSystems().loadData()
            self.assertIn('eng', registry)
            self.assertIn('KJV', registry)

    def test_documented_python_examples(self):
        guide = Path(__file__).resolve().parents[1] / 'Documentation/VersificationMappingAPI.md'
        namespace = {}
        for index, example in enumerate(re.findall(r'```python\n(.*?)```', guide.read_text(), re.DOTALL)):
            with self.subTest(example=index):
                exec(compile(example, str(guide), 'exec'), namespace)

    def test_count_methods_work_for_reference_and_source_systems(self):
        self.assertEqual(self.system('eng').getNumChapters('GEN'), 50)
        self.assertEqual(self.system('BOSReference').getNumVerses('LAO', '1'), 20)
        self.assertEqual(self.system('lxx').getNumChapters('EZN'), 23)
        self.assertEqual(self.system('KJV').getNumChapters('GEN'), 50)

    def test_to_and_from_reference_use_four_tuple_compatibility(self):
        english = self.system('eng')
        self.assertEqual(english.convertToReferenceVersification('GEN', 31, 55), ref('GEN', 32, 1))
        self.assertEqual(english.convertFromReferenceVersification('GEN', 32, 1), ref('GEN', 31, 55))

    def test_system_to_system_accepts_name_or_object(self):
        english = self.system('eng')
        for target in ('lxx', self.system('lxx')):
            self.assertEqual(english.convertToVersification(target, 'GEN', 31, 55), ref('GEN', 32, 1))

    def test_ambiguity_is_structured_or_raises_with_result(self):
        russian = self.system('rsc')
        result = russian.convertToReferenceVersification('PSA', 9, 22, detailed=True)
        self.assertEqual(result.status, MappingStatus.AMBIGUOUS)
        with self.assertRaises(AmbiguousMappingError):
            russian.convertToReferenceVersification('PSA', 9, 22)

    def test_unsupported_historical_counts_no_longer_echo_input(self):
        kjv = self.system('KJV')
        with self.assertRaises(UnsupportedMappingError):
            kjv.convertToReferenceVersification('GEN', 1, 1)
        self.assertEqual(kjv.getMappingCapabilities()['status'], 'unsupported')
        self.assertEqual(self.system('eng').getMappingCapabilities()['status'], 'partial')

    def test_plural_api_returns_complete_passage(self):
        result = self.system('eng').convertReferencesToVersification('BOSReference',
                            [ref('GEN', 31, 55), ref('GEN', 32, 1)])
        self.assertEqual(result.references, (ref('GEN', 32, 1), ref('GEN', 32, 2)))

    def test_unknown_constructor_is_explicit(self):
        with self.assertLogs(level='ERROR'), self.assertRaises(UnknownVersificationSystemError):
            self.system('nonexistent')

    def test_range_api_accepts_a_target_object(self):
        result = self.system('eng').convertRangeToVersification(self.system('BOSReference'),
                           ref('GEN', 31, 55), ref('GEN', 32, 1))
        self.assertEqual(result.references, (ref('GEN', 32, 1), ref('GEN', 32, 2)))


class DistributionTests(unittest.TestCase):
    def test_engine_works_from_zip_without_native_modules_or_repository(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'mapping.zip'
            paths = ['BibleOrgSys/__init__.py', 'BibleOrgSys/Reference/__init__.py',
                     'BibleOrgSys/Reference/Converters/__init__.py',
                     'BibleOrgSys/Reference/Converters/BibleVersificationMappingsConverter.py',
                     'BibleOrgSys/Reference/BibleVersificationMappings.py']
            paths += [p.relative_to(root).as_posix() for p in (root / 'BibleOrgSys/DataFiles/VersificationMappings').rglob('*') if p.is_file()]
            with zipfile.ZipFile(archive, 'w') as output:
                for path in paths:
                    output.write(root / path, path)
            code = ('import sys; sys.path.insert(0,sys.argv[1]); '
                    'from BibleOrgSys.Reference.BibleVersificationMappings import get_default_mapping_engine; '
                    'e=get_default_mapping_engine(); '
                    'assert e.convert("eng","BOSReference",[("GEN",31,55)]).require_single()==("GEN","32","1",None); '
                    'assert e.convert("eng","org",[("NUM",26,1)]).references==(("NUM","25","19",None),("NUM","26","1",None)); '
                    'assert e.convert("eng","org",[("PSA",60,0)]).references==(("PSA","60","1",None),("PSA","60","2",None)); '
                    'assert "bos_books_codes_py" not in sys.modules')
            result = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(archive)], cwd=temporary,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
