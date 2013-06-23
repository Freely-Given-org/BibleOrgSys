#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# DigitalBiblePlatform.py
#   Last modified: 2013-06-24 (also update ProgVersion below)
#
# Module handling online DBP resources
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
This module interfaces with the online Bible versions available
    from Faith Comes By Hearing (FCBH).

In this module, we use:
    DAM = Digital Asset Management – the software system for users to administer the volumes contained in the DBP.
    DAM ID – the unique id by which an individual volume is identified.
    DBP = Digital Bible Platform

More details are available from http://www.DigitalBiblePlatform.com.
"""

ProgName = "Digital Bible Platform handler"
ProgVersion = "0.02"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )


from singleton import singleton
import os, logging
from gettext import gettext as _
import urllib.request, json
from collections import OrderedDict

import Globals
from VerseReferences import SimpleVerseKey


URLBase = "http://dbt.io/"
MAX_CACHED_VERSES = 100 # Per Bible version in use



@singleton # Can only ever have one instance
class DBPBibles:
    """
    Class to download and manipulate online DBP Bibles.

    """
    def __init__( self ):
        """
        Create the internal Bible object.
        """
        with open( "DBPKey.txt", "rt" ) as keyFile:
            self.key = keyFile.read() # Our personal key
        self.URLFixedData = "?v=2&key=" + self.key

        # See if the site is online by making a small call to get the API version
        self.URLTest = "api/apiversion"
        self.onlineVersion = None
        result = self.getOnlineData( self.URLTest )
        if 'Version' in result: self.onlineVersion = result['Version']

        if Globals.verbosityLevel > 1: print( _("Downloading list of available volumes from FCBH...") )
        self.languageList = self.versionList = self.volumeList = None
        if self.onlineVersion: # Get a list of available data sets
            self.languageList = self.getOnlineData( "library/language" ) # Get an alphabetically ordered list of dictionaries -- one for each language
            #print( "languageList", len(self.languageList), self.languageList )
            self.versionList = self.getOnlineData( "library/version" ) # Get an alphabetically ordered list of dictionaries -- one for each version
            #print( "versionList", len(self.versionList), self.versionList )
            self.volumeList = self.getOnlineData( "library/volume" ) # Get an alphabetically ordered list of dictionaries -- one for each volume
            #print( "volumeList", len(self.volumeList), self.volumeList )

            #if 0:# Get all book codes and English names
                #bookCodeDictList = self.getOnlineData( "library/bookname", "language_code=ENG" )
                ## Not sure why it comes back as a dictionary in a one-element list
                #assert( isinstance( bookCodeDictList, list ) and len(bookCodeDictList)==1 )
                #bookCodeDict = bookCodeDictList[0]
                #assert( isinstance( bookCodeDict, dict ) )
                #print( "bookCodeDict", len(bookCodeDict), bookCodeDict )

        self.volumeNameList = {}
        if self.volumeList: # Create a list of resource types
            for j, volume in enumerate(self.volumeList):
                assert( volume['language_name'] and volume['volume_name'] )
                ourName= '{} {}'.format( volume['language_name'], volume['volume_name'] )
                assert( volume['media'] and volume['delivery'] and volume['collection_code'] )
                if volume['media'] == 'text':
                    if 'web' in volume['delivery']:
                        ourName= '{} {}'.format( volume['language_name'], volume['volume_name'] )
                        if ourName in self.volumeNameList:
                            #print( "\nAlready have", ourName )
                            ##print( "New", j, volume )
                            #ix = self.volumeNameList[ourName]
                            #oldVolume = self.volumeList[ix]
                            ##print( "Old", ix, oldVolume )
                            #assert( len(volume) == len(oldVolume) )
                            #for someKey in volume:
                                #if volume[someKey] != oldVolume[someKey]:
                                    #if someKey not in ('dam_id','fcbh_id','sku','updated_on','collection_name',):
                                        #print( "  ", someKey, volume[someKey], oldVolume[someKey] )
                            self.volumeNameList[ourName].append( j )
                        else: self.volumeNameList[ourName] = [j]
                    #else: print( j, repr(volume['language_name']), repr(volume['volume_name']) )
                    else: print( "No web delivery in", ourName, volume['delivery'] )
                elif volume['media']!='audio': print( "No text in", ourName, volume['media'] )
        #print( "volumeNameList", len(self.volumeNameList), self.volumeNameList )
    # end of DBPBibles.__init__


    def __str__( self ):
        """
        Create a string representation of the Bibles object.
        """
        indent = 2
        result = "DBP online Bible object"
        if self.onlineVersion: result += ('\n' if result else '') + ' '*indent + _("Online version: {}").format( self.onlineVersion )
        if self.languageList: result += ('\n' if result else '') + ' '*indent + _("Languages: {}").format( len(self.languageList) )
        if self.versionList: result += ('\n' if result else '') + ' '*indent + _("Versions: {}").format( len(self.versionList) )
        if self.volumeList: result += ('\n' if result else '') + ' '*indent + _("Volumes: {}").format( len(self.volumeList) )
        if self.volumeNameList: result += ('\n' if result else '') + ' '*indent + _("Displayable volumes: {}").format( len(self.volumeNameList) )
        return result
    # end of DBPBibles.__str__


    def getOnlineData( self, fieldREST, additionalParameters=None ):
        """
        Given a string, e.g., "api/apiversion"
            Does an HTTP GET to our site.
            Receives the JSON result (hopefully)
            Converts the JSON bytes to a JSON string
            Loads the JSON string into a dictionary
            Returns the dictionary.
        Returns None if the data cannot be fetched.
        """
        requestString = "{}{}{}{}".format( URLBase, fieldREST, self.URLFixedData, '&'+additionalParameters if additionalParameters else '' )
        #print( "Request string is", repr(requestString) )
        try: responseJSON = urllib.request.urlopen( requestString )
        except urllib.error.URLError: return None
        #print( "responseJSON", responseJSON.read() )
        responseSTR = responseJSON.readall().decode('utf-8')
        #print( "responseSTR", repr(responseSTR) )
        return( json.loads( responseSTR ) )
    # end of DBPBibles.getOnlineData


    def getDAM( self, refNumber ):
        """
        """
        return self.volumeList[refNumber]['dam_id']
    # end of DBPBibles.getDAM


    def searchNames( self, searchText ):
        """
        """
        searchTextUC = searchText.upper()
        results = []
        for name in self.volumeNameList:
            if searchTextUC in name.upper():
                for refNumber in self.volumeNameList[name]:
                    DAM = self.getDAM(refNumber)
                    assert( DAM.endswith( '2ET' ) ) # O2 (OT) or N2 (NT), plus ET for text
                    results.append( (refNumber,DAM,) )
        return results
    # end of DBPBibles.searchNames
# end of class DBPBibles



class DBPBible:
    """
    Class to download and manipulate an online DBP Bible.

    """
    def __init__( self, damRoot ):
        """
        Create the internal Bible object.
        """
        assert( damRoot and isinstance( damRoot, str ) and len(damRoot)==6 )
        self.damRoot = damRoot

         # Setup and initialise the base class first
        #USXXMLBible.__init__( self, givenFolderName, givenName, encoding )

        with open( "DBPKey.txt", "rt" ) as keyFile:
            self.key = keyFile.read() # Our personal key
        self.URLFixedData = "?v=2&key=" + self.key

        # See if the site is online by making a small call to get the API version
        self.URLTest = "api/apiversion"
        self.onlineVersion = None
        result = self.getOnlineData( self.URLTest )
        if 'Version' in result: self.onlineVersion = result['Version']

        self.bookList = None
        if self.onlineVersion: # Check that this particular resource is available by getting a list of books
            bookList = self.getOnlineData( "library/book", "dam_id="+self.damRoot ) # Get an ordered list of dictionaries -- one for each book
            #print( "bookList", len(bookList), bookList )

            #if 0:# Get all book codes and English names
                #bookCodeDictList = self.getOnlineData( "library/bookname", "language_code=ENG" )
                ## Not sure why it comes back as a dictionary in a one-element list
                #assert( isinstance( bookCodeDictList, list ) and len(bookCodeDictList)==1 )
                #bookCodeDict = bookCodeDictList[0]
                #assert( isinstance( bookCodeDict, dict ) )
                #print( "bookCodeDict", len(bookCodeDict), bookCodeDict )

        self.books = OrderedDict()
        if bookList: # Convert to a form that's easier for us to use later
            for bookDict in bookList:
                OSISCode = bookDict['book_id']
                #print( "OSIS", OSISCode )
                BBB = Globals.BibleBooksCodes.getBBBFromOSIS( OSISCode )
                if isinstance( BBB, list ): BBB = BBB[0] # Take the first one if we get something like ['EZR','EZN']
                #print( "BBB", BBB )
                #print( bookDict )
                self.books[BBB] = bookDict
            del bookList

        self.cache = OrderedDict()
    # end of DBPBible.__init__


    def __str__( self ):
        """
        Create a string representation of the Bible object.
        """
        indent = 2
        result = "DBP online Bible object"
        if self.onlineVersion: result += ('\n' if result else '') + ' '*indent + _("Online version: {}").format( self.onlineVersion )
        result += ('\n' if result else '') + ' '*indent + _("DAM root: {}").format( self.damRoot )
        if self.books: result += ('\n' if result else '') + ' '*indent + _("Books: {}").format( len(self.books) )
        return result
    # end of DBPBible.__str__


    def __len__( self ):
        """
        This method returns the number of books in the Bible.
        """
        return len( self.books )
    # end of DBPBible.__len__


    def __contains__( self, BBB ):
        """
        This method checks whether the Bible contains the BBB book.
        Returns True or False.
        """
        if Globals.debugFlag: assert( isinstance(BBB,str) and len(BBB)==3 )
        return BBB in self.books
    # end of DBPBible.__contains__


    def __getitem__( self, keyIndex ):
        """
        Given an index, return the book object (or raise an IndexError)
        """
        return list(self.books.items())[keyIndex][1] # element 0 is BBB, element 1 is the book object
    # end of DBPBible.__getitem__


    def getOnlineData( self, fieldREST, additionalParameters=None ):
        """
        Given a string, e.g., "api/apiversion"
            Does an HTTP GET to our site.
            Receives the JSON result (hopefully)
            Converts the JSON bytes to a JSON string
            Loads the JSON string into a dictionary
            Returns the dictionary.
        Returns None if the data cannot be fetched.
        """
        if Globals.verbosityLevel > 2: print( "Requesting data from {} for {}...".format( URLBase, self.damRoot ) )
        requestString = "{}{}{}{}".format( URLBase, fieldREST, self.URLFixedData, '&'+additionalParameters if additionalParameters else '' )
        #print( "Request string is", repr(requestString) )
        try: responseJSON = urllib.request.urlopen( requestString )
        except urllib.error.URLError: return None
        responseSTR = responseJSON.readall().decode('utf-8')
        return( json.loads( responseSTR ) )
    # end of DBPBible.getOnlineData


    def getVerseData( self, key ):
        """
        """
        if Globals.debugFlag: print( "DBPBible.getVerseData( {} ) for {}".format( key, self.damRoot ) )
        if str(key) in self.cache:
            self.cache.move_to_end( str(key) )
            return self.cache[str(key)]
        BBB = key.getBBB()
        if BBB in self.books:
            info = self.books[BBB]
            rawData = self.getOnlineData( "text/verse", "dam_id={}&book_id={}&chapter_id={}&verse_start={}".format( info['dam_id']+'2ET', info['book_id'], key.getChapterNumber(), key.getVerseNumber() ) )
            resultList = []
            if isinstance( rawData, list ) and len(rawData)==1:
                rawDataDict = rawData[0]
                #print( len(rawDataDict), rawDataDict )
                assert( len(rawDataDict)==8 and isinstance( rawDataDict, dict ) )
                resultList.append( ('p#','p#',rawDataDict['paragraph_number'],rawDataDict['paragraph_number'],[]) ) # Must be first for Biblelator
                if key.getVerseNumber()=='1': resultList.append( ('c#','c#',rawDataDict['chapter_id'],rawDataDict['chapter_id'],[]) )
                resultList.append( ('v','v',rawDataDict['verse_id'],rawDataDict['verse_id'],[]) )
                resultList.append( ('v~','v~',rawDataDict['verse_text'].strip(),rawDataDict['verse_text'].strip(),[]) )
                self.cache[str(key)] = resultList
                if len(self.cache) > MAX_CACHED_VERSES:
                    #print( "Removing oldest cached entry", len(self.cache) )
                    self.cache.popitem( last=False )
            return resultList
    # end of DBPBible.getVerseData
# end of class DBPBible



def demo():
    """
    Demonstrate how some of the above classes can be used.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    if 1: # Test the DBPBibles class
        print()
        dbpBibles = DBPBibles()
        print( dbpBibles )
        #if 0:
            #for someName in dbpBibles.volumeNameList:
                #if 'English' in someName: print( "English:", someName, dbpBibles.volumeNameList[someName] )
        print( "English search", dbpBibles.searchNames( "English" ) )
        print( "MS search", dbpBibles.searchNames( "Salug" ) )

    if 1: # Test the DBPBible class
        print()
        dbpBible1 = DBPBible( "ENGESV" )
        print( dbpBible1 )
        for verseKey in (SimpleVerseKey('GEN','1','1'),SimpleVerseKey('MAT','1','1'),SimpleVerseKey('JHN','3','16'),):
            print( verseKey )
            print( dbpBible1.getVerseData( verseKey ) )

    if 1: # Test the DBPBible class
        print()
        dbpBible2 = DBPBible( "MBTWBT" )
        print( dbpBible2 )
        for verseKey in (SimpleVerseKey('MAT','1','1'),SimpleVerseKey('JHN','3','16'),):
            print( verseKey )
            print( dbpBible2.getVerseData( verseKey ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of DigitalBiblePlatform.py