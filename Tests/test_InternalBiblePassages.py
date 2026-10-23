# SPDX-License-Identifier: MPL-2.0
"""Offline mapped-text retrieval tests; no OBD or rendering dependencies.

Run with BOS's native dependencies installed:
    .venv/bin/python -m unittest discover -s Tests -p test_InternalBiblePassages.py
"""
import logging
import pickle
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from BibleOrgSys.Bible import Bible
from BibleOrgSys.Formats.USFMBible import USFMBible
from BibleOrgSys.Internals.InternalBiblePassages import (
    MappedBiblePassage, MissingPassageBookError, MissingPassageVerseError,
    PassagePortion, passageReferencesFromEntries,
)
import BibleOrgSys.Reference.BibleVersification as bv
import BibleOrgSys.Reference.BibleVersificationMappings as vm
from BibleOrgSys.Reference.BibleVersificationMappings import (
    AmbiguousMappingError, InvalidReferenceError, MappingStatus, PartialMappingError,
    UnsupportedMappingError, VersificationMappingEngine,
)
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem


class PassageTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.number = 0
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def bible(self, text, BBB='GEN', system='org', lazy=False):
        self.number += 1
        folder = self.root / str(self.number)
        folder.mkdir()
        (folder / f'{BBB}.usfm').write_text(f'\\id {BBB}\n\\h {BBB}\n{text}')
        bible = USFMBible(folder, versification=system)
        if lazy:
            bible.preload()
        else:
            bible.load()
        return bible

    def text(self, portions):
        return ' '.join(e.getCleanText() for portion in portions for e in portion.entries
                        if e.getMarker() in ('d','v~'))

    def test_public_mapping_accepts_name_system_or_bible_and_keeps_provenance(self):
        bible = self.bible('\\c 3\n\\p\n'+''.join(f'\\v {v} Native-{v}.\n' for v in range(19,25)), 'MAL')
        references = [('MAL',4,v) for v in range(1,7)]
        for source in ('eng',BibleVersificationSystem('eng'),Bible(versification='eng')):
            with self.subTest(source=type(source)):
                result = bible.getMappedPassage(source,iter(references),combineAdjacent=True)
                self.assertIsInstance(result,MappedBiblePassage)
                self.assertEqual(result.mapping.status,MappingStatus.EXACT)
                self.assertEqual(result.mapping.source_system,'eng')
                self.assertEqual(result.mapping.target_system,'org')
                self.assertEqual(result.mapping.references,
                                 tuple(('MAL','3',str(v),None) for v in range(19,25)))
                self.assertTrue(result.mapping.provenance)
                self.assertTrue(result.mapping.data_revision)
                self.assertEqual(len(result.portions),1)
                self.assertEqual(result.portions[0].reference,('MAL','3','19'))
                self.assertIn('Native-24.',self.text(result.portions))

    def test_reviewed_absence_is_opt_in_partial_and_keeps_native_words(self):
        bible = self.bible('\\c 7\n\\v 67 singers¦11\n\\v 68 camels¦22\n', 'NEH')
        refs = [('NEH',7,67),('NEH',7,68),('NEH',7,69)]
        with self.assertRaises(UnsupportedMappingError):
            bible.getMappedPassage('eng',refs)
        mapped = bible.getMappedPassage('eng',refs,allowAbsent=True)
        self.assertEqual(mapped.mapping.status,MappingStatus.PARTIAL)
        self.assertEqual(mapped.absent_source_references,(('NEH','7','68',None),))
        self.assertEqual(mapped.native_references,(('NEH','7','67',None),('NEH','7','68',None)))
        self.assertIn('camels¦22',self.text(mapped.portions))
        self.assertTrue(mapped.mapping.diagnostics)
        absent = bible.getMappedPassage('eng',[('NEH',7,68)],allowAbsent=True)
        self.assertEqual(absent.mapping.status,MappingStatus.PARTIAL)
        self.assertFalse(absent.portions)
        with self.assertRaises(UnsupportedMappingError):
            bible.getMappedPassage('Original',refs,allowAbsent=True)
        with self.assertRaises(KeyError):
            bible.getMappedPassage('eng',[('NEH',7,70)],allowAbsent=True)

    def test_default_keeps_verse_portions_separate(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1 One.\n\\v 2 Two.\n')
        result = bible.getMappedPassage('eng',[('GEN',1,1),('GEN',1,2)])
        self.assertEqual(len(result.portions),2)
        self.assertIsInstance(result.portions[0],PassagePortion)
        self.assertEqual(result.portions[0].context,['chapters','c'])

    def test_malformed_stored_labels_identify_bible_and_source_file(self):
        bible = self.bible('\\c 13\n\\p\n\\v 7And malformed text.\n')
        bible.abbreviation = 'BAD-LABEL'
        entries,context = bible.getContextVerseData(('GEN','13','7And'),strict=True)
        # A native index can return a malformed stored label for a numeric lookup.
        cache = {(id(bible),'GEN','13'):{'7':(entries,context)}}
        for retrieve in (
                lambda: bible.getPassageData([('GEN',13,7)],chapterCache=cache),
                lambda: bible.getMappedPassage('org',[('GEN',13,7)],chapterCache=cache),
                lambda: passageReferencesFromEntries(('GEN','13'),entries,bible),
                lambda: passageReferencesFromEntries(('GEN','13'),entries,'org',sourceBible=bible)):
            with self.assertRaisesRegex(ValueError,'Unsupported source verse label') as caught:
                retrieve()
            message = str(caught.exception)
            self.assertIn('BAD-LABEL',message)
            self.assertIn('7And',message)
            self.assertIn('GEN 13:',message)
            self.assertIn(str(self.root/'1'/'GEN.usfm'),message)
            self.assertEqual(str(pickle.loads(pickle.dumps(caught.exception))),message)

    def test_bos_exception_payloads_and_notes_survive_pickle(self):
        result = vm.MappingResult('eng','org',(('ACT','19','41',None),),vm.MappingStatus.PARTIAL)
        for error in (vm.VersificationMappingError(result),vm.PartialMappingError(result),
                      vm.AmbiguousMappingError(result),vm.UnsupportedMappingError(result),
                      vm.InvalidReferenceError(result),vm.MultipleReferencesError(result),
                      MissingPassageBookError(('SA1','13','7')),
                      MissingPassageVerseError(('SA1','13','7'))):
            with self.subTest(error=type(error).__name__):
                error.add_note('Bible KJB-1611')
                restored = pickle.loads(pickle.dumps(error))
                self.assertIs(type(restored),type(error))
                self.assertEqual(str(restored),str(error))
                self.assertEqual(restored.__dict__,error.__dict__)

    def test_cross_chapter_mapping_retains_native_context_and_order(self):
        bible = self.bible('\\c 31\n\\p\n\\v 54 Last.\n\\c 32\n\\p\n'
                           '\\v 1 Boundary.\n\\v 2 Following.\n')
        passage = bible.getMappedPassage('eng',[('GEN',31,54),('GEN',31,55)],combineAdjacent=True)
        self.assertEqual([p.reference for p in passage.portions],[('GEN','31','54'),('GEN','32','1')])
        self.assertIn('Boundary.',self.text(passage.portions))
        self.assertNotIn('Following.',self.text(passage.portions))

    def test_complete_merge_and_partial_group_exception(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1 Merged.\n')
        engine = VersificationMappingEngine({'maxVerses':{'GEN':[1]}}, {
            'eng':{'maxVerses':{'GEN':[2]},'groupMappings':[{'source':'GEN 1:1-2','target':'GEN 1:1'}]},
            'org':{'maxVerses':{'GEN':[1]},'identityBooks':{'GEN':'GEN'}},
        })
        with patch.object(bv,'get_default_mapping_engine',return_value=engine):
            result = bible.getMappedPassage('eng',[('GEN',1,1),('GEN',1,2)])
            self.assertEqual(self.text(result.portions),'Merged.')
            with self.assertRaises(PartialMappingError) as caught:
                bible.getMappedPassage('eng',[('GEN',1,1)])
            self.assertEqual(caught.exception.result.status,MappingStatus.PARTIAL)

    def test_discontinuous_mapping_does_not_fetch_an_enclosing_range(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1 First.\n\\v 2 Unrelated.\n\\v 3 Third.\n')
        engine = VersificationMappingEngine({'maxVerses':{'GEN':[3]}}, {
            'eng':{'maxVerses':{'GEN':[2]},'mappedVerses':{'GEN 1:1':'GEN 1:3','GEN 1:2':'GEN 1:1'}},
            'org':{'maxVerses':{'GEN':[3]},'identityBooks':{'GEN':'GEN'}},
        })
        with patch.object(bv,'get_default_mapping_engine',return_value=engine):
            result = bible.getMappedPassage('eng',[('GEN',1,1),('GEN',1,2)],combineAdjacent=True)
        self.assertEqual(self.text(result.portions),'Third. First.')
        self.assertEqual([p.reference[2] for p in result.portions],['3','1'])

    def test_acts_19_same_system_and_combined_original_text_keep_native_word_ids(self):
        rv = self.bible('\\c 19\n\\p\n\\v 40 Speech¦98355.\n\\v 41 Dismissal¦98365.\n','ACT','eng')
        lv = self.bible('\\c 19\n\\p\n\\v 40 Speech¦98355. Dismissal¦98365.\n','ACT','org')
        for verse, word in ((40,'Speech'),(41,'Dismissal')):
            with self.subTest(verse=verse):
                english = rv.getMappedPassage('eng',[('ACT',19,verse)],expandGroups=True)
                self.assertFalse(english.mapping.is_expanded)
                self.assertEqual(len(english.mapping.references),1)
                self.assertIn(word,self.text(english.portions))
                original = lv.getMappedPassage('eng',[('ACT',19,verse)],expandGroups=True)
                self.assertTrue(original.mapping.is_expanded)
                self.assertEqual(original.mapping.source_references,
                                 (('ACT','19','40',None),('ACT','19','41',None)))
                self.assertEqual(original.mapping.requested_references,(('ACT','19',str(verse),None),))
                self.assertEqual(original.native_references,(('ACT','19','40',None),))
                self.assertEqual(original.portions[0].reference,('ACT','19','40'))
                self.assertEqual(self.text(original.portions),'Speech¦98355. Dismissal¦98365.')

    def test_stored_bridge_expands_coverage_and_cascades_through_mapping(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1-2 Combined¦42.\n')
        result = bible.getMappedPassage('org',[['GEN',1,2]],expandGroups=True)
        self.assertTrue(result.mapping.is_expanded)
        self.assertEqual(result.mapping.source_references,(('GEN','1','1',None),('GEN','1','2',None)))
        self.assertEqual(self.text(result.portions),'Combined¦42.')

        engine = VersificationMappingEngine({'maxVerses':{'GEN':[2]}}, {
            'eng':{'maxVerses':{'GEN':[3]},'groupMappings':[{'source':'GEN 1:1-2','target':'GEN 1:1'}],
                   'mappedVerses':{'GEN 1:3':'GEN 1:2'}},
            'org':{'maxVerses':{'GEN':[2]},'identityBooks':{'GEN':'GEN'}},
        })
        with patch.object(bv,'get_default_mapping_engine',return_value=engine):
            result = bible.getMappedPassage('eng',[('GEN',1,1)],expandGroups=True)
        self.assertEqual(result.mapping.source_references,tuple(('GEN','1',str(v),None) for v in (1,2,3)))
        self.assertEqual(result.mapping.requested_references,(('GEN','1','1',None),))
        self.assertEqual(len(result.portions),1)
        self.assertEqual(self.text(result.portions),'Combined¦42.')

    def test_unmapped_extra_text_in_stored_bridge_is_not_reported_as_exact(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1-2 Bridge.\n')
        engine = VersificationMappingEngine({'maxVerses':{'GEN':[2]}}, {
            'eng':{'maxVerses':{'GEN':[1]},'identityBooks':{'GEN':'GEN'}},
            'org':{'maxVerses':{'GEN':[2]},'identityBooks':{'GEN':'GEN'}},
        })
        with patch.object(bv,'get_default_mapping_engine',return_value=engine):
            with self.assertRaises(PartialMappingError):
                bible.getMappedPassage('eng',[('GEN',1,1)],expandGroups=True)

    def test_native_access_needs_no_declaration_and_can_span_books(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1 Genesis.\n')
        other = self.bible('\\c 1\n\\p\n\\v 1 Exodus.\n','EXO')
        bible.books['EXO'] = other.books['EXO']
        bible.clearVersificationSystem()
        portions = bible.getPassageData([('GEN',1,1),('EXO',1,1)],combineAdjacent=True)
        self.assertEqual(len(portions),2)
        self.assertEqual(self.text(portions),'Genesis. Exodus.')
        self.assertEqual(bible.getPassageData([]),())

    def test_bridges_whole_verses_and_exact_suffixes(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1-2 Bridge.\n\\v 3a First half.\n\\v 3b Second half.\n')
        portions = bible.getPassageData([('GEN',1,1),('GEN',1,2),('GEN',1,3),('GEN',1,3,'a')])
        self.assertEqual(len(portions),3)
        self.assertEqual(self.text(portions),'Bridge. First half. Second half.')
        self.assertEqual(portions[1].reference,('GEN','1','3a'))
        self.assertEqual(self.text(bible.getPassageData([('GEN',1,3,'b')])),'Second half.')
        # Asking for half a storage bridge returns the indivisible stored span.
        self.assertEqual(self.text(bible.getPassageData([('GEN',1,2)])),'Bridge.')
        with self.assertRaises(MissingPassageVerseError):
            bible.getPassageData([('GEN',1,3,'c')])

    def test_lazy_books_and_both_chapter_cache_access_paths(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1-2 Bridge.\n',lazy=True)
        self.assertNotIn('GEN',bible.books)
        cache = {}
        self.assertEqual(self.text(bible.getPassageData([('GEN',1,1)],chapterCache=cache)),'Bridge.')
        self.assertIn('GEN',bible.books)
        self.assertIn((id(bible),'GEN','1'),cache)
        index = bible['GEN']._CVIndex
        class BulkIndex:
            def getChapterVerseEntriesWithContext(self, chapter):
                return {'1-2':bible.getContextVerseData(('GEN',chapter,'1-2'),strict=True)}
        # The stand-in uses saved data: Bible's scalar accessor itself needs the
        # original index. Precompute before replacing it.
        bridge = bible.getContextVerseData(('GEN','1','1-2'),strict=True)
        with patch.object(BulkIndex,'getChapterVerseEntriesWithContext',return_value={'1-2':bridge}), \
             patch.object(bible.books['GEN'],'_CVIndex',BulkIndex()), \
             patch.object(bible,'getContextVerseData',return_value=bridge):
            result = bible.getPassageData([('GEN',1,1),('GEN',1,2)])
        self.assertIs(bible['GEN']._CVIndex,index)
        self.assertEqual(len(result),1)

    def test_returned_lists_cannot_mutate_cached_passages(self):
        bible = self.bible('\\c 1\n\\p\n\\v 1 One.\n\\v 2 Two.\n')
        cache = {}
        first = bible.getPassageData([('GEN',1,1)],chapterCache=cache)[0]
        first.entries.extend(bible.getPassageData([('GEN',1,2)])[0].entries)
        first.context.append('changed')
        again = bible.getPassageData([('GEN',1,1)],chapterCache=cache)[0]
        self.assertEqual(self.text([again]),'One.')
        self.assertNotIn('changed',again.context)

    def test_missing_book_or_later_verse_never_returns_a_partial_passage(self):
        bible = self.bible('\\c 3\n\\p\n\\v 19 First.\n','MAL')
        with self.assertRaises(MissingPassageVerseError) as caught:
            bible.getMappedPassage('eng',[('MAL',4,1),('MAL',4,2)])
        self.assertEqual(caught.exception.reference,('MAL','3','20'))
        with self.assertRaises(MissingPassageBookError) as caught:
            bible.getMappedPassage('eng',[('GEN',1,1)])
        self.assertEqual(caught.exception.reference,('GEN','1','1'))

    def test_non_exact_mappings_fail_before_loading_text(self):
        for target,source,refs,error in (
            ('eng','KJV',[('TOB',1,1)],UnsupportedMappingError),
            # Supplement revision 2 makes this an incomplete atomic group.
            ('org','eng',[('PSA',13,5)],PartialMappingError),
            ('org','rsc',[('PSA',9,22)],AmbiguousMappingError),
            ('eng','eng',[('GEN',0,1)],InvalidReferenceError),
            ('eng','eng',[],InvalidReferenceError),
        ):
            bible = Bible(versification=target)
            with patch.object(bible,'loadBookIfNecessary',side_effect=AssertionError('must not load')):
                with self.subTest(source=source,target=target,refs=refs), self.assertRaises(error):
                    bible.getMappedPassage(source,refs)

    def test_conflicting_declarations_on_either_bible_remain_ambiguous(self):
        declared = Bible(versification='eng')
        conflict = Bible()
        conflict._recordVersificationMetadata('A','Versification','eng')
        conflict._recordVersificationMetadata('B','Versification','org')
        for target,source in ((conflict,declared),(declared,conflict)):
            with self.subTest(target=target.getVersificationSystemName()):
                with self.assertRaises(AmbiguousMappingError) as caught:
                    target.getMappedPassage(source,[('GEN',1,1)])
                self.assertTrue(any(d.code=='VERSIFICATION_CONFLICT' for d in caught.exception.result.diagnostics))
        conflict.setVersificationSystem('eng')
        result = declared.convertReferencesFromVersification(conflict,[('GEN',1,1)])
        self.assertEqual(result.status,MappingStatus.EXACT)
        self.assertTrue(any(d.code=='VERSIFICATION_CONFLICT' for d in result.diagnostics))

    def test_entry_references_include_only_declared_titles_and_preserve_suffixes(self):
        bible = self.bible('\\c 3\n\\d Separate title.\n\\q1\n\\v 1 First.\n\\v 2-3 Bridge.\n'
                           '\\v 4a Part.\n\\c 98\n\\d Inline title.\n\\q1\n\\v 1 Next.\n','PSA','eng')
        entries,_ = bible.getContextVerseData(('PSA',))
        expected = (('PSA','3','0',None),('PSA','3','1',None),('PSA','3','2',None),
                    ('PSA','3','3',None),('PSA','3','4','a'),('PSA','98','1',None))
        for source in ('eng',BibleVersificationSystem('eng'),bible):
            self.assertEqual(passageReferencesFromEntries(('PSA','-1'),entries,source),expected)
        intro = entries[:next(n for n,e in enumerate(entries) if e.getMarker()=='c')]
        self.assertEqual(passageReferencesFromEntries(('PSA','-1'),intro,'eng'),())

    def test_mapped_title_stays_separate_from_numbered_text(self):
        bible = self.bible('\\c 3\n\\p\n\\v 1 Native title.\n\\v 2 Native first.\n','PSA')
        title = bible.getMappedPassage('eng',[('PSA',3,0)])
        verse = bible.getMappedPassage('eng',[('PSA',3,1)])
        self.assertEqual(self.text(title.portions),'Native title.')
        self.assertEqual(self.text(verse.portions),'Native first.')


if __name__ == '__main__':
    unittest.main()
