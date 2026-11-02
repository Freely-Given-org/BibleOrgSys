# SPDX-License-Identifier: MPL-2.0
"""Reviewed English/Hebrew group corrections and compiled coverage regression tests.

The expected correspondences below are independent of the supplement loader.
No external Bible checkout, internet connection, or sniffing program is used.
Native integration tests use small temporary USFM texts with distinguishable
content in each member, so missing text is observable as well as missing addresses.
"""

from copy import deepcopy
import importlib.util
import logging
from pathlib import Path
import tempfile
import unittest

from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingStatus, MultipleReferencesError, PartialMappingError,
    VersificationMappingEngine, get_default_mapping_engine,
)
from BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter import (
    VersificationDataError, load_bundle, parse_reference_span,
)


def ref(book, chapter, verse):
    return book, str(chapter), str(verse), None


CASES = (
    (ref('NUM', 26, 1), (ref('NUM', 25, 19), ref('NUM', 26, 1))),
    (ref('SA1', 20, 42), (ref('SA1', 20, 42), ref('SA1', 21, 1))),
    (ref('KI1', 22, 43), (ref('KI1', 22, 43), ref('KI1', 22, 44))),
    (ref('CH1', 12, 4), (ref('CH1', 12, 4), ref('CH1', 12, 5))),
    *((ref('PSA', c, 0), (ref('PSA', c, 1), ref('PSA', c, 2))) for c in (51, 52, 54, 60)),
)


class SupplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = get_default_mapping_engine()
        cls.bundle = load_bundle()

    def test_all_eight_complete_groups_in_both_directions(self):
        for english, hebrew in CASES:
            for reference_system in ('org', 'BOSReference'):
                with self.subTest(english=english, system=reference_system):
                    result = self.engine.convert('eng', reference_system, [english])
                    self.assertEqual(result.status, MappingStatus.EXACT)
                    self.assertEqual(result.references, hebrew)
                    self.assertEqual(result.alternatives, ())
                    self.assertTrue(any('BOS supplement eng-' in p for p in result.provenance))
                    with self.assertRaises(MultipleReferencesError):
                        result.require_single()
                    self.assertEqual(self.engine.convert(reference_system, 'eng', hebrew).require_single(), english)
                    self.assertEqual(self.engine.convert('eng', 'eng', [english]).require_single(), english)

    def test_either_half_remains_partial_including_the_previously_exact_half(self):
        for english, hebrew in CASES:
            for part in hebrew:
                for source in ('org', 'BOSReference'):
                    with self.subTest(english=english, part=part, source=source):
                        result = self.engine.convert(source, 'eng', [part])
                        self.assertEqual(result.status, MappingStatus.PARTIAL)
                        self.assertEqual(result.references, ())
                        self.assertIn('INCOMPLETE_MAPPING_GROUP', {d.code for d in result.diagnostics})
                        with self.assertRaises(PartialMappingError):
                            result.require_single()

    def test_ranges_and_group_with_following_verse_do_not_duplicate_or_drop_members(self):
        for english, hebrew in CASES:
            with self.subTest(english=english):
                ranged = self.engine.convert_range('org', 'eng', hebrew[0], hebrew[-1])
                self.assertEqual(ranged.require_single(), english)
                # Samuel's next English verse begins a new chapter.
                following_english = ref('SA1', 21, 1) if english[0] == 'SA1' else ref(
                    english[0], english[1], int(english[2]) + 1)
                following_hebrew = ref(hebrew[-1][0], hebrew[-1][1], int(hebrew[-1][2]) + 1)
                forward = self.engine.convert('eng', 'org', [english, following_english])
                self.assertEqual(forward.status, MappingStatus.EXACT)
                self.assertEqual(forward.references, hebrew + (following_hebrew,))
                self.assertEqual(self.engine.convert('org', 'eng', forward.references).references,
                                 (english, following_english))

    def test_replaced_ranges_preserve_all_surrounding_number_shifts(self):
        checks = [(ref('NUM', 25, 18), ref('NUM', 25, 18)),
                  (ref('SA1', 20, 41), ref('SA1', 20, 41)),
                  (ref('KI1', 22, 42), ref('KI1', 22, 42)),
                  (ref('CH1', 12, 3), ref('CH1', 12, 3))]
        checks += [(ref('KI1', 22, v), ref('KI1', 22, v+1)) for v in range(44, 54)]
        checks += [(ref('CH1', 12, v), ref('CH1', 12, v+1)) for v in range(5, 41)]
        checks += [(ref('PSA', c, v), ref('PSA', c, v+2))
                   for c, last in ((51, 19), (52, 9), (54, 7), (60, 12)) for v in range(1, last+1)]
        for english, hebrew in checks:
            with self.subTest(english=english):
                self.assertEqual(self.engine.convert('eng', 'org', [english]).require_single(), hebrew)
                self.assertEqual(self.engine.convert('org', 'eng', [hebrew]).require_single(), english)

    def test_compiled_audit_detects_all_eight_original_gaps_and_their_resolution(self):
        before = deepcopy(self.bundle)
        before['supplement']['corrections'] = before['supplement']['corrections'][8:]
        original = VersificationMappingEngine.from_bundled_data(bundle=before).audit_reference_coverage('eng')
        corrected = self.engine.audit_reference_coverage('eng')

        def missing(coverage):
            return {p for b in coverage['books'].values() for r in b['unmappedRanges']
                    for p in parse_reference_span(r).points()}

        expected = {f'{group[0][0]} {group[0][1]}:{group[0][2]}' for _, group in CASES}
        self.assertEqual(missing(original) - missing(corrected), expected)
        self.assertEqual(missing(corrected) - missing(original), set())
        self.assertEqual(original['unmappedCount'] - corrected['unmappedCount'], 8)
        self.assertEqual(corrected['representedCount'] - original['representedCount'], 8)
        for book in ('NUM', 'SA1', 'KI1', 'CH1'):
            self.assertEqual(corrected['books'][book]['unmappedCount'], 0)
        self.assertGreater(corrected['blockedCount'], 0)  # Other unresolved bridges remain explicit.

    def test_supplement_preserves_raw_sources_and_has_pinned_evidence_for_every_correction(self):
        before = deepcopy(self.bundle)
        VersificationMappingEngine.from_bundled_data(bundle=self.bundle)
        self.assertEqual(before, self.bundle)
        self.assertEqual(len(self.bundle['supplement']['corrections']), 56)
        self.assertEqual(self.bundle['systems']['eng']['mappedVerses']['PSA 51:0'], 'PSA 51:2')
        self.assertEqual(self.bundle['supplement']['dataLicense'], 'CC-BY-SA-4.0')
        evidence = {row['name']: row for row in self.bundle['supplementEvidence']}
        for correction in self.bundle['supplement']['corrections']:
            self.assertTrue(correction['evidence']['verification'])
            row = evidence[correction['evidence']['copenhagenRule']]
            self.assertIn(next(iter(row['ranges'][correction['evidence']['copenhagenRangeIndex']])),
                          ('SubdividedVerse', 'MergedVerses'))

    def test_stale_conflicting_or_unsubstantiated_corrections_are_rejected(self):
        def check(change, message):
            bundle = deepcopy(self.bundle)
            change(bundle)
            with self.assertRaisesRegex(VersificationDataError, message):
                VersificationMappingEngine.from_bundled_data(bundle=bundle)

        check(lambda b: b['systems']['eng']['mappedVerses'].__setitem__('1SA 20:42', '1SA 20:41'), 'Stale')
        check(lambda b: b['supplement'].__setitem__('sourceSnapshot', 'other'), 'snapshot')
        check(lambda b: b['supplement']['corrections'][2]['remainingMappings'].clear(), 'unaffected')
        check(lambda b: b['supplement']['corrections'][0].__setitem__('target', ['NUM 99:1']), 'endpoint')
        check(lambda b: b['supplement']['corrections'][0]['evidence'].__setitem__('copenhagenRule', 'unknown'), 'evidence')
        check(lambda b: b['supplement']['corrections'].append(deepcopy(b['supplement']['corrections'][0])), 'Duplicate')
        check(lambda b: b['systems']['eng']['mappedVerses'].__setitem__('NUM 26:1', 'NUM 26:1'), 'overlaps')

    def test_supplement_content_changes_result_revision_even_if_version_is_not_bumped(self):
        changed = deepcopy(self.bundle)
        changed['supplement']['corrections'][0]['reason'] += ' Additional verification.'
        other = VersificationMappingEngine.from_bundled_data(bundle=changed)
        self.assertNotEqual(other.data_revision, self.engine.data_revision)
        self.assertEqual(self.engine.reference_version, '1-draft')


class ExplicitGroupAndAuditTests(unittest.TestCase):
    def test_lists_preserve_order_and_can_cross_books_on_either_side(self):
        counts = {'GEN': [2, 2], 'EXO': [2]}
        engine = VersificationMappingEngine({'maxVerses': counts}, {'custom': {
            'maxVerses': counts,
            'groupMappings': [{'source': ['GEN 1:2', 'GEN 2:1'], 'target': ['EXO 1:2', 'GEN 1:1']}],
        }})
        result = engine.convert('custom', 'BOSReference', [ref('GEN', 1, 2), ref('GEN', 2, 1)])
        self.assertEqual(result.references, (ref('EXO', 1, 2), ref('GEN', 1, 1)))
        inverse = engine.convert('BOSReference', 'custom', result.references)
        self.assertEqual(inverse.references, (ref('GEN', 1, 2), ref('GEN', 2, 1)))
        self.assertEqual(engine.convert('custom', 'BOSReference', [ref('GEN', 1, 2)]).status, MappingStatus.PARTIAL)

    def test_invalid_group_lists_are_quarantined_in_both_directions(self):
        for target in ([], ['GEN 1:1', 'GEN 1:1'], ['GEN 1:2-1'], ['GEN 1:1', 'GEN 1:99'],
                       ['GEN 1:1', 'GEN 1:1a'], ['GEN 1:1;', 'GEN 2:1']):
            with self.subTest(target=target):
                engine = VersificationMappingEngine({'maxVerses': {'GEN': [3]}}, {'a': {
                    'maxVerses': {'GEN': [3]}, 'identityBooks': {'GEN': 'GEN'},
                    'groupMappings': [{'source': ['GEN 1:1'], 'target': target}],
                }})
                for source, dest in (('a', 'BOSReference'), ('BOSReference', 'a')):
                    self.assertNotEqual(engine.convert(source, dest, [ref('GEN', 1, 1)]).status, MappingStatus.EXACT)

    def test_audit_distinguishes_missing_quarantined_and_group_member_addresses(self):
        engine = VersificationMappingEngine({'maxVerses': {'GEN': [5]}}, {'a': {
            'maxVerses': {'GEN': [5]},
            'groupMappings': [{'source': 'GEN 1:1', 'target': ['GEN 1:1-2']}],
            'mappedVerses': {'GEN 1:9': 'GEN 1:3'},
        }})
        report = engine.audit_reference_coverage('a')
        self.assertEqual((report['representedCount'], report['blockedCount'], report['unmappedCount']), (2, 1, 2))
        self.assertEqual(report['books']['GEN']['unmappedRanges'], ['GEN 1:4-5'])
        self.assertEqual(report['books']['GEN']['blockedRanges'], ['GEN 1:3'])


@unittest.skipUnless(importlib.util.find_spec('bos_books_codes_py') and importlib.util.find_spec('bible_organisational_system'),
                     'Bible integration needs BOS native dependencies; use .venv/bin/python.')
class SupplementBibleIntegrationTests(unittest.TestCase):
    def test_public_single_plural_and_range_apis_preserve_group_contract(self):
        from BibleOrgSys.Bible import Bible
        from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem
        for factory in (lambda name: Bible(versification=name), BibleVersificationSystem):
            english, original = factory('eng'), factory('org')
            for source, group in CASES:
                with self.subTest(factory=factory, source=source):
                    result = english.convertToReferenceVersification(*source, detailed=True)
                    self.assertEqual(result.references, group)
                    with self.assertRaises(MultipleReferencesError):
                        english.convertToReferenceVersification(*source)
                    with self.assertRaises(PartialMappingError):
                        english.convertFromReferenceVersification(*group[0])
                    self.assertEqual(original.convertReferencesToVersification('eng', group).require_single(), source)
                    self.assertEqual(original.convertRangeToVersification('eng', group[0], group[-1]).require_single(), source)

    def test_mapped_passage_fetches_both_native_parts_and_rejects_partial_inverse(self):
        from BibleOrgSys.Formats.USFMBible import USFMBible
        prior_logging = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, prior_logging)
        with tempfile.TemporaryDirectory() as temporary:
            for index, (source, group) in enumerate(CASES):
                with self.subTest(source=source):
                    code = {'SA1': '1SA', 'KI1': '1KI', 'CH1': '1CH'}.get(source[0], source[0])
                    original_dir = Path(temporary) / f'org-{index}'
                    original_dir.mkdir()
                    lines, chapter = [f'\\id {code}\n\\h Test\n'], None
                    for part, marker in zip(group, ('First-part.', 'Second-part.')):
                        if part[1] != chapter:
                            lines.append(f'\\c {part[1]}\n\\p\n')
                            chapter = part[1]
                        lines.append(f'\\v {part[2]} {marker}\n')
                    (original_dir / f'{code}.usfm').write_text(''.join(lines))
                    original = USFMBible(original_dir, versification='org')
                    original.load()
                    passage = original.getMappedPassage('eng', [source])
                    self.assertEqual(passage.mapping.references, group)
                    text = ' '.join(e.getCleanText() for p in passage.portions for e in p.entries
                                    if e.getMarker() == 'v~')
                    self.assertEqual(text, 'First-part. Second-part.')

                    english_dir = Path(temporary) / f'eng-{index}'
                    english_dir.mkdir()
                    marker = '\\d' if source[2] == '0' else f'\\p\n\\v {source[2]}'
                    (english_dir / f'{code}.usfm').write_text(
                        f'\\id {code}\n\\h Test\n\\c {source[1]}\n{marker} Both-parts.\n'
                        + ('\\p\n\\v 1 Body.\n' if source[2] == '0' else ''))
                    english = USFMBible(english_dir, versification='eng')
                    english.load()
                    passage = english.getMappedPassage('org', group)
                    self.assertEqual(passage.mapping.references, (source,))
                    text = ' '.join(e.getCleanText() for p in passage.portions for e in p.entries
                                    if e.getMarker() in ('d', 'v~'))
                    self.assertEqual(text, 'Both-parts.')
                    for part in group:
                        with self.assertRaises(PartialMappingError):
                            english.getMappedPassage('org', [part])


if __name__ == '__main__':
    unittest.main()
