#!/usr/bin/python3
#
# USFMBible.py
#   Last modified: 2012-06-29 by RJH (also update versionString below)
#
# Module handling compilations of USFM Bible books
#
# Copyright (C) 2010-2012 Robert Hunt
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
Module for defining and manipulating complete or partial USFM Bibles.
"""

progName = "USFM Bible handler"
versionString = "0.26"


import os, logging, datetime
from gettext import gettext as _
from collections import OrderedDict

import Globals
from USFMBibleBook import USFMBibleBook
from InternalBible import InternalBible


class USFMBible( InternalBible ):
    """
    Class to load and manipulate USFM Bibles.

    """
    def __init__( self, name, logErrorsFlag ):
        """
        Create the internal USFM Bible object.
        """
        InternalBible.__init__( self, name, logErrorsFlag ) # Initialise the base class
        self.objectType = "USFM"
        self.objectNameString = "USFM Bible object"
    # end of __init_


    def load( self, folder, encoding='utf-8' ):
        """
        Load the books.
        """
        def loadSSFData( ssfFilepath, encoding='utf-8' ):
            """Process the SSF data from the given filepath.
                Returns a dictionary."""
            if Globals.verbosityLevel > 2: print( _("Loading SSF data from '{}'").format( ssfFilepath ) )
            lastLine, lineCount, status, ssfData = '', 0, 0, {}
            with open( ssfFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        print( "      Detected UTF-16 Byte Order Marker" )
                        line = line[1:] # Remove the Byte Order Marker
                    if line[-1]=='\n': line = line[:-1] # Remove trailing newline character
                    line = line.strip() # Remove leading and trailing whitespace
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    processed = False
                    if status==0 and line=="<ScriptureText>":
                        status = 1
                        processed = True
                    elif status==1 and line=="</ScriptureText>":
                        status = 2
                        processed = True
                    elif status==1 and line[0]=='<' and line.endswith('/>'): # Handle a self-closing (empty) field
                        fieldname = line[1:-3] if line.endswith(' />') else line[1:-2] # Handle it with or without a space
                        if ' ' not in fieldname:
                            ssfData[fieldname] = ''
                            processed = True
                        elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                            bits = fieldname.split( None, 1 )
                            assert( len(bits)==2 )
                            fieldname = bits[0]
                            attributes = bits[1]
                            #print( "attributes = '{}'".format( attributes) )
                            ssfData[fieldname] = (contents, attributes)
                            processed = True
                    elif status==1 and line[0]=='<' and line[-1]=='>':
                        ix1 = line.index('>')
                        ix2 = line.index('</')
                        if ix1!=-1 and ix2!=-1 and ix2>ix1:
                            fieldname = line[1:ix1]
                            contents = line[ix1+1:ix2]
                            if ' ' not in fieldname and line[ix2+2:-1]==fieldname:
                                ssfData[fieldname] = contents
                                processed = True
                            elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                                bits = fieldname.split( None, 1 )
                                assert( len(bits)==2 )
                                fieldname = bits[0]
                                attributes = bits[1]
                                #print( "attributes = '{}'".format( attributes) )
                                if line[ix2+2:-1]==fieldname:
                                    ssfData[fieldname] = (contents, attributes)
                                    processed = True
                    if not processed: print( "ERROR: Unexpected '{}' line in SSF file".format( line ) )
            if Globals.verbosityLevel > 2:
                print( "  " + _("Got {} SSF entries:").format( len(ssfData) ) )
                if Globals.verbosityLevel > 3:
                    for key in sorted(ssfData):
                        print( "    {}: {}".format( key, ssfData[key] ) )
            return ssfData
        # end of loadSSFData

        import USFMFilenames

        if Globals.verbosityLevel > 1: print( _("USFMBible: Loading {} from {}...").format( self.name, folder ) )
        self.sourceFolder = folder # Remember our folder

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( folder ):
            somepath = os.path.join( folder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: print( "ERROR: Not sure what '{}' is in {}!".format( somepath, folder ) )
        if foundFolders: print( "USFMBible.load: Surprised to see subfolders in '{}': {}".format( folder, foundFolders ) )
        if not foundFiles:
            print( "USFMBible.load: Couldn't find any files in '{}'".format( folder ) )
            return # No use continuing

        self.USFMFilenamesObject = USFMFilenames.USFMFilenames( folder )

        # Attempt to load the SSF file
        ssfFilepathList = self.USFMFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
        if len(ssfFilepathList) == 1: # Seems we found the right one
            self.ssfData = loadSSFData( ssfFilepathList[0] )

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        for BBB,filename in self.USFMFilenamesObject.getConfirmedFilenames():
            UBB = USFMBibleBook( self.logErrorsFlag )
            UBB.load( BBB, folder, filename, encoding )
            UBB.validateUSFM()
            #print( UBB )
            self.books[BBB] = UBB
            # Make up our book name dictionaries while we're at it
            assumedBookNames = UBB.getAssumedBookNames()
            for assumedBookName in assumedBookNames:
                self.BBBToNameDict[BBB] = assumedBookName
                assumedBookNameLower = assumedBookName.lower()
                self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)

        if not self.books: # Didn't successfully load any regularly named books -- maybe the files have weird names??? -- try to be intelligent here
            if Globals.verbosityLevel > 2: print( "USFMBible.load: Didn't find any regularly named USFM files in '{}'".format( folder ) )
            #print( "\n", len(foundFiles), sorted(foundFiles) )
            for thisFilename in foundFiles:
                # Look for BBB in the ID line (which should be the first line in a USFM file)
                isUSFM = False
                thisPath = os.path.join( folder, thisFilename )
                with open( thisPath ) as possibleUSFMFile: # Automatically closes the file when done
                    for line in possibleUSFMFile:
                        if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                        if line.startswith( '\\id ' ):
                            USFMId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                            if Globals.verbosityLevel > 2: print( "Have possible USFM ID '{}'".format( USFMId ) )
                            BBB = self.BibleBooksCodes.getBBBFromUSFM( USFMId )
                            if Globals.verbosityLevel > 2: print( "BBB is '{}'".format( BBB ) )
                            isUSFM = True
                        elif line.startswith ( '\\' ):
                            print( "First line in {} in {} starts with a backslash but not an id line '{}'".format( thisFilename, folder, line ) )
                        elif not line:
                            print( "First line in {} in {} appears to be blank".format( thisFilename, folder ) )
                        break # We only look at the first line
                if isUSFM: # have an irregularly named file, but it appears to be USFM
                    UBB = USFMBibleBook( self.logErrorsFlag )
                    UBB.load( BBB, folder, thisFilename, encoding )
                    UBB.validateUSFM()
                    # print( UBB )
                    if BBB in self.books: print( "Oops, loadUSFMBible has already found '{}' in {}, now we have a duplicate in {}".format( BBB, self.books[BBB].sourceFilename, thisFilename ) )
                    self.books[BBB] = UBB
                    # Make up our book name dictionaries while we're at it
                    assumedBookNames = UBB.getAssumedBookNames()
                    for assumedBookName in assumedBookNames:
                        self.BBBToNameDict[BBB] = assumedBookName
                        assumedBookNameLower = assumedBookName.lower()
                        self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
                else: print( "{} doesn't seem to be a USFM Bible book in {}".format( thisFilename, folder ) )
            if self.books: print( "USFMBible.load: Found {} irregularly named USFM files".format( len(self.books) ) )
        #print( "\n", len(self.books), sorted(self.books) ); halt
    # end of load
# end of class USFMBible


def main():
    """
    Demonstrate reading and checking some Bible databases.
    """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    name, encoding, testFolder = "Matigsalug", "utf-8", "/mnt/Data/Matigsalug/Scripture/MBTV/" # You can put your test folder here
    if os.access( testFolder, os.R_OK ):
        UB = USFMBible( name, True ) # The second parameter is the logErrorsFlag -- set to True if you want to see errors at the terminal
        UB.load( testFolder, encoding )
        if Globals.verbosityLevel > 0: print( UB )
        UB.check()
        #UBErrors = UB.getErrors()
        # print( UBErrors )
        #print( UB.getVersification () )
        #print( UB.getAddedUnits () )
        #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
            ##print( "Looking for", ref )
            #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
    else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    #if Globals.commandLineOptions.export:
    #    wantErrorMessages = True
    #    if Globals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( progName, versionString ) )
    #       pass

if __name__ == '__main__':
    main()
## End of USFMBible.py
