#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline regression tests for the bundled reference data and its audit.

Run with standard Python (no native BOS modules or test dependencies required)::

    python -m unittest discover -s Tests -p 'test_BibleVersificationMappingsData.py' -v

The snapshot's defects are deliberately tested as *findings*. Tests passing does
not certify that these mappings can yet be used for reference conversion.
"""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from BibleOrgSys.Reference.Converters import BibleVersificationMappingsConverter as converter


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / 'BibleOrgSys/DataFiles/VersificationMappings'


def tiny_system(**changes):
    return {'maxVerses': {'GEN': ['5'], 'EXO': ['5']}, 'mappedVerses': {},
            'excludedVerses': [], 'partialVerses': {}, **changes}


class BundledDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = converter.load_bundle()
        cls.reference = converter.build_reference(cls.bundle)
        cls.report = converter.build_coverage_report(cls.bundle, cls.reference)

    def test_snapshot_is_pinned_and_attributed(self):
        manifest = self.bundle['manifest']
        self.assertEqual(manifest['snapshotCommit'], '519af776ab65d89a51e37f750779250f940459ef')
        self.assertEqual(manifest['dataLicense'], 'CC-BY-SA-4.0')
        self.assertEqual(len(manifest['files']), 15)
        self.assertEqual(tuple(self.bundle['systems']), converter.STANDARD_SYSTEMS)
        for entry in manifest['files']:
            with self.subTest(path=entry['path']):
                payload = (DATA_ROOT / entry['path']).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), entry['sha256'])

    def test_reference_and_report_are_reproducible(self):
        for name, text in converter.generated_documents(self.bundle).items():
            with self.subTest(file=name):
                self.assertEqual((DATA_ROOT / name).read_text(encoding='utf-8'), text)

    def test_reference_retains_all_original_counts(self):
        original = self.bundle['systems']['org']['maxVerses']
        self.assertEqual(len(original), 95)
        for usfm, counts in original.items():
            with self.subTest(book=usfm):
                bbb = converter.bos_book_code(usfm, 'org', self.bundle['bookCodes'])
                self.assertEqual(self.reference['books'][bbb]['maxVerses'], list(map(int, counts)))
                self.assertEqual(self.reference['books'][bbb]['sourceSystem'], 'org')

    def test_hebrew_and_greek_core_is_identified_separately(self):
        core = {bbb: book for bbb, book in self.reference['books'].items() if book['role'] == 'core-book'}
        self.assertEqual(len(core), 66)
        # Hebrew Joel and Malachi retain their original chapter divisions.
        self.assertEqual(len(core['JOL']['maxVerses']), 4)
        self.assertEqual(len(core['MAL']['maxVerses']), 3)
        self.assertEqual(len(core['MAT']['maxVerses']), 28)
        self.assertNotIn('TOB', core)

    def test_extensions_have_explicit_sources_and_no_inferred_equivalence(self):
        self.assertEqual(len(self.reference['books']), 102)
        self.assertFalse(self.reference['conversionReady'])
        self.assertEqual(self.reference['version'], '1-draft')
        self.assertNotIn('mappedVerses', self.reference)
        extensions = self.bundle['policy']['extensions']
        self.assertEqual(set(extensions), {'DAG', 'LAO', '6EZ', '1MQ', '3MQ', 'REP', '4BA'})
        for usfm, extension in extensions.items():
            with self.subTest(book=usfm):
                source = extension['sourceSystem']
                bbb = converter.bos_book_code(usfm, source, self.bundle['bookCodes'])
                book = self.reference['books'][bbb]
                self.assertEqual(book['sourceSystem'], source)
                self.assertEqual(book['maxVerses'], list(map(int, self.bundle['systems'][source]['maxVerses'][usfm])))
                self.assertTrue(book['notes'])

    def test_composite_daniel_does_not_expand_the_hebrew_core(self):
        self.assertEqual(len(self.reference['books']['DAN']['maxVerses']), 12)
        self.assertEqual(len(self.reference['books']['DNG']['maxVerses']), 12)
        self.assertEqual(self.reference['books']['DNG']['role'], 'composite-view')
        self.assertEqual(self.reference['books']['DNG']['sourceSystem'], 'lxx')
        self.assertIn('PAZ', self.reference['books'])
        self.assertIn('SUS', self.reference['books'])
        self.assertIn('BEL', self.reference['books'])

    def test_latin_extensions_keep_their_native_book_identity(self):
        self.assertEqual(self.reference['books']['LAO']['maxVerses'], [20])
        self.assertEqual(self.reference['books']['EZ6']['maxVerses'], [63, 78])
        self.assertEqual(self.reference['books']['EZ6']['role'], 'extract-view')

    def test_vulgate_textual_gaps_are_blocked_even_without_explicit_rules(self):
        vul = self.report['systems']['vul']
        self.assertEqual(len(vul['documentedRestrictions']), 1)
        for book in ('TOB', 'JDT', 'SIR'):
            with self.subTest(book=book):
                coverage = vul['books'][book]
                self.assertEqual(coverage['status'], 'unmapped-textual-tradition')
                self.assertEqual(coverage['explicitMappingRuleCount'], 0)
                self.assertFalse(coverage['identityMappingAssumed'])

    def test_no_source_system_claims_conversion_or_identity_coverage(self):
        for name, audit in self.report['systems'].items():
            with self.subTest(system=name):
                self.assertFalse(audit['conversionReady'])
                self.assertEqual(audit['mappingTargetSystem'], 'org')
                self.assertTrue(all(not b['identityMappingAssumed'] for b in audit['books'].values()))

    def test_original_missing_daniel_and_verse_68_are_preserved_as_findings(self):
        issues = self.report['systems']['org']['issues']
        undefined = [i for i in issues if i['code'] == 'UNDEFINED_BOOK']
        self.assertEqual(len(undefined), 8)
        self.assertTrue(all(i['reference'].startswith('DAG ') and i['role'] == 'target' for i in undefined))
        self.assertTrue(any(i['code'] == 'VERSE_OUTSIDE_COUNTS' and i['reference'] == 'S3Y 1:38-68'
                            for i in issues))
        # The provisional catalogue must not hide the raw org defect in the report.
        self.assertIn('DNG', self.reference['books'])
        self.assertEqual(self.reference['books']['PAZ']['maxVerses'], [67])

    def test_reversed_vulgate_range_is_not_silently_repaired(self):
        rules = self.bundle['systems']['vul']['mappedVerses']
        self.assertEqual(rules['DAG 3:52-23'], 'S3Y 1:30-31')
        findings = [i for i in self.report['systems']['vul']['issues'] if i['code'] == 'REVERSED_RANGE']
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['reference'], 'DAG 3:52-23')
        self.assertEqual(self.bundle['policy']['corrections'], [])

    def test_lettered_esther_and_lxx_whitespace_need_explicit_policies(self):
        self.assertIn('ESG 1:1a', self.report['systems']['eng']['letteredReferences'])
        self.assertGreater(self.report['systems']['eng']['issueCounts']['UNDECLARED_SEGMENT'], 0)
        self.assertEqual(self.report['systems']['lxx']['issueCounts']['SEGMENT_LABEL_WHITESPACE'], 74)
        self.assertEqual(self.bundle['systems']['lxx']['partialVerses']['EXO 28:29'], ['-', 'a '])

    def test_ethiopian_counts_are_not_implicitly_filled_in(self):
        data = self.bundle['systems']['ethiopian_custom']
        self.assertEqual(len(data['maxVerses']['EXO']), 3)
        self.assertNotIn('basedOn', data)
        self.assertIn('EXO 21:16', data['mappedVerses'])
        audit = self.report['systems']['ethiopian_custom']
        self.assertIn('INCOMPLETE_CUSTOM_COUNTS', audit['issueCounts'])
        self.assertEqual(audit['books']['EXO']['status'], 'underspecified-custom-counts')

    def test_custom_sample_exercises_omissions_merges_and_inheritance(self):
        sample = self.report['sampleCustomDefinition']
        self.assertEqual(sample['excludedVerseEntryCount'], 49)
        self.assertEqual(sample['mergedVerseEntryCount'], 29)
        self.assertIn('INHERITANCE_NOT_RESOLVED', sample['issueCounts'])
        self.assertEqual(self.report['inheritanceIssues'], [])

    def test_known_bos_gaps_are_visible(self):
        self.assertEqual(self.report['legacyBooksMissingFromReference'],
                         ['BA2', 'DNA', 'ESA', 'EZ5', 'EZN', 'LBA', 'MQ2', 'PS3'])
        self.assertEqual(self.report['booksMissingFromReferenceByLegacySystem']['BibMaxRef'],
                         ['BA2', 'LBA', 'MQ2', 'PS3'])

    def test_crosswalk_matches_existing_bos_book_catalogue(self):
        xml_path = REPO_ROOT / 'BibleOrgSys/DataFiles/BibleBooksCodes.xml'
        self.assertEqual(hashlib.sha256(xml_path.read_bytes()).hexdigest(), self.bundle['bookCodes']['sourceSHA256'])
        allowed = {}
        for entry in ET.parse(xml_path).getroot():
            usfm = entry.findtext('USFMAbbreviation')
            if usfm:
                allowed.setdefault(usfm.upper(), set()).add(entry.findtext('referenceAbbreviation'))
        for usfm, entry in self.bundle['bookCodes']['books'].items():
            with self.subTest(book=usfm):
                self.assertIn(entry['bosCode'], allowed[usfm])
                self.assertEqual(set(entry['alternatives']), allowed[usfm] - {entry['bosCode']})

    def test_lxx_ezra_uses_source_context_only(self):
        crosswalk = self.bundle['bookCodes']
        self.assertEqual(converter.bos_book_code('EZR', 'lxx', crosswalk), 'EZN')
        self.assertEqual(converter.bos_book_code('EZR', 'org', crosswalk), 'EZR')
        self.assertEqual(self.report['systems']['lxx']['books']['EZR']['bosBook'], 'EZN')
        self.assertEqual(converter.bos_book_code('JDB', 'org', crosswalk), 'JGB')
        self.assertEqual(converter.bos_book_code('S3Y', 'org', crosswalk), 'PAZ')
        with self.assertRaises(converter.VersificationDataError):
            converter.bos_book_code('ZZZ', 'org', crosswalk)

    def test_legacy_inventory_snapshot_matches_bos(self):
        path = REPO_ROOT / self.bundle['legacy']['source']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.bundle['legacy']['sourceSHA256'])
        legacy = json.loads(path.read_text())
        self.assertEqual(self.bundle['legacy']['systems'], {s: list(d['CV']) for s, d in legacy.items()})

    def test_building_and_auditing_do_not_mutate_source_data(self):
        before = deepcopy(self.bundle)
        converter.generated_documents(self.bundle)
        self.assertEqual(self.bundle, before)

    def test_policy_cannot_replace_a_core_book(self):
        bundle = deepcopy(self.bundle)
        bundle['policy']['extensions']['GEN'] = bundle['policy']['extensions']['LAO']
        with self.assertRaisesRegex(converter.VersificationDataError, 'replace a base book'):
            converter.build_reference(bundle)

    def test_policy_cannot_point_to_absent_counts(self):
        bundle = deepcopy(self.bundle)
        bundle['policy']['extensions']['LAO']['sourceSystem'] = 'org'
        with self.assertRaisesRegex(converter.VersificationDataError, 'Missing reference count source'):
            converter.build_reference(bundle)

    def test_reference_code_collisions_are_not_overwritten(self):
        bundle = deepcopy(self.bundle)
        bundle['bookCodes']['books']['LAO']['bosCode'] = 'GEN'
        with self.assertRaisesRegex(converter.VersificationDataError, 'Two reference entries'):
            converter.build_reference(bundle)


class RangeAndAuditTests(unittest.TestCase):
    def test_numeric_range_and_zero_title(self):
        span = converter.parse_reference_span('PSA 90:0-2')
        self.assertEqual(span.points(), ('PSA 90:0', 'PSA 90:1', 'PSA 90:2'))

    def test_single_suffix_is_preserved(self):
        self.assertEqual(converter.parse_reference_span('ESG 1:1a').points(), ('ESG 1:1a',))

    def test_suffix_ranges_are_not_expanded_without_an_inventory(self):
        self.assertIsNone(converter.parse_reference_span('ESG 1:1a-1c').points())
        self.assertIsNone(converter.parse_reference_span('ESG 1:1a-2b').points())

    def test_huge_ranges_do_not_allocate_unbounded_lists(self):
        self.assertIsNone(converter.parse_reference_span('GEN 1:1-99999999').points())

    def test_invalid_references_fail_explicitly(self):
        for reference in ('DAG 3:52-23', 'GEN 1:3c-3a', 'GEN 0:1', 'GEN -1:1', 'GEN 1:-1',
                          'GEN 1:1-2:3', 'GEN 1:1,3', 'XYZ', '', None):
            with self.subTest(reference=reference), self.assertRaises(converter.VersificationDataError):
                converter.parse_reference_span(reference)

    def test_unequal_ranges_are_not_zipped(self):
        data = tiny_system(mappedVerses={'GEN 1:1-3': 'EXO 1:1'})
        result = converter.audit_system('example', data, tiny_system())
        issue = next(i for i in result['issues'] if i['code'] == 'UNEQUAL_RANGE_LENGTHS')
        self.assertEqual((issue['sourceLength'], issue['targetLength']), (3, 1))
        self.assertEqual(issue['source'], 'GEN 1:1-3')

    def test_overlapping_rules_keep_all_relationships(self):
        data = tiny_system(mappedVerses={'GEN 1:1-2': 'EXO 1:1-2', 'GEN 1:2-3': 'EXO 1:2-3'})
        result = converter.audit_system('example', data, tiny_system())
        for code, point in [('SOURCE_OVERLAP', 'GEN 1:2'), ('TARGET_OVERLAP', 'EXO 1:2')]:
            with self.subTest(code=code):
                issue = next(i for i in result['issues'] if i['code'] == code)
                self.assertEqual(issue['references'], [point])
                self.assertEqual(len(issue['rules']), 2)

    def test_many_to_one_inverse_collision_is_retained(self):
        data = tiny_system(mappedVerses={'GEN 1:1': 'EXO 1:1', 'GEN 1:2': 'EXO 1:1'})
        result = converter.audit_system('example', data, tiny_system())
        issue = next(i for i in result['issues'] if i['code'] == 'TARGET_OVERLAP')
        self.assertEqual({r['source'] for r in issue['rules']}, {'GEN 1:1', 'GEN 1:2'})

    def test_source_and_destination_bounds_use_different_systems(self):
        data = tiny_system(maxVerses={'GEN': ['8']}, mappedVerses={'GEN 1:8': 'EXO 1:6'})
        result = converter.audit_system('example', data, tiny_system())
        issues = [i for i in result['issues'] if i['code'] == 'VERSE_OUTSIDE_COUNTS']
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]['role'], 'target')

    def test_omissions_merges_and_partial_refs_are_also_checked(self):
        data = tiny_system(excludedVerses=['GEN 2:1'], mergedVerses=['GEN 1:4-7'],
                           partialVerses={'EXO 1:6': ['a', 'b']})
        result = converter.audit_system('example', data, tiny_system())
        self.assertIn('CHAPTER_OUTSIDE_COUNTS', result['issueCounts'])
        locations = {i['location'] for i in result['issues'] if i['code'] == 'VERSE_OUTSIDE_COUNTS'}
        self.assertEqual(locations, {'mergedVerses/0', 'partialVerses/EXO 1:6'})

    def test_zero_titles_are_observed_without_assuming_universal_zero_support(self):
        data = tiny_system(mappedVerses={'GEN 1:0': 'EXO 1:0'})
        result = converter.audit_system('example', data, tiny_system())
        self.assertEqual(result['verseZeroReferences'], ['EXO 1:0', 'GEN 1:0'])
        self.assertNotIn('REFERENCE_SYNTAX', result['issueCounts'])

    def test_invalid_counts_are_not_coerced(self):
        for counts in ([True], [-1], [1.5], ['-1'], ['1.5'], [], '31'):
            with self.subTest(counts=counts):
                result = converter.audit_system('bad', tiny_system(maxVerses={'GEN': counts}), tiny_system())
                self.assertIn('INVALID_COUNTS', result['issueCounts'])

    def test_invalid_and_duplicate_partial_labels(self):
        for labels, code in [([], 'INVALID_SEGMENT_LABELS'), ([3], 'INVALID_SEGMENT_LABELS'),
                             (['a', 'a'], 'DUPLICATE_SEGMENT_LABEL'), (['a '], 'SEGMENT_LABEL_WHITESPACE')]:
            with self.subTest(labels=labels):
                result = converter.audit_system('bad', tiny_system(partialVerses={'GEN 1:1': labels}), tiny_system())
                self.assertIn(code, result['issueCounts'])

    def test_unknown_field_is_recorded(self):
        result = converter.audit_system('bad', tiny_system(typo=[]), tiny_system())
        self.assertIn('UNKNOWN_FIELD', result['issueCounts'])

    def test_unknown_and_cyclic_inheritance(self):
        definitions = {'a': {'basedOn': 'b'}, 'b': {'basedOn': 'a'}, 'c': {'basedOn': 'missing'}}
        self.assertEqual(converter.audit_inheritance(definitions), [
            {'code': 'INHERITANCE_CYCLE', 'systems': ['a', 'b']},
            {'code': 'UNKNOWN_BASE', 'system': 'c', 'base': 'missing'},
        ])

    def test_inheritance_does_not_fill_in_missing_counts(self):
        data = tiny_system(basedOn='org', maxVerses={'GEN': ['1']}, mappedVerses={'GEN 1:2': 'GEN 1:2'})
        result = converter.audit_system('custom', data, tiny_system())
        self.assertIn('INHERITANCE_NOT_RESOLVED', result['issueCounts'])
        self.assertEqual(result['bookCount'], 1)
        self.assertTrue(any(i['code'] == 'VERSE_OUTSIDE_COUNTS' and i['role'] == 'source'
                            for i in result['issues']))


class IntegrityAndDistributionTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('BOS_VERSIFICATION_TEST_WHEEL'),
                         'Set BOS_VERSIFICATION_TEST_WHEEL to test a built wheel as well as zip resources.')
    def test_built_wheel_contains_and_audits_the_complete_bundle(self):
        wheel = Path(os.environ['BOS_VERSIFICATION_TEST_WHEEL']).resolve()
        with zipfile.ZipFile(wheel) as archive:
            self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
            for path in DATA_ROOT.rglob('*'):
                if path.is_file():
                    with self.subTest(file=path.name):
                        self.assertEqual(archive.read(path.relative_to(REPO_ROOT).as_posix()), path.read_bytes())
            # The packaging adjustment must retain the previously bundled data.
            for relative in ('BibleOrgSys/DataFiles/DerivedFiles/BibleVersificationSystems_Tables.json',
                             'BibleOrgSys/DistributedFiles/DistributedFiles.ReadMe.txt'):
                self.assertEqual(archive.read(relative), (REPO_ROOT / relative).read_bytes())
            metadata_path = next(p for p in archive.namelist() if p.endswith('.dist-info/METADATA'))
            dependencies = [line for line in archive.read(metadata_path).decode().splitlines()
                            if line.startswith('Requires-Dist:')]
            self.assertFalse(any('versification' in line.lower() for line in dependencies))
        with tempfile.TemporaryDirectory() as temporary:
            code = (
                'import sys; sys.path.insert(0, sys.argv[1]); '
                'from BibleOrgSys.Reference.Converters import BibleVersificationMappingsConverter as c; '
                'assert c.__file__.startswith(sys.argv[1]); '
                'assert c.main(["--check"]) == 0; '
                'from BibleOrgSys.Reference import BibleVersificationMappings as m; '
                'assert m.__file__.startswith(sys.argv[1]); '
                'engine = m.get_default_mapping_engine(); '
                'assert engine.convert("eng", "lxx", [("GEN",31,55)]).require_single() == ("GEN","32","1",None); '
                'assert engine.convert("eng", "org", [("NUM",26,1)]).references == (("NUM","25","19",None),("NUM","26","1",None)); '
                'assert engine.convert("eng", "org", [("PSA",51,0)]).references == (("PSA","51","1",None),("PSA","51","2",None)); '
                'assert engine.convert("org", "eng", [("PSA",51,2)]).status == m.MappingStatus.PARTIAL; '
                'assert engine.convert("vul", "org", [("EXO",40,13)]).references == (("EXO","40","13",None),("EXO","40","14",None),("EXO","40","15",None)); '
                'assert engine.convert("eng", "org", [("ACT",19,40)]).status == m.MappingStatus.PARTIAL; '
                'assert engine.convert("vul", "org", [("MA2",2,18),("MA2",2,19)]).require_single() == ("MA2","2","18",None); '
                'assert engine.convert("rsc", "BOSReference", [("PSA",9,22)]).status == m.MappingStatus.AMBIGUOUS; '
                'assert engine.convert("vul", "BOSReference", [("TOB",1,1)]).status == m.MappingStatus.UNSUPPORTED; '
                'assert "bos_books_codes_py" not in sys.modules'
            )
            result = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(wheel)],
                                    cwd=temporary, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_modified_source_fails_checksum_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'bundle'
            shutil.copytree(DATA_ROOT, root)
            source = root / 'Copenhagen/versification-mappings/standard-mappings/org.json'
            source.write_bytes(source.read_bytes() + b'\n')
            with self.assertRaisesRegex(converter.VersificationDataError, 'checksum mismatch'):
                converter.load_bundle(root)

    def test_modified_supplement_evidence_fails_checksum_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'bundle'
            shutil.copytree(DATA_ROOT, root)
            source = root / 'Copenhagen/versification-sniffing/rules/merged_rules.json'
            source.write_bytes(source.read_bytes() + b'\n')
            with self.assertRaisesRegex(converter.VersificationDataError, 'checksum mismatch'):
                converter.load_bundle(root)

    def test_incomplete_manifest_cannot_skip_checksum_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'bundle'
            shutil.copytree(DATA_ROOT, root)
            path = root / 'source-manifest.json'
            manifest = json.loads(path.read_text())
            manifest['files'].pop()
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(converter.VersificationDataError, 'each bundled source exactly once'):
                converter.load_bundle(root)

    def test_duplicate_json_keys_are_rejected_even_with_updated_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'bundle'
            shutil.copytree(DATA_ROOT, root)
            relative = 'Copenhagen/versification-mappings/standard-mappings/org.json'
            payload = b'{"maxVerses": {}, "maxVerses": {}}'
            (root / relative).write_bytes(payload)
            path = root / 'source-manifest.json'
            manifest = json.loads(path.read_text())
            next(e for e in manifest['files'] if e['path'] == relative)['sha256'] = hashlib.sha256(payload).hexdigest()
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(converter.VersificationDataError, 'Duplicate JSON key'):
                converter.load_bundle(root)

    def test_check_detects_stale_outputs_and_write_reproduces_them(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            self.assertEqual(converter.main(['--write', '--output-dir', temporary]), 0)
            self.assertEqual(converter.main(['--check', '--output-dir', temporary]), 0)
            (Path(temporary) / 'BOSReference.json').write_text('{}\n')
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                converter.main(['--check', '--output-dir', temporary])
            self.assertEqual(error.exception.code, 1)

    def test_zip_resources_work_without_checkout_native_modules_or_site_packages(self):
        # A deliberately minimal distribution catches undeclared imports and
        # filesystem-path assumptions independently of the maintainer's checkout.
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'bos-data.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                for relative in ('BibleOrgSys/__init__.py', 'BibleOrgSys/Reference/__init__.py',
                                 'BibleOrgSys/Reference/Converters/__init__.py',
                                 'BibleOrgSys/Reference/Converters/BibleVersificationMappingsConverter.py',
                                 'BibleOrgSys/Reference/Converters/BibleVersificationSniffingAudit.py',
                                 'BibleOrgSys/Reference/BibleVersificationMappings.py'):
                    output.write(REPO_ROOT / relative, relative)
                for path in DATA_ROOT.rglob('*'):
                    if path.is_file():
                        output.write(path, path.relative_to(REPO_ROOT).as_posix())
            code = (
                'import sys; sys.path.insert(0, sys.argv[1]); '
                'from BibleOrgSys.Reference.Converters import BibleVersificationMappingsConverter as c; '
                'assert c.__file__.startswith(sys.argv[1]); '
                'assert c.main(["--check"]) == 0; '
                'assert "bos_books_codes_py" not in sys.modules'
            )
            result = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(archive)],
                                    cwd=temporary, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('102 catalogue entries', result.stdout)


if __name__ == '__main__':
    unittest.main()
