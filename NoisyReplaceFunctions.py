#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# NoisyReplaceFunctions.py
#
# Functions for replace and regex replace which explain what they did.
#
# Copyright (C) 2018 Robert Hunt
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
Functions for replace and regex replace which explain what they did.

    noisyFind( text, this, reporterFunction=None )
    noisyRegExFind( text, this, reporterFunction=None )
    noisyReplaceAll( text, this, that, loop=False )
    noisyDeleteAll( text, this )
    noisyRegExReplaceAll( text, this, that )
"""

from gettext import gettext as _

LastModifiedDate = '2018-02-07' # by RJH
ShortProgName = "NoisyReplaceFunctions"
ProgName = "Noisy Replace Functions"
ProgVersion = '0.05'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging
import re

# BibleOrgSys imports
import BibleOrgSysGlobals


def noisyFind( text, this, reporterFunction=None ):
    """
    """
    if reporterFunction is None: reporterFunction = print
    if BibleOrgSysGlobals.verbosityLevel > 0 or reporterFunction is not print:
        count = text.count( this )
        if count:
            reporterFunction( "Found {:,} occurrence{} of {!r}".format( count, '' if count==1 else 's', this ) )
        elif debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "No occurrences of {!r} found".format( this ) )
# end of noisyFind


def noisyRegExFind( text, this, reporterFunction=None ):
    """
    """
    if reporterFunction is None: reporterFunction = print
    if BibleOrgSysGlobals.verbosityLevel > 0 or reporterFunction is not print:
        count = len( re.findall( this, text ) )
        if count:
            reporterFunction( "Found {:,} occurrence{} of regex {!r}".format( count, '' if count==1 else 's', this ) )
        elif debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "No occurrences of {!r} regex found".format( this ) )
# end of noisyRegExFind


def noisyReplaceAll( text, this, that, loop=False ):
    """
    """
    count = text.count( this )
    if count == 0:
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "No occurrences of {!r} found to replace".format( this ) )
        return text

    if BibleOrgSysGlobals.verbosityLevel > 1:
        print( "Replacing {:,} occurrence{} of {!r} with {!r}".format( count, '' if count==1 else 's', this, that ) )
    if loop:
        newText = text
        while this in newText:
            newText = newText.replace( this, that )
    else: newText = text.replace( this, that )

    count2 = newText.count( this )
    if count2 and BibleOrgSysGlobals.verbosityLevel > 0:
        print( "  NOTE: {:,} occurrence{} of {!r} still remaining!".format( count2, '' if count2==1 else 's', this ) )
    return newText
# end of noisyReplaceAll


def noisyDeleteAll( text, this ):
    """
    """
    count = text.count( this )
    if count == 0:
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "No occurrences of {!r} found to delete".format( this ) )
        return text
    if BibleOrgSysGlobals.verbosityLevel > 1:
        print( "Deleting {:,} occurrence{} of {!r}".format( count, '' if count==1 else 's', this ) )
    newText = text.replace( this, '' )

    count2 = newText.count( this )
    if count2: # and BibleOrgSysGlobals.verbosityLevel > 0:
        logging.critical( "  NOTE: {:,} occurrence{} of {!r} still remaining!".format( count2, '' if count2==1 else 's', this ) )
    return newText
# end of noisyDeleteAll


def noisyRegExReplaceAll( text, this, that ):
    """
    """
    regex = re.compile( this )

    count1 = len( re.findall( regex, text ) )
    if BibleOrgSysGlobals.verbosityLevel > 1:
        print( "Replacing {:,} occurrence{} of regex {!r} with {!r}".format( count1, '' if count1==1 else 's', this, that ) )

    newText, count2 = re.subn( regex, that, text )
    if count2!=count1 and BibleOrgSysGlobals.verbosityLevel > 0:
        print( "  Replaced {:,} occurrence{} of regex {!r} with {!r}".format( count2, '' if count==2 else 's', this, that ) )

    count3 = len( re.findall( regex, newText ) )
    if count3: # and BibleOrgSysGlobals.verbosityLevel > 0:
        logging.critical( "  NOTE: {:,} occurrence{} of regex {!r} still remaining!".format( count3, '' if count3==1 else 's', this ) )
    return newText
# end of noisyRegExReplaceAll


def demo():
    """
    Demo program to handle command line parameters and then run some short test/demo functions.
    """
    if BibleOrgSysGlobals.verbosityLevel>0: print( ProgNameVersion )

# end of NoisyReplaceFunctions.demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of NoisyReplaceFunctions.py
