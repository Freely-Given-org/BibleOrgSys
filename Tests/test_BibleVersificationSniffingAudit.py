# SPDX-License-Identifier: MPL-2.0
"""Offline Copenhagen audit, independently enumerated corrections and text retrieval.

The expected groups are reviewed fixtures, not copied from the supplement at
runtime. Optional maintainer OET files and upstream repositories are not needed.
"""

from collections import Counter
from copy import deepcopy
import importlib.util
from itertools import combinations
import logging
from pathlib import Path
import tempfile
import unittest

from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingStatus, PartialMappingError, VersificationMappingEngine, get_default_mapping_engine,
)
from BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter import (
    VersificationDataError, load_bundle, parse_reference_span,
)
from BibleOrgSys.Reference.Converters.BibleVersificationSniffingAudit import (
    GROUP_TYPES, build_sniffing_report, sniffing_references,
)


# Semicolon here separates explicit complete spans; it is not sniffing syntax.
NEW_CASES = (
    ('eng', 'PSA 13:5-6', 'PSA 13:6'),
    ('eng', 'ISA 63:19;ISA 64:1', 'ISA 63:19'),
    ('eng', 'ACT 19:40-41', 'ACT 19:40'),
    ('vul', 'GEN 50:22', 'GEN 50:22-23'),
    ('vul', 'EXO 40:13', 'EXO 40:13-15'),
    ('vul', 'LEV 26:45', 'LEV 26:45-46'),
    ('vul', 'NUM 11:34', 'NUM 11:34-35'),
    ('vul', 'JOS 4:23-24', 'JOS 4:23'),
    ('vul', 'JOS 5:14-15', 'JOS 5:14'),
    ('vul', 'JOS 21:36', 'JOS 21:36-37'),
    ('vul', 'JOS 21:37', 'JOS 21:38-39'),
    ('vul', 'JDG 5:31-32', 'JDG 5:31'),
    ('vul', 'JDG 21:24', 'JDG 21:24-25'),
    ('vul', 'CH1 11:46', 'CH1 11:46-47'),
    ('vul', 'CH1 12:4', 'CH1 12:4-5'),
    ('vul', 'CH1 20:7', 'CH1 20:7-8'),
    ('vul', 'NEH 3:30', 'NEH 3:30-31'),
    ('vul', 'NEH 12:33', 'NEH 12:33-34'),
    ('vul', 'JOB 16:4-5', 'JOB 16:4'),
    ('vul', 'JOB 42:16', 'JOB 42:16-17'),
    ('vul', 'PSA 2:12-13', 'PSA 2:12'),
    ('vul', 'PSA 4:9-10', 'PSA 4:9'),
    ('vul', 'PSA 10:1-2', 'PSA 11:1'),
    ('vul', 'PSA 12:1', 'PSA 13:1-2'),
    ('vul', 'PSA 12:2-3', 'PSA 13:3'),
    ('vul', 'PSA 43:22', 'PSA 44:22-23'),
    ('vul', 'PSA 55:11', 'PSA 56:11-12'),
    ('vul', 'ISA 63:19;ISA 64:1', 'ISA 63:19'),
    ('vul', 'JER 37:4', 'JER 37:4-5'),
    ('vul', 'EZE 2:9', 'EZE 2:9-10'),
    ('vul', 'HOS 2:23-24', 'HOS 2:25'),
    ('vul', 'AMO 6:10-11', 'AMO 6:10'),
    ('vul', 'MIC 5:11', 'MIC 5:10-11'),
    ('vul', 'WIS 5:13-14', 'WIS 5:13'),
    ('vul', 'WIS 6:1-2', 'WIS 6:1'),
    ('vul', 'WIS 6:22-23', 'WIS 6:21'),
    ('vul', 'WIS 9:18-19', 'WIS 9:18'),
    ('vul', 'WIS 11:5-6', 'WIS 11:5'),
    ('vul', 'WIS 19:12', 'WIS 19:12-13'),
    ('vul', 'WIS 19:20', 'WIS 19:21-22'),
    ('vul', 'MA2 2:18-19', 'MA2 2:18'),
    ('vul', 'MAT 17:14', 'MAT 17:14-15'),
    ('vul', 'MRK 4:40', 'MRK 4:40-41'),
    ('vul', 'ACT 7:55', 'ACT 7:55-56'),
    ('vul', 'ACT 14:6', 'ACT 14:6-7'),
    ('vul', 'NUM 26:1', 'NUM 25:19;NUM 26:1'),
)


def refs(text):
    result = []
    for span in text.split(';'):
        for point in parse_reference_span(span).points():
            book, cv = point.split()
            chapter, verse = cv.split(':')
            result.append((book, chapter, verse, None))
    return tuple(result)


class ReviewedSniffingCorrectionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle()
        cls.engine = get_default_mapping_engine()

    def test_all_46_new_groups_both_directions_and_via_reference(self):
        self.assertEqual(len(NEW_CASES), 46)
        actual = {(c['system'], refs(';'.join(c['source'])), refs(';'.join(c['target'])))
                  for c in self.bundle['supplement']['corrections'][8:]}
        self.assertEqual(actual, {(s, refs(a), refs(b)) for s, a, b in NEW_CASES})
        for profile, a, b in NEW_CASES:
            for original in ('org', 'BOSReference'):
                with self.subTest(profile=profile, source=a, target=original):
                    source, target = refs(a), refs(b)
                    forward = self.engine.convert(profile, original, source)
                    backward = self.engine.convert(original, profile, target)
                    self.assertEqual((forward.status, forward.references), (MappingStatus.EXACT, target))
                    self.assertEqual((backward.status, backward.references), (MappingStatus.EXACT, source))
                    self.assertEqual(forward.alternatives, ())
                    self.assertTrue(any('BOS supplement ' in p for p in forward.provenance))
                    self.assertEqual(self.engine.convert_range(profile, original, source[0], source[-1]).references, target)
                    self.assertEqual(self.engine.convert_range(original, profile, target[0], target[-1]).references, source)

    def test_every_proper_subset_is_partial_even_when_old_singleton_was_exact(self):
        for profile, a, b in NEW_CASES:
            for source, target, group in ((profile, 'org', refs(a)), ('org', profile, refs(b))):
                for size in range(1, len(group)):
                    for subset in combinations(group, size):
                        with self.subTest(source=source, target=target, subset=subset):
                            result = self.engine.convert(source, target, subset)
                            self.assertEqual((result.status, result.references), (MappingStatus.PARTIAL, ()))
                            self.assertIn('INCOMPLETE_MAPPING_GROUP', {d.code for d in result.diagnostics})
                            with self.assertRaises(PartialMappingError):
                                result.require_single()

    def test_unaffected_members_of_all_touched_chapters_keep_their_results(self):
        old = deepcopy(self.bundle)
        old['supplement']['corrections'] = old['supplement']['corrections'][:8]
        previous = VersificationMappingEngine.from_bundled_data(bundle=old)
        for profile in ('eng', 'vul'):
            for inverse in (False, True):
                side = 2 if inverse else 1
                changed = {r for case in NEW_CASES if case[0] == profile for r in refs(case[side])}
                source, target = ('org', profile) if inverse else (profile, 'org')
                for book, chapter in {(r[0], r[1]) for r in changed}:
                    maximum = self.engine._domains[source].counts[book][int(chapter)-1]
                    for verse in range(maximum+1):
                        point = (book, chapter, str(verse), None)
                        if point in changed:
                            continue
                        with self.subTest(source=source, target=target, point=point):
                            before = previous.convert(source, target, [point])
                            after = self.engine.convert(source, target, [point])
                            self.assertEqual((after.status, after.references, after.alternatives),
                                             (before.status, before.references, before.alternatives))

    def test_new_numeric_groups_agree_with_their_exact_evidence_columns(self):
        rules = {r['name']: r for r in self.bundle['supplementEvidence']}
        for correction in self.bundle['supplement']['corrections'][8:]:
            if correction['id'] == 'vul-num-26-1':
                continue  # Explicitly completed truncated row; inherited revision-1 text evidence.
            with self.subTest(correction=correction['id']):
                evidence = correction['evidence']
                rule = rules[evidence['copenhagenRule']]
                values = next(iter(rule['ranges'][evidence['copenhagenRangeIndex']].values()))
                for column, system, group in ((evidence['sourceColumn'], correction['system'], correction['source']),
                                               (evidence['referenceColumn'], 'org', correction['target'])):
                    self.assertEqual(sniffing_references(values[rule['columns'].index(column)], system,
                                                         self.engine, self.bundle), refs(';'.join(group)))
                    role = 'reference' if system == 'org' else 'source'
                    for condition in rule['tests'][rule['columns'].index(column)]:
                        if condition.strip().endswith('=Last'):
                            point = sniffing_references(condition.strip()[:-5], system, self.engine, self.bundle)[0]
                            self.assertEqual(correction[role + 'ChapterCounts'][point[0] + ' ' + point[1]], int(point[2]))

    def test_stale_counts_and_invalid_evidence_row_fail_closed(self):
        for role in ('sourceChapterCounts', 'referenceChapterCounts'):
            bundle = deepcopy(self.bundle)
            counts = bundle['supplement']['corrections'][8][role]
            counts[next(iter(counts))] += 1
            with self.assertRaisesRegex(VersificationDataError, 'chapter evidence'):
                VersificationMappingEngine.from_bundled_data(bundle=bundle)
        for index in (-1, 999, True, 2):  # Psalm 13 row 2 is OneToOne, not semantic grouping.
            bundle = deepcopy(self.bundle)
            bundle['supplement']['corrections'][8]['evidence']['copenhagenRangeIndex'] = index
            with self.assertRaisesRegex(VersificationDataError, 'evidence row'):
                VersificationMappingEngine.from_bundled_data(bundle=bundle)

    def test_composition_between_latin_english_and_original_keeps_atomic_groups(self):
        cases = (
            ('vul', 'eng', 'PSA 12:1', 'PSA 13:0-1'),
            ('eng', 'vul', 'ISA 63:19;ISA 64:1', 'ISA 63:19;ISA 64:1'),
            ('eng', 'vul', 'ACT 19:40-41', 'ACT 19:40'),
        )
        for source, target, a, b in cases:
            with self.subTest(source=source, a=a):
                result = self.engine.convert(source, target, refs(a))
                self.assertEqual((result.status, result.references), (MappingStatus.EXACT, refs(b)))


class SniffingInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle()
        cls.engine = get_default_mapping_engine()
        cls.report = build_sniffing_report(cls.bundle, cls.engine)

    def test_every_original_row_is_accounted_for_without_modifying_inputs(self):
        self.assertEqual((self.report['ruleCount'], self.report['rowCount'], self.report['splitMergeRowCount']),
                         (403, 1466, 556))
        before = deepcopy(self.bundle)
        self.assertEqual(build_sniffing_report(self.bundle, self.engine), self.report)
        self.assertEqual(self.bundle, before)
        self.assertEqual(len({(r['ruleIndex'], r['rangeIndex']) for r in self.report['rows']}), 1466)
        for row in self.report['rows']:
            original = self.bundle['supplementEvidence'][row['ruleIndex']]
            self.assertEqual(original['ranges'][row['rangeIndex']], {row['type']: row['references']})
            self.assertEqual(original['columns'], row['columns'])
            if row['type'] in GROUP_TYPES:
                self.assertEqual(set(row['profiles']), {'eng', 'vul', 'lxx'})
                self.assertTrue(all(a['status'] and a['reason'] for a in row['profiles'].values()))
            else:
                self.assertIn(row['status'], ('positional-row', 'textual-content-review', 'malformed-row'))
        self.assertEqual(self.report['rowTypeCounts']['SubdividedVerse'], 427)
        self.assertEqual(self.report['rowTypeCounts']['MergedVerses'], 129)
        counts = Counter(a['status'] for row in self.report['rows'] for a in row.get('profiles', {}).values())
        self.assertEqual(dict(counts), self.report['assessmentCounts'])
        self.assertEqual(sum(counts.values()), 556*3)
        self.assertEqual(counts['reviewed-correction'], 54)
        self.assertEqual(counts['candidate-needs-review'], 14)
        self.assertEqual(counts['textual-tradition-blocked'], 277)
        self.assertEqual(counts['positional-alignment-covered'], 236)
        self.assertEqual(counts['title-convention-covered'], 59)

    def test_conflicting_profiles_qualified_editions_and_malformed_rows_remain_explicit(self):
        rows = {(r['ruleIndex'], r['rangeIndex']): r for r in self.report['rows']}
        for key, profile, status, reason in (
            ((31, 0), 'lxx', 'candidate-needs-review', '29'),
            ((336, 0), 'vul', 'candidate-needs-review', 'org has 20'),
            ((339, 0), 'vul', 'candidate-needs-review', 'verse earlier'),
            ((285, 0), 'eng', 'candidate-needs-review', 'whole passage'),
            ((15, 5), 'lxx', 'edition-not-selected', 'qualified'),
            ((41, 0), 'vul', 'notation-or-domain-review', 'Incomplete'),
        ):
            with self.subTest(key=key, profile=profile):
                assessment = rows[key]['profiles'][profile]
                self.assertEqual(assessment['status'], status)
                self.assertIn(reason, assessment['reason'])
        malformed = [r for r in self.report['rows'] if r.get('status') == 'malformed-row']
        self.assertEqual([(r['ruleIndex'], r['rangeIndex']) for r in malformed], [(72, 1), (75, 1)])
        self.assertEqual(set(self.report['unmatchedProfiles']), {'rsc', 'rso', 'ethiopian_custom'})
        for book in ('SIR', 'TOB', 'JDT'):
            self.assertEqual(self.engine.convert('vul', 'org', [(book, 1, 1)]).status, MappingStatus.UNSUPPORTED)

    def test_parser_does_not_complete_punctuation_segments_or_absent_endpoints(self):
        for value in ('Num.25:19;', 'Gen.5:31.1', 'Absent', 'Psa.125:6-7', 'Neh.3:30', 'Gen.2:2-1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sniffing_references(value, 'lxx' if value.startswith('Neh') else 'vul', self.engine, self.bundle)
        self.assertEqual(sniffing_references('Isa.63:19-64:1', 'eng', self.engine, self.bundle),
                         refs('ISA 63:19;ISA 64:1'))


@unittest.skipUnless(importlib.util.find_spec('bos_books_codes_py') and importlib.util.find_spec('bible_organisational_system'),
                     'Native Bible integration requires the BOS project environment.')
class SniffingBibleIntegrationTests(unittest.TestCase):
    def test_loaded_passages_include_every_member_in_both_directions(self):
        from BibleOrgSys.Formats.USFMBible import USFMBible
        previous_logging = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, previous_logging)
        # Cross-chapter, three-member, Psalm-body, NT and deuterocanonical cases.
        cases = [NEW_CASES[i] for i in (0, 1, 2, 4, 23, 33, 40)]
        with tempfile.TemporaryDirectory() as temporary:
            for index, (profile, a, b) in enumerate(cases):
                for native, requested, local, remote in ((profile, 'org', refs(a), refs(b)),
                                                        ('org', profile, refs(b), refs(a))):
                    with self.subTest(profile=profile, source=a, native=native):
                        directory = Path(temporary) / f'{index}-{native}'
                        directory.mkdir()
                        code = {'MA2': '2MA'}.get(local[0][0], local[0][0])
                        lines, chapter = [f'\\id {code}\n\\h Test\n'], None
                        for part, point in enumerate(local):
                            if point[1] != chapter:
                                lines.append(f'\\c {point[1]}\n\\p\n')
                                chapter = point[1]
                            lines.append(f'\\v {point[2]} Part-{part}.\n')
                        (directory / f'{code}.usfm').write_text(''.join(lines))
                        bible = USFMBible(directory, versification=native)
                        bible.load()
                        result = bible.getMappedPassage(requested, remote)
                        self.assertEqual(result.mapping.references, local)
                        text = ' '.join(e.getCleanText() for p in result.portions for e in p.entries if e.getMarker() == 'v~')
                        self.assertEqual(text, ' '.join(f'Part-{i}.' for i in range(len(local))))
                        if len(remote) > 1:
                            with self.assertRaises(PartialMappingError):
                                bible.getMappedPassage(requested, remote[:1])


if __name__ == '__main__':
    unittest.main()
