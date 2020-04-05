#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SFMFile.py
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
Module for reading UTF-8 SFM (Standard Format Marker) file.

There are three kinds of SFM encoded files which can be loaded:
    1/ SFMLines: A "flat" file, read line by line into a list.
            This could be any kind of SFM data.
    2/ SFMRecords: A "record based" file (e.g., a dictionary), read record by record into a list
    3/ SFMRecords: A header segment, then a "record based" structure read into the same list,
            for example an interlinearized text.

  In each case, the SFM and its data field are read into a 2-tuple and saved (in order) in the list.

  Raises IOError if file doesn't exist.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-02-24' # by RJH
SHORT_PROGRAM_NAME = "SFMFile"
PROGRAM_NAME = "SFM Files loader"
PROGRAM_VERSION = '0.86'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging
import sys

if __name__ == '__main__':
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals



class SFMLines:
    """
    Class holding a list of (non-blank) SFM lines.
    Each line is a tuple consisting of (SFMMarker, SFMValue).
    """

    def __init__(self):
        self.lines = []

    def __str__(self):
        """
        This method returns the string representation of a SFM lines object.

        @return: the name of a SFM field object formatted as a string
        @rtype: string
        """
        result = "SFM Lines Object"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        for line in self.lines:
            result += ('\n' if result else '') + str( line )
        return result

    def read( self, SFMFilepath, ignoreSFMs=None, encoding='utf-8' ):
        """
        Read a simple SFM (Standard Format Marker) file into a list of tuples.

        @param SFMFilepath: The filename
        @type SFMFilepath: string
        @param key: The SFM record marker (not including the backslash)
        @type encoding: string
        @rtype: list
        @return: list of lists containing the records
        """

        # Check/handle parameters
        if ignoreSFMs is None: ignoreSFMs = ()

        lastLine, lineCount, result = '', 0, []
        with open( SFMFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
            try:
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF or \ufeff
                        logging.info( "SFMLines: Detected Unicode Byte Order Marker (BOM) in {}".format( SFMFilepath ) )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    #print ( 'SFM file line is "' + line + '"' )
                    #if line[0:2]=='\\_': continue # Just discard Toolbox header lines
                    if line[0]=='#': continue # Just discard comment lines

                    if line[0]!='\\': # Not a SFM line
                        if len(result)==0: # We don't have any SFM data lines yet
                            if BibleOrgSysGlobals.verbosityLevel > 2:
                                logging.error( "Non-SFM line in " + SFMFilepath + " -- line ignored at #" + str(lineCount) )
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
                    si2 = lineAfterBackslash.find( '\\' )
                    if si2!=-1 and (si1==-1 or si2<si1): # Marker stops at a backslash
                        marker = lineAfterBackslash[:si2]
                        text = lineAfterBackslash[si2:]
                    elif si1!=-1: # Marker stops at a space
                        marker = lineAfterBackslash[:si1]
                        text = lineAfterBackslash[si1+1:] # We drop the space
                    else: # The line is only the marker
                        marker = lineAfterBackslash
                        text = ''

                    if marker not in ignoreSFMs:
                        result.append( (marker, text) )

            except UnicodeError as err:
                print( "Unicode error:", sys.exc_info()[0], err )
                logging.critical( "Invalid line in " + SFMFilepath + " -- line ignored at #" + str(lineCount) )
                if lineCount > 1: print( 'Previous line was: ', lastLine )
                #print( line )
                #raise

            self.lines = result
    # end of SFMLines.read
# end of class SFMLines



class SFMRecords:
    """
    Class holding a list of SFM records.
    Each record is a list of SFM lines.
        (The record always starts with the same SFMMarker, except perhaps the first record.)
    Each line is a 2-tuple consisting of (SFMMarker, SFMValue).
    """

    def __init__(self):
        self.records = []

    def __str__(self):
        """
        This method returns the string representation of a SFM lines object.

        @return: the name of a SFM field object formatted as a string
        @rtype: string
        """
        result = ""
        for record in self.records:
            if result: result += '\n' # Blank line between records
            for line in record:
                result += ('\n' if result else '') + str( line )
        return result


    def read( self, SFMFilepath, key=None, ignoreSFMs=None, ignoreEntries=None, changePairs=None, encoding='utf-8' ):
        """
        Read a simple SFM (Standard Format Marker) file into a list of lists of tuples.

        @param SFMFilepath: The filename
        @type SFMFilepath: string
        @param key: The SFM record marker (not including the backslash)
        @type encoding: string
        @rtype: list
        @return: list of lists containing the records
        """

        def changeMarker( currentMarker, changePairs ):
            """
            Change the SFM marker if required
            """
            if changePairs:
                for findMarker, replaceMarker in changePairs:
                    if findMarker==currentMarker: return replaceMarker
            return currentMarker
        # end of changeMarker

        # Main code for SFMRecords.read()
        # Check/handle parameters
        if ignoreSFMs is None: ignoreSFMs = ()
        #print( "ignoreSFMs =", ignoreSFMs )
        if ignoreEntries is None: ignoreEntries = ()
        #print( "ignoreEntries =", ignoreEntries )
        if key:
            if '\\' in key: raise ValueError('SFM marker must not contain backslash')
            if ' ' in key: raise ValueError('SFM marker must not contain spaces')
        self.SFMFilepath = SFMFilepath
        self.key = key
        self.ignoreSFMs = ignoreSFMs
        self.ignoreEntries = ignoreEntries
        self.changePairs = changePairs
        self.encoding = encoding

        lastLine, lineCount, record, result = '', 0, [], []
        with open( SFMFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
            try:
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and encoding.lower()=='utf-8' and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "SFMRecords: Detected Unicode Byte Order Marker (BOM) in {}".format( SFMFilepath ) )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    #print ( 'SFM file line is "' + line + '"' )
                    #if line[0:2]=='\\_': continue # Just discard Toolbox header lines
                    if line[0]=='#': continue # Just discard comment lines
                    if line[0]!='\\':
                        if len(record)==0:
                            print( 'SFMFile.py: SFM file line is "' + line + '"' )
                            print( "First character of line is '" + line[0] + "' (" + str(ord(line[0])) + ")" )
                            print( "XXXRecord is", record)
                            raise IOError('Oops: Line break on last line of record not handled here "' + line + '"')
                        else: # Append this continuation line
                            oldmarker, oldtext = record.pop()
                            record.append( (oldmarker, oldtext+' '+line) )
                            continue

                    lineAfterBackslash = line[1:]
                    si1 = lineAfterBackslash.find( ' ' )
                    si2 = lineAfterBackslash.find( '\\' )
                    if si2!=-1 and (si1==-1 or si2<si1): # Marker stops at a backslash
                        marker = changeMarker( lineAfterBackslash[:si2], changePairs )
                        text = lineAfterBackslash[si2:]
                    elif si1!=-1: # Marker stops at a space
                        marker = changeMarker( lineAfterBackslash[:si1], changePairs )
                        text = lineAfterBackslash[si1+1:] # We drop the space
                    else: # The line is only the marker
                        marker = changeMarker( lineAfterBackslash, changePairs )
                        text = ''
                        if marker==key: print ("Warning: Have a blank key field after", record)

                    if not key and marker not in ignoreSFMs:
                        print ('    Assuming', marker, 'to be the SFM key for', SFMFilepath)
                        key = marker
                    if marker==key: # Save the previous record
                        if record and record[0][1] not in ignoreEntries: # Looks at the text associated with the first (record key) marker
                            strippedRecord = []
                            for savedMarker,savedText in record:
                                if savedMarker not in ignoreSFMs:
                                    strippedRecord.append( (savedMarker, savedText) )
                            if strippedRecord:
                                result.append( strippedRecord )
                        record = []
                    # Save the current marker and text
                    record.append( (marker, text) )

            except UnicodeError as err:
                print( "Unicode error:", sys.exc_info()[0], err )
                logging.critical( "Invalid line in " + SFMFilepath + " -- line ignored at " + str(lineCount) )
                if lineCount > 1: print( 'Previous line was: ', lastLine )
                else: print( 'Possible encoding error -- expected', encoding )
                #raise

            # Write the final record
            if record and record[0][1] not in ignoreEntries: # Looks at the text associated with the first (record key) marker
                strippedRecord = []
                for savedMarker,savedText in record:
                    if savedMarker not in ignoreSFMs:
                        strippedRecord.append( (savedMarker, savedText) )
                if strippedRecord:
                    result.append( strippedRecord ) # Append the last record

            self.records = result
    # end of SFMRecords.read


    def analyze( self ):
        """
        Analyzes the list of records read in from the file
            to find the smallest and largest size (number of lines) of each record
        as well as making a list of all the SFM marker types
            and a dictionary of all the possible values of all the various SFM markers.
        Returns these two integers
            plus the list and the dictionary.
        """
        smallestSize, largestSize, markerList, markerSets = 9999, -1, [], {}
        for record in self.records:
            lr = len( record )
            if lr < smallestSize: smallestSize = lr
            if lr > largestSize: largestSize = lr
            for marker, value in record:
                if marker not in markerList:
                    markerList.append( marker )
                    markerSets[marker] = []
                if value not in markerSets[marker]:
                    markerSets[marker].append( value )
        return smallestSize, largestSize, markerList, markerSets
    # end of SFMRecords.analyze


    def copyToDict( self, internalStructure ):
        """
        self.records is a list of lists.

        This function copies them to a dictionary
            where the keys are the values of the given marker (self.key).

        The inner structure can either be lists (if the parameter is "list" )
            which is most useful if lines with the identical SFM can be repeated within the record.
        The inner structure can be dicts (if the parameter is "dict" )
            which then checks that each line within the record starts with a unique marker.
            The order of the original lines within each record is lost.

        Returns the dictionary.
        """
        assert internalStructure in ( "list", "dict" )
        self.dataDict = {}
        for record in self.records:
            for j, (marker,value) in enumerate( record ):
                if j==0:
                    assert marker == self.key
                    key = value
                    self.dataDict[key] = [] if internalStructure=="list" else {}
                else:
                    if isinstance( self.dataDict[key], list ):
                        self.dataDict[key].append( (marker,value) )
                    elif isinstance( self.dataDict[key], dict ):
                        #print( j, key, marker, value )
                        if marker in self.dataDict[key]:
                            logging.warning( "Multiple {} lines in {} record--will be overwritten".format( marker, key ) )
                        self.dataDict[key][marker] = value
        return self.dataDict
    # end of SFMRecords.copyToDict
# end of class SFMRecords



def demo() -> None:
    """
    Demonstrate reading and processing some UTF-8 SFM databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    import os.path
    filepath = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MatigsalugDictionaryA.sfm' )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "Using {} as test file…".format( filepath ) )

    linesDB = SFMLines()
    linesDB.read( filepath, ignoreSFMs=('mn','aMU','aMW','cu','cp') )
    print( len(linesDB.lines), 'lines read from file', filepath )
    for i, r in enumerate(linesDB.lines):
        print ( i, r)
        if i>9: break
    print ( '…\n',len(linesDB.lines)-1, linesDB.lines[-1], '\n') # Display the last record

    recordsDB = SFMRecords()
    recordsDB.read( filepath, 'og', ignoreSFMs=('mn','aMU','aMW','cu','cp'))
    print( len(recordsDB.records), 'records read from file', filepath )
    for i, r in enumerate(recordsDB.records):
        print ( i, r)
        if i>3: break
    print( '…\n',len(recordsDB.records)-1, recordsDB.records[-1]) # Display the last record
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of SFMFile.py
