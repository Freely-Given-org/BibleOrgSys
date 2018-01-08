#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HebrewWLCBible.py
#
# Module handling Open Scriptures Hebrew WLC.
#
# Copyright (C) 2011-2018 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
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

LastModifiedDate = '2018-01-08' # by RJH
ShortProgName = "HebrewWLCBibleHandler"
ProgName = "Hebrew WLC format handler"
ProgVersion = '0.13'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, pickle

import BibleOrgSysGlobals, Hebrew
from InternalBibleInternals import InternalBibleEntry, InternalBibleExtra, parseWordAttributes
from OSISXMLBible import OSISXMLBible
from PickledBible import PickledBible, ZIPPED_FILENAME_END

DEFAULT_OSIS_WLC_FILEPATH = '../morphhb/wlc/'
DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH = 'Resources/WLC' + ZIPPED_FILENAME_END

DEFAULT_GLOSSING_DICT_FILEPATH = '../BibleOrgSys/DataFiles/WLCHebrewGlosses.pickle'
DEFAULT_GLOSSING_EXPORT_FILEPATH = '../BibleOrgSys/DataFiles/WLCHebrewGlosses.txt'
DEFAULT_GLOSSING_REVERSE_EXPORT_FILEPATH = '../BibleOrgSys/DataFiles/WLCHebrewGlossesReversed.txt'

ORIGINAL_MORPHEME_BREAK_CHAR = '/'
OUR_MORPHEME_BREAK_CHAR = '='


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
        if debuggingThisModule: print( "HebrewWLCBibleAddon.__init__()" )

        self.glossingDict = None
    # end of HebrewWLCBibleAddon.__init__


    def getVerseDictList( self, verseDataEntry, ref ):
        """
        Given a verseDataEntry (an InternalBibleEntry)
        Return the text as a list of dictionaries.
        """
        if debuggingThisModule: print( "getVerseDictList( {}, {} )".format( verseDataEntry, ref ) )
        assert isinstance( verseDataEntry, InternalBibleEntry )

        def handleExtra( thisExtra ):
            """
            Checks an extra to see if it's a ww extra (word attributes).

            If so, returns wwDict with word attributes.
            Otherwise, returns None.
            """
            if debuggingThisModule: print( "handleExtra", thisExtra )

            if thisExtra.getType() == 'ww':
                wwField = thisExtra.getText()
                wwDict = parseWordAttributes( 'WLC', BBB, C, V, wwField, errorList=None )
                if 'morph' in wwDict and wwDict['morph'].startswith( 'OSHM:' ):
                    wwDict['morph'] = wwDict['morph'][5:]
                if debuggingThisModule: print( "wwDict", wwDict )
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
                print( " {}".format( extra ) )
                ix = extra.getIndex()
                print( "   {}".format( adjText[0 if ix<6 else ix-6:ix+1] ) )

        BBB,C,V = ref.getBCV()

        if debuggingThisModule: print( "adjText", repr(adjText) )
        resultList = []
        ix = ixAdd = 0
        punctuation = ''
        for j,token in enumerate( adjText.split() ):
            if debuggingThisModule: print( "token", j, repr(token) )
            ix += len(token)
            if token != '\\w': # ignore these:
                if token.endswith( '\\w*' ): token = token[:-3]
                elif token.endswith( '\\w' ):
                    token = token[:-2] # e.g., 'עַל\\w*־\\w'
                    ixAdd = 2
                    ix -= 2
                if '\\w*' in token: # e.g., 'הָ/אָֽרֶץ\\w*׃'
                    token, punctuation = token.split( '\\w*', 1 )
                    if debuggingThisModule: print( "t,p", repr(token), repr(punctuation) )
                    #ixAdd += len( punctuation )
                    ix -= len( punctuation )
                if debuggingThisModule: print( ix, "token", repr(token) )
                something = lineExtras.checkForIndex( ix ) # Could be moved lower if we remove assert after debugging
                wwDict = None
                if isinstance( something, InternalBibleExtra ):
                    wwDict = handleExtra( something )
                    #if debuggingThisModule: print( "extra", something )
                    #if something.getType() == 'ww':
                        #wwField = something.getText()
                        #wwDict = parseWordAttributes( 'WLC', BBB, C, V, wwField, errorList=None )
                        #if 'morph' in wwDict and wwDict['morph'].startswith( 'OSHM:' ):
                            #wwDict['morph'] = wwDict['morph'][5:]
                        #if debuggingThisModule: print( "wwDict", wwDict )
                    #else:
                        #logging.error( "Ignoring {} extra {} at {} for {}".format( something.getType(), something.getText(), ref, token ) )
                elif isinstance( something, list ):
                    #logging.critical( "Doesn't handle list of extras yet" )
                    #print( "something", something )
                    #print( "getVerseDictList( {}, {} )".format( verseDataEntry, ref ) )
                    for something2 in something:
                        #print( "something2", something2 )
                        if isinstance( something2, InternalBibleExtra ):
                            result = handleExtra( something2 )
                            if result: wwDict = result
                        else: halt # Programming error -- what's this???
                elif something is not None:
                    print( "HERE", something )
                    halt # Programming error -- what's this???
                resultList.append( wwDict if wwDict else {'word':token} )
                if punctuation:
                    ix += len( punctuation )
                    something = lineExtras.checkForIndex( ix ) # Could be moved lower if we remove assert after debugging
                    if debuggingThisModule: print( "have punctuation", repr(punctuation), something )
                    resultList.append( {'word':punctuation} )
                    punctuation = ''
            #if debuggingThisModule: print( "{}/{} ix={} token={!r} lemma={!r}".format( j+1, count, ix, token, lemma ) )
            ix += ixAdd + 1 # for space between words
            ixAdd = 0

        if debuggingThisModule: print( "getVerseDictList returning: {}".format( resultList ) )
        return resultList
    # end of HebrewWLCBibleAddon.getVerseDictList


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
        #print( "removeCantillationMarks( {!r}, {} )".format( text, removeMetegOrSiluq ) )

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


    def loadGlossingDict( self, glossingDictFilepath=None ):
        """
        """
        self.glossingDictFilepath = glossingDictFilepath
        if glossingDictFilepath is None:
            self.glossingDictFilepath = DEFAULT_GLOSSING_DICT_FILEPATH

        # Read our glossing data from the pickle file
        if BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
            print( "Loading Hebrew glossing dictionary from '{}'…".format( self.glossingDictFilepath ) )
        with open( self.glossingDictFilepath, 'rb' ) as pickleFile:
            self.glossingDict = pickle.load( pickleFile )
            # It's a dictionary with (pointed and parsed) Hebrew keys and 2-tuple entries
            #   Hebrew keys have morphological breaks separated by =
            #   2-tuple entries consist of a gloss,
            #      (with gloss alternatives separated by /)
            #   followed by a list of currently known/parsed references
            #print( "glossingDict:", self.glossingDict )
        self.loadedGlossEntryCount = len( self.glossingDict )
        self.haveGlossingDictChanges = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
            print( "  {} Hebrew gloss entries read.".format( self.loadedGlossEntryCount ) )

        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
            print( "Checking {} loaded Hebrew gloss entries for consistency…".format( self.loadedGlossEntryCount ) )
            for word,(gloss,referencesList) in self.glossingDict.copy().items(): # Use a copy because we can modify it
                #print( repr(word), repr(gloss), referencesList )
                assert isinstance( word, str )
                assert isinstance( gloss, str )
                assert isinstance( referencesList, list )
                if ' ' in word or '/' in word:
                    logging.critical( "Removing invalid Hebrew (normalized) word: {!r}".format( word ) )
                    del self.glossingDict[word]
                    self.haveGlossingDictChanges = True
                if ' ' in gloss:
                    logging.critical( "Removing {!r} word with invalid gloss: {!r}".format( word, gloss ) )
                    del self.glossingDict[word]
                    self.haveGlossingDictChanges = True
                for reference in referencesList:
                    assert isinstance( reference, tuple )
                    assert len(reference) == 4 # BBB,C,V,word# (starting with 1)
                    for part in reference:
                        assert isinstance( part, str ) # We don't use INTs for references
                    assert referencesList.count( reference ) == 1 # Don't allow multiples
            print( "  Finished checking Hebrew glosses" )
    # end of HebrewWLCBibleAddon.loadGlossingDict


    def saveAnyChangedGlosses( self, exportAlso=False ):
        """
        Save the glossing dictionary to a pickle file.
        """
        if debuggingThisModule: print( "saveAnyChangedGlosses()" )

        if self.haveGlossingDictChanges:
            BibleOrgSysGlobals.backupAnyExistingFile( self.glossingDictFilepath, 9 )
            if BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
                print( "  Saving Hebrew glossing dictionary ({}->{} entries) to '{}'…".format( self.loadedGlossEntryCount, len(self.glossingDict), self.glossingDictFilepath ) )
            elif BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  Saving Hebrew glossing dictionary ({}->{} entries)…".format( self.loadedGlossEntryCount, len(self.glossingDict) ) )
            with open( self.glossingDictFilepath, 'wb' ) as pickleFile:
                pickle.dump( self.glossingDict, pickleFile )

            if exportAlso: self.exportGlossingDictionary()
    # end of HebrewWLCBibleAddon.saveAnyChangedGlosses


    def importGlossingDictionary( self, glossingDictImportFilepath=None, overrideFlag=False ):
        """
        Import the glossing dictionary from (an exported or handcrafted) text file.

        NOTE: Usually we use the much faster loadGlossingDict (load pickle) function above.
        """
        import ast
        #print( "importGlossingDictionary()" )
        if glossingDictImportFilepath is None: glossingDictImportFilepath = DEFAULT_GLOSSING_EXPORT_FILEPATH

        if self.haveGlossingDictChanges:
            print( _("Import disallowed because you already have glossing changes!") )
        elif self.glossingDict and not overrideFlag:
            print( _("Import disallowed because you have already loaded the glossing dictionary") )
        else:
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "Importing glossing dictionary from '{}'…".format( glossingDictImportFilepath ) )
            lineCount = 0
            newDict = {}
            with open( glossingDictImportFilepath, 'r' ) as importFile:
                for line in importFile:
                    lineCount += 1
                    if lineCount==1 and line[0]==chr(65279): #U+FEFF
                        logging.info( "Glossingizer: Detected UTF-16 Byte Order Marker in {}".format( glossingDictImportFilepath ) )
                        line = line[1:] # Remove the UTF-8 Byte Order Marker
                    if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    bits = line.split( '  ' )
                    #print( "bits", bits )
                    if len(bits) == 3:
                        referencesText, gloss, word = bits
                        if not referencesText or not gloss or not word:
                            print( "  Empty field error" )
                        elif ' ' in gloss \
                        or gloss.count(OUR_MORPHEME_BREAK_CHAR)!=word.count(OUR_MORPHEME_BREAK_CHAR):
                            print( "  Bad gloss field error: {!r} for {!r}".format( gloss, word ) )
                        referencesList = ast.literal_eval( referencesText )
                        #print( "references", repr(referencesText), repr(referencesList) )
                        assert isinstance( referencesList, list )
                        newDict[word] = referencesList, gloss
                    else:
                        print( "  Ignored '{}' line at {} ({} bits)".format( line, lineCount, len(bits) ) )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loaded {} entries.".format( len(newDict) ) )
            if len(newDict) > self.loadedGlossEntryCount-10: # Seems to have been successful
                if len(newDict) != self.loadedGlossEntryCount: print( "  Went from {} to {} entries!".format( self.loadedGlossEntryCount, len(newDict) ) )
                self.glossingDict = newDict # Replace the dictionary with the upgraded one
    # end of HebrewWLCBibleAddon.importGlossingDictionary


    def exportGlossingDictionary( self, glossingDictExportFilepath=None ):
        """
        Export the glossing dictionary to a text file
            plus a reversed text file (without the references).

        Also does a few checks while exporting.
            (These can be fixed and then the file can be imported.)
        """
        #print( "exportGlossingDictionary()" )
        if glossingDictExportFilepath is None: glossingDictExportFilepath = DEFAULT_GLOSSING_EXPORT_FILEPATH
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "Exporting glossing dictionary ({} entries) to '{}'…".format( len(self.glossingDict), glossingDictExportFilepath ) )

        BibleOrgSysGlobals.backupAnyExistingFile( glossingDictExportFilepath, 5 )
        with open( glossingDictExportFilepath, 'wt' ) as exportFile:
            for word,(gloss,referencesList) in self.glossingDict.items():
                if ' ' in word or '/' in word:
                    logging.error( "Word {!r} has illegal characters".format( word ) )
                if ' ' in gloss:
                    logging.error( "Gloss {!r} for {!r} has illegal characters".format( gloss, word ) )
                if word.count('=') != gloss.count('='):
                    logging.error( "Gloss {!r} and word {!r} has different numbers of morphemes".format( gloss, word ) )
                if not referencesList:
                    logging.error( "Gloss {!r} for {!r} has no references".format( gloss, word ) )
                exportFile.write( "{}  {}  {}\n".format( referencesList, gloss, word ) ) # Works best in editors with English on the left, Hebrew on the right

        if self.glossingDict:
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "Exporting reverse glossing dictionary ({} entries) to '{}'…".format( len(self.glossingDict), DEFAULT_GLOSSING_REVERSE_EXPORT_FILEPATH ) )
            BibleOrgSysGlobals.backupAnyExistingFile( DEFAULT_GLOSSING_REVERSE_EXPORT_FILEPATH, 5 )
            doneGlosses = []
            with open( DEFAULT_GLOSSING_REVERSE_EXPORT_FILEPATH, 'wt' ) as exportFile:
                for word,(gloss,referencesList) in self.glossingDict.items():
                    if gloss in doneGlosses:
                        logging.warning( "Gloss {!r} has already appeared: currently for word {!r}".format( gloss, word ) )
                    exportFile.write( "{}  {}\n".format( gloss, word ) ) # Works best in editors with English on the left, Hebrew on the right
                    doneGlosses.append( gloss )
    # end of HebrewWLCBibleAddon.exportGlossingDictionary


    def setNewGloss( self, normalizedHebrewWord, gloss, ref ):
        """
        Check a new gloss and add it to the glossing dictionary.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "setNewGloss( {!r}, {!r}, {} )".format( normalizedHebrewWord, gloss, ref ) )
        assert isinstance( normalizedHebrewWord, str )
        assert ' ' not in normalizedHebrewWord
        assert '/' not in normalizedHebrewWord # Should already be converted to =
        assert normalizedHebrewWord not in self.glossingDict
        assert isinstance( gloss, str )
        assert ' ' not in gloss
        assert isinstance( ref, tuple ) and len(ref)==4 # BBB,C,V plus word# (starting with 1)

        self.glossingDict[normalizedHebrewWord] = (gloss,[ref])
        self.haveGlossingDictChanges = True
    # end of HebrewWLCBibleAddon.setNewGloss


    def addNewGlossingReference( self, normalizedHebrewWord, ref ):
        """
        Check a new ref to the glossing dictionary if it's not already there.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "addNewGlossingReference( {!r}, {} )".format( normalizedHebrewWord, ref ) )
        assert isinstance( normalizedHebrewWord, str )
        assert ' ' not in normalizedHebrewWord
        assert '/' not in normalizedHebrewWord # Should already be converted to =
        assert normalizedHebrewWord in self.glossingDict
        assert isinstance( ref, tuple ) and len(ref)==4 # BBB,C,V plus word# (starting with 1)

        (gloss,referencesList) = self.glossingDict[normalizedHebrewWord]
        assert ref not in referencesList
        if ref not in referencesList:
            referencesList.append( ref )
            self.glossingDict[normalizedHebrewWord] = (gloss,referencesList)
            self.haveGlossingDictChanges = True
    # end of HebrewWLCBibleAddon.addNewGlossingReference


    def updateGlossingReferences( self ):
        """
        Go through the entire WLC and check for words that we already have a gloss for
            and update the reference fields.
        """
        from VerseReferences import SimpleVerseKey
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Updating references for WLC glosses…" )

        self.loadBooks()
        #self.loadBook( 'GEN' )
        numRefsAdded = 0
        for BBB,bookObject in self.books.items(): # These don't seem to be in order!
            # The following few lines show a way to iterate through all verses
            #   (assuming all chapters are full of verses -- not sure how it handles bridged verses)
            C = V = 1
            #print( BBB )
            while True:
                currentVerseKey = SimpleVerseKey( BBB, C, V )
                try: verseDataList, context = self.getContextVerseData( currentVerseKey )
                except KeyError:
                    C, V = C+1, 1
                    currentVerseKey = SimpleVerseKey( BBB, C, V )
                    try: verseDataList, context = self.getContextVerseData( currentVerseKey )
                    except KeyError: break # start next book
                #print( "context", context )
                #print( "verseDataList", verseDataList )
                for verseDataEntry in verseDataList:
                    #print( "verseDataEntry", verseDataEntry )
                    assert isinstance( verseDataEntry, InternalBibleEntry )
                    marker, cleanText, extras = verseDataEntry.getMarker(), verseDataEntry.getCleanText(), verseDataEntry.getExtras()
                    adjustedText, originalText = verseDataEntry.getAdjustedText(), verseDataEntry.getOriginalText()
                    if marker in ('v~','p~'):
                        verseDictList = self.getVerseDictList( verseDataEntry, currentVerseKey )
                        #print( currentVerseKey.getShortText(), "verseDictList", verseDictList )
                        for j,verseDict in enumerate( verseDictList ): # each verseDict represents one word or token
                            fullRefTuple = (BBB,str(C),str(V),str(j+1))
                            #print( fullRefTuple, verseDict )
                            word = verseDict['word']
                            normalizedHebrewWord =  self.removeCantillationMarks( word, removeMetegOrSiluq=True ) \
                                        .replace( ORIGINAL_MORPHEME_BREAK_CHAR, OUR_MORPHEME_BREAK_CHAR )
                            #print( '  ', len(word), repr(word), len(normalizedHebrewWord), repr(normalizedHebrewWord) )
                            gloss,referencesList = self.glossingDict[normalizedHebrewWord] \
                                                    if normalizedHebrewWord in self.glossingDict else ('',[])
                            #if gloss: print( fullRefTuple, repr(gloss) )
                            if gloss and gloss not in '־׃ספ-' and fullRefTuple not in referencesList:
                                #print( "  Adding {}".format( fullRefTuple ) )
                                self.addNewGlossingReference( normalizedHebrewWord, fullRefTuple )
                                numRefsAdded += 1
                V = V + 1
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "  {} new references added ({} words in dict)".format( numRefsAdded, len(self.glossingDict) ) )
    # end of HebrewWLCBibleAddon.updateGlossingReferences
# end of HebrewWLCBibleAddon class



class OSISHebrewWLCBible( OSISXMLBible, HebrewWLCBibleAddon ):
    """
    Class for handling a Hebrew WLC (OSIS XML) object (which may contain one or more Bible books)
    """
    def __init__( self, OSISXMLFilepath=None ):
        """
        Create an empty object.
        """
        if debuggingThisModule: print( "OSISHebrewWLCBible.__init__( {} )".format( OSISXMLFilepath ) )

        if not OSISXMLFilepath: OSISXMLFilepath = DEFAULT_OSIS_WLC_FILEPATH
        OSISXMLBible.__init__( self, OSISXMLFilepath, givenName='Westminster Leningrad Codex', givenAbbreviation='WLC' )
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
        if debuggingThisModule: print( "PickledHebrewWLCBible.__init__( {} )".format( zippedPickleFilepath ) )

        if not zippedPickleFilepath: zippedPickleFilepath = DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH
        PickledBible.__init__( self, zippedPickleFilepath )
        HebrewWLCBibleAddon.__init__( self )
        # end of PickledHebrewWLCBible.__init__
# end of PickledHebrewWLCBible class



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    from VerseReferences import SimpleVerseKey

    # Demonstrate the Hebrew WLC class
    standardTestReferences = ('GEN', '1', '1'), ('SA1','1','1'), ('DAN', '1', '5')

    if 1: # Test one book
        #testFile = "../morphhb/wlc/Ruth.xml" # Hebrew Ruth
        testFile = '../morphhb/wlc/Dan.xml' # Hebrew Daniel
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nA/ Demonstrating the Hebrew WLC class (one book only)…" )
        #print( testFile )
        wlc = OSISHebrewWLCBible( testFile )
        wlc.load() # Load and process the XML book
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( wlc ) # Just print a summary
            print()

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( testKey )
                print( "VD", wlc.getVerseDataList( testKey ) )
                print()
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #print( "These all display left-to-right in the terminal unfortunately  :-(" )
                print( verseText )
            verseText = wlc.removeMorphemeBreaks()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( verseText )
            verseText = wlc.removeCantillationMarks()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( consonantalVerseText )
                print()

    if 1: # Load all books and test
        testFolder = DEFAULT_OSIS_WLC_FILEPATH # Hebrew
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nB/ Demonstrating the Hebrew WLC class (whole Bible)…" )
        #print( testFolder )
        wlc = OSISHebrewWLCBible( testFolder )
        wlc.loadBooks() # Load and process the XML files
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( wlc ) # Just print a summary
            print()

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( testKey )
                print( "VD", wlc.getVerseDataList( testKey ) )
                print()
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #print( "These all display left-to-right in the terminal unfortunately  :-(" )
                print( verseText )
            verseText = wlc.removeMorphemeBreaks()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( verseText )
            verseText = wlc.removeCantillationMarks()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( consonantalVerseText )
                print()

    if 1: # Load books as we test
        testFolder = DEFAULT_OSIS_WLC_FILEPATH # Hebrew
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nC/ Demonstrating the Hebrew WLC class (load on the go)…" )
        #print( testFolder )
        wlc = OSISHebrewWLCBible( testFolder )
        #wlc.load() # Load and process the XML
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( wlc ) # Just print a summary
            print()

        for testReference in standardTestReferences:
            testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( testKey )
                print( "VD", wlc.getVerseDataList( testKey ) )
                print()
            verseText = wlc.getVerseText( testKey )
            wlc.currentText = verseText
            if BibleOrgSysGlobals.verbosityLevel > 0:
                #print( "These all display left-to-right in the terminal unfortunately  :-(" )
                print( verseText )
            verseText = wlc.removeMorphemeBreaks()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( verseText )
            verseText = wlc.removeCantillationMarks()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( verseText )
            consonantalVerseText = wlc.removeVowelPointing()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print()
                print( consonantalVerseText )
                print()

    if 1: # Test some of the glossing functions
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nD/ Demonstrating the Hebrew WLC glossing functions…" )
        wlc = OSISHebrewWLCBible( DEFAULT_OSIS_WLC_FILEPATH )
        wlc.loadGlossingDict()
        wlc.exportGlossingDictionary()
        wlc.saveAnyChangedGlosses()
        wlc.importGlossingDictionary()
        wlc.importGlossingDictionary( overrideFlag=True )

    if 1: # Test some of the glossing functions
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nE/ Adding new references to glossing dict…" )
        wlc = OSISHebrewWLCBible()
        wlc.loadGlossingDict()
        wlc.updateGlossingReferences()
        wlc.saveAnyChangedGlosses( exportAlso = True )

    if 1: # Test some of the glossing functions
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nF/ Demonstrating the Hebrew WLC glossing functions…" )
        wlc = PickledHebrewWLCBible( DEFAULT_ZIPPED_PICKLED_WLC_FILEPATH )
        wlc.loadGlossingDict()
        wlc.exportGlossingDictionary()
        wlc.saveAnyChangedGlosses()
        wlc.importGlossingDictionary()
        wlc.importGlossingDictionary( overrideFlag=True )

    if 1: # Test some of the glossing functions
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nG/ Adding new references to glossing dict…" )
        wlc = PickledHebrewWLCBible()
        wlc.loadGlossingDict()
        wlc.updateGlossingReferences()
        wlc.saveAnyChangedGlosses( exportAlso = True )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of HebrewWLCBible.py
