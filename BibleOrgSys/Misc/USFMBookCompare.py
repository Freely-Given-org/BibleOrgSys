#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFMBookCompare.py
#
# Module comparing USFM Bible book files
#
# Copyright (C) 2016-2020 Robert Hunt
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
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module comparing USFM Bible book files
    which should be versions of each other
    to try to determine which is likely the most recently edited.

Given two file paths, reads and compares the USFM Bible books
    and returns or prints a dictionary of results.

This also functions as a stand-alone program.

TODO: Needs internationalisation _("around strings")
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-04-12' # by RJH
SHORT_PROGRAM_NAME = "USFMBookCompare"
PROGRAM_NAME = "USFM book file comparator"
PROGRAM_VERSION = '0.17'
programNameVersion = '{} v{}'.format( SHORT_PROGRAM_NAME, PROGRAM_VERSION )

debuggingThisModule = False


import os
import logging
from pathlib import Path
from datetime import datetime

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
#from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys.InputOutput.USFMFile import USFMFile



def USFMBookCompare( filepath1, filepath2, file1Name='file1', file2Name='file2' ):
    """
    """
    vPrint( 'Info', debuggingThisModule, "\nUSFMBookCompare() for USFM Bible books" )
    vPrint( 'Verbose', debuggingThisModule, "  comparing {}".format( filepath1 ) )
    vPrint( 'Verbose', debuggingThisModule, "        and {}".format( filepath2 ) )


    # Set up empty results dictionaries
    resultDict = {}
    resultDict['File1'], resultDict['File2'] = {}, {}
    resultDict['Same'], resultDict['Different'], resultDict['Summary'] = {}, {}, {}


    # Note paths and folders
    resultDict['File1']['Filepath'], resultDict['File2']['Filepath'] = filepath1, filepath2
    resultDict['File1']['Folder'], resultDict['File1']['Filename'] = os.path.split( filepath1 )
    resultDict['File2']['Folder'], resultDict['File2']['Filename'] = os.path.split( filepath2 )
    if resultDict['File2']['Filename'] == resultDict['File1']['Filename']:
        resultDict['Same']['Filename'] = resultDict['File1']['Filename']
    if resultDict['File2']['Folder'] == resultDict['File1']['Folder']:
        resultDict['Same']['Folder'] = resultDict['File1']['Folder']


    # Note file dates and sizes
    s1, s2 = os.stat( filepath1 ), os.stat( filepath2 )
    resultDict['File1']['Filesize'], resultDict['File2']['Filesize'] = s1.st_size, s2.st_size
    if resultDict['File1']['Filesize'] == resultDict['File2']['Filesize']:
        resultDict['Same']['Filesize'] = resultDict['File1']['Filesize']
    else:
        resultDict['Different']['Filesize'] = (resultDict['File1']['Filesize'],resultDict['File2']['Filesize'])
        if s1.st_size > s2.st_size:
            resultDict['Summary']['Filesize'] = "{} is bigger (by {:,} bytes)".format( file1Name, s1.st_size - s2.st_size )
        elif s1.st_size < s2.st_size:
            resultDict['Summary']['Filesize'] = "{} is bigger (by {:,} bytes)".format( file2Name, s2.st_size - s1.st_size )
    resultDict['File1']['ModifiedTimeStamp'], resultDict['File2']['ModifiedTimeStamp'] = s1.st_mtime, s2.st_mtime
    if s1.st_mtime - s2.st_mtime > 1.0:
        resultDict['Summary']['ModifiedTime'] = "{} is newer".format( file1Name )
    elif s2.st_mtime - s1.st_mtime > 1.0:
        resultDict['Summary']['ModifiedTime'] = "{} is newer".format( file2Name )
    t1, t2 = datetime.fromtimestamp( s1.st_mtime ), datetime.fromtimestamp( s2.st_mtime )
    resultDict['File1']['ModifiedDate'], resultDict['File2']['ModifiedDate'] = t1.strftime('%Y-%m-%d'), t2.strftime('%Y-%m-%d')
    if resultDict['File1']['ModifiedDate'] == resultDict['File2']['ModifiedDate']:
        resultDict['Same']['ModifiedDate'] = resultDict['File1']['ModifiedDate']
    else:
        resultDict['Different']['ModifiedDate'] = (resultDict['File1']['ModifiedDate'],resultDict['File2']['ModifiedDate'])
    resultDict['File1']['ModifiedTime'], resultDict['File2']['ModifiedTime'] = t1.strftime('%H:%M:%S'), t2.strftime('%H:%M:%S')
    if resultDict['File1']['ModifiedTime'] == resultDict['File2']['ModifiedTime']:
        resultDict['Same']['ModifiedTime'] = resultDict['File1']['ModifiedTime']
    else:
        resultDict['Different']['ModifiedTime'] = (resultDict['File1']['ModifiedTime'],resultDict['File2']['ModifiedTime'])


    # Read the files
    uf1, uf2 = USFMFile(), USFMFile()
    uf1.read( filepath1 )
    uf2.read( filepath2 )
    #vPrint( 'Quiet', debuggingThisModule, 'f1', uf1.lines )
    #vPrint( 'Quiet', debuggingThisModule, 'f2', uf2.lines )


    # Note line counts
    resultDict['File1']['LineCount'], resultDict['File2']['LineCount'] = len(uf1.lines), len(uf2.lines)
    if resultDict['File1']['LineCount'] == resultDict['File2']['LineCount']:
        resultDict['Same']['LineCount'] = resultDict['File1']['LineCount']
    else:
        resultDict['Different']['LineCount'] = (resultDict['File1']['LineCount'],resultDict['File2']['LineCount'])


    # Work through each file counting chapters and verses, etc.
    resultDict['File1']['IntroLineCount'] = resultDict['File2']['IntroLineCount'] = 0
    resultDict['File1']['ChapterMarkerCount'] = resultDict['File2']['ChapterMarkerCount'] = 0
    resultDict['File1']['VerseMarkerCount'] = resultDict['File2']['VerseMarkerCount'] = 0
    resultDict['File1']['HasContentCount'] = resultDict['File2']['HasContentCount'] = 0
    startedCVs = False
    lastC = lastV = 0
    C, V = '-1', '-1' # So first/id line starts at -1:0
    for marker,line in uf1.lines:
        #vPrint( 'Quiet', debuggingThisModule, '1', C, V, lastC, lastV, marker, line )
        if marker=='c':
            resultDict['File1']['ChapterMarkerCount'] += 1
            C, V, lastV = line.strip(), '0', 0
            try: intC = int( C )
            except ValueError: intC = -2 # invalid value
            startedCVs = True
            if intC != lastC + 1:
                if 'File1Chapters' not in resultDict['Summary']: # only record the first one
                    resultDict['Summary']['File1Chapters'] = "{} has chapters out of order ({} after {})".format( file1Name, C, lastC )
            lastC = intC
        elif marker=='v':
            resultDict['File1']['VerseMarkerCount'] += 1
            V = line.strip().split()[0]
            if '-' in V: # it's a verse bridge
                V,V2 = V.split( '-', 1 )
            else: V2 = None
            try: intV = int( V )
            except ValueError: intV = -1
            startedCVs = True # Some one chapter books don't include a chapter marker
            if intV != lastV + 1:
                if 'File1Verses' not in resultDict['Summary']: # only record the first one
                    resultDict['Summary']['File1Verses'] = "{} has verses out of order ({}:{} after {}:{})".format( file1Name, C, V, C, lastV )
            if V2: lastV = int( V2 )
            else: lastV = intV
        if not startedCVs: resultDict['File1']['IntroLineCount'] += 1
        if line.strip(): resultDict['File1']['HasContentCount'] += 1
        if '<<<<' in line or '====' in line or '>>>>' in line:
            if 'File1Conflicts' not in resultDict['Summary']: # only record the first one
                resultDict['Summary']['File1Conflicts'] = "{} may have a merge conflict around {}:{}".format( file1Name, C, V )

    startedCVs = False
    lastC = lastV = 0
    C, V = '-1', '-1' # So first/id line starts at -1:0
    for marker,line in uf2.lines:
        #vPrint( 'Quiet', debuggingThisModule, '1', C, V, lastC, lastV, marker, line )
        if marker=='c':
            resultDict['File2']['ChapterMarkerCount'] += 1
            C, V, lastV = line.strip(), '0', 0
            try: intC = int( C )
            except ValueError: intC = -2 # invalid value
            startedCVs = True
            if intC != lastC + 1:
                if 'File2Chapters' not in resultDict['Summary']: # only record the first one
                    resultDict['Summary']['File2Chapters'] = "{} has chapters out of order ({} after {})".format( file2Name, C, lastC )
            lastC = intC
        elif marker=='v':
            resultDict['File2']['VerseMarkerCount'] += 1
            V = line.strip().split()[0]
            if '-' in V: # it's a verse bridge
                V,V2 = V.split( '-', 1 )
            else: V2 = None
            try: intV = int( V )
            except ValueError: intV = -1
            startedCVs = True # Some one chapter books don't include a chapter marker
            if intV != lastV + 1:
                if 'File2Verses' not in resultDict['Summary']: # only record the first one
                    resultDict['Summary']['File2Verses'] = "{} has verses out of order ({}:{} after {}:{})".format( file2Name, C, V, C, lastV )
            if V2: lastV = int( V2 )
            else: lastV = intV
        if not startedCVs: resultDict['File2']['IntroLineCount'] += 1
        if line.strip(): resultDict['File2']['HasContentCount'] += 1
        if '<<<<' in line or '====' in line or '>>>>' in line:
            if 'File2Conflicts' not in resultDict['Summary']: # only record the first one
                resultDict['Summary']['File2Conflicts'] = "{} may have a merge conflict around {}:{}".format( file2Name, C, V )

    if resultDict['File1']['IntroLineCount'] == resultDict['File2']['IntroLineCount']:
        resultDict['Same']['IntroLineCount'] = resultDict['File1']['IntroLineCount']
    else:
        resultDict['Different']['IntroLineCount'] = (resultDict['File1']['IntroLineCount'],resultDict['File2']['IntroLineCount'])
        if resultDict['File1']['IntroLineCount'] > resultDict['File2']['IntroLineCount']:
            difference = resultDict['File1']['IntroLineCount'] - resultDict['File2']['IntroLineCount']
            resultDict['Summary']['IntroLineCount'] = "{} has {} more intro marker{}".format( file1Name, difference, '' if difference==1 else 's' )
        elif resultDict['File1']['IntroLineCount'] < resultDict['File2']['IntroLineCount']:
            difference = resultDict['File2']['IntroLineCount'] - resultDict['File1']['IntroLineCount']
            resultDict['Summary']['IntroLineCount'] = "{} has {} more intro marker{}".format( file2Name, difference, '' if difference==1 else 's' )
    if resultDict['File1']['ChapterMarkerCount'] == resultDict['File2']['ChapterMarkerCount']:
        resultDict['Same']['ChapterMarkerCount'] = resultDict['File1']['ChapterMarkerCount']
    else:
        resultDict['Different']['ChapterMarkerCount'] = (resultDict['File1']['ChapterMarkerCount'],resultDict['File2']['ChapterMarkerCount'])
        if resultDict['File1']['ChapterMarkerCount'] > resultDict['File2']['ChapterMarkerCount']:
            difference = resultDict['File1']['ChapterMarkerCount'] - resultDict['File2']['ChapterMarkerCount']
            resultDict['Summary']['ChapterMarkerCount'] = "{} has {} more chapter marker{}".format( file1Name,  )
        elif resultDict['File1']['ChapterMarkerCount'] < resultDict['File2']['ChapterMarkerCount']:
            difference = resultDict['File2']['ChapterMarkerCount'] - resultDict['File1']['ChapterMarkerCount']
            resultDict['Summary']['ChapterMarkerCount'] = "{} has {} more chapter marker{}".format( file2Name, difference, '' if difference==1 else 's' )
    if resultDict['File1']['VerseMarkerCount'] == resultDict['File2']['VerseMarkerCount']:
        resultDict['Same']['VerseMarkerCount'] = resultDict['File1']['VerseMarkerCount']
    else:
        resultDict['Different']['VerseMarkerCount'] = (resultDict['File1']['VerseMarkerCount'],resultDict['File2']['VerseMarkerCount'])
        if resultDict['File1']['VerseMarkerCount'] > resultDict['File2']['VerseMarkerCount']:
            difference = resultDict['File1']['VerseMarkerCount'] - resultDict['File2']['VerseMarkerCount']
            resultDict['Summary']['VerseMarkerCount'] = "{} has {} more verse marker{}".format( file1Name, difference, '' if difference==1 else 's' )
        elif resultDict['File1']['VerseMarkerCount'] < resultDict['File2']['VerseMarkerCount']:
            difference = resultDict['File2']['VerseMarkerCount'] - resultDict['File1']['VerseMarkerCount']
            resultDict['Summary']['VerseMarkerCount'] = "{} has {} more verse marker{}".format( file2Name, difference, '' if difference==1 else 's' )
    if resultDict['File1']['HasContentCount'] == resultDict['File2']['HasContentCount']:
        resultDict['Same']['HasContentCount'] = resultDict['File1']['HasContentCount']
    else:
        resultDict['Different']['HasContentCount'] = (resultDict['File1']['HasContentCount'],resultDict['File2']['HasContentCount'])
        if resultDict['File1']['HasContentCount'] > resultDict['File2']['HasContentCount']:
            difference = resultDict['File1']['HasContentCount'] - resultDict['File2']['HasContentCount']
            resultDict['Summary']['HasContentCount'] = "{} has {} more content line{}".format( file1Name, difference, '' if difference==1 else 's' )
        elif resultDict['File1']['HasContentCount'] < resultDict['File2']['HasContentCount']:
            difference = resultDict['File2']['HasContentCount'] - resultDict['File1']['HasContentCount']
            resultDict['Summary']['HasContentCount'] = "{} has {} more content line{}".format( file2Name, difference, '' if difference==1 else 's' )


    # Work through the files again comparing lines
    #   Trying to resync if there's a different number of lines…NOT FINISHED YET XXXXXXXXXXXXXXX
    resultDict['Same']['SameMarkerCount'] = resultDict['Different']['DifferentMarkerCount'] = 0
    resultDict['Same']['SameLineCount'] = resultDict['Different']['DifferentLineCount'] = 0
    lineIndex = lineOffset = 0
    startedCVs1 = startedCVs2 = False
    while True:
        if lineIndex >= resultDict['File1']['LineCount']:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "File1 done" )
            break
        if lineIndex >= resultDict['File2']['LineCount']:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "File2 done" )
            break
        (m1,l1), (m2,l2) = uf1.lines[lineIndex], uf2.lines[lineIndex+lineOffset]
        #vPrint( 'Quiet', debuggingThisModule, lineIndex, lineOffset, m1, m2 )
        if m1==m2: resultDict['Same']['SameMarkerCount'] += 1
        else:
            if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, "Diff", m1, m2, l1, l2 )
            resultDict['Different']['DifferentMarkerCount'] += 1
        if m1==m2 and l1==l2: resultDict['Same']['SameLineCount'] += 1
        else:
            if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, "Diff", m1, m2, l1, l2 )
            resultDict['Different']['DifferentLineCount'] += 1
        lineIndex += 1


    # Clean up and return
    for something,value in list( resultDict['Different'].items() ):
        if not value: del resultDict['Different'][something]
    return resultDict
# end of USFMBookCompare



def briefDemo() -> None:
    """
    Brief demo to check class is working -- must be fast
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    fp1 = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/MBT01GEN.SCP' )
    fp2 = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/MBT01GEN.SCP.BAK' )
    allOkay = True
    if not os.path.exists( fp1 ): logging.critical( "Filepath1 {!r} is invalid -- aborting".format( fp1 ) ); allOkay = False
    if not os.path.exists( fp2 ): logging.critical( "Filepath2 {!r} is invalid -- aborting".format( fp2 ) ); allOkay = False
    if allOkay:
        vPrint( 'Quiet', debuggingThisModule, "\nFile1 is: {}".format( fp1 ) )
        vPrint( 'Quiet', debuggingThisModule, "File2 is: {}".format( fp2 ) )

        result = USFMBookCompare( fp1, fp2, file1Name='SCP file', file2Name='BAK file' )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "\nResults:" )
            for division,dResults in result.items():
                if not dResults: continue
                if division in ('File1','File2') and BibleOrgSysGlobals.verbosityLevel < 4 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                if division in ('Same','Different') and BibleOrgSysGlobals.verbosityLevel < 3 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                vPrint( 'Quiet', debuggingThisModule, "  {} results are:".format( division ) )
                for field,fResult in dResults.items():
                    vPrint( 'Quiet', debuggingThisModule, "    {}: {}".format( field,fResult ) )
# end of USFMBookCompare.briefDemo

def fullDemo() -> None:
    """
    Demonstration program to show off USFM Bible book comparison.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    fp1 = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/MBT01GEN.SCP' )
    fp2 = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/MBT01GEN.SCP.BAK' )
    allOkay = True
    if not os.path.exists( fp1 ): logging.critical( "Filepath1 {!r} is invalid -- aborting".format( fp1 ) ); allOkay = False
    if not os.path.exists( fp2 ): logging.critical( "Filepath2 {!r} is invalid -- aborting".format( fp2 ) ); allOkay = False
    if allOkay:
        vPrint( 'Quiet', debuggingThisModule, "\nFile1 is: {}".format( fp1 ) )
        vPrint( 'Quiet', debuggingThisModule, "File2 is: {}".format( fp2 ) )

        result = USFMBookCompare( fp1, fp2, file1Name='SCP file', file2Name='BAK file' )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "\nResults:" )
            for division,dResults in result.items():
                if not dResults: continue
                if division in ('File1','File2') and BibleOrgSysGlobals.verbosityLevel < 4 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                if division in ('Same','Different') and BibleOrgSysGlobals.verbosityLevel < 3 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                vPrint( 'Quiet', debuggingThisModule, "  {} results are:".format( division ) )
                for field,fResult in dResults.items():
                    vPrint( 'Quiet', debuggingThisModule, "    {}: {}".format( field,fResult ) )
# end of USFMBookCompare.fullDemo

def main() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    fp1, fp2 = BibleOrgSysGlobals.commandLineArguments.file1, BibleOrgSysGlobals.commandLineArguments.file2
    allOkay = True
    if not os.path.exists( fp1 ): logging.critical( "Filepath1 {!r} is invalid—aborting".format( fp1 ) ); allOkay = False
    if not os.path.exists( fp2 ): logging.critical( "Filepath2 {!r} is invalid—aborting".format( fp2 ) ); allOkay = False
    if allOkay:
        result = USFMBookCompare( fp1, fp2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "\nResults:" )
            for division,dResults in result.items():
                if division in ('File1','File2') and BibleOrgSysGlobals.verbosityLevel < 4 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                if division in ('Same','Different') and BibleOrgSysGlobals.verbosityLevel < 3 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                vPrint( 'Quiet', debuggingThisModule, "  {} results are:".format( division ) )
                for field,fResult in dResults.items():
                    vPrint( 'Quiet', debuggingThisModule, "    {}: {}".format( field,fResult ) )
# end of USFMBookCompare.main

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demoFlag = False # Set to true to run the demo instead of main()

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION )
    if not demoFlag:
        parser.add_argument('file1', help="USFM Bible book file 1" )
        parser.add_argument('file2', help="USFM Bible book file 2" )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    if demoFlag: demo()
    else: main()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USFMBookCompare.py
