#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# EasyWorshipBible.py
#
# Module handling EasyWorship Bible files
#
# Copyright (C) 2015-2026 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module reading and loading EasyWorship Bible undocumented binary files.

Filenames usually end with .ewb and contain some header info
    including a table of book abbreviations with numbers of chapters and verses
    followed by compressed blobs of basic book data (no headings, footnotes, etc.)

Seems that some non-UTF8 versions can't be read yet. :(
"""
import logging
import os.path
from pathlib import Path
import struct
import zlib
from binascii import hexlify
import multiprocessing

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Internals.InternalBibleBook import BOS_CUSTOM_NESTING_MARKERS
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
import bos_books_codes_py


LAST_MODIFIED_DATE = '2026-02-27' # by RJH
SHORT_PROGRAM_NAME = "EasyWorshipBible"
PROGRAM_NAME = "EasyWorship Bible format handler"
PROGRAM_VERSION = '0.17'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


FILENAME_ENDING = '.EWB' # Must be UPPERCASE



def EasyWorshipBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for EasyWorship Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one EasyWorship Bible is found,
        returns the loaded EasyWorshipBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"EasyWorshipBibleFileCheck( {givenFolderName}, {strictCheck}, {autoLoad}, {autoLoadBooks} )" )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, (str,Path) )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( f"EasyWorshipBibleFileCheck: Given {givenFolderName!r} folder is unreadable" )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( f"EasyWorshipBibleFileCheck: Given {givenFolderName!r} path is not a folder" )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f" EasyWorshipBibleFileCheck: Looking for files in given {givenFolderName}" )
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
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "EasyWorshipBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = EasyWorshipBible( givenFolderName, foundFiles[0] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( f"EasyWorshipBibleFileCheck: {tryFolderName!r} subfolder is unreadable" )
            continue
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    EasyWorshipBibleFileCheck: Looking for files in {tryFolderName}" )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ): foundSubfolders.append( something )
                elif os.path.isfile( somepath ):
                    somethingUpper = something.upper()
                    if somethingUpper.endswith( FILENAME_ENDING ):
                        foundProjects.append( (tryFolderName,something) )
                        numFound += 1
        except PermissionError: pass # can't read folder, e.g., system folder
        #if foundFileCount >= len(compulsoryFiles):
            #foundProjects.append( tryFolderName )
            #numFound += 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "EasyWorshipBibleFileCheck foundProjects", numFound, foundProjects )
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

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Running createEasyWorshipBible…" )
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
        if not bos_books_codes_py.is_chapter_verse_book( BBB ):
            continue # Ignore these books
        pseudoESFMData = bookObject._processedLines

        textBuffer = ''
        vBridgeStartInt = vBridgeEndInt = None # For printing missing (bridged) verse numbers
        for entry in pseudoESFMData:
            marker, text = entry.getMarker(), entry.getCleanText()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, marker, text )
            if '¬' in marker or marker in BOS_CUSTOM_NESTING_MARKERS: continue # Just ignore added markers -- not needed here
            elif marker == 'c':
                C = int( text ) # Just so we get an error if we have something different
                V = lastVWritten = '0'
            elif marker == 'v':
                #V = text.replace( '–', '-' ).replace( '—', '-' ) # Replace endash, emdash with hyphen
                V = text
                for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                    ix = V.find( bridgeChar )
                    if ix != -1:
                        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createEasyWorshipBible: preparing for verse bridge in {BibleObject.abbreviation} at {BBB} {C}:{V}" )
                        # Remove verse bridges
                        vStart = V[:ix].replace( 'a', '' ).replace( 'b', '' ).replace( 'c', '' )
                        vEnd = V[ix+1:].replace( 'a', '' ).replace( 'b', '' ).replace( 'c', '' )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, repr(vStart), repr(vEnd) )
                        try: vBridgeStartInt, vBridgeEndInt = int( vStart ), int( vEnd )
                        except ValueError:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createEasyWorshipBible: bridge doesn't seem to be integers in {BBB} {C}:{V!r}" )
                            vBridgeStartInt = vBridgeEndInt = None # One of them isn't an integer
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', BBB, repr(vBridgeStartInt), repr(vBridgeEndInt) )
                        VBridgedText = V
                        V = vStart
                        break
            elif marker == 'v~':
                try:
                    if int(V) <= int(lastVWritten):
                        # TODO: Not sure what level the following should be? info/warning/error/critical ????
                        logging.warning( f'createEasyWorshipBible: Maybe duplicating {BBB} {C}:{V} after {lastVWritten} with {text}' )
                        #continue
                except ValueError: pass # had a verse bridge
                if vBridgeStartInt and vBridgeEndInt: # We had a verse bridge
                    if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createEasyWorshipBible: handling verse bridge in {BibleObject.abbreviation} at {BBB} {C}:{vBridgeStartInt}-{vBridgeEndInt}" )
                    if 1: # new code -- copies the bridged text to all verses
                        for vNum in range( vBridgeStartInt, vBridgeEndInt+1 ): # Fill in missing verse numbers
                            textBuffer += ('\r\n\r\n' if textBuffer else '') + f'{C}:{vNum} ({VBridgedText}) {text}'
                    else: # old code
                        textBuffer += ('\r\n\r\n' if textBuffer else '') + f'{C}:{vBridgeStartInt} ({vBridgeEndInt}) {text}'
                        for vNum in range( vBridgeStartInt+1, vBridgeEndInt+1 ): # Fill in missing verse numbers
                            textBuffer += f'\r\n\r\n{C}:{vNum} (-)'
                    lastVWritten = str( vBridgeEndInt )
                    vBridgeStartInt = vBridgeEndInt = None
                else:
                    textBuffer += ('\r\n\r\n' if textBuffer else '') + f'{C}:{V} {text}'
                    lastVWritten = V
            elif marker == 'p~':
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert textBuffer # This is a continued part of the verse -- failed with this bad source USFM:
                                        #     \c 1 \v 1 \p These events happened…
                textBuffer += f' {text}' # continuation of the same verse
            else:
                ignoredMarkers.add( marker )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, textBuffer )
        textBuffer = textBuffer \
                        .replace( '“', '"' ).replace( '”', '"' ) \
                        .replace( "‘", "'" ).replace( "’", "'" ) \
                        .replace( '–', '--' ).replace( '—', '--' )
        bookBytes = zlib.compress( textBuffer.encode( 'utf8' ), ZLIB_COMPRESSION_LEVEL )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, hexlify(bookBytes[:20]), bookBytes )
        assert bookBytes[0]==0x78 and bookBytes[1]==0xda # Zlib compression header
        appendage = b'QK\x03\x04' + struct.pack( '<I', len(textBuffer) ) + b'\x08\x00'
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "appendage", len(appendage), hexlify(appendage), appendage )
        assert len(appendage) == 10
        compressedDictionary[BBB] = bookBytes + appendage

    # Work out the "compressed" (osfuscated) module name
    #name = BibleObject.getAName()
    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'sn', repr(BibleObject.shortName) )
    #if len(name)>18:
        #if BibleObject.shortName: name = shortName
        #elif name.endswith( ' Version' ): name = name[:-8]
    #name = name.replace( ' ', '' )
    #if not name.startswith( 'ezFree' ): name = 'ezFree' + name
    name = 'ezFree' + ( BibleObject.abbreviation if BibleObject.abbreviation else 'UNK' )
    if len(name)>16: name = name[:16] # Shorten
    encodedNameBytes = zlib.compress( name.encode( 'utf8' ), ZLIB_COMPRESSION_LEVEL )
    if BibleOrgSysGlobals.debugFlag:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Name {name!r} went from {len(name)} to {len(encodedNameBytes)} bytes' )
    assert encodedNameBytes[0]==0x78 and encodedNameBytes[1]==0xda # Zlib compression header
    assert len(encodedNameBytes) <= 26

    filename = f'{BibleObject.abbreviation}{FILENAME_ENDING}'.lower()
    filepath = os.path.join( outputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, '  createEasyWorshipBible: ' + f"Writing {filepath!r}…" )
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
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(bookName) if bookName else '', bookName )
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
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "appendage", len(appendage), hexlify(appendage), appendage )
        assert len(appendage) == 6
        myFile.write( appendage )
        remainderCount = 18 + len(name) - len(encodedNameBytes) - 4 - len(appendage)
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "remainderCount", remainderCount )
        assert remainderCount == 0
        #myFile.write( b'\x00' * remainderCount )
        myFile.write( b'\x00\x00\x08\x00' ) # Not sure what this means
        #if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "At", myFile.tell(), 'want', startingBookAddress )
        assert myFile.tell() == startingBookAddress

        # Write the book info to the binary files
        for BBB in BOS.getBookList():
            if BBB in compressedDictionary:
                myFile.write( compressedDictionary[BBB] ) # Write zlib output
            else:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f'  Book {BBB} is not available for EasyWorship export' )

        # Write the end of file stuff
        myFile.write( b'\x18:\x00\x00\x00\x00\x00\x00ezwBible' )

    if ignoredMarkers:
        logging.info( f"createEasyWorshipBible: Ignored markers were {ignoredMarkers}" )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + f"WARNING: Ignored createEasyWorshipBible markers were {ignoredMarkers}" )

    # Now create a zipped version
    filepath = os.path.join( outputFolder, filename )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Zipping {filename} EWB file…" )
    zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
    zf.write( filepath, filename )
    zf.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  BibleWriter.createEasyWorshipBible finished successfully." )
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
    def __init__( self, sourceFolder, sourceFilename ) -> None:
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
            logging.critical( f"EasyWorshipBible: File {self.sourceFilepath!r} is unreadable" )

        global BOS
        if BOS is None: BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        assert FILENAME_ENDING in self.sourceFilename.upper()
        self.abbreviation = os.path.splitext( self.sourceFilename)[0] # Remove file extension
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.sourceFilename, self.abbreviation )
    # end of EasyWorshipBible.__init__


    def load( self ):
        """
        Load the compressed data file and import book objects.
        """
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nLoading {self.sourceFilepath}…" )
        with open( self.sourceFilepath, 'rb' ) as myFile: # Automatically closes the file when done
            fileBytes = myFile.read()
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {len(fileBytes):,} bytes read" )

        keep = {}
        index = 0

        # Block 1 is 32-bytes long and always the same for EW2009 Bibles
        #dPrint( 'Never', DEBUGGING_THIS_MODULE, 'introBlock', hexlify( fileBytes[index:index+32] ), fileBytes[index:index+32] )
        keep['introBlock'] = (index,fileBytes[index:index+32])
        hString = ''
        for j in range( 32 ):
            char8 = fileBytes[index+j]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, char8, repr(char8) )
            if char8 < 0x20: break
            hString += chr( char8 )
        #if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'hString', repr(hString), index )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert hString == 'EasyWorship Bible Text'
        introBlockb = fileBytes[index+j:index+32]
        #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'introBlockb', hexlify( introBlockb ), introBlockb )
        assert introBlockb == b'\x1a\x02<\x00\x00\x00\xe0\x00\x00\x00' # b'1a023c000000e0000000'
        # Skipped some (important?) binary here??? but it's the same for every module
        index += 32

        # Block 2 is 56-bytes long
        moduleNameBlock = fileBytes[index:index+56]
        keep['moduleNameBlock'] = (index,moduleNameBlock)
        #dPrint( 'Never', DEBUGGING_THIS_MODULE, 'moduleNameBlock', hexlify( moduleNameBlock ), moduleNameBlock )
        nString = ''
        for j in range( 32 ):
            char8 = fileBytes[index+j]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, char8, repr(char8) )
            if char8 < 0x20: break
            nString += chr( char8 )
        #if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'nString', repr(nString), index )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorshipBible.load: " + f"Setting module name to {self.name!r}" )
        self.name = nString
        #assert self.name # Not there for amp and gkm
        moduleNameBlockb = fileBytes[index+j:index+56]
        #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'moduleNameBlockb', len(moduleNameBlockb), hexlify( moduleNameBlockb ), moduleNameBlockb )
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
            blockName = f'bookInfoBlock-{bookNumber}'
            keep[blockName] = (index,bookInfoBlock)
            #dPrint( 'Never', DEBUGGING_THIS_MODULE, blockName, hexlify( bookInfoBlock ), bookInfoBlock )
            bookName = ''
            for j in range( 32 ):
                char8 = fileBytes[index+j]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, char8, repr(char8) )
                if char8 < 0x20: break # bookName seems quite optional -- maybe the English ones are assumed if empty???
                bookName += chr( char8 )
            assert fileBytes[index+j:index+51] == b'\x00' * (51-j) # Skipped some zeroes here
            index += 51
            if bookName and bookName[-1] == '.': bookName = bookName[:-1] # Remove final period
            #dPrint( 'Info', DEBUGGING_THIS_MODULE, 'bookName', repr(bookName) )
            numChapters = fileBytes[index]
            numVerses = []
            for j in range( numChapters ):
                numVerses.append( fileBytes[index+j+1] )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "here1", 157-j-2, hexlify(fileBytes[index+j+2:index+157]), fileBytes[index+j+2:index+157] )
            if self.abbreviation != 'fn1938': # Why does this fail???
                assert fileBytes[index+j+2:index+157] == b'\x00' * (157-j-2) # Skipped some zeroes here
            index += 157
            #if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f' {numVerses!r} numChapters={bookName} verses={numChapters}' )
            bookStart, = struct.unpack( "<I", fileBytes[index:index+4] )
            assert fileBytes[index+4:index+8] == b'\x00' * 4 # Skipped some zeroes here
            index += 8
            #if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    bookStart is at {bookStart:,}' )
            bookLength, = struct.unpack( "<I", fileBytes[index:index+4] )
            assert fileBytes[index+4:index+8] == b'\x00' * 4 # Skipped some zeroes here
            index += 8
            #if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    {bookNumber} bookLength is {bookLength:,} which goes to {bookStart+bookLength:,}' )
            bookBytes = fileBytes[bookStart:bookStart+bookLength] # Looking ahead into the file
            rawBooks.append( (bookName, numChapters, numVerses, bookStart, bookLength, bookBytes) )
            if bookLength == 0: # e.g., gkm Philippians (book number 50)
                logging.critical( f"Booknumber {bookNumber} is empty in {self.abbreviation}" )
            else:
                #if DEBUGGING_THIS_MODULE:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"cHeader1 for {self.abbreviation}: {bookBytes[0]}={hexlify(bookBytes[0:1])} {bookBytes[1]}={hexlify(bookBytes[1:2])}" )
                assert bookBytes[0]==0x78 and bookBytes[1]==0xda # Zlib compression header (for compression levels 7-9)
        assert index == 14872 # 32 + 56 + 224*66

        workNameBlock = fileBytes[index:index+30] # 30 here is just a maximum, not fixed
        keep['workNameBlock'] = (index,workNameBlock) # This block starts with a length, then a work name, e.g., ezFreeASV
        #if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'workNameBlock', index, hexlify(workNameBlock), workNameBlock )
        length3, = struct.unpack( "<I", fileBytes[index:index+4] )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "length3", length3 ) # Seems to include the compressed string plus six more bytes
        keep['length3'] = (index,length3)
        if length3:
            bookInfoBlock = fileBytes[index+4:index+4+length3-4-6]
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"cHeader2 for {self.abbreviation}: {bookInfoBlock[0]}={hexlify(bookInfoBlock[0:1])} {bookInfoBlock[1]}={hexlify(bookInfoBlock[1:2])}" )
            assert bookInfoBlock[0]==0x78 and bookInfoBlock[1]==0xda # Zlib compression header (for compression levels 7-9)
            byteResult = zlib.decompress( bookInfoBlock )
            #rewriteResult1 = zlib.compress( byteResult, 9 )
            #byteResult1 = zlib.decompress( rewriteResult1 )
            #compressor = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=15, memLevel=8, strategy=zlib.Z_DEFAULT_STRATEGY )
            #rewriteResult2 = compressor.compress( byteResult )
            #rewriteResult2 += compressor.flush()
            #byteResult2 = zlib.decompress( rewriteResult2 )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "rewrite1 {} {} {}\n         {} {} {}\n         {} {} {}\n      to {} {}\n      to {} {}\n      to {} {}" \
                        #.format( len(bookInfoBlock), hexlify(bookInfoBlock), bookInfoBlock,
                                 #len(rewriteResult1), hexlify(rewriteResult1), rewriteResult1,
                                 #len(rewriteResult2), hexlify(rewriteResult2), rewriteResult2,
                                 #len(byteResult), byteResult,
                                 #len(byteResult1), byteResult1,
                                 #len(byteResult2), byteResult2 ) )
            textResult = byteResult.decode( 'utf8' )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Block4: Got {len(textResult)} chars {textResult!r} from {length3} bytes" )
            assert textResult.startswith('ezFree') or textResult.startswith('ezPaid')
            keep['workName'] = (index+4,textResult)
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorshipBible.load: " + f"Setting module work name to {textResult!r}" )
            if self.name: self.workName = textResult
            else: # Should rarely happen
                self.name = self.workName = textResult
            workNameAppendage = fileBytes[index+4+length3-6-4:index+4+length3-4]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "workNameAppendage", len(workNameAppendage), hexlify(workNameAppendage), workNameAppendage )
            keep['workNameAppendage'] = (index+4+length3-6-4,workNameAppendage)
            assert workNameAppendage[:4] == b'QK\x03\x04'
            uncompressedNameLength, = struct.unpack( "<B", workNameAppendage[4:5] )
            assert workNameAppendage[5:] == b'\x00'
            assert len(textResult) == uncompressedNameLength
        keep['length3'] = (index,length3)
        index += length3
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.abbreviation, len(textResult), repr(textResult), 'length3', length3, len(textResult)+18 )
        assert length3 == len(textResult) + 18

        bookDataStartIndex = rawBooks[0][3]
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "bookDataStartIndex", bookDataStartIndex )

        #if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'After known contents @ {index:,}', hexlify( fileBytes[index:index+60] ), fileBytes[index:index+60] )

        block0080 = fileBytes[index:bookDataStartIndex]
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "block0080", index, len(block0080), hexlify(block0080), block0080 )
        keep['block0080'] = (index,block0080)
        assert block0080 == b'\x00\x00\x08\x00' # b'00000800'
        index += len( block0080 )
        keep['bookDataStartIndex'] = (index,bookDataStartIndex)
        assert index == bookDataStartIndex # Should now be at the start of the first book (already fetched above)

        # Look at extra stuff right at the end of the file
        assert len(rawBooks) == 66
        index = bookStart + bookLength # of the last book
        endBytes = fileBytes[index:]
        #if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'endBytes', len(endBytes), hexlify(endBytes), endBytes )
        assert len(endBytes) == 16
        keep['endBytes'] = (index,endBytes)
        assert endBytes == b'\x18:\x00\x00\x00\x00\x00\x00ezwBible' # b'183a000000000000657a774269626c65'
        del fileBytes # Not needed any more

        # Now we have to decode the book text (compressed about 4x with zlib)
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"EWB loading books for {self.abbreviation}…" )
        for j, BBB in enumerate( BOS.getBookList() ):
            bookAbbrev, numChapters, numVerses, bookStart, bookLength, bookBytes = rawBooks[j]
            if bookLength == 0:
                assert not bookBytes
                logging.critical( f"   Skipped empty {BBB}" )
                continue
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f'  Decoding {BBB}…' )
            bookBytes, bookExtra = bookBytes[:-10], bookBytes[-10:]
            assert len(bookExtra) == 10
            keep[f'bookExtra-{j+1}'] = (-10,bookExtra)
            assert bookExtra[:4] == b'QK\x03\x04'
            uncompressedBookLength, = struct.unpack( "<I", bookExtra[4:8] )
            assert bookExtra[8:] == b'\x08\x00'
            byteResult = zlib.decompress( bookBytes )
            assert len(byteResult) == uncompressedBookLength
            try: textResult = byteResult.decode( 'utf8' )
            except UnicodeDecodeError:
                logging.critical( f"Unable to decode {self.abbreviation} {BBB} bookText -- maybe it's not utf-8???" )
                continue
            if DEBUGGING_THIS_MODULE:
                rewriteResult1 = zlib.compress( byteResult, 9 )
                byteResult1 = zlib.decompress( rewriteResult1 )
                if rewriteResult1 != bookBytes:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nbookBytes", len(bookBytes), hexlify(bookBytes) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nrewriteResult1", len(rewriteResult1), hexlify(rewriteResult1) )
                    halt
                if byteResult1 != byteResult:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(byteResult), hexlify(byteResult) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(byteResult1), hexlify(byteResult1) )
                    halt
            if '\t' in textResult:
                logging.warning( f"Replacing tab characters in {BBB} = {bookAbbrev}" )
                textResult = textResult.replace( '\t', ' ' )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, textResult )
            if BibleOrgSysGlobals.strictCheckingFlag: assert '  ' not in textResult

            thisBook = BibleBook( self, BBB )
            thisBook.objectNameString = 'EasyWorship Bible Book object'
            thisBook.objectTypeString = 'EasyWorship Bible'
            if bookAbbrev: thisBook.addLine( 'toc3', bookAbbrev )

            C, V = '-1', '-1' # So first/id line starts at -1:0
            for line in textResult.split( '\r\n' ):
                if not line: continue # skip blank lines
                #if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Processing {self.abbreviation} {BBB} line: {line!r}' )
                assert line[0].isdigit()
                assert ':' in line[:4]
                CV,verseText = line.split( ' ', 1 )
                newC,newV = CV.split( ':' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, newC, V, repr(verseText) )
                if newC != C:
                    if self.abbreviation=='hcsb' and BBB in ('SA2',): # Handle a bad bug -- chapter 24 has verses out of order
                        logging.critical( f"Skipping error for out-of-order chapters in {BBB}!" )
                    else: assert int(newC) > int(C)
                    C, V = newC, '0'
                    thisBook.addLine( 'c', C )
                if self.abbreviation=='TB' and BBB=='JOL': # Handle a bug -- chapter 3 repeats
                    if int(newV) < int(V): break
                elif self.abbreviation=='drv' and BBB in ('GEN','EXO','NUM',): # Handle a bug -- Gen 18:1&12, Exo 28:42&43 out of order
                    logging.critical( f"Skipping error for out-of-order verses in {self.abbreviation} {BBB}" )
                elif self.abbreviation=='rsv' and BBB in ('EXO','HAG',): # Handle a bug -- chapter 22 has verses out of order
                    logging.critical( f"Skipping error for out-of-order verses in {self.abbreviation} {BBB}" )
                elif self.abbreviation=='gnt' and BBB in ('ISA','ZEC','MRK',): # Handle a bug -- chapter 38 has verses out of order
                    logging.critical( f"Skipping error for out-of-order verses in {self.abbreviation} {BBB}" )
                elif self.abbreviation=='hcsb' and BBB in ('SA2',): # Handle a bug -- chapter 24 has verses out of order
                    logging.critical( f"Skipping error for out-of-order verses in {self.abbreviation} {BBB}" )
                elif self.abbreviation=='msg' and BBB in ('NUM','JDG','SA2','CH2','EZE','ACT',): # Handle a bug -- chapter 24 has verses out of order
                    logging.critical( f"Skipping error for out-of-order verses in {self.abbreviation} {BBB}" )
                else:
                    try: assert int(newV) > int(V)
                    except ValueError:
                        logging.critical( f"Something's not an integer around {self.abbreviation} {BBB} {C}:{V} {verseText}" )
                    except AssertionError:
                        logging.critical( f"Something's out of order around {self.abbreviation} {BBB} {C}:{V} {verseText}" )
                V = newV
                thisBook.addLine( 'v', V + ' ' + verseText )

            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "Saving", BBB )
            self.stashBook( thisBook )

        self.doPostLoadProcessing()
        return keep
    # end of EasyWorshipBible.load
# end of EasyWorshipBible class



def testEWB( TEWBfilename ):
    # Crudely demonstrate the EasyWorship Bible class
    from BibleOrgSys.Reference import VerseReferences
    BiblesFolderpath = Path( '/srv/Bibles/' )
    #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EasyWorshipBible/' )
    testFolder = BiblesFolderpath.joinpath( 'EasyWorship Bibles/' )

    #TEWBfolder = os.path.join( testFolder, TEWBfilename+'/' )
    TEWBfolder = testFolder
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Demonstrating the EasyWorship Bible class…" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Test folder is {TEWBfolder!r} {TEWBfilename!r}" )
    ewb = EasyWorshipBible( TEWBfolder, TEWBfilename )
    keep = ewb.load() # Load and process the file
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, ewb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        ewb.check()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
        ewbErrors = ewb.getCheckResults()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ewbErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##ewb.toDrupalBible()
        ewb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), ('OT','PSA','11','0'), \
                        ('OT','DAN','1','21'),
                        ('OT','ZEC','2','6'),('OT','ZEC','2','7'), # Bridged in MBTV and GNT
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(ewb)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(ewb)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(ewb)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, svk, ewb.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = ewb.getVerseText( svk )
            fullVerseText = ewb.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, shortText, verseText )
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'  {fullVerseText}' )
    return keep
# end of testEWB


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Brief Demo…" )

    BiblesFolderpath = Path( '/srv/Bibles/' )
    #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EasyWorshipBible/' )
    testFolder = BiblesFolderpath.joinpath( 'EasyWorship Bibles/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = EasyWorshipBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestA1", result1 )
        result2 = EasyWorshipBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestA2", result2 )
        result3 = EasyWorshipBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestA3", result3 )

        #testSubfolder = os.path.join( testFolder, 'AV/' )
        #result3 = EasyWorshipBibleFileCheck( testSubfolder )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestB1", result3 )
        #result4 = EasyWorshipBibleFileCheck( testSubfolder, autoLoad=True )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestB2", result4 )
        #result5 = EasyWorshipBibleFileCheck( testSubfolder, autoLoadBooks=True )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestB3", result5 )

    if 0: # specified module
        singleModule = 'mbtv.ewb'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nEasyWorship C/ Trying {singleModule}" )
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
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nEasyWorship D{j+1}/ Trying {testFilename}" )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            allModulesKeepDict[testFilename] = testEWB( testFilename )
            break
        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE and len(allModulesKeepDict)>1:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nCollected data blocks from all {len(allModulesKeepDict)} processed versions:" )
            # Print the various binary blocks together by block number
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, allModulesKeepDict['alb.ewb'].keys() )
            #for blockName in ('introBlock','moduleNameBlock','byte84','workNameBlock','workName','bookDataStartIndex','block0080','endBytes'):
            for blockName in allModulesKeepDict['alb.ewb'].keys():
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
                for moduleFilename,stuff in allModulesKeepDict.items():
                    if blockName in stuff:
                        index,result = stuff[blockName]
                        if blockName == 'introBlock': # Nice and consistent (32-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert index == 0
                            assert result == b'EasyWorship Bible Text\x1a\x02<\x00\x00\x00\xe0\x00\x00\x00'
                        elif blockName == 'moduleNameBlock':
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'byte84': # revision number or something ???
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                        #elif blockName in ('bookInfoBlock-1','bookInfoBlock-66'):
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'workNameBlock':
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'length3':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, result )
                            assert 26 <= result <= 32
                        elif blockName == 'workName':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), result, moduleFilename )
                            assert index == 14876
                        elif blockName == 'workNameAppendage': # Nice and consistent (4-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert len(result) == 6
                            assert result[:4] == b'QK\x03\x04'
                            assert result[4] < 16 # Length of uncompressed work name
                            assert result[5:] == b'\x00'
                        elif blockName == 'block0080': # Nice and consistent (4-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert result == b'\x00\x00\x08\x00'
                        elif blockName == 'bookDataStartIndex':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                            assert 14902 <= result <= 14908
                        elif blockName == 'endBytes': # Nice and consistent (16-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert result == b'\x18:\x00\x00\x00\x00\x00\x00ezwBible' # b'183a000000000000657a774269626c65'
                        elif not blockName.startswith( 'bookInfoBlock-' ) \
                        and not blockName.startswith( 'bookExtra-' ):
                            # Shouldn't get here
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            if DEBUGGING_THIS_MODULE: halt
# end of EasyWorshipBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Full Demo…" )

    BiblesFolderpath = Path( '/srv/Bibles/' )
    #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EasyWorshipBible/' )
    testFolder = BiblesFolderpath.joinpath( 'EasyWorship Bibles/' )


    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = EasyWorshipBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestA1", result1 )
        result2 = EasyWorshipBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestA2", result2 )
        result3 = EasyWorshipBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestA3", result3 )

        #testSubfolder = os.path.join( testFolder, 'AV/' )
        #result3 = EasyWorshipBibleFileCheck( testSubfolder )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestB1", result3 )
        #result4 = EasyWorshipBibleFileCheck( testSubfolder, autoLoad=True )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestB2", result4 )
        #result5 = EasyWorshipBibleFileCheck( testSubfolder, autoLoadBooks=True )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EasyWorship TestB3", result5 )

    if 0: # specified module
        singleModule = 'mbtv.ewb'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nEasyWorship C/ Trying {singleModule}" )
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
        for j, testFilename in enumerate( one ): # Choose one of the above: one, good, nonEnglish, bad, allModules
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nEasyWorship B{j+1}/ Trying {testFilename}" )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            allModulesKeepDict[testFilename] = testEWB( testFilename )
        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE and len(allModulesKeepDict)>1:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nCollected data blocks from all {len(allModulesKeepDict)} processed versions:" )
            # Print the various binary blocks together by block number
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, allModulesKeepDict['alb.ewb'].keys() )
            #for blockName in ('introBlock','moduleNameBlock','byte84','workNameBlock','workName','bookDataStartIndex','block0080','endBytes'):
            for blockName in allModulesKeepDict['alb.ewb'].keys():
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
                for moduleFilename,stuff in allModulesKeepDict.items():
                    if blockName in stuff:
                        index,result = stuff[blockName]
                        if blockName == 'introBlock': # Nice and consistent (32-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert index == 0
                            assert result == b'EasyWorship Bible Text\x1a\x02<\x00\x00\x00\xe0\x00\x00\x00'
                        elif blockName == 'moduleNameBlock':
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'byte84': # revision number or something ???
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                        #elif blockName in ('bookInfoBlock-1','bookInfoBlock-66'):
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'workNameBlock':
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'length3':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, result )
                            assert 26 <= result <= 32
                        elif blockName == 'workName':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), result, moduleFilename )
                            assert index == 14876
                        elif blockName == 'workNameAppendage': # Nice and consistent (4-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert len(result) == 6
                            assert result[:4] == b'QK\x03\x04'
                            assert result[4] < 16 # Length of uncompressed work name
                            assert result[5:] == b'\x00'
                        elif blockName == 'block0080': # Nice and consistent (4-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert result == b'\x00\x00\x08\x00'
                        elif blockName == 'bookDataStartIndex':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                            assert 14902 <= result <= 14908
                        elif blockName == 'endBytes': # Nice and consistent (16-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert result == b'\x18:\x00\x00\x00\x00\x00\x00ezwBible' # b'183a000000000000657a774269626c65'
                        elif not blockName.startswith( 'bookInfoBlock-' ) \
                        and not blockName.startswith( 'bookExtra-' ):
                            # Shouldn't get here
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            if DEBUGGING_THIS_MODULE: halt


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testEWB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nEasyWorship E{j+1}/ Trying {someFolder}" )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testEWB( someFolder )
# end of EasyWorshipBible.fullDemo

if __name__ == '__main__':
    multiprocessing.set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of EasyWorshipBible.py
