# SPDX-License-Identifier: MPL-2.0
"""Real loading and persistence tests; use .venv/bin/python for BOS dependencies.

All fixtures are local and temporary. No external repository or network is used.

CHANGELOG:
    2026-10-21 KJV is now a partially supported NT profile, not count-only.
"""
import copy
import json
import os
from pathlib import Path
import pickle
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Formats.USFMBible import USFMBible
from BibleOrgSys.Formats.USXXMLBible import USXXMLBible
from BibleOrgSys.Formats.OSISXMLBible import OSISXMLBible
from BibleOrgSys.Formats.PTX8Bible import PTX8Bible, PTX8BibleFileCheck
from BibleOrgSys.Formats.ESFMBible import ESFMBible
from BibleOrgSys.Formats.PickledBible import PickledBible, createPickledBible
from BibleOrgSys.Reference.BibleVersificationMappings import (
    AmbiguousMappingError, InvalidReferenceError, MappingStatus,
    UnsupportedMappingError, UnknownVersificationSystemError,
)
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
from BibleOrgSys.UnknownBible import UnknownBible


def ref(chapter=31, verse=55):
    return 'GEN', str(chapter), str(verse), None


def usfm(folder):
    text = '\\id GEN Test\n\\usfm 3.0\n\\h Genesis\n\\c 31\n\\p\n'
    text += ''.join(f'\\v {v} Test sentence {v}.\n' for v in range(1, 56))
    text += '\\c 32\n\\p\n\\v 1 Next sentence.\n'
    Path(folder, '01GEN.usfm').write_text(text, encoding='utf-8')


def settings(folder, value='4', filename='Settings.xml'):
    Path(folder, filename).write_text(f'<ScriptureText><Name>TEST</Name><FullName>Test Bible</FullName>'
        f'<Encoding>65001</Encoding><Versification>{value}</Versification></ScriptureText>', encoding='utf-8')


def osis(path, value='eng', other='vul', work='Test', own_id='Test'):
    own = f'<refSystem>{value}</refSystem>' if value is not None else ''
    Path(path).write_text(f'''<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">
<osisText osisIDWork="{own_id}" osisRefWork="Other" xml:lang="en">
<header><work osisWork="{work}"><title>Test</title>{own}</work>
<work osisWork="Other"><refSystem>{other}</refSystem></work></header>
<div type="book" osisID="Gen"><chapter osisID="Gen.31">
<verse osisID="Gen.31.55">Test sentence.</verse></chapter></div>
</osisText></osis>''', encoding='utf-8')


def metadata(bible, kind, **fields):
    if bible.suppliedMetadata is None:
        bible.suppliedMetadata = {}
    bible.suppliedMetadata[kind] = fields
    bible.applySuppliedMetadata(kind)


class BibleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BibleOrgSysGlobals.preloadCommonData()

    def setUp(self):
        for name, value in (('maxProcesses', 1), ('verbosityLevel', 0)):
            p = patch.object(BibleOrgSysGlobals, name, value)
            p.start()
            self.addCleanup(p.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)


class DeclarationTests(BibleTestCase):
    def test_no_default_from_bible_name_or_unapplied_settings(self):
        b = Bible()
        b.name = b.abbreviation = 'KJV'
        b.settingsDict['Versification'] = 'eng'
        self.assertIsNone(b.getVersificationSystemName())
        self.assertEqual(b.getVersificationDeclaration()['status'], 'undeclared')
        self.assertIsNone(b.getVersificationSystem())
        with self.assertRaises(UnsupportedMappingError) as raised:
            b.convertToReferenceVersification(*ref())
        self.assertIn('UNDECLARED_VERSIFICATION', {d.code for d in raised.exception.result.diagnostics})

    def test_constructor_and_setter_accept_names_and_system_objects(self):
        b = Bible(versification=BibleVersificationSystem('eng'))
        self.assertEqual(b.getVersificationSystemName(), 'eng')
        self.assertIs(b.setVersificationSystem('lxx'), b)
        self.assertEqual(b.getVersificationSystem().getVersificationSystemName(), 'lxx')

    def test_invalid_explicit_declaration_is_atomic(self):
        b = Bible(versification='eng')
        for value in ('English', 'ENG', '', ' eng ', 'nonsense'):
            with self.subTest(value=value), self.assertRaises(UnknownVersificationSystemError):
                b.setVersificationSystem(value)
            self.assertEqual(b.getVersificationSystemName(), 'eng')
        for value in (None, 4, {}, Bible()):
            with self.subTest(value=value), self.assertRaises(TypeError):
                b.setVersificationSystem(value)

    def test_count_only_and_disabled_profiles_remain_unsupported(self):
        for name in ('Original', 'ethiopian_custom'):
            with self.subTest(name=name):
                b = Bible(versification=name)
                self.assertEqual(b.getVersificationSystemName(), name)
                self.assertEqual(b.getMappingCapabilities()['status'], 'unsupported')
                self.assertEqual(b.convertToReferenceVersification('GEN', 1, 1, detailed=True).status,
                                 MappingStatus.UNSUPPORTED)

    def test_metadata_keeps_raw_value_and_returns_detached_evidence(self):
        b = Bible()
        metadata(b, 'File', VersificationSystem=' eng ')
        d = b.getVersificationDeclaration()
        self.assertEqual((d['system'], d['source']), ('eng', 'metadata'))
        self.assertEqual(d['metadata'][0]['value'], ' eng ')
        d['metadata'][0]['system'] = 'vul'
        self.assertEqual(b.getVersificationSystemName(), 'eng')

    def test_explicit_wins_in_either_order_and_clear_restores_metadata(self):
        for before in (True, False):
            with self.subTest(before=before):
                b = Bible(versification='eng' if before else None)
                metadata(b, 'File', Versification='vul')
                if not before:
                    b.setVersificationSystem('eng')
                result = b.convertToReferenceVersification(*ref(), detailed=True)
                self.assertEqual(result.require_single(), ref(32, 1))
                self.assertIn('VERSIFICATION_CONFLICT', {d.code for d in result.diagnostics})
                b.clearVersificationSystem()
                self.assertEqual(b.getVersificationSystemName(), 'vul')

    def test_conflicting_metadata_blocks_both_directions(self):
        b = Bible()
        metadata(b, 'File', Versification='eng')
        metadata(b, 'Project', VersificationSystem='vul')
        self.assertEqual(b.getVersificationDeclaration()['status'], 'conflict')
        self.assertIsNone(b.getVersificationSystemName())
        for method in (b.convertToReferenceVersification, b.convertFromReferenceVersification):
            with self.assertRaises(AmbiguousMappingError):
                method(*ref())

    def test_unknown_metadata_does_not_fall_back_to_known_metadata(self):
        b = Bible()
        metadata(b, 'File', Versification='eng')
        metadata(b, 'Project', Versification='MyCustomScheme')
        self.assertEqual(b.getVersificationDeclaration()['status'], 'unresolved')
        self.assertIsNone(b.getVersificationSystemName())
        b.setVersificationSystem('eng')
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))

    def test_reapplied_metadata_is_idempotent_and_removed_fields_clear(self):
        b = Bible()
        for _ in range(3):
            metadata(b, 'Project', Versification='eng')
        self.assertEqual(len(b.getVersificationDeclaration()['metadata']), 1)
        metadata(b, 'Project')
        self.assertEqual(b.getVersificationDeclaration()['status'], 'undeclared')

    def test_conflicting_fields_in_one_source_are_preserved(self):
        b = Bible()
        metadata(b, 'File', Versification='eng', VersificationSystem='lxx')
        self.assertEqual(b.getVersificationDeclaration()['status'], 'conflict')

    def test_paratext_numeric_and_named_ids_are_namespace_specific(self):
        names = ('Original', 'Septuagint', 'Vulgate', 'English', 'RussianProtestant', 'RussianOrthodox')
        for index, (name, expected) in enumerate(zip(names, ('org', 'lxx', 'vul', 'eng', 'rsc', 'rso')), 1):
            for raw in (str(index), index, name):
                with self.subTest(raw=raw):
                    b = Bible()
                    metadata(b, 'PTX8', Settings={'Versification': raw})
                    self.assertEqual(b.getVersificationSystemName(), expected)
        self.assertEqual(Bible(versification='Original').getVersificationSystemName(), 'Original')

    def test_paratext_custom_or_malformed_ids_are_unresolved(self):
        for raw in ('0', 'Unknown', 'English+Project', '4custom', '99', '', None, True, ['4']):
            with self.subTest(raw=raw):
                b = Bible()
                metadata(b, 'PTX8', Settings={'Versification': raw})
                self.assertEqual(b.getVersificationDeclaration()['status'], 'unresolved')

    def test_ssf_metadata_uses_paratext_namespace(self):
        b = Bible()
        b.suppliedMetadata = {'PTX7': {'SSF': {'Versification': '4'}}}
        b.applySuppliedMetadata('SSF')
        self.assertEqual(b.getVersificationSystemName(), 'eng')

    def test_unreadable_project_context_does_not_assume_absence_of_overrides(self):
        b = Bible()
        b.sourceFolder = self.folder / 'missing'
        metadata(b, 'PTX8', Settings={'Versification': '4'})
        self.assertEqual(b.getVersificationDeclaration()['status'], 'unresolved')

    def test_metadata_file_loader_declares_system(self):
        path = self.folder / 'metadata.txt'
        path.write_text('VersificationSystem = eng\n', encoding='utf-8')
        b = Bible()
        b.loadMetadataTextFile(path)
        self.assertEqual(b.getVersificationSystemName(), 'eng')


class ConversionTests(BibleTestCase):
    def test_bible_conversions_match_system_conversions(self):
        b = Bible(versification='eng')
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertEqual(b.convertFromReferenceVersification(*ref(32, 1)), ref())
        for target in ('lxx', BibleVersificationSystem('lxx'), Bible(versification='lxx')):
            self.assertEqual(b.convertToVersification(target, *ref()), ref(32, 1))

    def test_passages_and_ranges_in_both_directions(self):
        b = Bible(versification='eng')
        expected = (ref(32, 1), ref(32, 2))
        result = b.convertReferencesToVersification('BOSReference', [ref(), ref(32, 1)])
        self.assertEqual(result.references, expected)
        self.assertEqual(b.convertRangeToVersification('BOSReference', ref(), ref(32, 1)), result)
        self.assertEqual(b.convertReferencesFromReferenceVersification(expected).references, (ref(), ref(32, 1)))
        self.assertEqual(b.convertRangeFromReferenceVersification(*expected).references, (ref(), ref(32, 1)))

    def test_target_bible_needs_resolved_declaration(self):
        source, target = Bible(versification='eng'), Bible()
        self.assertEqual(source.convertToVersification(target, *ref(), detailed=True).status, MappingStatus.UNSUPPORTED)
        metadata(target, 'File', Versification='eng', VersificationSystem='vul')
        self.assertEqual(source.convertToVersification(target, *ref(), detailed=True).status, MappingStatus.AMBIGUOUS)

    def test_mapping_errors_are_not_hidden(self):
        with self.assertRaises(AmbiguousMappingError):
            Bible(versification='rsc').convertToReferenceVersification('PSA', 9, 22)
        with self.assertRaises(UnsupportedMappingError):
            Bible(versification='vul').convertToReferenceVersification('TOB', 1, 1)
        with self.assertRaises(InvalidReferenceError):
            Bible(versification='eng').convertToReferenceVersification('GEN', 0, 1)

    def test_changed_declaration_has_no_stale_cache(self):
        b = Bible(versification='eng')
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))
        b.setVersificationSystem('org')
        self.assertEqual(b.convertFromReferenceVersification(*ref(32, 1)), ref(32, 1))


class FormatLoadingTests(BibleTestCase):
    def test_usfm_preserves_loaded_text_and_observed_structure(self):
        usfm(self.folder)
        b = USFMBible(self.folder, versification='eng')
        b.load()
        before = copy.deepcopy(b.getVersification())
        text = b.getVerseText(SimpleVerseKey('GEN', '31', '55'))
        self.assertIn('Test sentence 55.', text)
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertEqual(b.getVersification(), before)
        self.assertEqual(b.getVerseText(SimpleVerseKey('GEN', '31', '55')), text)
        self.assertIn('Next sentence.', b.getVerseText(SimpleVerseKey('GEN', '32', '1')))

    def test_no_metadata_remains_undeclared_after_loading(self):
        usfm(self.folder)
        b = USFMBible(self.folder)
        b.load()
        self.assertIsNone(b.getVersificationSystemName())

    def test_settings_and_ssf_companions_and_override(self):
        usfm(self.folder)
        settings(self.folder)
        b = USFMBible(self.folder)
        b.preload()
        self.assertEqual(b.getVersificationSystemName(), 'eng')
        settings(self.folder, '2', 'Test.SSF')
        b = USFMBible(self.folder)
        b.preload()
        self.assertEqual(b.getVersificationDeclaration()['status'], 'conflict')
        b = USFMBible(self.folder, versification='eng')
        b.load()
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))

    def test_invalid_companion_is_unresolved(self):
        usfm(self.folder)
        (self.folder / 'Settings.xml').write_text('<broken>', encoding='utf-8')
        b = USFMBible(self.folder)
        b.preload()
        self.assertEqual(b.getVersificationDeclaration()['status'], 'unresolved')

    def test_custom_vrs_blocks_base_profile(self):
        usfm(self.folder)
        settings(self.folder)
        (self.folder / 'custom.vrs').write_text('# Project changes\nGEN 1:1 = GEN 1:2\n', encoding='utf-8')
        for loader in (USFMBible, PTX8Bible):
            with self.subTest(loader=loader.__name__):
                b = loader(self.folder)
                b.preload()
                self.assertEqual(b.getVersificationDeclaration()['status'], 'unresolved')
                b.setVersificationSystem('eng')
                self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))

    def test_paratext_declaration_available_before_books(self):
        usfm(self.folder)
        settings(self.folder)
        b = PTX8Bible(self.folder)
        b.preload()
        self.assertFalse(b.books)
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))
        b.loadBooks()
        self.assertIn('Test sentence 55.', b.getVerseText(SimpleVerseKey('GEN', '31', '55')))

    def test_paratext_detection_accepts_usfm_two_and_three(self):
        settings(self.folder)
        # Detection counts these known project files without loading their data.
        for name in ('BookNames.xml', 'CheckingStatus.xml', 'CommentTags.xml', 'ProjectProgress.xml', 'WordAnalyses.xml'):
            (self.folder / name).write_text('<test/>', encoding='utf-8')
        for version_three in (True, False):
            with self.subTest(version_three=version_three):
                usfm(self.folder)
                path = self.folder / '01GEN.usfm'
                if not version_three:
                    path.write_text(path.read_text().replace('\\usfm 3.0\n', ''), encoding='utf-8')
                self.assertEqual(PTX8BibleFileCheck(self.folder), 1)

    def test_usx_loads_metadata_and_preserves_addresses(self):
        settings(self.folder)
        (self.folder / '001GEN.usx').write_text('''<usx version="3.0"><book code="GEN" style="id">Test</book>
<chapter number="31" style="c" sid="GEN 31"/>
<para style="p"><verse number="55" style="v" sid="GEN 31:55"/>Test sentence.<verse eid="GEN 31:55"/></para>
<chapter eid="GEN 31"/></usx>''', encoding='utf-8')
        b = USXXMLBible(self.folder)
        b.loadBooks()
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertIn('Test sentence.', b.getVerseText(SimpleVerseKey('GEN', '31', '55')))

    def test_primary_loader_constructor_keywords(self):
        usfm(self.folder)
        for loader in (USFMBible, USXXMLBible, PTX8Bible, ESFMBible):
            self.assertEqual(loader(self.folder, versification='eng').getVersificationSystemName(), 'eng')

    def test_osis_own_work_not_cross_reference_work(self):
        path = self.folder / 'Bible.xml'
        osis(path)
        b = OSISXMLBible(path)
        b.loadBooks()
        self.assertEqual(b.getVersificationSystemName(), 'eng')
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertIn('Test sentence.', b.getVerseText(SimpleVerseKey('GEN', '31', '55')))

    def test_osis_generic_and_kjv_are_not_english_aliases(self):
        for raw, status, name in [('Bible', 'unresolved', None), ('Bible.KJV', 'declared', 'KJV')]:
            with self.subTest(raw=raw):
                path = self.folder / 'Bible.xml'
                osis(path, value=raw)
                b = OSISXMLBible(path)
                b.loadBooks()
                self.assertEqual(b.getVersificationDeclaration()['status'], status)
                self.assertEqual(b.getVersificationSystemName(), name)
                self.assertEqual(b.convertToReferenceVersification(*ref(), detailed=True).status, MappingStatus.UNSUPPORTED)

    def test_osis_missing_own_work_does_not_use_other_work(self):
        path = self.folder / 'Bible.xml'
        osis(path, work='NotThisBible')
        b = OSISXMLBible(path)
        b.loadBooks()
        self.assertEqual(b.getVersificationDeclaration()['status'], 'undeclared')

    def test_osis_python_fallback_and_explicit_override(self):
        path = self.folder / 'Bible.xml'
        osis(path, 'vul')
        b = OSISXMLBible(path, versification='eng')
        with patch('BibleOrgSys.Formats.OSISXMLBible.parseOsis', side_effect=RuntimeError('force fallback')):
            with self.assertLogs(level='WARNING'):
                b.loadBooks()
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertIn('VERSIFICATION_CONFLICT', {d['code'] for d in b.getVersificationDeclaration()['diagnostics']})

    def test_duplicate_own_work_refsystems_are_not_overwritten(self):
        path = self.folder / 'Bible.xml'
        osis(path)
        path.write_text(path.read_text().replace('<refSystem>eng</refSystem>',
                       '<refSystem>eng</refSystem><refSystem>vul</refSystem>'), encoding='utf-8')
        b = OSISXMLBible(path)
        b.loadBooks()
        self.assertEqual(b.getVersificationDeclaration()['status'], 'conflict')

    def test_osis_parallel_headers_are_resolved_on_parent(self):
        first, second = self.folder / 'Gen.xml', self.folder / 'Exod.xml'
        osis(first, 'eng')
        osis(second, 'vul')
        second.write_text(second.read_text().replace('Gen.', 'Exod.').replace('osisID="Gen"', 'osisID="Exod"'), encoding='utf-8')
        b = OSISXMLBible(self.folder)
        with patch.object(BibleOrgSysGlobals, 'maxProcesses', 2):
            b.loadBooks()
        self.assertEqual(set(b.books), {'GEN', 'EXO'})
        self.assertEqual(b.getVersificationDeclaration()['status'], 'conflict')

    def test_multiple_osis_headers_preserve_disagreement_and_refresh(self):
        first, second = self.folder / 'Gen.xml', self.folder / 'Exod.xml'
        osis(first, 'eng')
        osis(second, 'vul')
        b = Bible()
        b._loadOSISVersificationMetadata(first)
        b._loadOSISVersificationMetadata(second)
        self.assertEqual(b.getVersificationDeclaration()['status'], 'conflict')
        osis(second, None)
        b._loadOSISVersificationMetadata(second)
        self.assertEqual(b.getVersificationSystemName(), 'eng')

    def test_flattened_osis_metadata_is_not_a_declaration(self):
        b = Bible()
        metadata(b, 'OSIS', RefSystem='eng')
        self.assertIsNone(b.getVersificationSystemName())

    def test_auto_loading_accepts_explicit_declaration(self):
        usfm(self.folder)
        b = UnknownBible(self.folder, versification='eng').search(autoLoadBooks=True)
        self.assertIsInstance(b, Bible)
        self.assertEqual(b.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertIn('Test sentence 55.', b.getVerseText(SimpleVerseKey('GEN', '31', '55')))

    def test_auto_loading_override_keeps_conflicting_project_evidence(self):
        usfm(self.folder)
        settings(self.folder, '3')
        # Keep this test about declaration precedence; minimal project fixtures
        # can match several Rust detectors with different metadata thresholds.
        detected = [SimpleNamespace(format='USFM Bible', path=str(self.folder))]
        with patch('BibleOrgSys.UnknownBible.bible_organisational_system.detectBibles', return_value=detected):
            b = UnknownBible(self.folder, versification='eng').search(autoLoadBooks=True)
        self.assertIsInstance(b, Bible)
        self.assertEqual(b.getVersificationSystemName(), 'eng')
        self.assertIn('VERSIFICATION_CONFLICT', {d['code'] for d in b.getVersificationDeclaration()['diagnostics']})


class PersistenceTests(BibleTestCase):
    def bible(self):
        b = Bible(versification='eng')
        b.name, b.abbreviation = 'Test Bible', 'TEST'
        metadata(b, 'Project', Versification='vul')
        return b

    def test_pickle_and_copy_preserve_conflict_without_engine_caches(self):
        b = self.bible()
        b.convertToReferenceVersification(*ref())
        for restored in (pickle.loads(pickle.dumps(b)), copy.deepcopy(b)):
            self.assertEqual(restored.getVersificationDeclaration(), b.getVersificationDeclaration())
            self.assertEqual(restored.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertLess(len(pickle.dumps(b)), 10000)

    def test_old_objects_without_new_fields_are_undeclared(self):
        b = self.bible()
        del b._versificationState
        self.assertEqual(pickle.loads(pickle.dumps(b)).getVersificationDeclaration()['status'], 'undeclared')

    def test_minimal_bos_archive_preserves_declaration(self):
        b = self.bible()
        self.assertTrue(createPickledBible(b, outputFolder=self.folder))
        restored = PickledBible(self.folder)
        restored.preload()
        self.assertEqual(restored.getVersificationDeclaration(), b.getVersificationDeclaration())
        self.assertEqual(restored.convertToReferenceVersification(*ref()), ref(32, 1))

    def test_new_caller_override_wins_over_saved_declaration(self):
        self.assertTrue(createPickledBible(self.bible(), outputFolder=self.folder))
        restored = PickledBible(self.folder, versification='org')
        restored.preload()
        self.assertEqual(restored.getVersificationSystemName(), 'org')
        self.assertIn('VERSIFICATION_CONFLICT', {d['code'] for d in restored.getVersificationDeclaration()['diagnostics']})

    def test_fast_archive_keeps_declaration_with_lazy_books(self):
        usfm(self.folder)
        b = USFMBible(self.folder, givenName='Test Bible', givenAbbreviation='TEST', versification='eng')
        b.load()
        self.assertTrue(b.pickleFast(self.folder))
        restored = PickledBible(self.folder / 'TEST.BOSBible')
        self.assertFalse(restored.books)
        self.assertEqual(restored.getVersificationSystemName(), 'eng')
        self.assertEqual(restored.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertIn('Test sentence 55.', restored.getVerseText(SimpleVerseKey('GEN', '31', '55')))
        self.assertIs(restored.books['GEN'].containerBibleObject, restored)
        overridden = PickledBible(self.folder / 'TEST.BOSBible', versification='org')
        self.assertEqual(overridden.getVersificationSystemName(), 'org')
        self.assertIn('VERSIFICATION_CONFLICT', {d['code'] for d in overridden.getVersificationDeclaration()['diagnostics']})

    def test_zipped_minimal_archive_keeps_declarations_and_loaded_text(self):
        usfm(self.folder)
        b = USFMBible(self.folder, givenName='Test', givenAbbreviation='TEST', versification='eng')
        b.load()
        output = self.folder / 'output'
        output.mkdir()
        self.assertTrue(createPickledBible(b, outputFolder=output, zipOnly=True))
        restored = PickledBible(next(output.glob('*.zip')))
        restored.preload()
        self.assertEqual(restored.convertToReferenceVersification(*ref()), ref(32, 1))
        self.assertIn('Test sentence 55.', restored.getVerseText(SimpleVerseKey('GEN', '31', '55')))

    def test_old_minimal_archive_without_declaration_remains_undeclared(self):
        b = Bible()
        b.name = 'Old Bible'
        self.assertTrue(createPickledBible(b, outputFolder=self.folder))
        restored = PickledBible(self.folder)
        restored.preload()
        self.assertEqual(restored.getVersificationDeclaration()['status'], 'undeclared')

    def test_state_contains_only_versioned_declarations(self):
        state = json.loads(self.bible()._versificationState)
        self.assertEqual(set(state), {'version', 'explicit', 'metadata'})
        self.assertEqual(state['version'], 1)


class DocumentationAndDistributionTests(BibleTestCase):
    def test_documented_python_examples(self):
        guide = Path(__file__).resolve().parents[1] / 'Documentation/BibleVersification.md'
        namespace = {}
        for index, example in enumerate(re.findall(r'```python\n(.*?)```', guide.read_text(), re.DOTALL)):
            with self.subTest(example=index):
                exec(compile(example, str(guide), 'exec'), namespace)

    @unittest.skipUnless(os.environ.get('BOS_VERSIFICATION_TEST_WHEEL'), 'Set BOS_VERSIFICATION_TEST_WHEEL to test an installed wheel.')
    def test_wheel_loads_a_bible_and_converts_without_checkout(self):
        wheel = Path(os.environ['BOS_VERSIFICATION_TEST_WHEEL']).resolve()
        installed = self.folder / 'installed'
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(installed)
        data = self.folder / 'data'
        data.mkdir()
        usfm(data)
        code = '''import sys
sys.path.insert(0, sys.argv[1])
from BibleOrgSys.Formats import USFMBible
assert USFMBible.__file__.startswith(sys.argv[1])
from BibleOrgSys import BibleOrgSysGlobals
BibleOrgSysGlobals.preloadCommonData()
b = USFMBible.USFMBible(sys.argv[2], versification='eng')
b.load()
assert b.convertToReferenceVersification('GEN',31,55) == ('GEN','32','1',None)
assert b.convertToReferenceVersification('NUM',26,1,detailed=True).references == (('NUM','25','19',None),('NUM','26','1',None))
assert b.convertFromReferenceVersification('NUM',26,1,detailed=True).status.value == 'partial'
'''
        result = subprocess.run([sys.executable, '-I', '-c', code, str(installed), str(data)],
                                cwd=self.folder, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
