#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# XMLFile.py
#
# Module handling simple XML files
#
# Copyright (C) 2013-2022 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module for handling XML files using a high-performance Rust backend.
"""
import logging
import os, sys
from pathlib import Path
from xml.etree.ElementTree import ElementTree

from bible_organisational_system import validateWellFormedness, validateWithLint
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2026-05-17' # by RJH (Rust conversion)
SHORT_PROGRAM_NAME = "XMLFile"
PROGRAM_NAME = "XML file handler"
PROGRAM_VERSION = '0.10'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


xmllintError = ("No error", "Unclassified", "Error in DTD", "Validation error", "Validation error", "Error in schema compilation", "Error writing output", "Error in pattern", "Error in reader registration", "Out of memory")



class XMLFile():
    """
    Class for reading and validating XML files.
    Now powered by Rust.
    """
    def __init__( self, sourceFilename, sourceFolder=None, schema=None ) -> None:
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
            if self.schema.lower().startswith( 'http:' ) or self.schema.lower().startswith( 'https:' ):
                self.schemaURL = self.schema
            else:
                self.schemaFilepath = self.schema

        self.validatedByLoading = self.validatedWithLint = None
        self.XMLTree = None # Will hold the XML data

        # Do a preliminary check on the readability of our schema file
        if not os.access( self.sourceFilepath, os.R_OK ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"XMLFile: File {self.sourceFilepath!r} is unreadable" )
        if self.schemaFilepath and not os.access( self.schemaFilepath, os.R_OK ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"XMLFile: Schema file {self.schemaFilepath!r} is unreadable" )
        # Remote schema check moved to when needed or handled by Rust/requests if needed.
    # end of XMLFile.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "XML file object (Rust-powered)"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        if self.sourceFilename: result += ('\n' if result else '') + "  Source filename: " + self.sourceFilename
        if self.sourceFolder:
            result += ('\n' if result else '') + f"  Source folder: {self.sourceFolder}"
        if self.sourceFilepath: result += ('\n' if result else '') + "  Source filepath: " + self.sourceFilepath
        if self.validatedByLoading is not None: result += ('\n' if result else '') + f"  Validated by loading = {self.validatedByLoading}"
        if self.validatedWithLint is not None:
            result += ('\n' if result else '') + f"  Validated with lint = {self.validatedWithLint}"
            if self.schema: result += ('\n' if result else '') + f"    with schema = {self.schema}"
        return result
    # end of XMLFile.__str__


    def validateByLoading( self ):
        """
        Load the XML tree to see if it gives errors.
        Uses Rust for fast well-formedness check.
        """
        errorString = None

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading {self.sourceFilepath}…" )
        try:
            # Rust check first
            validateWellFormedness(str(self.sourceFilepath))
            # If well-formed, we can load it into Python if needed (for legacy XMLTree access)
            self.XMLTree = ElementTree().parse( self.sourceFilepath )
            self.validatedByLoading = True
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Successfully loaded and validated {self.sourceFilepath}." )
        except Exception as err:
            errorString = str(err)
            logging.error( f"validateByLoading failed for {self.sourceFilepath}: {errorString}" )
            self.validatedByLoading = False

        return self.validatedByLoading, errorString
    # end of XMLFile.validateByLoading


    def validateWithLint( self ):
        """
        Runs the xmllint program to validate the XML file (via Rust backend).
        """
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Running xmllint validation on {self.sourceFilepath}…" )
        
        schema = self.schemaURL or self.schemaFilepath
        success, stdout, stderr, code = validateWithLint(str(self.sourceFilepath), schema)

        self.validatedWithLint = success
        if not success:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  WARNING: xmllint gave an error on {self.sourceFilepath}: {code} = {xmllintError[code] if code is not None and code < len(xmllintError) else 'Unknown'}" )
        else:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  xmllint validated {self.sourceFilepath}." )

        return self.validatedWithLint, stdout, stderr
    # end of XMLFile.validateWithLint

    def validateAll( self ):
        return self.validateByLoading()[0] and self.validateWithLint()[0] # No returned error messages
    # end of XMLFile.validateAll
# end of class XMLFile



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    AutoProcessesFolder = "../../"
    osisSchemaHTTP = 'http://ebible.org/osisCore.2.1.1.xsd'
    # osisSchemaFile = os.path.join( AutoProcessesFolder, 'sword-tools/thml2osis/xslt/tests/osisCore.2.1.1.xsd' )
    # usxSchemaFile = os.path.join( AutoProcessesFolder, 'VariousScripts/usx 1.rng' )

    def doTest( folder, filenameList, schema=None ):
        for testFilename in filenameList:
            xf = XMLFile( testFilename, folder, schema=schema )
            if os.access( xf.sourceFilepath, os.R_OK ):
                xf.validateByLoading()
                xf.validateWithLint()
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, xf )
            else:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Skipping {xf.sourceFilepath} (not found)" )
            break
    # end of doTest

    if 1: # Test some OpenSong Bibles
        testFolder = Path( '/srv/Bibles//OpenSong Bibles/' )
        good = ( "KJV.xmm", "AMP.xmm", )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\n\nDemonstrating the XMLFile class with OpenSong Bibles…" )
        doTest( testFolder, good )

    if 1: # Test some OSIS Bibles
        testFolder = Path( '/srv/Bibles/Formats/OSIS/kjvxml from DMSmith/' )
        testNames = ( "kjv.xml", )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\n\nDemonstrating the XMLFile class with OSIS Bibles (no schema)…" )
        doTest( testFolder, testNames )
        # vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\n\nDemonstrating the XMLFile class with OSIS Bibles (web schema)…" )
        # doTest( testFolder, (testNames[0],), schema=osisSchemaHTTP )
# end of XMLFile.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of XMLFile.py
