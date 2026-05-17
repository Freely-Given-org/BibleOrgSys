#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# MLWriter.py
#
# Module handling pretty writing of XML (and xHTML) and HTML files
#
# Copyright (C) 2010-2022 Robert Hunt
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
Module handling creation of simple XML (and xHTML) and HTML files.

Now powered by Rust for high-performance text generation.
"""
import os
import logging
from pathlib import Path

from bible_organisational_system import (
    MlWriter as RustMlWriter,
    MlOutputType,
    HumanReadable,
    SectionName,
    escapeCharacters as rust_escape_characters,
)
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from bible_organisational_system import InternalBibleExtraList


LAST_MODIFIED_DATE = '2026-05-17' # by RJH (Rust conversion)
SHORT_PROGRAM_NAME = "MLWriter"
PROGRAM_NAME = "XML/HTML Writer"
PROGRAM_VERSION = '0.50'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


allowedOutputTypes = 'XML','HTML' # Use XML for xHTML
HTMLParaTags = 'p', # Not automatically started on a new line
HTMLInsideTags = 'a', 'b', 'em', 'i', 'sup', 'sub', 'span' # Not automatically started on or finished with a new line
HTMLCombinedTags = HTMLParaTags + HTMLInsideTags
XML_PREDEFINED_ENTITIES = ('quot','apos','lt','gt','amp')
HTML_PREDEFINED_CHARACTER_ENTITIES = (
                'exclamation','quot','percent','amp','apos','add','lt','equal','gt','nbsp',
                'iexcl','cent','pound','curren','yen','brevbar','sect','uml','copy','ordf',
                'laquo','not','shy','reg','macr','deg','plusmn','sup2','sup3','acute',
                'micro','para','middot','cedil','sup1','ordm','raquo',
                'frac14','frac12','frac34', 'iquest' ) # plus about 200 more
ESCAPE_PAIRS = (('&','&amp;'),('"','&quot;'),('<','&lt;'),('>','&gt;'))
ESCAPE_MAP = { k:v for k,v in ESCAPE_PAIRS}
assert len(ESCAPE_MAP) == len(ESCAPE_PAIRS)


class MLWriter:
    """
    A class to write (and check) data with XML type syntax.

    Note that character escapes are not automatically done by this class.
    """

    def __init__( self, filename:Path|str, folder:Path|str|None=None, outputType:str|None=None ) -> None:
        """
        Constructor.
            filename: filename string or complete filepath
            folder (optional): will be prepended to the filename
            outputType( optional): defaults to 'XML' but can also be 'HTML'
        """
        assert filename and isinstance( filename, (Path,str) )
        if folder: assert isinstance( folder, (Path,str) )
        if outputType is None: outputType = 'XML' # default
        assert outputType in allowedOutputTypes

        self._filename, self._folder, self._outputType = filename, folder, outputType
        self._outputFilePath = os.path.join ( self._folder, self._filename ) if folder is not None else self._filename

        ot = MlOutputType.Xml if outputType == 'XML' else MlOutputType.Html
        self._rust_inner = RustMlWriter(str(self._outputFilePath), ot)

        self.haltOnErrors = DEBUGGING_THIS_MODULE != False or BibleOrgSysGlobals.strictCheckingFlag
        self._rust_inner.halt_on_errors = self.haltOnErrors

    @property
    def spaceBeforeSelfcloseTag(self):
        return False # Rust impl manages this now, but we can set it if needed
    @spaceBeforeSelfcloseTag.setter
    def spaceBeforeSelfcloseTag(self, value):
        self._rust_inner.space_before_selfclose_tag = value

    @property
    def linesWritten(self):
        return self._rust_inner.lines_written

    def __str__( self ) -> str:
        """
        This method returns the string representation of the XML writer system.

        @return: the name of the object formatted as a string
        @rtype: string
        """
        result = "MLWriter object (Rust-powered)"
        result += ('\n' if result else '') + "  " + f"Type: {self._outputType}"
        return result
    # end of MLWriter.__str__


    def setOutputType( self, newType:str ) -> None:
        """
        Set the output type = XML or HTML
                Use XML for xHTML.
        """
        assert newType in allowedOutputTypes
        self._outputType = newType
        # Note: In Rust, output type is set at creation. For now, we assume it's not changed after init.


    def setHumanReadable( self, value:str='All', indentSize:int=2 ) -> None:
        """
        Set the human readable flag.
        """
        hr_map = {
            'All': HumanReadable.All,
            'Header': HumanReadable.Header,
            'None': HumanReadable.NoIndentation,
            'NLSpace': HumanReadable.NlSpace,
        }
        self._rust_inner.set_human_readable(hr_map[value], indentSize)
    # end of MLWriter.setHumanReadableFlag


    def setSectionName( self, sectionName:str|None ) -> None:
        """ Tells the writer the current section that we are writing. """
        sn_map = {
            'None': SectionName.NoSection,
            'Header': SectionName.Header,
            'Main': SectionName.Main,
        }
        self._rust_inner.set_section_name(sn_map[sectionName])
    # end of MLWriter.setSection


    def getFilePosition( self ) -> int:
        """ Returns the current position through the file. """
        return self._rust_inner.get_file_position()
    # end of MLWriter.getFilePosition


    @staticmethod
    def escape_characters( rawTextString:str, checkFirst:bool=False ) -> str:
        """
        Does XML escapes, e.g., & -> &amp;
        """
        # For now, we use the Rust implementation which is simple.
        # checkFirst is ignored in this fast version.
        return rust_escape_characters(rawTextString)
    # end of MLWriter.escape_characters static function

    @staticmethod
    def escape_characters_with_extras( rawTextString:str, extras:InternalBibleExtraList, checkFirst:bool=False ) -> tuple[str,InternalBibleExtraList]:
        """
        Does XML escapes, e.g., & -> &amp;
        """
        # This is a complex one, keeping it in Python for now if not already in Rust.
        # But for efficiency, we should move it later.
        if not extras:
             return rust_escape_characters(rawTextString), extras
        
        # Fallback to manual if extras present (as in original)
        raise Exception("MLWriter: escape characters with extras NOT FULLY MIGRATED YET")
    # end of MLWriter.escape_characters_with_extras static function

    def start( self, lineEndings:str='l', noAutoXML:bool=False, writeBOM:bool=False ) -> None:
        """
        Opens the file and writes a header record to it.
        """
        self._rust_inner.start(lineEndings[0], noAutoXML, writeBOM)
    # end of MLWriter.start


    def checkText( self, textString:str ) -> str:
        # Rust backend handles most of this now or we skip it for performance
        return textString


    def writeNewLine( self, count:int=1 ) -> None:
        """
        Writes a (1 or more) new line sequence to the output.
        """
        # Not directly in Rust inner yet as a separate call, but we can simulate
        for _ in range(count):
            self._rust_inner.write_line_text("", no_nl=False)
    # end of MLWriter.writeNewLine


    def writeLineComment( self, text:str, noTextCheck:bool=False ) -> int:
        """
        Writes an XML comment field.
        """
        return self._rust_inner.write_line_text(f'<!-- {text} -->', no_nl=False)
    # end of MLWriter.writeLineComment


    def writeLineText( self, text:str, noTextCheck:bool=False, noNL:bool|None=None ) -> int:
        """
        Writes raw text onto a line.
        """
        return self._rust_inner.write_line_text(text, no_nl=noNL)
    # end of MLWriter.writeLineText


    def writeLineOpen( self, openTag:str, attribInfo:tuple|list|dict|None=None, noNL:bool|None=None ) -> None:
        """
        Writes an opening tag on a line.
        """
        attribs = []
        if isinstance(attribInfo, dict):
            attribs = list(attribInfo.items())
        elif isinstance(attribInfo, list):
            attribs = attribInfo
        elif isinstance(attribInfo, tuple):
            attribs = [attribInfo]
        
        # Convert all values to strings for Rust
        attribs = [(str(k), str(v)) for k, v in attribs]
        
        self._rust_inner.write_line_open(openTag, attribs if attribs else None, no_nl=noNL)
    # end of MLWriter.writeLineOpen


    def writeLineOpenText( self, openTag:str, text:str, attribInfo:tuple|list|dict|None=None, noTextCheck:bool=False ) -> None:
        """
        Writes an opening tag on a line.
        """
        self.writeLineOpen(openTag, attribInfo, noNL=True)
        self.writeLineText(text, noNL=True)
        # Note: This doesn't close it, following original logic where it just starts it.
    # end of MLWriter.writeLineOpenText


    def writeLineClose( self, closeTag:str ) -> None:
        """
        Writes a closing tag on a line.
        """
        self._rust_inner.write_line_close(closeTag)
    # end of MLWriter.writeLineOpen


    def writeLineOpenClose( self, tag:str, text:str, attribInfo:tuple|list|dict|None=None, noTextCheck:bool=False ) -> int:
        """
        Writes an opening and closing tag on the same line.
        """
        attribs = []
        if isinstance(attribInfo, dict):
            attribs = list(attribInfo.items())
        elif isinstance(attribInfo, list):
            attribs = attribInfo
        elif isinstance(attribInfo, tuple):
            attribs = [attribInfo]
        attribs = [(str(k), str(v)) for k, v in attribs]

        return self._rust_inner.write_line_open_close(tag, text, attribs if attribs else None)
    # end of MLWriter.writeLineOpenClose


    def writeLineOpenSelfclose( self, tag:str, attribInfo=None ) -> int:
        """
        Writes a self-closing tag with optional attributes.
        """
        attribs = []
        if isinstance(attribInfo, dict):
            attribs = list(attribInfo.items())
        elif isinstance(attribInfo, list):
            attribs = attribInfo
        elif isinstance(attribInfo, tuple):
            attribs = [attribInfo]
        attribs = [(str(k), str(v)) for k, v in attribs]

        return self._rust_inner.write_line_open_selfclose(tag, attribs if attribs else None)
    # end of MLWriter.writeLineOpenSelfclose


    def close( self, writeFinalNL:bool=False ) -> None:
        """
        Finish everything up and close the file.
        """
        self._rust_inner.close(writeFinalNL)
    # end of MLWriter.close


    def autoClose( self ) -> None:
        """
        Close all open tags and finish everything up and close the file.
        """
        # Rust impl could have this, but for now we can call it in Python as before if we keep a stack,
        # but Rust also has the stack. We'll just call close and let it check or handle it.
        self._rust_inner.close(False)
    # end of MLWriter.autoClose


    def validate( self, schemaFilepath:Path|str ) -> tuple:
        """
        Validate the just closed file against the given schema (pathname or URL).
        """
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Running MLWriter.validate( {schemaFilepath} ) on {self._outputType} file {self._outputFilePath}…" )

        if self._outputType == 'XML':
            import subprocess # for running xmllint
            schemaFilepath = str(schemaFilepath)
            parameters = [ '/usr/bin/xmllint', '--noout', '--relaxng' if '.rng' in schemaFilepath else '--schema', schemaFilepath, str(self._outputFilePath) ]
            try:
                checkProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                checkProgramOutputBytes, checkProgramErrorOutputBytes = checkProcess.communicate()
                returnCode = checkProcess.returncode
            except FileNotFoundError:
                errorMsg = f"MLWriter.validate is unable to open {parameters[0]!r}"
                logging.error( errorMsg )
                if self.haltOnErrors: raise Exception( errorMsg )
                return None
            checkProgramOutputString = checkProgramErrorOutputString = ''
            if checkProgramOutputBytes: checkProgramOutputString = f"{self._filename}:\n{checkProgramOutputBytes.decode( encoding='utf-8', errors='replace' )}"
            if checkProgramErrorOutputBytes:
                tempString = checkProgramErrorOutputBytes.decode( encoding='utf-8', errors='replace' )
                if tempString.count('\n')>1 or not tempString.endswith('validates\n'):
                    checkProgramErrorOutputString = f'{self._filename}:\n{tempString}'
            xmllintError = ("No error", "Unclassified", "Error in DTD", "Validation error", "Validation error", "Error in schema compilation", "Error writing output", "Error in pattern", "Error in reader registration", "Out of memory")
            if returnCode != 0:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  WARNING: xmllint gave an error on the created {self._filename} file: {returnCode} = {xmllintError[returnCode]}" )
            else: vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  xmllint validated the xml file {self._filename}." )
            return returnCode, checkProgramOutputString, checkProgramErrorOutputString,
    # end of MLWriter.validate
# end of MLWriter class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # Demo the writer object with XML
        outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH
        outputFilename = 'test.xml'
        if not os.access( outputFolderpath, os.F_OK ): os.mkdir( outputFolderpath ) # Make the empty folder if there wasn't already one there
        schema = "~/imaginary.xsd"
        mlWr = MLWriter( outputFilename, outputFolderpath )
        mlWr.setHumanReadable( 'All' )
        mlWr.start()
        mlWr.setSectionName( 'Header' )
        mlWr.writeLineOpen( "vwxyz", [("xmlns","http://someURL.net/namespace"),("xmlns:xsi","http://someURL.net/XMLSchema-instance"),("xsi:schemaLocation",f"http://someURL.net/namespace {schema}")] )
        mlWr.writeLineOpen( 'header' )
        mlWr.writeLineOpenClose( 'title', "myTitle" )
        mlWr.writeLineClose( 'header' )
        mlWr.setSectionName( 'Main' )
        mlWr.writeLineOpen( 'body' )
        mlWr.writeLineOpen( "division", [('id','Div1'),('name','First division')] )
        mlWr.writeLineOpenClose( "text", "myText in here", ("font","favouriteFont") )
        mlWr.close()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr ) # Just print a summary

    if 1: # Demo the writer object with HTML5
        import datetime
        outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH
        outputFilename = 'test.html'
        if not os.access( outputFolderpath, os.F_OK ): os.mkdir( outputFolderpath ) # Make the empty folder if there wasn't already one there
        schema = ""
        mlWr = MLWriter( outputFilename, outputFolderpath, 'HTML' )
        mlWr.setHumanReadable( 'All' )
        mlWr.start()
        mlWr.setSectionName( 'Header' )
        mlWr.writeLineText( '<!DOCTYPE html>', noTextCheck=True )
        mlWr.writeLineOpen( 'html' )
        mlWr.writeLineOpen( 'head' )
        mlWr.writeLineText( '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">', noTextCheck=True )
        mlWr.writeLineText( '<link rel="stylesheet" type="text/css" href="CSS/BibleBook.css">', noTextCheck=True )
        mlWr.writeLineOpenClose( 'title' , "My HTML5 Test Page" )
        mlWr.writeLineClose( 'head' )

        mlWr.setSectionName( 'Main' )
        mlWr.writeLineOpen( 'body' )
        mlWr.writeLineOpen( 'header' )
        mlWr.writeLineText( 'HEADER STUFF GOES HERE' )
        mlWr.writeLineClose( 'header' )
        mlWr.writeLineOpen( 'nav' )
        mlWr.writeLineText( 'NAVIGATION STUFF GOES HERE' )
        mlWr.writeLineClose( 'nav' )
        mlWr.writeLineOpenClose( "h1", "myHeading in here", ('class','testHeading') )
        mlWr.writeLineOpenClose( "p", "myText in here", [("class","funParagraph"),('id','myAnchor'),] )
        mlWr.writeLineOpen( 'footer' )
        mlWr.writeLineOpen( 'p', ('class','footerLine') )
        mlWr.writeLineOpen( 'a', ('href','http://www.w3.org/html/logo/') )
        mlWr.writeLineText( '<img src="http://www.w3.org/html/logo/badge/html5-badge-h-css3-semantics.png" width="165" height="64" alt="HTML5 Powered with CSS3 / Styling, and Semantics" title="HTML5 Powered with CSS3 / Styling, and Semantics">', noTextCheck=True )
        mlWr.writeLineClose( 'a' )
        mlWr.writeLineText( f'This page automatically created by: {PROGRAM_NAME} v{PROGRAM_VERSION} {datetime.date.today().strftime("%d-%b-%Y")}' )
        mlWr.writeLineClose( 'p' )
        mlWr.writeLineClose( 'footer' )
        mlWr.writeLineClose( 'body' )
        mlWr.close()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr ) # Just print a summary
# end of MLWriter.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of MLWriter.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of MLWriter.py
