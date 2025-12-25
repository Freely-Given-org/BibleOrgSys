#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Bible.py
#
# Module handling a internal Bible object
#
# Copyright (C) 2010-2025 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module handling an internal Bible object.

A class which extends BibleWriter (which itself extends InternalBible).

TODO: Check if we really need this class at all???
"""
from gettext import gettext as _
import logging

if __name__ == '__main__':
    import os.path
    import sys
    aboveFolderpath = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
    if aboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleBook import InternalBibleBook
from BibleOrgSys.BibleWriter import BibleWriter


LAST_MODIFIED_DATE = '2025-05-15' # by RJH
SHORT_PROGRAM_NAME = "BibleObjects"
PROGRAM_NAME = "Bible object handler"
PROGRAM_VERSION = '0.16'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


logger = logging.getLogger(SHORT_PROGRAM_NAME)



class BibleBook( InternalBibleBook ):
    """
    Class for handling a single Bible book.
        A Bible book consists of a list of tuples.
            Each tuple has two strings:
                a code to label information like section headings, paragraph text, etc.
                the content
        Chapter/Verse information is stored separately in an index (a dictionary)
            The dictionary index is a (C,V) tuple.
            The data is a tuple of
                index into data tuple (0..)
                offset into data tuple (0..)
            This means that the index has to be updated if the data is updated.
    """

    def __init__( self, containerBibleObject, BBB:str ) -> None:
        """
        Constructor: creates an empty Bible book.
        """
        self.doExtraChecking = DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag
        if self.doExtraChecking:
            if isinstance( containerBibleObject, str ):
                logger.critical( "containerBibleObject is a string '{}' (not a Bible object): presumably this is a test???".format( containerBibleObject ) )
            else: assert isinstance( containerBibleObject, Bible )

        super().__init__( containerBibleObject, BBB )
    # end of __init__

    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = _("BibleBook object")
        return result
    # end of __str__
# end of class BibleBook



class Bible( BibleWriter ):
    """
    Class for handling an entire Bible.

    All the various different flavours of Bible (e.g., USFM, OSIS XML, CSV)
        are based on this class.
    """

    def __init__( self ) -> None:
        """
        Constructor: creates an empty Bible object.
        """
        BibleWriter.__init__( self )
        self.doExtraChecking = DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag
        self.objectNameString = 'Bible object (generic/unknown type)'
        self.objectTypeString = 'Unknown'

        self.BibleOrganisationalSystem = None
        # Add our own extended data stores
        #self.metadata = {}
        #self.frontMatter = []
        #self.divisions = []
        #self.actualBooks = []
        #self.backMatter = []
# end of class Bible



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Since this is only designed to be a base class, it can't actually do much at all
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTest Bible…" )
    B = Bible()
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, B )
# end of Bible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Since this is only designed to be a base class, it can't actually do much at all
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTest Bible…" )
    B = Bible()
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, B )

    #if 0: # No need for this here
        ## Test a single folder containing a USFM Bible
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTest USFM Bible…" )
        #from BibleOrgSys.Formats.USFMBible import USFMBible
        #name, encoding, testFolder = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
        #if os.access( testFolder, os.R_OK ):
            #UB = USFMBible( testFolder, name, encoding )
            #UB.load()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UB )
            #if BibleOrgSysGlobals.strictCheckingFlag:
                #UB.check()
            #UB.doAllExports( "BOSOutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
        #else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of Bible.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of Bible.py
