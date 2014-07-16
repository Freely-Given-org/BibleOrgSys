#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMFile.py
#   Last modified: 2014-05-28 (also update ProgVersion below)
#
# SFM (Standard Format Marker) data file reader
#
# Copyright (C) 2010-2014 Robert Hunt
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

  USFMFile: A "flat" file, read line by line into a list.
            This could be any kind of SFM data.

  The USFM and its data field are read into a 2-tuple and saved (in order) in the list.

  Gives a fatal error (IOError) if file doesn't exist.
"""


ProgName = "USFM File loader"
ProgVersion = "0.83"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )


import logging, sys

import Globals



class USFMFile:
    """
    Class holding a list of (non-blank) USFM lines.
    Each line is a tuple consisting of (SFMMarker, SFMValue).
    """

    def __init__(self):
        self.lines = []

    def __str__(self):
        """
        This method returns the string representation of a SFM lines object.

        @return: the name of a USFM field object formatted as a string
        @rtype: string
        """
        result = "USFM File Object"
        if Globals.debugFlag or Globals.verbosityLevel>2: result += ' v' + ProgVersion
        for line in self.lines:
            result += ('\n' if result else '') + str( line )
        return result

    def read( self, sfm_filename, ignoreSFMs=None, encoding='utf-8' ):
        """Read a simple USFM (Unified Standard Format Marker) file into a list of tuples.

        @param sfm_filename: The filename
        @type sfm_filename: string
        @param key: The SFM record marker (not including the backslash)
        @type encoding: string
        @rtype: list
        @return: list of lists containing the records
        """
        #print( "USFMFile.read( {}, {}, {} )".format( repr(sfm_filename), repr(ignoreSFMs), repr(encoding) ) )

        # Check/handle parameters
        if ignoreSFMs is None: ignoreSFMs = ()

        dummyValue = 999999 # Some number bigger than the number of characters in a line
        lastLine, lineCount, result = '', 0, []
        with open( sfm_filename, encoding=encoding ) as ourFile: # Automatically closes the file when done
            try:
                for line in ourFile:
                    lineCount += 1
                    if lineCount==1 and encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF
                        logging.info( "USFMFile: Detected UTF-16 Byte Order Marker in {}".format( sfm_filename ) )
                        line = line[1:] # Remove the UTF-8 Byte Order Marker
                    if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    #print ( 'USFM file line is "' + line + '"' )
                    #if line[0:2]=='\\_': continue # Just discard Toolbox header lines
                    if line[0]=='#': continue # Just discard comment lines

                    if line[0]!='\\': # Not a SFM line
                        if len(result)==0: # We don't have any SFM data lines yet
                            if Globals.verbosityLevel > 2:
                                logging.error( "Non-USFM line in " + sfm_filename + " -- line ignored at #" + str(lineCount) )
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

                    lineAfterBackslash = line[1:]
                    si1 = lineAfterBackslash.find( ' ' )
                    si2 = lineAfterBackslash.find( '*' )
                    si3 = lineAfterBackslash.find( '\\' )
                    if si1==-1: si1 = dummyValue
                    if si2==-1: si2 = dummyValue
                    if si3==-1: si3 = dummyValue
                    si = min( si1, si2, si3 )

                    if si != dummyValue:
                        if si == si3: # Marker stops before a backslash
                            marker = lineAfterBackslash[:si3]
                            text = lineAfterBackslash[si3:]
                        elif si == si2: # Marker stops at an asterisk
                            marker = lineAfterBackslash[:si2+1]
                            text = lineAfterBackslash[si2+1:]
                        elif si == si1: # Marker stops before a space
                            marker = lineAfterBackslash[:si1]
                            text = lineAfterBackslash[si1+1:] # We drop the space completely
                    else: # The line is only the marker
                        marker = lineAfterBackslash
                        text = ''

                    #print( " ", repr(marker), repr(text) )
                    if marker not in ignoreSFMs:
                        result.append( (marker, text) )

            except UnicodeError as err:
                print( "Unicode error:", sys.exc_info()[0], err )
                logging.critical( "Invalid line in " + sfm_filename + " -- line ignored at #" + str(lineCount) )
                if lineCount > 1: print( 'Previous line was: ', lastLine )
                #print( line )
                #raise

            self.lines = result
    # end of USFMFile.read
# end of class USFMFile



def demo():
    """
    Demonstrate reading and processing some UTF-8 SFM databases.
    """
    if Globals.verbosityLevel > 1: print( ProgNameVersion )

    import os.path
    filepath = os.path.join( 'Tests/DataFilesForTests/', 'MatigsalugDictionaryA.sfm' )
    if Globals.verbosityLevel > 2: print( "Using {} as test file...".format( filepath ) )

    linesDB = USFMFile()
    linesDB.read( filepath, ignoreSFMs=('mn','aMU','aMW','cu','cp') )
    print( len(linesDB.lines), 'lines read from file', filepath )
    for i, r in enumerate(linesDB.lines):
        print ( i, r)
        if i>9: break
    print ( '...\n',len(linesDB.lines)-1, linesDB.lines[-1], '\n') # Display the last record
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of USFMFile.py