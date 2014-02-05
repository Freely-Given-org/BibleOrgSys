#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Globals.py
#   Last modified: 2014-02-06 by RJH (also update ProgVersion below)
#
# Module handling Global variables for our Bible Organisational System
#
# Copyright (C) 2010-2014 Robert Hunt
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
Module handling global variables
    and some useful general functions.

Contains functions:
    setupLoggingToFile( ProgName, ProgVersion, folder=None )
    addConsoleLogging()
    addLogfile( projectName, folder=None )
    removeLogfile( projectHandler )

    makeSafeFilename( someName )
    makeSafeXML( someString )
    makeSafeString( someString )
    peekIntoFile( filenameOrFilepath, folder=None, numLines=1 )

    totalSize( o, handlers={} )

    fileCompare( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 )
    fileCompareXML( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10, ignoreWhitespace=True )

    checkXMLNoText( element, locationString, idString=None )
    checkXMLNoTail( element, locationString, idString=None )
    checkXMLNoAttributes( element, locationString, idString=None )
    checkXMLNoSubelements( element, locationString, idString=None )
    checkXMLNoSubelementsWithText( element, locationString, idString=None )
    getFlattenedXML( element, locationString, idString=None, level=0 )

    applyStringAdjustments( originalText, adjustmentList )

    pickleObject( theObject, filename, folder=None )
    unpickleObject( filename, folder=None )

    setup( ProgName, ProgVersion, loggingFolder=None )

    setVerbosity( verbosityLevelParameter )
    setDebugFlag( newValue=True )
    setStrictCheckingFlag( newValue=True )
    setLogErrorsFlag( newValue=True )

    addStandardOptionsAndProcess( parserObject )
    printAllGlobals( indent=None )

    closedown( ProgName, ProgVersion )

    demo()
"""

ProgName = "Globals"
ProgVersion = "0.37"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os.path, pickle
import multiprocessing
from optparse import OptionParser
from gettext import gettext as _


# Global variables
#=================

commandLineOptions, commandLineArguments = None, None

strictCheckingFlag = logErrorsFlag = debugFlag = False
maxProcesses = 1
verbosityLevel = None
verbosityString = 'Normal'


defaultLogFolder = 'Logs/' # Relative path
defaultcacheFolder = 'ObjectCache/' # Relative path



# Some language independant punctuation help
openingSpeechChars = """“«"‘‹¿¡"""
closingSpeechChars = """”»"’›?!"""
matchingOpeningCharacters = {'(':')', '[':']', '{':'}', '<':'>', '<<':'>>', '“':'”', '‘':'‘', '«':'»', '‹':'›', '¿':'?', '¡':'!', }
matchingCharacters = {'(':')',')':'(', '[':']',']':'[', '{':'}','}':'{', '<':'>','>':'<', '<<':'>>','>>':'<<',
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

def setupLoggingToFile( ProgName, ProgVersion, folder=None ):
    """Sets up the main logfile for the program and returns the full pathname."""
    # Gets called from our demo() function when program starts up
    filename = ProgName.replace('/','-').replace(':','_').replace('\\','_') + '_log.txt'
    if folder is None: folder = defaultLogFolder # relative path
    filepath = os.path.join( folder, filename )

    # Create the folder if necessary
    if not os.access( folder, os.W_OK ):
        os.makedirs( folder ) # Works for an absolute or a relative pathname

    # Rename the existing file to a backup copy if it already exists
    if os.access( filepath, os.F_OK ):
        if __name__ == '__main__':
            print ( filepath, 'already exists -- renaming it first!' )
        if os.access( filepath+'.bak', os.F_OK ):
            os.remove( filepath+'.bak' )
        os.rename( filepath, filepath+'.bak' )

    # Now setup our new log file
    setLevel = logging.DEBUG if debugFlag else logging.INFO
    logging.basicConfig( filename=filepath, level=setLevel, format=loggingLongFormat, datefmt=loggingDateFormat )

    return filepath
# end of setupLogging


def addConsoleLogging( consoleLoggingLevel=None ):
    # Now add a handler to also send ERROR and higher to console (depending on verbosity)
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
# end of addConsoleLogging


def addLogfile( projectName, folder=None ):
    """Adds an extra project specific log file to the logger."""
    filename = projectName + '_log.txt'
    if folder is None: folder = defaultLogFolder # relative path
    filepath = os.path.join( folder, filename )

    # Create the folder if necessary
    if not os.access( folder, os.W_OK ):
        os.makedirs( folder ) # Works for an absolute or a relative pathname

    # Rename the existing file to a backup copy if it already exists
    if os.access( filepath, os.F_OK ):
        if __name__ == '__main__':
            print ( filepath, 'already exists -- renaming it first!' )
        if os.access( filepath+'.bak', os.F_OK ):
            os.remove( filepath+'.bak' )
        os.rename( filepath, filepath+'.bak' )

    projectHandler = logging.FileHandler( filepath )
    projectHandler.setFormatter( logging.Formatter( loggingShortFormat, loggingDateFormat ) )
    projectHandler.setLevel( logging.INFO )
    root = logging.getLogger()
    root.addHandler( projectHandler )
    return filepath, projectHandler
# end of addLogfile


def removeLogfile( projectHandler ):
    """Removes the project specific logger."""
    root = logging.getLogger()  # No param means get the root logger
    root.removeHandler( projectHandler )
# end of removeLogfile


##########################################################################################################
#
# Make a string safe if it's going to be used as a filename
#
#       We don't want a malicious user to be able to gain access to the filesystem
#               by putting a filepath into a filename string.

def makeSafeFilename( someName ):
    """
    Replaces potentially unsafe characters in a name to make it suitable for a filename.
    """
    return someName.replace('/','-') \
        .replace('\\','_BACKSLASH_').replace(':','_COLON_').replace(';','_SEMICOLON_') \
        .replace('#','_HASH_').replace('?','_QUESTIONMARK_').replace('*','_ASTERISK_')
# end of makeSafeFilename


##########################################################################################################
#
# Make a string safe if it could be used in an XML document
#

def makeSafeXML( someString ):
    """
    Replaces special characters in a string to make it for XML.
    """
    return someString.replace('&','&amp;').replace('"','&quot;').replace('<','&lt;').replace('>','&gt;')
# end of makeSafeXML


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
# end of makeSafeString


##########################################################################################################
#
# Peek at the first line(s) of a file

def peekIntoFile( filenameOrFilepath, folder=None, numLines=1 ):
    """
    Reads and returns the first line of a text file as a string
        unless more than one line is requested
        in which case a list of strings is returned (including empty strings for empty lines).
    """
    assert( 1 <= numLines < 5 )
    filepath = os.path.join( folder, filenameOrFilepath ) if folder else filenameOrFilepath
    lines = []
    try:
        with open( filepath, 'rt' ) as possibleUSFMFile: # Automatically closes the file when done
            lineNumber = 0
            for line in possibleUSFMFile:
                lineNumber += 1
                if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                #print( thisFilename, lineNumber, line )
                if numLines==1: return line # Always returns the first line
                lines.append( line )
                if lineNumber >= numLines: return lines
    except UnicodeDecodeError:
        #if not filepath.lower().endswith( 'usfm-color.sty' ): # Seems this file isn't UTF-8, but we don't need it here anyway so ignore it
        logging.warning( "Seems we couldn't decode Unicode in '{}'".format( filepath ) ) # Could be binary or a different encoding
# end of peekIntoFile


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
# end of totalSize


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
        logging.error( "fileCompare: File1 '{}' is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( "fileCompare: File2 '{}' is unreadable".format( filepath2 ) )
        return None

    # Read the files
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

    len1, len2 = len(lines1), len(lines2 )
    equalFlag = True
    if len1 != len2:
        if printFlag: print( "Count of lines differ: file1={}, file2={}".format( len1, len2 ) )
        equalFlag = False

    diffCount = 0
    for k in range( 0, min( len1, len2 ) ):
        if lines1[k] != lines2[k]:
            if printFlag:
                print( "  {}:{} ({} chars)\n  {}:{} ({} chars)" \
                    .format( k+1, repr(lines1[k]), len(lines1[k]), k+1, repr(lines2[k]), len(lines2[k]) ) )
            equalFlag = False
            diffCount += 1
            if diffCount > exitCount:
                if printFlag and Globals.verbosityLevel > 1:
                    print( "fileCompare: stopped comparing after {} mismatches".format( exitCount ) )
                break

    return equalFlag
# end of fileCompare


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
        logging.error( "fileCompareXML: File1 '{}' is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( "fileCompareXML: File2 '{}' is unreadable".format( filepath2 ) )
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
# end of fileCompareXML


##########################################################################################################
#
# Validating XML fields (from element tree)
#

haltOnWarning = False # Used for XML debugging

def checkXMLNoText( element, locationString, idString=None ):
    """ Give a warning if the element text contains anything other than whitespace. """
    if element.text and element.text.strip():
        logging.warning( "{}Unexpected '{}' element text in {}".format( (idString+' ') if idString else '', element.text, locationString ) )
        if debugFlag and haltOnWarning: halt

def checkXMLNoTail( element, locationString, idString=None ):
    """ Give a warning if the element tail contains anything other than whitespace. """
    if element.tail and element.tail.strip():
        logging.warning( "{}Unexpected '{}' element tail in {}".format( (idString+' ') if idString else '', element.tail, locationString ) )
        if debugFlag and haltOnWarning: halt


def checkXMLNoAttributes( element, locationString, idString=None ):
    for attrib,value in element.items():
        logging.warning( "{}Unexpected '{}' attribute ({}) in {}".format( (idString+' ') if idString else '', attrib, value, locationString ) )
        if debugFlag and haltOnWarning: halt


def checkXMLNoSubelements( element, locationString, idString=None ):
    for subelement in element.getchildren():
        logging.warning( "{}Unexpected '{}' sub-element ({}) in {}".format( (idString+' ') if idString else '', subelement.tag, subelement.text, locationString ) )
        if debugFlag and haltOnWarning: halt


def checkXMLNoSubelementsWithText( element, locationString, idString=None ):
    """ Checks that the element doesn't have text AND subelements """
    if ( element.text and element.text.strip() ) \
    or ( element.tail and element.tail.strip() ):
        for subelement in element.getchildren():
            logging.warning( "{}Unexpected '{}' sub-element ({}) in {} with text/tail {}/{}" \
                .format( (idString+' ') if idString else '', subelement.tag, subelement.text, locationString,
                        element.text.strip() if element.text else element.text,
                        element.tail.strip() if element.tail else element.tail ) )
            if debugFlag and haltOnWarning: halt
# end of Globals.checkXMLNoSubelementsWithText


def getFlattenedXML( element, locationString, idString=None, level=0 ):
    """
    Return the XML nested inside the element as a text string.
    """
    result = ''
    if level: result += '<' + element.tag + '>' # For lower levels (other than the called one) need to add the tags
    if element.text: result += element.text
    # We ignore attributes here
    for subelement in element:
        result += getFlattenedXML( subelement, subelement.tag + ' in ' + locationString, idString, level+1 ) # Recursive call
    if level:
        result += '</' + element.tag + '>'
        if element.tail: result += element.tail
    #else: print( "getFlattenedXML: Result is '{}'".format( result ) )
    return result
# end of getFlattenedXML


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
        if debugFlag: assert( text[ix+offset:ix+offset+lenFS] == findStr ) # Our find string must be there
        elif text[ix+offset:ix+offset+lenFS] != findStr:
            logging.error( "applyStringAdjustments programming error -- given bad data for '{}': {}".format( originalText, adjustmentList ) )
        #print( "before", repr(text) )
        text = text[:ix+offset] + replaceStr + text[ix+offset+lenFS:]
        #print( " after", repr(text) )
        offset += lenRS - lenFS
    return text
# end of applyStringAdjustments


##########################################################################################################
#
# Reloading a saved Python object from the cache
#

def pickleObject( theObject, filename, folder=None, disassembleObjectFlag=False ):
    """
    Writes the object to a .pickle file that can be easily loaded into a Python3 program.
        If folder is None (or missing), defaults to the default cache folder specified above.
        Creates the folder(s) if necessary.

    disassembleObjectFlag is used to find segfaults by pickling the object piece by piece.
    """
    assert( theObject )
    assert( filename )
    if folder is None: folder = defaultcacheFolder
    filepath = filename # default
    if folder:
        if not os.access( folder, os.R_OK ): # Make the folder hierarchy if necessary
            os.makedirs( folder )
        filepath = os.path.join( folder, filename )
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
                        print( b.bookReferenceCode )
                        pickleObject( b, f, folder )
                else:
                    pickleObject( a, f, folder, disassembleObjectFlag=True )
            else: print( '  skip' )

    with open( filepath, 'wb' ) as pickleOutputFile:
        pickle.dump( theObject, pickleOutputFile )
# end of pickle


def unpickleObject( filename, folder=None ):
    """
    Reads the object from the file and returns it.

    NOTE: The class for the object must, of course, be loaded already (at the module level).
    """
    assert( filename )
    if folder is None: folder = defaultcacheFolder
    filepath = os.path.join( folder, filename )
    if verbosityLevel > 2: print( _("Loading object from pickle file {}...").format( filepath ) )
    with open( filepath, 'rb') as pickleInputFile:
        return pickle.load( pickleInputFile ) # The protocol version used is detected automatically, so we do not have to specify it
# end of unpickle


##########################################################################################################
#
# Default program setup routine

def setup( ProgName, ProgVersion, loggingFolder=None ):
    """
    Does the initial set-up for our scripts / programs.

    Sets up logging to a file in the default logging folder.

    Returns the parser object
        so that custom command line parameters can be added
        then addStandardOptionsAndProcess must be called on it.
    """
    setupLoggingToFile( ProgName, ProgVersion, loggingFolder )
    logging.info( "{} v{} started".format( ProgName, ProgVersion ) )

    if verbosityLevel > 2:
        print( "  This program comes with ABSOLUTELY NO WARRANTY." )
        print( "  It is free software, and you are welcome to redistribute it under certain conditions." )
        print( "  See the license in file 'gpl-3.0.txt' for more details.\n" )

    # Handle command line parameters
    parser = OptionParser( version="v{}".format( ProgVersion ) )
    return parser
# end of setup


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
# end of setVerbosity


def setDebugFlag( newValue=True ):
    """ Set the debug flag. """
    global debugFlag
    debugFlag = newValue
    if (debugFlag and verbosityLevel> 2) or verbosityLevel>3:
        print( '  debugFlag =', debugFlag )
# end of setDebugFlag


def setStrictCheckingFlag( newValue=True ):
    """ See the strict checking flag. """
    global strictCheckingFlag
    strictCheckingFlag = newValue
    if (strictCheckingFlag and verbosityLevel> 2) or verbosityLevel>3:
        print( '  strictCheckingFlag =', strictCheckingFlag )
# end of setStrictCheckingFlag


def setLogErrorsFlag( newValue=True ):
    """ See the error logging checking flag. """
    global logErrorsFlag
    logErrorsFlag = newValue
    if (logErrorsFlag and verbosityLevel> 2) or verbosityLevel>3:
        print( '  logErrorsFlag =', logErrorsFlag )
    if  logErrorsFlag: addConsoleLogging()
# end of setLogErrorsFlag


def addStandardOptionsAndProcess( parserObject, exportAvailable=False ):
    """ Adds our standardOptions to the command line parser. """
    global commandLineOptions, commandLineArguments, maxProcesses

    parserObject.add_option( "-s", "--silent", action="store_const", dest="verbose", const=0, help="output no information to the console" )
    parserObject.add_option( "-q", "--quiet", action="store_const", dest="verbose", const=1, help="output less information to the console" )
    parserObject.add_option( "-i", "--informative", action="store_const", dest="verbose", const=3, help="output more information to the console" )
    parserObject.add_option( "-v", "--verbose", action="store_const", dest="verbose", const=4, help="output lots of information for the user" )
    parserObject.add_option( "-e", "--errors", action="store_true", dest="errors", default=False, help="log errors to console" )
    parserObject.add_option( "-w", "--warnings", action="store_true", dest="warnings", default=False, help="log warnings and errors to console" )
    parserObject.add_option( "-d", "--debug", action="store_true", dest="debug", default=False, help="output even more information for the programmer/debugger" )
    parserObject.add_option( "-1", "--single", action="store_true", dest="single", default=False, help="don't use multiprocessing" )
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
    #if commandLineOptions.log: setLogErrorsFlag()

    # Determine multiprocessing strategy
    if 0: maxProcesses = multiprocessing.cpu_count()
    #if maxProcesses > 1: maxProcesses -= 1 # Leave one CPU alone (normally)
    if maxProcesses > 1: maxProcesses = maxProcesses * 8 // 10 # Use 80% of them so other things keep working also
    if commandLineOptions.single: maxProcesses = 1
    if debugFlag:
        maxProcesses = 1 # Limit to one process
        print( "  commandLineOptions: {}".format( commandLineOptions ) )
        print( "  commandLineArguments: {}".format( commandLineArguments ) )
# end of addStandardOptionsAndProcess


def printAllGlobals( indent=None ):
    """ Print all global variables. """
    if indent is None: indent = 2
    print( "{}commandLineOptions: {}".format( ' '*indent, commandLineOptions ) )
    print( "{}commandLineArguments: {}".format( ' '*indent, commandLineArguments ) )
    print( "{}debugFlag: {}".format( ' '*indent, debugFlag ) )
    print( "{}maxProcesses: {}".format( ' '*indent, maxProcesses ) )
    print( "{}verbosityString: {}".format( ' '*indent, verbosityString ) )
    print( "{}verbosityLevel: {}".format( ' '*indent, verbosityLevel ) )
    print( "{}strictCheckingFlag: {}".format( ' '*indent, strictCheckingFlag ) )
    print( "{}logErrorsFlag: {}".format( ' '*indent, logErrorsFlag ) )
# end of printAllGlobals


def closedown( ProgName, ProgVersion ):
    """
    Does all the finishing off for the program.
    """
    logging.info( "{} v{} finished.".format( ProgName, ProgVersion ) )
# end of closedown



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
    line1b = peekIntoFile( "ReadMe.txt", "Tests/", 3 ) # Filename and folder
    print( "ReadMe.txt starts with {}".format( repr(line1b) ) )
    line1c = peekIntoFile( "DataFiles/BibleBooksCodes.xml" ) # Filepath
    print( "BibleBooksCodes.xml starts with {}".format( repr(line1c) ) )

    print( "\nFirst one made filename safe: {}".format( repr( makeSafeFilename( line1a[0] ) ) ) )
    print( "Last one made string safe: {}".format( repr( makeSafeString( line1c ) ) ) )

    text = "The quick brown fox jumped over the lazy brown dog."
    adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
    print( "\n{}->{}".format( repr(text), repr( applyStringAdjustments( text, adjustments ) ) ) )
# end of demo

setVerbosity( verbosityString )
if __name__ != '__main__': # Load global Bible data sets
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
    # Configure basic set-up
    parser = setup( ProgName, ProgVersion )
    addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    closedown( ProgName, ProgVersion )
# end of Globals.py