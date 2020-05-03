#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GreekNT.py
#
# Module handling GreekNT.xml
#
# Copyright (C) 2012-2018 Robert Hunt
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
Module handling xxx to produce C and Python data tables.

    010101 N- ----NSF- Βίβλος Βίβλος βίβλος βίβλος
    010101 N- ----GSF- γενέσεως γενέσεως γενέσεως γένεσις
    010101 N- ----GSM- Ἰησοῦ Ἰησοῦ Ἰησοῦ Ἰησοῦς
    010101 N- ----GSM- χριστοῦ χριστοῦ Χριστοῦ Χριστός
    010101 N- ----GSM- υἱοῦ υἱοῦ υἱοῦ υἱός
    010101 N- ----GSM- Δαυὶδ Δαυὶδ Δαυίδ Δαυίδ
    010101 N- ----GSM- υἱοῦ υἱοῦ υἱοῦ υἱός
    010101 N- ----GSM- Ἀβραάμ. Ἀβραάμ Ἀβραάμ Ἀβραάμ
    010102 N- ----NSM- Ἀβραὰμ Ἀβραὰμ Ἀβραάμ Ἀβραάμ
    010102 V- 3AAI-S-- ἐγέννησεν ἐγέννησεν ἐγέννησε(ν) γεννάω
    010102 RA ----ASM- τὸν τὸν τόν ὁ
    010102 N- ----ASM- Ἰσαάκ, Ἰσαάκ Ἰσαάκ Ἰσαάκ
    010102 N- ----NSM- Ἰσαὰκ Ἰσαὰκ Ἰσαάκ Ἰσαάκ
    010102 C- -------- δὲ δὲ δέ δέ
    010102 V- 3AAI-S-- ἐγέννησεν ἐγέννησεν ἐγέννησε(ν) γεννάω
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2018-12-12' # by RJH
SHORT_PROGRAM_NAME = "GreekNTHandler"
PROGRAM_NAME = "Greek NT format handler"
PROGRAM_VERSION = '0.08'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


import os
import logging

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.OriginalLanguages import Greek
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey



class GreekNT( Bible ):
    """
    Class for handling a Greek NT object (which may contain one or more Bible books)

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """
    def __init__( self, sourceFilepath, givenName=None, encoding='utf-8' ):
        """
        Constructor: expects the filepath of the source folder.
        Loads (and crudely validates the file(s)) into ???.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Greek NT Bible object'
        self.objectTypeString = 'GreekNT'

        # Now we can set our object variables
        self.sourceFilepath, self.givenName, self.encoding  = sourceFilepath, givenName, encoding

        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.frontMatter = self.divs = self.divTypesString = None
        #self.bkData, self.USFMBooks = {}, {}
        self.lang = self.language = None

        # Do a preliminary check on the readability of our files
        self.possibleFilenames = []
        if os.path.isdir( self.sourceFilepath ): # We've been given a folder -- see if we can find the files
            # There's no standard for OSIS xml file naming
            fileList = os.listdir( self.sourceFilepath )
            #vPrint( 'Quiet', debuggingThisModule, len(fileList), fileList )
            # First try looking for OSIS book names
            for filename in fileList:
                if filename.lower().endswith('.txt'):
                    thisFilepath = os.path.join( self.sourceFilepath, filename )
                    #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, "Trying {}…".format( thisFilepath ) )
                    if os.access( thisFilepath, os.R_OK ): # we can read that file
                        self.possibleFilenames.append( filename )
        elif not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( "GreekNT: File {!r} is unreadable".format( self.sourceFilepath ) )
            return # No use continuing
        #vPrint( 'Quiet', debuggingThisModule, self.possibleFilenames ); halt

        self.name = self.givenName
        #gNTfc = GreekNTFileConverter( self.sourceFilepath ) # Load and process the XML
        #gNTfc.loadMorphGNT()
        #self.books = gNTfc.bookData
    # end of __init__


    #def x__str__( self ) -> str:
        #"""
        #This method returns the string representation of a Bible book code.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #result = "Greek Bible converter object"
        ##if self.title: result += ('\n' if result else '') + self.title
        ##if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        ##if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        #if len(self.books)==1:
            #for BBB in self.books: break # Just get the first one
            #result += ('\n' if result else '') + "  " + _("Contains one book: {}").format( BBB )
        #else: result += ('\n' if result else '') + "  " + _("Number of books = {:,}").format( len(self.books) )
        #return result
    ## end of __str__


    def loadBooks( self ):
        """
        """
        vPrint( 'Info', debuggingThisModule, "Loading Greek NT from {}…".format( self.sourceFilepath ) )
        for BBB in Greek.morphgntBookList:
            self.loadBook( BBB, Greek.morphgntFilenameDict[BBB] )
        vPrint( 'Verbose', debuggingThisModule, "{} books loaded.".format( len(self.books) ) )
        #if self.possibleFilenames: # then we possibly have multiple files, probably one for each book
            #for filename in self.possibleFilenames:
                #pathname = os.path.join( self.sourceFilepath, filename )
                #self.loadBook( pathname )
        #else: # most often we have all the Bible books in one file
            #self.loadFile( self.sourceFilepath )
        self.doPostLoadProcessing()
    # end of loadBooks

    def load( self ):
        self.loadBooks()


    def loadBook( self, BBB:str, filename, encoding='utf-8' ):

        def unpackLine( line ):
            # Should be seven parts in the line
            #   0 book/chapter/verse
            #   1 part of speech (POS)
            #   2 parsing code
            #   3 text (including punctuation)
            #   4 word (with punctuation stripped)
            #   5 normalized word
            #   6 lemma
            # e.g., 180101 N- ----NSM- Παῦλος Παῦλος Παῦλος Παῦλος
            #       180102 N- ----DSF- ⸀ἀδελφῇ ἀδελφῇ ἀδελφῇ ἀδελφή
            #       180102 P- -------- κατ’ κατ’ κατά κατά
            #       180102 N- ----DSF- ἐκκλησίᾳ· ἐκκλησίᾳ ἐκκλησίᾳ ἐκκλησία
            bits = line.split()
            assert len(bits) == 7
            #vPrint( 'Quiet', debuggingThisModule, bits )

            bn, cn, vn = bits[0][0:2], bits[0][2:4], bits[0][4:6]
            if bn[0]=='0': bn = bn[1:] # Remove any leading zero
            if cn[0]=='0': cn = cn[1:] # Remove any leading zero
            if vn[0]=='0': vn = vn[1:] # Remove any leading zero
            #vPrint( 'Quiet', debuggingThisModule, b, c, v )

            POSCode = bits[1]
            assert len(POSCode) == 2
            assert POSCode in Greek.POSCodes.keys()

            parsingCode = bits[2]
            assert len(parsingCode) == 8
            #vPrint( 'Quiet', debuggingThisModule, parsingCode )
            for j,char in enumerate(parsingCode):
                assert char in Greek.parsingCodes[j]
            assert parsingCode[0] in Greek.personCodes
            assert parsingCode[1] in Greek.tenseCodes
            assert parsingCode[2] in Greek.voiceCodes
            assert parsingCode[3] in Greek.modeCodes
            assert parsingCode[4] in Greek.caseCodes
            assert parsingCode[5] in Greek.numberCodes
            assert parsingCode[6] in Greek.genderCodes
            assert parsingCode[7] in Greek.degreeCodes

            return (bn,cn,vn,), (POSCode,parsingCode,), (bits[3],bits[4],bits[5],bits[6],)
        # end of unpackLine

        self.thisBook = BibleBook( self, BBB )
        self.thisBook.objectNameString = 'Morph Greek NT Bible Book object'
        self.thisBook.objectTypeString = 'MorphGNT'
        filepath = os.path.join( self.sourceFilepath, filename )
        vPrint( 'Info', debuggingThisModule, "  Loading {}…".format( filename ) )
        lastLine, lineCount = '', 0
        lastC = lastV = None
        with open( filepath, encoding=encoding ) as myFile: # Automatically closes the file when done
            if 1: #try:
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and encoding.lower()=='utf-8' and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "GreekNT: Detected Unicode Byte Order Marker (BOM) in {}".format( filename ) )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    #if not line: continue # Just discard blank lines
                    lastLine = line
                    #vPrint( 'Quiet', debuggingThisModule, 'gNT file line is "' + line + '"' )
                    #if line[0]=='#': continue # Just discard comment lines
                    unpackedLine = unpackLine( line )
                    #vPrint( 'Quiet', debuggingThisModule, unpackedLine )
                    ref, grammar, words = unpackedLine
                    bn, cn, vn = ref
                    POSCode, parsingCode = grammar
                    word1, word2, word3, word4 = words
                    if cn != lastC:
                        self.thisBook.addLine( 'c', cn )
                        lastC, lastV = cn, None
                    if vn != lastV:
                        self.thisBook.addLine( 'v', vn )
                        lastV = vn
                    self.thisBook.addLine( 'vw', "{}/{}/{}/{}".format( word1, word2, word3, word4 ) )
                    self.thisBook.addLine( 'g', "{}/{}".format( POSCode, parsingCode ) )
                    #reference = BBB,bits[0][1],bits[0][2], # Put the BBB into the reference
                    #lineTuples.append( (reference,bits[1],bits[2],) )
                    #vPrint( 'Quiet', debuggingThisModule, reference,bits[1],bits[2] ); halt
            #if 0: #except:
                #logging.critical( "Invalid line in " + filepath + " -- line ignored at " + str(lineCount) )
                #if lineCount > 1: vPrint( 'Quiet', debuggingThisModule, 'Previous line was: ', lastLine )
                #else: vPrint( 'Quiet', debuggingThisModule, 'Possible encoding error -- expected', encoding )
        if self.thisBook:
            vPrint( 'Verbose', debuggingThisModule, "    {} words loaded from {}".format( len(self.thisBook), filename ) )
            self.stashBook( self.thisBook )
            #self.books[BBB] = self.thisBook
    # end of loadBook


    def analyzeWords( self ):
        """
        Go through the NT data and do some filing and sorting of the Greek words.

        Used by the interlinearizer app.
        """
        vPrint( 'Verbose', debuggingThisModule, "analyzeWords: have {} books in the loaded NT".format( len(self.books) ) )

        self.wordCounts = {} # Wordcount organised by BBB
        self.wordCounts['Total'] = 0
        self.actualWordsToNormalized, self.normalizedWordsToActual, self.normalizedWordsToParsing, self.lemmasToNormalizedWords = {}, {}, {}, {}
        for BBB in self.books:
            wordCount = len(self.books[BBB])
            self.wordCounts[BBB] = wordCount
            self.wordCounts['Total'] += wordCount
            vPrint( 'Verbose', debuggingThisModule, "  analyzeWords: {} has {} Greek words".format( BBB, wordCount ) )
            for reference,parsing,(punctuatedWord,actualWord,normalizedWord,lemma) in self.books[BBB]: # Stuff is: reference,parsing,words
                # File the actual words
                if actualWord not in self.actualWordsToNormalized:
                    self.actualWordsToNormalized[actualWord] = [([reference],normalizedWord,)]
                    #vPrint( 'Quiet', debuggingThisModule, "Saved", actualWord, "with", self.actualWordsToNormalized[actualWord] )
                else: # we've already had this word before
                    previous = self.actualWordsToNormalized[actualWord]
                    #vPrint( 'Quiet', debuggingThisModule, "had", actualWord, "before with", previous, "now with", reference, normalizedWord )
                    found = changed = False
                    newList = []
                    for oldRefList,oldnormalizedWord in previous:
                        #vPrint( 'Quiet', debuggingThisModule, "  oRL", oldRefList, "oP", oldnormalizedWord )
                        if normalizedWord == oldnormalizedWord:
                            assert not found
                            if reference not in oldRefList:
                                oldRefList.append( reference )
                                newList.append( (oldRefList,oldnormalizedWord,) )
                                changed = True
                            found = True
                        else: newList.append( (oldRefList,oldnormalizedWord,) )
                    if not found:
                        #vPrint( 'Quiet', debuggingThisModule, "  Found a new", normalizedWord, "normalized word for", actualWord, "was", previous )
                        newList.append( ([reference],normalizedWord,) )
                        changed = True
                    if changed:
                        self.actualWordsToNormalized[actualWord] = newList
                        #vPrint( 'Quiet', debuggingThisModule, "  now have", newList )
                # File the normalized words
                if normalizedWord not in self.normalizedWordsToActual:
                    self.normalizedWordsToActual[normalizedWord] = [([reference],actualWord,)]
                    #vPrint( 'Quiet', debuggingThisModule, "Saved", normalizedWord, "with", self.normalizedWordsToActual[normalizedWord] )
                else: # we've already had this word before
                    previous = self.normalizedWordsToActual[normalizedWord]
                    #vPrint( 'Quiet', debuggingThisModule, "had", normalizedWord, "before with", previous, "now with", reference, actualWord )
                    found = changed = False
                    newList = []
                    for oldRefList,oldActualWord in previous:
                        #vPrint( 'Quiet', debuggingThisModule, "  oRL", oldRefList, "oP", oldActualWord )
                        if actualWord == oldActualWord:
                            assert not found
                            if reference not in oldRefList:
                                oldRefList.append( reference )
                                newList.append( (oldRefList,oldActualWord,) )
                                changed = True
                            found = True
                        else: newList.append( (oldRefList,oldActualWord,) )
                    if not found:
                        newList.append( ([reference],actualWord,) )
                        changed = True
                    if changed:
                        self.normalizedWordsToActual[normalizedWord] = newList
                        #vPrint( 'Quiet', debuggingThisModule, "  now have", newList )
                if normalizedWord not in self.normalizedWordsToParsing:
                    self.normalizedWordsToParsing[normalizedWord] = [([reference],parsing,)]
                    #vPrint( 'Quiet', debuggingThisModule, "Saved", normalizedWord, "with", self.normalizedWordsToParsing[normalizedWord] )
                else: # we've already had this word before
                    previous = self.normalizedWordsToParsing[normalizedWord]
                    #vPrint( 'Quiet', debuggingThisModule, "had", normalizedWord, "before with", previous, "now with", reference, parsing )
                    found = changed = False
                    newList = []
                    for oldRefList,oldParsing in previous:
                        #vPrint( 'Quiet', debuggingThisModule, "  oRL", oldRefList, "oP", oldParsing )
                        if parsing == oldParsing:
                            assert not found
                            if reference not in oldRefList:
                                oldRefList.append( reference )
                                newList.append( (oldRefList,oldParsing,) )
                                changed = True
                            found = True
                        else: newList.append( (oldRefList,oldParsing,) )
                    if not found:
                        newList.append( ([reference],parsing,) )
                        changed = True
                    if changed:
                        self.normalizedWordsToParsing[normalizedWord] = newList
                        #vPrint( 'Quiet', debuggingThisModule, "  now have", newList )
                # File the self.lemmasToNormalizedWords
                if lemma not in self.lemmasToNormalizedWords:
                    self.lemmasToNormalizedWords[lemma] = [([reference],normalizedWord,)]
                    #vPrint( 'Quiet', debuggingThisModule, "Saved", lemma, "with", self.lemmasToNormalizedWords[lemma] )
                else: # we've already had this word before
                    previous = self.lemmasToNormalizedWords[lemma]
                    #vPrint( 'Quiet', debuggingThisModule, "had", lemma, "before with", previous, "now with", reference, normalizedWord )
                    found = changed = False
                    newList = []
                    for oldRefList,oldnormalizedWord in previous:
                        #vPrint( 'Quiet', debuggingThisModule, "  oRL", oldRefList, "oP", oldnormalizedWord )
                        if normalizedWord == oldnormalizedWord:
                            assert not found
                            if reference not in oldRefList:
                                oldRefList.append( reference )
                                newList.append( (oldRefList,oldnormalizedWord,) )
                                changed = True
                            found = True
                        else: newList.append( (oldRefList,oldnormalizedWord,) )
                    if not found:
                        newList.append( ([reference],normalizedWord,) )
                        changed = True
                    if changed:
                        self.lemmasToNormalizedWords[lemma] = newList
                        #vPrint( 'Quiet', debuggingThisModule, "  now have", newList )
        vPrint( 'Info', debuggingThisModule, "analyzeWords: NT has {} Greek words".format( self.wordCounts['Total'] ) )
        vPrint( 'Info', debuggingThisModule, "analyzeWords: NT has {} actual Greek words".format( len(self.actualWordsToNormalized) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for j,aW in enumerate( self.actualWordsToNormalized.keys() ):
                vPrint( 'Quiet', debuggingThisModule, "  ", aW, self.actualWordsToNormalized[aW] )
                if j==6: break
        vPrint( 'Info', debuggingThisModule, "analyzeWords: NT has {} normalized Greek words".format( len(self.normalizedWordsToActual) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for j,nW in enumerate( self.normalizedWordsToActual.keys() ):
                vPrint( 'Quiet', debuggingThisModule, "  ", nW, self.normalizedWordsToActual[nW] )
                if j==6: break
        vPrint( 'Info', debuggingThisModule, "analyzeWords: NT has {} normalized Greek words".format( len(self.normalizedWordsToParsing) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for j,nW in enumerate( self.normalizedWordsToParsing.keys() ):
                vPrint( 'Quiet', debuggingThisModule, "  ", nW, self.normalizedWordsToParsing[nW] )
                if j==6: break
        vPrint( 'Info', debuggingThisModule, "analyzeWords: NT has {} Greek self.lemmasToNormalizedWords".format( len(self.lemmasToNormalizedWords) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for j,lem in enumerate( self.lemmasToNormalizedWords.keys() ):
                vPrint( 'Quiet', debuggingThisModule, "  ", lem, self.lemmasToNormalizedWords[lem] )
                if j==6: break
        if 0:
            vPrint( 'Quiet', debuggingThisModule, "The following actual words have multiple normalized forms:" )
            for j,aW in enumerate( self.actualWordsToNormalized.keys() ):
                if len(self.actualWordsToNormalized[aW])>1:
                    vPrint( 'Quiet', debuggingThisModule, "  ", aW )
                    for entry in self.actualWordsToNormalized[aW]:
                        vPrint( 'Quiet', debuggingThisModule, "    ", entry[1], self.normalizedWordsToParsing[entry[1]], entry[0] )
    # end of analyzeWords


    #def xgetVerseDataList( self, reference ):
        #""" Return the text for the verse with some adjustments. """
        #assert len(reference) == 3 # BBB,C,V
        #BBB, chapterString, verseString = reference
        #assert isinstance(BBB,str) and len(BBB)==3
        #assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
        #assert isinstance( chapterString, str )
        #assert isinstance( verseString, str )
        #data = []
        #if BBB in self.books:
            #for stuff in self.books[BBB]: # Stuff is: reference,parsing,words
                #if chapterString==stuff[0][1] and verseString==stuff[0][2]:
                    ##vPrint( 'Quiet', debuggingThisModule, reference, stuff )
                    #data.append( stuff )
        #if data:
            ##myData = []
            ##for word,lemma in data:
            ##    myData.append( (word.replace('/','='), lemma,) )
            ##return myData
            #return data
        #else: vPrint( 'Quiet', debuggingThisModule, "oops. empty verse data for", reference )
    ## end of getVerseDataList

    #def xgetVerseText( self, reference ):
        #""" Return the text for the verse with some adjustments. """
        #verseData = self.getVerseDataList( reference )
        #self.originalText = ''
        #for stuff in verseData: # Stuff is: reference,parsing,words
            #if self.originalText: self.originalText += ' '
            #self.originalText += stuff[2][0]
        ##if self.originalText: self.originalText = self.originalText.replace(' '+'־'+' ','־') # Remove spaces around the maqqef
        ##if self.originalText: self.originalText = self.originalText.replace('/','=') # We use = for morpheme break character not /
        #self.currentText = self.originalText
        #if self.originalText: return self.originalText
        #else: vPrint( 'Quiet', debuggingThisModule, "oops. empty verse text for", reference )
    ## end of getVerseText
# end of GreekNT class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    fileFolder = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../ExternalPrograms/morphgnt/sblgnt/' )

    # Demonstrate the Greek NT class
    vPrint( 'Normal', debuggingThisModule, "\nDemonstrating the Greek NT class…" )
    testReference = SimpleVerseKey('MAT', '1', '1')
    #vPrint( 'Quiet', debuggingThisModule, testFolder, testReference )
    gNT = GreekNT( fileFolder ) # Load and process the XML
    gNT.loadBooks()
    #gNT.analyzeWords() # File and sort the Greek words for later use
    vPrint( 'Quiet', debuggingThisModule, gNT ) # Just print a summary
    vPrint( 'Quiet', debuggingThisModule, '' )
    vPrint( 'Quiet', debuggingThisModule, testReference, gNT.getVerseDataList( testReference ) )
    vPrint( 'Quiet', debuggingThisModule, '' )

    for testReference in SimpleVerseKey('MAT', '28', '1'), SimpleVerseKey('MRK','2','2'), SimpleVerseKey('REV','21','21'):
        verseText = gNT.getVerseText( testReference )
        vPrint( 'Quiet', debuggingThisModule, testReference, verseText )
        vPrint( 'Quiet', debuggingThisModule, '' )
# end of fullDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of GreekNT.py
