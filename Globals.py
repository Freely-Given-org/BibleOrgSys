#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Globals.py
#
# Module handling Global variables for our Bible Organisational System
#   Last modified: 2011-01-13 (also update versionString below)
#
# Copyright (C) 2010-2011 Robert Hunt
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
Module handling global variables.
"""

progName = "Globals"
versionString = "0.06"

import logging, os.path


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
    # Gets called from our main() function when program starts up
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
# end of setup_logfile


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
# end of add_logfile


def remove_logfile( projectHandler ):
    """Removes the project specific logger."""
    root = logging.getLogger()  # No param means get the root logger
    root.removeHandler( projectHandler )
# end of remove_logfile


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
        verbosityString = 'Informative'
    else: logging.error( "Invalid '" + verbosityLevel + "' verbosity parameter" )

    if debugFlag:
        print( '  Verbosity =', verbosityString )
        print( '  VerbosityLevel =', verbosityLevel )
# end of setVerbosity


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
# end of setVerbosityLevel


def setDebugFlag( newValue=True ):
    """ See the debug flag. """
    global debugFlag
    debugFlag = newValue
    if debugFlag or verbosityLevel>3:
        print( '  debugFlag =', debugFlag )
# end of setDebugFlag


def addStandardOptionsAndProcess( parserObject ):
    """ Adds our standardOptions to the command line parser. """
    global commandLineOptions, commandLineArguments
    global strictCheckingFlag
    parserObject.add_option("-f", "--fast", action="store_true", dest="fast", default=False, help="disable strict datafile checking")
    parserObject.add_option("-s", "--silent", action="store_const", dest="verbose", const=0, help="output no information to the console")
    parserObject.add_option("-q", "--quiet", action="store_const", dest="verbose", const=1, help="output less information to the console")
    parserObject.add_option("-i", "--informative", action="store_const", dest="verbose", const=3, help="output more information to the console")
    parserObject.add_option("-v", "--verbose", action="store_const", dest="verbose", const=4, help="output lots of information for the user")
    parserObject.add_option("-d", "--debug", action="store_true", dest="debug", default=False, help="output even more information for the programmer/debugger")
    commandLineOptions, commandLineArguments = parserObject.parse_args()
    if commandLineOptions.debug: setDebugFlag()
    setVerbosity( commandLineOptions.verbose if commandLineOptions.verbose is not None else 2)
    if debugFlag:
        print( "  commandLineOptions: {}".format( commandLineOptions ) )
        print( "  commandLineArguments: {}".format( commandLineArguments ) )
    if commandLineOptions.fast: strictCheckingFlag = False
# end of addStandardOptionsAndProcess


def printAllGlobals( indent=None ):
    """ Print all global variables. """
    if indent is None: indent = 2
    print( "{}commandLineOptions: {}".format( ( ' '*indent, commandLineOptions) ) )
    print( "{}commandLineArguments: {}".format( ( ' '*indent, commandLineArguments) ) )
    print( "{}debugFlag: {}".format( ( ' '*indent, debugFlag) ) )
    print( "{}verbosityString: {}".format( ( ' '*indent, verbosityString) ) )
    print( "{}verbosityLevel: {}".format( ( ' '*indent, verbosityLevel) ) )
    print( "{}strictCheckingFlag: {}".format( ( ' '*indent, strictCheckingFlag) ) )
# end of printAllGlobals()


# Global variables
##################

commandLineOptions, commandLineArguments = None, None

debugFlag = False
verbosityString = 'Normal'
setVerbosityLevel( verbosityString )

strictCheckingFlag = True


def demo():
    """
    Demo program to handle command line parameters and then run what they want.
    """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    addStandardOptionsAndProcess( parser )

    if verbosityLevel>0: print( "{} V{}".format( progName, versionString ) )
    if verbosityLevel>2:
        printAllGlobals()
# end of demo

if __name__ == '__main__':
    demo()
## end of Globals.py
