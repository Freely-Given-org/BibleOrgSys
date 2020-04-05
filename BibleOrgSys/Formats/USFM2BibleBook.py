#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFM2BibleBook.py
#
# Module handling the importation of USFM2 Bible books
#
# Copyright (C) 2010-2020 Robert Hunt
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
Module for defining and manipulating USFM2 Bible books.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-03-11' # by RJH
SHORT_PROGRAM_NAME = "USFM2BibleBook"
PROGRAM_NAME = "USFM2 Bible book handler"
PROGRAM_VERSION = '0.53'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.InputOutput.USFMFile import USFMFile
from BibleOrgSys.Bible import BibleBook

from BibleOrgSys.Reference.USFM2Markers import USFM2Markers, USFM3_ALL_NEW_MARKERS
USFM2Markers = USFM2Markers().loadData()


sortedNLMarkers = None



class USFM2BibleBook( BibleBook ):
    """
    Class to load and manipulate a single USFM2 file / book.
    """

    def __init__( self, containerBibleObject, BBB ):
        """
        Create the USFM2 Bible book object.
        """
        BibleBook.__init__( self, containerBibleObject, BBB ) # Initialise the base class
        self.objectNameString = 'USFM2 Bible Book object'
        self.objectTypeString = 'USFM2'

        global sortedNLMarkers
        if sortedNLMarkers is None:
            sortedNLMarkers = sorted( USFM2Markers.getNewlineMarkersList('Combined'), key=len, reverse=True )
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

        def doaddLine( originalMarker, originalText ):
            """
            Check for newLine markers within the line (if so, break the line) and save the information in our database.

            Also convert ~ to a proper non-break space.
            """
            #print( "doaddLine( {!r}, {!r} )".format( originalMarker, originalText ) )
            marker, text = originalMarker, originalText.replace( '~', ' ' )
            if '\\' in text: # Check markers inside the lines
                markerList = USFM2Markers.getMarkerListFromText( text )
                ix = 0
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
                    if insideMarker == '\\': # it's a free-standing backspace
                        loadErrors.append( _("{} {}:{} Improper free-standing backspace character within line in \\{}: {!r}").format( self.BBB, C, V, marker, text ) )
                        logging.error( _("Improper free-standing backspace character within line after {} {}:{} in \\{}: {!r}").format( self.BBB, C, V, marker, text ) ) # Only log the first error in the line
                        self.addPriorityError( 100, C, V, _("Improper free-standing backspace character inside a line") )
                    elif USFM2Markers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
                        if ix==0:
                            loadErrors.append( _("{} {}:{} NewLine marker {!r} shouldn't appear within line in \\{}: {!r}").format( self.BBB, C, V, insideMarker, marker, text ) )
                            logging.error( _("NewLine marker {!r} shouldn't appear within line after {} {}:{} in \\{}: {!r}").format( insideMarker, self.BBB, C, V, marker, text ) ) # Only log the first error in the line
                            self.addPriorityError( 96, C, V, _("NewLine marker \\{} shouldn't be inside a line").format( insideMarker ) )
                        thisText = text[ix:iMIndex].rstrip()
                        self.addLine( marker, thisText )
                        ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                        #print( "Did a split from {}:{!r} to {}:{!r} leaving {}:{!r}".format( originalMarker, originalText, marker, thisText, insideMarker, text[ix:] ) )
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
        loadErrors = []

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Preloading {}…").format( filename ) )
        with open( self.sourceFilepath, 'rt', encoding=encoding) as f:
            try: completeText = f.read()
            except Exception: completeText = ''
        for marker in USFM3_ALL_NEW_MARKERS:
            count = completeText.count(f'\\{marker}')
            if count:
                loadErrors.append( _("Found {} USFM3 '\\{}' markers in USFM2 file: {}").format( count, marker, self.sourceFilename ) )
                logging.error( _("Found {} USFM3 '\\{}' markers in USFM2 file: {}").format( count, marker, self.sourceFilepath ) )
                self.addPriorityError( 88, 0, 0, _("Found {} USFM3 '\\{}' markers in file").format( count, marker ) )
        del completeText # Not required any more

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Loading {}…").format( filename ) )
        #self.BBB = BBB
        #self.isSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( BBB )
        originalBook = USFMFile()
        originalBook.read( self.sourceFilepath, encoding=encoding )

        # Do some important cleaning up before we save the data
        C, V = '-1', '-1' # So first/id line starts at -1:0
        lastMarker = lastText = ''
        loadErrors = []
        for marker,text in originalBook.lines: # Always process a line behind in case we have to combine lines
            #print( "After {} {}:{} \\{} {!r}".format( self.BBB, C, V, marker, text ) )

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                #print( "bits", text.split() )
                try: C = text.split()[0]
                except IndexError: # Seems we had a \c field that's just whitespace
                    loadErrors.append( _("{} {}:{} Found {!r} invalid chapter field") \
                                        .format( self.BBB, C, V, text ) )
                    logging.critical( _("Found {!r} invalid chapter field after {} {}:{}") \
                                        .format( text, self.BBB, C, V ) )
                    self.addPriorityError( 100, C, V, _("Found invalid/empty chapter field in file") )
                V = '0'
            elif marker=='v' and text:
                newV = text.split()[0]
                if V=='0' and not ( newV=='1' or newV.startswith( '1-' ) ):
                    loadErrors.append( _("{} {}:{} Expected v1 after chapter marker not {!r}") \
                                        .format( self.BBB, C, V, newV ) )
                    logging.error( _("Unexpected {!r} verse number immediately after chapter field after {} {}:{}") \
                                        .format( newV, self.BBB, C, V ) )
                    self.addPriorityError( 100, C, V, _("Got unexpected chapter number") )
                V = newV
                if C == '-1': C = '1' # Some single chapter books don't have an explicit chapter 1 marker
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 )
            elif marker=='restore': continue # Ignore these lines completely

            # Now load the actual Bible book data
            if USFM2Markers.isNewlineMarker( marker ):
                if lastMarker: doaddLine( lastMarker, lastText )
                lastMarker, lastText = marker, text
            elif USFM2Markers.isInternalMarker( marker ) \
            or marker.endswith('*') and USFM2Markers.isInternalMarker( marker[:-1] ): # the line begins with an internal marker -- append it to the previous line
                if text:
                    loadErrors.append( _("{} {}:{} Found '\\{}' internal marker at beginning of line with text: {!r}").format( self.BBB, C, V, marker, text ) )
                    logging.warning( _("Found '\\{}' internal marker after {} {}:{} at beginning of line with text: {!r}").format( marker, self.BBB, C, V, text ) )
                else: # no text
                    loadErrors.append( _("{} {}:{} Found '\\{}' internal marker at beginning of line (with no text)").format( self.BBB, C, V, marker ) )
                    logging.warning( _("Found '\\{}' internal marker after {} {}:{} at beginning of line (with no text)").format( marker, self.BBB, C, V ) )
                self.addPriorityError( 27, C, V, _("Found \\{} internal marker on new line in file").format( marker ) )
                if not lastText.endswith(' '): lastText += ' ' # Not always good to add a space, but it's their fault!
                lastText +=  '\\' + marker + ' ' + text
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "{} {} {} Appended {}:{!r} to get combined line {}:{!r}".format( self.BBB, C, V, marker, text, lastMarker, lastText ) )
            elif USFM2Markers.isNoteMarker( marker ) \
            or marker.endswith('*') and USFM2Markers.isNoteMarker( marker[:-1] ): # the line begins with a note marker -- append it to the previous line
                if text:
                    loadErrors.append( _("{} {}:{} Found '\\{}' note marker at beginning of line with text: {!r}").format( self.BBB, C, V, marker, text ) )
                    logging.warning( _("Found '\\{}' note marker after {} {}:{} at beginning of line with text: {!r}").format( marker, self.BBB, C, V, text ) )
                else: # no text
                    loadErrors.append( _("{} {}:{} Found '\\{}' note marker at beginning of line (with no text)").format( self.BBB, C, V, marker ) )
                    logging.warning( _("Found '\\{}' note marker after {} {}:{} at beginning of line (with no text)").format( marker, self.BBB, C, V ) )
                self.addPriorityError( 26, C, V, _("Found \\{} note marker on new line in file").format( marker ) )
                if not lastText.endswith(' ') and marker!='f': lastText += ' ' # Not always good to add a space, but it's their fault! Don't do it for footnotes, though.
                lastText +=  '\\' + marker + ' ' + text
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "{} {} {} Appended {}:{!r} to get combined line {}:{!r}".format( self.BBB, C, V, marker, text, lastMarker, lastText ) )
            else: # the line begins with an unknown marker
                if marker == 's5' and not text: # it's a Door43 translatable section marker
                    loadErrors.append( _("{} {}:{} Removed '\\{}' Door43 custom marker at beginning of line (with no text)") \
                                        .format( self.BBB, C, V, marker ) )
                    logging.error( _("Removed '\\{}' Door43 custom marker after {} {}:{} at beginning of line (with no text)") \
                                        .format( marker, self.BBB, C, V ) )
                    marker = '' # so it gets deleted
                elif marker and marker[0] == 'z': # it's a custom marker
                    if text:
                        loadErrors.append( _("{} {}:{} Found '\\{}' unknown custom marker at beginning of line with text: {!r}") \
                                            .format( self.BBB, C, V, marker, text ) )
                        logging.warning( _("Found '\\{}' unknown custom marker after {} {}:{} at beginning of line with text: {!r}") \
                                            .format( marker, self.BBB, C, V, text ) )
                    else: # no text
                        loadErrors.append( _("{} {}:{} Found '\\{}' unknown custom marker at beginning of line (with no text)") \
                                            .format( self.BBB, C, V, marker ) )
                        logging.warning( _("Found '\\{}' unknown custom marker after {} {}:{} at beginning of line (with no text)") \
                                            .format( marker, self.BBB, C, V ) )
                    self.addPriorityError( 80, C, V, _("Found \\{} unknown custom marker on new line in file").format( marker ) )
                else: # it's an unknown marker
                    if text:
                        loadErrors.append( _("{} {}:{} Found '\\{}' unknown marker at beginning of line with text: {!r}") \
                                            .format( self.BBB, C, V, marker, text ) )
                        logging.error( _("Found '\\{}' unknown marker after {} {}:{} at beginning of line with text: {!r}") \
                                            .format( marker, self.BBB, C, V, text ) )
                    else: # no text
                        loadErrors.append( _("{} {}:{} Found '\\{}' unknown marker at beginning of line (with no text)") \
                                            .format( self.BBB, C, V, marker ) )
                        logging.error( _("Found '\\{}' unknown marker after {} {}:{} at beginning of line (with no text)") \
                                            .format( marker, self.BBB, C, V ) )
                    self.addPriorityError( 100, C, V, _("Found \\{} unknown marker on new line in file").format( marker ) )
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
                                loadErrors.append( _("{} {}:{} Changed '\\{}' unknown marker to {!r} at beginning of line: {}").format( self.BBB, C, V, marker, tryMarker, text ) )
                                logging.warning( _("Changed '\\{}' unknown marker to {!r} after {} {}:{} at beginning of line: {}").format( marker, tryMarker, self.BBB, C, V, text ) )
                            else:
                                loadErrors.append( _("{} {}:{} Changed '\\{}' unknown marker to {!r} at beginning of otherwise empty line").format( self.BBB, C, V, marker, tryMarker ) )
                                logging.warning( _("Changed '\\{}' unknown marker to {!r} after {} {}:{} at beginning of otherwise empty line").format( marker, tryMarker, self.BBB, C, V ) )
                            break
                    # Otherwise, don't bother processing this line -- it'll just cause more problems later on
        if lastMarker: doaddLine( lastMarker, lastText ) # Process the final line

        if not originalBook.lines: # There were no lines!!!
            loadErrors.append( _("{} This USFM2 file was totally empty: {}").format( self.BBB, self.sourceFilename ) )
            logging.error( _("USFM2 file for {} was totally empty: {}").format( self.BBB, self.sourceFilename ) )
            lastMarker, lastText = 'rem', 'This (USFM) file was completely empty' # Save something since we had a file at least

        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
        #if debugging: print( self._rawLines ); halt
    # end of USFM2BibleBook.load
# end of class USFM2BibleBook



def demo() -> None:
    """
    Demonstrate reading and processing some USFM2 Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    def demoFile( name, filename, folder, BBB ):
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Loading {} from {}…").format( BBB, filename ) )
        UBB = USFM2BibleBook( name, BBB )
        UBB.load( filename, folder, encoding )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "  ID is {!r}".format( UBB.getField( 'id' ) ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Header is {!r}".format( UBB.getField( 'h' ) ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Main titles are {!r} and {!r}".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
        #if BibleOrgSysGlobals.verbosityLevel > 0: print( UBB )
        UBB.validateMarkers()
        UBBVersification = UBB.getVersification()
        if BibleOrgSysGlobals.verbosityLevel > 2: print( UBBVersification )
        UBBAddedUnits = UBB.getAddedUnits()
        if BibleOrgSysGlobals.verbosityLevel > 2: print( UBBAddedUnits )
        discoveryDict = UBB._discover()
        #print( "discoveryDict", discoveryDict )
        UBB.check()
        UBErrors = UBB.getErrors()
        if BibleOrgSysGlobals.verbosityLevel > 2: print( UBErrors )
    # end of demoFile


    from BibleOrgSys.InputOutput import USFMFilenames

    if 1: # Test individual files -- choose one of these or add your own
        name, encoding, testFolder, filename, BBB = "USFM2Test", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/'), '70-MATeng-amp.usfm', 'MAT' # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "06-JOS.usfm", "JOS" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "44-SIR.usfm", "SIR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT102SA.SCP", "SA2" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT15EZR.SCP", "EZR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT41MAT.SCP", "MAT" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT67REV.SCP", "REV" # You can put your test file here
        if os.access( testFolder, os.R_OK ):
            demoFile( name, filename, testFolder, BBB )
        else: print( _("Sorry, test folder '{}' doesn't exist on this computer.").format( testFolder ) )

    if 0: # Test a whole folder full of files
        name, encoding, testFolder = "Matigsalug", 'utf-8', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
        #name, encoding, testFolder = "WEB", 'utf-8', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/' ) # You can put your test folder here
        if os.access( testFolder, os.R_OK ):
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Scanning {} from {}…").format( name, testFolder ) )
            fileList = USFMFilenames.USFMFilenames( testFolder ).getMaximumPossibleFilenameTuples()
            for BBB,filename in fileList:
                demoFile( name, filename, testFolder, BBB )
        else: print( _("Sorry, test folder '{}' doesn't exist on this computer.").format( testFolder ) )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USFM2BibleBook.py
