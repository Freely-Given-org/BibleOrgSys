#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UnknownBible.py
#   Last modified: 2013-04-15 (also update versionString below)
#
# Module handling a unknown Bible object
#
# Copyright (C) 2013 Robert Hunt
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
Module handling an unknown Bible object.

Given a folder name, analyses the files in it
    and tries to determine what type of Bible it probably contains (if any).

Currently aware of the following Bible types:
    USFM
    Unbound Bible
    OSIS, USX, OpenSong, Zefania (all XML)
    Sword modules.
"""

progName = "Unknown Bible object handler"
versionString = "0.01"

import logging, os.path
from gettext import gettext as _

import Globals
from USFMBible import USFMBible
from USXBible import USXBible
from OpenSongXMLBible import OpenSongXMLBible
from OSISXMLBible import OSISXMLBible
from ZefaniaXMLBible import ZefaniaXMLBible
from UnboundBible import UnboundBibleFileCheck, UnboundBible
from SwordResources import SwordInterface


class UnknownBible:
    """
    Class for handling an entire Bible.
    """

    def __init__( self, folder ):
        """
        Constructor: creates an empty Bible object.
        """
        assert( folder and isinstance( folder, str ) )
        self.folder = folder
    # end of UnknownBible.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = _("Unknown Bible object")
        result += ('\n' if result else '') + "  " + _("Folder: {} ").format( self.folder )
        return result
    # end of UnknownBible.__str__


    def search( self, autoLoad=False ):
        """
        Search our folder to found what if any Bible versions can be found.

        These searches are best done in a certain order to avoid false detections.
        """
        # Try UnboundBible
        UnboundBibleResult = UnboundBibleFileCheck( self.folder )
        print( "UBR", UnboundBibleResult )

        if UnboundBibleResult:
            if autoLoad: return UnboundBibleFileCheck( self.folder, autoLoad=True )
            else: return "Unbound", UnboundBibleResult
    # end of UnknownBible.search
# end of class UnknownBible


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format(versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format(progName, versionString ) )

    # Now demo the class
    testFolders = ( "../../../../../Data/Work/Bibles/Biola Unbound modules/asv",
                    "../../../../../Data/Work/Matigsalug/Bible/MBTV/", )
    for j, testFolder in enumerate( testFolders ):
        print( "\n\n{} Trying {}...".format( j+1, testFolder ) )
        B = UnknownBible( testFolder )
        print( B )
        result1 = B.search( autoLoad=False )
        result2 = B.search( autoLoad=True ) if result1 else None
        if Globals.verbosityLevel > 0: print( "  Results are: {} and {}".format( result1, result2 ) )
# end of demo

if __name__ == '__main__':
    demo()
# end of UnknownBible.py