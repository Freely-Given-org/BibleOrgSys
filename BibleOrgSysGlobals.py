#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleOrgSysGlobals.py
#
# Module handling Global variables for our Bible Organisational System
#
# Copyright (C) 2010-2016 Robert Hunt
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
Module handling global variables
    and some useful general functions.

Contains functions:
    setupLoggingToFile( ProgName, ProgVersion, loggingFolderPath=None )
    addConsoleLogging()
    addLogfile( projectName, folderName=None )
    removeLogfile( projectHandler )

    makeSafeFilename( someName )
    makeSafeXML( someString )
    makeSafeString( someString )
    removeAccents( someString )

    backupAnyExistingFile( filenameOrFilepath )
    peekIntoFile( filenameOrFilepath, folderName=None, numLines=1 )

    totalSize( o, handlers={} )

    fileCompare( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 )
    fileCompareUSFM( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 )
    fileCompareXML( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10, ignoreWhitespace=True )

    elementStr( element )
    checkXMLNoText( element, locationString, idString=None )
    checkXMLNoTail( element, locationString, idString=None )
    checkXMLNoAttributes( element, locationString, idString=None )
    checkXMLNoSubelements( element, locationString, idString=None )
    checkXMLNoSubelementsWithText( element, locationString, idString=None )
    getFlattenedXML( element, locationString, idString=None, level=0 )

    applyStringAdjustments( originalText, adjustmentList )

    pickleObject( theObject, filename, folderName=None )
    unpickleObject( filename, folderName=None )

    setup( ProgName, ProgVersion, loggingFolder=None )

    setVerbosity( verbosityLevelParameter )
    setDebugFlag( newValue=True )
    setStrictCheckingFlag( newValue=True )

    addStandardOptionsAndProcess( parserObject )
    printAllGlobals( indent=None )

    closedown( ProgName, ProgVersion )

    demo()
"""

from gettext import gettext as _

LastModifiedDate = '2016-02-13' # by RJH
ShortProgName = "BOSGlobals"
ProgName = "BibleOrgSys Globals"
ProgVersion = '0.61'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os.path, pickle
from optparse import OptionParser


# Global variables
#=================

commandLineOptions, commandLineArguments = None, None

strictCheckingFlag = debugFlag = False
haltOnXMLWarning = False # Used for XML debugging
maxProcesses = 1
verbosityLevel = None
verbosityString = 'Normal'


DEFAULT_LOG_FOLDER = 'Logs/' # Relative path
DEFAULT_CACHE_FOLDER = 'ObjectCache/' # Relative path
if debuggingThisModule:
    LOGGING_NAME_DICT = {logging.DEBUG:'DEBUG', logging.INFO:'INFO', logging.WARNING:'WARNING', logging.ERROR:'ERROR', logging.CRITICAL:'CRITICAL'}


# Some language independant punctuation help
OPENING_SPEECH_CHARACTERS = """“«"‘‹¿¡""" # The length and order of these two strings must match
CLOSING_SPEECH_CHARACTERS = """”»"’›?!"""
assert len(OPENING_SPEECH_CHARACTERS) == len(CLOSING_SPEECH_CHARACTERS)
MATCHING_OPENING_CHARACTERS = {'(':')', '[':']', '{':'}', '<':'>', '<<':'>>', '“':'”', '‘':'‘', '«':'»', '‹':'›', '¿':'?', '¡':'!', }
MATCHING_CHARACTERS = {'(':')',')':'(', '[':']',']':'[', '{':'}','}':'{', '<':'>','>':'<', '<<':'>>','>>':'<<',
                      '“':'”','”':'“', '‘':'’','’':'‘', '«':'»','»':'«', '‹':'›','›':'‹', '¿':'?','?':'¿', '¡':'!','!':'¡', }



##########################################################################################################
#
# Handling logging
#

#def function_with_a_bug(params):
#    """Just sitting here to remind me how to do it"""
#    old_log_level = logging.getLogger().getEffectiveLevel()
#    logging.getLogger().setLevel( logging.DEBUG )
#    logging.debug( "Entering function_with_a_bug" )
#    logging.debug( "Params were {}", params )
#    for item in params:
#        logging.debug( "Processing {}", item )
#        result = do_something_with( item )
#        logging.debug( "Result was: {}", result )
#    logging.getLogger().setLevel( old_log_level )
## end of function_with_a_bug


loggingDateFormat = "%Y-%m-%d %H:%M"
loggingConsoleFormat = '%(levelname)s: %(message)s'
loggingShortFormat = '%(levelname)8s: %(message)s'
loggingLongFormat = '%(asctime)s %(levelname)8s: %(message)s'

def setupLoggingToFile( ShortProgName, ProgVersion, folderPath=None ):
    """
    Sets up the main logfile for the program and returns the full pathname.

    Gets called from our demo() function when program starts up.
    """
    if debuggingThisModule:
        print( "BibleOrgSysGlobals.setupLoggingToFile( {}, {}, {} )".format( repr(ShortProgName), repr(ProgVersion), repr(folderPath) ) )
    filename = ShortProgName.replace('/','-').replace(':','_').replace('\\','_') + '_log.txt'
    if folderPath is None: folderPath = DEFAULT_LOG_FOLDER # relative path
    filepath = os.path.join( folderPath, filename )

    # Create the folderPath if necessary
    if not os.access( folderPath, os.W_OK ):
        os.makedirs( folderPath ) # Works for an absolute or a relative pathname

    # Rename the existing file to a backup copy if it already exists
    if os.access( filepath, os.F_OK ):
        if debuggingThisModule or __name__ == '__main__':
            print( "setupLoggingToFile: {} already exists -- renaming it first!".format( repr(filepath) ) )
        if os.access( filepath+'.bak', os.F_OK ):
            os.remove( filepath+'.bak' )
        os.rename( filepath, filepath+'.bak' )

    # Now setup our new log file -- DOESN'T SEEM TO WORK IN WINDOWS!!!
    # In Windows, doesn't seem to create the log file, even if given a filename rather than a filepath
    setLevel = logging.DEBUG if debugFlag else logging.INFO
    if debuggingThisModule:
        print( "BibleOrgSysGlobals.setBasicConfig to( {}, {}={}, {}, {} )".format( repr(filepath), setLevel, LOGGING_NAME_DICT[setLevel], repr(loggingLongFormat), repr(loggingDateFormat) ) )
    logging.basicConfig( filename=filepath, level=setLevel, format=loggingLongFormat, datefmt=loggingDateFormat )

    #return filepath
# end of BibleOrgSysGlobals.setupLoggingToFile


def addConsoleLogging( consoleLoggingLevel=None ):
    """
    Adds a handler to also send ERROR and higher to console (depending on verbosity)
    """
    if debuggingThisModule:
        print( "BibleOrgSysGlobals.addConsoleLogging( {}={} )".format( consoleLoggingLevel, LOGGING_NAME_DICT[consoleLoggingLevel] ) )
    stderrHandler = logging.StreamHandler() # StreamHandler with no parameters defaults to sys.stderr
    stderrHandler.setFormatter( logging.Formatter( loggingConsoleFormat, None ) )
    if consoleLoggingLevel is not None:
        stderrHandler.setLevel( consoleLoggingLevel )
    else: # work it out for ourselves
        if verbosityLevel == 0: # Silent
            stderrHandler.setLevel( logging.CRITICAL )
        elif verbosityLevel == 4: # Verbose
            stderrHandler.setLevel( logging.WARNING )
        else: # Quiet or normal
            stderrHandler.setLevel( logging.ERROR )
    root = logging.getLogger()  # No param means get the root logger
    root.addHandler(stderrHandler)
# end of BibleOrgSysGlobals.addConsoleLogging


def addLogfile( projectName, folderName=None ):
    """
    Adds an extra project specific log file to the logger.
    """
    if debuggingThisModule: print( "BibleOrgSysGlobals.addLogfile( {}, {} )".format( projectName, folderName ) )
    filename = projectName + '_log.txt'
    if folderName is None: folderName = DEFAULT_LOG_FOLDER # relative path
    filepath = os.path.join( folderName, filename )

    # Create the folderName if necessary
    if not os.access( folderName, os.W_OK ):
        os.makedirs( folderName ) # Works for an absolute or a relative pathname

    # Rename the existing file to a backup copy if it already exists
    if os.access( filepath, os.F_OK ):
        if __name__ == '__main__':
            print( filepath, 'already exists -- renaming it first!' )
        if os.access( filepath+'.bak', os.F_OK ):
            os.remove( filepath+'.bak' )
        os.rename( filepath, filepath+'.bak' )

    projectHandler = logging.FileHandler( filepath )
    projectHandler.setFormatter( logging.Formatter( loggingShortFormat, loggingDateFormat ) )
    projectHandler.setLevel( logging.INFO )
    root = logging.getLogger()
    root.addHandler( projectHandler )
    return filepath, projectHandler
# end of BibleOrgSysGlobals.addLogfile


def removeLogfile( projectHandler ):
    """
    Removes the project specific logger.
    """
    if debuggingThisModule: print( "BibleOrgSysGlobals.removeLogfile( {} )".format( projectHandler ) )
    root = logging.getLogger()  # No param means get the root logger
    root.removeHandler( projectHandler )
# end of BibleOrgSysGlobals.removeLogfile


##########################################################################################################
#

def printUnicodeInfo( text, description ):
    """
    """
    import unicodedata
    print( "{}:".format( description ) )
    for j,char in enumerate(text):
        print( "{:2} {:04x} {} {!r}   (cat={} bid={} comb={} mirr={})" \
            .format(j, ord(char), unicodedata.name(char), char, unicodedata.category(char), unicodedata.bidirectional(char), unicodedata.combining(char), unicodedata.mirrored(char) ) )

##########################################################################################################
#
# Make a string safe if it's going to be used as a filename
#
#       We don't want a malicious user to be able to gain access to the filesystem
#               by putting a filepath into a filename string.

def makeSafeFilename( someName ):
    """
    Replaces potentially unsafe characters in a name to make it suitable for a filename.

    NOTE: This leaves spaces as they were.
    """
    return someName.replace('/','-') \
        .replace('\\','_BACKSLASH_').replace(':','_COLON_').replace(';','_SEMICOLON_') \
        .replace('#','_HASH_').replace('?','_QUESTIONMARK_').replace('*','_ASTERISK_') \
        .replace('<','_LT_').replace('>','_GT_')
# end of BibleOrgSysGlobals.makeSafeFilename


##########################################################################################################
#
# Make a string safe if it could be used in an XML document
#

def makeSafeXML( someString ):
    """
    Replaces special characters in a string to make it for XML.
    """
    return someString.replace('&','&amp;').replace('"','&quot;').replace('<','&lt;').replace('>','&gt;')
# end of BibleOrgSysGlobals.makeSafeXML


##########################################################################################################
#
# Make a string safe if it could be used in an HTML or other document
#
#       We don't want a malicious user to be able to gain access to the system
#               by putting system commands into a string that's then used in a webpage or something.

def makeSafeString( someString ):
    """
    Replaces potentially unsafe characters in a string to make it safe for display.
    """
    #return someString.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    return someString.replace('<','_LT_').replace('>','_GT_')
# end of BibleOrgSysGlobals.makeSafeString


##########################################################################################################
#
# Remove accents

accentDict = { 'À':'A','Á':'A','Â':'A','Ã':'A','Ä':'A','Å':'A','Ă':'A','Ą':'A', 'Æ':'AE',
              'Ç':'C','Ć':'C','Ĉ':'C','Ċ':'C','Č':'C',
              'Ð':'D','Ď':'D','Đ':'D',
              'È':'E','É':'E','Ê':'E','Ë':'E','Ē':'E','Ĕ':'E','Ė':'E','Ę':'E','Ě':'E',
              'Ĝ':'G','Ğ':'G','Ġ':'G','Ģ':'G',
              'Ì':'I','Í':'I','Î':'I','Ï':'I',
              'Ñ':'N',
              'Ò':'O','Ó':'O','Ô':'O','Õ':'O','Ö':'O','Ø':'O',
              'Ù':'U','Ú':'U','Û':'U','Ü':'U',
              'Ý':'Y',
              'à':'a','á':'a','â':'a','ã':'a','ä':'a','å':'a','ā':'a','ă':'a','ą':'a', 'æ':'ae',
              'ç':'c','ć':'c','ĉ':'c','ċ':'c','č':'c',
              'ð':'d','ď':'d','đ':'d',
              'è':'e','é':'e','ê':'e','ë':'e','ē':'e','ĕ':'e','ė':'e','ę':'e','ě':'e',
              'ģ':'g','ğ':'g','ġ':'g','ģ':'g',
              'ì':'i','í':'i','î':'i','ï':'i',
              'ñ':'n',
              'ò':'o','ó':'o','ô':'o','õ':'o','ö':'o','ø':'o',
              'ù':'u','ú':'u','û':'u','ü':'u',
              'ý':'y','ÿ':'y',
              }
def removeAccents( someString ):
    """
    Remove accents from the string and return it (used for fuzzy matching)
    """
    resultString = ''
    for char in someString:
        resultString += accentDict[char] if char in accentDict else char
    return resultString
# end of BibleOrgSysGlobals.makeSafeString


##########################################################################################################
#
# Make a backup copy of a file

def backupAnyExistingFile( filenameOrFilepath ):
    """
    Make a backup copy of a file if it exists.
    """

    if debugFlag: assert not filenameOrFilepath.endswith( '.bak' )
    if os.access( filenameOrFilepath, os.F_OK ):
        if debugFlag:
            logging.info( "backupAnyExistingFile: {} already exists -- renaming it first!".format( repr(filenameOrFilepath) ) )
        if os.access( filenameOrFilepath+'.bak', os.F_OK ):
            os.remove( filenameOrFilepath+'.bak' )
        os.rename( filenameOrFilepath, filenameOrFilepath+'.bak' )
# end of BibleOrgSysGlobals.backupAnyExistingFile


##########################################################################################################
#
# Peek at the first line(s) of a file

def peekIntoFile( filenameOrFilepath, folderName=None, numLines=1, encoding=None ):
    """
    Reads and returns the first line of a text file as a string
        unless more than one line is requested
        in which case a list of strings is returned (including empty strings for empty lines).
    """
    if debugFlag: assert 1 <= numLines < 5
    if encoding is None: encoding = 'utf-8'
    filepath = os.path.join( folderName, filenameOrFilepath ) if folderName else filenameOrFilepath
    lines = []
    try:
        with open( filepath, 'rt', encoding=encoding ) as possibleUSFMFile: # Automatically closes the file when done
            lineNumber = 0
            for line in possibleUSFMFile:
                lineNumber += 1
                if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                #print( thisFilename, lineNumber, line )
                if numLines==1: return line # Always returns the first line
                lines.append( line )
                if lineNumber >= numLines: return lines
    except UnicodeDecodeError: # Could be binary or a different encoding
        #if not filepath.lower().endswith( 'usfm-color.sty' ): # Seems this file isn't UTF-8, but we don't need it here anyway so ignore it
        logging.warning( "{}peekIntoFile: Seems we couldn't decode Unicode in {!r}".format( 'BibleOrgSysGlobals.' if debugFlag else '', filepath ) )
# end of BibleOrgSysGlobals.peekIntoFile


##########################################################################################################
#
# For debugging, etc.

def totalSize( o, handlers={} ):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    from sys import getsizeof
    from itertools import chain

    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbosityLevel > 3: print( s, type(o), repr(o) )

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)
# end of BibleOrgSysGlobals.totalSize


##########################################################################################################
#
# File comparisons
#

def fileCompare( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 ):
    """
    Compare the two files.
    """
    filepath1 = os.path.join( folder1, filename1 ) if folder1 else filename1
    filepath2 = os.path.join( folder2, filename2 ) if folder2 else filename2
    if verbosityLevel > 1:
        if filename1==filename2:
            print( "Comparing {} files in folders {} and {}...".format( repr(filename1), repr(folder1), repr(folder2) ) )
        else: print( "Comparing files {} and {}...".format( repr(filename1), repr(filename2) ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        logging.error( "fileCompare: File1 {!r} is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( "fileCompare: File2 {!r} is unreadable".format( filepath2 ) )
        return None

    # Read the files into lists
    lineCount, lines1 = 0, []
    with open( filepath1, 'rt' ) as file1:
        for line in file1:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2:
                    print( "      fileCompare: Detected UTF-16 Byte Order Marker in file1" )
                line = line[1:] # Remove the UTF-8 Byte Order Marker
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines1.append( line )
    lineCount, lines2 = 0, []
    with open( filepath2, 'rt' ) as file2:
        for line in file2:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2:
                    print( "      fileCompare: Detected UTF-16 Byte Order Marker in file2" )
                line = line[1:] # Remove the UTF-8 Byte Order Marker
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines2.append( line )

    # Compare the length of the lists/files
    len1, len2 = len(lines1), len(lines2 )
    equalFlag = True
    if len1 != len2:
        if printFlag: print( "Count of lines differ: file1={}, file2={}".format( len1, len2 ) )
        equalFlag = False

    # Now compare the actual lines
    diffCount = 0
    for k in range( 0, min( len1, len2 ) ):
        if lines1[k] != lines2[k]:
            if printFlag:
                print( "  {}a:{} ({} chars)\n  {}b:{} ({} chars)" \
                    .format( k+1, repr(lines1[k]), len(lines1[k]), k+1, repr(lines2[k]), len(lines2[k]) ) )
            equalFlag = False
            diffCount += 1
            if diffCount > exitCount:
                if printFlag and verbosityLevel > 1:
                    print( "fileCompare: stopped comparing after {} mismatches".format( exitCount ) )
                break

    return equalFlag
# end of BibleOrgSysGlobals.fileCompare


def fileCompareUSFM( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 ):
    """
    Compare the two USFM files,
        ignoring little things like \s vs \s1.
    """
    filepath1 = os.path.join( folder1, filename1 ) if folder1 else filename1
    filepath2 = os.path.join( folder2, filename2 ) if folder2 else filename2
    if verbosityLevel > 1:
        if filename1==filename2:
            print( "Comparing USFM {} files in folders {} and {}...".format( repr(filename1), repr(folder1), repr(folder2) ) )
        else: print( "Comparing USFM files {} and {}...".format( repr(filename1), repr(filename2) ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        logging.error( "fileCompare: File1 {!r} is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( "fileCompare: File2 {!r} is unreadable".format( filepath2 ) )
        return None

    # Read the files into lists
    lineCount, lines1 = 0, []
    with open( filepath1, 'rt' ) as file1:
        for line in file1:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2:
                    print( "      fileCompare: Detected UTF-16 Byte Order Marker in file1" )
                line = line[1:] # Remove the UTF-8 Byte Order Marker
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines1.append( line )
    lineCount, lines2 = 0, []
    with open( filepath2, 'rt' ) as file2:
        for line in file2:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2:
                    print( "      fileCompare: Detected UTF-16 Byte Order Marker in file2" )
                line = line[1:] # Remove the UTF-8 Byte Order Marker
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines2.append( line )

    # Compare the length of the lists/files
    len1, len2 = len(lines1), len(lines2 )
    equalFlag = True
    if len1 != len2:
        if printFlag: print( "Count of lines differ: file1={}, file2={}".format( len1, len2 ) )
        equalFlag = False

    # Now compare the actual lines
    diffCount = 0
    C = V = '0'
    for k in range( 0, min( len1, len2 ) ):
        originalLine1, originalLine2 = lines1[k], lines2[k]
        adjustedLine1, adjustedLine2 = originalLine1, originalLine2
        while adjustedLine1 and adjustedLine1[-1]==' ': adjustedLine1 = adjustedLine1[:-1] # Remove the final space
        while adjustedLine2 and adjustedLine2[-1]==' ': adjustedLine2 = adjustedLine2[:-1] # Remove the final space
        if adjustedLine1.startswith( '\\c '): C = adjustedLine1[3:]
        if adjustedLine1.startswith( '\\v '): V = adjustedLine1[3:].split()[0]
        for unnumbered,numbered in ( ('mt','mt1'),('mte','mte1'), ('imt','imt1'),('imte','imte1'),
                                    ('is','is1'), ('iq','iq1'), ('io','io1'), ('ili','ili1'),
                                    ('ms','ms1'), ('s','s1'), ('li','li1'), ('q','q1'), ('pi','pi1'), ('ph','ph1'), ):
            if adjustedLine1 == '\\'+unnumbered: adjustedLine1 = '\\'+numbered
            else: adjustedLine1 = adjustedLine1.replace( '\\'+unnumbered+' ', '\\'+numbered+' ' )
            if adjustedLine2 == '\\'+unnumbered: adjustedLine2 = '\\'+numbered
            else: adjustedLine2 = adjustedLine2.replace( '\\'+unnumbered+' ', '\\'+numbered+' ' )
        if adjustedLine1 != adjustedLine2:
            if printFlag:
                print( "  {}:{} {}a:{} ({} chars)\n  {}:{} {}b:{} ({} chars)" \
                    .format( C, V, k+1, repr(originalLine1), len(originalLine1), C, V, k+1, repr(originalLine2), len(originalLine1) ) )
            equalFlag = False
            diffCount += 1
            if diffCount > exitCount:
                if printFlag and verbosityLevel > 1:
                    print( "fileCompare: stopped comparing after {} mismatches".format( exitCount ) )
                break

    return equalFlag
# end of BibleOrgSysGlobals.fileCompareUSFM


def fileCompareXML( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10, ignoreWhitespace=True ):
    """
    Compare the two files.
    """
    filepath1 = os.path.join( folder1, filename1 ) if folder1 else filename1
    filepath2 = os.path.join( folder2, filename2 ) if folder2 else filename2
    if verbosityLevel > 1:
        if filename1==filename2: print( "Comparing XML {} files in folders {} and {}...".format( repr(filename1), repr(folder1), repr(folder2) ) )
        else: print( "Comparing XML files {} and {}...".format( repr(filename1), repr(filename2) ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        logging.error( "fileCompareXML: File1 {!r} is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( "fileCompareXML: File2 {!r} is unreadable".format( filepath2 ) )
        return None

    # Load the files
    from xml.etree.ElementTree import ElementTree
    tree1 = ElementTree().parse( filepath1 )
    tree2 = ElementTree().parse( filepath2 )

    def compareElements( element1, element2 ):
        """
        """
        nonlocal diffCount, location
        if element1.tag != element2.tag:
            if printFlag:
                print( "Element tags differ ({} and {})".format( repr(element1.tag), repr(element2.tag) ) )
                if verbosityLevel > 2: print( "  at", location )
            diffCount += 1
            if diffCount > exitCount: return
            location.append( "{}/{}".format( element1.tag, element2.tag ) )
        else: location.append( element1.tag )
        attribs1, attribs2 = element1.items(), element2.items()
        if len(attribs1) != len(attribs2):
            if printFlag:
                print( "Number of attributes differ ({} and {})".format( len(attribs1), len(attribs2) ) )
                if verbosityLevel > 2: print( "  at", location )
            diffCount += 1
            if diffCount > exitCount: return
        for avPair in attribs1:
            if avPair not in attribs2:
                if printFlag:
                    print( "File1 has {} but not in file2 {}".format( avPair, attribs2 ) )
                    if verbosityLevel > 2: print( "  at", location )
                diffCount += 1
                if diffCount > exitCount: return
        for avPair in attribs2:
            if avPair not in attribs1:
                if printFlag:
                    print( "File2 has {} but not in file1 {}".format( avPair, attribs1 ) )
                    if verbosityLevel > 2: print( "  at", location )
                diffCount += 1
                if diffCount > exitCount: return
        if element1.text != element2.text:
            if ignoreWhitespace:
                if element1.text is None and not element2.text.strip(): pass
                elif element2.text is None and not element1.text.strip(): pass
                elif element1.text and element2.text and element1.text.strip()==element2.text.strip(): pass
                else:
                    if printFlag:
                        print( "Element text differs:\n {}\n {}".format( repr(element1.text), repr(element2.text) ) )
                        if verbosityLevel > 2: print( "  at", location )
                    diffCount += 1
                    if diffCount > exitCount: return
            else:
                if printFlag:
                    print( "Element text differs:\n {}\n {}".format( repr(element1.text), repr(element2.text) ) )
                    if verbosityLevel > 2: print( "  at", location )
                diffCount += 1
                if diffCount > exitCount: return
        if element1.tail != element2.tail:
            if ignoreWhitespace:
                if element1.tail is None and not element2.tail.strip(): pass
                elif element2.tail is None and not element1.tail.strip(): pass
                elif element1.tail and element2.tail and element1.tail.strip()==element2.tail.strip(): pass
                else:
                    if printFlag:
                        print( "Element tail differs:\n {}\n {}".format( repr(element1.tail), repr(element2.tail) ) )
                        if verbosityLevel > 2: print( "  at", location )
                    diffCount += 1
                    if diffCount > exitCount: return
            else:
                if printFlag:
                    print( "Element tail differs:\n {}\n {}".format( repr(element1.tail), repr(element2.tail) ) )
                    if verbosityLevel > 2: print( "  at", location )
                diffCount += 1
                if diffCount > exitCount: return
        if len(element1) != len(element2):
            if printFlag:
                print( "Number of subelements differ ({} and {})".format( len(element1), len(element2) ) )
                if verbosityLevel > 2: print( "  at", location )
            diffCount += 1
            if diffCount > exitCount: return
        # Compare the subelements
        for j in range( 0, min( len(element1), len(element2) ) ):
            compareElements( element1[j], element2[j] ) # Recursive call
            if diffCount > exitCount: return

    # Compare the files
    diffCount, location = 0, []
    compareElements( tree1, tree2 )
    if diffCount and verbosityLevel > 1: print( "{} differences discovered.".format( diffCount if diffCount<=exitCount else 'Many' ) )
    return diffCount==0
# end of BibleOrgSysGlobals.fileCompareXML


##########################################################################################################
#
# Validating XML fields (from element tree)
#

def elementStr( element ):
    """
    Return a string representation of an element (from element tree).
    """
    resultStr = 'Element {!r}: '.format( element.tag )
    printed = False
    for attrib,value in element.items():
        if printed: resultStr += ','
        else: resultStr += 'Attribs:'; printed = True
        resultStr += '{}={!r}'.format( attrib, value )
    if element.text is not None: resultStr += 'Text={!r}'.format( element.text )
    printed = False
    for subelement in element:
        if printed: resultStr += ','
        else: resultStr += 'Children:'; printed = True
        resultStr += elementStr( subelement ) # recursive call
    if element.tail is not None: resultStr += 'Tail={!r}'.format( element.tail )
    return resultStr
# end of BibleOrgSysGlobals.elementStr


def checkXMLNoText( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Give an error if the element text contains anything other than whitespace.
    """
    if element.text and element.text.strip():
        errorString = "{}Unexpected {} element text in {}" \
                        .format( (idString+' ') if idString else '', repr(element.text), locationString )
        logging.error( errorString )
        if loadErrorsDict is not None: loadErrorsDict.append( errorString )
        if debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoText

def checkXMLNoTail( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Give a warning if the element tail contains anything other than whitespace.
    """
    if element.tail and element.tail.strip():
        warningString = "{}Unexpected {} element tail in {}" \
                        .format( (idString+' ') if idString else '', repr(element.tail), locationString )
        logging.warning( warningString )
        if loadErrorsDict is not None: loadErrorsDict.append( warningString )
        if debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoTail


def checkXMLNoAttributes( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Give a warning if the element contains any attributes.
    """
    for attrib,value in element.items():
        warningString = "{}Unexpected {} attribute ({}) in {}" \
                        .format( (idString+' ') if idString else '', repr(attrib), value, locationString )
        logging.warning( warningString )
        if loadErrorsDict is not None: loadErrorsDict.append( warningString )
        if debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoAttributes


def checkXMLNoSubelements( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Give an error if the element contains any sub-elements.
    """
    for subelement in element:
        errorString = "{}Unexpected {} sub-element ({}) in {}" \
                        .format( (idString+' ') if idString else '', repr(subelement.tag), subelement.text, locationString )
        logging.error( errorString )
        if loadErrorsDict is not None: loadErrorsDict.append( errorString )
        if debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoSubelements

def checkXMLNoSubelementsWithText( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Checks that the element doesn't have text AND subelements
    """
    if ( element.text and element.text.strip() ) \
    or ( element.tail and element.tail.strip() ):
        for subelement in element.getchildren():
            warningString = "{}Unexpected {} sub-element ({}) in {} with text/tail {}/{}" \
                            .format( (idString+' ') if idString else '', repr(subelement.tag), subelement.text, locationString,
                                element.text.strip() if element.text else element.text,
                                element.tail.strip() if element.tail else element.tail )
            logging.warning( warningString )
            if loadErrorsDict is not None: loadErrorsDict.append( warningString )
            if debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoSubelementsWithText


def getFlattenedXML( element, locationString, idString=None, level=0 ):
    """
    Return the XML nested inside the element as a text string.

    The last two parameters are used for handling recursion.

    Strips the tail (which often contains excess nl characters).
    """
    result = ''
    # Get attributes
    attributes = ''
    for attribName,attribValue in element.items():
        attributes += '{}{}="{}"'.format( ' ' if attributes else '', attribName, attribValue )
    if level: # For lower levels (other than the called one) need to add the tags
        result += '<' + element.tag
        if attributes: result += ' ' + attributes
        result += '>'
    elif attributes:
        #print( "We are losing attributes here:", attributes ); halt
        result += '<' + attributes + '>'
    if element.text: result += element.text
    for subelement in element:
        result += getFlattenedXML( subelement, subelement.tag + ' in ' + locationString, idString, level+1 ) # Recursive call
    if level:
        result += '</' + element.tag + '>'
    if element.tail and element.tail.strip(): result += ' ' + element.tail.strip()
    #else: print( "getFlattenedXML: Result is {!r}".format( result ) )
    return result
# end of BibleOrgSysGlobals.getFlattenedXML


##########################################################################################################
#
# Fixing strings
#

def applyStringAdjustments( originalText, adjustmentList ):
    """
    Applies the list of adjustments to the text and returns the new text.

    The adjustmentList is a list object containing 3-tuples with:
        1/ index where field should be found (in originalText)
        2/ findString (null for a pure insert)
        3/ replaceString (often a different length)

    For example, given "The quick brown fox jumped over the lazy brown dog."
                        012345678901234567890123456789012345678901234567890
                                  1         2         3         4         5
        applying adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
            (note that all of the above indexes refer to the original string before any substitutions)
        gives "A very quick orange fox tripped over the fat dog."
    """
    text = originalText
    offset = 0
    for ix, findStr, replaceStr in sorted(adjustmentList): # sorted with lowest index first
        lenFS, lenRS = len(findStr), len(replaceStr)
        if debugFlag: assert text[ix+offset:ix+offset+lenFS] == findStr # Our find string must be there
        elif text[ix+offset:ix+offset+lenFS] != findStr:
            logging.error( "applyStringAdjustments programming error -- given bad data for {!r}: {}".format( originalText, adjustmentList ) )
        #print( "before", repr(text) )
        text = text[:ix+offset] + replaceStr + text[ix+offset+lenFS:]
        #print( " after", repr(text) )
        offset += lenRS - lenFS
    return text
# end of BibleOrgSysGlobals.applyStringAdjustments


##########################################################################################################
#
# Reloading a saved Python object from the cache
#

def pickleObject( theObject, filename, folderName=None, disassembleObjectFlag=False ):
    """
    Writes the object to a .pickle file that can be easily loaded into a Python3 program.
        If folderName is None (or missing), defaults to the default cache folderName specified above.
        Creates the folderName(s) if necessary.

    disassembleObjectFlag is used to find segfaults by pickling the object piece by piece.
    """
    assert theObject is not None
    assert filename
    if folderName is None: folderName = DEFAULT_CACHE_FOLDER
    filepath = filename # default
    if folderName:
        if not os.access( folderName, os.R_OK ): # Make the folderName hierarchy if necessary
            os.makedirs( folderName )
        filepath = os.path.join( folderName, filename )
    if verbosityLevel > 2: print( _("Saving object to {}...").format( filepath ) )

    if disassembleObjectFlag: # Pickles an object attribute by attribute (to help narrow down segfault)
        print( '\nobject', disassembleObjectFlag, dir(theObject) )
        for name in dir( theObject ):
            a = theObject.__getattribute__( name )
            t = type( a )
            ts = str( t )
            f = 'pickle' + name
            print( 'attrib', name, ts )
            if '__' not in name and 'method' not in ts:
                print( '  go' )
                if name=='books':
                    print( '  books' )
                    for bn in a:
                        print( '     ', bn )
                        b = a[bn]
                        print( b.BBB )
                        pickleObject( b, f, folderName )
                else:
                    pickleObject( a, f, folderName, disassembleObjectFlag=True )
            else: print( '  skip' )

    with open( filepath, 'wb' ) as pickleOutputFile:
        pickle.dump( theObject, pickleOutputFile, pickle.HIGHEST_PROTOCOL )
# end of BibleOrgSysGlobals.pickleObject


def unpickleObject( filename, folderName=None ):
    """
    Reads the object from the file and returns it.

    NOTE: The class for the object must, of course, be loaded already (at the module level).
    """
    assert filename
    if folderName is None: folderName = DEFAULT_CACHE_FOLDER
    filepath = os.path.join( folderName, filename )
    if verbosityLevel > 2: print( _("Loading object from pickle file {}...").format( filepath ) )
    with open( filepath, 'rb') as pickleInputFile:
        return pickle.load( pickleInputFile ) # The protocol version used is detected automatically, so we do not have to specify it
# end of BibleOrgSysGlobals.unpickleObject


##########################################################################################################
#
# Default program setup routine

def setup( ShortProgName, ProgVersion, loggingFolderPath=None ):
    """
    Does the initial set-up for our scripts / programs.

    Sets up logging to a file in the default logging folderName.

    Returns the parser object
        so that custom command line parameters can be added
        then addStandardOptionsAndProcess must be called on it.
    """
    if debuggingThisModule:
        print( "BibleOrgSysGlobals.setup( {}, {}, {} )".format( repr(ShortProgName), repr(ProgVersion), repr(loggingFolderPath) ) )
    setupLoggingToFile( ShortProgName, ProgVersion, folderPath=loggingFolderPath )
    logging.info( "{} v{} started".format( ShortProgName, ProgVersion ) )

    if verbosityLevel > 2:
        print( "  This program comes with ABSOLUTELY NO WARRANTY." )
        print( "  It is free software, and you are welcome to redistribute it under certain conditions." )
        print( "  See the license in file 'gpl-3.0.txt' for more details.\n" )

    # Handle command line parameters
    parser = OptionParser( version="v{}".format( ProgVersion ) )
    return parser
# end of BibleOrgSysGlobals.setup


##########################################################################################################
#
# Verbosity and debug settings
#

def setVerbosity( verbosityLevelParameter ):
    """Sets the VerbosityLevel global variable to an integer value depending on the Verbosity control."""

    global verbosityString, verbosityLevel
    if isinstance( verbosityLevelParameter, str ):
        if verbosityLevelParameter == 'Silent':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 0
        elif verbosityLevelParameter == 'Quiet':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 1
        elif verbosityLevelParameter == 'Normal':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 2
        elif verbosityLevelParameter == 'Informative':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 3
        elif verbosityLevelParameter == 'Verbose':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 4
        else: logging.error( "Invalid '" + verbosityLevelParameter + "' verbosity parameter" )
    else: # assume it's an integer
        if verbosityLevelParameter == 0:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Silent'
        elif verbosityLevelParameter == 1:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Quiet'
        elif verbosityLevelParameter == 2:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Normal'
        elif verbosityLevelParameter == 3:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Informative'
        elif verbosityLevelParameter == 4:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Verbose'
        else: logging.error( "Invalid '" + verbosityLevelParameter + "' verbosity parameter" )

    if debugFlag:
        print( '  Verbosity =', verbosityString )
        print( '  VerbosityLevel =', verbosityLevel )
# end of BibleOrgSysGlobals.setVerbosity


def setDebugFlag( newValue=True ):
    """ Set the debug flag. """
    global debugFlag
    debugFlag = newValue
    if (debugFlag and verbosityLevel> 2) or verbosityLevel>3:
        print( '  debugFlag =', debugFlag )
# end of BibleOrgSysGlobals.setDebugFlag


def setStrictCheckingFlag( newValue=True ):
    """ See the strict checking flag. """
    global strictCheckingFlag
    strictCheckingFlag = newValue
    if (strictCheckingFlag and verbosityLevel> 2) or verbosityLevel>3:
        print( '  strictCheckingFlag =', strictCheckingFlag )
# end of BibleOrgSysGlobals.setStrictCheckingFlag


def addStandardOptionsAndProcess( parserObject, exportAvailable=False ):
    """
    Adds our standardOptions to the command line parser.
    """
    global commandLineOptions, commandLineArguments, maxProcesses
    if debuggingThisModule:
        print( "BibleOrgSysGlobals.addStandardOptionsAndProcess( ..., {} )".format( exportAvailable ) )

    parserObject.add_option( "-s", "--silent", action="store_const", dest="verbose", const=0, help="output no information to the console" )
    parserObject.add_option( "-q", "--quiet", action="store_const", dest="verbose", const=1, help="output less information to the console" )
    parserObject.add_option( "-i", "--informative", action="store_const", dest="verbose", const=3, help="output more information to the console" )
    parserObject.add_option( "-v", "--verbose", action="store_const", dest="verbose", const=4, help="output lots of information for the user" )
    parserObject.add_option( "-e", "--errors", action="store_true", dest="errors", default=False, help="log errors to console" )
    parserObject.add_option( "-w", "--warnings", action="store_true", dest="warnings", default=False, help="log warnings and errors to console" )
    parserObject.add_option( "-d", "--debug", action="store_true", dest="debug", default=False, help="output even more information for the programmer/debugger" )
    parserObject.add_option( "-1", "--single", action="store_true", dest="single", default=False, help="don't use multiprocessing (that's the digit one)" )
    parserObject.add_option( "-c", "--strict", action="store_true", dest="strict", default=False, help="perform very strict checking of all input" )
    if exportAvailable:
        parserObject.add_option("-x", "--export", action="store_true", dest="export", default=False, help="export the data file(s)")
    commandLineOptions, commandLineArguments = parserObject.parse_args()
    if commandLineOptions.errors and commandLineOptions.warnings:
        parserObject.error( "options -e and -w are mutually exclusive" )

    setVerbosity( commandLineOptions.verbose if commandLineOptions.verbose is not None else 2)
    if commandLineOptions.debug: setDebugFlag()

    # Determine console logging levels
    if commandLineOptions.warnings: addConsoleLogging( logging.WARNING if not debugFlag else logging.DEBUG )
    elif commandLineOptions.errors: addConsoleLogging( logging.ERROR )
    else: addConsoleLogging( logging.CRITICAL ) # default
    if commandLineOptions.strict: setStrictCheckingFlag()

    # Determine multiprocessing strategy
    maxProcesses = os.cpu_count()
    if maxProcesses > 1: maxProcesses = maxProcesses * 8 // 10 # Use 80% of them so other things keep working also
    if commandLineOptions.single: maxProcesses = 1
    if debugFlag:
        maxProcesses = 1 # Limit to one process
        print( "  commandLineOptions: {}".format( commandLineOptions ) )
        print( "  commandLineArguments: {}".format( commandLineArguments ) )
# end of BibleOrgSysGlobals.addStandardOptionsAndProcess


def printAllGlobals( indent=None ):
    """ Print all global variables (for debugging usually). """
    if indent is None: indent = 2
    print( "{}commandLineOptions: {}".format( ' '*indent, commandLineOptions ) )
    print( "{}commandLineArguments: {}".format( ' '*indent, commandLineArguments ) )
    print( "{}debugFlag: {}".format( ' '*indent, debugFlag ) )
    print( "{}maxProcesses: {}".format( ' '*indent, maxProcesses ) )
    print( "{}verbosityString: {}".format( ' '*indent, verbosityString ) )
    print( "{}verbosityLevel: {}".format( ' '*indent, verbosityLevel ) )
    print( "{}strictCheckingFlag: {}".format( ' '*indent, strictCheckingFlag ) )
# end of BibleOrgSysGlobals.printAllGlobals


def closedown( ProgName, ProgVersion ):
    """
    Does all the finishing off for the program.
    """
    logging.info( "{} v{} finished.".format( ProgName, ProgVersion ) )
# end of BibleOrgSysGlobals.closedown



def demo():
    """
    Demo program to handle command line parameters
        and then demonstrate some basic functions.
    """
    if verbosityLevel>0: print( ProgNameVersion )
    if verbosityLevel>2: printAllGlobals()

    # Demonstrate peekAtFirstLine function
    line1a = peekIntoFile( "Bible.py", numLines=2 ) # Simple filename
    print( "Bible.py starts with {}".format( repr(line1a) ) )
    line1b = peekIntoFile( "ReadMe.txt", "Tests/", 3 ) # Filename and folderName
    print( "ReadMe.txt starts with {}".format( repr(line1b) ) )
    line1c = peekIntoFile( "DataFiles/BibleBooksCodes.xml" ) # Filepath
    print( "BibleBooksCodes.xml starts with {}".format( repr(line1c) ) )

    print( "\nFirst one made string safe: {}".format( repr( makeSafeString( line1a[0] ) ) ) )
    print( "First one made filename safe: {}".format( repr( makeSafeFilename( line1a[0] ) ) ) )
    print( "Last one made string safe: {}".format( repr( makeSafeString( line1c ) ) ) )
    print( "Last one made filename safe: {}".format( repr( makeSafeFilename( line1c ) ) ) )

    text = "The quick brown fox jumped over the lazy brown dog."
    adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
    print( "\n{}->{}".format( repr(text), repr( applyStringAdjustments( text, adjustments ) ) ) )

    print( "\ncpu_count", os.cpu_count() )
# end of BibleOrgSysGlobals.demo


setVerbosity( verbosityString )
if __name__ != '__main__':
    # Load Bible data sets that are globally useful
    from BibleBooksCodes import BibleBooksCodes
    BibleBooksCodes = BibleBooksCodes().loadData()
    from USFMMarkers import USFMMarkers
    USFMMarkers = USFMMarkers().loadData()
    USFMParagraphMarkers = USFMMarkers.getNewlineMarkersList( 'CanonicalText' )
    #print( len(USFMParagraphMarkers), sorted(USFMParagraphMarkers) )
    #for marker in ( ):
        #print( marker )
        #USFMParagraphMarkers.remove( marker )
    # was 30 ['cls', 'li1', 'li2', 'li3', 'li4', 'm', 'mi', 'p', 'pc', 'ph1', 'ph2', 'ph3', 'ph4',
    #    'pi1', 'pi2', 'pi3', 'pi4', 'pm', 'pmc', 'pmo', 'pmr', 'pr', 'q1', 'q2', 'q3', 'q4',
    #    'qm1', 'qm2', 'qm3', 'qm4']
    # now 34 ['cls', 'li1', 'li2', 'li3', 'li4', 'm', 'mi', 'nb', 'p', 'pc', 'ph1', 'ph2', 'ph3', 'ph4',
    #    'pi1', 'pi2', 'pi3', 'pi4', 'pm', 'pmc', 'pmo', 'pmr', 'pr', 'q1', 'q2', 'q3', 'q4', 'qa', 'qc',
    #    'qm1', 'qm2', 'qm3', 'qm4', 'qr']
    #print( len(USFMParagraphMarkers), sorted(USFMParagraphMarkers) ); halt

if __name__ == '__main__':
    import multiprocessing

    # Configure basic Bible Organisational System (BOS) set-up
    parser = setup( ShortProgName, ProgVersion )
    addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    closedown( ShortProgName, ProgVersion )
# end of BibleOrgSysGlobals.py