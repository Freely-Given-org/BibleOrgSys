#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFMBookCompare.py
#
# Module comparing USFM Bible book files
#
# Copyright (C) 2016 Robert Hunt
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
Module comparing USFM Bible book files

Given two file paths, reads and compares the USFM Bible books
    and returns or prints a dictionary of results.
"""

from gettext import gettext as _

LastModifiedDate = '2016-05-16' # by RJH
ShortProgName = "USFMBookCompare"
ProgName = "USFM book file comparator"
ProgVersion = '0.13'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, logging
from collections import OrderedDict
from datetime import datetime

#from singleton import singleton
import BibleOrgSysGlobals
from USFMFile import USFMFile



def USFMBookCompare( filepath1, filepath2 ):
    """
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "\nUSFMBookCompare() for USFM Bible books" )
    if BibleOrgSysGlobals.verbosityLevel > 3:
        print( "  comparing {}".format( filepath1 ) )
        print( "        and {}".format( filepath2 ) )


    # Set up empty results dictionaries
    resultDict = OrderedDict()
    resultDict['File1'], resultDict['File2'] = OrderedDict(), OrderedDict()
    resultDict['Same'], resultDict['Different'], resultDict['Summary'] = OrderedDict(), OrderedDict(), OrderedDict()


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
            resultDict['Summary']['Filesize'] = "file1 is bigger (by {:,} bytes)".format( s1.st_size - s2.st_size )
        elif s1.st_size < s2.st_size:
            resultDict['Summary']['Filesize'] = "file2 is bigger (by {:,} bytes)".format( s2.st_size - s1.st_size )
    resultDict['File1']['ModifiedTimeStamp'], resultDict['File2']['ModifiedTimeStamp'] = s1.st_mtime, s2.st_mtime
    if s1.st_mtime - s2.st_mtime > 1.0:
        resultDict['Summary']['ModifiedTime'] = "file1 is newer"
    elif s2.st_mtime - s1.st_mtime > 1.0:
        resultDict['Summary']['ModifiedTime'] = "file2 is newer"
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
    #print( 'f1', uf1.lines )
    #print( 'f2', uf2.lines )


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
    C = V = '0'
    for marker,line in uf1.lines:
        #print( '1', C, V, lastC, lastV, marker, line )
        if marker=='c':
            resultDict['File1']['ChapterMarkerCount'] += 1
            C, V, lastV = line.strip(), '0', 0
            try: intC = int( C )
            except ValueError: intC = -1
            startedCVs = True
            if intC != lastC + 1:
                if 'File1Chapters' not in resultDict['Summary']: # only record the first one
                    resultDict['Summary']['File1Chapters'] = "file1 has chapters out of order ({} after {})".format( C, lastC )
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
                    resultDict['Summary']['File1Verses'] = "file1 has verses out of order ({}:{} after {}:{})".format( C, V, C, lastV )
            if V2: lastV = int( V2 )
            else: lastV = intV
        if not startedCVs: resultDict['File1']['IntroLineCount'] += 1
        if line.strip(): resultDict['File1']['HasContentCount'] += 1
        if '<<<<' in line or '====' in line or '>>>>' in line:
            if 'File1Conflicts' not in resultDict['Summary']: # only record the first one
                resultDict['Summary']['File1Conflicts'] = "file1 may have a merge conflict around {}:{}".format( C, V )

    startedCVs = False
    lastC = lastV = 0
    C = V = '0'
    for marker,line in uf2.lines:
        #print( '1', C, V, lastC, lastV, marker, line )
        if marker=='c':
            resultDict['File2']['ChapterMarkerCount'] += 1
            C, V, lastV = line.strip(), '0', 0
            try: intC = int( C )
            except ValueError: intC = -1
            startedCVs = True
            if intC != lastC + 1:
                if 'File2Chapters' not in resultDict['Summary']: # only record the first one
                    resultDict['Summary']['File2Chapters'] = "file2 has chapters out of order ({} after {})".format( C, lastC )
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
                    resultDict['Summary']['File2Verses'] = "file2 has verses out of order ({}:{} after {}:{})".format( C, V, C, lastV )
            if V2: lastV = int( V2 )
            else: lastV = intV
        if not startedCVs: resultDict['File2']['IntroLineCount'] += 1
        if line.strip(): resultDict['File2']['HasContentCount'] += 1
        if '<<<<' in line or '====' in line or '>>>>' in line:
            if 'File2Conflicts' not in resultDict['Summary']: # only record the first one
                resultDict['Summary']['File2Conflicts'] = "file2 may have a merge conflict around {}:{}".format( C, V )

    if resultDict['File1']['IntroLineCount'] == resultDict['File2']['IntroLineCount']:
        resultDict['Same']['IntroLineCount'] = resultDict['File1']['IntroLineCount']
    else:
        resultDict['Different']['IntroLineCount'] = (resultDict['File1']['IntroLineCount'],resultDict['File2']['IntroLineCount'])
        if resultDict['File1']['IntroLineCount'] > resultDict['File2']['IntroLineCount']:
            resultDict['Summary']['IntroLineCount'] = "file1 has {} more intro markers".format( resultDict['File1']['IntroLineCount'] - resultDict['File2']['IntroLineCount'] )
        elif resultDict['File1']['IntroLineCount'] < resultDict['File2']['IntroLineCount']:
            resultDict['Summary']['IntroLineCount'] = "file2 has {} more intro markers".format( resultDict['File2']['IntroLineCount'] - resultDict['File1']['IntroLineCount'] )
    if resultDict['File1']['ChapterMarkerCount'] == resultDict['File2']['ChapterMarkerCount']:
        resultDict['Same']['ChapterMarkerCount'] = resultDict['File1']['ChapterMarkerCount']
    else:
        resultDict['Different']['ChapterMarkerCount'] = (resultDict['File1']['ChapterMarkerCount'],resultDict['File2']['ChapterMarkerCount'])
        if resultDict['File1']['ChapterMarkerCount'] > resultDict['File2']['ChapterMarkerCount']:
            resultDict['Summary']['ChapterMarkerCount'] = "file1 has {} more chapter markers".format( resultDict['File1']['ChapterMarkerCount'] - resultDict['File2']['ChapterMarkerCount'] )
        elif resultDict['File1']['ChapterMarkerCount'] < resultDict['File2']['ChapterMarkerCount']:
            resultDict['Summary']['ChapterMarkerCount'] = "file2 has {} more chapter markers".format( resultDict['File2']['ChapterMarkerCount'] - resultDict['File1']['ChapterMarkerCount'] )
    if resultDict['File1']['VerseMarkerCount'] == resultDict['File2']['VerseMarkerCount']:
        resultDict['Same']['VerseMarkerCount'] = resultDict['File1']['VerseMarkerCount']
    else:
        resultDict['Different']['VerseMarkerCount'] = (resultDict['File1']['VerseMarkerCount'],resultDict['File2']['VerseMarkerCount'])
        if resultDict['File1']['VerseMarkerCount'] > resultDict['File2']['VerseMarkerCount']:
            resultDict['Summary']['VerseMarkerCount'] = "file1 has {} more verse markers".format( resultDict['File1']['VerseMarkerCount'] - resultDict['File2']['VerseMarkerCount'] )
        elif resultDict['File1']['VerseMarkerCount'] < resultDict['File2']['VerseMarkerCount']:
            resultDict['Summary']['VerseMarkerCount'] = "file2 has {} more verse markers".format( resultDict['File2']['VerseMarkerCount'] - resultDict['File1']['VerseMarkerCount'] )
    if resultDict['File1']['HasContentCount'] == resultDict['File2']['HasContentCount']:
        resultDict['Same']['HasContentCount'] = resultDict['File1']['HasContentCount']
    else:
        resultDict['Different']['HasContentCount'] = (resultDict['File1']['HasContentCount'],resultDict['File2']['HasContentCount'])
        if resultDict['File1']['HasContentCount'] > resultDict['File2']['HasContentCount']:
            resultDict['Summary']['HasContentCount'] = "file1 has {} more content lines".format( resultDict['File1']['HasContentCount'] - resultDict['File2']['HasContentCount'] )
        elif resultDict['File1']['HasContentCount'] < resultDict['File2']['HasContentCount']:
            resultDict['Summary']['HasContentCount'] = "file2 has {} more content lines".format( resultDict['File2']['HasContentCount'] - resultDict['File1']['HasContentCount'] )


    # Work through the files again comparing lines
    #   Trying to resync if there's a different number of lines....................NOT FINISHED YET XXXXXXXXXXXXXXX
    resultDict['Same']['SameMarkerCount'] = resultDict['Different']['DifferentMarkerCount'] = 0
    resultDict['Same']['SameLineCount'] = resultDict['Different']['DifferentLineCount'] = 0
    lineIndex = lineOffset = 0
    startedCVs1 = startedCVs2 = False
    while True:
        if lineIndex >= resultDict['File1']['LineCount']:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "F1 done" )
            break
        if lineIndex >= resultDict['File2']['LineCount']:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "F2 done" )
            break
        (m1,l1), (m2,l2) = uf1.lines[lineIndex], uf2.lines[lineIndex+lineOffset]
        #print( lineIndex, lineOffset, m1, m2 )
        if m1==m2: resultDict['Same']['SameMarkerCount'] += 1
        else:
            if BibleOrgSysGlobals.debugFlag: print( "Diff", m1, m2, l1, l2 )
            resultDict['Different']['DifferentMarkerCount'] += 1
        if m1==m2 and l1==l2: resultDict['Same']['SameLineCount'] += 1
        else:
            if BibleOrgSysGlobals.debugFlag: print( "Diff", m1, m2, l1, l2 )
            resultDict['Different']['DifferentLineCount'] += 1
        lineIndex += 1


    # Clean up and return
    for something,value in list( resultDict['Different'].items() ):
        if not value: del resultDict['Different'][something]
    return resultDict
# end of USFMBookCompare



def demo():
    """
    Demonstration program to show off USFM Bible book comparison.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( ProgNameVersion )
    #if BibleOrgSysGlobals.print( BibleOrgSysGlobals.commandLineArguments )

    fp1 = 'Tests/DataFilesForTests/USFMTest2/MBT01GEN.SCP'
    fp2 = 'Tests/DataFilesForTests/USFMTest2/MBT01GEN.SCP.BAK'
    allOkay = True
    if not os.path.exists( fp1 ): logging.critical( "Filepath1 {!r} is invalid -- aborting".format( fp1 ) ); allOkay = False
    if not os.path.exists( fp2 ): logging.critical( "Filepath2 {!r} is invalid -- aborting".format( fp2 ) ); allOkay = False
    if allOkay:
        result = USFMBookCompare( fp1, fp2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nResults:" )
            for division,dResults in result.items():
                if not dResults: continue
                if division in ('File1','File2') and BibleOrgSysGlobals.verbosityLevel < 4 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                if division in ('Same','Different') and BibleOrgSysGlobals.verbosityLevel < 3 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                print( "  {} results are:".format( division ) )
                for field,fResult in dResults.items():
                    print( "    {}: {}".format( field,fResult ) )
# end of demo

def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( ProgNameVersion )
    #if BibleOrgSysGlobals.print( BibleOrgSysGlobals.commandLineArguments )

    fp1, fp2 = BibleOrgSysGlobals.commandLineArguments.file1, BibleOrgSysGlobals.commandLineArguments.file2
    allOkay = True
    if not os.path.exists( fp1 ): logging.critical( "Filepath1 {!r} is invalid -- aborting".format( fp1 ) ); allOkay = False
    if not os.path.exists( fp2 ): logging.critical( "Filepath2 {!r} is invalid -- aborting".format( fp2 ) ); allOkay = False
    if allOkay:
        result = USFMBookCompare( fp1, fp2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nResults:" )
            for division,dResults in result.items():
                if division in ('File1','File2') and BibleOrgSysGlobals.verbosityLevel < 4 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                if division in ('Same','Different') and BibleOrgSysGlobals.verbosityLevel < 3 \
                and not BibleOrgSysGlobals.debugFlag:
                    continue
                print( "  {} results are:".format( division ) )
                for field,fResult in dResults.items():
                    print( "    {}: {}".format( field,fResult ) )
# end of main

if __name__ == '__main__':
    #multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    import sys
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    parser.add_argument('file1', help="USFM Bible book file 1" ) #, metavar='XXX')
    parser.add_argument('file2', help="USFM Bible book file 2" ) #, metavar='XXX')
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of USFMBookCompare.py