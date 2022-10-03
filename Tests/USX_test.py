#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USX_test.py
#
# App to create zipped PickledBible for distributable Bible/commentary resources.
#
# Copyright (C) 2022 Robert Hunt
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
App to create zipped PickledBible for distributable Bible/commentary resources,
    e.g., Open Scriptures Hebrew Bible,
            WEB and related versions,
            older public domain Bible versions.

Made to be run from the BibleOrgSys folder, i.e.,
    Apps/USX_test.py

CHANGELOG:
"""
from gettext import gettext as _
from typing import Tuple
import os
from pathlib import Path
import multiprocessing
import subprocess
import logging

# BibleOrgSys imports
if __name__ == '__main__':
    import sys
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.OriginalLanguages.HebrewWLCBible import OSISHebrewWLCBible
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Formats.USFMBible import USFMBible
from BibleOrgSys.Formats.PTX8Bible import PTX8Bible
from BibleOrgSys.Formats.PickledBible import PickledBible, ZIPPED_PICKLE_FILENAME_END

from Extras.BibleDropBoxHelpers import submitBDBFolder


LAST_MODIFIED_DATE = '2022-08-01' # by RJH
SHORT_PROGRAM_NAME = "USX_test"
PROGRAM_NAME = "Test USX exports vs Paratext"
PROGRAM_VERSION = '0.50'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
PROGRAM_NAME_VERSION_DATE = f'{PROGRAM_NAME_VERSION} {_("last modified")} {LAST_MODIFIED_DATE}'

DEBUGGING_THIS_MODULE = False


SCHEMA_FILEPATH = os.path.abspath( os.path.join( os.path.dirname(__file__), '../ExternalSchemas/DerivedFiles/usx_3.0.7.rng' ) )

BOS_USX3_EXPORT_FOLDERPATH = Path( '/home/robert/BibleOrgSysData/BOSOutputFiles/BOS_USX3_Export/USX3Files/' )


def validateXML( usx_filepath: Path | str ) -> Tuple:
    """
    Validate the USX file against the schema.

    Returns a 3-tuple consisting of
        a result code (0=success)
        and two strings containing the program output and error output.
    """
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Running validateXML() on USX file {usx_filepath}…" )

    # Not sure if this will work on most Linux systems -- certainly won't work on other operating systems
    schemaFilepath = str(SCHEMA_FILEPATH) # In case it's a Path object
    parameters = [ '/usr/bin/xmllint', '--noout', '--relaxng' if '.rng' in schemaFilepath else '--schema', schemaFilepath, str(usx_filepath) ]
    try:
        checkProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        checkProgramOutputBytes, checkProgramErrorOutputBytes = checkProcess.communicate()
        returnCode = checkProcess.returncode
    except FileNotFoundError:
        logging.error( "MLWriter.validateXML is unable to open {!r}".format( parameters[0] ) )
        return None
    checkProgramOutputString = checkProgramErrorOutputString = ''
    if checkProgramOutputBytes: checkProgramOutputString = '{}:\n{}'.format( usx_filepath, checkProgramOutputBytes.decode( encoding='utf-8', errors='replace' ) )
    if checkProgramErrorOutputBytes:
        tempString = checkProgramErrorOutputBytes.decode( encoding='utf-8', errors='replace' )
        if tempString.count('\n')>1 or not tempString.endswith('validates\n'):
            checkProgramErrorOutputString = '{}:\n{}'.format( usx_filepath, tempString )
    xmllintError = ("No error", "Unclassified", "Error in DTD", "Validation error", "Validation error", "Error in schema compilation", "Error writing output", "Error in pattern", "Error in reader registration", "Out of memory")
    if returnCode != 0:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  WARNING: xmllint gave an error on the created {usx_filepath} file: {returnCode} = {xmllintError[returnCode]}" )
        if returnCode == 5: # schema error
            logging.critical( "MLWriter.validateXML couldn't read/parse the schema at {}".format( schemaFilepath ) )
            if BibleOrgSysGlobals.debugFlag and (DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag): schema_fault
    else: vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  xmllint validated the xml file {usx_filepath}." )
    return returnCode, checkProgramOutputString, checkProgramErrorOutputString,
# end of USX_test.validateXML


def briefDemo() -> None:
    """
    Create freely-licenced resources which can be distributed with the BOS
        but don't save them in the normal output folder.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )


# end of USX_test.briefDemo

def fullDemo() -> None:
    """
    Create freely-licenced resources which can be distributed with the BOS
        but don't save them in the normal output folder.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

# end of USX_test.fullDemo


def main() -> None:
    """
    Create freely-licenced resources which can be distributed with the BOS.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    for j,(abbrev, USFMInputFolderpath, theirUSXInputFolderpath) in enumerate( (
                ('ASV', Path( '/home/robert/Paratext8Projects/ASV/' ),
                        Path( '/srv/Documents/Paratext9_stuff/PT9_USX_Exports/ASV/' ) ),
                ('MBTV', Path( '/home/robert/Paratext8Projects/MBTV/' ),
                         Path( '/srv/Documents/Paratext9_stuff/PT9_USX_Exports/MBTV/' ) ),
                # We never got ULT to work here because Paratext 9 "Manage books" import (cf. file copy into folder) totally mangled their USFM files
                # ('ULT', Path( '/home/robert/Paratext8Projects/ULT/' ),
                #          Path( '/srv/Documents/Paratext9_stuff/PT9_USX_Exports/ULT/' ) ),
                ('WEB', Path( '/home/robert/Paratext8Projects/engWEB14/' ),
                         Path( '/srv/Documents/Paratext9_stuff/PT9_USX_Exports/engWEB14/' ) ),
                ) ):
        if os.access( USFMInputFolderpath, os.R_OK ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nUSFM {j+1}/ {abbrev}" )
            thisUsfmBible = USFMBible( USFMInputFolderpath, abbrev, encoding='utf-8' )
            thisUsfmBible.abbreviation = abbrev
            if abbrev in ('ULT','UST'): thisUsfmBible.uWencoded = True
            thisUsfmBible.load()
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Gen assumed book name:", repr( thisUsfmBible.getAssumedBookName( 'GEN' ) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Gen long TOC book name:", repr( thisUsfmBible.getLongTOCName( 'GEN' ) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Gen short TOC book name:", repr( thisUsfmBible.getShortTOCName( 'GEN' ) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Gen book abbreviation:", repr( thisUsfmBible.getBooknameAbbreviation( 'GEN' ) ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, thisUsfmBible )

            # print( f"\n{type(thisUsfmBible)} {dir(thisUsfmBible)=}" )
            # print( f"\n{type(thisUsfmBible.books['RUT'])=} {dir(thisUsfmBible.books['RUT'])=}" )
            # print( f"\n{type(thisUsfmBible.books['RUT']._processedLines)=} {dir(thisUsfmBible.books['RUT']._processedLines)=}" )
            # print( f"\n{type(thisUsfmBible.books['RUT']._CVIndex)=} {dir(thisUsfmBible.books['RUT']._CVIndex)=}" )

            if 0: # Extra stuff to display BOS internals that's nothing much to do with USX
                import json
                with open( '_processedLines.txt', 'wt') as f:
                    for IBEobject in thisUsfmBible.books['RUT']._processedLines:
                        f.write( f"{str(IBEobject).replace('InternalBibleEntry object','')}\n" )
                        if IBEobject.extras:
                            f.write( f"  {str(IBEobject.extras).replace(' object:',':')}\n" )
                # with open( '_processedLines.json', 'wt') as f:
                #     json.dump(f, thisUsfmBible.books['RUT']._processedLines.data )
                with open( '_CVIndex.txt', 'wt') as f:
                    for entry in thisUsfmBible.books['RUT']._CVIndex.items():
                        f.write( f"{str(entry).replace(' object:',':')}\n" )
                # with open( '_CVIndex.json', 'wt') as f:
                #     json.dump(f, thisUsfmBible.books['RUT']._CVIndex )
                # with open( '_SectionIndex.txt', 'wt') as f:
                #     for entry in thisUsfmBible.books['RUT']._SectionIndex.items():
                #         f.write( f'{entry}\n' )

            if 0: # Check Psalms index around \ms Book sections (Ps 1, 42, 73, 90, 107)
                # print( f"{thisUsfmBible.books['PSA']._CVIndex[('41','13')]=}" ) # 5600-5613 inclusive
                print( f"PSA 0 {thisUsfmBible.books['PSA']._processedLines[:20]=}" )
                # print( f"{thisUsfmBible.books['PSA']._CVIndex[('42','0')]=}" ) # 5614
                # print( f"{thisUsfmBible.books['PSA']._CVIndex[('42','1')]=}" ) # 5615-5624 inclusive
                print( f"PSA 41 {thisUsfmBible.books['PSA']._processedLines[5600:5620]=}" ) # \ms1 at chapter 42
                # print( f"{thisUsfmBible.books['PSA']._CVIndex[('73','0')]=}" ) # 9901
                print( f"PSA 72 {thisUsfmBible.books['PSA']._processedLines[9894:9910]=}" ) # \ms1 at chapter 73
                # print( f"{thisUsfmBible.books['PSA']._CVIndex[('119','0')]=}" ) # 17513-17516 inclusive
                print( f"PSA 119 {thisUsfmBible.books['PSA']._processedLines[17510:17520]=}" ) # \qc at chapter 119:1
                print( f"PSA 150 {thisUsfmBible.books['PSA']._processedLines[-12:]=}" )

            if BibleOrgSysGlobals.strictCheckingFlag:
                thisUsfmBible.check()
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
                UsfmBErrors = thisUsfmBible.getCheckResults()
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UBErrors )
            thisUsfmBible.toPseudoUSFM()
            thisUsfmBible.toESFM()
            thisUsfmBible.toUSXXML()

            # Now validate and compare them
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Now validating and comparing the reference and our exported {abbrev} USX (XML) files…" )
            for BBB in thisUsfmBible.books:
                Uuu = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
                UUU = Uuu.upper()
                nnn = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSXNumStr( BBB )
                if not nnn:
                    logging.critical( f"Ignoring validation of {BBB=} {Uuu=} {UUU=}-- enable to determine nnn" )
                usx_filename = f'{nnn}{UUU}.usx'

                # Firstly, validate the Paratext export (to make sure that we're not chasing rabbits)
                ParatextFilepath = theirUSXInputFolderpath.joinpath( usx_filename )
                returnCode1, checkProgramOutputString1, checkProgramErrorOutputString1 = validateXML( ParatextFilepath )
                if returnCode1 == 0:
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"validateXML for PT file returned 'success' {checkProgramOutputString1} {checkProgramErrorOutputString1}" )
                else:
                    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"validateXML for PT file returned bad {returnCode1} {checkProgramOutputString1=} {checkProgramErrorOutputString1=}" )

                # Now, validate our export (to make sure that we're not chasing rabbits)
                exportFilepath = BOS_USX3_EXPORT_FOLDERPATH.joinpath( usx_filename )
                returnCode2, checkProgramOutputString2, checkProgramErrorOutputString2 = validateXML( exportFilepath )
                if returnCode2 == 0:
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"validateXML for our file returned 'success' {checkProgramOutputString2} {checkProgramErrorOutputString2}" )
                else:
                    logging.critical( f"validateXML for our USX export file returned bad {returnCode2} {checkProgramOutputString2=} {checkProgramErrorOutputString2=}" )

                if 1 or returnCode1==0 and returnCode2==0: # Now try a line-by-line compare
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Comparing {BBB} USX files…" )
                    result = BibleOrgSysGlobals.fileCompareXML( usx_filename, usx_filename, BOS_USX3_EXPORT_FOLDERPATH, theirUSXInputFolderpath )
                    if result:
                        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  CompareA result for {BBB} was good {result}" )
                    else:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  CompareA result for {BBB} was bad {result}" )
                if result is False:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Comparing {BBB} (USX) files…" )
                    result = BibleOrgSysGlobals.fileCompare( usx_filename, usx_filename, BOS_USX3_EXPORT_FOLDERPATH, theirUSXInputFolderpath, exitCount=1 )
                    if result:
                        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  CompareB result for {BBB} was good {result}" )
                    else:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  CompareB result for {BBB} was bad {result}" )
        else:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, USFM input folder '{USFMInputFolderpath}' is not readable on this computer." )


# end of USX_test.main

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=False )

    main()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of USX_test.py
