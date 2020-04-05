#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# XMLFile.py
#
# Module handling simple XML files
#
# Copyright (C) 2013-2019 Robert Hunt
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
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-22' # by RJH
SHORT_PROGRAM_NAME = "XMLFile"
PROGRAM_NAME = "XML file handler"
PROGRAM_VERSION = '0.04'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


import logging, os, sys, subprocess
from pathlib import Path
from xml.etree.ElementTree import ElementTree, ParseError
import urllib.request

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals


xmllintError = ("No error", "Unclassified", "Error in DTD", "Validation error", "Validation error", "Error in schema compilation", "Error writing output", "Error in pattern", "Error in reader registration", "Out of memory")



class XMLFile():
    """
    Class for reading and validating XML files.
    """
    def __init__( self, sourceFilename, sourceFolder=None, schema=None ):
        """
        Constructor: just sets up the XML Bible file converter object.
        """
        # Now we can set our object variables
        self.sourceFilename, self.sourceFolder, self.schema = sourceFilename, sourceFolder, schema

        # Combine the folder if necessary
        self.sourceFilepath = os.path.join( self.sourceFolder, self.sourceFilename ) if self.sourceFolder else self.sourceFilename

        self.schemaFilepath = self.schemaURL = None
        if self.schema is not None:
            assert isinstance( self.schema, str )
            if self.schema.lower().startswith( 'http:' ):
                self.schemaURL = self.schema

        self.validatedByLoading = self.validatedWithLint = None
        self.XMLTree = None # Will hold the XML data

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "XMLFile: File {!r} is unreadable".format( self.sourceFilepath ) )
        if self.schemaFilepath and not os.access( self.schemaFilepath, os.R_OK ):
            print( "XMLFile: Schema file {!r} is unreadable".format( self.schemaFilepath ) )
        if self.schemaURL:
            try:
                resp = urllib.request.urlopen( self.schemaURL )
            except urllib.error.URLError:
                logging.error( "XMLFile: Schema file {!r} is not downloadable".format( self.schemaURL ) )
                resp = None
            if resp is not None:
                data = resp.read() # a bytes object
                text = data.decode('utf-8') # a string
    # end of XMLFile.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "XML file object"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        if self.sourceFilename: result += ('\n' if result else '') + "  Source filename: " + self.sourceFilename
        if self.sourceFolder:
            result += ('\n' if result else '') + f"  Source folder: {self.sourceFolder}"
        if self.sourceFilepath: result += ('\n' if result else '') + "  Source filepath: " + self.sourceFilepath
        if self.validatedByLoading is not None: result += ('\n' if result else '') + "  Validated by loading = {}".format( self.validatedByLoading )
        if self.validatedWithLint is not None:
            result += ('\n' if result else '') + "  Validated with lint = {}".format( self.validatedWithLint )
            if self.schema: result += ('\n' if result else '') + "    with schema = {}".format( self.schema )
        return result
    # end of XMLFile.__str__


    def validateByLoading( self ):
        """
        Load the XML tree to see if it gives errors
        """
        errorString = None

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )
        try:
            self.XMLTree = ElementTree().parse( self.sourceFilepath )
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  ElementTree loaded the xml file {}.".format( self.sourceFilepath ) )
            self.validatedByLoading = True
        except FileNotFoundError:
            errorString = sys.exc_info()[1]
            logging.error( "validateByLoading: Unable to open {}".format( self.sourceFilepath ) )
            self.validatedByLoading = False
        except ParseError:
            errorString = sys.exc_info()[1]
            logging.error( "  ElementTree failed loading the xml file {}: {!r}.".format( self.sourceFilepath, errorString ) )
            self.validatedByLoading = False

        return self.validatedByLoading, errorString
    # end of XMLFile.validateByLoading


    def validateWithLint( self ):
        """
        On a Linux system, runs the xmllint program to validate the XML file.
        """
        checkProgramOutputString = checkProgramErrorOutputString = None

        parameters = [ '/usr/bin/xmllint', '--noout', self.sourceFilepath ]
        if self.schemaFilepath:
            parameters = [ '/usr/bin/xmllint', '--noout', '--schema', self.schemaFilepath, self.sourceFilepath ]
        checkProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        checkProgramOutputBytes, checkProgramErrorOutputBytes = checkProcess.communicate()

        if checkProgramOutputBytes:
            checkProgramOutputString = checkProgramOutputBytes.decode( encoding='utf-8', errors='replace' )
        if checkProgramErrorOutputBytes:
            checkProgramErrorOutputString = checkProgramErrorOutputBytes.decode( encoding='utf-8', errors='replace' )

        if checkProcess.returncode != 0:
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  WARNING: xmllint gave an error on the {} XML file: {} = {}" \
                            .format( self.sourceFilepath, checkProcess.returncode, xmllintError[checkProcess.returncode] ) )
            self.validatedWithLint = False
        else:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  xmllint validated the xml file {}.".format( self.sourceFilepath ) )
            self.validatedWithLint = True

        if BibleOrgSysGlobals.debugFlag: print( "cPOS  = {!r}".format( checkProgramOutputString ) )
        if BibleOrgSysGlobals.debugFlag: print( "cPEOS = {!r}".format( checkProgramErrorOutputString ) )
        return self.validatedWithLint, checkProgramOutputString, checkProgramErrorOutputString
    # end of XMLFile.validateWithLint

    def validateAll( self ):
        return self.validateByLoading()[0] and self.validateWithLint()[0] # No returned error messages
    # end of XMLFile.validateAll
# end of class XMLFile



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    AutoProcessesFolder = "../../"
    osisSchemaHTTP = 'http://ebible.org/osisCore.2.1.1.xsd'
    osisSchemaFile = os.path.join( AutoProcessesFolder, 'sword-tools/thml2osis/xslt/tests/osisCore.2.1.1.xsd' )
    usxSchemaFile = os.path.join( AutoProcessesFolder, 'VariousScripts/usx 1.rng' )

    def doTest( folder, filenameList, schema=None ):
        for testFilename in filenameList:
            #testFilepath = os.path.join( folder, testFilename )
            #if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n  Test filepath is {!r}".format( testFilepath ) )

            # Demonstrate the XML file class
            #xf = XMLFile( testFilepath, schema=schema )
            xf = XMLFile( testFilename, folder, schema=schema )
            xf.validateByLoading()
            xf.validateWithLint()
            #print( xf.validateAll() )
            print( xf )
    # end of doTest

    if 1: # Test some OpenSong Bibles
        testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles//OpenSong Bibles/' )
        single = ( "KJV.xmm", )
        good = ( "KJV.xmm", "AMP.xmm", "Chinese_SU.xmm", "Contemporary English Version.xmm", "ESV", "Italiano", "MKJV", \
            "MSG.xmm", "NASB.xmm", "NIV", "NKJV.xmm", "NLT", "telugu.xmm", )
        nonEnglish = ( "BIBLIA warszawska", "Chinese Union Version Simplified.txt", "hun_karoli", "KNV_HU", "LBLA.xmm", \
            "Nowe Przymierze", "NVI.xmm", "NVI_PT", "PRT-IBS.xmm", "RV1960", "SVL.xmm", "UJPROT_HU", "vdc", \
            "Vietnamese Bible.xmm", )
        bad = ( "EPS99", )
        allOfThem = good + nonEnglish + bad
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\n\nDemonstrating the XMLFile class with OpenSong Bibles…" )
        doTest( testFolder, allOfThem )

    if 1: # Test some OSIS Bibles
        testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/Formats/OSIS/kjvxml from DMSmith/' )
        testNames = ( "kjv.xml", "kjvfull.xml", "kjvlite.xml", )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\n\nDemonstrating the XMLFile class with OSIS Bibles (no schema)…" )
        doTest( testFolder, testNames )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\n\nDemonstrating the XMLFile class with OSIS Bibles (file schema)…" )
        doTest( testFolder, testNames, schema=osisSchemaFile )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\n\nDemonstrating the XMLFile class with OSIS Bibles (web schema)…" )
        doTest( testFolder, (testNames[0],), schema=osisSchemaHTTP )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of XMLFile.py
