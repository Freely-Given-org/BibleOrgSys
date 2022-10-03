#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# DemoTests.py
#
# Module running various other modules demo() or main() functions
#                           as a way of testing the overall systems.
#
# Copyright (C) 2013-2022 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This program tests the successful loading of most of the other modules
    and tries running the demo() functions for modules
    and the main() functions for programs.

It then prints a simple summary of how many modules run successfully
    without crashing
and how many failed.

This isn't as thorough as the proper test routines
    but it's still much better than nothing.

CHANGELOG:
    2022-06-04 commented out TokenisedBible test (uncompleted module has been removed)
    2022-04-22 added ScriptureBurritoBible test
"""
from gettext import gettext as _
from typing import List, Tuple
import sys
import os.path
from datetime import datetime
from pathlib import Path

if __name__ == '__main__':
    aboveFolderPath = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
    if aboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Formats import USFMBible # Has to be here for unpickling in TestBib5 to work

# Some Misc and Apps modules imported below are up a level
sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # Some Misc and Apps modules imported below are up a level
#dPrint( 'Info', DEBUGGING_THIS_MODULE, sys.path )

LAST_MODIFIED_DATE = '2022-06-07' # by RJH
SHORT_PROGRAM_NAME = "DemoTests"
PROGRAM_NAME = "BOS+ Demo tests"
PROGRAM_VERSION = '0.69'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
PROGRAM_NAME_VERSION_DATE = f'{PROGRAM_NAME_VERSION} {_("last modified")} {LAST_MODIFIED_DATE}'


DEBUGGING_THIS_MODULE = False


##################################################################################################

testDemos = True # Setting to False only checks importing (very fast)
testFullDemos = False # Setting to False only runs briefDemos (20-30 mins cf. 2-3 hrs)

testDefault = True
#testStrict = False
testVerbose = False
testStrictVerbose = False
testStrictVerboseDebug = False
#testStrictExport = False
#testStrictExportVerbose = False
testStrictVerboseDebugExport = False
assert testDefault or testVerbose or testStrictVerbose \
        or testStrictVerboseDebug or testStrictVerboseDebugExport


includeKnownBadExports = False
includeKnownGood = True
includeExtensiveTests = False # e.g., Haiola, BDB submissions, etc.
includeGIUs = False


##################################################################################################


interrupted = False # Global to mark if we have an external interrupt
resultFilepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_LOG_FOLDERPATH.joinpath( 'DemoTestsResults.txt' )



def getElapsedTime( moduleName:str, startTime ):
    """
    Returns a 2-tuple with the module name and the integer number of elapsed seconds.
    """
    return moduleName, ( datetime.now() - startTime ).seconds # This is an integer
# end of getElapsedTime


def getElapsedTimeString( moduleName:str, elapsedSeconds ):
    """
    Returns a formatted string containing the elapsed time since startTime.
    """
    minutes = elapsedSeconds / 60.0
    hours = minutes / 60.0
    if minutes > 90:
        return f'{hours:.2g} hours'.lstrip()
    if elapsedSeconds > 90:
        return f'{minutes:.2g} minutes'.lstrip()
    secondsString = str(elapsedSeconds)
    return moduleName, secondsString + (' second' if secondsString=='1' else ' seconds')
# end of getElapsedTimeString


def publishResultLine( line, printFlag:bool=True ):
    """
    Given a string, print it plus save it to the results file.
    """
    if printFlag and BibleOrgSysGlobals.verbosityLevel > 0: print( line )
    with open( resultFilepath, 'at' ) as myFile: myFile.write( line + '\n' )
# end of publishResultLine


def formatAndPublish( timeList ):
    """
    The parameter is a list of 2-tuples containing (moduleName, timeInSeconds).
    """
    result = "TimeList: "
    for name,seconds in sorted( timeList, key=lambda s: -s[1] ):
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, name, seconds )
        if seconds > 0: result += f" {name}={seconds}"
    publishResultLine( result, printFlag=BibleOrgSysGlobals.commandLineArguments.times or BibleOrgSysGlobals.verbosityLevel > 2 )
# end of formatAndPublish


def formatFailureDetails( exceptionObject:Exception ) -> Tuple[str,Exception,str]:
    """
    Returns a 3-tuple.
    """
    import traceback
    # import linecache
    exc_type, _exc_obj, traceback_obj = sys.exc_info()
    #frame = traceback_obj.tb_frame
    #lineNum = traceback_obj.tb_lineno
    #filename = frame.f_code.co_filename
    #linecache.checkcache( filename )
    #line = linecache.getline( filename, lineNum, frame.f_globals )

    #dPrint( 'Info', DEBUGGING_THIS_MODULE, exc_type, exc_obj, traceback_obj )
    #tbs = traceback.extract_tb( traceback_obj )
    #for j,tbj in enumerate( tbs ):
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, "tb{} {}".format( j, tbj ) )
    #dPrint( 'Info', DEBUGGING_THIS_MODULE, "tbs", tbs[1:] )
    #dPrint( 'Info', DEBUGGING_THIS_MODULE, "tb1", tbs[1] )
    #dPrint( 'Info', DEBUGGING_THIS_MODULE, "format", traceback.format_exc() )
    #dPrint( 'Info', DEBUGGING_THIS_MODULE, "stack", traceback.extract_stack( tbs[1] ) )

    return exc_type, exceptionObject, traceback.format_exc()
# end of formatFailureDetails



def doAll( testType:str, failures:List[str], failureDetails:List[str],
                         successes:List[str], times:List[str] ) -> None:
    """
    Run the demo() function on all the modules (depending on the testType).

    Updates success and failure lists, etc., in outer scope.
    """
    global interrupted

    def doTest( moduleName:str, testModule ) -> None:
        """
        Run either fullDemo() or briefDemo() for the given module as required.
        """
        global interrupted
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nTesting: {moduleName}…" )
        goTime = datetime.now()
        if testDemos:
            try:
                testFunction = testModule.fullDemo if testFullDemos else testModule.briefDemo
                testFunction()
                successes.append( moduleName )
            # except KeyboardInterrupt:
            #     raise KeyboardInterrupt
            except Exception as err:
                expandedName = f"{moduleName} {'fullDemo' if testFullDemos else 'briefDemo'}"
                print( f"{expandedName} failed!" )
                failures.append( expandedName )
                failureDetails.append( f"{expandedName}: {formatFailureDetails( err )}" )
                if isinstance( err, KeyboardInterrupt): print("reraise"); raise KeyboardInterrupt
        times.append( getElapsedTime( moduleName, goTime ) )
    # end of doTest function

    moduleName = 'BibleOrgSysGlobals'
    doTest( moduleName, BibleOrgSysGlobals )

    moduleName = 'ControlFiles'
    try:
        from BibleOrgSys.InputOutput import ControlFiles
        doTest( moduleName, ControlFiles )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'SFMFile'
    try:
        from BibleOrgSys.InputOutput import SFMFile
        doTest( moduleName, SFMFile )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'TextFile'
    try:
        from BibleOrgSys.InputOutput import TextFile
        doTest( moduleName, TextFile )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'XMLFile'
    try:
        from BibleOrgSys.InputOutput import XMLFile
        doTest( moduleName, XMLFile )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'MLWriter'
    try:
        from BibleOrgSys.InputOutput import MLWriter
        doTest( moduleName, MLWriter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'BibleBooksCodesConverter'
    try:
        from BibleOrgSys.Reference.Converters import BibleBooksCodesConverter
        doTest( moduleName, BibleBooksCodesConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleBooksCodes'
    try:
        from BibleOrgSys.Reference import BibleBooksCodes
        doTest( moduleName, BibleBooksCodes )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'ISO_639_3_LanguagesConverter'
    try:
        from BibleOrgSys.Reference.Converters import ISO_639_3_LanguagesConverter
        doTest( moduleName, ISO_639_3_LanguagesConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'ISO_639_3_Languages'
    try:
        from BibleOrgSys.Reference import ISO_639_3_Languages
        doTest( moduleName, ISO_639_3_Languages )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleBookOrdersConverter'
    try:
        from BibleOrgSys.Reference.Converters import BibleBookOrdersConverter
        doTest( moduleName, BibleBookOrdersConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleBookOrders'
    try:
        from BibleOrgSys.Reference import BibleBookOrders
        doTest( moduleName, BibleBookOrders )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BiblePunctuationSystemsConverter'
    try:
        from BibleOrgSys.Reference.Converters import BiblePunctuationSystemsConverter
        doTest( moduleName, BiblePunctuationSystemsConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BiblePunctuationSystems'
    try:
        from BibleOrgSys.Reference import BiblePunctuationSystems
        doTest( moduleName, BiblePunctuationSystems )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleBooksNamesConverter'
    try:
        from BibleOrgSys.Reference.Converters import BibleBooksNamesConverter
        doTest( moduleName, BibleBooksNamesConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleBooksNames'
    try:
        from BibleOrgSys.Reference import BibleBooksNames
        doTest( moduleName, BibleBooksNames )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleVersificationSystemsConverter'
    try:
        from BibleOrgSys.Reference.Converters import BibleVersificationSystemsConverter
        doTest( moduleName, BibleVersificationSystemsConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleVersificationSystems'
    try:
        from BibleOrgSys.Reference import BibleVersificationSystems
        doTest( moduleName, BibleVersificationSystems )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleOrganisationalSystemsConverter'
    try:
        from BibleOrgSys.Reference.Converters import BibleOrganisationalSystemsConverter
        doTest( moduleName, BibleOrganisationalSystemsConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleOrganisationalSystems'
    try:
        from BibleOrgSys.Reference import BibleOrganisationalSystems
        doTest( moduleName, BibleOrganisationalSystems )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleReferencesLinksConverter'
    try:
        from BibleOrgSys.Reference.Converters import BibleReferencesLinksConverter
        doTest( moduleName, BibleReferencesLinksConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleReferencesLinks'
    try:
        from BibleOrgSys.Reference import BibleReferencesLinks
        doTest( moduleName, BibleReferencesLinks )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'VerseReferences'
    try:
        from BibleOrgSys.Reference import VerseReferences
        doTest( moduleName, VerseReferences )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleReferences'
    try:
        from BibleOrgSys.Reference import BibleReferences
        doTest( moduleName, BibleReferences )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'USFM2MarkersConverter'
    try:
        from BibleOrgSys.Reference.Converters import USFM2MarkersConverter
        doTest( moduleName, USFM2MarkersConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'USFM2Markers'
    try:
        from BibleOrgSys.Reference import USFM2Markers
        doTest( moduleName, USFM2Markers )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'USFM3MarkersConverter'
    try:
        from BibleOrgSys.Reference.Converters import USFM3MarkersConverter
        doTest( moduleName, USFM3MarkersConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'USFM3Markers'
    try:
        from BibleOrgSys.Reference import USFM3Markers
        doTest( moduleName, USFM3Markers )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'USFMFilenames'
    try:
        from BibleOrgSys.InputOutput import USFMFilenames
        doTest( moduleName, USFMFilenames )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'USXFilenames'
    try:
        from BibleOrgSys.InputOutput import USXFilenames
        doTest( moduleName, USXFilenames )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'InternalBibleInternals'
    try:
        from BibleOrgSys.Internals import InternalBibleInternals
        doTest( moduleName, InternalBibleInternals )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'InternalBibleIndexes'
    try:
        from BibleOrgSys.Internals import InternalBibleIndexes
        doTest( moduleName, InternalBibleIndexes )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'InternalBibleBook'
    try:
        from BibleOrgSys.Internals import InternalBibleBook
        doTest( moduleName, InternalBibleBook )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'InternalBible'
    try:
        from BibleOrgSys.Internals import InternalBible
        doTest( moduleName, InternalBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'Bible'
    try:
        from BibleOrgSys import Bible
        doTest( moduleName, Bible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleWriter'
    try:
        from BibleOrgSys import BibleWriter
        doTest( moduleName, BibleWriter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'UnknownBible'
    try:
        from BibleOrgSys import UnknownBible
        doTest( moduleName, UnknownBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'USFM2BibleBook'
    try:
        from BibleOrgSys.Formats import USFM2BibleBook
        doTest( moduleName, USFM2BibleBook )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'USFM2Bible'
    try:
        from BibleOrgSys.Formats import USFM2Bible
        doTest( moduleName, USFM2Bible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'USFMBibleBook'
    try:
        from BibleOrgSys.Formats import USFMBibleBook
        doTest( moduleName, USFMBibleBook )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'USFMBible'
    try:
        # NOTE: USFMBible is already imported at the beginning of the file
        doTest( moduleName, USFMBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'ESFMBibleBook'
    try:
        from BibleOrgSys.Formats import ESFMBibleBook
        doTest( moduleName, ESFMBibleBook )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'ESFMBible'
    try:
        from BibleOrgSys.Formats import ESFMBible
        doTest( moduleName, ESFMBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'USXXMLBibleBook'
    try:
        from BibleOrgSys.Formats import USXXMLBibleBook
        doTest( moduleName, USXXMLBibleBook )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'USXXMLBible'
    try:
        from BibleOrgSys.Formats import USXXMLBible
        doTest( moduleName, USXXMLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'USFXXMLBible'
    try:
        from BibleOrgSys.Formats import USFXXMLBible
        doTest( moduleName, USFXXMLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'UnboundBible'
    try:
        from BibleOrgSys.Formats import UnboundBible
        doTest( moduleName, UnboundBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'ForgeForSwordSearcherBible'
    try:
        from BibleOrgSys.Formats import ForgeForSwordSearcherBible
        doTest( moduleName, ForgeForSwordSearcherBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'VPLBible'
    try:
        from BibleOrgSys.Formats import VPLBible
        doTest( moduleName, VPLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'DrupalBible'
    try:
        from BibleOrgSys.Formats import DrupalBible
        doTest( moduleName, DrupalBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'YETBible'
    try:
        from BibleOrgSys.Formats import YETBible
        doTest( moduleName, YETBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'theWordBible'
    try:
        from BibleOrgSys.Formats import theWordBible
        doTest( moduleName, theWordBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'EasyWorshipBible'
    try:
        from BibleOrgSys.Formats import EasyWorshipBible
        doTest( moduleName, EasyWorshipBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'MySwordBible'
    try:
        from BibleOrgSys.Formats import MySwordBible
        doTest( moduleName, MySwordBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'ESwordBible'
    try:
        from BibleOrgSys.Formats import ESwordBible
        doTest( moduleName, ESwordBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'ESwordCommentary'
    try:
        from BibleOrgSys.Formats import ESwordCommentary
        doTest( moduleName, ESwordCommentary )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'MyBibleBible'
    try:
        from BibleOrgSys.Formats import MyBibleBible
        doTest( moduleName, MyBibleBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'OpenSongXMLBible'
    try:
        from BibleOrgSys.Formats import OpenSongXMLBible
        doTest( moduleName, OpenSongXMLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'PierceOnlineBible'
    try:
        from BibleOrgSys.Formats import PierceOnlineBible
        doTest( moduleName, PierceOnlineBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'VerseViewXMLBible'
    try:
        from BibleOrgSys.Formats import VerseViewXMLBible
        doTest( moduleName, VerseViewXMLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'ZefaniaXMLBible'
    try:
        from BibleOrgSys.Formats import ZefaniaXMLBible
        doTest( moduleName, ZefaniaXMLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'HaggaiXMLBible'
    try:
        from BibleOrgSys.Formats import HaggaiXMLBible
        doTest( moduleName, HaggaiXMLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'OSISXMLBible'
    try:
        from BibleOrgSys.Formats import OSISXMLBible
        doTest( moduleName, OSISXMLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'LDML'
    try:
        from BibleOrgSys.Reference import LDML
        doTest( moduleName, LDML )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'PTX7Bible'
    try:
        from BibleOrgSys.Formats import PTX7Bible
        doTest( moduleName, PTX7Bible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'PTX8Bible'
    try:
        from BibleOrgSys.Formats import PTX8Bible
        doTest( moduleName, PTX8Bible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'DBLBible'
    try:
        from BibleOrgSys.Formats import DBLBible
        doTest( moduleName, DBLBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'ScriptureBurritoBible'
    try:
        from BibleOrgSys.Formats import ScriptureBurritoBible
        doTest( moduleName, ScriptureBurritoBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    # moduleName = 'DigitalBibleLibraryOnline'
    # try:
    #     from BibleOrgSys.NotIncluded.Online import DigitalBibleLibraryOnline
    #     doTest( moduleName, DigitalBibleLibraryOnline )
    # except KeyboardInterrupt: interrupted=True; return
    # except (ImportError, SyntaxError) as err:
    #     print( f"{moduleName} import failed!" )
    #     failures.append( f"{moduleName} import" )
    #     failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'Door43OnlineCatalog'
    try:
        from BibleOrgSys.Online import Door43OnlineCatalog
        doTest( moduleName, Door43OnlineCatalog )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'Door43ContentServiceOnline'
    try:
        from BibleOrgSys.Online import Door43ContentServiceOnline
        doTest( moduleName, Door43ContentServiceOnline )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'PalmDBBible'
    try:
        from BibleOrgSys.Formats import PalmDBBible
        doTest( moduleName, PalmDBBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'GoBible'
    try:
        from BibleOrgSys.Formats import GoBible
        doTest( moduleName, GoBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BCVBible'
    try:
        from BibleOrgSys.Formats import BCVBible
        doTest( moduleName, BCVBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'CSVBible'
    try:
        from BibleOrgSys.Formats import CSVBible
        doTest( moduleName, CSVBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    # This module is removed, at least for now
    # moduleName = 'TokenisedBible'
    # try:
    #     from BibleOrgSys.Formats import TokenisedBible
    #     doTest( moduleName, TokenisedBible )
    # except KeyboardInterrupt: interrupted=True; return
    # except (ImportError, SyntaxError) as err:
    #     print( f"{moduleName} import failed!" )
    #     failures.append( f"{moduleName} import" )
    #     failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'uWNotesBible'
    try:
        from BibleOrgSys.Formats import uWNotesBible
        doTest( moduleName, uWNotesBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'uWOBSBible'
    try:
        from BibleOrgSys.Formats import uWOBSBible
        doTest( moduleName, uWOBSBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    # moduleName = 'JSONBible'
    # try:
    #     from BibleOrgSys.NotIncluded.Formats import JSONBible
    #     doTest( moduleName, JSONBible )
    # except KeyboardInterrupt: interrupted=True; return
    # except (ImportError, SyntaxError) as err:
    #     print( f"{moduleName} import failed!" )
    #     failures.append( f"{moduleName} import" )
    #     failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'PickledBible'
    try:
        from BibleOrgSys.Formats import PickledBible
        doTest( moduleName, PickledBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'Hebrew'
    try:
        from BibleOrgSys.OriginalLanguages import Hebrew
        doTest( moduleName, Hebrew )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'HebrewLexiconConverter'
    try:
        from BibleOrgSys.OriginalLanguages.Converters import HebrewLexiconConverter
        doTest( moduleName, HebrewLexiconConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'HebrewLexicon'
    try:
        from BibleOrgSys.OriginalLanguages import HebrewLexicon
        doTest( moduleName, HebrewLexicon )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'HebrewWLCBible'
    try:
        from BibleOrgSys.OriginalLanguages import HebrewWLCBible
        doTest( moduleName, HebrewWLCBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'Greek'
    try:
        from BibleOrgSys.OriginalLanguages import Greek
        doTest( moduleName, Greek )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'GreekLexiconConverter'
    try:
        from BibleOrgSys.OriginalLanguages.Converters import GreekLexiconConverter
        doTest( moduleName, GreekLexiconConverter )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'GreekLexicon'
    try:
        from BibleOrgSys.OriginalLanguages import GreekLexicon
        doTest( moduleName, GreekLexicon )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'GreekNT'
    try:
        from BibleOrgSys.OriginalLanguages import GreekNT
        doTest( moduleName, GreekNT )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'BibleLexicon'
    try:
        from BibleOrgSys.OriginalLanguages import BibleLexicon
        doTest( moduleName, BibleLexicon )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'GenericOnlineBible'
    try:
        from BibleOrgSys.Online import GenericOnlineBible
        doTest( moduleName, GenericOnlineBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'BibleBrainOnline'
    try:
        from BibleOrgSys.Online import BibleBrainOnline
        doTest( moduleName, BibleBrainOnline )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'SwordInstallManager'
    try:
        from BibleOrgSys.Online import SwordInstallManager
        doTest( moduleName, SwordInstallManager )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'SwordBible'
    try:
        from BibleOrgSys.Formats import SwordBible
        # doTest( moduleName, SwordBible )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'SwordModules'
    try:
        from BibleOrgSys.Formats import SwordModules
        # doTest( moduleName, SwordModules )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    swordTypes = 'CrosswireLibrary', 'OurCode'
    from BibleOrgSys.Formats import SwordResources
    originalSwordType = SwordResources.SwordType
    print( f"originalSwordType = {originalSwordType}" )
    assert originalSwordType in swordTypes
    for swIndex,thisSwordType in enumerate( swordTypes ): # We'll do all these tests twice if possible
        if swIndex == 1: # Now do them all again for the other type
            newSwordType = thisSwordType if originalSwordType==swordTypes[0] else swordTypes[0]
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nNow switching from '{originalSwordType}' to '{newSwordType}' …" )
            SwordResources.setSwordType( newSwordType )
        try:
            doTest( f'SwordResources {SwordResources.SwordType}', SwordResources )
            doTest( f'SwordInstallManager {SwordResources.SwordType}', SwordInstallManager )
            doTest( f'SwordBible {SwordResources.SwordType}', SwordBible )
            doTest( f'SwordModules {SwordResources.SwordType}', SwordModules )
        except KeyboardInterrupt: interrupted=True; return
        except NameError as err:
            if "'Sword' is not defined" in str(e):
                print( f"{SwordResources.SwordType} import failed!" )
                failures.append( f"{SwordResources.SwordType} import" )
                failureDetails.append( f"{SwordResources.SwordType}: {formatFailureDetails( err )}" )
            else:
                print( f"{SwordResources.SwordType} failed!" )
                failures.append( SwordResources.SwordType )
                failureDetails.append( f"{SwordResources.SwordType}: {formatFailureDetails( err )}" )
    SwordResources.setSwordType( originalSwordType ) # Put it back again

    moduleName = 'NoisyReplaceFunctions'
    try:
        from BibleOrgSys.Misc import NoisyReplaceFunctions
        doTest( moduleName, NoisyReplaceFunctions )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'USFMBookCompare'
    try:
        from BibleOrgSys.Misc import USFMBookCompare
        doTest( moduleName, USFMBookCompare )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'CompareBibles'
    try:
        from BibleOrgSys.Misc import CompareBibles
        doTest( moduleName, CompareBibles )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleDropBoxHelpers'
    try:
        from Extras import BibleDropBoxHelpers
        doTest( moduleName, BibleDropBoxHelpers )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'AnalyseAlignments'
    try:
        from Extras import AnalyseAlignments
        doTest( moduleName, AnalyseAlignments )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'English'
    try:
        from Extras import English
        doTest( moduleName, English )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'ILEXDictionary'
    try:
        from Extras import ILEXDictionary
        doTest( moduleName, ILEXDictionary )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


# In Tests folder
    if includeExtensiveTests:
        moduleName = 'TestMS'
        try:
            import TestMS
            doTest( moduleName, TestMS )
        except KeyboardInterrupt: interrupted=True; return
        except (ImportError, SyntaxError) as err:
            print( f"{moduleName} import failed!" )
            failures.append( f"{moduleName} import" )
            failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


        moduleName = 'TestBib'
        try:
            import TestBib
            doTest( moduleName, TestBib )
        except KeyboardInterrupt: interrupted=True; return
        except (ImportError, SyntaxError) as err:
            print( f"{moduleName} import failed!" )
            failures.append( f"{moduleName} import" )
            failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
        if includeKnownGood:
            if BibleOrgSysGlobals.verbosityLevel > 0 : print( "\n\nTesting: TestBib…" )
            goTime = datetime.now()
            try: TestBib.demo1(); successes.append( "TestBib1" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestBib1 failed!" )
                failures.append( "TestBib1" )
                failureDetails.append( f"TestBib1: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestBib1", goTime ) )
            goTime = datetime.now()
            try: TestBib.demo2(); successes.append( "TestBib2" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestBib2 failed!" )
                failures.append( "TestBib2" )
                failureDetails.append( f"TestBib2: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestBib2", goTime ) )
            goTime = datetime.now()
            try: TestBib.demo3(); successes.append( "TestBib3" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestBib3 failed!" )
                failures.append( "TestBib3" )
                failureDetails.append( f"TestBib3: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestBib3", goTime ) )
            goTime = datetime.now()
            try: TestBib.demo4(); successes.append( "TestBib4" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestBib4 failed!" )
                failures.append( "TestBib4" )
                failureDetails.append( f"TestBib4: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestBib4", goTime ) )
            goTime = datetime.now()
            try: TestBib.demo5(); successes.append( "TestBib5" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestBib5 failed!" )
                failures.append( "TestBib5" )
                failureDetails.append( f"TestBib5: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestBib5", goTime ) )


        moduleName = 'TestHaiolaExports'
        try:
            import TestHaiolaExports
        except KeyboardInterrupt: interrupted=True; return
        except (ImportError, SyntaxError) as err:
            print( f"{moduleName} import failed!" )
            failures.append( f"{moduleName} import" )
            failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
        if includeKnownGood:
            if BibleOrgSysGlobals.verbosityLevel > 0 : print( "\n\nTesting: TestHaiolaExports…" )
            goTime = datetime.now()
            try: TestHaiolaExports.demo1(); successes.append( "TestHaiolaExports1" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestHaiolaExports1 failed!" )
                failures.append( "TestHaiolaExports1" )
                failureDetails.append( f"TestHaiolaExports1: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestHaiolaExports1", goTime ) )
            goTime = datetime.now()
            try: TestHaiolaExports.demo2(); successes.append( "TestHaiolaExports2" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestHaiolaExports2 failed!" )
                failures.append( "TestHaiolaExports2" )
                failureDetails.append( f"TestHaiolaExports2: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestHaiolaExports2", goTime ) )
            goTime = datetime.now()
            try: TestHaiolaExports.demo3(); successes.append( "TestHaiolaExports3" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestHaiolaExports3 failed!" )
                failures.append( "TestHaiolaExports3" )
                failureDetails.append( f"TestHaiolaExports3: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestHaiolaExports3", goTime ) )
            goTime = datetime.now()
            try: TestHaiolaExports.demo4(); successes.append( "TestHaiolaExports4" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestHaiolaExports4 failed!" )
                failures.append( "TestHaiolaExports4" )
                failureDetails.append( f"TestHaiolaExports4: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestHaiolaExports4", goTime ) )


        moduleName = 'TestBDBSubmissions'
        try:
            import TestBDBSubmissions
        except KeyboardInterrupt: interrupted=True; return
        except (ImportError, SyntaxError) as err:
            print( f"{moduleName} import failed!" )
            failures.append( f"{moduleName} import" )
            failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
        if includeKnownGood:
            if BibleOrgSysGlobals.verbosityLevel > 0 : print( "\n\nTesting: TestBDBSubmissions…" )
            goTime = datetime.now()
            try: TestBDBSubmissions.demo1(); successes.append( "TestBDBSubmissions1" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestBDBSubmissions1 failed!" )
                failures.append( "TestBDBSubmissions1" )
                failureDetails.append( f"TestBDBSubmissions1: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestBDBSubmissions1", goTime ) )
            goTime = datetime.now()
            try: TestBDBSubmissions.demo2(); successes.append( "TestBDBSubmissions2" )
            except KeyboardInterrupt: interrupted=True; return
            except Exception as err:
                print( "TestBDBSubmissions2 failed!" )
                failures.append( "TestBDBSubmissions2" )
                failureDetails.append( f"TestBDBSubmissions2: {formatFailureDetails( err )}" )
            times.append( getElapsedTime( "TestBDBSubmissions2", goTime ) )



    # And the actual interactive programs (which have a main() function but we just run the demo() function)
    # In Apps folder
    sys.path.insert( 0, '../BibleOrgSys/Apps/' )

    moduleName = 'CreateDistributableResources'
    try:
        import CreateDistributableResources
        doTest( moduleName, CreateDistributableResources )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )
    moduleName = 'CreatePrivateResources'
    try:
        import CreatePrivateResources
        doTest( moduleName, CreatePrivateResources )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'Scrape'
    try:
        import Scrape
        doTest( moduleName, Scrape )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'DisplayReferences'
    try:
        import DisplayReferences
        doTest( moduleName, DisplayReferences )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    moduleName = 'Interlinearizer'
    try:
        import Interlinearizer
        doTest( moduleName, Interlinearizer )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    #if not BibleOrgSysGlobals.commandLineArguments.auto: # Don't run these ones which have a GUI
    moduleName = 'InterlinearizerApp'
    try:
        import InterlinearizerApp
        doTest( moduleName, InterlinearizerApp )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    # Biblelator
    ############
    sys.path.insert( 0, '../Biblelator/' )

    # Biblelator programs
    moduleName = 'Biblelator'
    try:
        from Biblelator import Biblelator
        if includeGIUs:
            doTest( moduleName, Biblelator )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BiblelatorGlobals'
    try:
        from Biblelator import BiblelatorGlobals
        if includeGIUs:
            doTest( moduleName, BiblelatorGlobals )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    # Biblelator Apps
    moduleName = 'SwordManager'
    try:
        from Biblelator.Apps import SwordManager
        if includeGIUs:
            doTest( moduleName, SwordManager )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BOSManager'
    try:
        from Biblelator.Apps import BOSManager
        if includeGIUs:
            doTest( moduleName, BOSManager )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BiblelatorSettingsEditor'
    try:
        from Biblelator.Apps import BiblelatorSettingsEditor
        if includeGIUs:
            doTest( moduleName, BiblelatorSettingsEditor )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'FRepEx'
    try:
        from Biblelator.Apps import FRepEx
        if includeGIUs:
            doTest( moduleName, FRepEx )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    # Biblelator Dialogs
    moduleName = 'About'
    try:
        from Biblelator.Dialogs import About
        if includeGIUs:
            doTest( moduleName, About )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BiblelatorDialogs'
    try:
        from Biblelator.Dialogs import BiblelatorDialogs
        if includeGIUs:
            doTest( moduleName, BiblelatorDialogs )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BiblelatorSimpleDialogs'
    try:
        from Biblelator.Dialogs import BiblelatorSimpleDialogs
        if includeGIUs:
            doTest( moduleName, BiblelatorSimpleDialogs )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'Help'
    try:
        from Biblelator.Dialogs import Help
        if includeGIUs:
            doTest( moduleName, Help )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'ModalDialog'
    try:
        from Biblelator.Dialogs import ModalDialog
        if includeGIUs:
            doTest( moduleName, ModalDialog )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    # Biblelator Helpers
    moduleName = 'AutocompleteFunctions'
    try:
        from Biblelator.Helpers import AutocompleteFunctions
        if includeGIUs:
            doTest( moduleName, AutocompleteFunctions )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'AutocorrectFunctions'
    try:
        from Biblelator.Helpers import AutocorrectFunctions
        if includeGIUs:
            doTest( moduleName, AutocorrectFunctions )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BiblelatorHelpers'
    try:
        from Biblelator.Helpers import BiblelatorHelpers
        if includeGIUs:
            doTest( moduleName, BiblelatorHelpers )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'SpellChecking'
    try:
        from Biblelator.Helpers import SpellChecking
        if includeGIUs:
            doTest( moduleName, SpellChecking )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    # Biblelator Settings
    moduleName = 'BiblelatorSettingsFunctions'
    try:
        from Biblelator.Settings import BiblelatorSettingsFunctions
        if includeGIUs:
            doTest( moduleName, BiblelatorSettingsFunctions )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'Settings'
    try:
        from Biblelator.Settings import Settings
        if includeGIUs:
            doTest( moduleName, Settings )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )


    # Biblelator Windows
    moduleName = 'BibleNotesWindow'
    try:
        from Biblelator.Windows import BibleNotesWindow
        if includeGIUs:
            doTest( moduleName, BibleNotesWindow )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleReferenceCollection'
    try:
        from Biblelator.Windows import BibleReferenceCollection
        if includeGIUs:
            doTest( moduleName, BibleReferenceCollection )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleResourceCollection'
    try:
        from Biblelator.Windows import BibleResourceCollection
        if includeGIUs:
            doTest( moduleName, BibleResourceCollection )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'BibleResourceWindows'
    try:
        from Biblelator.Windows import BibleResourceWindows
        if includeGIUs:
            doTest( moduleName, BibleResourceWindows )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'ChildWindows'
    try:
        from Biblelator.Windows import ChildWindows
        if includeGIUs:
            doTest( moduleName, ChildWindows )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'ESFMEditWindow'
    try:
        from Biblelator.Windows import ESFMEditWindow
        if includeGIUs:
            doTest( moduleName, ESFMEditWindow )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'LexiconResourceWindows'
    try:
        from Biblelator.Windows import LexiconResourceWindows
        if includeGIUs:
            doTest( moduleName, LexiconResourceWindows )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'TextBoxes'
    try:
        from Biblelator.Windows import TextBoxes
        if includeGIUs:
            doTest( moduleName, TextBoxes )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'TextEditWindow'
    try:
        from Biblelator.Windows import TextEditWindow
        if includeGIUs:
            doTest( moduleName, TextEditWindow )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'TSVEditWindow'
    try:
        from Biblelator.Windows import TSVEditWindow
        if includeGIUs:
            doTest( moduleName, TSVEditWindow )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

    moduleName = 'USFMEditWindow'
    try:
        from Biblelator.Windows import USFMEditWindow
        if includeGIUs:
            doTest( moduleName, USFMEditWindow )
    except KeyboardInterrupt: interrupted=True; return
    except (ImportError, SyntaxError) as err:
        print( f"{moduleName} import failed!" )
        failures.append( f"{moduleName} import" )
        failureDetails.append( f"{moduleName}: {formatFailureDetails( err )}" )

# end of doAll


def main():
    """
    Short program to demonstrate/test the above class(es).

    Note that the debug flag, etc. can also be set externally, but that's their problem.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    with open( resultFilepath, 'wt', encoding='utf-8' ) as myFile: myFile.write( PROGRAM_NAME_VERSION + '\n' )

    if 1 or 'win' in sys.platform or BibleOrgSysGlobals.debugFlag:
        publishResultLine( f"  Platform is {sys.platform}" ) # e.g., 'linux, or 'win32' for my Windows-10 (64-bit)
        publishResultLine( f"    OS name is {os.name}" ) # e.g., 'posix', or 'nt' for my Windows-10
        if sys.platform == 'linux': publishResultLine( f"OS uname is {os.uname()}" ) # gives about five fields
        import locale
        publishResultLine( f"  default locale is {locale.getdefaultlocale()}" ) # ('en_NZ', 'cp1252') for my Windows-10
        publishResultLine( f"    preferredEncoding is {locale.getpreferredencoding()}" ) # cp1252 for my Windows-10
        publishResultLine( f"Running Python {sys.version}" )


    global interrupted
    interrupted = False


    if testDefault: # Use the default settings
        BibleOrgSysGlobals.setStrictCheckingFlag( False )
        failuresDefault, failureDetailsDefault, successesDefault, timesDefault = [], [], [], []
        doAll( 'Default', failuresDefault, failureDetailsDefault, successesDefault, timesDefault )

    if testVerbose: # Add the verbose flag
        # Does testing of the extra print statements
        saveVerbosityString = BibleOrgSysGlobals.verbosityString
        BibleOrgSysGlobals.setVerbosity( 'Verbose' )
        failuresVerbose, failureDetailsVerbose, successesVerbose, timesVerbose = [], [], [], []
        doAll( 'Verbose', failuresVerbose, failureDetailsVerbose, successesVerbose, timesVerbose )
        BibleOrgSysGlobals.setVerbosity( saveVerbosityString ) # restore it

    #if testStrict: # Add the strict flag
        ## Does stricter test of the data inputs
        #BibleOrgSysGlobals.setStrictCheckingFlag( True )
        #failuresStrict, successesStrict, timesStrict = [], [], [], []
        #doAll( 'Strict', failuresStrict, successesStrict, timesStrict )

    #if testStrictExport: # Add the export flag (with strict flag)
        ## Tests all the export routines
        #BibleOrgSysGlobals.setStrictCheckingFlag( True )
        #BibleOrgSysGlobals.commandLineArguments.export = True
        #failuresExport, successesExport, timesExport = [], [], [], []
        #doAll( 'StrictExport', failuresExport, successesExport, timesExport )

    #if testStrictExportLogging: # Add the error logging flag (with strict export flags)
        ## Tests more of the logging statements
        #BibleOrgSysGlobals.setStrictCheckingFlag( True )
        #BibleOrgSysGlobals.commandLineArguments.export = True,
        #failuresLogging, successesLogging, timesLogging = [], [], [], []
        #doAll( 'StrictExportLogging', failuresLogging, successesLogging, timesLogging )

    #if testStrictExportVerbose and BibleOrgSysGlobals.verbosityString!='Verbose': # already
        ## Add the verbose flag (with strict export logging flags)
        ##   Does more testing of print statements, etc.
        #BibleOrgSysGlobals.setStrictCheckingFlag( True )
        #saveVerbosityString = BibleOrgSysGlobals.verbosityString
        #BibleOrgSysGlobals.setVerbosity( 'Verbose' )
        #BibleOrgSysGlobals.commandLineArguments.export = True
        #failuresVerbose, successesVerbose, timesVerbose = [], [], [], []
        #doAll( 'StrictExportVerbose', failuresVerbose, successesVerbose, timesVerbose )
        #BibleOrgSysGlobals.setVerbosity( saveVerbosityString ) # restore it

    if testStrictVerboseDebug:
        BibleOrgSysGlobals.setStrictCheckingFlag( True )
        saveVerbosityString = BibleOrgSysGlobals.verbosityString
        BibleOrgSysGlobals.setVerbosity( 'Verbose' )
        #BibleOrgSysGlobals.commandLineArguments.export = False
        BibleOrgSysGlobals.debugFlag = True
        failuresStrictVerboseDebug, failureDetailsStrictVerboseDebug, successesStrictVerboseDebug, timesStrictVerboseDebug = [], [], [], []
        doAll( 'StrictExportVerbose', failuresStrictVerboseDebug, failureDetailsStrictVerboseDebug, successesStrictVerboseDebug, timesStrictVerboseDebug )
        BibleOrgSysGlobals.setVerbosity( saveVerbosityString ) # restore it

    if testStrictVerboseDebugExport:
        #if not BibleOrgSysGlobals.debugFlag: # already
        # Add the debug flag (with strict export verbose flags)
        #   Does more assert testing, etc.
        BibleOrgSysGlobals.setStrictCheckingFlag( True )
        saveVerbosityString = BibleOrgSysGlobals.verbosityString
        BibleOrgSysGlobals.setVerbosity( 'Verbose' )
        #BibleOrgSysGlobals.commandLineArguments.warnings = True # No advantage -- just slows things down
        BibleOrgSysGlobals.commandLineArguments.export = True
        BibleOrgSysGlobals.debugFlag = True
        failuresStrictVerboseDebugExport, failureDetailsStrictVerboseDebugExport, successesStrictVerboseDebugExport, timesStrictVerboseDebugExport = [], [], [], []
        doAll( 'StrictExportVerboseDebug', failuresStrictVerboseDebugExport, failureDetailsStrictVerboseDebugExport, successesStrictVerboseDebugExport, timesStrictVerboseDebugExport )
        BibleOrgSysGlobals.setVerbosity( saveVerbosityString ) # restore it


    # Display our summary results
    if interrupted:
        publishResultLine( "\n\nWe were interrupted and the test didn't run until completion!!!" )

    if testDefault:
        if failuresDefault:
            publishResultLine( f"\n\nHad {len(failuresDefault)} default mode failures: {sorted(failuresDefault)}" )
            publishResultLine( f"  Details: {sorted(failureDetailsDefault)}" )
        else:
            publishResultLine( "\n\nAll default mode tests succeeded." )
        if BibleOrgSysGlobals.commandLineArguments.passes or BibleOrgSysGlobals.verbosityLevel > 2:
            publishResultLine( f"Had {len(successesDefault)} default mode successes: {sorted(successesDefault)}" )
        formatAndPublish( timesDefault )

    if testVerbose:
        if failuresVerbose:
            publishResultLine( f"\n\nHad {len(failuresVerbose)} verbose mode failures: {sorted(failuresVerbose)}" )
            publishResultLine( f"  Details: {sorted(failureDetailsVerbose)}" )
        else:
            publishResultLine( "\n\nAll verbose mode tests succeeded." )
        if BibleOrgSysGlobals.commandLineArguments.passes or BibleOrgSysGlobals.verbosityLevel > 2:
            publishResultLine( f"Had {len(successesVerbose)} verbose mode successes: {sorted(successesVerbose)}" )
        formatAndPublish( timesVerbose )

    #if testStrict:
        #if failuresStrict:
            #publishResultLine( "\n\nHad {} strict mode failures: {}".format( len(failuresStrict), sorted(failuresStrict) ) )
        #else:
            #publishResultLine( "\n\nAll strict mode tests succeeded." )
        #if BibleOrgSysGlobals.commandLineArguments.passes or BibleOrgSysGlobals.verbosityLevel > 2:
            #publishResultLine( "Had {} strict mode successes: {}".format( len(successesStrict), sorted(successesStrict) ) )
        #formatAndPublish( timesStrict )

    #if testStrictExport:
        #if failuresExport:
            #publishResultLine( "\n\nHad {} strict export mode failures: {}".format( len(failuresExport), sorted(failuresExport) ) )
        #else:
            #publishResultLine( "\n\nAll strict export mode tests succeeded." )
        #if BibleOrgSysGlobals.commandLineArguments.passes or BibleOrgSysGlobals.verbosityLevel > 2:
            #publishResultLine( "Had {} strict export mode successes: {}".format( len(successesExport), sorted(successesExport) ) )
        #formatAndPublish( timesExport )

    #if testStrictExportLogging:
        #if failuresLogging:
            #publishResultLine( "\n\nHad {} strict export logging mode failures: {}".format( len(failuresLogging), sorted(failuresLogging) ) )
        #else:
            #publishResultLine( "\n\nAll strict export logging mode tests succeeded." )
        #if BibleOrgSysGlobals.commandLineArguments.passes or BibleOrgSysGlobals.verbosityLevel > 2:
            #publishResultLine( "Had {} strict export logging mode successes: {}".format( len(successesLogging), sorted(successesLogging) ) )
        #formatAndPublish( timesLogging )

    #if testStrictExportVerbose:
        #if failuresVerbose:
            #publishResultLine( "\n\nHad {} strict export verbose mode failures: {}".format( len(failuresVerbose), sorted(failuresVerbose) ) )
        #else:
            #publishResultLine( "\n\nAll strict export verbose mode tests succeeded." )
        #if BibleOrgSysGlobals.commandLineArguments.passes or BibleOrgSysGlobals.verbosityLevel > 2:
            #publishResultLine( "Had {} strict export verbose mode successes: {}".format( len(successesVerbose), sorted(successesVerbose) ) )
        #formatAndPublish( timesVerbose )

    if testStrictVerboseDebug:
        if failuresStrictVerboseDebug:
            publishResultLine( f"\n\nHad {len(failuresStrictVerboseDebug)} strict verbose debug mode failures: {sorted(failuresStrictVerboseDebug)}" )
            publishResultLine( f"  Details: {sorted(failureDetailsStrictVerboseDebug)}" )
        else:
            publishResultLine( "\n\nAll strict verbose debug mode tests succeeded." )
        if BibleOrgSysGlobals.commandLineArguments.passes or BibleOrgSysGlobals.verbosityLevel > 2:
            publishResultLine( f"Had {len(successesStrictVerboseDebug)} strict verbose debug mode successes: {sorted(successesStrictVerboseDebug)}" )
        formatAndPublish( timesStrictVerboseDebug )

    if testStrictVerboseDebugExport:
        if failuresStrictVerboseDebugExport:
            publishResultLine( f"\n\nHad {len(failuresStrictVerboseDebugExport)} strict export verbose debug mode failures: {sorted(failuresStrictVerboseDebugExport)}" )
            publishResultLine( f"  Details: {sorted(failureDetailsStrictVerboseDebugExport)}" )
        else:
            publishResultLine( "\n\nAll strict verbose debug export mode tests succeeded." )
        if BibleOrgSysGlobals.commandLineArguments.passes or BibleOrgSysGlobals.verbosityLevel > 2:
            publishResultLine( f"Had {len(successesStrictVerboseDebugExport)} strict verbose debug export mode successes: {sorted(successesStrictVerboseDebugExport)}" )
        formatAndPublish( timesStrictVerboseDebugExport )
# end of main

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    # Add our custom parameters
    #parser.add_argument("-a", "--automatic", action="store_true", dest="auto", default=False, help="only run tests which don't require operator intervention")
    parser.add_argument("-t", "--times", action="store_true", dest="times", default=False, help="print list of times to run each module")
    parser.add_argument("-p", "--passes", action="store_true", dest="passes", default=False, help="print list of passes (as well as module failures)")
    # The following are required by Interlinearizer.py
    parser.add_argument("-g", "--greek", action="store_true", dest="greekMode", default=False, help="operate in Greek mode")
    parser.add_argument("-j", "--hebrew", action="store_true", dest="hebrewMode", default=False, help="operate in Hebrew mode")
    # The following are required by DisplayReferences.py
    parser.add_argument( "-b", "--book", metavar="BBB", dest="book", default=False, help="set the default book (to 3-letter book reference code)" )
    parser.add_argument( "-r", "--reference", metavar="BCVRef", dest="reference", default=False, help="set the default reference (using BBB.C:V)" )
    parser.add_argument( "-u", "--usx", action="store_true", dest="usx", default=False, help="use USX version (instead of USFM) if it exists" )
    parser.add_argument( "-o", "--other", action="store_true", dest="other", default=False, help="use other version (instead of USFM) if it exists" )
    parser.add_argument( "-f", "--folder", metavar="FOLDER", dest="folder", default=False, help="use the version in this folder (instead of built-in versions)" )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    main()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of DemoTests.py
