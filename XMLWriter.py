#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# XMLWriter.py
#   Last modified: 2013-05-14 by RJH (also update versionString below)
#
# Module handling pretty writing of XML (and xHTML) files
#
# Copyright (C) 2010-2013 Robert Hunt
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
Module handling creation of simple XML (and xHTML) files.

Why write yet another module to do this?
    Better control of field checking and warning/error messages
    Better control of file layout and indentation
    It only took half a day anyway.

TODO: Add buffering
TODO: Add writeAutoDTD

"""

progName = "XML Writer"
versionString = "0.27"


import os, logging
from gettext import gettext as _

import Globals


class XMLWriter:
    """
    A class to handle data for Bible book order systems.
    """

    def __init__( self ):
        """
        Constructor.
        """
        self.outputFilePath = None # The folder and filename
        self.outputFile = None # The actual file object

        self.spaceBeforeSelfcloseTag = False
        self._suppressFollowingIndent = False
        self._humanReadable = 'All' # Else 'None' or 'Header' or the special 'NLSpace' mode
        self._indentPerLevel = 2 # Number of spaces to indent for each level
        self._limitColumns = True # Add new lines when going over the column width limit
        self._maxColumns = 200 # Very roughly indicates the desired column width to aim for (but it can vary considerable either way because we only break in certain positions)

        self._status = "Idle" # Not sure that we really even need this
        self._sectionName = "None" # Else 'Header' or 'Main' (allows finer use of humanReadable control)
        self._buffer = ''
        self._bufferFlushSize = 1000 # Flush the buffer to the disk when it gets this many characters
        self._bufferSaveSize = 30 # How much off the buffer to hold back for possible backtracking
        self._openStack = [] # Here we keep track of what XML markers need to be closed
        self._currentColumn = 0
        self._nl = '\n'
        self.linesWritten = 0
    # end of __init__

    def __str__( self ):
        """
        This method returns the string representation of the XML writer system.

        @return: the name of the object formatted as a string
        @rtype: string
        """
        result = "XMLWriter object"
        result += ('\n' if result else '') + "  " + _("Status: {}").format(self._status)
        return result
    # end of __str__

    def setOutputFilePath( self, filename, folder=None ):
        """ Set the output filepath. """
        assert( self._status == 'Idle' )
        self.filename = filename
        self.folder = folder
        self.outputFilePath = os.path.join ( self.folder, self.filename ) if folder is not None else self.filename
        return self
    # end of setOutputFilePath

    def setHumanReadable( self, value='All', indentSize=2 ):
        """ Set the human readable flag. """
        assert( value=='All' or value=='Header' or value=='None' or value=='NLSpace' )
        self._humanReadable = value
        self._indentPerLevel = indentSize
        if value=='NLSpace':
            self._limitColumns = False
    # end of setHumanReadableFlag

    def setSectionName( self, sectionName ):
        """ Tells the writer the current section that we are writing.
            This can affect formatting depending on the _humanReadable flag. """
        assert( sectionName=='None' or sectionName=='Header' or sectionName=='Main' )
        self._sectionName = sectionName
    # end of setSection

    def _writeToFile( self, string ):
        """ Writes a string to the file.
            NOTE: This doesn't update self._currentColumn (because we don't know what we're writing here). """
        assert( self.outputFile is not None )
        self.outputFile.write( string )
    # end of _writeToFile

    def _writeBuffer( self, writeAll=True ):
        """ Writes the buffer to the file. """
        assert( self.outputFile is not None )
        if self._buffer:
            #print( "Writing buffer of {} characters".format( len(self._buffer) ) )
            if writeAll: # Write it all
                self._writeToFile( self._buffer )
                self._buffer = ''
            elif len(self._buffer) > self._bufferSaveSize: # Write most of it (in case we need to retrack)
                #print( "From '{}' writing '{}' leaving '{}'".format( self._buffer, self._buffer[:-self._bufferSaveSize], self._buffer[-self._bufferSaveSize:] ) )
                self._writeToFile( self._buffer[:-self._bufferSaveSize] )
                self._buffer = self._buffer[-self._bufferSaveSize:]
            #else: pass # Write none
    # end of _writeBuffer

    def _writeToBuffer( self, string ):
        """ Writes a string to the buffer.
            NOTE: This doesn't update self._currentColumn (because we don't know what we're writing here). """
        if len(self._buffer) >= self._bufferFlushSize: # Our buffer is getting too big (and slow)
            self._writeBuffer( False ) # Physically write most of it to disk
        self._buffer += string
    # end of _writeToBuffer

    def _autoWrite( self, string ):
        """ Writes a string to the file with appropriate indenting and newlines. """
        assert( self.outputFile is not None )
        chars = self._SP() + string
        length = len( chars )
        self._currentColumn += length
        final = self._NL()
        if final != self._nl: length += len( final )
        self._writeToBuffer( chars + final )
        self._currentColumn += length
        return length
    # end of _write

    def getFilePosition( self ):
        """ Returns the current position through the file (in bytes from the beginning of the file).
                (This can be used by software that wants to index into the XML file.) """
        assert( self.outputFile is not None )
        self._writeBuffer( True )
        return self.outputFile.tell()
    # end of getFilePosition

    def _SP( self ):
        """Returns an indent with space characters if required (else an empty string)."""
        if self._suppressFollowingIndent: self._suppressFollowingIndent = False; return ''
        if self._humanReadable == "None": return ''
        if self._humanReadable=="All" or self._humanReadable=="NLSpace": return ' '*len(self._openStack)*self._indentPerLevel
        # Else, we'll assume that it's set to "Header"
        if self._sectionName == 'Main': return ''
        return ' '*len(self._openStack)*self._indentPerLevel # for header
    # end of _SP

    def _NL( self ):
        """Returns a newline character if required (else an empty string)."""
        if self._humanReadable == "None": result = ''
        elif self._humanReadable == "All":  result = self._nl
        elif self._humanReadable == "NLSpace":  result = ' '
        # Else, we'll assume that it's set to "Header"
        elif self._sectionName == 'Main': result = '' # (not header)
        else: result= self._nl # for header

        # Overrride if we've gone past the max column width
        if self._limitColumns and self._currentColumn >= self._maxColumns: result = self._nl

        if result == self._nl: self._currentColumn = 0
        return result
    # end of _NL

    def removeFinalNewline( self, suppressFollowingIndent=False ):
        """ Removes a final newline sequence from the buffer. """
        removed = False
        if self._buffer:
            if self._nl in ('\n','\r') and self._buffer[-1]==self._nl:
                self._buffer = self._buffer[:-1]
                removed = True
            elif self._nl=='\r\n' and len(self._buffer)>=2 and self._buffer[-2:]=='\r\n':
                self._buffer = self._buffer[:-2]
                removed = True
        if not removed: logging.error( "XMLWriter: No newline to remove" )
        self._suppressFollowingIndent = suppressFollowingIndent
    # end of removeFinalNewline

    def start( self, lineEndings='l', noAutoXML=False, writeBOM=False ):
        """
        Opens the file and writes a header record to it.
            lineEndings: l for Linux
                         w for Windows
        """
        assert( self._status == 'Idle' )
        if lineEndings=='l': self._nl = '\n'
        elif lineEndings=='w': self._nl = '\r\n'
        else: logging.error( "XMLWriter: Unknown '{}' lineEndings flag".format( lineEndings ) )
        if Globals.verbosityLevel>2: print( _("Writing {}...").format(self.outputFilePath) )
        self.outputFile = open( self.outputFilePath, 'wt' ) # Just create the empty file
        self.outputFile.close()
        if writeBOM:
            #logging.error( "Haven't worked out how to write BOM yet" )
            with open( self.outputFilePath, 'ab' ) as self.outputFile: # Append binary bytes
                self.outputFile.write( b'\xef\xbb\xbf' )
                #self.outputFile.write( decode( codecs.BOM_UTF8 ) )
        self.outputFile = open( self.outputFilePath, 'at' ) # Append text mode
        self._status = 'Open'
        self._currentColumn = 0
        if not noAutoXML:
            chars = self._SP() + '<?xml version="1.0" encoding="utf-8"?>'
            self._currentColumn += len(chars)
            self._autoWrite( chars )
        self._sectionName = 'None'
    # end of start

    def checkTag( self, tagString ):
        """ Returns a checked string containing the tag name. Note that special characters should have already been handled before calling this routine. """
        #print( "tagString: '{}'", tagString )
        assert( tagString ) # It can't be blank
        assert( '<' not in tagString and '>' not in tagString and '"' not in tagString )
        return tagString
    # end of checkTag

    def checkText( self, textString ):
        """ Returns a checked string containing the tag name. Note that special characters should have already been handled before calling this routine. """
        assert( textString ) # It can't be blank
        if '<' in textString or '>' in textString or '"' in textString: logging.error( _("XMLWriter:checkText: unexpected characters found in '{}'").format( textString ) )
        return textString
    # end of checkText

    def checkAttribName( self, nameString ):
        """ Returns a checked string containing the attribute name. Note that special characters should have already been handled before calling this routine. """
        assert( nameString ) # It can't be blank
        assert( '<' not in nameString and '>' not in nameString and '"' not in nameString )
        return nameString
    # end of checkAttribName

    def checkAttribValue( self, valueString ):
        """ Returns a checked string containing the attribute value. Note that special characters should have already been handled before calling this routine. """
        if isinstance( valueString, int ): valueString = str( valueString ) # Do an automatic conversion if they pass us an integer
        assert( valueString ) # It can't be blank (can it?)
        assert( '<' not in valueString and '>' not in valueString and '"' not in valueString )
        return valueString
    # end of checkAttribValue

    def getAttributes( self, attribInfo ):
        """ Returns a string containing the validated attributes. """
        result = ''
        if isinstance( attribInfo, tuple ): # Assume it's a single pair
            assert( len(attribInfo) == 2 )
            assert( isinstance( attribInfo[0], str ) )
            assert( isinstance( attribInfo[1], str ) )
            if result: result += ' '
            result += '{}="{}"'.format( self.checkAttribName(attribInfo[0]), self.checkAttribValue(attribInfo[1]) )
        elif isinstance( attribInfo, list ):
            for attrib,value in attribInfo:
                assert( isinstance( attrib, str ) )
                assert( isinstance( value, str ) or isinstance( value, int ) )
                if result: result += ' '
                result += '{}="{}"'.format( self.checkAttribName(attrib), self.checkAttribValue(value) )
        else: # It's not a tuple or a list so we assume it's a dictionary or ordered dictionary
            for attrib,value in attribInfo.items():
                if result: result += ' '
                result += '{}="{}"'.format( self.checkAttribName(attrib), self.checkAttribValue(value) )
        return result
    # end if getAttributes

    def writeNewLine( self, count=1 ):
        """ Writes a (1 or more) new line sequence to the output. """
        self._writeToBuffer( self._nl * count )
        self._currentColumn = 0
    # end of writeNewLine

    def writeLineComment( self, text, noTextCheck=False ):
        """ Writes an XML comment field. """
        return self._autoWrite( '<!-- {} -->'.format(text if noTextCheck else self.checkText(text)) )
    # end of writeLineComment

    def writeLineText( self, text, noTextCheck=False ):
        """ Writes raw text onto a line. """
        #print( 'writeLineText', text, self._openStack )
        return self._autoWrite( text if noTextCheck else self.checkText(text) )
    # end of writeLineText

    def writeLineOpen( self, openTag, attribInfo=None ):
        """ Writes an opening tag on a line. """
        if attribInfo is None:
            self._autoWrite( '<{}>'.format(self.checkTag(openTag)) )
        else: # have one or more attributes
            self._autoWrite( '<{} {}>'.format( self.checkTag(openTag), self.getAttributes(attribInfo) ) )
        self._openStack.append( openTag )
    # end of writeLineOpen

    def writeLineOpenText( self, openTag, text, attribInfo=None, noTextCheck=False ):
        """ Writes an opening tag on a line.
        Note: We don't want to check the text if we know it already contains valid XML (e.g., character formatting)."""
        #print( "text: '{}'".format(text )
        if noTextCheck == False: text = self.checkText( text )
        if attribInfo is None:
            self._autoWrite( '<{}>{}'.format( self.checkTag(openTag), text ) )
        else: # have one or more attributes
            self._autoWrite( '<{} {}>{}'.format( self.checkTag(openTag), self.getAttributes(attribInfo), text ) )
        self._openStack.append( openTag )
    # end of writeLineOpenText

    def writeLineClose( self, closeTag ):
        """ Writes an opening tag on a line. """
        #print( 'writeLineClose', self._openStack )
        if not self._openStack: logging.error( _("XMLWriter:writeLineClose: closed '{}' tag even though no tags open").format( closeTag ) )
        else:
            expectedTag = self._openStack.pop()
            if expectedTag != closeTag: logging.error( _("XMLWriter:writeLineClose: closed '{}' tag but should have closed '{}'").format( closeTag, expectedTag ) )
        self._autoWrite( '</{}>'.format(self.checkTag(closeTag)) )
    # end of writeLineOpen

    def writeLineOpenClose( self, tag, text, attribInfo=None, noTextCheck=False ):
        """ Writes an opening and closing tag on the same line. """
        checkedTag = self.checkTag(tag)
        checkedText = text if noTextCheck else self.checkText(text)
        if attribInfo is None:
            return self._autoWrite( '<{}>{}</{}>'.format( checkedTag, checkedText, checkedTag ) )
        #else: # have one or more attributes
        return self._autoWrite( '<{} {}>{}</{}>'.format( checkedTag, self.getAttributes(attribInfo), checkedText, checkedTag ) )
    # end of writeLineOpenClose

    def writeLineOpenSelfclose( self, tag, attribInfo=None ):
        """ Writes a self-closing tag with optional attributes. """
        checkedTag = self.checkTag(tag)
        if attribInfo is None:
            return self._autoWrite( '<{}{}/>'.format( checkedTag, ' ' if self.spaceBeforeSelfcloseTag else '' ) )
        #else: # have one or more attributes
        return self._autoWrite( '<{} {}{}/>'.format( checkedTag, self.getAttributes(attribInfo), ' ' if self.spaceBeforeSelfcloseTag else '' ) )
    # end of writeLineOpenSelfclose

    def close( self, writeFinalNL=False ):
        """ Finish everything up and close the file. """
        assert( self.outputFile is not None )
        if self._openStack: logging.error( _("XMLWriter:close: have unclosed tags: {}").format(self._openStack) )
        if writeFinalNL: self.writeNewLine()
        if self._buffer: self._writeBuffer()
        if self._status != "Buffered": pass
        self.outputFile.close()
        self._status = "Closed"
    # end of close

    def autoClose( self ):
        """ Close all open tags and finish everything up and close the file. """
        assert( self.outputFile is not None )
        assert( self._status == 'Open' )
        if Globals.debugFlag: print( "autoClose stack: {}", self._openStack )
        for index in range( len(self._openStack)-1, -1, -1 ): # Have to step through this backwards
            self.writeLineClose( self._openStack[index] )
        self._sectionName = 'None'
        self.close()
    # end of autoClose

    def validateXML( self, schemaFile ):
        """ Validate the just closed XML file against the given schema (pathname or URL).
            Returns a 3-tuple consisting of a result code (0=success) and two strings containing the program output and error output.
        """
        assert( self._status == "Closed" )

        import subprocess # for running xmllint
        # Not sure if this will work on most Linux systems -- certainly won't work on other operating systems
        parameters = [ '/usr/bin/xmllint', '--noout', '--relaxng' if '.rng' in schemaFile else '--schema', schemaFile, self.outputFilePath ]
        checkProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        checkProgramOutputBytes, checkProgramErrorOutputBytes = checkProcess.communicate()
        returnCode = checkProcess.returncode
        checkProgramOutputString = checkProgramErrorOutputString = ''
        if checkProgramOutputBytes: checkProgramOutputString = '{}:\n{}'.format( self.filename, checkProgramOutputBytes.decode( encoding="utf-8", errors="replace" ) )
        if checkProgramErrorOutputBytes:
            tempString = checkProgramErrorOutputBytes.decode( encoding="utf-8", errors="replace" )
            if tempString.count('\n')>1 or not tempString.endswith('validates\n'):
                checkProgramErrorOutputString = '{}:\n{}'.format( self.filename, tempString )
        xmllintError = ("No error", "Unclassified", "Error in DTD", "Validation error", "Validation error", "Error in schema compilation", "Error writing output", "Error in pattern", "Error in reader registration", "Out of memory")
        if returnCode != 0:
            if Globals.verbosityLevel > 2: print( "  WARNING: xmllint gave an error on the created {} file: {} = {}".format( self.filename, returnCode, xmllintError[returnCode] ) )
        elif Globals.verbosityLevel > 3: print( "  xmllint validated the xml file {}.".format( self.filename ) )
        return returnCode, checkProgramOutputString, checkProgramErrorOutputString,
    # end of validateXML
# end of XMLWriter class


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel>0: print( "{} V{}".format( progName, versionString ) )

    if 1: # Demo the writer object with XML
        outputFolder = "OutputFiles"
        outputFilename = "test.xml"
        if not os.access( outputFolder, os.F_OK ): os.mkdir( outputFolder ) # Make the empty folder if there wasn't already one there
        #schema = "http://someURL.net/myOwn.xsd"
        schema = "~/imaginary.xsd"
        xw = XMLWriter().setOutputFilePath( outputFilename, outputFolder )
        xw.setHumanReadable( "All" )
        xw.start()
        xw.writeLineOpen( "vwxyz", [("xmlns","http://someURL.net/namespace"),("xmlns:xsi","http://someURL.net/XMLSchema-instance"),("xsi:schemaLocation","http://someURL.net/namespace {}".format(schema))] )
        xw.writeLineOpen( "header" )
        xw.writeLineOpenClose( "title", "myTitle" )
        xw.writeLineClose( "header" )
        xw.writeLineOpen( "body" )
        xw.writeLineOpen( "division", [('id','Div1'),('name','First division')] )
        xw.writeLineOpenClose( "text", "myText in here", ("font","favouriteFont") )
        xw.autoClose()
        print( xw ) # Just print a summary
        print( xw.validateXML( schema ) )

        from XMLFile import XMLFile
        xf = XMLFile( outputFilename, outputFolder )
        xf.validateByLoading()
        xf.validateWithLint()
        #print( xf.validateAll() )
        print( xf )

    if 1: # Demo the writer object with HTML
        outputFolder = "OutputFiles"
        outputFilename = "test.html"
        if not os.access( outputFolder, os.F_OK ): os.mkdir( outputFolder ) # Make the empty folder if there wasn't already one there
        schema = ""
        xw = XMLWriter().setOutputFilePath( outputFilename, outputFolder )
        xw.setHumanReadable( "All" )
        xw.start( noAutoXML=True )
        xw.writeLineText( '<!DOCTYPE html>', noTextCheck=True )
        xw.writeLineOpen( 'html' )
        xw.writeLineOpen( "header" )
        xw.writeLineOpenClose( "title", "myTitle" )
        xw.writeLineClose( "header" )
        xw.writeLineOpen( "body" )
        #xw.writeLineOpen( "div", [('id','Div1'),('name','First division')] )
        xw.writeLineOpenClose( "h1", "myHeading in here", ('class','testHeading') )
        xw.writeLineOpenClose( "p", "myText in here", [("class","funParagraph"),('id','myAnchor'),] )
        xw.autoClose()
        print( xw ) # Just print a summary
        print( xw.validateXML( schema ) )

        from XMLFile import XMLFile
        xf = XMLFile( outputFilename, outputFolder )
        xf.validateByLoading()
        xf.validateWithLint()
        #print( xf.validateAll() )
        print( xf )
# end of demo

if __name__ == '__main__':
    demo()
# end of XMLWriter.py