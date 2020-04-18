#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# NoisyReplaceFunctions.py
#
# Functions for replace and regex replace which explain what they did.
#
# Copyright (C) 2018-2020 Robert Hunt
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
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Functions for replace and regex replace which explain what they did.

    noisyFind( text, this, reporterFunction=None )
    noisyRegExFind( text, this, reporterFunction=None )

    noisyReplaceAll( text, this, that, loop=False )
    noisyRegExReplaceAll( text, this, that )

    noisyDeleteAll( text, this )
    noisyRegExDeleteAll( text, this )
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-04-10' # by RJH
SHORT_PROGRAM_NAME = "NoisyReplaceFunctions"
PROGRAM_NAME = "Noisy Replace Functions"
PROGRAM_VERSION = '0.07'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


import logging
import re

# BibleOrgSys imports
if __name__ == '__main__':
    import os.path
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint




def noisyFind( text:str, this:str, reporterFunction=None ):
    """
    """
    if reporterFunction is None: reporterFunction = print
    if BibleOrgSysGlobals.verbosityLevel > 0 or reporterFunction is not print:
        count = text.count( this )
        if count:
            reporterFunction( "Found {:,} occurrence{} of {!r}".format( count, '' if count==1 else 's', this ) )
        elif debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, "No occurrences of {!r} found".format( this ) )
# end of noisyFind


def noisyRegExFind( text:str, this:str, reporterFunction=None ):
    """
    """
    if reporterFunction is None: reporterFunction = print
    if BibleOrgSysGlobals.verbosityLevel > 0 or reporterFunction is not print:
        count = len( re.findall( this, text ) )
        if count:
            reporterFunction( _("Found {:,} occurrence{} of regex {!r}").format( count, '' if count==1 else 's', this ) )
        elif debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, _("No occurrences of {!r} regex found").format( this ) )
# end of noisyRegExFind



def noisyReplaceAll( text:str, this:str, that:str, loop:bool=False ) -> str:
    """
    """
    count = text.count( this )
    if count == 0:
        vPrint( 'Info', debuggingThisModule, _("No occurrences of {!r} found to replace").format( this ) )
        return text

    vPrint( 'Normal', debuggingThisModule, _("Replacing {:,} occurrence{} of {!r} with {!r}").format( count, '' if count==1 else 's', this, that ) )
    if loop:
        newText = text
        while this in newText:
            newText = newText.replace( this, that )
    else: newText = text.replace( this, that )

    count2 = newText.count( this )
    if count2 and BibleOrgSysGlobals.verbosityLevel > 0:
        vPrint( 'Quiet', debuggingThisModule, "  " + _("NOTE: {:,} occurrence{} of {!r} still remaining!").format( count2, '' if count2==1 else 's', this ) )
    return newText
# end of noisyReplaceAll


def noisyRegExReplaceAll( text:str, this:str, that:str ) -> str:
    """
    """
    regex = re.compile( this )

    count1 = len( re.findall( regex, text ) )
    if count1 == 0:
        vPrint( 'Info', debuggingThisModule, _("No occurrences of regex {!r} found to replace").format( this ) )
        return text
    vPrint( 'Normal', debuggingThisModule, _("Replacing {:,} occurrence{} of regex {!r} with {!r}").format( count1, '' if count1==1 else 's', this, that ) )

    newText, count2 = re.subn( regex, that, text )
    if count2!=count1 and BibleOrgSysGlobals.verbosityLevel > 0:
        vPrint( 'Quiet', debuggingThisModule, "  " + _("Replaced {:,} occurrence{} of regex {!r} with {!r}").format( count2, '' if count2==2 else 's', this, that ) )

    count3 = len( re.findall( regex, newText ) )
    if count3: # and BibleOrgSysGlobals.verbosityLevel > 0:
        logging.critical( "  " + _("NOTE: {:,} occurrence{} of regex {!r} still remaining!").format( count3, '' if count3==1 else 's', this ) )
    return newText
# end of noisyRegExReplaceAll



def noisyDeleteAll( text:str, this:str ) -> str:
    """
    """
    count = text.count( this )
    if count == 0:
        vPrint( 'Info', debuggingThisModule, _("No occurrences of {!r} found to delete").format( this ) )
        return text
    vPrint( 'Normal', debuggingThisModule, _("Deleting {:,} occurrence{} of {!r}").format( count, '' if count==1 else 's', this ) )
    newText = text.replace( this, '' )

    count2 = newText.count( this )
    if count2: # and BibleOrgSysGlobals.verbosityLevel > 0:
        logging.critical( "  " + _("NOTE: {:,} occurrence{} of {!r} still remaining!").format( count2, '' if count2==1 else 's', this ) )
    return newText
# end of noisyDeleteAll


def noisyRegExDeleteAll( text:str, this:str ) -> str:
    """
    """
    regex = re.compile( this )

    count1 = len( re.findall( regex, text ) )
    if count1 == 0:
        vPrint( 'Info', debuggingThisModule, _("No occurrences of regex {!r} found to delete").format( this ) )
        return text
    vPrint( 'Normal', debuggingThisModule, _("Deleting {:,} occurrence{} of regex {!r}").format( count1, '' if count1==1 else 's', this ) )

    newText, count2 = re.subn( regex, '', text )
    if count2!=count1 and BibleOrgSysGlobals.verbosityLevel > 2:
        vPrint( 'Quiet', debuggingThisModule, "  " + _("Deleted {:,} occurrence{} of regex {!r}").format( count2, '' if count2==2 else 's', this ) )

    count3 = len( re.findall( regex, newText ) )
    if count3: # and BibleOrgSysGlobals.verbosityLevel > 0:
        logging.critical( "  " + _("NOTE: {:,} occurrence{} of regex {!r} still remaining!").format( count3, '' if count3==1 else 's', this ) )
    return newText
# end of noisyRegExDeleteAll



def briefDemo() -> None:
    """
    Demo program to handle command line parameters and then run some short test/demo functions.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    sampleText = """This is just a sample text that we can use to demonstrate NoisyReplaceFunctions.py.

These functions can be used for string find, replace, and delete, but they are noisy
    in the sense that they print exactly what's happening.
"""
    resultDA_bad = noisyDeleteAll( sampleText, 'xyx' )
    vPrint( 'Quiet', debuggingThisModule, f"resultDA_bad={resultDA_bad}" )
    resultDA_good = noisyDeleteAll( sampleText, 'string' )
    vPrint( 'Quiet', debuggingThisModule, f"resultDA_good={resultDA_good}" )
# end of NoisyReplaceFunctions.demo


def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of NoisyReplaceFunctions.py
