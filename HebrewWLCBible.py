#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HebrewWLCBible.py
#
# Module handling HebrewWLCBible.xml
#
# Copyright (C) 2011-2017 Robert Hunt
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
Module handling WLCHebrew.xml to produce C and Python data tables.
"""

from gettext import gettext as _

LastModifiedDate = '2017-12-28' # by RJH
ShortProgName = "HebrewWLCBibleHandler"
ProgName = "Hebrew WLC format handler"
ProgVersion = '0.11'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, pickle

import BibleOrgSysGlobals, Hebrew
from OSISXMLBible import OSISXMLBible
from InternalBibleInternals import InternalBibleEntry, InternalBibleExtra, parseWordAttributes


DEFAULT_WLC_FILEPATH = '../morphhb/wlc/'
DEFAULT_GLOSSING_DICT_FILEPATH = '../BibleOrgSys/DataFiles/WLCHebrewGlosses.pickle'
DEFAULT_GLOSSING_EXPORT_FILEPATH = '../BibleOrgSys/DataFiles/WLCHebrewGlosses.txt'
DEFAULT_GLOSSING_REVERSE_EXPORT_FILEPATH = '../BibleOrgSys/DataFiles/WLCHebrewGlossesReversed.txt'

ORIGINAL_MORPHEME_BREAK_CHAR = '/'
OUR_MORPHEME_BREAK_CHAR = '='


class HebrewWLCBible( OSISXMLBible ):
    """
    Class for handling a Hebrew WLC object (which may contain one or more Bible books)

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """
    def __init__( self, XMLFilepath=None, givenAbbreviation=None ):
       """
       Create an empty object.
       """
       if not XMLFilepath: XMLFilepath = DEFAULT_WLC_FILEPATH
       if not givenAbbreviation: givenAbbreviation = 'WLC'
       OSISXMLBible.__init__( self, XMLFilepath, givenAbbreviation=givenAbbreviation )

       self.glossingDict = None
    # end of __init__


    #def __str__( self ):
        #"""
        #This method returns the string representation of a Bible book code.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #result = "Hebrew WLC object"
        ##if self.title: result += ('\n' if result else '') + self.title
        ##if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        ##if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        #if len(self.books)==1:
            #for BBB in self.books: break # Just get the first one
            #result += ('\n' if result else '') + "  " + _("Contains one book: {}").format( BBB )
        #else: result += ('\n' if result else '') + "  " + _("Number of books = {}").format( len(self.books) )
        #return result
    ## end of __str__


    #def getVerseDataList( self, reference ):
        #""" Return the text for the verse with some adjustments. """
        #data = OSISXMLBible.getVerseDataList( self, reference )
        ##print( data );halt
        #if data:
            #myData = InternalBibleEntryList()
            #for dataLine in data:
                #print( "dL", dataLine )
                #if dataLine.getMarker() == 'v~':
                    #cT = dataLine.getCleanText().replace('/','=')
                    #myData.append( InternalBibleEntry( dataLine[0], dataLine[1], dataLine[2], cT, dataLine[4], dataLine[5] ) )
                #else: myData.append( dataLine )
            #return myData
        #else: print( "oops. empty verse data for", reference )


    #def xgetVerseText( self, reference ):
        #""" Return the text for the verse with some adjustments. """
        #self.originalText = OSISXMLBible.getVerseText( self, reference )
        #if self.originalText is None: self.originalText = ''
        #if self.originalText: self.originalText = self.originalText.replace(' '+'־'+' ','־') # Remove spaces around the maqqef
        #if self.originalText: self.originalText = self.originalText.replace('/','=') # We use = for morpheme break character not /
        #self.currentText = self.originalText
        ##print( self.currentText ); halt
        #if self.originalText: return self.originalText
        #else: print( "oops. empty verse text for", reference )


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

            If so, ipdates global dict wwDict with word attributes.
            """
            if debuggingThisModule: print( "handleExtra", thisExtra )
            if thisExtra.getType() == 'ww':
                wwField = thisExtra.getText()
                wwDict = parseWordAttributes( 'WLC', BBB, C, V, wwField, errorList=None )
                if 'morph' in wwDict and wwDict['morph'].startswith( 'OSHM:' ):
                    wwDict['morph'] = wwDict['morph'][5:]
                if debuggingThisModule: print( "wwDict", wwDict )
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
                    handleExtra( something )
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
                            handleExtra( something2 )
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
    # end of HebrewWLCBible.getVerseDictList


    def removeMorphemeBreaks( self, text=None ):
        """
        Return the text with morpheme break marks removed.
        """
        if text is None:
            self.currentText = self.currentText.replace('=', '') if self.currentText else self.currentText
            return self.currentText
        # else we were passed a text string
        return text.replace('=', '')
    # end of HebrewWLCBible.removeMorphemeBreaks

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
    # end of HebrewWLCBible.removeCantillationMarks

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
    # end of HebrewWLCBible.removeVowelPointing


    def loadGlossingDict( self, glossingDictFilepath=None ):
        """
        """
        self.glossingDictFilepath = glossingDictFilepath
        if glossingDictFilepath is None:
            self.glossingDictFilepath = DEFAULT_GLOSSING_DICT_FILEPATH

        # Read our glossing glossing data from the pickle file
        if BibleOrgSysGlobals.verbosityLevel > 1:
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
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  {} Hebrew glossing gloss entries read.".format( self.loadedGlossEntryCount ) )

        if 1 or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
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
    # end of HebrewWLCBible.loadGlossingDict


    def saveAnyChangedGlosses( self ):
        """
        Save the glossing dictionary to a pickle file.
        """
        if debuggingThisModule: print( "saveAnyChangedGlosses()" )

        if self.haveGlossingDictChanges:
            BibleOrgSysGlobals.backupAnyExistingFile( self.glossingDictFilepath, 4 )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "Saving Hebrew glossing dictionary ({}->{} entries) to '{}'…".format( self.loadedGlossEntryCount, len(self.glossingDict), self.glossingDictFilepath ) )
            with open( self.glossingDictFilepath, 'wb' ) as pickleFile:
                pickle.dump( self.glossingDict, pickleFile )

            #expResponse = input( "Export changed dictionary? [No] " )
            #if expResponse.upper() in ( 'Y', 'YES' ):
                #self.exportGlossingDictionary()
            self.exportGlossingDictionary()
    # end of saveAnyChangedGlosses


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
    # end of importGlossingDictionary


    def exportGlossingDictionary( self, glossingDictExportFilepath=None ):
        """
        Import the glossing dictionary from (an exported or handcrafted) text file.
        """
        #print( "exportGlossingDictionary()" )
        if glossingDictExportFilepath is None: glossingDictExportFilepath = DEFAULT_GLOSSING_EXPORT_FILEPATH

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "Exporting glossing dictionary ({} entries) to '{}'…".format( self.loadedGlossEntryCount, glossingDictExportFilepath ) )

        BibleOrgSysGlobals.backupAnyExistingFile( glossingDictExportFilepath, 5 )
        with open( glossingDictExportFilepath, 'w' ) as exportFile:
            for word,(gloss,referencesList) in self.glossingDict.items():
                #assert ' ' not in word
                #assert '/' not in word
                #assert ' ' not in gloss
                exportFile.write( "{}  {}  {}\n".format( referencesList, gloss, word ) ) # Works best in editors with English on the left, Hebrew on the right

        if self.glossingDict:
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "Exporting reverse glossing dictionary ({} entries) to '{}'…".format( self.loadedGlossEntryCount, DEFAULT_GLOSSING_REVERSE_EXPORT_FILEPATH ) )
            BibleOrgSysGlobals.backupAnyExistingFile( DEFAULT_GLOSSING_REVERSE_EXPORT_FILEPATH, 5 )
            with open( DEFAULT_GLOSSING_REVERSE_EXPORT_FILEPATH, 'w' ) as exportFile:
                for word,(gloss,referencesList) in self.glossingDict.items():
                    #print( repr(word), repr(gloss) )
                    #assert ' ' not in word
                    #assert '/' not in word
                    #assert ' ' not in gloss
                    exportFile.write( "{}  {}\n".format( gloss, word ) ) # Works best in editors with English on the left, Hebrew on the right
    # end of exportGlossingDictionary


    def setNewGloss( self, normalizedHebrewWord, gloss, ref ):
        """
        Check a new gloss and add it to the glossing dictionary.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1:
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
    # end of HebrewWLCBible.setNewGloss


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
    # end of HebrewWLCBible.addNewGlossingReference


    def updateGlossingReferences( self ):
        """
        Go through the entire WLC and check for words that we already have a gloss for
            and update the reference fields.
        """
        from VerseReferences import SimpleVerseKey
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "Updating references for WLC glosses…" )

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
    # end of HebrewWLCBible.updateGlossingReferences
# end of HebrewWLCBible class



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
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nA/ Demonstrating the Hebrew WLC class for DAN…" )
        #print( testFile )
        wlc = HebrewWLCBible( testFile, givenAbbreviation='WLC' )
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
        testFolder = DEFAULT_WLC_FILEPATH # Hebrew
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nB/ Demonstrating the Hebrew WLC class (whole Bible)…" )
        #print( testFolder )
        wlc = HebrewWLCBible( testFolder, givenAbbreviation='WLC' )
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
        testFolder = DEFAULT_WLC_FILEPATH # Hebrew
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nC/ Demonstrating the Hebrew WLC class (load on the go)…" )
        #print( testFolder )
        wlc = HebrewWLCBible( testFolder )
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
        wlc = HebrewWLCBible( DEFAULT_WLC_FILEPATH, givenAbbreviation='WLC' )
        wlc.loadGlossingDict()
        wlc.exportGlossingDictionary()
        wlc.saveAnyChangedGlosses()
        wlc.importGlossingDictionary()
        wlc.importGlossingDictionary( overrideFlag=True )

    if 1: # Test some of the glossing functions
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nE/ Adding new references to glossing dict…" )
        wlc = HebrewWLCBible()
        wlc.loadGlossingDict()
        wlc.updateGlossingReferences()
        wlc.saveAnyChangedGlosses()
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of HebrewWLCBible.py
