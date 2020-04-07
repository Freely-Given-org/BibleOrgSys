#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# PalmDBBible.py
#
# Module handling PDB Bible files
#
# Copyright (C) 2013-2019 Robert Hunt
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
Module reading and loading PalmDB Bible files.

See documentation of the format here:
    http://yohan.es/bible-pdb/bible-plus-pdb-format/
e.g.,

    …

Limitations:
    …
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-05-12' # by RJH
SHORT_PROGRAM_NAME = "PDBBible"
PROGRAM_NAME = "PDB Bible format handler"
PROGRAM_VERSION = '0.67'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, struct
import multiprocessing
from binascii import hexlify


if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook


filenameEndingsToAccept = ('.PDB',) # Must be UPPERCASE



def PalmDBBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for PDB Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one PDB Bible is found,
        returns the loaded PalmDBBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "PalmDBBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("PalmDBBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("PalmDBBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " PalmDBBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            if somethingUpperExt in filenameEndingsToAccept:
                foundFiles.append( something )

    # See if there's an PalmDBBible project here in this given folder
    numFound = 0
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename.endswith( '.PDB' ):
            #if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                #firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName )
                #if not firstLine.startswith( "info\t"):
                    #if BibleOrgSysGlobals.verbosityLevel > 2: print( "PalmDBBible (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                    #continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PalmDBBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = PalmDBBible( givenFolderName, lastFilenameFound[:-4] ) # Remove the end of the actual filename ".PDB"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("PalmDBBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    PalmDBBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                if somethingUpperExt in filenameEndingsToAccept:
                    foundSubfiles.append( something )

        # See if there's an PalmDBBible project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if thisFilename.endswith( '.PDB' ):
                #if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                    #firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName )
                    #if not firstLine.startswith( "info\t"):
                        #if BibleOrgSysGlobals.verbosityLevel > 2: print( "PalmDBBible (unexpected) first line was {!r} in {}".format( firstLine, thisFilname ) ); halt
                        #continue
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PalmDBBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            uB = PalmDBBible( foundProjects[0][0], foundProjects[0][1][:-4] ) # Remove the end of the actual filename ".PDB"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of PalmDBBibleFileCheck



class PalmDBBible( Bible ):
    """
    Class for reading, validating, and converting PalmDBBible files.
    """
    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'PDB Bible object'
        self.objectTypeString = 'PDB'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'.PDB' )
        if not os.access( self.sourceFilepath, os.R_OK ):
            self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'.pdb' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("PalmDBBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of PalmDBBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )
        loadErrors = []
        mainDBIndex = []


        def readRecord( recordNumber, thisFile ):
            """
            Uses mainDBIndex to read in the specified PalmDB record.
                dataOffset gives the file offset from the beginning of the file.
            """
            if BibleOrgSysGlobals.debugFlag:
                if debuggingThisModule:
                    print( _("readRecord( {}, {} )").format( recordNumber, thisFile ) )
                assert recordNumber < len(mainDBIndex)
            dataOffset, recordLength, recordAttributes, id0, id1, id2 = mainDBIndex[recordNumber]
            #recordLength = 99999 if recordNumber==len(mainDBIndex)-1 else (mainDBIndex[recordNumber+1][0] - dataOffset)
            #print( " dataOffset={} recordLength={}".format( dataOffset, recordLength ) )
            #print( " recordAttributes={} id0={} id1={} id2={}".format( recordAttributes, id0, id1, id2 ) )
            thisFile.seek( dataOffset )
            #print( "Reading {} bytes from record {} at offset {}".format( recordLength, recordNumber, dataOffset ) )
            binaryInfo = thisFile.read( recordLength )
            if recordNumber < len(mainDBIndex)-1: assert len(binaryInfo) == recordLength
            return binaryInfo
        # end of readRecord

        characterReplacements = ( ( '\xe2\x80\x94', '—' ), ( '\xe2\x80\x96', 'WWW' ),
                                  ( '\xe2\x80\x98', '’' ), ( '\xe2\x80\x99', '’' ),
                                  ( '\xe2\x80\x9c', '“' ), ( '\xe2\x80\x9d', '”' ),
                                  ( 'Ã\x83Æ\x92Ã\x82Â¡', 'á' ), ( 'Ã\x83Æ\x92Ã\x82Â©', 'é' ), ( 'Ã\x83Æ\x92Ã\x82Â\xad', 'í' ), )
        def getBinaryString( binary, numBytes ):
            """
            Gets bytes out of the binary and converts them to characters.
            Stops when numBytes is reached, or a NULL is encountered.

            Returns the string.
            """
            #if BibleOrgSysGlobals.debugFlag:
                #print( _("getBinaryString( {}={}, {} )").format( hexlify(binary), binary, numBytes ) )
            if len(binary) < numBytes: halt # Too few bytes provided
            binary = binary[:numBytes]
            if debuggingThisModule:
                for someInt in binary:
                    #print( repr(someInt) )
                    if someInt == 0xe2:
                        print( _("getBinaryString( {}={}, {} ) found e2").format( hexlify(binary), binary, numBytes ) )
            result = ''
            errorFlag = False
            for j, value in enumerate( binary ):
                if j>=numBytes or value==0: break
                if value > 0x7F:
                    if debuggingThisModule:
                        print( _("getBinaryString( {}={}, {} ) found non-ascii").format( hexlify(binary), binary, numBytes ) )
                        print( "{} Got non-ASCII character {:02x}->{!r}".format( j, value, chr(value) ) )
                    errorFlag = True
                result += chr( value )
            if errorFlag:
                if debuggingThisModule:
                    #print( "{:04x}".format( ord('“') ) ) # ”
                    print( "Got1 invalid string {!r}".format( result ) )
                result = result.replace( '\x97', '—' )
                if numBytes == 1:
                    if result == '\x92': result = '’'
                    #elif result == '\x97': result = '—'
                elif numBytes >= 3:
                    bits = binary[1:3]
                    if debuggingThisModule:
                        print( "bits {!r}".format( bits ) )
                        bitInt, = struct.unpack( ">H", bits )
                        print( "bitInt {:04x}".format( bitInt ) )
                        print( "try", repr(bits.decode(encoding='latin-1')) )
                    for byteSeries, replacement in characterReplacements:
                        ix =  result.find( byteSeries )
                        if debuggingThisModule and ix != -1: print( "found {}".format( byteSeries ) )
                        result = result.replace( byteSeries, replacement )
                    #if   result.startswith( '\xe2\x80\x94' ): result = 'XXX' + result[3:]
                    #elif result.startswith( '\xe2\x80\x98' ): result = 'YYY' + result[3:]
                    #elif result.startswith( '\xe2\x80\x99' ): result = 'ZZZ' + result[3:]
                    #elif result.startswith( '\xe2\x80\x9c' ): result = 'PPP' + result[3:]
                    #elif result.startswith( '\xe2\x80\x9d' ): result = 'QQQ' + result[3:]
                    #else: halt
                    if debuggingThisModule:
                        if '\xe2' in result: halt
                        print( "Got2 invalid string {!r}".format( result ) )
            return result
        # end of getBinaryString


        def getFileString( thisFile, numBytes ):
            """
            Used for reading the PalmDB header information from the file.
            """
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( _("getFileString( {}, {} )").format( thisFile, numBytes ) )
            return getBinaryString( thisFile.read( numBytes ), numBytes )
        # end of getFileString


        words = []
        def loadWordlists():
            """
            """
            nonlocal words
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( _("loadWordlists()") )

            # Now read the word index info
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Loading word index info…" )
            binary = readRecord( wordIndexIndex, myFile )
            byteOffset = 0
            totalIndicesCount, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
            #print( " totalIndicesCount =",totalIndicesCount )
            wordIndexMetadata = []
            expectedWords = 0
            for n in range( totalIndicesCount ):
                wordLength, numFixedLengthWords, compressedFlag, ignored = struct.unpack( ">HHBB",  binary[byteOffset:byteOffset+6] ); byteOffset += 6
                if BibleOrgSysGlobals.verbosityLevel > 3:
                    print( "   {:2}: wordLength={} numFixedLengthWords={} compressedFlag={}".format( n, wordLength, numFixedLengthWords, compressedFlag ) )
                wordIndexMetadata.append( (wordLength, numFixedLengthWords, compressedFlag) )
                expectedWords += numFixedLengthWords
            assert byteOffset == len(binary)
            #print( " expectedWords =", expectedWords )
            #if BibleOrgSysGlobals.debugFlag:
                #halt

            # Now read in the word lists
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "\nLoading word lists…" )
            #binary = readRecord( wordIndexIndex+1, myFile )
            recordOffset = byteOffset = 0
            binary = b''
            numRegularWords = numCompressedWords = 0
            wordCountIndexes = {}
            for wordLength, numFixedLengthWords, compressedFlag in wordIndexMetadata:
                #print( "   Got {} {:04x}".format( len(words), len(words) ) )
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "    Loading wordLength={} numFixedLengthWords={} compressedFlag={}…".format( wordLength, numFixedLengthWords, compressedFlag ) )
                wordStart = wordCountIndexes[wordLength] = len(words) # Remember where certain lengths of words start
                #else: print( wordCountIndexes )
                for n in range( numFixedLengthWords ):
                    numRemainingBufferBytes = len(binary) - byteOffset
                    #print( "Got {} bytes available in buffer".format(  numRemainingBufferBytes ) )
                    if numRemainingBufferBytes < wordLength: # Need to continue to the next record
                        #binary += myFile.read( 256 ) # These records are assumed here to be contiguous
                        binary += readRecord( wordIndexIndex+recordOffset+1, myFile )
                        recordOffset += 1
                    if not compressedFlag:
                        # We have a pointer to an array of characters
                        #if len(binary)-byteOffset < wordLength: # Need to continue to the next record
                            #binary += myFile.read( 256 )
                        wordBytes = binary[byteOffset:byteOffset+wordLength]; byteOffset += wordLength
                        word = getBinaryString( wordBytes, wordLength )
                        if debuggingThisModule: print( "@{:04x}={} {} {!r}".format( len(words), len(words), wordLength, word ) )
                        if word == '\t': word = '    '
                        elif word == '\n': word = '<NEWLINE>'
                        elif '\\' in repr(word):
                            if word[0] == '\\': word = '«' + word[1:] # Not sure what this should mean or should be???
                            if word[-1] == '\\': word = word[:-1] + '»' # Not sure what this should mean or should be???
                            ok = False
                            for stuff in ( '\'', '\x0eb\x0e', '\x0ei\x0e', '\x0en\x0e', '\x0er\x0e', ):
                                if '\\' not in repr(word.replace( stuff, '' )): ok = True
                            if not ok:
                                logging.warning( "PalmDBBible: Found unexpected slash in dictionary word {!r} @ {:04x}={} from {}".format( word, len(words), len(words), hexlify(wordBytes) ) )
                                loadErrors.append( _("PalmDBBible: Found unexpected slash in dictionary word {!r} @ {:04x}={}").format( word, len(words), len(words) ) )
                                #thisBook.addPriorityError( 20, C, V, _("Found unexpected slash in dictionary word {!r} @ {:04x}={}").format( word, len(words), len(words) ) )
                                if debuggingThisModule:
                                    print( "      Found unexpected slash in dictionary word {!r} @ {:04x}={}".format( word, len(words), len(words) ) )
                                    halt
                        words.append( word )
                        numRegularWords += 1
                    else: # it's a compressed word
                        # We have pointers to smaller words
                        assert wordLength == 4 # But this is the number of bytes, not the number of word characters!
                        if debuggingThisModule: print( "compressed", byteOffset, hexlify(binary[byteOffset:byteOffset+4]) )
                        ix1,ix2 = struct.unpack( ">HH",  binary[byteOffset:byteOffset+4] ); byteOffset += 4
                        if   ix1 == 0xFFFF: word1 = '<BOOK>'
                        elif ix1 == 0xFFFE: word1 = '<CHAPTER>'
                        elif ix1 == 0xFFFD: word1 = '<DESC>'
                        elif ix1 == 0xFFFC: word1 = '<VERSE>'
                        else: word1 = words[ix1-1]
                        if   ix2 == 0xFFFF: word2 = '<BOOK>'
                        elif ix2 == 0xFFFE: word2 = '<CHAPTER>'
                        elif ix2 == 0xFFFD: word2 = '<DESC>'
                        elif ix2 == 0xFFFC: word2 = '<VERSE>'
                        else: word2 = words[ix2-1]
                        if debuggingThisModule: print( "@{:04x}={} word1={!r} word2={!r}".format( len(words), len(words), word1, word2 ) )
                        word = word1 + separatorCharacter + word2
                        if 0:
                            print( ' ix1={:04x}={}'.format( ix1, ix1 ) )
                            print( '   word1={!r}'.format( word1 ) )
                            print( ' ix2={:04x}={}'.format( ix2, ix2 ) )
                            print( '   word2={!r}'.format( word2 ) )
                            print( "Assembled word={!r}".format( word ) )
                        words.append( word )
                        numCompressedWords += 1
                if debuggingThisModule:
                    numLoaded = len(words) - wordStart
                    wordDisplay = words[wordStart:] if numLoaded < 10 else repr(words[wordStart])+'..'+repr(words[-1])
                    print( "      Loaded {} {}-char words (now have {}={:04x} total): {}".format( numLoaded, wordLength, len(words), len(words), wordDisplay ) )
            #print( 'xyz', byteOffset, len(binary) )
            assert byteOffset == len(binary)
        # end of loadWordlists


        remainder14count = remainder14bits = 0
        def get14( binary16 ):
            """
            Get the next 14-bits from the 16 binary bits supplied
                plus any remainder from the last call.
            """
            nonlocal remainder14count, remainder14bits
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( _("get14( {} ) {} {:04x}").format( hexlify(binary16), remainder14count, remainder14bits ) )
            if binary16: next16, = struct.unpack( ">H", binary16 )
            else:
                if debuggingThisModule: print( "Added error zero bits (should only be at the end of a book)" )
                next16 = 0
            #print( "next16 {:04x} {}".format( next16, next16 ) )
            if remainder14count == 0:
                result = next16 >> 2
                remainder14count = 2
                remainder14bits = (next16 & 0x0003) << 12
                bytesUsed = 2
            elif remainder14count == 2:
                result = (next16 >> 4) | remainder14bits
                remainder14count = 4
                remainder14bits = (next16 & 0x000F) << 10
                bytesUsed = 2
            elif remainder14count == 4:
                result = (next16 >> 6) | remainder14bits
                remainder14count = 6
                remainder14bits = (next16 & 0x003F) << 8
                bytesUsed = 2
            elif remainder14count == 6:
                result = (next16 >> 8) | remainder14bits
                remainder14count = 8
                remainder14bits = (next16 & 0x00FF) << 6
                bytesUsed = 2
            elif remainder14count == 8:
                result = (next16 >> 10) | remainder14bits
                remainder14count = 10
                remainder14bits = (next16 & 0x03FF) << 4
                bytesUsed = 2
            elif remainder14count == 10:
                result = (next16 >> 12) | remainder14bits
                remainder14count = 12
                remainder14bits = (next16 & 0x0FFF) << 2
                bytesUsed = 2
            elif remainder14count == 12:
                result = (next16 >> 14) | remainder14bits
                remainder14count = 14
                remainder14bits = next16 & 0x03FFF
                bytesUsed = 2
            elif remainder14count == 14:
                result = remainder14bits
                remainder14count = 0
                bytesUsed = 0
            #print( " returning {:04x}={}, {} ({})".format( result, result, bytesUsed, remainder14count ) )
            return result, bytesUsed
        # end of get14


        hadP = False
        def saveSegment( BBB, C, V, verseText ):
            """
            Used to save the verse data into the global thisBook.
            """
            nonlocal hadP
            if BibleOrgSysGlobals.debugFlag:
                if debuggingThisModule:
                    print( _("saveSegment( {} {}:{}, {!r} )").format( BBB, C, V, verseText ) )
                assert verseText
                if 'SQ' in verseText or 'AAA' in verseText or 'XXX' in verseText or 'WWW' in verseText:
                    print( "What's this here for:", repr(verseText) )
                    if debuggingThisModule: halt

            adjText = verseText.strip().replace( ' .', '.' ).replace( ' ,', ',' ) \
                                       .replace( ' :', ':' ).replace( ' ;', ';' ).replace( ' ?', '?' ) \
                                       .replace( '[ ', '[' ).replace( ' ]', ']' ) \
                                       .replace( ' ”', '”' ).replace( ' ’', '’' )
            for fChar, fSFM in ( ('i','add'), ('r','wj'), ('b','b'), ('n','i'), ):
                inside = False
                while '\x0e'+fChar+'\x0e' in adjText:
                    adjText = adjText.replace( '\x0e'+fChar+'\x0e', '\\'+fSFM+'*' if inside else '\\'+fSFM, 1 )
                    inside = not inside
                if '\x0en\x0e' not in verseText: # WHY ???
                    assert not inside # Would be uneven number of matches
                adjText = adjText.replace( ' \\'+fSFM+'*', '\\'+fSFM+'*' ) # Remove unwanted spaces before closing field
                #print( "  adjText1={!r}".format( adjText ) )
            if '\x0en\x0e' not in adjText: # WHY ???
                assert '\x0e' not in adjText
            #print( "  adjText2={!r}".format( adjText1 ) )
            if '\\x' in repr(adjText):
                print( "What's this slash here for:", repr(adjText) )
                if debuggingThisModule: halt
            #adjText1 = adjText

            # Put footnotes in properly
            while '{' in adjText and '}' in adjText: # assume it's a footnote
                ixStart = adjText.index( '{' )
                ixEnd = adjText.index( '}' )
                assert ixEnd > ixStart
                #print( "Replacing footnote from {}-{} in {!r}".format( ixStart, ixEnd, adjText ) )
                adjText = adjText[:ixStart].rstrip() + '\\f + \\ft {}\\f*'.format( adjText[ixStart+1:ixEnd].strip() ) + adjText[ixEnd+1:]
                #print( "  Now have: {!r}".format( adjText ) )

            # Split verse data into separate logical fields where necessary
            adjText = adjText.replace( '<NEWLINE>', '\\m ' )
            if adjText.startswith( '<BOOK>' ):
                assert C == 0
                adjText = adjText[6:].lstrip()
                if debuggingThisModule: print( "  adjText BOOK={!r}".format( adjText ) )
                thisBook.addLine( 'mt', adjText ); adjText = ''
            elif adjText.startswith( '<CHAPTER>' ):
                assert C > 0
                adjText = adjText[9:].lstrip()
                thisBook.addLine( 'c', str(C) )
                thisBook.addLine( 's', adjText ); adjText = ''
                thisBook.addLine( 'p', '' ); hadP = True
            elif adjText.startswith( '<VERSE>' ):
                assert C > 0
                adjText = adjText[7:].lstrip()
            elif adjText.startswith( '<DESC>' ):
                adjText = adjText[6:].lstrip()
                if debuggingThisModule: print( "  adjText DESC={!r}".format( adjText ) )
                marker = 'ip' if C==0 else 's'
                thisBook.addLine( marker, adjText ); adjText = ''
                if marker == 's': thisBook.addLine( 'p', '' ); hadP = True
            if adjText:
                if not hadP:
                    thisBook.addLine( 'p', '' ); hadP = True
                #if adjText != adjText1: print( "  adjText3={!r}".format( adjText ) )
                thisBook.addLine( 'v', '{} {}'.format( V, adjText ) )
        # end of saveSegment


        # main code for load()
        with open( self.sourceFilepath, 'rb' ) as myFile: # Automatically closes the file when done
            # Read the PalmDB header info
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Loading PalmDB header info…" )
            name = getFileString( myFile, 32 )
            binary4 = myFile.read( 4 )
            attributes, version = struct.unpack( ">hh", binary4 )
            binary12 = myFile.read( 12 )
            creationDate, lastModificationDate, lastBackupDate = struct.unpack( ">III", binary12 )
            binary12 = myFile.read( 12 )
            modificationNumber, appInfoID, sortInfoID = struct.unpack( ">III", binary12 )
            appType = getFileString( myFile, 4 )
            creator = getFileString( myFile, 4 )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  name = {!r} appType = {!r} creator = {!r}".format( name, appType, creator ) )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                print( "  attributes={} version={}".format( attributes, version ) )
                print( "  creationDate={} lastModificationDate={} lastBackupDate={}".format( creationDate, lastModificationDate, lastBackupDate ) )
                print( "  modificationNumber={} appInfoID={} sortInfoID={}".format( modificationNumber, appInfoID, sortInfoID ) )
            binary4 = myFile.read( 4 )
            uniqueIDseed = struct.unpack( ">I", binary4 )
            binary6 = myFile.read( 6 )
            nextRecordListID, numDBRecords = struct.unpack( ">IH", binary6 )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                print( "  uniqueIDseed={} nextRecordListID={} numDBRecords={}".format( uniqueIDseed, nextRecordListID, numDBRecords ) )
                print( "  numDBRecords =", numDBRecords )
            tmpIndex = []
            for n in range( numDBRecords ):
                binary8 = myFile.read( 8 )
                dataOffset, recordAttributes, id0, id1, id2 = struct.unpack( ">IBBBB", binary8 )
                #print( '', dataOffset, recordAttributes, id0, id1, id2 )
                assert recordAttributes + id0 + id1 + id2 == 0
                tmpIndex.append( (dataOffset, recordAttributes, id0, id1, id2) )
            for recordNumber in range( len(tmpIndex) ):
                dataOffset, recordAttributes, id0, id1, id2 = tmpIndex[recordNumber]
                recordLength = 4096 if recordNumber==len(tmpIndex)-1 else (tmpIndex[recordNumber+1][0] - dataOffset)
                mainDBIndex.append( (dataOffset, recordLength, recordAttributes, id0, id1, id2) )
            if 0:
                print( "  {} DB header bytes read".format( myFile.tell() ) )
                print()
                for recordNumber in range( len(mainDBIndex) ):
                    dataOffset, recordLength, recordAttributes, id0, id1, id2 = mainDBIndex[recordNumber]
                    print( "Record {} @ {} len={} attribs={} {} {} {}".format( recordNumber, dataOffset, recordLength, recordAttributes, id0, id1, id2 ) )
                    #assert recordLength <= 4096
                    if 0:
                        recordBytes = readRecord( recordNumber, myFile )
                        if recordNumber < 8 or recordLength < 200:
                            print( "    {}\n    {}".format( hexlify(recordBytes), recordBytes ) )
                        else: print( "    {}".format( hexlify(recordBytes) ) )
            #if BibleOrgSysGlobals.debugFlag:
                #halt

            # Now read the first record of actual Bible data which is the Bible header info
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "\nLoading Bible header info…" )
            binary = readRecord( 0, myFile )
            byteOffset = 0
            versionName = getBinaryString( binary, 16 ); byteOffset += 16
            versionInfo = getBinaryString( binary[byteOffset:], 128 ); byteOffset += 128
            separatorCharacter = getBinaryString( binary[byteOffset:], 1 ); byteOffset += 1
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( repr(versionName), repr(versionInfo), repr(separatorCharacter) )
            assert separatorCharacter == ' '
            versionAttribute, wordIndexIndex, numWordListRecords, numBooks = struct.unpack( ">BHHH",  binary[byteOffset:byteOffset+7] ); byteOffset += 7
            #print( "  versionAttribute =",versionAttribute )
            copyProtectedFlag = versionAttribute & 1
            byteShiftedFlag = not versionAttribute & 2
            RTLFlag = versionAttribute & 4
            if BibleOrgSysGlobals.verbosityLevel > 1:
                if copyProtectedFlag: print( " Copy protected!" ); halt
                else: print( " Not copy protected." )
                if byteShiftedFlag: print( "  BYTE SHIFTED! # See http://en.wikipedia.org/wiki/Shift_JIS for Japanese" )
                else: print( " Not byte shifted." )
                if RTLFlag: print( " Right-aligned (RTL languages)!" ); halt
                else: print( " Left-aligned (LTR languages)." )
                if BibleOrgSysGlobals.verbosityLevel > 3:
                    print( "  wordIndexIndex={} numWordListRecords={} numBooks={}".format( wordIndexIndex, numWordListRecords, numBooks ) )
            bookIndexMetadata = []
            for n in range(  0, numBooks ):
                bookNumber, bookRecordLocation, numBookRecords = struct.unpack( ">HHH",  binary[byteOffset:byteOffset+6] ); byteOffset += 6
                shortName = getBinaryString( binary[byteOffset:], 8 ); byteOffset += 8
                longName = getBinaryString( binary[byteOffset:], 32 ); byteOffset += 32
                if BibleOrgSysGlobals.verbosityLevel > 3:
                    print( '    Book {:2}: {!r} {!r} bkNum={} loc={} numBookRecords={}'.format( n+1, shortName, longName, bookNumber, bookRecordLocation, numBookRecords ) )
                bookIndexMetadata.append( (shortName, longName, bookNumber, bookRecordLocation, numBookRecords) )
            assert byteOffset == len(binary)
            #if BibleOrgSysGlobals.debugFlag:
                #print( "bookIndexMetadata", len(bookIndexMetadata), bookIndexMetadata )
                #halt

            # Now load the word lists
            loadWordlists()
            numWords = len(words)
            if debuggingThisModule: print( "numWords =", numWords )
            #if BibleOrgSysGlobals.debugFlag:
                #print( "words", numWords, words[:200], words[-80:] )
                #halt

            # Now read in the Bible book chapter/verse data
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Loading Bible book chapter/verse lists…" )
            ## There seems to be no absolute standard for these :-(
            #convertSNtoBBB = {'GE':'GEN', 'EX':'EXO', 'DTN':'DEU', '1SAM':'SA1', '2SAM':'SA2', '1SA':'SA1', '2SA':'SA2', '1KI':'KI1', '2KI':'KI2',
                            #'1CHR':'CH1', '2CHR':'CH2', '1CH':'CH1', '2CH':'CH2', 'PS':'PSA', 'PRV':'PRO', 'SONG':'SNG', 'EZK':'EZE', 'JOEL':'JOL',
                            #'AM':'AMO', 'NAM':'NAH', 'OBD':'OBA', 'JON':'JNA', 'MI':'MIC',
                            #'MT':'MAT', 'MK':'MRK', 'LK':'LUK', 'JOHN':'JHN', '1COR':'CO1', '2COR':'CO2', '1CO':'CO1', '2CO':'CO2',
                            #'PHIL':'PHP', '1THESS':'TH1', '2THESS':'TH2', '1TH':'TH1', '2TH':'TH2', '1TIM':'TI1', '2TIM':'TI2', '1TI':'TI1', '2TI':'TI2',
                            #'JAS':'JAM', 'PHLM':'PHM', '1PET':'PE1', '2PET':'PE2', '1PE':'PE1', '2PE':'PE2', '1JO':'JN1', '2JO':'JN2', '3JO':'JN3', '1JN':'JN1', '2JN':'JN2', '3JN':'JN3',
                            #'JUDE':'JDE', 'JUD':'JDE', }
            #convertBNtoBBB = {10:'GEN', 20:'EXO', 30:'LEV', 40:'NUM', 50:'DEU', '1SAM':'SA1', '2SAM':'SA2', '1SA':'SA1', '2SA':'SA2', '1KI':'KI1', '2KI':'KI2',
                            #'1CHR':'CH1', '2CHR':'CH2', '1CH':'CH1', '2CH':'CH2', 'PS':'PSA', 'PRV':'PRO', 'SONG':'SNG', 'EZK':'EZE', 'JOEL':'JOL',
                            #'AM':'AMO', 'NAM':'NAH', 'OBD':'OBA', 'JON':'JNA', 'MI':'MIC',
                            #'MT':'MAT', 'MK':'MRK', 'LK':'LUK', 'JOHN':'JHN', '1COR':'CO1', '2COR':'CO2', '1CO':'CO1', '2CO':'CO2',
                            #'PHIL':'PHP', '1THESS':'TH1', '2THESS':'TH2', '1TH':'TH1', '2TH':'TH2', '1TIM':'TI1', '2TIM':'TI2', '1TI':'TI1', '2TI':'TI2',
                            #'JAS':'JAM', 'PHLM':'PHM', '1PET':'PE1', '2PET':'PE2', '1PE':'PE1', '2PE':'PE2', '1JO':'JN1', '2JO':'JN2', '3JO':'JN3', '1JN':'JN1', '2JN':'JN2', '3JN':'JN3',
                            #'JUDE':'JDE', 'JUD':'JDE', }
            for shortName, longName, bookNumber, bookRecordLocation, numBookRecords in bookIndexMetadata:
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "\n{!r} {!r} bookNumber={} bookRecordLocation={} numBookRecords={}".format( shortName, longName, bookNumber, bookRecordLocation, numBookRecords ) )
                #myFile.seek( mainDBIndex[bookRecordLocation] )
                #binary = myFile.read( 102400 )
                # Read the header record
                binary = readRecord( bookRecordLocation, myFile )
                #print( binary )
                byteOffset = 0
                numChapters, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                #print( longName, "numChapters", numChapters )
                accumulatedVersesList = []
                for c in range( numChapters ):
                    accumulatedVerses, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                    accumulatedVersesList.append( accumulatedVerses )
                    #print( c+1, accumulatedVerses, "accumulatedVerses" )
                accumulatedTokensPerChapterList = []
                for c in range( numChapters ):
                    accumulatedTokensPerChapter, = struct.unpack( ">I",  binary[byteOffset:byteOffset+4] ); byteOffset += 4
                    #print( c+1, accumulatedTokensPerChapter, "accumulatedTokensPerChapter" )
                    accumulatedTokensPerChapterList.append( accumulatedTokensPerChapter )
                accumulatedTokensPerVerseList = []
                totalAccumulatedVerses = 0
                for n in range( accumulatedVerses ):
                    accumulatedTokensPerVerse, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                    #print( n+1, accumulatedTokensPerVerse, "accumulatedTokensPerVerse" )
                    accumulatedTokensPerVerseList.append( accumulatedTokensPerVerse )
                    totalAccumulatedVerses += accumulatedTokensPerVerse
                if debuggingThisModule:
                    print( "accumulatedVerses", len(accumulatedVersesList), accumulatedVersesList )
                    print( "accumulatedTokensPerChapter", len(accumulatedTokensPerChapterList), accumulatedTokensPerChapterList )
                    print( "accumulatedTokensPerVerse", len(accumulatedTokensPerVerseList), accumulatedTokensPerVerseList )
                assert len(accumulatedTokensPerVerseList) == accumulatedVerses
                #print( "Acc V & T", totalAccumulatedVerses, accumulatedTokensPerChapter )
                assert byteOffset == len(binary)

                # Find total characters
                #totalCharacters = 0
                #for accumulatedVerses in accumulatedVersesList:
                    #totalCharacters += accumulatedTokensPerVerseList[accumulatedVerses]
                totalCharacters = accumulatedTokensPerChapterList[-1] + accumulatedTokensPerVerseList[-1]
                #print( "totalCharacters", totalCharacters )

                # Read the Bible word data records
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "\nReading {}{} Bible words for {} {}/{}…".format( totalCharacters, ' byte-shifted' if byteShiftedFlag else '', name, shortName, longName ) )
                BBB = None
                if bookNumber % 10 == 0:
                    if bookNumber <= 160:
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bookNumber / 10 )
                    elif bookNumber == 170: BBB = 'TOB'
                    elif bookNumber == 180: BBB = 'JDT'
                    elif bookNumber == 190: BBB = 'EST'
                    elif 220 <= bookNumber <= 260:
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( (bookNumber-40) / 10 )
                    elif 290 <= bookNumber <= 310:
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( (bookNumber-60) / 10 )
                    elif bookNumber == 320: BBB = 'BAR'
                    elif 330 <= bookNumber <= 730:
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( (bookNumber-70) / 10 )
                elif bookNumber == 315: BBB = 'LJE'
                #BBB = convertBNtoBBB[bookNumber]
                #shortNameUpper = shortName.upper()
                #BBB = convertSNtoBBB[shortNameUpper] if shortNameUpper in convertSNtoBBB else shortNameUpper
                if BibleOrgSysGlobals.verbosityLevel > 2: print( " Loading {} {}…".format( name, BBB ) )
                #if self.name == 'kjv' and BBB=='GAL': continue
                thisBook = BibleBook( self, BBB )
                thisBook.objectNameString = 'Palm Bible Book object'
                thisBook.objectTypeString = 'Palm'
                #thisBook.addLine( 'id', BBB ) # Would need to be USFM code not BBB!
                thisBook.addLine( 'h', longName )
                thisBook.addLine( 'toc1', longName )
                thisBook.addLine( 'toc1', longName )
                thisBook.addLine( 'toc3', shortName )
                hadP = False

                C = V = 0
                nextRecordNumber = bookRecordLocation+1
                accumulatedVerseCount = verseCount = recordCount = 0
                remainder14count = remainder14bits = 0
                byteOffset = 0
                binary = b''
                verse = ''
                for j in range( totalCharacters ):
                    #if BBB=='EXO' and V==3: halt
                    #print( self.name )
                    #if (name == 'kjv' and BBB=='GAL' and V>5) \
                    #or (name == 'kjv' and BBB=='TI2' and V>24) \
                    #or (name in ('hcsba','i_tb','AYT','i_bis',) and BBB=='GAL' and V>24):
                        #logging.error( "PalmDBBible: Aborted book {} at {}:{} because of formatting issue".format( BBB, C, V ) )
                        #loadErrors.append( _("PalmDBBible: Aborted book {} at {}:{} because of formatting issue").format( BBB, C, V ) )
                        #thisBook.addPriorityError( 50, C, V, _("Aborted load because of decoding issue") )
                        #break # WHY does it fail???
                    if byteOffset+1 >= len(binary) + int(remainder14count/8) \
                    and bookRecordLocation+recordCount+1 < len(mainDBIndex): # Need to continue to the next record
                        #binary += myFile.read( 256 ) # These records are assumed here to be contiguous
                        binary += readRecord( bookRecordLocation+recordCount+1, myFile )
                        recordCount += 1
                        if debuggingThisModule:
                            print( "Record {}/{}".format( recordCount, numBookRecords ) )
                            print( "BibleWords {}/{}={}…".format( byteOffset, len(binary), hexlify(binary[byteOffset:byteOffset+32]) ) )
                        #byteOffset = 0
                        #if j==0:
                            #assert binary[byteOffset:byteOffset+2] == b'\xFF\xFF'
                            #byteOffset = 2
                    if byteShiftedFlag:
                        #print( "offset", byteOffset, hexlify(binary[byteOffset:byteOffset+4]) )
                        ix, bytesUsed = get14( binary[byteOffset:byteOffset+2] )
                        byteOffset += bytesUsed
                        if ix >= 0x3FF0: ix = ix | 0xC000 # To get it into the original range
                    else: ix, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                    if debuggingThisModule: print( "  here bO was {} ix={:04x}={}".format( byteOffset-2, ix, ix ) )
                    if ix > len(words):
                        #print( "Got HUGE ix {:04x} {}/{}".format( ix, ix, len(words) ) )
                        #ix = ix | 0xC000 # To get it into the original range
                        #assert 0xFFFC <= ix <= 0xFFFF
                        if   ix == 0xFFFF: word = '<BOOK>'
                        elif ix == 0xFFFE: word = '<CHAPTER>'
                        elif ix == 0xFFFD: word = '<DESC>'
                        elif ix == 0xFFFC: word = '<VERSE>'
                        #elif ix == 0xFFF4: word = '<44444>'
                        else:
                            if debuggingThisModule:
                                print( "\n\n\nGot HUGE ix {:04x} {}/{} @ {}/{}".format( ix, ix, len(words), byteOffset, len(binary) ) )
                            word = '<UNKNOWN>'
                            if debuggingThisModule: halt
                            #if C==0: C = 1
                        #print( "{} {}:{} tC={} vC={} acc={} {!r}".format( BBB, C, V, j, verseCount, accumulatedTokensPerVerseList[verseCount], verse ) )
                    else:
                        if ix == 0: word = ''
                        else: word = words[ix-1]
                    if debuggingThisModule: print( "  {} {}:{} {}word={!r}".format( BBB, C, V, 'compressed ' if ix>numRegularWords else '', word ) )
                    for wordBit in word.split(): # Handle each part of combined words separately to ensure correct handling of each part
                        if wordBit.startswith( '<BOOK>' ):
                            #print( "\n<BOOK>" )
                            #if not word.startswith( '<BOOK>' ): print( repr(verse), '+', repr(word) ); halt
                            if verse: saveSegment( BBB, C, V, verse ); verse = ''
                            C = V = 0
                        elif wordBit.startswith( '<CHAPTER>' ):
                            #print( "\n<CHAPTER>" )
                            #if not word.startswith( '<CHAPTER>' ): print( repr(verse), '+', repr(word) ); halt
                            if verse: saveSegment( BBB, C, V, verse ); verse = ''
                            accumulatedVerseCount += verseCount
                            verseCount = 0
                            C += 1; V = 0
                        elif wordBit.startswith( '<DESC>' ):
                            if debuggingThisModule: print( "\n<DESC>" )
                            #if not word.startswith( '<DESC>' ): print( repr(verse), '+', repr(word) ); halt
                            if verse: saveSegment( BBB, C, V, verse ); verse = ''
                        elif wordBit.startswith( '<VERSE>' ):
                            #print( "\n<VERSE>" )
                            #if not word.startswith( '<VERSE>' ): print( repr(verse), '+', repr(word) ); halt
                            if C==0: C = 1; print( "Correct C to one!" )
                            if verse: saveSegment( BBB, C, V, verse ); verse = ''
                            if V==0: V = 1
                        elif wordBit.startswith( '<UNKNOWN>' ):
                            if debuggingThisModule: print( "\n<UNKNOWN>" )
                            if verse: saveSegment( BBB, C, V, verse ); verse = ''
                        verse += wordBit + separatorCharacter
                    #print( repr(word), repr(verse) )
                    #print( "{} {}:{} tC={} vC={} acc={} {!r}".format( BBB, C, V, j, verseCount, accumulatedTokensPerVerseList[verseCount], word ) )
                    maxCount = accumulatedTokensPerVerseList[verseCount+accumulatedVerseCount]
                    if C > 1: maxCount += accumulatedTokensPerChapterList[C-1]
                    #print( "cC={} vC={} mC={}".format( accumulatedVerseCount, verseCount, maxCount ) )
                    if j+1 >= maxCount:
                        if verse: saveSegment( BBB, C, V, verse ); verse = ''
                        verseCount += 1
                        V += 1
                    if 'throne of God and of the Lamb . In the midst of the street' in verse:
                        if BibleOrgSysGlobals.verbosityLevel > 1:
                            print( "Handle Rev 22:1-2 special case in KJV", repr(verse) )
                        logging.warning( "PalmDBBible: Handled special verse-split case for Rev 22:1-2" )
                        loadErrors.append( _("PalmDBBible: Handled special verse-split case for Rev 22:1-2") )
                        thisBook.addPriorityError( 10, C, V, _("Handled special verse-split case for Rev 22:1-2") )
                        bits = verse.split( '.', 1 )
                        saveSegment( BBB, C, V, bits[0]+'.' )
                        verse = bits[1]
                        #verseCount += 1
                        V += 1
                    #tokenCount += 1
                    #if len(verse)>200: print( repr(verse) ); halt
                #print( "verse", repr(verse[:100]) )
                #print( "Done", byteOffset, len(binary) )
                #assert byteOffset == len(binary)
                self.stashBook( thisBook )
            #if BibleOrgSysGlobals.debugFlag:
                #halt

        if loadErrors:
            self.errorDictionary['Load Errors'] = loadErrors

        self.doPostLoadProcessing()
    # end of PalmDBBible.load
# end of PalmDBBible class



def testPB( TUBfilename ):
    # Crudely demonstrate the PDB Bible class
    from BibleOrgSys.Reference import VerseReferences
    #TUBfolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/PalmBiblePlus/' ) # Must be the same as below
    TUBfolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PDBTest/' )

    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the PDB Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( TUBfolder, TUBfilename ) )
    ub = PalmDBBible( TUBfolder, TUBfilename )
    ub.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( ub ) # Just print a summary
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('NT','MAT','3','5'), ('NT','MAT','27','46'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(ub)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(ub)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(ub)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #print( svk, ob.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = ub.getVerseText( svk )
        except KeyError:
            verseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
# end of testPB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/PalmBiblePlus/' )
    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PDBTest/' )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = PalmDBBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "PDB TestA1", result1 )
        result2 = PalmDBBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "PDB TestA2", result2 )
        result3 = PalmDBBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "PDB TestA3", result3 )


    if 1: # specified modules
        single = ( 'HCSB', )
        good = ( 'kjv', 'HCSB', 'CEVUK', 'test', '1974_TB', '2013_AYT', '1985_BIS', 'web', )
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: single, good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPDB B{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testPB( testFilename )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testPB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPDB C{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testPB( someFolder )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of PalmDBBible.py
