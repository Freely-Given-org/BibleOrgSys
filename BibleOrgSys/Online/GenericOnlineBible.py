#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GenericOnlineBible.py
#
# Base module handling generic online websites
#
# Copyright (C) 2019 Robert Hunt
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
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-03-17' # by RJH
SHORT_PROGRAM_NAME = "GenericOnlineBible"
PROGRAM_NAME = "Generic online Bible handler"
PROGRAM_VERSION = '0.02'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging
import urllib.request
import json
from collections import OrderedDict

if __name__ == '__main__':
    import sys
    import re
import logging # Append the containing folder to the path to search for the BOS
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Misc.singleton import singleton


MAX_CACHED_VERSES = 100 # Per Bible version in use



class GenericOnlineBible:
    """
    Class to download and manipulate an online DBP Bible.

    Note that this Bible class is NOT based on the Bible class
        because it's so unlike most Bibles which are local.
    """
    def __init__( self ):
        """
        Create the Digital Bible Platform Bible object.
            Accepts a 6-character code which is the initial part of the DAM:
                1-3: Language code, e.g., ENG
                4-6: Version code, e.g., ESV
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "GenericOnlineBible.__init__()" )

        self.bookList = None
        self.books = {}

        self.cache = OrderedDict() # has move_to_end function
    # end of GenericOnlineBible.__init__


    def __str__( self ):
        """
        Create a string representation of the Bible object.
        """
        indent = 2
        result = "Generic online Bible object"
        if self.books: result += ('\n' if result else '') + ' '*indent + _("Books: {}").format( len(self.books) )
        return result
    # end of GenericOnlineBible.__str__


    def __len__( self ):
        """
        This method returns the number of books in the Bible.
        """
        return len( self.books )
    # end of GenericOnlineBible.__len__


    def __contains__( self, BBB ):
        """
        This method checks whether the Bible contains the BBB book.
        Returns True or False.
        """
        if BibleOrgSysGlobals.debugFlag:
            assert isinstance(BBB,str) and len(BBB)==3

        return BBB in self.books
    # end of GenericOnlineBible.__contains__


    def __getitem__( self, keyIndex ):
        """
        Given an index, return the book object (or raise an IndexError)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"GenericOnlineBible.__getitem__( {keyIndex} )" )

        return list(self.books.items())[keyIndex][1] # element 0 is BBB, element 1 is the book object
    # end of GenericOnlineBible.__getitem__


    #def getOnlineData( self, fieldREST, additionalParameters=None ):
        #"""
        #Given a string, e.g., "api/apiversion"
            #Does an HTTP GET to our site.
            #Receives the JSON result (hopefully)
            #Converts the JSON bytes to a JSON string
            #Loads the JSON string into a dictionary
            #Returns the dictionary.
        #Returns None if the data cannot be fetched.
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( _("GenericOnlineBible.getOnlineData( {!r} {!r} )").format( fieldREST, additionalParameters ) )

        #if BibleOrgSysGlobals.verbosityLevel > 2: print( "Requesting data from {} for {}…".format( URL_BASE, self.damRoot ) )
        #requestString = "{}{}{}{}".format( URL_BASE, fieldREST, self.URLFixedData, '&'+additionalParameters if additionalParameters else '' )
        ##print( "Request string is", repr(requestString) )
        #try: responseJSON = urllib.request.urlopen( requestString )
        #except urllib.error.URLError:
            #if BibleOrgSysGlobals.debugFlag: logging.critical( "GenericOnlineBible.getOnlineData: error fetching {!r} {!r}".format( fieldREST, additionalParameters ) )
            #return None
        #responseSTR = responseJSON.read().decode('utf-8')
        #return json.loads( responseSTR )
    ## end of GenericOnlineBible.getOnlineData


    def cacheVerse( self, key, verseData ):
        """
        Given a BCV key, add the data to the cache.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"GenericOnlineBible.cacheVerse( {key}, {verseData} )" )

        if str(key) in self.cache:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "  " + _("Retrieved from cache") )
            self.cache.move_to_end( str(key) )
            cachedVerseData = self.cache[str(key)]
            if cachedVerseData != verseData:
                logging.warning( f"New cached data for {key} {verseData} doesn't match previously cached data: {cachedVerseData}" )

        # Not found in the cache
        self.cache[str(key)] = verseData
    # end of GenericOnlineBible.cacheVerse


    def getCachedVerseDataList( self, key ):
        """
        Given a BCV key, see if we have the verse data in the cache.

        Return None if not.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"GenericOnlineBible.getCachedVerseDataList( {key} )" )

        if str(key) in self.cache:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "  " + _("Retrieved from cache") )
            self.cache.move_to_end( str(key) )
            return self.cache[str(key)]

        # Not found in the cache
        return None
    # end of GenericOnlineBible.getCachedVerseDataList


    def getContextVerseData( self, key ):
        """
        Given a BCV key, get the verse data with context.

        (Most platforms don't provide the context so an empty list is returned.)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"GenericOnlineBible.getContextVerseData( {key} )" )

        return self.getVerseDataList( key ), [] # No context
    # end of GenericOnlineBible.getContextVerseData
# end of class GenericOnlineBible



def demo() -> None:
    """
    Demonstrate how some of the above classes can be used.
    """
    from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey

    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    testRefs = ( ('GEN','1','1'), ('JER','33','3'), ('MAL','4','6'), ('MAT','1','1'), ('JHN','3','16'), ('JDE','1','14'), ('REV','22','21'), )

    if 1: # Test the GenericOnlineBible class
        print()
        dbpBible1 = GenericOnlineBible()
        print( dbpBible1 )
        for testRef in testRefs:
            verseKey = SimpleVerseKey( *testRef )
            print( verseKey )
            dbpBible1.cacheVerse( verseKey, [f"Verse text for {verseKey}"] )
            print( f"  Cache length: {len(dbpBible1.cache)}" )
            print( " ", dbpBible1.getCachedVerseDataList( verseKey ) )
         # Now test the GenericOnlineBible class caching
        print()
        for testRef in testRefs:
            verseKey = SimpleVerseKey( *testRef )
            print( verseKey, "cached" )
            print( " ", dbpBible1.getCachedVerseDataList( verseKey ) )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of GenericOnlineBible.py
