#!/usr/bin/python3
#
# USXBible.py
#   Last modified: 2012-07-05 by RJH (also update versionString below)
#
# Module handling compilations of USX Bible books
#
# Copyright (C) 2012 Robert Hunt
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
Module for defining and manipulating complete or partial USX Bibles.
"""

progName = "USX Bible handler"
versionString = "0.02"


import os, logging, datetime
from gettext import gettext as _
from collections import OrderedDict

import Globals
from USXBibleBook import USXBibleBook
from InternalBible import InternalBible


class USXBible( InternalBible ):
    """
    Class to load and manipulate USX Bibles.

    """
    def __init__( self, name, logErrorsFlag ):
        """
        Create the internal USX Bible object.
        """
        self.objectType = "USX"
        self.objectNameString = "USX Bible object"
        InternalBible.__init__( self, name, logErrorsFlag ) # Initialise the base class
    # end of __init_


    def load( self, folder, encoding='utf-8', logErrors=True ):
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

        import USXFilenames

        if Globals.verbosityLevel > 1: print( _("USXBible: Loading {} from {}...").format( self.name, folder ) )
        self.sourceFolder = folder # Remember our folder

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( folder ):
            somepath = os.path.join( folder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: print( "ERROR: Not sure what '{}' is in {}!".format( somepath, folder ) )
        if foundFolders: print( "USXBible.load: Surprised to see subfolders in '{}': {}".format( folder, foundFolders ) )
        if not foundFiles:
            print( "USXBible.load: Couldn't find any files in '{}'".format( folder ) )
            return # No use continuing

        self.USXFilenamesObject = USXFilenames.USXFilenames( folder )

        if 0:
            # Attempt to load the metadata file
            ssfFilepathList = self.USXFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
            if len(ssfFilepathList) == 1: # Seems we found the right one
                self.ssfData = loadSSFData( ssfFilepathList[0] )

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        for BBB,filename in self.USXFilenamesObject.getConfirmedFilenames():
            UBB = USXBibleBook( self.logErrorsFlag )
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
            if Globals.verbosityLevel > 2: print( "USXBible.load: Didn't find any regularly named USX files in '{}'".format( folder ) )
            for thisFilename in foundFiles:
                # Look for BBB in the ID line (which should be the first line in a USX file)
                isUSX = False
                thisPath = os.path.join( folder, thisFilename )
                with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                    for line in possibleUSXFile:
                        if line.startswith( '\\id ' ):
                            USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                            if Globals.verbosityLevel > 2: print( "Have possible USX ID '{}'".format( USXId ) )
                            BBB = self.BibleBooksCodes.getBBBFromUSFM( USXId )
                            if Globals.verbosityLevel > 2: print( "BBB is '{}'".format( BBB ) )
                            isUSX = True
                        break # We only look at the first line
                if isUSX:
                    UBB = USXBibleBook( self.logErrorsFlag )
                    UBB.load( BBB, folder, thisFilename, encoding )
                    UBB.validateUSFM()
                    print( UBB )
                    self.books[BBB] = UBB
                    # Make up our book name dictionaries while we're at it
                    assumedBookNames = UBB.getAssumedBookNames()
                    for assumedBookName in assumedBookNames:
                        self.BBBToNameDict[BBB] = assumedBookName
                        assumedBookNameLower = assumedBookName.lower()
                        self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
            if self.books: print( "USXBible.load: Found {} irregularly named USX files".format( len(self.books) ) )
    # end of load
# end of class USXBible


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

    name, encoding, testFolder = "Matigsalug", "utf-8", "/mnt/Data/Work/VirtualBox_Shared_Folder/USXExports/Projects/MBTV/" # You can put your USX test folder here
    if os.access( testFolder, os.R_OK ):
        UB = USXBible( name, False ) # The second parameter is the logErrorsFlag
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
## End of USXBible.py
