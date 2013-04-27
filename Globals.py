#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Globals.py
#   Last modified: 2013-04-27 (also update versionString below)
#
# Module handling Global variables for our Bible Organisational System
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
Module handling global variables
    and some useful general functions.
"""

progName = "Globals"
versionString = "0.15"

import logging, os.path


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
loggingShortFormat = '%(levelname)8s: %(message)s'
loggingLongFormat = '%(asctime)s %(levelname)8s: %(message)s'

def setup_logfile( folder, progName ):
    """Sets up the main logfile for the program and returns the full pathname."""
    # Gets called from our demo() function when program starts up
    filename = progName + '_log.txt'
    fullFilename = os.path.join( folder, filename )

    # Create the folder if necessary
    if not os.access( folder, os.W_OK ):
        os.makedirs( folder ) # Works for an absolute or a relative pathname

    # Rename the existing file to a backup copy if it already exists
    if os.access( fullFilename, os.F_OK ):
        if __name__ == '__main__':
            print ( fullFilename, 'already exists -- renaming it first!' )
        if os.access( fullFilename+'.bak', os.F_OK ):
            os.remove( fullFilename+'.bak' )
        os.rename( fullFilename, fullFilename+'.bak' )

    # Now setup our new log file
    setLevel = logging.INFO
    if booleanControl( 'Debug' ): setLevel = logging.DEBUG
    logging.basicConfig( filename=fullFilename, level=setLevel, format=loggingShortFormat, datefmt=loggingDateFormat )

    # Now add a handler to also send ERROR and higher to console
    stderr_handler = logging.StreamHandler() # StreamHandler with no parameters defaults to sys.stderr
    if verbosityLevel == 0: # Silent
        stderr_handler.setLevel( logging.CRITICAL )
    elif verbosityLevel == 4: # Verbose
        stderr_handler.setLevel( logging.WARNING )
    else: # Quiet or normal
        stderr_handler.setLevel( logging.ERROR )
    root = logging.getLogger()  # No param means get the root logger
    root.addHandler(stderr_handler)
    return fullFilename
# end of Globals.setup_logfile


def add_logfile( folder, projectName ):
    """Adds an extra project specific log file to the logger."""
    filename = projectName + '_log.txt'
    fullFilename = os.path.join( folder, filename )

    # Create the folder if necessary
    if not os.access( folder, os.W_OK ):
        os.makedirs( folder ) # Works for an absolute or a relative pathname

    # Rename the existing file to a backup copy if it already exists
    if os.access( fullFilename, os.F_OK ):
        if __name__ == '__main__':
            print ( fullFilename, 'already exists -- renaming it first!' )
        if os.access( fullFilename+'.bak', os.F_OK ):
            os.remove( fullFilename+'.bak' )
        os.rename( fullFilename, fullFilename+'.bak' )

    projectHandler = logging.FileHandler( fullFilename )
    projectHandler.setFormatter( logging.Formatter( loggingShortFormat, loggingDateFormat ) )
    projectHandler.setLevel( logging.INFO )
    root = logging.getLogger()
    root.addHandler( projectHandler )
    return fullFilename, projectHandler
# end of Globals.add_logfile


def remove_logfile( projectHandler ):
    """Removes the project specific logger."""
    root = logging.getLogger()  # No param means get the root logger
    root.removeHandler( projectHandler )
# end of Globals.remove_logfile


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
        if logErrorsFlag: logging.warning( "Seems we couldn't decode Unicode in '{}'".format( filepath ) ) # Could be binary or a different encoding
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

        if Globals.verbosityLevel > 3: print( s, type(o), repr(o) )

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)
# end of Globals.totalSize


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
        if filename1==filename2: print( "Comparing {} files in folders {} and {}...".format( repr(filename1), repr(folder1), repr(folder2) ) )
        else: print( "Comparing files {} and {}...".format( repr(filename1), repr(filename2) ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        if logErrorsFlag: logging.error( "Globals.fileCompare: File1 '{}' is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        if logErrorsFlag: logging.error( "Globals.fileCompare: File2 '{}' is unreadable".format( filepath2 ) )
        return None

    # Read the files
    lineCount, lines1 = 0, []
    with open( filepath1, 'rt' ) as file1:
        for line in file1:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2: print( "      Detected UTF-16 Byte Order Marker in file1" )
                line = line[1:] # Remove the UTF-8 Byte Order Marker
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines1.append( line )
    lineCount, lines2 = 0, []
    with open( filepath2, 'rt' ) as file2:
        for line in file2:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2: print( "      Detected UTF-16 Byte Order Marker in file2" )
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
                    .format( k, repr(lines1[k]), len(lines1[k]), k, repr(lines2[k]), len(lines2[k]) ) )
            equalFlag = False
            diffCount += 1
            if diffCount > exitCount: break

    return equalFlag
# end of Globals.fileCompare


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
        if logErrorsFlag: logging.error( "Globals.fileCompareXML: File1 '{}' is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        if logErrorsFlag: logging.error( "Globals.fileCompareXML: File2 '{}' is unreadable".format( filepath2 ) )
        return None

    # Load the files
    from xml.etree.cElementTree import ElementTree
    tree1 = ElementTree().parse( filepath1 )
    tree2 = ElementTree().parse( filepath2 )

    def compareElements( element1, element2 ):
        """
        """
        nonlocal diffCount, location
        if element1.tag != element2.tag:
            if printFlag: print( "Element tags differ ({} and {}) at {}".format( repr(element1.tag), repr(element2.tag), location ) )
            diffCount += 1
            if diffCount > exitCount: return
            location.append( "{}/{}".format( element1.tag, element2.tag ) )
        else: location.append( element1.tag )
        attribs1, attribs2 = element1.items(), element2.items()
        if len(attribs1) != len(attribs2):
            if printFlag: print( "Number of attributes differ ({} and {}) at {}".format( len(attribs1), len(attribs2), location ) )
            diffCount += 1
            if diffCount > exitCount: return
        for avPair in attribs1:
            if avPair not in attribs2:
                if printFlag: print( "File1 has {} but not in file2 {} at {}".format( avPair, attribs2, location ) )
                diffCount += 1
                if diffCount > exitCount: return
        for avPair in attribs2:
            if avPair not in attribs1:
                if printFlag: print( "File2 has {} but not in file1 {} at {}".format( avPair, attribs1, location ) )
                diffCount += 1
                if diffCount > exitCount: return
        if element1.text != element2.text:
            if ignoreWhitespace:
                if element1.text is None and not element2.text.strip(): pass
                elif element2.text is None and not element1.text.strip(): pass
                elif element1.text and element2.text and element1.text.strip()==element2.text.strip(): pass
                else:
                    if printFlag: print( "Element text differs:\n {}\n {}\n at {}".format( repr(element1.text), repr(element2.text), location ) )
                    diffCount += 1
                    if diffCount > exitCount: return
            else:
                if printFlag: print( "Element text differs:\n {}\n {}\n at {}".format( repr(element1.text), repr(element2.text), location ) )
                diffCount += 1
                if diffCount > exitCount: return
        if element1.tail != element2.tail:
            if ignoreWhitespace:
                if element1.tail is None and not element2.tail.strip(): pass
                elif element2.tail is None and not element1.tail.strip(): pass
                else:
                    if printFlag: print( "Element tail differs:\n {}\n {}\n at {}".format( repr(element1.tail), repr(element2.tail), location ) )
                    diffCount += 1
                    if diffCount > exitCount: return
            else:
                if printFlag: print( "Element tail differs:\n {}\n {}\n at {}".format( repr(element1.tail), repr(element2.tail), location ) )
                diffCount += 1
                if diffCount > exitCount: return
        if len(element1) != len(element2):
            if printFlag: print( "Number of subelements differ ({} and {}) at {}".format( len(element1), len(element2), location ) )
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
# end of Globals.fileCompareXML


##########################################################################################################
#
# Validating XML fields (from element tree)
#

def checkXMLNoText( element, locationString, idString=None ):
    """ Give a warning if the element text contains anything other than whitespace. """
    if logErrorsFlag and element.text and element.text.strip(): logging.warning( "{}Unexpected '{}' element text in {}".format( (idString+' ') if idString else '', element.text, locationString ) )

def checkXMLNoTail( element, locationString, idString=None ):
    """ Give a warning if the element tail contains anything other than whitespace. """
    if logErrorsFlag and element.tail and element.tail.strip(): logging.warning( "{}Unexpected '{}' element tail in {}".format( (idString+' ') if idString else '', element.tail, locationString ) )

def checkXMLNoAttributes( element, locationString, idString=None ):
    if logErrorsFlag:
        for attrib,value in element.items():
            logging.warning( "{}Unexpected '{}' attribute ({}) in {}".format( (idString+' ') if idString else '', attrib, value, locationString ) )

def checkXMLNoSubelements( element, locationString, idString=None ):
    if logErrorsFlag:
        for subelement in element.getchildren():
            logging.warning( "{}Unexpected '{}' sub-element ({}) in {}".format( (idString+' ') if idString else '', subelement.tag, subelement.text, locationString ) )


##########################################################################################################
#
# Verbosity and debug settings
#

def setVerbosity( verbosityLevelParameter ):
    """Sets the VerbosityLevel global variable to an integer value depending on the Verbosity control."""

    global verbosityString, verbosityLevel
    verbosityLevel = verbosityLevelParameter
    if verbosityLevel == 0:
        verbosityString = 'Silent'
    elif verbosityLevel == 1:
        verbosityString = 'Quiet'
    elif verbosityLevel == 2:
        verbosityString = 'Normal'
    elif verbosityLevel == 3:
        verbosityString = 'Informative'
    elif verbosityLevel == 4:
        verbosityString = 'Verbose'
    else: logging.error( "Invalid '" + verbosityLevel + "' verbosity parameter" )

    if debugFlag:
        print( '  Verbosity =', verbosityString )
        print( '  VerbosityLevel =', verbosityLevel )
# end of Globals.setVerbosity


def setVerbosityLevel( verbosityStringParameter ):
    """Sets the VerbosityLevel global variable to an integer value depending on the Verbosity control."""

    global verbosityString, verbosityLevel
    verbosityString = verbosityStringParameter
    if verbosityString == 'Silent':
        verbosityLevel = 0
    elif verbosityString == 'Quiet':
        verbosityLevel = 1
    elif verbosityString == 'Normal':
        verbosityLevel = 2
    elif verbosityString == 'Informative':
        verbosityLevel = 3
    elif verbosityString == 'Verbose':
        verbosityLevel = 4
    else: logging.error( "Invalid '" + verbosityString + "' verbosity parameter" )

    if debugFlag:
        print( '  VerbosityLevel =', verbosityLevel )
        print( '  Verbosity =', verbosityString )
# end of Globals.setVerbosityLevel


def setDebugFlag( newValue=True ):
    """ Set the debug flag. """
    global debugFlag
    debugFlag = newValue
    if debugFlag or verbosityLevel>3:
        print( '  debugFlag =', debugFlag )
# end of Globals.setDebugFlag


def setStrictCheckingFlag( newValue=True ):
    """ See the strict checking flag. """
    global strictCheckingFlag
    strictCheckingFlag = newValue
    if strictCheckingFlag or verbosityLevel>3:
        print( '  strictCheckingFlag =', strictCheckingFlag )
# end of Globals.setStrictCheckingFlag


def setLogErrorsFlag( newValue=True ):
    """ See the error logging checking flag. """
    global logErrorsFlag
    logErrorsFlag = newValue
    if logErrorsFlag or verbosityLevel>3:
        print( '  logErrorsFlag =', logErrorsFlag )
# end of Globals.setLogErrorsFlag


def addStandardOptionsAndProcess( parserObject ):
    """ Adds our standardOptions to the command line parser. """
    global commandLineOptions, commandLineArguments
    global strictCheckingFlag
    parserObject.add_option("-s", "--silent", action="store_const", dest="verbose", const=0, help="output no information to the console")
    parserObject.add_option("-q", "--quiet", action="store_const", dest="verbose", const=1, help="output less information to the console")
    parserObject.add_option("-i", "--informative", action="store_const", dest="verbose", const=3, help="output more information to the console")
    parserObject.add_option("-v", "--verbose", action="store_const", dest="verbose", const=4, help="output lots of information for the user")
    parserObject.add_option("-t", "--strict", action="store_true", dest="strict", default=False, help="perform very strict checking of all input")
    parserObject.add_option("-l", "--log", action="store_true", dest="log", default=False, help="log errors to console")
    parserObject.add_option("-d", "--debug", action="store_true", dest="debug", default=False, help="output even more information for the programmer/debugger")
    commandLineOptions, commandLineArguments = parserObject.parse_args()
    if commandLineOptions.strict: setStrictCheckingFlag()
    if commandLineOptions.log: setLogErrorsFlag()
    if commandLineOptions.debug: setDebugFlag()
    setVerbosity( commandLineOptions.verbose if commandLineOptions.verbose is not None else 2)
    if debugFlag:
        print( "  commandLineOptions: {}".format( commandLineOptions ) )
        print( "  commandLineArguments: {}".format( commandLineArguments ) )
# end of Globals.addStandardOptionsAndProcess


def printAllGlobals( indent=None ):
    """ Print all global variables. """
    if indent is None: indent = 2
    print( "{}commandLineOptions: {}".format( ' '*indent, commandLineOptions ) )
    print( "{}commandLineArguments: {}".format( ' '*indent, commandLineArguments ) )
    print( "{}debugFlag: {}".format( ' '*indent, debugFlag ) )
    print( "{}verbosityString: {}".format( ' '*indent, verbosityString ) )
    print( "{}verbosityLevel: {}".format( ' '*indent, verbosityLevel ) )
    print( "{}strictCheckingFlag: {}".format( ' '*indent, strictCheckingFlag ) )
    print( "{}logErrorsFlag: {}".format( ' '*indent, logErrorsFlag ) )
# end of Globals.printAllGlobals



# Global variables
#=================

commandLineOptions, commandLineArguments = None, None

strictCheckingFlag = logErrorsFlag = debugFlag = False
verbosityLevel = None
verbosityString = 'Normal'
setVerbosityLevel( verbosityString )


# Global Bible data sets
#=======================

if __name__ != '__main__':
    from BibleBooksCodes import BibleBooksCodes
    BibleBooksCodes = BibleBooksCodes().loadData()
    from USFMMarkers import USFMMarkers
    USFMMarkers = USFMMarkers().loadData()



def demo():
    """
    Demo program to handle command line parameters
        and then demonstrate some basic functions.
    """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    addStandardOptionsAndProcess( parser )

    if verbosityLevel>0: print( "{} V{}".format( progName, versionString ) )
    if verbosityLevel>2:
        printAllGlobals()

    # Demonstrate peekAtFirstLine function
    line1 = peekIntoFile( "Globals.py", numLines=2 ) # Simple filename
    print( "Globals.py starts with '{}'".format( line1 ) )
    line1 = peekIntoFile( "ReadMe.txt", "Tests/", 3 ) # Filename and folder
    print( "ReadMe.txt starts with '{}'".format( line1 ) )
    line1 = peekIntoFile( "DataFiles/BibleBooksCodes.xml" ) # Filepath
    print( "BibleBooksCodes.xml starts with '{}'".format( line1 ) )
# end of demo

if __name__ == '__main__':
    demo()
## end of Globals.py