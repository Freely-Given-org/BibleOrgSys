#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFMFile.py
#
# SFM (Standard Format Marker) data file reader
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
Module for reading UTF-8 USFM (Unified Standard Format Marker) Bible file.

  USFMFile: A "flat" text file, read line by line into a list.

  The USFM and its data field are read into a 2-tuple and saved (in order) in the list.

  Raises an IOError error if file doesn't exist.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-02-24' # by RJH
SHORT_PROGRAM_NAME = "USFMFile"
PROGRAM_NAME = "USFM File loader"
PROGRAM_VERSION = '0.86'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


from typing import Tuple, Optional
import sys
import logging

if __name__ == '__main__':
    import os.path
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals


DUMMY_VALUE = 999_999 # Some number bigger than the number of characters in a line



def splitMarkerFromText( line:str ) -> Tuple[Optional[str],str]:
    """
    Given a line of text (may be empty),
        returns a backslash marker and the text.

    If the marker is self-closing and without any internal fields, e.g., \\ts\\*
        the closure characters will be included with the marker.

    Returns None for the backslash marker if there isn't one.
    Returns an empty string for the text if there isn't any.
    """
    if not line: return None, ''
    if line[0] != '\\': return None, line # Not a USFM line

    # We have a line that starts with a backslash
    # The marker can end with a space, asterisk, or another marker
    lineAfterLeadingBackslash = line[1:]
    ixSP = lineAfterLeadingBackslash.find( ' ' )
    ixAS = lineAfterLeadingBackslash.find( '*' )
    ixBS = lineAfterLeadingBackslash.find( '\\' )
    if ixSP==-1: ixSP = DUMMY_VALUE
    if ixAS==-1: ixAS = DUMMY_VALUE
    if ixBS==-1: ixBS = DUMMY_VALUE
    ix = min( ixSP, ixAS, ixBS ) # Find the first terminating character (if any)

    if ix == DUMMY_VALUE: # The line is only the marker
        return lineAfterLeadingBackslash, ''
    else:
        if ix == ixBS: # Marker stops before a backslash
            if len(lineAfterLeadingBackslash) > ixBS+1 \
            and lineAfterLeadingBackslash[ixBS+1] == '*': # seems to be a self-closed marker
                marker = lineAfterLeadingBackslash[:ixBS+2]
                text = lineAfterLeadingBackslash[ixBS+2:]
            else: # Seems not self-closed
                marker = lineAfterLeadingBackslash[:ixBS]
                text = lineAfterLeadingBackslash[ixBS:]
        elif ix == ixAS: # Marker stops at an asterisk
            marker = lineAfterLeadingBackslash[:ixAS+1]
            text = lineAfterLeadingBackslash[ixAS+1:]
        elif ix == ixSP: # Marker stops before a space
            marker = lineAfterLeadingBackslash[:ixSP]
            text = lineAfterLeadingBackslash[ixSP+1:] # We drop the space completely
    return marker, text
# end if splitMarkerFromText



class USFMFile:
    """
    Class holding a list of (non-blank) USFM lines.
    Each line is a tuple consisting of (SFMMarker, SFMValue).
    """

    def __init__(self) -> None:
        self.lines = []
    # end of USFMFile.__init__


    def __str__(self) -> str:
        """
        This method returns the string representation of a SFM lines object.

        @return: the name of a USFM field object formatted as a string
        @rtype: string
        """
        result = "USFM File Object"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        for line in self.lines:
            result += ('\n' if result else '') + str( line )
        return result
    # end of USFMFile.__str__


    def read( self, USFMFilepath:str, ignoreSFMs:Optional[bool]=None, encoding:Optional[str]=None ) -> None:
        """
        Read a simple USFM (Unified Standard Format Marker) file into a list of tuples.

        @param USFMFilepath: The filename
        @type USFMFilepath: string
        @param key: The SFM record marker (not including the backslash)
        @type encoding: string
        @rtype: list

        Puts the result into self.lines
        """
        #print( "USFMFile.read( {!r}, {!r}, {!r} )".format( USFMFilepath, ignoreSFMs, encoding ) )

        # Check/handle parameters
        if ignoreSFMs is None: ignoreSFMs = ()
        if encoding is None: encoding = 'utf-8'

        lastLine, lineCount, result = '', 0, []
        with open( USFMFilepath, encoding=encoding ) as ourFile: # Automatically closes the file when done
            try:
                for line in ourFile:
                    lineCount += 1
                    if lineCount==1 and encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF
                        logging.info( "USFMFile: Detected Unicode Byte Order Marker (BOM) in {}".format( USFMFilepath ) )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    #print ( 'USFM file line is "' + line + '"' )
                    #if line[0:2]=='\\_': continue # Just discard Toolbox header lines
                    if line[0]=='#': continue # Just discard comment lines

                    if line[0]!='\\': # Not a SFM line
                        if len(result)==0: # We don't have any SFM data lines yet
                            if BibleOrgSysGlobals.verbosityLevel > 2:
                                logging.error( "Non-USFM line in " + USFMFilepath + " -- line ignored at #" + str(lineCount) )
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
                print( "USFMFile Unicode error:", sys.exc_info()[0], err )
                logging.critical( "Invalid line in " + USFMFilepath + " -- line ignored at #" + str(lineCount) )
                if lineCount > 1: print( 'Previous line was: ', lastLine )
                #print( line )
                #raise

            self.lines = result
    # end of USFMFile.read
# end of class USFMFile



def demo() -> None:
    """
    Demonstrate reading and processing some UTF-8 USFM files.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    import os.path
    filepath = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MatigsalugDictionaryA.sfm' )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "Using {} as test file…".format( filepath ) )

    linesDB = USFMFile()
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
# end of USFMFile.py
