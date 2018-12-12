#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# GetKJVVerseNumber.py
#
# App to convert between Bible references and absolute verse numbers.
#
# Copyright (C) 2015-2018 Robert Hunt
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
A short app as part of BOS (Bible Organisational System) demos.
This app inputs a Bible reference (e.g. 'Gen 1:1' or 'mt 1-5'
    and converts it to an absolute verse number (or vice versa.)

Of course, you must already have Python3 installed on your system.
    (Probably installed by default on most modern Linux systems.)

Note that this app MUST BE RUN FROM YOUR BOS folder,
    e.g., using the command:
        Apps/GetKJVVerseNumber.py

You can discover the version with
        Apps/GetKJVVerseNumber.py --version

You can discover the available command line parameters with
        Apps/GetKJVVerseNumber.py --help

    e.g., for verbose mode
        Apps/GetKJVVerseNumber.py --verbose
    or
        Apps/GetKJVVerseNumber.py -v

This app also demonstrates how little code is required to use the BOS
    to load a Bible Organisational System (in this case: GENERIC-KJV-66-ENG).

The (Python3) BOS is developed and well-tested on Linux (Ubuntu)
    but also runs on Windows (although not so well tested).
"""

from gettext import gettext as _

LastModifiedDate = '2018-12-12' # by RJH
ShortProgName = "GetKJVVerseNumber"
ProgName = "Get KJV Verse Number"
ProgVersion = '0.10'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

# Allow the system to find the BOS even when the app is down in its own folder
import sys
sys.path.append( '.' ) # Append the containing folder to the path to search for the BOS
import BibleOrgSysGlobals
from BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleReferences import BibleSingleReference


def main():
    """
    This is the main program for the app
        which just tries to open and load some kind of Bible file(s)
            from the inputFolder that you specified
        and then export a PhotoBible (in the default OutputFiles folder).

    Note that the standard verbosityLevel is 2:
        -s (silent) is 0
        -q (quiet) is 1
        -i (information) is 3
        -v (verbose) is 4.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print( ProgNameVersion )

    ourBibleOrganisationalSystem = BibleOrganisationalSystem( "GENERIC-KJV-66-ENG" )
    ourVersificationSystem = ourBibleOrganisationalSystem.getVersificationSystemName()
    ourBibleSingleReference = BibleSingleReference( ourBibleOrganisationalSystem )

    print( _("Use QUIT or EXIT to finish.") )

    while True: # Loop until they stop it
        userInput = input( '\n' + _("Enter a verse number 1..31102 or a single Bible verse reference (or QUIT): ") )
        if userInput.lower() in ('exit', 'quit', 'q', 'stop', 'halt',):
            break

        # See if it's an absolute verse number
        try: userInt = int(userInput)
        except ValueError: userInt = None
        if userInt:
            if 1 <= userInt <= 31102:
                BBB, C, V = ourBibleOrganisationalSystem.convertAbsoluteVerseNumber( userInt )
                print( _("{} verse number {} is {} {}:{}").format( ourVersificationSystem, userInt, BBB, C, V ) )
            else:
                print( _("Absolute verse numbers must be in range 1..31,102.") )

        else: # assume it's a Bible reference
            adjustedUserInput = userInput
            if ':' not in adjustedUserInput:
                for alternative in ('.', ',', '-',): # Handle possible alternative C:V punctuations
                    if alternative in adjustedUserInput:
                        adjustedUserInput = adjustedUserInput.replace( alternative, ':', 1 )
                        break
            results = ourBibleSingleReference.parseReferenceString( adjustedUserInput )
            #print( results )
            successFlag, haveWarnings, BBB, C, V, S = results
            if successFlag:
                print( _("{!r} converted to {} {}:{} in our internal system.").format( userInput, BBB, C, V ) )
                absoluteVerseNumber = ourBibleOrganisationalSystem.getAbsoluteVerseNumber( BBB, C, V )
                print( _("  {} {}:{} is verse number {:,} in the {} versification system.").format( BBB, C, V, absoluteVerseNumber, ourVersificationSystem ) )
                if BibleOrgSysGlobals.debugFlag:
                    print( _("  {} {}:{} is verse number 0x{:04x} in the {} versification system.").format( BBB, C, V, absoluteVerseNumber, ourVersificationSystem ) )
            else:
                print( _("Unable to find a valid single verse reference in your input: {!r}").format( userInput ) )
# end of main

if __name__ == '__main__':
    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of GetKJVVerseNumber.py
