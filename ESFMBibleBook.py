#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ESFMBibleBook.py
#   Last modified: 2014-07-05 by RJH (also update ProgVersion below)
#
# Module handling the ESFM markers for Bible books
#
# Copyright (C) 2010-2014 Robert Hunt
# Author: Robert Hunt <robert316@users.sourceforge.net>
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
Module for defining and manipulating ESFM Bible books.
"""

ProgName = "ESFM Bible book handler"
ProgVersion = "0.41"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import os, logging
from gettext import gettext as _

import Globals
from InternalBibleInternals import ALL_WORD_PUNCT_CHARS
from USFMFile import USFMFile
from Bible import BibleBook


sortedNLMarkers = sorted( Globals.USFMMarkers.getNewlineMarkersList('Combined'), key=len, reverse=True )



class ESFMBibleBook( BibleBook ):
    """
    Class to load and manipulate a single ESFM file / book.
    """

    def __init__( self, name, BBB ):
        """
        Create the ESFM Bible book object.
        """
        BibleBook.__init__( self, name, BBB ) # Initialise the base class
        self.objectNameString = "ESFM Bible Book object"
        self.objectTypeString = "ESFM"
    # end of __init__


    def load( self, filename, folder=None ):
        """
        Load the ESFM Bible book from a file.

        Tries to combine physical lines into logical lines,
            i.e., so that all lines begin with a ESFM paragraph marker.

        Uses the appendLine function of the base class to save the lines.

        Note: the base class later on will try to break apart lines with a paragraph marker in the middle --
                we don't need to worry about that here.
        """

        def ESFMPreprocessing( BBB, C, V, originalText ):
            """
            Converts ESFM tagging to pseudo-USFM codes for easier handling later on.

            Parameters:
                BBB, C, V parameters are just for use in error messages
                originalText is the text line from the file

            Returns:
                A string replacement to use instead of originalText

            Converts:
                XXX=PYYYY to \dic PXXX=YYY\dic*
                    e.g., "{the three lepers}=PMat6Lepers" to "the three lepers\dic Pthe_three_lepers=Mat6lepers\dic*"
                i.e, braces and equal signs are removed from the text
                    and the information is placed in a \dic field.

            Note: This DOESN'T remove the underline/underscore characters used to join translated words
                which were one word in the original, e.g., went_down
            """
            text = ''

            if 1: # TEMP: remove ESFM tags
                inTag = False
                for char in originalText:
                    if inTag:
                        if char in ' _' or char in ALL_WORD_PUNCT_CHARS: # Note: A forward slash is permitted
                            inTag = False
                            text += char
                    else: # not in tag
                        if char == '=': inTag = True; continue
                        text += char
                text = text.replace('{','').replace('}','').replace('_(',' ').replace(')_',' ').replace('_',' ')
                #if text != originalText:
                    #print( "from: {}".format( repr(originalText) ) )
                    #print( " got: {}".format( repr(text) ) )

            return text
        # end of ESFMBibleBook.ESFMPreprocessing


        def doAppendLine( originalMarker, originalText ):
            """
            Check for newLine markers within the line (if so, break the line) and save the information in our database.

            Also convert ~ to a proper non-break space.
            """
            #print( "doAppendLine( {}, {} )".format( repr(originalMarker), repr(originalText) ) )
            marker, text = originalMarker, originalText.replace( '~', ' ' )
            if '\\' in text: # Check markers inside the lines
                markerList = Globals.USFMMarkers.getMarkerListFromText( text )
                ix = 0
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
                    if insideMarker == '\\': # it's a free-standing backspace
                        loadErrors.append( _("{} {}:{} Improper free-standing backspace character within line in \\{}: '{}'").format( self.BBB, C, V, marker, text ) )
                        logging.error( _("Improper free-standing backspace character within line after {} {}:{} in \\{}: '{}'").format( self.BBB, C, V, marker, text ) ) # Only log the first error in the line
                        self.addPriorityError( 100, C, V, _("Improper free-standing backspace character inside a line") )
                    elif Globals.USFMMarkers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
                        if ix==0:
                            loadErrors.append( _("{} {}:{} NewLine marker '{}' shouldn't appear within line in \\{}: '{}'").format( self.BBB, C, V, insideMarker, marker, text ) )
                            logging.error( _("NewLine marker '{}' shouldn't appear within line after {} {}:{} in \\{}: '{}'").format( insideMarker, self.BBB, C, V, marker, text ) ) # Only log the first error in the line
                            self.addPriorityError( 96, C, V, _("NewLine marker \\{} shouldn't be inside a line").format( insideMarker ) )
                        thisText = text[ix:iMIndex].rstrip()
                        self.appendLine( marker, thisText )
                        ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                        #print( "Did a split from {}:'{}' to {}:'{}' leaving {}:'{}'".format( originalMarker, originalText, marker, thisText, insideMarker, text[ix:] ) )
                        marker = insideMarker # setup for the next line
                if ix != 0: # We must have separated multiple lines
                    text = text[ix:] # Get the final bit of the line
            self.appendLine( marker, text ) # Call the function in the base class to save the line (or the remainder of the line if we split it above)
        # end of ESFMBibleBook.doAppendLine


        if Globals.verbosityLevel > 2: print( "  " + _("Loading {}...").format( filename ) )
        #self.BBB = BBB
        #self.isSingleChapterBook = Globals.BibleBooksCodes.isSingleChapterBook( BBB )
        self.sourceFilename = filename
        self.sourceFolder = folder
        self.sourceFilepath = os.path.join( folder, filename ) if folder else filename
        originalBook = USFMFile()
        originalBook.read( self.sourceFilepath, encoding='utf-8' )

        # Do some important cleaning up before we save the data
        C = V = '0'
        lastMarker = lastText = ''
        loadErrors = []
        for marker,originalText in originalBook.lines: # Always process a line behind in case we have to combine lines
            #print( "After {} {}:{} \\{} '{}'".format( BBB, C, V, marker, originalText ) )

            # Keep track of where we are for more helpful error messages
            if marker=='c' and originalText: C, V = originalText.split()[0], '0'
            elif marker=='v' and originalText:
                V = originalText.split()[0]
                if C == '0': C = '1' # Some single chapter books don't have an explicit chapter 1 marker
            elif marker=='restore': continue # Ignore these lines completely

            text = ESFMPreprocessing( self.BBB, C, V, originalText ) # Convert ESFM encoding to pseudo-USFM

            # Now load the actual Bible book data
            if Globals.USFMMarkers.isNewlineMarker( marker ):
                if lastMarker: doAppendLine( lastMarker, lastText )
                lastMarker, lastText = marker, text
            elif Globals.USFMMarkers.isInternalMarker( marker ) \
            or marker.endswith('*') and Globals.USFMMarkers.isInternalMarker( marker[:-1] ): # the line begins with an internal marker -- append it to the previous line
                if text:
                    loadErrors.append( _("{} {}:{} Found '\\{}' internal marker at beginning of line with text: {}").format( self.BBB, C, V, marker, text ) )
                    logging.warning( _("Found '\\{}' internal marker after {} {}:{} at beginning of line with text: {}").format( marker, self.BBB, C, V, text ) )
                else: # no text
                    loadErrors.append( _("{} {}:{} Found '\\{}' internal marker at beginning of line (with no text)").format( self.BBB, C, V, marker ) )
                    logging.warning( _("Found '\\{}' internal marker after {} {}:{} at beginning of line (with no text)").format( marker, self.BBB, C, V ) )
                self.addPriorityError( 27, C, V, _("Found \\{} internal marker on new line in file").format( marker ) )
                if not lastText.endswith(' '): lastText += ' ' # Not always good to add a space, but it's their fault!
                lastText +=  '\\' + marker + ' ' + text
                if Globals.verbosityLevel > 3: print( "{} {} {} Appended {}:'{}' to get combined line {}:'{}'".format( self.BBB, C, V, marker, text, lastMarker, lastText ) )
            elif Globals.USFMMarkers.isNoteMarker( marker ) \
            or marker.endswith('*') and Globals.USFMMarkers.isNoteMarker( marker[:-1] ): # the line begins with a note marker -- append it to the previous line
                if text:
                    loadErrors.append( _("{} {}:{} Found '\\{}' note marker at beginning of line with text: {}").format( self.BBB, C, V, marker, text ) )
                    logging.warning( _("Found '\\{}' note marker after {} {}:{} at beginning of line with text: {}").format( marker, self.BBB, C, V, text ) )
                else: # no text
                    loadErrors.append( _("{} {}:{} Found '\\{}' note marker at beginning of line (with no text)").format( self.BBB, C, V, marker ) )
                    logging.warning( _("Found '\\{}' note marker after {} {}:{} at beginning of line (with no text)").format( marker, self.BBB, C, V ) )
                self.addPriorityError( 26, C, V, _("Found \\{} note marker on new line in file").format( marker ) )
                if not lastText.endswith(' ') and marker!='f': lastText += ' ' # Not always good to add a space, but it's their fault! Don't do it for footnotes, though.
                lastText +=  '\\' + marker + ' ' + text
                if Globals.verbosityLevel > 3: print( "{} {} {} Appended {}:'{}' to get combined line {}:'{}'".format( self.BBB, C, V, marker, text, lastMarker, lastText ) )
            else: # the line begins with an unknown marker
                if text:
                    loadErrors.append( _("{} {}:{} Found '\\{}' unknown marker at beginning of line with text: {}").format( self.BBB, C, V, marker, text ) )
                    logging.error( _("Found '\\{}' unknown marker after {} {}:{} at beginning of line with text: {}").format( marker, self.BBB, C, V, text ) )
                else: # no text
                    loadErrors.append( _("{} {}:{} Found '\\{}' unknown marker at beginning of line (with no text").format( self.BBB, C, V, marker ) )
                    logging.error( _("Found '\\{}' unknown marker after {} {}:{} at beginning of line (with no text)").format( marker, self.BBB, C, V ) )
                self.addPriorityError( 100, C, V, _("Found \\{} unknown marker on new line in file").format( marker ) )
                for tryMarker in sortedNLMarkers: # Try to do something intelligent here -- it might be just a missing space
                    if marker.startswith( tryMarker ): # Let's try changing it
                        if lastMarker: doAppendLine( lastMarker, lastText )
                        lastMarker, lastText = tryMarker, marker[len(tryMarker):] + ' ' + text
                        loadErrors.append( _("{} {}:{} Changed '\\{}' unknown marker to '{}' at beginning of line: {}").format( self.BBB, C, V, marker, tryMarker, text ) )
                        logging.warning( _("Changed '\\{}' unknown marker to '{}' after {} {}:{} at beginning of line: {}").format( marker, tryMarker, self.BBB, C, V, text ) )
                        break
                # Otherwise, don't bother processing this line -- it'll just cause more problems later on
        if lastMarker: doAppendLine( lastMarker, lastText ) # Process the final line

        if not originalBook.lines: # There were no lines!!!
            loadErrors.append( _("{} This ESFM file was totally empty: {}").format( self.BBB, self.sourceFilename ) )
            logging.error( _("ESFM file for {} was totally empty: {}").format( self.BBB, self.sourceFilename ) )
            lastMarker, lastText = 'rem', 'This (ESFM) file was completely empty' # Save something since we had a file at least

        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
        #if debugging: print( self._rawLines ); halt
    # end of ESFMBibleBook.load
# end of class ESFMBibleBook



def demo():
    """
    Demonstrate reading and processing some ESFM Bible databases.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )


    def demoFile( name, filename, folder, BBB ):
        if Globals.verbosityLevel > 1: print( _("Loading {} from {}...").format( BBB, filename ) )
        UBB = ESFMBibleBook( name, BBB )
        UBB.load( filename, folder, encoding )
        if Globals.verbosityLevel > 1: print( "  ID is '{}'".format( UBB.getField( 'id' ) ) )
        if Globals.verbosityLevel > 1: print( "  Header is '{}'".format( UBB.getField( 'h' ) ) )
        if Globals.verbosityLevel > 1: print( "  Main titles are '{}' and '{}'".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
        #if Globals.verbosityLevel > 0: print( UBB )
        UBB.validateMarkers()
        UBBVersification = UBB.getVersification ()
        if Globals.verbosityLevel > 2: print( UBBVersification )
        UBBAddedUnits = UBB.getAddedUnits ()
        if Globals.verbosityLevel > 2: print( UBBAddedUnits )
        discoveryDict = {}
        UBB.discover( discoveryDict )
        #print( "discoveryDict", discoveryDict )
        UBB.check()
        UBErrors = UBB.getErrors()
        if Globals.verbosityLevel > 2: print( UBErrors )
    # end of demoFile


    import ESFMFilenames

    if 1: # Test individual files
        #name, encoding, testFolder, filename, BBB = "WEB", "utf-8", "../../../../../Data/Work/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/", "06-JOS.usfm", "JOS" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", "utf-8", "../../../../../Data/Work/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/", "44-SIR.usfm", "SIR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", "utf-8", "../../../../../Data/Work/Matigsalug/Bible/MBTV/", "MBT102SA.SCP", "SA2" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", "utf-8", "../../../../../Data/Work/Matigsalug/Bible/MBTV/", "MBT15EZR.SCP", "EZR" # You can put your test file here
        name, encoding, testFolder, filename, BBB = "Matigsalug", "utf-8", "../../../../../Data/Work/Matigsalug/Bible/MBTV/", "MBT41MAT.SCP", "MAT" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", "utf-8", "../../../../../Data/Work/Matigsalug/Bible/MBTV/", "MBT67REV.SCP", "REV" # You can put your test file here
        if os.access( testFolder, os.R_OK ):
            demoFile( name, filename, testFolder, BBB )
        else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

    if 1: # Test a whole folder full of files
        name, encoding, testFolder = "Matigsalug", "utf-8", "../../../../../Data/Work/Matigsalug/Bible/MBTV/" # You can put your test folder here
        #name, encoding, testFolder = "WEB", "utf-8", "../../../../../Data/Work/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/" # You can put your test folder here
        if os.access( testFolder, os.R_OK ):
            if Globals.verbosityLevel > 1: print( _("Scanning {} from {}...").format( name, testFolder ) )
            fileList = ESFMFilenames.ESFMFilenames( testFolder ).getMaximumPossibleFilenameTuples()
            for BBB,filename in fileList:
                demoFile( name, filename, testFolder, BBB )
        else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of ESFMBibleBook.py