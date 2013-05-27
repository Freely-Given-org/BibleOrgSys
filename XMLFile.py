#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# XMLFile.py
#   Last modified: 2013-05-27 by RJH (also update versionString below)
#
# Module handling simple XML files
#
# Copyright (C) 2013 Robert Hunt
# Author: Robert Hunt <robert316@users.sourceforge.net>
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

progName = "XML file handler"
versionString = "0.01"


import logging, os, sys, subprocess
from gettext import gettext as _
from xml.etree.ElementTree import ElementTree
import urllib.request

import Globals


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
            assert( isinstance( self.schema, str ) )
            if self.schema.lower().startswith( 'http:' ):
                self.schemaURL = self.schema

        self.validatedByLoading = self.validatedWithLint = None
        self.tree = None # Will hold the XML data

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "XMLFile: File '{}' is unreadable".format( self.sourceFilepath ) )
        if self.schemaFilepath and not os.access( self.schemaFilepath, os.R_OK ):
            print( "XMLFile: Schema file '{}' is unreadable".format( self.schemaFilepath ) )
        if self.schemaURL:
            try:
                resp = urllib.request.urlopen( self.schemaURL )
                data = resp.read() # a bytes object
                text = data.decode('utf-8') # a string
            except:
                print( "XMLFile: Schema file '{}' is not downloadable".format( self.schemaURL ) )
    # end of XMLFile.__init__

    def __str__( self ):
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "XML file object"
        if Globals.debugFlag or Globals.verbosityLevel>2: result += ' v' + versionString
        if self.sourceFilename: result += ('\n' if result else '') + "  Source filename: " + self.sourceFilename
        if self.sourceFolder: result += ('\n' if result else '') + "  Source folder: " + self.sourceFolder
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

        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )
        try:
            self.tree = ElementTree().parse( self.sourceFilepath )
            assert( len ( self.tree ) ) # Fail here if we didn't load anything at all
            if Globals.verbosityLevel > 2: print( "  ElementTree loaded the xml file {}.".format( self.sourceFilepath ) )
            self.validatedByLoading = True
        except:
            errorString = sys.exc_info()[1]
            if Globals.verbosityLevel > 2: print( "  ElementTree failed loading the xml file {}: '{}'.".format( self.sourceFilepath, errorString ) )
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
            checkProgramOutputString = checkProgramOutputBytes.decode( encoding="utf-8", errors="replace" )
        if checkProgramErrorOutputBytes:
            checkProgramErrorOutputString = checkProgramErrorOutputBytes.decode( encoding="utf-8", errors="replace" )

        if checkProcess.returncode != 0:
            if Globals.verbosityLevel > 1: print( "  WARNING: xmllint gave an error on the {} XML file: {} = {}" \
                            .format( self.sourceFilepath, checkProcess.returncode, xmllintError[checkProcess.returncode] ) )
            self.validatedWithLint = False
        else:
            if Globals.verbosityLevel > 2: print( "  xmllint validated the xml file {}.".format( self.sourceFilepath ) )
            self.validatedWithLint = True

        if Globals.debugFlag: print( "cPOS  = '{}'".format( checkProgramOutputString ) )
        if Globals.debugFlag: print( "cPEOS = '{}'".format( checkProgramErrorOutputString ) )
        return self.validatedWithLint, checkProgramOutputString, checkProgramErrorOutputString
    # end of XMLFile.validateWithLint

    def validateAll( self ):
        return self.validateByLoading()[0] and self.validateWithLint()[0] # No returned error messages
# end of class XMLFile


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    AutoProcessesFolder = "../../"
    osisSchemaHTTP = 'http://www.bibletechnologies.net/osisCore.2.1.1.xsd'
    osisSchemaFile = os.path.join( AutoProcessesFolder, 'sword-tools/thml2osis/xslt/tests/osisCore.2.1.1.xsd' )
    usxSchemaFile = os.path.join( AutoProcessesFolder, 'VariousScripts/usx 1.rng' )

    def doTest( folder, filenameList, schema=None ):
        for testFilename in filenameList:
            #testFilepath = os.path.join( folder, testFilename )
            #if Globals.verbosityLevel > 0: print( "\n  Test filepath is '{}'".format( testFilepath ) )

            # Demonstrate the XML file class
            #xf = XMLFile( testFilepath, schema=schema )
            xf = XMLFile( testFilename, folder, schema=schema )
            xf.validateByLoading()
            xf.validateWithLint()
            #print( xf.validateAll() )
            print( xf )
    # end of doTest

    if 0: # Test some OpenSong Bibles
        testFolder = "../../../../../Data/Work/Bibles//OpenSong Bibles/"
        single = ( "KJV.xmm", )
        good = ( "KJV.xmm", "AMP.xmm", "Chinese_SU.xmm", "Contemporary English Version.xmm", "ESV", "Italiano", "MKJV", \
            "MSG.xmm", "NASB.xmm", "NIV", "NKJV.xmm", "NLT", "telugu.xmm", )
        nonEnglish = ( "BIBLIA warszawska", "Chinese Union Version Simplified.txt", "hun_karoli", "KNV_HU", "LBLA.xmm", \
            "Nowe Przymierze", "NVI.xmm", "NVI_PT", "PRT-IBS.xmm", "RV1960", "SVL.xmm", "UJPROT_HU", "vdc", \
            "Vietnamese Bible.xmm", )
        bad = ( "EPS99", )
        allOfThem = good + nonEnglish + bad
        if Globals.verbosityLevel > 1: print( "\n\nDemonstrating the XMLFile class with OpenSong Bibles..." )
        doTest( testFolder, allOfThem )

    if 1: # Test some OSIS Bibles
        testFolder = "../../../../../Data/Work/Bibles/Formats/OSIS/kjvxml from DMSmith/"
        testNames = ( "kjv.xml", "kjvfull.xml", "kjvlite.xml", )
        if Globals.verbosityLevel > 1: print( "\n\nDemonstrating the XMLFile class with OSIS Bibles (no schema)..." )
        doTest( testFolder, testNames )
        if Globals.verbosityLevel > 1: print( "\n\nDemonstrating the XMLFile class with OSIS Bibles (file schema)..." )
        doTest( testFolder, testNames, schema=osisSchemaFile )
        if Globals.verbosityLevel > 1: print( "\n\nDemonstrating the XMLFile class with OSIS Bibles (web schema)..." )
        doTest( testFolder, (testNames[0],), schema=osisSchemaHTTP )
# end of demo

if __name__ == '__main__':
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    demo()
# end of XMLFile.py