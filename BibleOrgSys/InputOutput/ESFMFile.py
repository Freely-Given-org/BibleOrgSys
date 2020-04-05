#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ESFMFile.py
#
# ESFM (Enhanced Standard Format Marker) data file reader
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
Module for reading UTF-8 ESFM (Enhanced Standard Format Marker) Bible file.

  ESFMFile: A "flat" text file, read line by line into a list.

  The ESFM and its data field are read into a 2-tuple and saved (in order) in the list.

  Raises an IOError error if file doesn't exist.
"""


from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-02-24' # by RJH
SHORT_PROGRAM_NAME = "ESFMFile"
PROGRAM_NAME = "ESFM File loader"
PROGRAM_VERSION = '0.87'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, sys

if __name__ == '__main__':
    import os.path
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.InputOutput.USFMFile import splitMarkerFromText



DUMMY_VALUE = 999999 # Some number bigger than the number of characters in a line



class ESFMFile:
    """
    Class holding a list of (non-blank) ESFM lines.
    Each line is a tuple consisting of (SFMMarker, SFMValue).
    """

    def __init__(self):
        self.lines = []
    # end of ESFMFile.__init__


    def __str__(self):
        """
        This method returns the string representation of a SFM lines object.

        @return: the name of a ESFM field object formatted as a string
        @rtype: string
        """
        result = "ESFM File Object"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        for line in self.lines:
            result += ('\n' if result else '') + str( line )
        return result
    # end of ESFMFile.__str__


    def read( self, esfm_filename, ignoreSFMs=None ):
        """Read a simple ESFM (Enhanced Standard Format Marker) file into a list of tuples.

        @param esfm_filename: The filename
        @type esfm_filename: string
        @param key: The SFM record marker (not including the backslash)
        @type encoding: string
        @rtype: list
        @return: list of lists containing the records
        """
        #print( "ESFMFile.read( {}, {}, {} )".format( repr(esfm_filename), repr(ignoreSFMs), repr(encoding) ) )

        # Check/handle parameters
        if ignoreSFMs is None: ignoreSFMs = ()

        lastLine, lineCount, result = '', 0, []
        with open( esfm_filename, encoding='utf-8' ) as ourFile: # Automatically closes the file when done
            try:
                for line in ourFile:
                    lineCount += 1
                    if lineCount==1 and line[0]==chr(65279): #U+FEFF or \ufeff
                        logging.info( "ESFMFile: Detected Unicode Byte Order Marker (BOM) in {}".format( esfm_filename ) )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    #print ( 'ESFM file line is "' + line + '"' )
                    #if line[0:2]=='\\_': continue # Just discard Toolbox header lines
                    if line[0]=='#': continue # Just discard comment lines

                    while line and line[0]==' ': line = line[1:] # Remove leading spaces
                    if line and line[0]!='\\': # Not a SFM line
                        if len(result)==0: # We don't have any SFM data lines yet
                            if BibleOrgSysGlobals.verbosityLevel > 2:
                                logging.error( "Non-ESFM line in " + esfm_filename + " -- line ignored at #" + str(lineCount) )
                            #print( "SFMFile.py: XXZXResult is", result, len(line) )
                            #for x in range(0, min(6,len(line))):
                                #print( x, "'" + str(ord(line[x])) + "'" )
                            #raise IOError('Oops: Line break on last line ??? not handled here "' + line + '"')
                        else: # Append this continuation line
                            if marker not in ignoreSFMs:
                                oldmarker, oldtext = result.pop()
                                #print ("Popped",oldmarker,oldtext)
                                #print ("Adding", line, "to", oldmarker, oldtext)
                                result.append( (oldmarker, oldtext+' '+line) )
                            continue

                    marker, text = splitMarkerFromText( line )
                    if marker not in ignoreSFMs:
                        result.append( (marker, text) )

            except UnicodeError as err:
                print( "Unicode error:", sys.exc_info()[0], err )
                logging.critical( "Invalid line in " + esfm_filename + " -- line ignored at #" + str(lineCount) )
                if lineCount > 1: print( 'Previous line was: ', lastLine )
                #print( line )
                #raise

            self.lines = result
    # end of ESFMFile.read
# end of class ESFMFile



def demo() -> None:
    """
    Demonstrate reading and processing some UTF-8 ESFM files.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    import os.path
    filepath = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MatigsalugDictionaryA.sfm' )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "Using {} as test file…".format( filepath ) )

    linesDB = ESFMFile()
    linesDB.read( filepath, ignoreSFMs=('mn','aMU','aMW','cu','cp') )
    print( len(linesDB.lines), 'lines read from file', filepath )
    for i, r in enumerate(linesDB.lines):
        print ( i, r)
        if i>9: break
    print ( '…\n',len(linesDB.lines)-1, linesDB.lines[-1], '\n') # Display the last record
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ESFMFile.py
