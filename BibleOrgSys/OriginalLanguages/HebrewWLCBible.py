#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HebrewWLCBible.py
#
# Module handling Open Scriptures Hebrew WLC.
#
# Copyright (C) 2011-2020 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module handling the Hebrew WLC OSIS files from Open Scriptures.
"""
from gettext import gettext as _
from pathlib import Path
import os.path
import logging
import pickle

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.OriginalLanguages import Hebrew
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntry, InternalBibleExtra, parseWordAttributes
from BibleOrgSys.Formats.OSISXMLBible import OSISXMLBible
from BibleOrgSys.Formats.PickledBible import PickledBible, ZIPPED_PICKLE_FILENAME_END



LAST_MODIFIED_DATE = '2020-05-27' # by RJH
SHORT_PROGRAM_NAME = "HebrewWLCBibleHandler"
PROGRAM_NAME = "Hebrew WLC format handler"
PROGRAM_VERSION = '0.26'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


INPUT_RESOURCES_FOLDERPATH = Path( '/home/robert/Programming/WebDevelopment/OpenScriptures/' )

DEFAULT_OSIS_WLC_FILEPATH = INPUT_RESOURCES_FOLDERPATH.joinpath( 'morphhb/wlc/' )
DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH.joinpath( f'WLC{ZIPPED_PICKLE_FILENAME_END}' )

DEFAULT_GLOSSING_DICT_FILEPATH = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DATAFILES_FOLDERPATH.joinpath( 'ManuallyEditedFiles/', 'WLCHebrewGlosses.pickle' )
DEFAULT_GLOSSING_EXPORT_FILEPATH = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( 'WLCHebrewGlosses.txt' )
DEFAULT_GENERIC_GLOSSING_REVERSE_EXPORT_FILEPATH = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( 'WLCHebrewGenericGlossesReversed.txt' )

ORIGINAL_MORPHEME_BREAK_CHAR = '/'
OUR_MORPHEME_BREAK_CHAR = '='

PART_OF_SPEECH_ABBREVIATION_DICT = { 'A':_("Aj"), 'C':_("Cn"), 'D':_("Av"),
             'N':_("N"), 'P':_("Pn"), 'R':_("Pr"),
             'S':_("S"), 'T':_("Pa"), 'V':_("V") }
PART_OF_SPEECH_NAME_DICT = { 'A':_("adjective"), 'C':_("conjunction"), 'D':_("adverb"),
             'N':_("noun"), 'P':_("pronoun"), 'R':_("preposition"),
             'S':_("suffix"), 'T':_("particle"), 'V':_("verb") }
# Next one doesn't include verbs
PART_OF_SPEECH_TYPE_DICT = { 'Aa':_("adjective"), 'Ac':_("cardinal number"), 'Ag':_("gentillic"), 'Ao':_("ordinal number"),
                  'C':_("conjunction"), 'D':_("adverb"),
                  'Nc':_("common noun"), 'Ng':_("gentillic noun"), 'Np':_("proper name"),
                  'Pd':_("demonstrative pronoun"), 'Pf':_("indefinite pronoun"), 'Pi':_("interrogative pronoun"),
                            'Pp':_("personal pronoun"), 'Pr':_("relative pronoun"),
                  'R':_("preposition"), 'Rd':_("definite article"), # (Preposition type is optional)
                  'Sd':_("directional he suffix"), 'Sh':_("paragogic he suffix"),
                            'Sn':_("paragogic nun suffix"), 'Sp':_("pronominal suffix"),
                  'Ta':_("affirmation particle"), 'Td':_("definite article"), 'Te':_("exhortation particle"),
                            'Ti':_("interrogative particle"), 'Tj':_("interjection particle"),
                            'Tm':_("demonstrative particle"), 'Tn':_("negative particle"),
                            'To':_("direct object marker"), 'Tr':_("relative particle") }
HEBREW_VERB_STEMS = { 'q':'qal', 'N':'niphal', 'p':'piel', 'P':'pual', 'h':'hiphil', 'H':'hophal', 't':'hithpael',
                      'o':'polel', 'O':'polal', 'r':'hithpolel', 'm':'poel', 'M':'poal', 'k':'palel', 'K':'pulal',
                      'Q':'qal passive', 'l':'pilpel', 'L':'polpal', 'f':'hithpalpel', 'D':'nithpael', 'j':'pealal',
                      'i':'pilel', 'u':'hothpaal', 'c':'tiphil', 'v':'hishtaphel', 'w':'nithpalel', 'y':'nithpoel',
                      'z':'hithpoel' }
ARAMAIC_VERB_STEMS = { 'q':'peal', 'Q':'peil', 'u':'hithpeel', 'p':'pael', 'P':'ithpaal', 'M':'hithpaal',
                       'a':'aphel', 'h':'haphel', 's':'saphel', 'e':'shaphel', 'H':'hophal', 'i':'ithpeel',
                       't':'hishtaphel', 'v':'ishtaphel', 'w':'hithaphel', 'o':'polel', 'z':'ithpoel',
                       'r':'hithpolel', 'f':'hithpalpel', 'b':'hephal', 'c':'tiphel', 'm':'poel',
                       'l':'palpel', 'L':'ithpalpel', 'O':'ithpolel', 'G':'ittaphal' }
VERB_CONJUGATION_TYPES = { 'p':'perfect (qatal)', 'q':'sequential perfect (weqatal)',
                           'i':'imperfect (yiqtol)', 'w':'sequential imperfect (wayyiqtol)',
                           'h':_("cohortative"), 'j':_("jussive"), 'v':_("imperative"), 'r':'participle active',
                           's':_("participle passive"), 'a':_("infinitive absolute"), 'c':_("infinitive construct") }
PERSON_NAMES = { '1':_("1st-person"), '2':_("2nd-person"), '3':_("3rd-person") }
GENDER_NAMES = { 'b':_("both(mf)"), 'c':_("common(mf)"), 'f':_("feminine"), 'm':_("masculine") } # b is for nouns, c is for verbs
NUMBER_NAMES = { 'd':_("dual"), 'p':_("plural"), 's':_("singular") }
STATE_NAMES = { 'a':_("absolute"), 'c':_("construct"), 'd':_("determined") }


class HebrewWLCBibleAddon():
    """
    Class for handling a Hebrew WLC object (which may contain one or more Bible books)

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """
    def __init__( self ):
        """
        Create an empty object.
        """
        fnPrint( debuggingThisModule, "HebrewWLCBibleAddon.__init__()" )

        self.glossingDict, self.haveGlossingDictChanges, self.loadedGlossEntryCount = None, False, 0
    # end of HebrewWLCBibleAddon.__init__


    def getVerseDictList( self, verseDataEntry, ref ):
        """
        Given a verseDataEntry (an InternalBibleEntry)
            return the text as a list of dictionaries (one for each word).

        e.g., {'word': 'הַ/מַּיִם', 'strong': 'd/4325', 'morph': 'HTd/Ncmpa', 'cantillationLevel': '0.1.1.0'}
        """
        fnPrint( debuggingThisModule, "getVerseDictList( {}, {} )".format( verseDataEntry, ref ) )
        assert isinstance( verseDataEntry, InternalBibleEntry )

        def handleExtra( thisExtra ):
            """
            Checks an extra to see if it's a ww extra (word attributes).

            If so, returns wwDict with word attributes.
            Otherwise, returns None.
            """
            vPrint( 'Never', debuggingThisModule, "handleExtra", thisExtra )

            if thisExtra.getType() == 'ww':
                wwField = thisExtra.getText()
                wwDict = parseWordAttributes( 'WLC', BBB, C, V, wwField, errorList=None )
                if 'morph' in wwDict and wwDict['morph'].startswith( 'OSHM:' ): # Open Scriptures Hebrew Morphology
                    wwDict['morph'] = wwDict['morph'][5:]
                #if 'morph' in wwDict and wwDict['morph'].startswith( 'H' ): # H for Hebrew, A for Aramaic
                    #wwDict['morph'] = wwDict['morph'][1:]
                vPrint( 'Never', debuggingThisModule, "wwDict", wwDict )
                return wwDict
            else:
                logging.warning( "WLC ignoring {} extra {} at {} for {}".format( thisExtra.getType(), thisExtra.getText(), ref, token ) )
        # end of getVerseDictList handleExtra

        # Start of getVerseDictList main code
        marker, originalMarker = verseDataEntry.getMarker(), verseDataEntry.getOriginalMarker()
        adjText = verseDataEntry.getAdjustedText()
        lineExtras = verseDataEntry.getExtras()
        if debuggingThisModule:
            for extra in lineExtras:
                vPrint( 'Quiet', debuggingThisModule, " {}".format( extra ) )
                ix = extra.getIndex()
                vPrint( 'Quiet', debuggingThisModule, "   {}".format( adjText[0 if ix<6 else ix-6:ix+1] ) )

        BBB,C,V = ref.getBCV()

        vPrint( 'Never', debuggingThisModule, "adjText", repr(adjText) )
        resultList = []
        ix = ixAdd = 0
        punctuation = ''
        for j,token in enumerate( adjText.split() ):
            vPrint( 'Never', debuggingThisModule, "token", j, repr(token) )
            ix += len(token)
            if token != '\\w': # ignore these:
                if token.endswith( '\\w*' ): token = token[:-3]
                elif token.endswith( '\\w' ):
                    token = token[:-2] # e.g., 'עַל\\w*־\\w'
                    ixAdd = 2
                    ix -= 2
                if '\\w*' in token: # e.g., 'הָ/אָֽרֶץ\\w*׃'
                    token, punctuation = token.split( '\\w*', 1 )
                    vPrint( 'Never', debuggingThisModule, "t,p", repr(token), repr(punctuation) )
                    #ixAdd += len( punctuation )
                    ix -= len( punctuation )
                vPrint( 'Never', debuggingThisModule, ix, "token", repr(token) )
                something = lineExtras.checkForIndex( ix ) if lineExtras else None # Could be moved lower if we remove assert after debugging
                wwDict = None
                if isinstance( something, InternalBibleExtra ):
                    wwDict = handleExtra( something )
                    #dPrint( 'Never', debuggingThisModule, "extra", something )
                    #if something.getType() == 'ww':
                        #wwField = something.getText()
                        #wwDict = parseWordAttributes( 'WLC', BBB, C, V, wwField, errorList=None )
                        #if 'morph' in wwDict and wwDict['morph'].startswith( 'OSHM:' ):
                            #wwDict['morph'] = wwDict['morph'][5:]
                        #dPrint( 'Never', debuggingThisModule, "wwDict", wwDict )
                    #else:
                        #logging.error( "Ignoring {} extra {} at {} for {}".format( something.getType(), something.getText(), ref, token ) )
                elif isinstance( something, list ):
                    #logging.critical( "Doesn't handle list of extras yet" )
                    #dPrint( 'Quiet', debuggingThisModule, "something", something )
                    #dPrint( 'Quiet', debuggingThisModule, "getVerseDictList( {}, {} )".format( verseDataEntry, ref ) )
                    for something2 in something:
                        #dPrint( 'Quiet', debuggingThisModule, "something2", something2 )
                        if isinstance( something2, InternalBibleExtra ):
                            result = handleExtra( something2 )
                            if result: wwDict = result
                        else: halt # Programming error -- what's this???
                elif something is not None:
                    vPrint( 'Quiet', debuggingThisModule, "HERE", something )
                    halt # Programming error -- what's this???
                resultList.append( wwDict if wwDict else {'word':token} )
                if punctuation:
                    ix += len( punctuation )
                    something = lineExtras.checkForIndex( ix ) # Could be moved lower if we remove assert after debugging
                    vPrint( 'Never', debuggingThisModule, "have punctuation", repr(punctuation), something )
                    resultList.append( {'word':punctuation} )
                    punctuation = ''
            #dPrint( 'Never', debuggingThisModule, "{}/{} ix={} token={!r} lemma={!r}".format( j+1, count, ix, token, lemma ) )
            ix += ixAdd + 1 # for space between words
            ixAdd = 0

        vPrint( 'Never', debuggingThisModule, "getVerseDictList returning: {}".format( resultList ) )
        return resultList
    # end of HebrewWLCBibleAddon.getVerseDictList


    def expandMorphologyAbbreviations( self, morphAbbrev ):
        """
        Return a longer string with the morphology abbreviation(s) converted to something more readable.
        """
        fnPrint( debuggingThisModule, "HebrewWLCBibleAddon.expandMorphologyAbbreviations( {} )".format( morphAbbrev ) )
        if not morphAbbrev: return ''

        if morphAbbrev.startswith( 'OSHM:' ): morphAbbrev = morphAbbrev[5:] # Open Scriptures Hebrew Morphology
        assert morphAbbrev[0] in 'HA' # Hebrew or Aramaic
        lgCode, morphAbbrev = morphAbbrev[0], morphAbbrev[1:]

        def handleRemainder( remainder ):
            resultString = ''
            if remainder:
                for p in PERSON_NAMES:
                    if remainder[0] == p:
                        resultString += ' ' + PERSON_NAMES[p]
                        remainder = remainder[1:]
                        break
            if remainder:
                for g in GENDER_NAMES:
                    if remainder[0] == g:
                        resultString += ' ' + GENDER_NAMES[g]
                        remainder = remainder[1:]
                        break
            if remainder:
                for n in NUMBER_NAMES.keys():
                    if remainder[0] == n:
                        resultString += ' ' + NUMBER_NAMES[n]
                        remainder = remainder[1:]
                        break
            if remainder:
                for s in STATE_NAMES.keys():
                    if remainder[0] == s:
                        resultString += ' ' + STATE_NAMES[s]
                        remainder = remainder[1:]
                        break
            if remainder:
                resultString += ' <<<' + remainder + '>>>'
                if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag: halt
            return resultString
        # end of expandMorphologyAbbreviations.handleRemainder

        resultString = ''
        for bit in morphAbbrev.split( '/' ):
            if resultString: resultString += ' / '
            #dPrint( 'Quiet', debuggingThisModule, "bit", bit )
            assert bit[0] in 'ACDNPRSTV'
            if bit[0] == 'V': # most complex
                resultString += HEBREW_VERB_STEMS[bit[1]] if lgCode=='H' else ARAMAIC_VERB_STEMS[bit[1]]
                resultString += ' ' + _("verb")
                resultString += ' ' + VERB_CONJUGATION_TYPES[bit[2]].replace( ' ', '_' )
                resultString += handleRemainder( bit[3:] )
            elif len(bit) > 2: # More complex
                resultString += PART_OF_SPEECH_TYPE_DICT[bit[:2]].replace( ' ', '_' )
                resultString += handleRemainder( bit[2:] )
            else: resultString += PART_OF_SPEECH_TYPE_DICT[bit].replace( ' ', '_' )
        return resultString
    # end of HebrewWLCBibleAddon.expandMorphologyAbbreviations


#####################################################################################################################
#
# Functions for normalising Hebrew words
#
    def removeMorphemeBreaks( self, text=None ):
        """
        Return the text with morpheme break marks removed.
        """
        if text is None:
            self.currentText = self.currentText.replace('=', '') if self.currentText else self.currentText
            return self.currentText
        # else we were passed a text string
        return text.replace('=', '')
    # end of HebrewWLCBibleAddon.removeMorphemeBreaks

    def removeCantillationMarks( self, text=None, removeMetegOrSiluq=False ):
        """
        Return the text with cantillation marks removed.
        """
        #dPrint( 'Quiet', debuggingThisModule, "removeCantillationMarks( {!r}, {} )".format( text, removeMetegOrSiluq ) )

        if text is None:
            # Recursive call
            self.currentText = self.removeCantillationMarks( self.currentText, removeMetegOrSiluq ) if self.currentText else self.currentText
            return self.currentText

        # else we were passed a text string
        h = Hebrew.Hebrew( text )
        return h.removeCantillationMarks( removeMetegOrSiluq=removeMetegOrSiluq )
    # end of HebrewWLCBibleAddon.removeCantillationMarks

    def removeVowelPointing( self, text=None, removeMetegOrSiluq=False ):
        """
        Return the text with cantillation marks removed.
        """
        if text is None:
            # Recursive call
            self.currentText = self.removeVowelPointing( self.currentText ) if self.currentText else self.currentText
            return self.currentText
        # else we were passed a text string
        h = Hebrew.Hebrew( text )
        return h.removeVowelPointing( None, removeMetegOrSiluq )
    # end of HebrewWLCBibleAddon.removeVowelPointing


#####################################################################################################################
#
# Functions for handling our glossing dictionary
#
    def _checkLoadedDict( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "_checkLoadedDict()" )
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.glossingDict

        vPrint( 'Quiet', debuggingThisModule, f"Checking {self.loadedGlossEntryCount:,} loaded Hebrew gloss entries for consistency…" )
        for word,(genericGloss,genericReferencesList,specificReferencesDict) in self.glossingDict.copy().items(): # Use a copy because we can modify it
            #dPrint( 'Quiet', debuggingThisModule, repr(word), repr(genericGloss), genericReferencesList )
            assert isinstance( word, str ) and word
            assert isinstance( genericGloss, str ) and genericGloss
            assert isinstance( genericReferencesList, list )
            if ' ' in word or ORIGINAL_MORPHEME_BREAK_CHAR in word:
                logging.critical( _("Removing invalid Hebrew (normalized) word: {!r}").format( word ) )
                del self.glossingDict[word]
                self.haveGlossingDictChanges = True
                continue
            if ' ' in genericGloss:
                logging.critical( _("Removing {!r} word with invalid generic gloss: {!r}").format( word, genericGloss ) )
                del self.glossingDict[word]
                self.haveGlossingDictChanges = True
                continue
            if genericReferencesList:
                for reference in genericReferencesList:
                    assert isinstance( reference, tuple )
                    assert len(reference) == 4 # BBB,C,V,word# (starting with 1)
                    for part in reference:
                        assert isinstance( part, str ) # We don't use INTs for references
                    assert genericReferencesList.count( reference ) == 1 # Don't allow multiples
            else: # the genericReferencesList is empty!
                logging.critical( _("Removing {!r} = {!r} entry with no references").format( word, genericGloss ) )
                del self.glossingDict[word]
                self.haveGlossingDictChanges = True
                continue
            #self.glossingDict[word] = (genericGloss,genericReferencesList,{})
            #self.haveGlossingDictChanges = True; continue
            for reference,specificGloss in specificReferencesDict.items():
                vPrint( 'Quiet', debuggingThisModule, "{!r} {!r} {} {!r}".format( word, genericGloss, reference, specificGloss ) )
                assert isinstance( reference, tuple )
                assert len(reference) == 4 # BBB,C,V,word# (starting with 1)
                for part in reference:
                    assert isinstance( part, str ) # We don't use INTs for references
                assert reference in genericReferencesList
                assert isinstance( specificGloss, str ) and specificGloss
                assert ' ' not in specificGloss
                #assert ORIGINAL_MORPHEME_BREAK_CHAR not in specificGloss
                #assert OUR_MORPHEME_BREAK_CHAR not in specificGloss
                assert specificGloss != genericGloss # Just leave it blank if they're the same
        vPrint( 'Quiet', debuggingThisModule, "  "+_("Finished checking Hebrew glosses") )
    # end of HebrewWLCBibleAddon._checkLoadedDict



    def loadGlossingDict( self, glossingDictFilepath=None ):
        """
        """
        self.glossingDictFilepath = glossingDictFilepath
        if glossingDictFilepath is None:
            self.glossingDictFilepath = DEFAULT_GLOSSING_DICT_FILEPATH

        # Read our glossing data from the pickle file
        if BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, _("Loading Hebrew glossing dictionary from '{}'…").format( self.glossingDictFilepath ) )
        with open( self.glossingDictFilepath, 'rb' ) as pickleFile:
            self.glossingDict = pickle.load( pickleFile )
            # It's a dictionary with (pointed and parsed) Hebrew keys and 2-tuple entries
            #   Hebrew keys have morphological breaks separated by =
            #   2-tuple entries consist of a generic gloss,
            #      (with generic gloss alternatives separated by /)
            #   followed by a list of currently known/parsed references
            #dPrint( 'Quiet', debuggingThisModule, "glossingDict:", self.glossingDict )
        self.loadedGlossEntryCount = len( self.glossingDict )
        self.haveGlossingDictChanges = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "  "+_("{:,} Hebrew gloss entries read.").format( self.loadedGlossEntryCount ) )

        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
            self._checkLoadedDict()
            if self.haveGlossingDictChanges: self.saveAnyChangedGlosses( exportAlso=True )
    # end of HebrewWLCBibleAddon.loadGlossingDict


    def saveAnyChangedGlosses( self, exportAlso=False ):
        """
        Save the glossing dictionary to a pickle file.
        """
        fnPrint( debuggingThisModule, "saveAnyChangedGlosses()" )

        if self.haveGlossingDictChanges:
            BibleOrgSysGlobals.backupAnyExistingFile( self.glossingDictFilepath, numBackups=9 )
            if BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
                vPrint( 'Quiet', debuggingThisModule, "  Saving Hebrew glossing dictionary ({}->{} entries) to '{}'…".format( self.loadedGlossEntryCount, len(self.glossingDict), self.glossingDictFilepath ) )
            elif BibleOrgSysGlobals.verbosityLevel > 1:
                vPrint( 'Quiet', debuggingThisModule, "  Saving Hebrew glossing dictionary ({}->{} entries)…".format( self.loadedGlossEntryCount, len(self.glossingDict) ) )
            with open( self.glossingDictFilepath, 'wb' ) as pickleFile:
                pickle.dump( self.glossingDict, pickleFile )

            if exportAlso: self.exportGlossingDictionary()
    # end of HebrewWLCBibleAddon.saveAnyChangedGlosses


    def importGlossingDictionary( self, glossingDictImportFilepath=None, overrideFlag=False ):
        """
        Import the glossing dictionary from (an exported or handcrafted) text file.

        NOTE: Usually we use the much faster loadGlossingDict (load pickle) function above.

        The overrideFlag lets you override an already-loaded glossing dictionary.
        """
        import ast
        #dPrint( 'Quiet', debuggingThisModule, "importGlossingDictionary()" )
        if glossingDictImportFilepath is None: glossingDictImportFilepath = DEFAULT_GLOSSING_EXPORT_FILEPATH

        if self.haveGlossingDictChanges:
            vPrint( 'Quiet', debuggingThisModule, _("Import disallowed because you already have glossing changes!") )
        elif self.glossingDict and not overrideFlag:
            vPrint( 'Quiet', debuggingThisModule, _("Import disallowed because you have already loaded the glossing dictionary") )
        else:
            vPrint( 'Normal', debuggingThisModule, "Importing glossing dictionary from '{}'…".format( glossingDictImportFilepath ) )
            lineCount = 0
            newDict = {}
            with open( glossingDictImportFilepath, 'r' ) as importFile:
                for line in importFile:
                    lineCount += 1
                    if lineCount==1 and line[0]==chr(65279): #U+FEFF
                        logging.info( "importGlossingDictionary: Detected UTF-16 Byte Order Marker in {}".format( glossingDictImportFilepath ) )
                        line = line[1:] # Remove the UTF-8 Byte Order Marker
                    if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    bits = line.split( '  ' )
                    #dPrint( 'Quiet', debuggingThisModule, "bits", bits )
                    if len(bits) == 4:
                        referencesText, specificReferencesDictText, genericGloss, word = bits
                        if not referencesText or not specificReferencesDictText or not genericGloss or not word:
                            vPrint( 'Quiet', debuggingThisModule, "  Empty field error" )
                        elif ' ' in genericGloss \
                        or genericGloss.count(OUR_MORPHEME_BREAK_CHAR)!=word.count(OUR_MORPHEME_BREAK_CHAR):
                            vPrint( 'Quiet', debuggingThisModule, "  Bad generic gloss field error: {!r} for {!r}".format( genericGloss, word ) )
                        genericReferencesList = ast.literal_eval( referencesText )
                        #dPrint( 'Quiet', debuggingThisModule, "references", repr(referencesText), repr(genericReferencesList) )
                        assert isinstance( genericReferencesList, list )
                        specificReferencesDict = ast.literal_eval( specificReferencesDictText )
                        #dPrint( 'Quiet', debuggingThisModule, "references", repr(referencesText), repr(genericReferencesList) )
                        assert isinstance( specificReferencesDict, dict )
                        newDict[word] = (genericGloss,genericReferencesList,specificReferencesDict)
                    else:
                        vPrint( 'Quiet', debuggingThisModule, "  Ignored '{}' line at {} ({} bits)".format( line, lineCount, len(bits) ) )
            vPrint( 'Normal', debuggingThisModule, f"  Loaded {len(newDict):,} entries." )
            if len(newDict) > self.loadedGlossEntryCount-10: # Seems to have been successful
                if len(newDict) != self.loadedGlossEntryCount: vPrint( 'Quiet', debuggingThisModule, "  Went from {} to {} entries!".format( self.loadedGlossEntryCount, len(newDict) ) )
                self.glossingDict = newDict # Replace the dictionary with the upgraded one
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
                    self._checkLoadedDict()
    # end of HebrewWLCBibleAddon.importGlossingDictionary


    def exportGlossingDictionary( self, glossingDictExportFilepath=None ):
        """
        Export the glossing dictionary to a text file
            plus a reversed text file (without the references).

        Also does a few checks while exporting.
            (These can be fixed and then the file can be imported.)
        """
        #dPrint( 'Quiet', debuggingThisModule, "exportGlossingDictionary()" )
        if glossingDictExportFilepath is None:
            glossingDictExportFilepath = DEFAULT_GLOSSING_EXPORT_FILEPATH
        vPrint( 'Normal', debuggingThisModule, _("Exporting glossing dictionary ({:,} entries) to '{}'…").format( len(self.glossingDict), glossingDictExportFilepath ) )

        if not os.path.isdir( BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH ):
            vPrint( 'Info', debuggingThisModule, f"Creating folder {BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH}…")
            os.mkdir( BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH )

        BibleOrgSysGlobals.backupAnyExistingFile( glossingDictExportFilepath, numBackups=5 )
        with open( glossingDictExportFilepath, 'wt' ) as exportFile:
            for word,(genericGloss,genericReferencesList,specificReferencesDict) in self.glossingDict.items():
                if ' ' in word or '/' in word:
                    logging.error( _("Word {!r} has illegal characters").format( word ) )
                if ' ' in genericGloss:
                    logging.error( _("Generic gloss {!r} for {!r} has illegal characters").format( genericGloss, word ) )
                if word.count('=') != genericGloss.count('='):
                    logging.error( _("Generic gloss {!r} and word {!r} has different numbers of morphemes").format( genericGloss, word ) )
                if not genericReferencesList:
                    logging.error( _("Generic gloss {!r} for {!r} has no references").format( genericGloss, word ) )
                exportFile.write( '{}  {}  {}  {}\n'.format( genericReferencesList, specificReferencesDict, genericGloss, word ) ) # Works best in editors with English on the left, Hebrew on the right

        if self.glossingDict:
            vPrint( 'Normal', debuggingThisModule, _("Exporting reverse glossing dictionary ({:,} entries) to '{}'…").format( len(self.glossingDict), DEFAULT_GENERIC_GLOSSING_REVERSE_EXPORT_FILEPATH ) )
            BibleOrgSysGlobals.backupAnyExistingFile( DEFAULT_GENERIC_GLOSSING_REVERSE_EXPORT_FILEPATH, 5 )
            doneGlosses = []
            with open( DEFAULT_GENERIC_GLOSSING_REVERSE_EXPORT_FILEPATH, 'wt' ) as exportFile:
                for word,(genericGloss,genericReferencesList,specificReferencesDict) in sorted( self.glossingDict.items(), key=lambda theTuple: theTuple[1][0].lower() ):
                    if genericGloss in doneGlosses:
                        logging.warning( _("Generic gloss {!r} has already appeared: currently for word {!r}").format( genericGloss, word ) )
                    exportFile.write( '{}  {}\n'.format( genericGloss, word ) ) # Works best in editors with English on the left, Hebrew on the right
                    doneGlosses.append( genericGloss )
    # end of HebrewWLCBibleAddon.exportGlossingDictionary


    def setNewGenericGloss( self, normalizedHebrewWord, genericGloss, ref ):
        """
        Check a new gloss and add it to the glossing dictionary.
        """
        fnPrint( debuggingThisModule, "setNewGenericGloss( {!r}, {!r}, {} )".format( normalizedHebrewWord, genericGloss, ref ) )
        assert isinstance( normalizedHebrewWord, str ) and normalizedHebrewWord
        assert ' ' not in normalizedHebrewWord
        assert ORIGINAL_MORPHEME_BREAK_CHAR not in normalizedHebrewWord # Should already be converted to OUR_MORPHEME_BREAK_CHAR
        #assert normalizedHebrewWord not in self.glossingDict
        assert isinstance( genericGloss, str ) and genericGloss
        assert ' ' not in genericGloss
        assert isinstance( ref, tuple ) and len(ref)==4 # BBB,C,V plus word# (starting with 1)

        if normalizedHebrewWord in self.glossingDict: # it's an update
            (prevGenericGloss,prevRefList,prevSpecificGlossDict) = self.glossingDict[normalizedHebrewWord]
            if genericGloss!=prevGenericGloss:
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, _("Updating generic gloss for {!r} from {!r} to {!r}").format( normalizedHebrewWord, prevGenericGloss, genericGloss ) )
                prevGenericGloss = genericGloss
            if ref not in prevRefList:
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, _("Adding {} for generic gloss {!r} for {!r}").format( ref, prevGenericGloss, normalizedHebrewWord ) )
                prevRefList.append( ref )
            self.glossingDict[normalizedHebrewWord] = (prevGenericGloss,prevRefList,prevSpecificGlossDict)
        else: # it's a new entry
            self.glossingDict[normalizedHebrewWord] = (genericGloss,[ref],{})
        self.haveGlossingDictChanges = True
    # end of HebrewWLCBibleAddon.setNewGenericGloss


    def setNewSpecificGloss( self, normalizedHebrewWord, specificGloss, ref ):
        """
        Check a new gloss and add it to the glossing dictionary.

        There must already be an entry for this Hebrew word (with a generic gloss).
        """
        fnPrint( debuggingThisModule, "setNewSpecificGloss( {!r}, {!r}, {} )".format( normalizedHebrewWord, specificGloss, ref ) )
        assert isinstance( normalizedHebrewWord, str ) and normalizedHebrewWord
        assert ' ' not in normalizedHebrewWord
        assert ORIGINAL_MORPHEME_BREAK_CHAR not in normalizedHebrewWord # Should already be converted to OUR_MORPHEME_BREAK_CHAR
        genericGloss,genericReferencesList,specificReferencesDict = self.glossingDict[normalizedHebrewWord]
        assert isinstance( genericGloss, str ) and genericGloss
        assert isinstance( ref, tuple ) and len(ref)==4 # BBB,C,V plus word# (starting with 1)
        assert ref in genericReferencesList
        #assert ref not in specificReferencesDict
        assert isinstance( specificGloss, str )
        assert ' ' not in specificGloss

        if ref in specificReferencesDict: # it must be an update
            vPrint( 'Normal', debuggingThisModule, _("Updating specific gloss for {!r} at {} from {!r} to {!r}").format( normalizedHebrewWord, ref, specificReferencesDict[ref], specificGloss ) )
            specificReferencesDict[ref] = specificGloss
        else: # it's a new entry
            specificReferencesDict[ref] = specificGloss
        self.glossingDict[normalizedHebrewWord] = (genericGloss,genericReferencesList,specificReferencesDict)
        self.haveGlossingDictChanges = True
    # end of HebrewWLCBibleAddon.setNewSpecificGloss


    def addNewGenericGlossingReference( self, normalizedHebrewWord, ref ):
        """
        Add a new ref to the glossing dictionary if it's not already there.
        """
        fnPrint( debuggingThisModule, "addNewGenericGlossingReference( {!r}, {} )".format( normalizedHebrewWord, ref ) )
        assert isinstance( normalizedHebrewWord, str )
        assert ' ' not in normalizedHebrewWord
        assert '/' not in normalizedHebrewWord # Should already be converted to =
        assert normalizedHebrewWord in self.glossingDict
        assert isinstance( ref, tuple ) and len(ref)==4 # BBB,C,V plus word# (starting with 1)

        (genericGloss,genericReferencesList,specificReferencesDict) = self.glossingDict[normalizedHebrewWord]
        assert ref not in genericReferencesList
        if ref not in genericReferencesList:
            genericReferencesList.append( ref )
            self.glossingDict[normalizedHebrewWord] = (genericGloss,genericReferencesList,specificReferencesDict)
            self.haveGlossingDictChanges = True
    # end of HebrewWLCBibleAddon.addNewGenericGlossingReference


    def updateGenericGlossingReferences( self ):
        """
        Go through the entire WLC and check for words that we already have a gloss for
            and update the reference fields.
        """
        from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
        vPrint( 'Normal', debuggingThisModule, _("Updating references for WLC generic glosses…") )

        self.loadBooks()
        numRefsAdded = 0
        for BBB,bookObject in self.books.items(): # These don't seem to be in order!
            # The following few lines show a way to iterate through all verses
            #   (assuming all chapters are full of verses -- not sure how it handles bridged verses)
            C = V = 1
            #dPrint( 'Quiet', debuggingThisModule, BBB )
            while True:
                currentVerseKey = SimpleVerseKey( BBB, C, V )
                try: verseDataList, context = self.getContextVerseData( currentVerseKey )
                except KeyError:
                    C, V = C+1, 1
                    currentVerseKey = SimpleVerseKey( BBB, C, V )
                    try: verseDataList, context = self.getContextVerseData( currentVerseKey )
                    except KeyError: break # start next book
                #dPrint( 'Quiet', debuggingThisModule, "context", context )
                #dPrint( 'Quiet', debuggingThisModule, "verseDataList", verseDataList )
                for verseDataEntry in verseDataList:
                    #dPrint( 'Quiet', debuggingThisModule, "verseDataEntry", verseDataEntry )
                    assert isinstance( verseDataEntry, InternalBibleEntry )
                    marker, cleanText, extras = verseDataEntry.getMarker(), verseDataEntry.getCleanText(), verseDataEntry.getExtras()
                    adjustedText, originalText = verseDataEntry.getAdjustedText(), verseDataEntry.getOriginalText()
                    if marker in ('v~','p~'):
                        verseDictList = self.getVerseDictList( verseDataEntry, currentVerseKey )
                        #dPrint( 'Quiet', debuggingThisModule, currentVerseKey.getShortText(), "verseDictList", verseDictList )
                        for j,verseDict in enumerate( verseDictList ): # each verseDict represents one word or token
                            fullRefTuple = (BBB,str(C),str(V),str(j+1))
                            #dPrint( 'Quiet', debuggingThisModule, fullRefTuple, verseDict )
                            word = verseDict['word']
                            normalizedHebrewWord =  self.removeCantillationMarks( word, removeMetegOrSiluq=True ) \
                                        .replace( ORIGINAL_MORPHEME_BREAK_CHAR, OUR_MORPHEME_BREAK_CHAR )
                            #dPrint( 'Quiet', debuggingThisModule, '  ', len(word), repr(word), len(normalizedHebrewWord), repr(normalizedHebrewWord) )
                            genericGloss,genericReferencesList,specificReferencesDict = self.glossingDict[normalizedHebrewWord] \
                                                    if normalizedHebrewWord in self.glossingDict else ('',[],{})
                            #if genericGloss: vPrint( 'Quiet', debuggingThisModule, fullRefTuple, repr(genericGloss) )
                            if genericGloss and genericGloss not in '־׃ספ-' and fullRefTuple not in genericReferencesList:
                                #dPrint( 'Quiet', debuggingThisModule, "  Adding {}".format( fullRefTuple ) )
                                self.addNewGenericGlossingReference( normalizedHebrewWord, fullRefTuple )
                                numRefsAdded += 1
                V = V + 1
        vPrint( 'Quiet', debuggingThisModule, "  {:,} new references added ({:,} words in dict)".format( numRefsAdded, len(self.glossingDict) ) )
    # end of HebrewWLCBibleAddon.updateGenericGlossingReferences
# end of HebrewWLCBibleAddon class



class OSISHebrewWLCBible( OSISXMLBible, HebrewWLCBibleAddon ):
    """
    Class for handling a Hebrew WLC (OSIS XML) object (which may contain one or more Bible books)
    """
    def __init__( self, OSISXMLFileOrFilepath=None ):
        """
        Create an empty object.
        """
        fnPrint( debuggingThisModule, "OSISHebrewWLCBible.__init__( {} )".format( OSISXMLFileOrFilepath ) )

        if not OSISXMLFileOrFilepath: OSISXMLFileOrFilepath = DEFAULT_OSIS_WLC_FILEPATH
        OSISXMLBible.__init__( self, OSISXMLFileOrFilepath, givenName='Westminster Leningrad Codex', givenAbbreviation='WLC' )
        HebrewWLCBibleAddon.__init__( self )
    # end of OSISHebrewWLCBible.__init__
# end of OSISHebrewWLCBible class



class PickledHebrewWLCBible( PickledBible, HebrewWLCBibleAddon ):
    """
    Class for handling a pickled Hebrew WLC object (which may contain one or more Bible books)

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, zippedPickleFilepath=None ):
        """
        Create an empty object.
        """
        fnPrint( debuggingThisModule, "PickledHebrewWLCBible.__init__( {} )".format( zippedPickleFilepath ) )

        if not zippedPickleFilepath: zippedPickleFilepath = DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH
        if not os.path.exists( zippedPickleFilepath ):
            logging.critical( "PickledHebrewWLCBible: filepath doesn't exist: {}".format( zippedPickleFilepath ) )
            return
        PickledBible.__init__( self, zippedPickleFilepath )
        HebrewWLCBibleAddon.__init__( self )
        # end of PickledHebrewWLCBible.__init__
# end of PickledHebrewWLCBible class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
    from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Demonstrate the Hebrew WLC class
    standardTestReferences = ('GEN', '1', '1'), ('SA1','1','1'), ('DAN', '1', '5')

    if 1: # Test one book
        #testFile = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/Ruth.xml' ) # Hebrew Ruth
        testFile = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/Dan.xml' ) # Hebrew Daniel
        vPrint( 'Quiet', debuggingThisModule, "\nA/ Demonstrating the Hebrew WLC class (one book only)…" )
        #dPrint( 'Quiet', debuggingThisModule, testFile )
        wlc = OSISHebrewWLCBible( testFile )
        wlc.load() # Load and process the XML book
        vPrint( 'Quiet', debuggingThisModule, str(wlc)+'\n' ) # Just print a summary

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            verseDataList = wlc.getVerseDataList( testKey )
            if verseDataList is not None: assert isinstance( verseDataList, InternalBibleEntryList )
            vPrint( 'Normal', debuggingThisModule, testKey )
            vPrint( 'Normal', debuggingThisModule, "VDL", str(verseDataList)+'\n' )
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #dPrint( 'Quiet', debuggingThisModule, "These all display left-to-right in the terminal unfortunately  :-(" )
                vPrint( 'Quiet', debuggingThisModule, verseText )
            verseText = wlc.removeMorphemeBreaks()
            vPrint( 'Normal', debuggingThisModule, "Without morpheme breaks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            verseText = wlc.removeCantillationMarks()
            vPrint( 'Normal', debuggingThisModule, "Without cantillation marks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            vPrint( 'Normal', debuggingThisModule, "Without vowel pointing" )
            vPrint( 'Normal', debuggingThisModule, str(consonantalVerseText)+'\n' )
            break

    if 1: # Load all books and test
        testFolder = DEFAULT_OSIS_WLC_FILEPATH # Hebrew
        vPrint( 'Quiet', debuggingThisModule, "\nB/ Demonstrating the Hebrew WLC class (whole Bible)…" )
        #dPrint( 'Quiet', debuggingThisModule, testFolder )
        wlc = OSISHebrewWLCBible( testFolder )
        wlc.loadBooks() # Load and process the XML files
        vPrint( 'Quiet', debuggingThisModule, str(wlc)+'\n' ) # Just print a summary

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            verseDataList = wlc.getVerseDataList( testKey )
            if verseDataList is not None: assert isinstance( verseDataList, InternalBibleEntryList )
            vPrint( 'Normal', debuggingThisModule, testKey )
            vPrint( 'Normal', debuggingThisModule, f"VDL {verseDataList}\n" )
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #dPrint( 'Quiet', debuggingThisModule, "These all display left-to-right in the terminal unfortunately  :-(" )
                vPrint( 'Quiet', debuggingThisModule, verseText )
            verseText = wlc.removeMorphemeBreaks()
            vPrint( 'Normal', debuggingThisModule, "Without morpheme breaks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            verseText = wlc.removeCantillationMarks()
            vPrint( 'Normal', debuggingThisModule, "Without cantillation marks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            vPrint( 'Normal', debuggingThisModule, "Without vowel pointing" )
            vPrint( 'Normal', debuggingThisModule, str(consonantalVerseText)+'\n' )
            # Check code for expanding morphological abbreviations
            if verseDataList is not None:
                for verseDataEntry in verseDataList:
                    assert isinstance( verseDataEntry, InternalBibleEntry )
                    marker = verseDataEntry.getMarker()
                    if marker in ('v~','p~'):
                        verseDictList = wlc.getVerseDictList( verseDataEntry, testKey )
                        vPrint( 'Quiet', debuggingThisModule, "verseDictList", verseDictList )
                        for j, verseDict in enumerate( verseDictList ):
                            vPrint( 'Quiet', debuggingThisModule, "verseDict", verseDict ) # for one word
                            #word = verseDict['word']
                            if 'morph' in verseDict:
                                vPrint( 'Quiet', debuggingThisModule, "  {}".format( wlc.expandMorphologyAbbreviations( verseDict['morph'] ) ) )
            break

    if 1: # Load books as we test
        testFolder = DEFAULT_OSIS_WLC_FILEPATH # Hebrew
        vPrint( 'Quiet', debuggingThisModule, "\nC/ Demonstrating the Hebrew WLC class (load on the go)…" )
        #dPrint( 'Quiet', debuggingThisModule, testFolder )
        wlc = OSISHebrewWLCBible( testFolder )
        #wlc.load() # Load and process the XML
        vPrint( 'Quiet', debuggingThisModule, str(wlc)+'\n' ) # Just print a summary

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            vPrint( 'Normal', debuggingThisModule, testKey )
            vPrint( 'Normal', debuggingThisModule, f"VD {wlc.getVerseDataList( testKey )}\n" )
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #dPrint( 'Quiet', debuggingThisModule, "These all display left-to-right in the terminal unfortunately  :-(" )
                vPrint( 'Quiet', debuggingThisModule, verseText )
            verseText = wlc.removeMorphemeBreaks()
            vPrint( 'Normal', debuggingThisModule, "Without morpheme breaks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            verseText = wlc.removeCantillationMarks()
            vPrint( 'Normal', debuggingThisModule, "Without cantillation marks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            vPrint( 'Normal', debuggingThisModule, "Without vowel pointing" )
            vPrint( 'Normal', debuggingThisModule, str(consonantalVerseText)+'\n' )
            break

    if 1: # Test some of the glossing functions
        vPrint( 'Quiet', debuggingThisModule, "\nD/ Demonstrating the Hebrew WLC glossing functions…" )
        wlc = OSISHebrewWLCBible( DEFAULT_OSIS_WLC_FILEPATH )
        wlc.loadGlossingDict()
        wlc.exportGlossingDictionary()
        wlc.saveAnyChangedGlosses()
        wlc.importGlossingDictionary()
        wlc.importGlossingDictionary( overrideFlag=True )

    if 1: # Test some of the glossing functions
        vPrint( 'Quiet', debuggingThisModule, "\nE/ Adding new references to glossing dict…" )
        wlc = OSISHebrewWLCBible()
        wlc.loadGlossingDict()
        wlc.updateGenericGlossingReferences()
        wlc.saveAnyChangedGlosses( exportAlso = True )

    if 1: # Test some of the glossing functions
        vPrint( 'Quiet', debuggingThisModule, "\nF/ Demonstrating the Hebrew WLC glossing functions…" )
        if not os.path.exists( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH ):
            logging.critical( "HebrewWLCBible.demoF: filepath doesn't exist: {}".format( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH ) )
        else:
            wlc = PickledHebrewWLCBible( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH )
            wlc.loadGlossingDict()
            wlc.exportGlossingDictionary()
            wlc.saveAnyChangedGlosses()
            wlc.importGlossingDictionary()
            wlc.importGlossingDictionary( overrideFlag=True )

    if 1: # Test some of the glossing functions
        vPrint( 'Quiet', debuggingThisModule, "\nG/ Adding new references to glossing dict…" )
        if not os.path.exists( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH ):
            logging.critical( "HebrewWLCBible.demoG: filepath doesn't exist: {}".format( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH ) )
        else:
            wlc = PickledHebrewWLCBible()
            wlc.loadGlossingDict()
            wlc.updateGenericGlossingReferences()
            wlc.saveAnyChangedGlosses( exportAlso = True )
# end of HebrewWLCBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
    from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Demonstrate the Hebrew WLC class
    standardTestReferences = ('GEN', '1', '1'), ('SA1','1','1'), ('DAN', '1', '5')

    if 1: # Test one book
        #testFile = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/Ruth.xml' ) # Hebrew Ruth
        testFile = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/Dan.xml' ) # Hebrew Daniel
        vPrint( 'Quiet', debuggingThisModule, "\nA/ Demonstrating the Hebrew WLC class (one book only)…" )
        #dPrint( 'Quiet', debuggingThisModule, testFile )
        wlc = OSISHebrewWLCBible( testFile )
        wlc.load() # Load and process the XML book
        vPrint( 'Quiet', debuggingThisModule, str(wlc)+'\n' ) # Just print a summary

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            verseDataList = wlc.getVerseDataList( testKey )
            if verseDataList is not None: assert isinstance( verseDataList, InternalBibleEntryList )
            vPrint( 'Normal', debuggingThisModule, testKey )
            vPrint( 'Normal', debuggingThisModule, "VDL", str(verseDataList)+'\n' )
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #dPrint( 'Quiet', debuggingThisModule, "These all display left-to-right in the terminal unfortunately  :-(" )
                vPrint( 'Quiet', debuggingThisModule, verseText )
            verseText = wlc.removeMorphemeBreaks()
            vPrint( 'Normal', debuggingThisModule, "Without morpheme breaks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            verseText = wlc.removeCantillationMarks()
            vPrint( 'Normal', debuggingThisModule, "Without cantillation marks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            vPrint( 'Normal', debuggingThisModule, "Without vowel pointing" )
            vPrint( 'Normal', debuggingThisModule, str(consonantalVerseText)+'\n' )

    if 1: # Load all books and test
        testFolder = DEFAULT_OSIS_WLC_FILEPATH # Hebrew
        vPrint( 'Quiet', debuggingThisModule, "\nB/ Demonstrating the Hebrew WLC class (whole Bible)…" )
        #dPrint( 'Quiet', debuggingThisModule, testFolder )
        wlc = OSISHebrewWLCBible( testFolder )
        wlc.loadBooks() # Load and process the XML files
        vPrint( 'Quiet', debuggingThisModule, str(wlc)+'\n' ) # Just print a summary

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            verseDataList = wlc.getVerseDataList( testKey )
            if verseDataList is not None: assert isinstance( verseDataList, InternalBibleEntryList )
            vPrint( 'Normal', debuggingThisModule, testKey )
            vPrint( 'Normal', debuggingThisModule, f"VDL {verseDataList}\n" )
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #dPrint( 'Quiet', debuggingThisModule, "These all display left-to-right in the terminal unfortunately  :-(" )
                vPrint( 'Quiet', debuggingThisModule, verseText )
            verseText = wlc.removeMorphemeBreaks()
            vPrint( 'Normal', debuggingThisModule, "Without morpheme breaks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            verseText = wlc.removeCantillationMarks()
            vPrint( 'Normal', debuggingThisModule, "Without cantillation marks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            vPrint( 'Normal', debuggingThisModule, "Without vowel pointing" )
            vPrint( 'Normal', debuggingThisModule, str(consonantalVerseText)+'\n' )
            # Check code for expanding morphological abbreviations
            if verseDataList is not None:
                for verseDataEntry in verseDataList:
                    assert isinstance( verseDataEntry, InternalBibleEntry )
                    marker = verseDataEntry.getMarker()
                    if marker in ('v~','p~'):
                        verseDictList = wlc.getVerseDictList( verseDataEntry, testKey )
                        vPrint( 'Quiet', debuggingThisModule, "verseDictList", verseDictList )
                        for j, verseDict in enumerate( verseDictList ):
                            vPrint( 'Quiet', debuggingThisModule, "verseDict", verseDict ) # for one word
                            #word = verseDict['word']
                            if 'morph' in verseDict:
                                vPrint( 'Quiet', debuggingThisModule, "  {}".format( wlc.expandMorphologyAbbreviations( verseDict['morph'] ) ) )

    if 1: # Load books as we test
        testFolder = DEFAULT_OSIS_WLC_FILEPATH # Hebrew
        vPrint( 'Quiet', debuggingThisModule, "\nC/ Demonstrating the Hebrew WLC class (load on the go)…" )
        #dPrint( 'Quiet', debuggingThisModule, testFolder )
        wlc = OSISHebrewWLCBible( testFolder )
        #wlc.load() # Load and process the XML
        vPrint( 'Quiet', debuggingThisModule, str(wlc)+'\n' ) # Just print a summary

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            vPrint( 'Normal', debuggingThisModule, testKey )
            vPrint( 'Normal', debuggingThisModule, f"VD {wlc.getVerseDataList( testKey )}\n" )
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #dPrint( 'Quiet', debuggingThisModule, "These all display left-to-right in the terminal unfortunately  :-(" )
                vPrint( 'Quiet', debuggingThisModule, verseText )
            verseText = wlc.removeMorphemeBreaks()
            vPrint( 'Normal', debuggingThisModule, "Without morpheme breaks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            verseText = wlc.removeCantillationMarks()
            vPrint( 'Normal', debuggingThisModule, "Without cantillation marks" )
            vPrint( 'Normal', debuggingThisModule, verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            vPrint( 'Normal', debuggingThisModule, "Without vowel pointing" )
            vPrint( 'Normal', debuggingThisModule, str(consonantalVerseText)+'\n' )

    if 1: # Test some of the glossing functions
        vPrint( 'Quiet', debuggingThisModule, "\nD/ Demonstrating the Hebrew WLC glossing functions…" )
        wlc = OSISHebrewWLCBible( DEFAULT_OSIS_WLC_FILEPATH )
        wlc.loadGlossingDict()
        wlc.exportGlossingDictionary()
        wlc.saveAnyChangedGlosses()
        wlc.importGlossingDictionary()
        wlc.importGlossingDictionary( overrideFlag=True )

    if 1: # Test some of the glossing functions
        vPrint( 'Quiet', debuggingThisModule, "\nE/ Adding new references to glossing dict…" )
        wlc = OSISHebrewWLCBible()
        wlc.loadGlossingDict()
        wlc.updateGenericGlossingReferences()
        wlc.saveAnyChangedGlosses( exportAlso = True )

    if 1: # Test some of the glossing functions
        vPrint( 'Quiet', debuggingThisModule, "\nF/ Demonstrating the Hebrew WLC glossing functions…" )
        if not os.path.exists( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH ):
            logging.critical( "HebrewWLCBible.demoF: filepath doesn't exist: {}".format( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH ) )
        else:
            wlc = PickledHebrewWLCBible( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH )
            wlc.loadGlossingDict()
            wlc.exportGlossingDictionary()
            wlc.saveAnyChangedGlosses()
            wlc.importGlossingDictionary()
            wlc.importGlossingDictionary( overrideFlag=True )

    if 1: # Test some of the glossing functions
        vPrint( 'Quiet', debuggingThisModule, "\nG/ Adding new references to glossing dict…" )
        if not os.path.exists( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH ):
            logging.critical( "HebrewWLCBible.demoG: filepath doesn't exist: {}".format( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH ) )
        else:
            wlc = PickledHebrewWLCBible()
            wlc.loadGlossingDict()
            wlc.updateGenericGlossingReferences()
            wlc.saveAnyChangedGlosses( exportAlso = True )
# end of HebrewWLCBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=False )

    if 0: # Update the glossing dictionary from the text file
        vPrint( 'Quiet', debuggingThisModule, "\nUpdating Hebrew WLC glossing dictionary from text file…" )
        wlc = OSISHebrewWLCBible( DEFAULT_OSIS_WLC_FILEPATH )
        wlc.glossingDictFilepath = DEFAULT_GLOSSING_DICT_FILEPATH
        wlc.importGlossingDictionary() # That we've edited in a text editor
        #wlc.exportGlossingDictionary()
        wlc.haveGlossingDictChanges = True
        wlc.saveAnyChangedGlosses()
    else: # normally
        fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of HebrewWLCBible.py
