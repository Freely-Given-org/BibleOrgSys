#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
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

Why write yet another module to do this?
    Better control of field checking and warning/error messages
    Better control of file layout and indentation
    It only took half a day anyway.

TODO: Add buffering
TODO: Add writeAutoDTD

"""
from gettext import gettext as _
import os
import logging
from pathlib import Path

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleExtraList


LAST_MODIFIED_DATE = '2022-11-22' # by RJH
SHORT_PROGRAM_NAME = "MLWriter"
PROGRAM_NAME = "XML/HTML Writer"
PROGRAM_VERSION = '0.41'
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

        self.spaceBeforeSelfcloseTag = False
        self._suppressFollowingIndent = False
        self._humanReadable = 'All' # Else 'None' or 'Header' or the special 'NLSpace' mode
        self._indentPerLevel = 2 # Number of spaces to indent for each level
        self._limitColumns = True # Add new lines when going over the column width limit
        self._maxColumns = 70 # Very roughly indicates the desired column width to aim for (but it can vary considerable either way because we only break in certain positions)

        self._status = 'Idle' # Not sure that we really even need this
        self._sectionName = 'None' # Else 'Header' or 'Main' (allows finer use of humanReadable control)
        self._buffer = ''
        self._bufferFlushSize = 1000 # Flush the buffer to the disk when it gets this many characters
        self._bufferSaveSize = 30 # How much off the buffer to hold back for possible backtracking
        self._openStack = [] # Here we keep track of what XML markers need to be closed
        self._currentColumn = 0
        self._nl = '\n'
        self.linesWritten = 0

        self.haltOnErrors = DEBUGGING_THIS_MODULE != False or BibleOrgSysGlobals.strictCheckingFlag
    # end of MLWriter.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of the XML writer system.

        @return: the name of the object formatted as a string
        @rtype: string
        """
        result = "MLWriter object"
        result += ('\n' if result else '') + "  " + _("Type: {}").format(self._outputType)
        result += ('\n' if result else '') + "  " + _("Status: {}").format(self._status)
        return result
    # end of MLWriter.__str__


    def setOutputType( self, newType:str ) -> None:
        """
        Set the output type = XML or HTML
                Use XML for xHTML.
        """
        assert self._status == 'Idle'
        assert newType in allowedOutputTypes
        self._outputType = newType
    # end of MLWriter.setOutputType


    def setHumanReadable( self, value:str='All', indentSize:int=2 ) -> None:
        """
        Set the human readable flag.
            'All': The entire file
            'Header': Just the header section
            'None'
            'NLSpace':
        """
        assert value in ('All', 'Header', 'None', 'NLSpace',)
        self._humanReadable = value
        self._indentPerLevel = indentSize
        if value=='NLSpace':
            self._limitColumns = False
    # end of MLWriter.setHumanReadableFlag


    def setSectionName( self, sectionName:str|None ) -> None:
        """ Tells the writer the current section that we are writing.
            This can affect formatting depending on the _humanReadable flag. """
        assert sectionName in ('None', 'Header', 'Main')
        self._sectionName = sectionName
    # end of MLWriter.setSection


    def _writeToFile( self, string:str ) -> None:
        """ Writes a string to the file.
            NOTE: This doesn't update self._currentColumn (because we don't know what we're writing here). """
        assert self.__outputFile is not None
        self.__outputFile.write( string )
    # end of MLWriter._writeToFile


    def _writeBuffer( self, writeAll:bool=True ) -> None:
        """ Writes the buffer to the file. """
        assert self.__outputFile is not None
        if self._buffer:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Writing buffer of {} characters".format( len(self._buffer) ) )
            if writeAll: # Write it all
                self._writeToFile( self._buffer )
                self._buffer = ''
            elif len(self._buffer) > self._bufferSaveSize: # Write most of it (in case we need to retrack)
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "From {!r} writing {!r} leaving {!r}".format( self._buffer, self._buffer[:-self._bufferSaveSize], self._buffer[-self._bufferSaveSize:] ) )
                self._writeToFile( self._buffer[:-self._bufferSaveSize] )
                self._buffer = self._buffer[-self._bufferSaveSize:]
            #else: pass # Write none
    # end of MLWriter._writeBuffer


    def _writeToBuffer( self, string:str ) -> None:
        """ Writes a string to the buffer.
            NOTE: This doesn't update self._currentColumn (because we don't know what we're writing here). """
        if len(self._buffer) >= self._bufferFlushSize: # Our buffer is getting too big (and slow)
            self._writeBuffer( False ) # Physically write most of it to disk
        self._buffer += string
    # end of MLWriter._writeToBuffer


    def _autoWrite( self, string:str, noNL:bool=False ) -> int:
        """
        Writes a string to the buffer.
            Prepends appropriate indenting.
            Append newlines if requested.
        """
        assert self.__outputFile is not None
        chars = self._SP() + string
        length = len( chars )
        self._currentColumn += length
        if noNL: self._suppressFollowingIndent = True
        else: # normal is to append a NL character
            final = self._NL()
            #if final != self._nl:
            chars += final
                #length += len( final )
                #self._currentColumn += length
        self._writeToBuffer( chars )
        return length
    # end of MLWriter._write


    def getFilePosition( self ) -> int:
        """ Returns the current position through the file (in bytes from the beginning of the file).
                (This can be used by software that wants to index into the XML file.) """
        assert self.__outputFile is not None
        self._writeBuffer( True )
        return self.__outputFile.tell()
    # end of MLWriter.getFilePosition


    def _SP( self ) -> str:
        """Returns an indent with space characters if required (else an empty string)."""
        if self._suppressFollowingIndent: self._suppressFollowingIndent = False; return ''
        if self._humanReadable == "None": return ''
        if self._humanReadable in ("All", "NLSpace"): return ' '*len(self._openStack)*self._indentPerLevel
        # Else, we'll assume that it's set to 'header'
        if self._sectionName == 'Main': return ''
        return ' '*len(self._openStack)*self._indentPerLevel # for header
    # end of MLWriter._SP


    def _NL( self ) -> str:
        """
        Returns a newline character if required (else an empty string).
        """
        if self._humanReadable == "None": result = ''
        elif self._humanReadable == "All":  result = self._nl
        elif self._humanReadable == "NLSpace":  result = ' '
        # Else, we'll assume that it's set to 'header'
        elif self._sectionName == 'Main': result = '' # (not header)
        else: result= self._nl # for header

        # Overrride if we've gone past the max column width
        if self._limitColumns and self._currentColumn >= self._maxColumns: result = self._nl

        if result == self._nl: self._currentColumn = 0
        return result
    # end of MLWriter._NL


    def removeFinalNewline( self, suppressFollowingIndent:bool=False ) -> None:
        """
        Removes a final newline sequence from the buffer.
        """
        removed = False
        if self._buffer:
            if self._nl in ('\n','\r') and self._buffer[-1]==self._nl:
                self._buffer = self._buffer[:-1]
                removed = True
            elif self._nl=='\r\n' and len(self._buffer)>=2 and self._buffer[-2:]=='\r\n':
                self._buffer = self._buffer[:-2]
                removed = True
        if not removed:
            errorMsg = "MLWriter: " + _("No newline to remove")
            logging.error( errorMsg )
            if self.haltOnErrors: raise Exception( errorMsg )
        self._suppressFollowingIndent = suppressFollowingIndent
    # end of MLWriter.removeFinalNewline

    @staticmethod
    def escape_characters( rawTextString:str, checkFirst:bool=False ) -> str:
        """
        Does XML escapes, e.g., & -> &amp;

        If checkFirst is set, prechecks that escapes haven't already been done

        This function is not called anywhere in this module,
            i.e., the user is responsible for calling it appropriately
        """
        if checkFirst:
            for char,escaped_chars in ESCAPE_PAIRS:
                if escaped_chars in rawTextString:
                    pass
                rawTextString = rawTextString.replace( char, escaped_chars )
            return rawTextString

        # else no checkfirst
        for char,escaped_chars in ESCAPE_PAIRS:
            rawTextString = rawTextString.replace( char, escaped_chars )
        return rawTextString
    # end of MLWriter.escape_characters static function

    @staticmethod
    def escape_characters_with_extras( rawTextString:str, extras:InternalBibleExtraList, checkFirst:bool=False ) -> tuple[str,InternalBibleExtraList]:
        """
        Does XML escapes, e.g., & -> &amp;

        Extras contain an index number into the text string,
            so any expansion of the text string must also update those numbers.

        If checkFirst is set, prechecks that escapes haven't already been done and gives a warning

        This function is not called anywhere in this module,
            i.e., the user is responsible for calling it appropriately
        """
        if checkFirst:
            for _char,escaped_chars in ESCAPE_PAIRS:
                if escaped_chars in rawTextString:
                    logging.error( f"""MLWriter.escape_characters_with_extras found already escaped '{escaped_chars}' in string '{rawTextString}'{" -- they'll now be wrongly escaped twice!!!" if extras else ''}""" )

        if not extras: # We can use the simpler function
            return MLWriter.escape_characters( rawTextString, checkFirst ), extras

        # Ok, we've got extras so we need to check more carefully
        # Precounting might speed things up ??? (not profile tested yet)
        escape_count = sum([rawTextString.count(c) for c in ESCAPE_MAP])
        if escape_count == 0:
            return MLWriter.escape_characters( rawTextString, checkFirst ), extras
        else: dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{escape_count=} {[rawTextString.count(c) for c in ESCAPE_MAP]} {rawTextString=}")

        # Ok, we've got chars needing to be escaped and we have extras so need to work through char by char
        char_strings, adjExtras = [], InternalBibleExtraList()
        for ix,char in enumerate(rawTextString):
            if char in ESCAPE_MAP:
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{ix=} {char=}")
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{rawTextString=} {char_strings=} {extras=} {adjExtras=}")
        raise Exception("MLWriter: escape characters with extras NOT WRITTEN YET")
        return ''.join(char_strings), adjExtras
    # end of MLWriter.escape_characters_with_extras static function

    def start( self, lineEndings:str='l', noAutoXML:bool=False, writeBOM:bool=False ) -> None:
        """
        Opens the file and writes a header record to it.
            lineEndings: l for Linux
                         w for Windows
        """
        assert self._status == 'Idle'
        if lineEndings == 'l': self._nl = '\n'
        elif lineEndings == 'w': self._nl = '\r\n'
        else:
            errorMsg = "MLWriter: " + _("Unknown {!r} lineEndings flag").format( lineEndings )
            logging.error( errorMsg )
            if self.haltOnErrors: raise Exception( errorMsg )
        if BibleOrgSysGlobals.verbosityLevel>2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "MLWriter: "+_("Writing {}…").format(self._outputFilePath) )
        self.__outputFile = open( self._outputFilePath, 'wt', encoding='utf-8' ) # Just create the empty file
        self.__outputFile.close()
        if writeBOM:
            #logging.error( "Haven't worked out how to write BOM yet" )
            with open( self._outputFilePath, 'ab' ) as self.__outputFile: # Append binary bytes
                self.__outputFile.write( b'\xef\xbb\xbf' )
                #self.__outputFile.write( decode( codecs.BOM_UTF8 ) )
        self.__outputFile = open( self._outputFilePath, 'at' ) # Append text mode
        self._status = 'Open'
        self._currentColumn = 0
        if self._outputType=='XML' and not noAutoXML:
            chars = self._SP() + '<?xml version="1.0" encoding="utf-8"?>'
            self._currentColumn += len(chars)
            self._autoWrite( chars )
        self._sectionName = 'None'
    # end of MLWriter.start


    def checkTag( self, tagString:str ) -> str:
        """
        Returns a checked string containing the tag name. Note that special characters should have already been handled before calling this routine.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "tagString: {!r}", tagString )
        assert tagString # It can't be blank
        assert '<' not in tagString and '>' not in tagString and '"' not in tagString
        return tagString
    # end of MLWriter.checkTag


    def checkText( self, textString:str ) -> str:
        """
        Returns a checked string containing the tag name. Note that special characters should have already been handled before calling this routine.
        """
        assert textString # It can't be blank
        if '<' in textString or '>' in textString or '"' in textString:
            errorMsg = "MLWriter:checkText: " + _("unexpected characters found in {} {!r}").format( self._outputType, textString )
            logging.error( errorMsg )
            if self.haltOnErrors: raise Exception( errorMsg )
        ix = textString.find( '&' )
        while ix != -1:
            ix2 = textString.find( ';', ix+1 )
            if ix2 == -1:
                errorMsg = "MLWriter:checkText: " + _("unescaped ampersand (&) found in {} {!r}").format( self._outputType, textString )
                logging.error( errorMsg )
                if self.haltOnErrors: raise Exception( errorMsg )
                break # Only give one error
            elif self._outputType == 'XML':
                if textString[ix+1:ix2] not in XML_PREDEFINED_ENTITIES:
                    errorMsg = "MLWriter:checkText: " + _("unknown entity starting with ampersand (&) found in XML {!r}").format( textString )
                    logging.error( errorMsg )
                    if self.haltOnErrors: raise Exception( errorMsg )
                    break # Only give one error
            elif self._outputType == 'HTML':
                if textString[ix+1:ix2] not in HTML_PREDEFINED_CHARACTER_ENTITIES:
                    errorMsg = "MLWriter:checkText: " + _("unknown character entity starting with ampersand (&) found in XML {!r}").format( textString )
                    logging.error( errorMsg )
                    if self.haltOnErrors: raise Exception( errorMsg )
                    break # Only give one error
            else: raise Exception("Programming error")
            ix = textString.find( '&', ix+1 )
        return textString
    # end of MLWriter.checkText


    def checkAttribName( self, nameString:str ) -> str:
        """
        Returns a checked string containing the attribute name. Note that special characters should have already been handled before calling this routine.
        """
        assert nameString # It can't be blank
        assert '<' not in nameString and '>' not in nameString and '"' not in nameString
        return nameString
    # end of MLWriter.checkAttribName


    def checkAttribValue( self, valueString:str ) -> str:
        """
        Returns a checked string containing the attribute value. Note that special characters should have already been handled before calling this routine.
        """
        if isinstance( valueString, int ): valueString = str( valueString ) # Do an automatic conversion if they pass us an integer
        assert valueString # It can't be blank (can it?)
        assert '<' not in valueString and '>' not in valueString and '"' not in valueString
        return valueString
    # end of MLWriter.checkAttribValue


    def getAttributes( self, attribInfo:tuple|list|dict ) -> str:
        """
        Returns a string containing the validated attributes.
        """
        result = ''
        if isinstance( attribInfo, tuple ): # Assume it's a single pair
            assert len(attribInfo) == 2
            assert isinstance( attribInfo[0], str )
            assert isinstance( attribInfo[1], str )
            if result: result += ' '
            result += '{}="{}"'.format( self.checkAttribName(attribInfo[0]), self.checkAttribValue(attribInfo[1]) )
        elif isinstance( attribInfo, list ):
            for attrib,value in attribInfo:
                assert isinstance( attrib, str )
                assert isinstance( value, str ) or isinstance( value, int )
                if result: result += ' '
                result += '{}="{}"'.format( self.checkAttribName(attrib), self.checkAttribValue(value) )
        else: # It's not a tuple or a list so we assume it's a dictionary or ordered dictionary
            for attrib,value in attribInfo.items():
                if result: result += ' '
                result += '{}="{}"'.format( self.checkAttribName(attrib), self.checkAttribValue(value) )
        return result
    # end of MLWriter.getAttributes


    def writeNewLine( self, count:int=1 ) -> None:
        """
        Writes a (1 or more) new line sequence to the output.
        """
        self._writeToBuffer( self._nl * count )
        self._currentColumn = 0
    # end of MLWriter.writeNewLine


    def writeLineComment( self, text:str, noTextCheck:bool=False ) -> int:
        """
        Writes an XML comment field.
        """
        return self._autoWrite( '<!-- {} -->'.format(text if noTextCheck else self.checkText(text)) )
    # end of MLWriter.writeLineComment


    def writeLineText( self, text:str, noTextCheck:bool=False, noNL:bool|None=None ) -> int:
        """
        Writes raw text onto a line.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'writeLineText', text, self._openStack )
        if noNL is None:
            noNL = self._outputType=='HTML' and self._openStack and self._openStack[-1] in HTMLCombinedTags
        return self._autoWrite( text if noTextCheck else self.checkText(text), noNL=noNL )
    # end of MLWriter.writeLineText


    def writeLineOpen( self, openTag:str, attribInfo:tuple|list|None=None, noNL:bool|None=None ) -> None:
        """
        Writes an opening tag on a line.
            Attributes might by 2-tuples or a list of 2-tuples.
            Usually appends a NL sequence.
        """
        if noNL is None: noNL = self._outputType=='HTML' and openTag in HTMLCombinedTags
        if attribInfo is None:
            self._autoWrite( '<{}>'.format(self.checkTag(openTag)), noNL=noNL )
        else: # have one or more attributes
            self._autoWrite( '<{} {}>'.format( self.checkTag(openTag), self.getAttributes(attribInfo) ), noNL=noNL )
        self._openStack.append( openTag )
    # end of MLWriter.writeLineOpen


    def writeLineOpenText( self, openTag:str, text:str, attribInfo:tuple|list|None=None, noTextCheck:bool=False ) -> None:
        """
        Writes an opening tag on a line.
        Note: We don't want to check the text if we know it already contains valid XML (e.g., character formatting).
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "text: {!r}".format(text )
        if noTextCheck == False: text = self.checkText( text )
        if attribInfo is None:
            self._autoWrite( '<{}>{}'.format( self.checkTag(openTag), text ) )
        else: # have one or more attributes
            self._autoWrite( '<{} {}>{}'.format( self.checkTag(openTag), self.getAttributes(attribInfo), text ) )
        self._openStack.append( openTag )
    # end of MLWriter.writeLineOpenText


    def writeLineClose( self, closeTag:str ) -> None:
        """
        Writes a closing tag on a line.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'writeLineClose', self._openStack )
        if not self._openStack:
            errorMsg = "MLWriter:writeLineClose: " + _("closed {!r} tag even though no tags open").format( closeTag )
            logging.error( errorMsg )
            if self.haltOnErrors: raise Exception( errorMsg )
        else:
            expectedTag = self._openStack.pop()
            if expectedTag != closeTag:
                errorMsg = "MLWriter.writeLineClose:" + _("closed {!r} tag but should have closed {!r}").format( closeTag, expectedTag )
                logging.error( errorMsg )
                if self.haltOnErrors: raise Exception( errorMsg )
        noNL = self._outputType=='HTML' and closeTag in HTMLInsideTags
        self._autoWrite( '</{}>'.format(self.checkTag(closeTag)), noNL=noNL )
    # end of MLWriter.writeLineOpen


    def writeLineOpenClose( self, tag:str, text:str, attribInfo:tuple|list|None=None, noTextCheck:bool=False ) -> int:
        """
        Writes an opening and closing tag on the same line.
        """
        checkedTag = self.checkTag(tag)
        checkedText = text if noTextCheck else self.checkText(text)
        noNL = self._outputType=='HTML' and tag in HTMLInsideTags
        if attribInfo is None:
            return self._autoWrite( '<{}>{}</{}>'.format( checkedTag, checkedText, checkedTag ), noNL=noNL )
        #else: # have one or more attributes
        return self._autoWrite( '<{} {}>{}</{}>'.format( checkedTag, self.getAttributes(attribInfo), checkedText, checkedTag ), noNL=noNL )
    # end of MLWriter.writeLineOpenClose


    def writeLineOpenSelfclose( self, tag:str, attribInfo=None ) -> int:
        """
        Writes a self-closing tag with optional attributes.
        """
        checkedTag = self.checkTag(tag)
        if attribInfo is None:
            return self._autoWrite( '<{}{}/>'.format( checkedTag, ' ' if self.spaceBeforeSelfcloseTag else '' ) )
        #else: # have one or more attributes
        return self._autoWrite( '<{} {}{}/>'.format( checkedTag, self.getAttributes(attribInfo), ' ' if self.spaceBeforeSelfcloseTag else '' ) )
    # end of MLWriter.writeLineOpenSelfclose


    def close( self, writeFinalNL:bool=False ) -> None:
        """
        Finish everything up and close the file.
        """
        assert self.__outputFile is not None
        if self._openStack:
            errorMsg = "MLWriter.close: " + _("have unclosed tags: {}").format(self._openStack)
            logging.error( errorMsg )
            if self.haltOnErrors: raise Exception( errorMsg )
        if writeFinalNL: self.writeNewLine()
        if self._buffer: self._writeBuffer()
        if self._status != 'Buffered': pass
        self.__outputFile.close()
        self._status = 'Closed'
    # end of MLWriter.close


    def autoClose( self ) -> None:
        """
        Close all open tags and finish everything up and close the file.
        """
        assert self.__outputFile is not None
        assert self._status == 'Open'
        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "autoClose stack: {}", self._openStack )
        for index in range( len(self._openStack)-1, -1, -1 ): # Have to step through this backwards
            self.writeLineClose( self._openStack[index] )
        self._sectionName = 'None'
        self.close()
    # end of MLWriter.autoClose


    def validate( self, schemaFilepath:Path|str ) -> tuple:
        """
        Validate the just closed file against the given schema (pathname or URL).

        Returns a 3-tuple consisting of
            a result code (0=success)
            and two strings containing the program output and error output.
        """
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "Running MLWriter.validate( {} ) on {} file {}…".format( schemaFilepath, self._outputType, self._outputFilePath ) )

        assert self._status == 'Closed'

        if self._outputType == 'XML':
            import subprocess # for running xmllint
            # Not sure if this will work on most Linux systems -- certainly won't work on other operating systems
            schemaFilepath = str(schemaFilepath) # In case it's a Path object
            parameters = [ '/usr/bin/xmllint', '--noout', '--relaxng' if '.rng' in schemaFilepath else '--schema', schemaFilepath, str(self._outputFilePath) ]
            try:
                checkProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                checkProgramOutputBytes, checkProgramErrorOutputBytes = checkProcess.communicate()
                returnCode = checkProcess.returncode
            except FileNotFoundError:
                errorMsg = "MLWriter.validate is unable to open {!r}".format( parameters[0] )
                logging.error( errorMsg )
                if self.haltOnErrors: raise Exception( errorMsg )
                return None
            checkProgramOutputString = checkProgramErrorOutputString = ''
            if checkProgramOutputBytes: checkProgramOutputString = '{}:\n{}'.format( self._filename, checkProgramOutputBytes.decode( encoding='utf-8', errors='replace' ) )
            if checkProgramErrorOutputBytes:
                tempString = checkProgramErrorOutputBytes.decode( encoding='utf-8', errors='replace' )
                if tempString.count('\n')>1 or not tempString.endswith('validates\n'):
                    checkProgramErrorOutputString = '{}:\n{}'.format( self._filename, tempString )
            xmllintError = ("No error", "Unclassified", "Error in DTD", "Validation error", "Validation error", "Error in schema compilation", "Error writing output", "Error in pattern", "Error in reader registration", "Out of memory")
            if returnCode != 0:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, "  WARNING: xmllint gave an error on the created {} file: {} = {}".format( self._filename, returnCode, xmllintError[returnCode] ) )
                if returnCode == 5: # schema error
                    errorMsg = "MLWriter.validate couldn't read/parse the schema at {}".format( schemaFilepath )
                    logging.critical( errorMsg )
                    if self.haltOnErrors: raise Exception( errorMsg )
            else: vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "  xmllint validated the xml file {}.".format( self._filename ) )
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
        #schema = "http://someURL.net/myOwn.xsd"
        schema = "~/imaginary.xsd"
        mlWr = MLWriter( outputFilename, outputFolderpath )
        mlWr.setHumanReadable( 'All' )
        mlWr.start()
        mlWr.setSectionName( 'Header' )
        mlWr.writeLineOpen( "vwxyz", [("xmlns","http://someURL.net/namespace"),("xmlns:xsi","http://someURL.net/XMLSchema-instance"),("xsi:schemaLocation","http://someURL.net/namespace {}".format(schema))] )
        mlWr.writeLineOpen( 'header' )
        mlWr.writeLineOpenClose( 'title', "myTitle" )
        mlWr.writeLineClose( 'header' )
        mlWr.setSectionName( 'Main' )
        mlWr.writeLineOpen( 'body' )
        mlWr.writeLineOpen( "division", [('id','Div1'),('name','First division')] )
        mlWr.writeLineOpenClose( "text", "myText in here", ("font","favouriteFont") )
        mlWr.autoClose()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr.validate( schema ) )

        from BibleOrgSys.InputOutput.XMLFile import XMLFile
        xf = XMLFile( outputFilename, outputFolderpath )
        try:
            xf.validateByLoading()
            xf.validateWithLint()
        except FileNotFoundError:
            logging.warning( "Unable to try validating XML file for some reason" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, xf.validateAll() )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, xf )

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
        #mlWr.writeLineOpen( "div", [('id','Div1'),('name','First division')] )
        mlWr.writeLineOpenClose( "h1", "myHeading in here", ('class','testHeading') )
        mlWr.writeLineOpenClose( "p", "myText in here", [("class","funParagraph"),('id','myAnchor'),] )
        mlWr.writeLineOpen( 'footer' )
        mlWr.writeLineOpen( 'p', ('class','footerLine') )
        mlWr.writeLineOpen( 'a', ('href','http://www.w3.org/html/logo/') )
        mlWr.writeLineText( '<img src="http://www.w3.org/html/logo/badge/html5-badge-h-css3-semantics.png" width="165" height="64" alt="HTML5 Powered with CSS3 / Styling, and Semantics" title="HTML5 Powered with CSS3 / Styling, and Semantics">', noTextCheck=True )
        mlWr.writeLineClose( 'a' )
        mlWr.writeLineText( "This page automatically created by: {} v{} {}".format( PROGRAM_NAME, PROGRAM_VERSION, datetime.date.today().strftime("%d-%b-%Y") ) )
        mlWr.writeLineClose( 'p' )
        mlWr.writeLineClose( 'footer' )
        mlWr.writeLineClose( 'body' )
        mlWr.autoClose()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr.validate( schema ) )
# end of MLWriter.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # Demo the writer object with XML
        outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH
        outputFilename = 'test.xml'
        if not os.access( outputFolderpath, os.F_OK ): os.mkdir( outputFolderpath ) # Make the empty folder if there wasn't already one there
        #schema = "http://someURL.net/myOwn.xsd"
        schema = "~/imaginary.xsd"
        mlWr = MLWriter( outputFilename, outputFolderpath )
        mlWr.setHumanReadable( 'All' )
        mlWr.start()
        mlWr.setSectionName( 'Header' )
        mlWr.writeLineOpen( "vwxyz", [("xmlns","http://someURL.net/namespace"),("xmlns:xsi","http://someURL.net/XMLSchema-instance"),("xsi:schemaLocation","http://someURL.net/namespace {}".format(schema))] )
        mlWr.writeLineOpen( 'header' )
        mlWr.writeLineOpenClose( 'title', "myTitle" )
        mlWr.writeLineClose( 'header' )
        mlWr.setSectionName( 'Main' )
        mlWr.writeLineOpen( 'body' )
        mlWr.writeLineOpen( "division", [('id','Div1'),('name','First division')] )
        mlWr.writeLineOpenClose( "text", "myText in here", ("font","favouriteFont") )
        mlWr.autoClose()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr.validate( schema ) )

        from BibleOrgSys.InputOutput.XMLFile import XMLFile
        xf = XMLFile( outputFilename, outputFolderpath )
        try:
            xf.validateByLoading()
            xf.validateWithLint()
        except FileNotFoundError:
            logging.warning( "Unable to try validating XML file for some reason" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, xf.validateAll() )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, xf )

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
        #mlWr.writeLineOpen( "div", [('id','Div1'),('name','First division')] )
        mlWr.writeLineOpenClose( "h1", "myHeading in here", ('class','testHeading') )
        mlWr.writeLineOpenClose( "p", "myText in here", [("class","funParagraph"),('id','myAnchor'),] )
        mlWr.writeLineOpen( 'footer' )
        mlWr.writeLineOpen( 'p', ('class','footerLine') )
        mlWr.writeLineOpen( 'a', ('href','http://www.w3.org/html/logo/') )
        mlWr.writeLineText( '<img src="http://www.w3.org/html/logo/badge/html5-badge-h-css3-semantics.png" width="165" height="64" alt="HTML5 Powered with CSS3 / Styling, and Semantics" title="HTML5 Powered with CSS3 / Styling, and Semantics">', noTextCheck=True )
        mlWr.writeLineClose( 'a' )
        mlWr.writeLineText( "This page automatically created by: {} v{} {}".format( PROGRAM_NAME, PROGRAM_VERSION, datetime.date.today().strftime("%d-%b-%Y") ) )
        mlWr.writeLineClose( 'p' )
        mlWr.writeLineClose( 'footer' )
        mlWr.writeLineClose( 'body' )
        mlWr.autoClose()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, mlWr.validate( schema ) )
# end of MLWriter.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of MLWriter.py
