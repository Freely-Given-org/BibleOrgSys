#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# EasyWorshipBible.py
#
# Module handling EasyWorship Bible files
#
# Copyright (C) 2015-2020 Robert Hunt
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
Module reading and loading EasyWorship Bible undocumented binary files.

Filenames usually end with .ewb and contain some header info
    including a table of book abbreviations with numbers of chapters and verses
    followed by compressed blobs of basic book data (no headings, footnotes, etc.)

Seems that some non-UTF8 versions can't be read yet. :(
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-04-07' # by RJH
SHORT_PROGRAM_NAME = "EasyWorshipBible"
PROGRAM_NAME = "EasyWorship Bible format handler"
PROGRAM_VERSION = '0.14'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os.path
import struct, zlib
from binascii import hexlify
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem



FILENAME_ENDING = '.EWB' # Must be UPPERCASE



def EasyWorshipBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for EasyWorship Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one EasyWorship Bible is found,
        returns the loaded EasyWorshipBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "EasyWorshipBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("EasyWorshipBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("EasyWorshipBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " EasyWorshipBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    numFound = foundFileCount = 0
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            if somethingUpper.endswith( FILENAME_ENDING ):
                foundFiles.append( something )
                numFound += 1
    #if foundFileCount >= len(compulsoryFiles):
        #numFound = 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "EasyWorshipBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = EasyWorshipBible( givenFolderName, foundFiles[0] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("EasyWorshipBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    EasyWorshipBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                if somethingUpper.endswith( FILENAME_ENDING ):
                    foundProjects.append( (tryFolderName,something) )
                    numFound += 1
        #if foundFileCount >= len(compulsoryFiles):
            #foundProjects.append( tryFolderName )
            #numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "EasyWorshipBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            oB = EasyWorshipBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
# end of EasyWorshipBibleFileCheck



def createEasyWorshipBible( BibleObject, outputFolder=None ):
    """
    Write the pseudo USFM out into the compressed EasyWorship format.

    Since we don't have a specification for the format,
        and since we don't know the meaning of all the binary pieces of the file,
        we can't be certain yet that this output will actually work. :-(
    """
    import zipfile

    # It seems 7-9 give the correct two header bytes
    ZLIB_COMPRESSION_LEVEL = 9 #  -1=default(=6), 0=none, 1=fastest…9=highest compression level

    if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running createEasyWorshipBible…" )
    if BibleOrgSysGlobals.debugFlag: assert BibleObject.books

    if not BibleObject.doneSetupGeneric: BibleObject.__setupWriter()
    if not outputFolder: outputFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_EasyWorshipBible_Export/' )
    if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

    # Set-up their Bible reference system
    BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

    ignoredMarkers = set()

    # Before we write the file, let's compress all our books
    # Books are written as C:V verseText with double-spaced lines
    compressedDictionary = {}
    for BBB,bookObject in BibleObject.books.items():
        if BBB in ('FRT','INT','BAK','OTH','GLS','XXA','XXB','XXC','XXD','XXE','XXF','XXG',): continue # Ignore these books
        pseudoESFMData = bookObject._processedLines

        textBuffer = ''
        vBridgeStartInt = vBridgeEndInt = None # For printing missing (bridged) verse numbers
        for entry in pseudoESFMData:
            marker, text = entry.getMarker(), entry.getCleanText()
            #print( BBB, marker, text )
            if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS: continue # Just ignore added markers -- not needed here
            elif marker == 'c':
                C = int( text ) # Just so we get an error if we have something different
                V = lastVWritten = '0'
            elif marker == 'v':
                #V = text.replace( '–', '-' ).replace( '—', '-' ) # Replace endash, emdash with hyphen
                V = text
                for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                    ix = V.find( bridgeChar )
                    if ix != -1:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
                            print( "createEasyWorshipBible: preparing for verse bridge in {} at {} {}:{}" \
                                        .format( BibleObject.abbreviation, BBB, C, V ) )
                        # Remove verse bridges
                        vStart = V[:ix].replace( 'a', '' ).replace( 'b', '' ).replace( 'c', '' )
                        vEnd = V[ix+1:].replace( 'a', '' ).replace( 'b', '' ).replace( 'c', '' )
                        #print( BBB, repr(vStart), repr(vEnd) )
                        try: vBridgeStartInt, vBridgeEndInt = int( vStart ), int( vEnd )
                        except ValueError:
                            print( "createEasyWorshipBible: bridge doesn't seem to be integers in {} {}:{!r}".format( BBB, C, V ) )
                            vBridgeStartInt = vBridgeEndInt = None # One of them isn't an integer
                        #print( ' ', BBB, repr(vBridgeStartInt), repr(vBridgeEndInt) )
                        VBridgedText = V
                        V = vStart
                        break
            elif marker == 'v~':
                try:
                    if int(V) <= int(lastVWritten):
                        # TODO: Not sure what level the following should be? info/warning/error/critical ????
                        logging.warning( 'createEasyWorshipBible: Maybe duplicating {} {}:{} after {} with {}'.format( BBB, C, V, lastVWritten, text ) )
                        #continue
                except ValueError: pass # had a verse bridge
                if vBridgeStartInt and vBridgeEndInt: # We had a verse bridge
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
                        print( "createEasyWorshipBible: handling verse bridge in {} at {} {}:{}-{}" \
                                    .format( BibleObject.abbreviation, BBB, C, vBridgeStartInt, vBridgeEndInt ) )
                    if 1: # new code -- copies the bridged text to all verses
                        for vNum in range( vBridgeStartInt, vBridgeEndInt+1 ): # Fill in missing verse numbers
                            textBuffer += ('\r\n\r\n' if textBuffer else '') + '{}:{} ({}) {}'.format( C, vNum, VBridgedText, text )
                    else: # old code
                        textBuffer += ('\r\n\r\n' if textBuffer else '') + '{}:{} ({}) {}'.format( C, vBridgeStartInt, vBridgeEndInt, text )
                        for vNum in range( vBridgeStartInt+1, vBridgeEndInt+1 ): # Fill in missing verse numbers
                            textBuffer += '\r\n\r\n{}:{} (-)'.format( C, vNum )
                    lastVWritten = str( vBridgeEndInt )
                    vBridgeStartInt = vBridgeEndInt = None
                else:
                    textBuffer += ('\r\n\r\n' if textBuffer else '') + '{}:{} {}'.format( C, V, text )
                    lastVWritten = V
            elif marker == 'p~':
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert textBuffer # This is a continued part of the verse -- failed with this bad source USFM:
                                        #     \c 1 \v 1 \p These events happened…
                textBuffer += ' {}'.format( text ) # continuation of the same verse
            else:
                ignoredMarkers.add( marker )
        #print( BBB, textBuffer )
        textBuffer = textBuffer \
                        .replace( '“', '"' ).replace( '”', '"' ) \
                        .replace( "‘", "'" ).replace( "’", "'" ) \
                        .replace( '–', '--' ).replace( '—', '--' )
        bookBytes = zlib.compress( textBuffer.encode( 'utf8' ), ZLIB_COMPRESSION_LEVEL )
        #print( BBB, hexlify(bookBytes[:20]), bookBytes )
        assert bookBytes[0]==0x78 and bookBytes[1]==0xda # Zlib compression header
        appendage = b'QK\x03\x04' + struct.pack( '<I', len(textBuffer) ) + b'\x08\x00'
        #print( "appendage", len(appendage), hexlify(appendage), appendage )
        assert len(appendage) == 10
        compressedDictionary[BBB] = bookBytes + appendage

    # Work out the "compressed" (osfuscated) module name
    #name = BibleObject.getAName()
    ##print( 'sn', repr(BibleObject.shortName) )
    #if len(name)>18:
        #if BibleObject.shortName: name = shortName
        #elif name.endswith( ' Version' ): name = name[:-8]
    #name = name.replace( ' ', '' )
    #if not name.startswith( 'ezFree' ): name = 'ezFree' + name
    name = 'ezFree' + ( BibleObject.abbreviation if BibleObject.abbreviation else 'UNK' )
    if len(name)>16: name = name[:16] # Shorten
    encodedNameBytes = zlib.compress( name.encode( 'utf8' ), ZLIB_COMPRESSION_LEVEL )
    if BibleOrgSysGlobals.debugFlag:
        print( 'Name {!r} went from {} to {} bytes'.format( name, len(name), len(encodedNameBytes) ) )
    assert encodedNameBytes[0]==0x78 and encodedNameBytes[1]==0xda # Zlib compression header
    assert len(encodedNameBytes) <= 26

    filename = '{}{}'.format( BibleObject.abbreviation, FILENAME_ENDING ).lower()
    filepath = os.path.join( outputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( '  createEasyWorshipBible: ' + _("Writing {!r}…").format( filepath ) )
    bookAddress = startingBookAddress = 14872 + len(name) + 18 + 4 # Name is something like ezFreeXXX
    vBridgeStartInt = vBridgeEndInt = None # For printing missing (bridged) verse numbers
    with open( filepath, 'wb' ) as myFile:
        assert myFile.tell() == 0
        # Write the header info to binary file
        myFile.write( b'EasyWorship Bible Text\x1a\x02<\x00\x00\x00\xe0\x00\x00\x00' )
        assert myFile.tell() == 32
        nameBytes = ( BibleObject.getAName() ).encode( 'utf8' )
        myFile.write( nameBytes + b'\x00' * (56 - len(nameBytes)) )
        assert myFile.tell() == 88 # 32 + 56

        # Write the numChapters,numVerses info along with the file position and length
        for BBB in BOS.getBookList():
            #bookName = BibleObject.getAssumedBookName( BBB )
            try: bookName = BibleObject.books[BBB].shortTOCName
            except (KeyError,AttributeError): bookName = None # KeyError if no BBB, AttributeError if no shortTOCName
            #print( len(bookName) if bookName else '', bookName )
            assert bookName is None or len(bookName) <= 51
            if bookName: bookNameBytes = bookName.encode( 'utf8' )
            else: bookNameBytes = b'' # Not compulsory -- will default to English
            myFile.write( bookNameBytes + b'\x00' * (51 - len(bookNameBytes)) )

            numVersesList = BOS.getNumVersesList( BBB )
            numChapters = len( numVersesList )
            myFile.write( struct.pack( 'B', numChapters ) )
            for verseCount in numVersesList: myFile.write( struct.pack( 'B', verseCount ) )
            myFile.write( b'\x00' * (157 - numChapters - 1) )

            try: bookBytes = compressedDictionary[BBB] # if it exists
            except KeyError: # Fill in missing books
                missingString = "1:1 Book not available\r\n\r\n"
                bookBytes = zlib.compress( missingString.encode( 'utf8' ), ZLIB_COMPRESSION_LEVEL )
                assert bookBytes[0]==0x78 and bookBytes[1]==0xda # Zlib compression header
                appendage = b'QK\x03\x04' + struct.pack( '<I', len(missingString) ) + b'\x08\x00'
                assert len(appendage) == 10
                bookBytes += appendage
                compressedDictionary[BBB] = bookBytes
            myFile.write( struct.pack( '<Q', bookAddress ) )
            myFile.write( struct.pack( '<Q', len(bookBytes) ) )
            bookAddress += len(bookBytes)
        assert myFile.tell() == 14872 # 32 + 56 + 224*66

        # Write the "compressed" (osfuscated) module name
        myFile.write( struct.pack( '<I', len(name) + 18 ) )
        assert myFile.tell() == 14876 # 32 + 56 + 224*66 + 4
        myFile.write( encodedNameBytes )

        appendage = b'QK\x03\x04' + struct.pack( 'B', len(name) ) + b'\x00'
        #print( "appendage", len(appendage), hexlify(appendage), appendage )
        assert len(appendage) == 6
        myFile.write( appendage )
        remainderCount = 18 + len(name) - len(encodedNameBytes) - 4 - len(appendage)
        #print( "remainderCount", remainderCount )
        assert remainderCount == 0
        #myFile.write( b'\x00' * remainderCount )
        myFile.write( b'\x00\x00\x08\x00' ) # Not sure what this means
        #if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            #print( "At", myFile.tell(), 'want', startingBookAddress )
        assert myFile.tell() == startingBookAddress

        # Write the book info to the binary files
        for BBB in BOS.getBookList():
            if BBB in compressedDictionary:
                myFile.write( compressedDictionary[BBB] ) # Write zlib output
            elif BibleOrgSysGlobals.verbosityLevel > 2:
                print( '  Book {} is not available for EasyWorship export'.format( BBB ) )

        # Write the end of file stuff
        myFile.write( b'\x18:\x00\x00\x00\x00\x00\x00ezwBible' )

    if ignoredMarkers:
        logging.info( "createEasyWorshipBible: Ignored markers were {}".format( ignoredMarkers ) )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  " + _("WARNING: Ignored createEasyWorshipBible markers were {}").format( ignoredMarkers ) )

    # Now create a zipped version
    filepath = os.path.join( outputFolder, filename )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} EWB file…".format( filename ) )
    zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
    zf.write( filepath, filename )
    zf.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        print( "  BibleWriter.createEasyWorshipBible finished successfully." )
    return True
# end of createEasyWorshipBible



BOS = None

class EasyWorshipBible( Bible ):
    """
    Class for reading, validating, and converting EasyWorshipBible files.

    KJV OT has 23,145 verses = 5A69 in 39 = 27 books
        NT has  7,957 verses = 1F15 in 27 = 1B books
        Total  31,102 verses = 797E in 66 = 42 books
    """
    def __init__( self, sourceFolder, sourceFilename ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'EasyWorship Bible object'
        self.objectTypeString = 'EWB'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename = sourceFolder, sourceFilename
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("EasyWorshipBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        global BOS
        if BOS is None: BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        assert FILENAME_ENDING in self.sourceFilename.upper()
        self.abbreviation = os.path.splitext( self.sourceFilename)[0] # Remove file extension
        #print( self.sourceFilename, self.abbreviation )
    # end of EasyWorshipBible.__init__


    def load( self ):
        """
        Load the compressed data file and import book objects.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("\nLoading {}…").format( self.sourceFilepath ) )
        with open( self.sourceFilepath, 'rb' ) as myFile: # Automatically closes the file when done
            fileBytes = myFile.read()
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            print( "  {:,} bytes read".format( len(fileBytes) ) )

        keep = {}
        index = 0

        # Block 1 is 32-bytes long and always the same for EW2009 Bibles
        #if debuggingThisModule: print( 'introBlock', hexlify( fileBytes[index:index+32] ), fileBytes[index:index+32] )
        keep['introBlock'] = (index,fileBytes[index:index+32])
        hString = ''
        for j in range( 32 ):
            char8 = fileBytes[index+j]
            #print( char8, repr(char8) )
            if char8 < 0x20: break
            hString += chr( char8 )
        #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: print( 'hString', repr(hString), index )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert hString == 'EasyWorship Bible Text'
        introBlockb = fileBytes[index+j:index+32]
        #if BibleOrgSysGlobals.debugFlag: print( 'introBlockb', hexlify( introBlockb ), introBlockb )
        assert introBlockb == b'\x1a\x02<\x00\x00\x00\xe0\x00\x00\x00' # b'1a023c000000e0000000'
        # Skipped some (important?) binary here??? but it's the same for every module
        index += 32

        # Block 2 is 56-bytes long
        moduleNameBlock = fileBytes[index:index+56]
        keep['moduleNameBlock'] = (index,moduleNameBlock)
        #if debuggingThisModule: print( 'moduleNameBlock', hexlify( moduleNameBlock ), moduleNameBlock )
        nString = ''
        for j in range( 32 ):
            char8 = fileBytes[index+j]
            #print( char8, repr(char8) )
            if char8 < 0x20: break
            nString += chr( char8 )
        #if BibleOrgSysGlobals.debugFlag or debuggingThisModule: print( 'nString', repr(nString), index )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "EasyWorshipBible.load: " + _("Setting module name to {!r}").format( self.name ) )
        self.name = nString
        #assert self.name # Not there for amp and gkm
        moduleNameBlockb = fileBytes[index+j:index+56]
        #if BibleOrgSysGlobals.debugFlag: print( 'moduleNameBlockb', len(moduleNameBlockb), hexlify( moduleNameBlockb ), moduleNameBlockb )
        #assert moduleNameBlockb.endswith( b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00' ) # b'000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000'
        for ix in range( index+j, index+56 ): # Mostly zeroes remaining
            if ix == 84: # What does this mean???
                value = fileBytes[ix]
                assert value in (0,1,2,3,4,5) # bbe=0, alb=1, esv2=2, esv=3, asv=4 nasb=5 Revision number???
                keep['byte84'] = (index,value)
            else: assert fileBytes[ix] == 0
        index += 56

        # Get the optional booknames and the raw data for each book into a list
        rawBooks = []
        for bookNumber in range( 1, 66+1 ):
            bookInfoBlock = fileBytes[index:index+51]
            blockName = 'bookInfoBlock-{}'.format( bookNumber )
            keep[blockName] = (index,bookInfoBlock)
            #if debuggingThisModule: print( blockName, hexlify( bookInfoBlock ), bookInfoBlock )
            bookName = ''
            for j in range( 32 ):
                char8 = fileBytes[index+j]
                #print( char8, repr(char8) )
                if char8 < 0x20: break # bookName seems quite optional -- maybe the English ones are assumed if empty???
                bookName += chr( char8 )
            assert fileBytes[index+j:index+51] == b'\x00' * (51-j) # Skipped some zeroes here
            index += 51
            if bookName and bookName[-1] == '.': bookName = bookName[:-1] # Remove final period
            #if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                #print( 'bookName', repr(bookName) )
            numChapters = fileBytes[index]
            numVerses = []
            for j in range( numChapters ):
                numVerses.append( fileBytes[index+j+1] )
            #print( "here1", 157-j-2, hexlify(fileBytes[index+j+2:index+157]), fileBytes[index+j+2:index+157] )
            if self.abbreviation != 'fn1938': # Why does this fail???
                assert fileBytes[index+j+2:index+157] == b'\x00' * (157-j-2) # Skipped some zeroes here
            index += 157
            #if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                #print( ' {!r} numChapters={} verses={}'.format( bookName, numChapters, numVerses ) )
            bookStart, = struct.unpack( "<I", fileBytes[index:index+4] )
            assert fileBytes[index+4:index+8] == b'\x00' * 4 # Skipped some zeroes here
            index += 8
            #if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                #print( '    bookStart is at {:,}'.format( bookStart ) )
            bookLength, = struct.unpack( "<I", fileBytes[index:index+4] )
            assert fileBytes[index+4:index+8] == b'\x00' * 4 # Skipped some zeroes here
            index += 8
            #if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                #print( '    {} bookLength is {:,} which goes to {:,}'.format( bookNumber, bookLength, bookStart+bookLength ) )
            bookBytes = fileBytes[bookStart:bookStart+bookLength] # Looking ahead into the file
            rawBooks.append( (bookName, numChapters, numVerses, bookStart, bookLength, bookBytes) )
            if bookLength == 0: # e.g., gkm Philippians (book number 50)
                logging.critical( "Booknumber {} is empty in {}".format( bookNumber, self.abbreviation ) )
            else:
                #if debuggingThisModule:
                    #print( "cHeader1 for {}: {}={} {}={}".format( self.abbreviation, bookBytes[0], hexlify(bookBytes[0:1]), bookBytes[1], hexlify(bookBytes[1:2]) ) )
                assert bookBytes[0]==0x78 and bookBytes[1]==0xda # Zlib compression header (for compression levels 7-9)
        assert index == 14872 # 32 + 56 + 224*66

        workNameBlock = fileBytes[index:index+30] # 30 here is just a maximum, not fixed
        keep['workNameBlock'] = (index,workNameBlock) # This block starts with a length, then a work name, e.g., ezFreeASV
        #if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            #print( 'workNameBlock', index, hexlify(workNameBlock), workNameBlock )
        length3, = struct.unpack( "<I", fileBytes[index:index+4] )
        #print( "length3", length3 ) # Seems to include the compressed string plus six more bytes
        keep['length3'] = (index,length3)
        if length3:
            bookInfoBlock = fileBytes[index+4:index+4+length3-4-6]
            if debuggingThisModule:
                print( "cHeader2 for {}: {}={} {}={}".format( self.abbreviation, bookInfoBlock[0], hexlify(bookInfoBlock[0:1]), bookInfoBlock[1], hexlify(bookInfoBlock[1:2]) ) )
            assert bookInfoBlock[0]==0x78 and bookInfoBlock[1]==0xda # Zlib compression header (for compression levels 7-9)
            byteResult = zlib.decompress( bookInfoBlock )
            #rewriteResult1 = zlib.compress( byteResult, 9 )
            #byteResult1 = zlib.decompress( rewriteResult1 )
            #compressor = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=15, memLevel=8, strategy=zlib.Z_DEFAULT_STRATEGY )
            #rewriteResult2 = compressor.compress( byteResult )
            #rewriteResult2 += compressor.flush()
            #byteResult2 = zlib.decompress( rewriteResult2 )
            #print( "rewrite1 {} {} {}\n         {} {} {}\n         {} {} {}\n      to {} {}\n      to {} {}\n      to {} {}" \
                        #.format( len(bookInfoBlock), hexlify(bookInfoBlock), bookInfoBlock,
                                 #len(rewriteResult1), hexlify(rewriteResult1), rewriteResult1,
                                 #len(rewriteResult2), hexlify(rewriteResult2), rewriteResult2,
                                 #len(byteResult), byteResult,
                                 #len(byteResult1), byteResult1,
                                 #len(byteResult2), byteResult2 ) )
            textResult = byteResult.decode( 'utf8' )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "Block4: Got {} chars {!r} from {} bytes".format( len(textResult), textResult, length3 ) )
            assert textResult.startswith('ezFree') or textResult.startswith('ezPaid')
            keep['workName'] = (index+4,textResult)
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "EasyWorshipBible.load: " + _("Setting module work name to {!r}").format( textResult ) )
            if self.name: self.workName = textResult
            else: # Should rarely happen
                self.name = self.workName = textResult
            workNameAppendage = fileBytes[index+4+length3-6-4:index+4+length3-4]
            #print( "workNameAppendage", len(workNameAppendage), hexlify(workNameAppendage), workNameAppendage )
            keep['workNameAppendage'] = (index+4+length3-6-4,workNameAppendage)
            assert workNameAppendage[:4] == b'QK\x03\x04'
            uncompressedNameLength, = struct.unpack( "<B", workNameAppendage[4:5] )
            assert workNameAppendage[5:] == b'\x00'
            assert len(textResult) == uncompressedNameLength
        keep['length3'] = (index,length3)
        index += length3
        #print( self.abbreviation, len(textResult), repr(textResult), 'length3', length3, len(textResult)+18 )
        assert length3 == len(textResult) + 18

        bookDataStartIndex = rawBooks[0][3]
        #print( "bookDataStartIndex", bookDataStartIndex )

        #if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            #print( 'After known contents @ {:,}'.format( index ), hexlify( fileBytes[index:index+60] ), fileBytes[index:index+60] )

        block0080 = fileBytes[index:bookDataStartIndex]
        #print( "block0080", index, len(block0080), hexlify(block0080), block0080 )
        keep['block0080'] = (index,block0080)
        assert block0080 == b'\x00\x00\x08\x00' # b'00000800'
        index += len( block0080 )
        keep['bookDataStartIndex'] = (index,bookDataStartIndex)
        assert index == bookDataStartIndex # Should now be at the start of the first book (already fetched above)

        # Look at extra stuff right at the end of the file
        assert len(rawBooks) == 66
        index = bookStart + bookLength # of the last book
        endBytes = fileBytes[index:]
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( 'endBytes', len(endBytes), hexlify(endBytes), endBytes )
        assert len(endBytes) == 16
        keep['endBytes'] = (index,endBytes)
        assert endBytes == b'\x18:\x00\x00\x00\x00\x00\x00ezwBible' # b'183a000000000000657a774269626c65'
        del fileBytes # Not needed any more

        # Now we have to decode the book text (compressed about 4x with zlib)
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "EWB loading books for {}…".format( self.abbreviation ) )
        for j, BBB in enumerate( BOS.getBookList() ):
            bookAbbrev, numChapters, numVerses, bookStart, bookLength, bookBytes = rawBooks[j]
            if bookLength == 0:
                assert not bookBytes
                logging.critical( "   Skipped empty {}".format( BBB ) )
                continue
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  Decoding {}…'.format( BBB ) )
            bookBytes, bookExtra = bookBytes[:-10], bookBytes[-10:]
            assert len(bookExtra) == 10
            keep['bookExtra-{}'.format(j+1)] = (-10,bookExtra)
            assert bookExtra[:4] == b'QK\x03\x04'
            uncompressedBookLength, = struct.unpack( "<I", bookExtra[4:8] )
            assert bookExtra[8:] == b'\x08\x00'
            byteResult = zlib.decompress( bookBytes )
            assert len(byteResult) == uncompressedBookLength
            try: textResult = byteResult.decode( 'utf8' )
            except UnicodeDecodeError:
                logging.critical( "Unable to decode {} {} bookText -- maybe it's not utf-8???".format( self.abbreviation, BBB ) )
                continue
            if debuggingThisModule:
                rewriteResult1 = zlib.compress( byteResult, 9 )
                byteResult1 = zlib.decompress( rewriteResult1 )
                if rewriteResult1 != bookBytes:
                    print( "\nbookBytes", len(bookBytes), hexlify(bookBytes) )
                    print( "\nrewriteResult1", len(rewriteResult1), hexlify(rewriteResult1) )
                    halt
                if byteResult1 != byteResult:
                    print( len(byteResult), hexlify(byteResult) )
                    print( len(byteResult1), hexlify(byteResult1) )
                    halt
            if '\t' in textResult:
                logging.warning( "Replacing tab characters in {} = {}".format( BBB, bookAbbrev ) )
                textResult = textResult.replace( '\t', ' ' )
            #print( textResult )
            if BibleOrgSysGlobals.strictCheckingFlag: assert '  ' not in textResult

            thisBook = BibleBook( self, BBB )
            thisBook.objectNameString = 'EasyWorship Bible Book object'
            thisBook.objectTypeString = 'EasyWorship Bible'
            if bookAbbrev: thisBook.addLine( 'toc3', bookAbbrev )

            C, V = '-1', '-1' # So first/id line starts at -1:0
            for line in textResult.split( '\r\n' ):
                if not line: continue # skip blank lines
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    #print( 'Processing {} {} line: {!r}'.format( self.abbreviation, BBB, line ) )
                assert line[0].isdigit()
                assert ':' in line[:4]
                CV,verseText = line.split( ' ', 1 )
                newC,newV = CV.split( ':' )
                #print( newC, V, repr(verseText) )
                if newC != C:
                    if self.abbreviation=='hcsb' and BBB in ('SA2',): # Handle a bad bug -- chapter 24 has verses out of order
                        logging.critical( "Skipping error for out-of-order chapters in {}!".format( BBB ) )
                    else: assert int(newC) > int(C)
                    C, V = newC, '0'
                    thisBook.addLine( 'c', C )
                if self.abbreviation=='TB' and BBB=='JOL': # Handle a bug -- chapter 3 repeats
                    if int(newV) < int(V): break
                elif self.abbreviation=='drv' and BBB in ('GEN','EXO','NUM',): # Handle a bug -- Gen 18:1&12, Exo 28:42&43 out of order
                    logging.critical( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                elif self.abbreviation=='rsv' and BBB in ('EXO','HAG',): # Handle a bug -- chapter 22 has verses out of order
                    logging.critical( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                elif self.abbreviation=='gnt' and BBB in ('ISA','ZEC','MRK',): # Handle a bug -- chapter 38 has verses out of order
                    logging.critical( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                elif self.abbreviation=='hcsb' and BBB in ('SA2',): # Handle a bug -- chapter 24 has verses out of order
                    logging.critical( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                elif self.abbreviation=='msg' and BBB in ('NUM','JDG','SA2','CH2','EZE','ACT',): # Handle a bug -- chapter 24 has verses out of order
                    logging.critical( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                else:
                    try: assert int(newV) > int(V)
                    except ValueError:
                        logging.critical( "Something's not an integer around {} {} {}:{} {}".format( self.abbreviation, BBB, C, V, verseText ) )
                    except AssertionError:
                        logging.critical( "Something's out of order around {} {} {}:{} {}".format( self.abbreviation, BBB, C, V, verseText ) )
                V = newV
                thisBook.addLine( 'v', V + ' ' + verseText )

            if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", BBB )
            self.stashBook( thisBook )

        self.doPostLoadProcessing()
        return keep
    # end of EasyWorshipBible.load
# end of EasyWorshipBible class



def testEWB( TEWBfilename ):
    # Crudely demonstrate the EasyWorship Bible class
    from BibleOrgSys.Reference import VerseReferences
    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EasyWorshipBible/' )
    testFolder = BiblesFolderpath.joinpath( 'EasyWorship Bibles/' )

    #TEWBfolder = os.path.join( testFolder, TEWBfilename+'/' )
    TEWBfolder = testFolder
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the EasyWorship Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( TEWBfolder, TEWBfilename ) )
    ewb = EasyWorshipBible( TEWBfolder, TEWBfilename )
    keep = ewb.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( ewb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        ewb.check()
        #print( UsfmB.books['GEN']._processedLines[0:40] )
        ewbErrors = ewb.getErrors()
        # print( ewbErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##ewb.toDrupalBible()
        ewb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('OT','ZEC','2','6'),('OT','ZEC','2','7'), # Bridged in MBTV and GNT
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(ewb)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(ewb)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(ewb)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #print( svk, ewb.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = ewb.getVerseText( svk )
            fullVerseText = ewb.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( reference, shortText, verseText )
            if BibleOrgSysGlobals.debugFlag: print( '  {}'.format( fullVerseText ) )
    return keep
# end of testEWB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EasyWorshipBible/' )
    testFolder = BiblesFolderpath.joinpath( 'EasyWorship Bibles/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = EasyWorshipBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestA1", result1 )
        result2 = EasyWorshipBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestA2", result2 )
        result3 = EasyWorshipBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestA3", result3 )

        #testSubfolder = os.path.join( testFolder, 'AV/' )
        #result3 = EasyWorshipBibleFileCheck( testSubfolder )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestB1", result3 )
        #result4 = EasyWorshipBibleFileCheck( testSubfolder, autoLoad=True )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestB2", result4 )
        #result5 = EasyWorshipBibleFileCheck( testSubfolder, autoLoadBooks=True )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestB3", result5 )

    if 0: # specified module
        singleModule = 'mbtv.ewb'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nEasyWorship C/ Trying {}".format( singleModule ) )
        #myTestFolder = os.path.join( testFolder, singleModule+'/' )
        #testFilepath = os.path.join( testFolder, singleModule+'/', singleModule+'_utf8.txt' )
        testEWB( singleModule )

    if 1: # specified modules
        allModulesKeepDict = {}
        one = ( 'asv.ewb', )
        good = ( 'alb.ewb','amp.ewb','asv.ewb','bbe.ewb','cei.ewb','darby.ewb',
                'dn1933.ewb','dnb1930.ewb','drv.ewb',
                'esv.ewb','esv.ewb_0','esv.ewb_2',
                'fn1938.ewb', 'hcv.ewb','kar.ewb','kjv.ewb',
                'lsg.ewb','luth1545.ewb', 'maori.ewb', 'mbtv.ewb',
                'nasb.ewb','niv.ewb','nkjv.ewb', 'sv1917.ewb', 'TB.ewb',
                'vul.ewb', 'wb.ewb', 'ylt.ewb' )
        nonEnglish = (  )
        bad = ( 'aa.ewb','gkm.ewb','gnt.ewb','hcsb.ewb','msg.ewb','rsv.ewb' )
        allModules = good + bad
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad, allModules
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nEasyWorship D{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            allModulesKeepDict[testFilename] = testEWB( testFilename )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and len(allModulesKeepDict)>1:
            print( "\n\nCollected data blocks from all {} processed versions:".format( len(allModulesKeepDict) ) )
            # Print the various binary blocks together by block number
            #print( allModulesKeepDict['alb.ewb'].keys() )
            #for blockName in ('introBlock','moduleNameBlock','byte84','workNameBlock','workName','bookDataStartIndex','block0080','endBytes'):
            for blockName in allModulesKeepDict['alb.ewb'].keys():
                print()
                for moduleFilename,stuff in allModulesKeepDict.items():
                    if blockName in stuff:
                        index,result = stuff[blockName]
                        if blockName == 'introBlock': # Nice and consistent (32-bytes)
                            #print( blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert index == 0
                            assert result == b'EasyWorship Bible Text\x1a\x02<\x00\x00\x00\xe0\x00\x00\x00'
                        elif blockName == 'moduleNameBlock':
                            print( blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'byte84': # revision number or something ???
                            print( blockName, index, result, moduleFilename, )
                        #elif blockName in ('bookInfoBlock-1','bookInfoBlock-66'):
                            #print( blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'workNameBlock':
                            print( blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'length3':
                            #print( blockName, index, result, moduleFilename, )
                            #print( result )
                            assert 26 <= result <= 32
                        elif blockName == 'workName':
                            #print( blockName, index, len(result), result, moduleFilename )
                            assert index == 14876
                        elif blockName == 'workNameAppendage': # Nice and consistent (4-bytes)
                            #print( blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert len(result) == 6
                            assert result[:4] == b'QK\x03\x04'
                            assert result[4] < 16 # Length of uncompressed work name
                            assert result[5:] == b'\x00'
                        elif blockName == 'block0080': # Nice and consistent (4-bytes)
                            #print( blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert result == b'\x00\x00\x08\x00'
                        elif blockName == 'bookDataStartIndex':
                            #print( blockName, index, result, moduleFilename, )
                            assert 14902 <= result <= 14908
                        elif blockName == 'endBytes': # Nice and consistent (16-bytes)
                            #print( blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert result == b'\x18:\x00\x00\x00\x00\x00\x00ezwBible' # b'183a000000000000657a774269626c65'
                        elif not blockName.startswith( 'bookInfoBlock-' ) \
                        and not blockName.startswith( 'bookExtra-' ):
                            # Shouldn't get here
                            print( blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            if debuggingThisModule: halt


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
                results = pool.map( testEWB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nEasyWorship E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testEWB( someFolder )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of EasyWorshipBible.py
