#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GetKJVVerseNumber.py
#
# App to convert between Bible references and absolute verse numbers.
#
# Copyright (C) 2015-2018 Robert Hunt
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

# Allow the system to find the BOS even when the app is down in its own folder
if __name__ == '__main__':
    import sys
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Reference.BibleReferences import BibleSingleReference


LAST_MODIFIED_DATE = '2018-12-12' # by RJH
SHORT_PROGRAM_NAME = "GetKJVVerseNumber"
PROGRAM_NAME = "Get KJV Verse Number"
PROGRAM_VERSION = '0.10'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'



def main() -> None:
    """
    This is the main program for the app
        which just tries to open and load some kind of Bible file(s)
            from the inputFolder that you specified
        and then export a PhotoBible (in the default BOSOutputFiles folder).

    Note that the standard verbosityLevel is 2:
        -s (silent) is 0
        -q (quiet) is 1
        -i (information) is 3
        -v (verbose) is 4.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    ourBibleOrganisationalSystem = BibleOrganisationalSystem( "GENERIC-KJV-66-ENG" )
    ourVersificationSystem = ourBibleOrganisationalSystem.getVersificationSystemName()
    ourBibleSingleReference = BibleSingleReference( ourBibleOrganisationalSystem )

    vPrint( 'Quiet', debuggingThisModule, _("Use QUIT or EXIT to finish.") )

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
                vPrint( 'Quiet', debuggingThisModule, _("{} verse number {} is {} {}:{}").format( ourVersificationSystem, userInt, BBB, C, V ) )
            else:
                vPrint( 'Quiet', debuggingThisModule, _("Absolute verse numbers must be in range 1..31,102.") )

        else: # assume it's a Bible reference
            adjustedUserInput = userInput
            if ':' not in adjustedUserInput:
                for alternative in ('.', ',', '-',): # Handle possible alternative C:V punctuations
                    if alternative in adjustedUserInput:
                        adjustedUserInput = adjustedUserInput.replace( alternative, ':', 1 )
                        break
            results = ourBibleSingleReference.parseReferenceString( adjustedUserInput )
            #dPrint( 'Quiet', debuggingThisModule, results )
            successFlag, haveWarnings, BBB, C, V, S = results
            if successFlag:
                vPrint( 'Quiet', debuggingThisModule, _("{!r} converted to {} {}:{} in our internal system.").format( userInput, BBB, C, V ) )
                absoluteVerseNumber = ourBibleOrganisationalSystem.getAbsoluteVerseNumber( BBB, C, V )
                vPrint( 'Quiet', debuggingThisModule, _("  {} {}:{} is verse number {:,} in the {} versification system.").format( BBB, C, V, absoluteVerseNumber, ourVersificationSystem ) )
                if BibleOrgSysGlobals.debugFlag:
                    vPrint( 'Quiet', debuggingThisModule, _("  {} {}:{} is verse number 0x{:04x} in the {} versification system.").format( BBB, C, V, absoluteVerseNumber, ourVersificationSystem ) )
            else:
                vPrint( 'Quiet', debuggingThisModule, _("Unable to find a valid single verse reference in your input: {!r}").format( userInput ) )
# end of main

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of GetKJVVerseNumber.py
