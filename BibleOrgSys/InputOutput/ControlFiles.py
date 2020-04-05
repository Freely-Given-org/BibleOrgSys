#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ControlFiles.py
#
# Control file module
#
# Copyright (C) 2008-2017 Robert Hunt
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
Module for reading and parsing simple text control files.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2017-03-08' # by RJH
SHORT_PROGRAM_NAME = "ControlFiles"
PROGRAM_NAME = "Control Files"
PROGRAM_VERSION = '0.06'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals


def readListFile( folder, filename, outputList, debug=False ):
    """
    Read a simple list file into a list (checking only for duplicate lines)
    """
    if debug:
        if not isinstance( outputList, list): raise ValueError('List expected here')
        oldlen = len( outputList )

    if Controls['VerbosityLevel'] > 1: print( '    Loading list file', filename + '…' )
    lines = []
    with open( os.path.join( folder, filename ), encoding='utf-8' ) as myFile: # Automatically closes the file when done
        for line in myFile:
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            if line[0]=='#': continue # Just discard comment lines
            if line in lines:
                logging.warning( 'DUPLICATE LINE IGNORED in list file: ' + line )
                continue
            lines.append( line )
            outputList.append( line )
    if debug: print( '      Had', oldlen, 'values, added', len(outputList)-oldlen, 'new list values, now have', len(outputList) )
# end of readListFile


def readControlFile( folder, filename, controls, haveLog=True, debug=False ):
    """
    Read and parse a control (text) file into the given list.
    """

    displayFolder = folder
    if not displayFolder:
        displayFolder = 'current folder (' + os.getcwd() + ')'
    #if 'VerbosityLevel' in GlobalControls and GlobalControls['VerbosityLevel'] > 1: print( '  Loading control file ' + filename + ' from ' + displayFolder + '…' )
    if debug: oldlen = len(controls)

    with open( os.path.join( folder, filename ), encoding='utf-8' ) as myFile: # Automatically closes the file when done
        for line in myFile:
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            if line[0]=='#': continue # Just discard comment lines
            if '=' not in line:
                if haveLog: logging.error( 'LINE IGNORED: Unknown format for control line: ' + line )
                else: print( 'LINE IGNORED: Unknown format for control line: ' + line )
                continue
            si = line.index( '=' )
            name = line[:si].strip() #Marker is from after backslash and before the equals sign
            value = line[si+1:].strip() # All the rest is the text field
            if not name:
                if haveLog: logging.error( 'LINE IGNORED: Missing control name: ' + line )
                else: print( 'LINE IGNORED: Missing control name: ' + line )
                continue
            if not value:
                value = ''
                #if haveLog: logging.error( 'LINE IGNORED: Missing control value: ' + line )
                #else: print( 'LINE IGNORED: Missing control value: ' + line )
                #continue
            if name in controls:
                if value != controls[name]:
                    if haveLog: logging.error( 'LINE IGNORED: Duplicate control name: ' + line + ", current value is '" + str(controls[name]) + "'" )
                    else: print( 'LINE IGNORED: Duplicate control name: ' + line + ", current value is '" + str(controls[name]) + "'" )
                else: # New value is same as old one
                    if haveLog: logging.info( 'LINE IGNORED: Duplicate control name: ' + line )
                    else: print( 'LINE IGNORED: Duplicate control name: ' + line )
                continue
            controls[name] = value
    if debug: print( '    Added', len(controls)-oldlen, 'new control values.' )
# end of readControlFile


def booleanValue ( value ):
    """Return True or False is value is something sensible.
        Else return None."""

    ix = value.find( '#' )
    if ix != -1: # Could be a comment at the end of the line
        value = value[:ix].rstrip()

    lcvalue = value.lower()
    if lcvalue in ['true','yes', 'on']: return True
    if lcvalue in ['false','no','off']: return False
# end of booleanValue


def booleanControl( controlName, controlDict=None ):
    """Return True if the given control name exists in the control dictionary
        and has a suitable value such as TRUE or ON."""
    if controlDict==None: controlDict = Controls

    if controlName not in controlDict:
        return False

    result = booleanValue( controlDict[controlName] )
    if result is None:
        logging.error( "Unknown value for controlname '" + controlName + "' = '" + str(controlDict[controlName]) + "'")
    return result
# end of booleanControl



def demo() -> None:
    """
    Demo program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel>0: print( programNameVersion )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ControlFiles.py
