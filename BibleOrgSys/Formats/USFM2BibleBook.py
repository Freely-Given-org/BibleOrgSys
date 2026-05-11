#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# USFM2BibleBook.py
#
# Module handling the importation of USFM2 Bible books
#
# Copyright (C) 2010-2020 Robert Hunt
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
Module for defining and manipulating USFM2 Bible books.

CHANGELOG:
    2023-10-13 Improved message about finding USFM3 markers (in USFM2 file)
"""
from pathlib import Path
import os
import logging

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.InputOutput.USFMFile import USFMFile
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.USFM2Markers import USFM2Markers, USFM3_ALL_NEW_MARKERS


LAST_MODIFIED_DATE = '2023-10-13' # by RJH
SHORT_PROGRAM_NAME = "USFM2BibleBook"
PROGRAM_NAME = "USFM2 Bible book handler"
PROGRAM_VERSION = '0.54'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


USFM2Markers = USFM2Markers().loadData()
sortedNLMarkers = None



class USFM2BibleBook( BibleBook ):
    """
    Class to load and manipulate a single USFM2 file / book.
    """

    def __init__( self, containerBibleObject:Bible, BBB:str ) -> None:
        """
        Create the USFM2 Bible book object.
        """
        BibleBook.__init__( self, containerBibleObject, BBB ) # Initialise the base class
        self.objectNameString = 'USFM2 Bible Book object'
        self.objectTypeString = 'USFM2'

        global sortedNLMarkers
        if sortedNLMarkers is None:
            sortedNLMarkers = sorted( USFM2Markers.get_newline_markers_list('Combined'), key=len, reverse=True )
    # end of USFM2BibleBook.__init__


    def load( self, filename, folder=None, encoding=None ):
        """
        Load the USFM2 Bible book from a file.

        Tries to combine physical lines into logical lines,
            i.e., so that all lines begin with a USFM2 paragraph marker.

        Uses the addLine function of the base class to save the lines.

        Note: the base class later on will try to break apart lines with a paragraph marker in the middle --
                we don't need to worry about that here.
        """

        def doaddLine( originalMarker, original_text ):
            """
            Check for newLine markers within the line (if so, break the line) and save the information in our database.

            Also convert ~ to a proper non-break space.
            """
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"doaddLine( {originalMarker!r}, {original_text!r} )" )
            marker, text = originalMarker, original_text.replace( '~', ' ' )
            if '\\' in text: # Check markers inside the lines
                markerList = USFM2Markers.get_marker_list_from_text( text )
                ix = 0
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
                    if insideMarker == '\\': # it's a free-standing backspace
                        loadErrors.append( f"{self.BBB} {C}:{V} Improper free-standing backspace character within line in \\{marker}: {text!r}" )
                        logging.error( f"Improper free-standing backspace character within line after {self.BBB} {C}:{V} in \\{marker}: {text!r}" ) # Only log the first error in the line
                        self.addPriorityError( 100, C, V, "Improper free-standing backspace character inside a line" )
                    elif USFM2Markers.is_newline_marker(insideMarker): # Need to split the line for everything else to work properly
                        if ix==0:
                            loadErrors.append( f"{self.BBB} {C}:{V} NewLine marker {marker!r} shouldn't appear within line in \\{insideMarker}: {text!r}" )
                            logging.error( f"NewLine marker {marker!r} shouldn't appear within line after {insideMarker} {self.BBB}:{C} in \\{V}: {text!r}" ) # Only log the first error in the line
                            self.addPriorityError( 96, C, V, f"NewLine marker \\{insideMarker} shouldn't be inside a line" )
                        thisText = text[ix:iMIndex].rstrip()
                        self.addLine( marker, thisText )
                        ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Did a split from {originalMarker}:{original_text!r} to {marker}:{thisText!r} leaving {insideMarker}:{text[ix:]!r}" )
                        marker = insideMarker # setup for the next line
                if ix != 0: # We must have separated multiple lines
                    text = text[ix:] # Get the final bit of the line
            self.addLine( marker, text ) # Call the function in the base class to save the line (or the remainder of the line if we split it above)
        # end of doaddLine


        # Main code for USFM2BibleBook.load()
        if encoding is None: encoding = 'utf-8'
        self.sourceFilename = filename
        self.sourceFolder = folder
        self.sourceFilepath = os.path.join( folder, filename ) if folder else filename
        loadErrors:list[str] = []

        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + f"Preloading {filename}…" )
        with open( self.sourceFilepath, 'rt', encoding=encoding) as f:
            try: completeText = f.read()
            except Exception: completeText = ''
        for marker in USFM3_ALL_NEW_MARKERS:
            count = completeText.count(f'\\{marker}')
            if count:
                loadErrors.append( f"Found {count} USFM3 '\\{marker}' markers in USFM2 file: {self.sourceFilename}" )
                logging.error( f"Found {count} USFM3 '\\{marker}' markers in USFM2 file: {self.sourceFilepath}" )
                self.addPriorityError( 88, 0, 0, f"Found {count:,} USFM3 '\\{marker}' markers in USFM2 file" )
        del completeText # Not required any more

        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + f"Loading {filename}…" )
        #self.BBB = BBB
        #self.isSingleChapterBook = bos_books_codes_py.is_single_chapter_book( BBB )
        originalBook = USFMFile()
        originalBook.read( self.sourceFilepath, encoding=encoding )

        # Do some important cleaning up before we save the data
        C, V = '-1', '-1' # So first/id line starts at -1:0
        lastMarker = lastText = ''
        loadErrors:list[str] = []
        for marker,text in originalBook.lines: # Always process a line behind in case we have to combine lines
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"After {self.BBB} {C}:{V} \\{marker} {text!r}" )

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "bits", text.split() )
                try: C = text.split()[0]
                except IndexError: # Seems we had a \c field that's just whitespace
                    loadErrors.append( f"{self.BBB} {C}:{V} Found {text!r} invalid chapter field" )
                    logging.critical( f"Found {text!r} invalid chapter field after {self.BBB} {C}:{V}" )
                    self.addPriorityError( 100, C, V, "Found invalid/empty chapter field in file" )
                V = '0'
            elif marker=='v' and text:
                newV = text.split()[0]
                if V=='0' and not ( newV=='1' or newV.startswith( '1-' ) ):
                    loadErrors.append( f"{self.BBB} {C}:{V} Expected v1 after chapter marker not {newV!r}" )
                    logging.error( f"Unexpected {newV!r} verse number immediately after chapter field after {self.BBB} {C}:{V}" )
                    self.addPriorityError( 100, C, V, "Got unexpected chapter number" )
                V = newV
                if C == '-1': C = '1' # Some single chapter books don't have an explicit chapter 1 marker
            elif C == '-1' and marker not in ('headers','intro'): V = str( int(V) + 1 )
            elif marker=='restore': continue # Ignore these lines completely

            # Now load the actual Bible book data
            if USFM2Markers.is_newline_marker( marker ):
                if lastMarker: doaddLine( lastMarker, lastText )
                lastMarker, lastText = marker, text
            elif USFM2Markers.isInternalMarker( marker ) \
            or marker.endswith('*') and USFM2Markers.isInternalMarker( marker[:-1] ): # the line begins with an internal marker -- append it to the previous line
                if text:
                    loadErrors.append( f"{self.BBB} {C}:{V} Found '\\{marker}' internal marker at beginning of line with text: {text!r}" )
                    logging.warning( f"Found '\\{marker}' internal marker after {self.BBB} {C}:{V} at beginning of line with text: {text!r}" )
                else: # no text
                    loadErrors.append( f"{self.BBB} {C}:{V} Found '\\{marker}' internal marker at beginning of line (with no text)" )
                    logging.warning( f"Found '\\{marker}' internal marker after {self.BBB} {C}:{V} at beginning of line (with no text)" )
                self.addPriorityError( 27, C, V, f"Found \\{marker} internal marker on new line in file" )
                if not lastText.endswith(' '): lastText += ' ' # Not always good to add a space, but it's their fault!
                lastText +=  '\\' + marker + ' ' + text
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{self.BBB} {C} {V} Appended {marker}:{lastMarker!r} to get combined line {text}:{lastText!r}" )
            elif USFM2Markers.isNoteMarker( marker ) \
            or marker.endswith('*') and USFM2Markers.isNoteMarker( marker[:-1] ): # the line begins with a note marker -- append it to the previous line
                if text:
                    loadErrors.append( f"{self.BBB} {C}:{V} Found '\\{marker}' note marker at beginning of line with text: {text!r}" )
                    logging.warning( f"Found '\\{marker}' note marker after {self.BBB} {C}:{V} at beginning of line with text: {text!r}" )
                else: # no text
                    loadErrors.append( f"{self.BBB} {C}:{V} Found '\\{marker}' note marker at beginning of line (with no text)" )
                    logging.warning( f"Found '\\{marker}' note marker after {self.BBB} {C}:{V} at beginning of line (with no text)" )
                self.addPriorityError( 26, C, V, f"Found \\{marker} note marker on new line in file" )
                if not lastText.endswith(' ') and marker!='f': lastText += ' ' # Not always good to add a space, but it's their fault! Don't do it for footnotes, though.
                lastText +=  '\\' + marker + ' ' + text
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{self.BBB} {C} {V} Appended {marker}:{lastMarker!r} to get combined line {text}:{lastText!r}" )
            else: # the line begins with an unknown marker
                if marker == 's5' and not text: # it's a Door43 translatable section marker
                    loadErrors.append( f"{self.BBB} {C}:{V} Removed '\\{marker}' Door43 custom marker at beginning of line (with no text)" )
                    logging.error( f"Removed '\\{marker}' Door43 custom marker after {self.BBB} {C}:{V} at beginning of line (with no text)" )
                    marker = '' # so it gets deleted
                elif marker and marker[0] == 'z': # it's a custom marker
                    if text:
                        loadErrors.append( f"{self.BBB} {C}:{V} Found '\\{marker}' unknown custom marker at beginning of line with text: {text!r}" )
                        logging.warning( f"Found '\\{marker}' unknown custom marker after {self.BBB} {C}:{V} at beginning of line with text: {text!r}" )
                    else: # no text
                        loadErrors.append( f"{self.BBB} {C}:{V} Found '\\{marker}' unknown custom marker at beginning of line (with no text)" )
                        logging.warning( f"Found '\\{marker}' unknown custom marker after {self.BBB} {C}:{V} at beginning of line (with no text)" )
                    self.addPriorityError( 80, C, V, f"Found \\{marker} unknown custom marker on new line in file" )
                else: # it's an unknown marker
                    if text:
                        loadErrors.append( f"{self.BBB} {C}:{V} Found '\\{marker}' unknown marker at beginning of line with text: {text!r}" )
                        logging.error( f"Found '\\{marker}' unknown marker after {self.BBB} {C}:{V} at beginning of line with text: {text!r}" )
                    else: # no text
                        loadErrors.append( f"{self.BBB} {C}:{V} Found '\\{marker}' unknown marker at beginning of line (with no text)" )
                        logging.error( f"Found '\\{marker}' unknown marker after {self.BBB} {C}:{V} at beginning of line (with no text)" )
                    self.addPriorityError( 100, C, V, f"Found \\{marker} unknown marker on new line in file" )
                    for tryMarker in sortedNLMarkers: # Try to do something intelligent here -- it might be just a missing space
                        if marker.startswith( tryMarker ): # Let's try changing it
                            if lastMarker: doaddLine( lastMarker, lastText )
                            #if marker=='s5' and not text:
                                ## Door43 projects use empty s5 fields as some kind of division markers
                                #lastMarker, lastText = 's', '---'
                            #else:
                            # Move the extra appendage to the marker into the actual text
                            lastMarker, lastText = tryMarker, marker[len(tryMarker):] + ' ' + text
                            if text:
                                loadErrors.append( f"{self.BBB} {C}:{V} Changed '\\{marker}' unknown marker to {text!r} at beginning of line: {tryMarker}" )
                                logging.warning( f"Changed '\\{marker}' unknown marker to {text!r} after {tryMarker} {self.BBB}:{C} at beginning of line: {V}" )
                            else:
                                loadErrors.append( f"{self.BBB} {C}:{V} Changed '\\{marker}' unknown marker to {tryMarker!r} at beginning of otherwise empty line" )
                                logging.warning( f"Changed '\\{marker}' unknown marker to {V!r} after {tryMarker} {self.BBB}:{C} at beginning of otherwise empty line" )
                            break
                    # Otherwise, don't bother processing this line -- it'll just cause more problems later on
        if lastMarker: doaddLine( lastMarker, lastText ) # Process the final line

        if not originalBook.lines: # There were no lines!!!
            loadErrors.append( f"{self.BBB} This USFM2 file was totally empty: {self.sourceFilename}" )
            logging.error( f"USFM2 file for {self.BBB} was totally empty: {self.sourceFilename}" )
            lastMarker, lastText = 'rem', 'This (USFM) file was completely empty' # Save something since we had a file at least

        if loadErrors: self.checkResultsDictionary['Load Errors'] = loadErrors
        #if debugging: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, self._rawLines ); halt
    # end of USFM2BibleBook.load
# end of class USFM2BibleBook



def briefDemo() -> None:
    """
    Demonstrate reading and processing some USFM2 Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    def demoFile( name, filename, folder, BBB ):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {BBB} from {filename}{f' from {folder}' if BibleOrgSysGlobals.verbosityLevel > 2 else ''}…" )
        UBB = USFM2BibleBook( name, BBB )
        UBB.load( filename, folder, encoding )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  ID is {UBB.getField( 'id' )!r}" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Header is {UBB.getField( 'h' )!r}" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Main titles are {UBB.getField( 'mt1' )!r} and {UBB.getField( 'mt2' )!r}" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UBB )
        UBB.validateMarkers()
        UBBVersification = UBB.getVersification()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBVersification )
        UBBAddedUnits = UBB.getAddedUnits()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBAddedUnits )
        discoveryDict = UBB._discover()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "discoveryDict", discoveryDict )
        UBB.checkBook()
        UBErrors = UBB.getCheckResults()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBErrors )
    # end of fullDemoFile


    from BibleOrgSys.InputOutput import USFMFilenames

    if 1: # Test individual files -- choose one of these or add your own
        name, encoding, testFolder, filename, BBB = "USFM2Test", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/'), '70-MATeng-amp.usfm', 'MAT' # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', Path( '/srv/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "06-JOS.usfm", "JOS" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', Path( '/srv/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "44-SIR.usfm", "SIR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/'), "MBT102SA.SCP", "SA2" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/'), "MBT15EZR.SCP", "EZR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/'), "MBT41MAT.SCP", "MAT" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/'), "MBT67REV.SCP", "REV" # You can put your test file here
        if os.access( testFolder, os.R_OK ):
            demoFile( name, filename, testFolder, BBB )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )

    if 1: # Test a whole folder full of files
        name, encoding, testFolder = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
        #name, encoding, testFolder = "WEB", 'utf-8', Path( '/srv/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/' ) # You can put your test folder here
        if os.access( testFolder, os.R_OK ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Scanning {name} from {testFolder}…" )
            fileList = USFMFilenames.USFMFilenames( testFolder ).getMaximumPossibleFilenameTuples()
            for BBB,filename in fileList:
                demoFile( name, filename, testFolder, BBB )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )
# end of USFM2BibleBook.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    def demoFile( name, filename, folder, BBB ):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {BBB} from {filename}{f' from {folder}' if BibleOrgSysGlobals.verbosityLevel > 2 else ''}…" )
        UBB = USFM2BibleBook( name, BBB )
        UBB.load( filename, folder, encoding )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  ID is {UBB.getField( 'id' )!r}" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Header is {UBB.getField( 'h' )!r}" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Main titles are {UBB.getField( 'mt1' )!r} and {UBB.getField( 'mt2' )!r}" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UBB )
        UBB.validateMarkers()
        UBBVersification = UBB.getVersification()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBVersification )
        UBBAddedUnits = UBB.getAddedUnits()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBAddedUnits )
        discoveryDict = UBB._discover()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "discoveryDict", discoveryDict )
        UBB.checkBook()
        UBErrors = UBB.getCheckResults()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBErrors )
    # end of fullDemoFile


    from BibleOrgSys.InputOutput import USFMFilenames

    if 1: # Test individual files -- choose one of these or add your own
        name, encoding, testFolder, filename, BBB = "USFM2Test", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/'), '70-MATeng-amp.usfm', 'MAT' # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', Path( '/srv/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "06-JOS.usfm", "JOS" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', Path( '/srv/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "44-SIR.usfm", "SIR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/'), "MBT102SA.SCP", "SA2" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/'), "MBT15EZR.SCP", "EZR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/'), "MBT41MAT.SCP", "MAT" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/'), "MBT67REV.SCP", "REV" # You can put your test file here
        if os.access( testFolder, os.R_OK ):
            demoFile( name, filename, testFolder, BBB )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )

    if 0: # Test a whole folder full of files
        name, encoding, testFolder = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
        #name, encoding, testFolder = "WEB", 'utf-8', Path( '/srv/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/' ) # You can put your test folder here
        if os.access( testFolder, os.R_OK ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Scanning {name} from {testFolder}…" )
            fileList = USFMFilenames.USFMFilenames( testFolder ).getMaximumPossibleFilenameTuples()
            for BBB,filename in fileList:
                demoFile( name, filename, testFolder, BBB )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )
# end of USFM2BibleBook.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USFM2BibleBook.py
