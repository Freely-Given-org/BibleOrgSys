#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Door43Online.py
#
# Module handling online resources from the unfoldingWord/Door43 catalog
#   (accessible through api.door43.org)
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
This module interfaces with the online Bible resources available
    from unfoldingWord/Door43 and accessible online through the API
    at https://api.door43.org/v3/catalog.json
    and documented at https://api-info.readthedocs.io/en/latest/index.html.

In this module, we use:
    API = Application Programming Interface

We currently use version 3 of the API.

More details are available from https://api-info.readthedocs.io/en/latest/index.html.
"""

from gettext import gettext as _

LastModifiedDate = '2019-02-05' # by RJH
ShortProgName = "Door43Online"
ProgName = "Door43 Online Catalog online handler"
ProgVersion = '0.02'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


from singleton import singleton
import os, logging
import urllib.request, json

import BibleOrgSysGlobals
from VerseReferences import SimpleVerseKey


URL_BASE = 'https://api.door43.org'
Door43_API_Version = '3'
URL_FULL_BASE = f'{URL_BASE}/v{Door43_API_Version}/'
MAX_CACHED_VERSES = 100 # Per Bible version in use



@singleton # Can only ever have one instance
class Door43Bibles:
    """
    Class to download and manipulate online Door43 Bibles.

    """
    def __init__( self ):
        """
        Create the internal Bibles object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bibles.__init__()" )

        self.languageList = self.versionList = self.volumeList = self.volumeNameDict = self.EnglishVolumeNameDict = None
    # end of Door43Bibles.__init__


    def fetchSubjects( self ):
        """
        Download the subject lists from Door43 (around 700 bytes in 2019)

        self.subjectJsonList contains a list of JSON file URLs
        self.subjectNameList will be the same length
                and contain a list of the actual subject names (no underscores, only spaces).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bibles.fetchSubjects()…" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Downloading list of available subjects from Door43…" )

        self.subjectJsonList = self.getOnlineData( 'subjects' ) # Get a normalised, alphabetically ordered list of subject strings
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "  subjectJsonList", len(self.subjectJsonList), self.subjectJsonList )
            assert len(self.subjectJsonList) >= 11 # Otherwise we are losing stuff
            assert isinstance( self.subjectJsonList, list )
        if self.subjectJsonList:
            # Extract the subject names
            jsonFilenameList, self.subjectNameList = [], []
            for subjectJsonURL in self.subjectJsonList:
                assert isinstance( subjectJsonURL, str ) # e.g., 'https://api.door43.org/v3/subjects/Translation_Words.json'
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "    subjectJsonURL", subjectJsonURL )
                bits1 = subjectJsonURL.split('/')
                assert len(bits1) == 6 # e.g., ['https:', '', 'api.door43.org', 'v3', 'subjects', 'Hebrew_Old_Testament.json']
                # print( "      bits1", bits1 )
                jsonFilenameList.append( bits1[-1] )
                subjectName = bits1[-1].split('.')[0] # e.g., 'Translation_Academy'
                self.subjectNameList.append( subjectName.replace( '_', ' ' ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "  subjectNameList", len(self.subjectNameList), self.subjectNameList )
                assert len(self.subjectNameList) == len(self.subjectJsonList) # Otherwise we are losing stuff
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( f"  {len(self.subjectNameList)} Door43 subject fields downloaded" )

            # Now load the individual subject files
            for jsonFilename in jsonFilenameList:
                self.subjectJsonList = self.getOnlineData( f'subjects/{jsonFilename}' )
        # return self.subjectJsonList
    # end of Door43Bibles.fetchSubjects


    def fetchCatalog( self ):
        """
        Download the catalog lists from Door43.

        This can be quite slow (around 1.4 MB in 2019)

        Populates self.languageList (1733 entries as of 2014-10)

        Each list entry is a dictionary, e.g.
            {'language_family_code': 'CTD', 'language_name': 'Zokam', 'language_iso_name': 'Tedim Chin',
                'english_name': 'Zokam', 'language_code': 'CTD', 'language_iso_2B': '', 'language_iso': 'ctd',
                'language_iso_1': '', 'language_iso_2T': ''}
            {'language_family_code': 'ZOS', 'language_name': 'Zoque de Francisco León',
                'language_iso_name': 'Francisco León Zoque', 'english_name': 'Zoque de Francisco Leon',
                'language_code': 'ZOS', 'language_iso_2B': '', 'language_iso': 'zos', 'language_iso_1': '',
                'language_iso_2T': ''}
            {'language_family_code': 'GND', 'language_name': 'Zulgo', 'language_iso_name': 'Zulgo-Gemzek',
                'english_name': 'Zulgo', 'language_code': 'GND', 'language_iso_2B': '', 'language_iso': 'gnd',
                'language_iso_1': '', 'language_iso_2T': ''}
            {'language_family_code': 'ZUN', 'language_name': 'Zuni', 'language_iso_name': 'Zuni',
                'english_name': 'Zuni', 'language_code': 'ZUN', 'language_iso_2B': 'zun', 'language_iso': 'zun',
                'language_iso_1': '', 'language_iso_2T': 'zun'}
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bibles.fetchCatalog()…" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Downloading list of available resources from Door43…" )

        catalog = self.getOnlineData( 'catalog.json' ) # Get an alphabetically ordered list of dictionaries -- one for each language
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "  catalog", len(catalog), catalog.keys() )
            assert 'catalogs' in catalog and 'languages' in catalog
            assert len(catalog) == 2 # Otherwise we are losing stuff
        if catalog:
            assert isinstance( catalog, dict )
            self.catalogList = catalog['catalogs'] # 4 entries: langnames, temp-langnames, approved-temp-langnames, new-language-questions
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "\n    catalogList", len(self.catalogList), self.catalogList )
            assert isinstance( self.catalogList, list )
            self.languageList = catalog['languages']
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "\n    languageList", len(self.languageList), self.languageList[0] )
            assert isinstance( self.languageList, list )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( f"  {len(self.catalogList)} Door43 catalogs downloaded" )
            print( f"  {len(self.languageList)} Door43 languages downloaded" )
        return catalog
    # end of Door43Bibles.fetchCatalog


    def fetchAllVersions( self ):
        """
        Download the version lists from Door43.

        This can be quite slow.

        Populates self.versionList (323 entries as of 2014-10)

        Each list entry is a dictionary, e.g.
            {'version_name': '', 'version_code': 'ABB', 'english_name': ''}
            {'version_name': '', 'version_code': 'ABM', 'english_name': ''}
            {'version_name': '', 'version_code': 'ABS', 'english_name': ''}
            …
            {'version_name': 'Biblia de América', 'version_code': 'BDA', 'english_name': ' Biblia de America'}
            {'version_name': 'Hermanos Libres del Ecuador', 'version_code': 'HLE', 'english_name': ' Hermanos Libres del Ecuador'}
            {'version_name': '1545 Luther Bibel', 'version_code': 'L45', 'english_name': '1545 Luther Bibel'}
            …
            {'version_name': 'Yessan-Mayo Yamano Version', 'version_code': 'YYV', 'english_name': 'Yessan-Mayo Yamano Version'}
            {'version_name': 'Yessan-Mayo Yawu', 'version_code': 'YWV', 'english_name': 'Yessan-Mayo Yawu'}
            {'version_name': 'Ze Zoo Zersion', 'version_code': 'ZZQ', 'english_name': 'Ze Zoo Zersion'}
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bibles.fetchAllVersions()" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Downloading list of available versions from Door43…" )

        if self.onlineVersion: # Get a list of available data sets
            self.versionList = self.getOnlineData( 'library/version' ) # Get an alphabetically ordered list of dictionaries -- one for each version
            if BibleOrgSysGlobals.debugFlag:
                print( "  versionList", len(self.versionList) )#, self.versionList )
        return self.versionList
    # end of Door43Bibles.fetchAllVersions


    def __str__( self ):
        """
        Create a string representation of the Bibles object.
        """
        indent = 2
        result = f"Door43 v{Door43_API_Version} online Bible object"
        if self.languageList: result += ('\n' if result else '') + ' '*indent + _("Languages: {}").format( len(self.languageList) )
        if self.versionList: result += ('\n' if result else '') + ' '*indent + _("Versions: {}").format( len(self.versionList) )
        if self.volumeList: result += ('\n' if result else '') + ' '*indent + _("Volumes: {}").format( len(self.volumeList) )
        if self.volumeNameDict: result += ('\n' if result else '') + ' '*indent + _("Displayable volumes: {}").format( len(self.volumeNameDict) )
        return result
    # end of Door43Bibles.__str__


    def getOnlineData( self, fieldREST, additionalParameters=None ):
        """
        Given a string, e.g., "api/apiversion"
            Does an HTTP GET to our site.
            Receives the JSON result (hopefully)
            Converts the JSON bytes to a JSON string
            Loads the JSON string into a Python container.
            Returns the container.

        Returns None if the data cannot be fetched.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"Door43Bibles.getOnlineData( {fieldREST!r}, {additionalParameters!r} )…" )

        requestString = f'{URL_FULL_BASE}{fieldREST}'
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Request string is", repr(requestString) )
        try: HTTPResponseObject = urllib.request.urlopen( requestString )
        except urllib.error.URLError as err:
            #errorClass, exceptionInstance, traceback = sys.exc_info()
            #print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
            logging.error( "Door43 URLError '{}' from {}".format( err, requestString ) )
            return None
        # print( "  HTTPResponseObject", HTTPResponseObject )
        contentType = HTTPResponseObject.info().get( 'content-type' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "    contentType", contentType )
        if contentType == 'application/json':
            responseJSON = HTTPResponseObject.read()
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "      responseJSON", len(responseJSON), responseJSON[:100], '…' )
            responseJSONencoding = HTTPResponseObject.info().get_content_charset( 'utf-8' )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "      responseJSONencoding", responseJSONencoding )
            responseSTR = responseJSON.decode( responseJSONencoding )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "      responseSTR", len(responseSTR), responseSTR[:100], '…' )
            return json.loads( responseSTR )
        else:
            if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                print( "    contentType", contentType )
            halt # Haven't had this contentType before
    # end of Door43Bibles.getOnlineData


    def searchNames( self, searchText ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bibles.searchNames( {!r} )".format( searchText ) )

        searchTextUC = searchText.upper()
        resultsList = []
        for name in self.volumeNameDict:
            if searchTextUC in name.upper():
                for refNumber in self.volumeNameDict[name]:
                    DAM = self.getDAM(refNumber)
                    if BibleOrgSysGlobals.debugFlag:
                        print( "DAM: {}".format( DAM ) )
                        if BibleOrgSysGlobals.debugFlag:
                            assert DAM.endswith('2ET') or DAM.endswith('1ET') # O2 (OT) or N2 (NT), plus ET for text
                    resultsList.append( (refNumber,DAM,) )
        return resultsList
    # end of Door43Bibles.searchNames
# end of class Door43Bibles



class Door43Bible:
    """
    Class to download and manipulate an online Door43 Bible.

    Note that this Bible class is NOT based on the Bible class
        because it's so unlike most Bibles which are local.
    """
    def __init__( self, damRoot ):
        """
        Create the Door43 cataloged Bible object.
            Accepts a 6-character code which is the initial part of the DAM:
                1-3: Language code, e.g., ENG
                4-6: Version code, e.g., ESV
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bible.__init__( {!r} )".format( damRoot ) )
            assert damRoot and isinstance( damRoot, str ) and len(damRoot)==6
        self.damRoot = damRoot

         # Setup and initialise the base class first
        #InternalBible.__init__( self, givenFolderName, givenName, encoding )

        self.URLFixedData = '?v={}&key={}'.format( Door43_API_Version, self.key )

        # See if the site is online by making a small call to get the API version
        self.URLTest = 'api/apiversion'
        self.onlineVersion = None
        result = self.getOnlineData( self.URLTest )
        if result:
            if 'Version' in result: self.onlineVersion = result['Version']
        else:
            logging.critical( "DPBBible.__init__: Digital Bible Platform appears to be offline" )
            raise ConnectionError # What should this really be?

        self.bookList = None
        if self.onlineVersion: # Check that this particular resource is available by getting a list of books
            bookList = self.getOnlineData( "library/book", "dam_id="+self.damRoot ) # Get an ordered list of dictionaries -- one for each book
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "Door43Bible.__init__: bookList", len(bookList))#, bookList )

            #if 0:# Get all book codes and English names
                #bookCodeDictList = self.getOnlineData( "library/bookname", "language_code=ENG" )
                ## Not sure why it comes back as a dictionary in a one-element list
                #assert isinstance( bookCodeDictList, list ) and len(bookCodeDictList)==1
                #bookCodeDict = bookCodeDictList[0]
                #assert isinstance( bookCodeDict, dict )
                #print( "bookCodeDict", len(bookCodeDict), bookCodeDict )

        self.books = OrderedDict()
        if bookList: # Convert to a form that's easier for us to use later
            for bookDict in bookList:
                OSISCode = bookDict['book_id']
                #print( "OSIS", OSISCode )
                BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromOSISAbbreviation( OSISCode )
                if isinstance( BBB, list ): BBB = BBB[0] # Take the first one if we get something like ['EZR','EZN']
                #print( "BBB", BBB )
                #print( bookDict )
                self.books[BBB] = bookDict
            del bookList

        self.cache = OrderedDict()
    # end of Door43Bible.__init__


    def __str__( self ):
        """
        Create a string representation of the Bible object.
        """
        indent = 2
        result = "Door43 online Bible object"
        if self.onlineVersion: result += ('\n' if result else '') + ' '*indent + _("Online version: {}").format( self.onlineVersion )
        result += ('\n' if result else '') + ' '*indent + _("DAM root: {}").format( self.damRoot )
        if self.books: result += ('\n' if result else '') + ' '*indent + _("Books: {}").format( len(self.books) )
        return result
    # end of Door43Bible.__str__


    def __len__( self ):
        """
        This method returns the number of books in the Bible.
        """
        return len( self.books )
    # end of Door43Bible.__len__


    def __contains__( self, BBB ):
        """
        This method checks whether the Bible contains the BBB book.
        Returns True or False.
        """
        if BibleOrgSysGlobals.debugFlag:
            assert isinstance(BBB,str) and len(BBB)==3

        return BBB in self.books
    # end of Door43Bible.__contains__


    def __getitem__( self, keyIndex ):
        """
        Given an index, return the book object (or raise an IndexError)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bible.__getitem__( {!r} )".format( keyIndex ) )

        return list(self.books.items())[keyIndex][1] # element 0 is BBB, element 1 is the book object
    # end of Door43Bible.__getitem__


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
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bible.getOnlineData( {!r} {!r} )".format( fieldREST, additionalParameters ) )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Requesting data from {} for {}…".format( URL_BASE, self.damRoot ) )
        requestString = "{}{}{}{}".format( URL_BASE, fieldREST, self.URLFixedData, '&'+additionalParameters if additionalParameters else '' )
        #print( "Request string is", repr(requestString) )
        try: responseJSON = urllib.request.urlopen( requestString )
        except urllib.error.URLError:
            if BibleOrgSysGlobals.debugFlag: logging.critical( "Door43Bible.getOnlineData: error fetching {!r} {!r}".format( fieldREST, additionalParameters ) )
            return None
        responseSTR = responseJSON.read().decode('utf-8')
        return json.loads( responseSTR )
    # end of Door43Bible.getOnlineData


    def getVerseDataList( self, key ):
        """
        Equivalent to the one in InternalBible, except we may have to fetch the data (if it's not already cached).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bible.getVerseDataList( {!r} ) for {!r}".format( key, self.damRoot ) )

        if str(key) in self.cache:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                 print( "  " + "Retrieved from cache" )
            self.cache.move_to_end( str(key) )
            return self.cache[str(key)]
        BBB = key.getBBB()
        if BBB in self.books:
            info = self.books[BBB]
            rawData = self.getOnlineData( 'text/verse', 'dam_id={}&book_id={}&chapter_id={}&verse_start={}'.format( info['dam_id']+'2ET', info['book_id'], key.getChapterNumber(), key.getVerseNumber() ) )
            resultList = []
            if isinstance( rawData, list ) and len(rawData)==1:
                rawDataDict = rawData[0]
                #print( len(rawDataDict), rawDataDict )
                assert len(rawDataDict)==8 and isinstance( rawDataDict, dict )
                resultList.append( ('p#','p#',rawDataDict['paragraph_number'],rawDataDict['paragraph_number'],[]) ) # Must be first for Biblelator
                if key.getVerseNumber()=='1': resultList.append( ('c#','c#',rawDataDict['chapter_id'],rawDataDict['chapter_id'],[]) )
                resultList.append( ('v','v',rawDataDict['verse_id'],rawDataDict['verse_id'],[]) )
                resultList.append( ('v~','v~',rawDataDict['verse_text'].strip(),rawDataDict['verse_text'].strip(),[]) )
                self.cache[str(key)] = resultList
                if len(self.cache) > MAX_CACHED_VERSES:
                    #print( "Removing oldest cached entry", len(self.cache) )
                    self.cache.popitem( last=False )
            return resultList
        else: # This version doesn't have this book
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  getVerseDataList: {} not in {} {}".format( BBB, self.damRoot, self.books.keys() ) )
    # end of Door43Bible.getVerseDataList


    def getContextVerseData( self, key ):
        """
        Given a BCV key, get the verse data.

        (The Digital Bible Platform doesn't provide the context so an empty list is always returned.)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43Bible.getContextVerseData( {!r} ) for {!r}".format( key, self.damRoot ) )

        return self.getVerseDataList( key ), [] # No context
    # end of Door43Bible.getContextVerseData
# end of class Door43Bible



def demo():
    """
    Demonstrate how some of the above classes can be used.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    if 1: # Test the Door43Bibles class
        print()
        door43Bibles = Door43Bibles()
        print( door43Bibles )
        #Door43Bibles.load() # takes a minute
        #print( Door43Bibles )

        if 1:
            door43Bibles.fetchSubjects()

        if 1:
            door43Bibles.fetchCatalog()
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( f"\nLanguage list ({len(door43Bibles.languageList)}):" )
            for j, lgDict in enumerate( door43Bibles.languageList ):
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( '  Lg', j+1, lgDict['identifier'], lgDict['direction'], lgDict['title'] )
                # lgDict.keys() are lgDict['identifier']
                assert 4 <= len(lgDict.keys()) <= 6 # 'category_labels', 'direction', 'identifier', 'resources', 'title', 'versification_labels'
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( '   ', len(lgDict.keys()), lgDict.keys() )
                for something in lgDict['resources']:
                    assert isinstance( something, dict )
                    if BibleOrgSysGlobals.verbosityLevel > 2:
                        print( f"   \"{something['title']}\" ({something['subject']}) ({len(something.keys())}) {something.keys()}" )
                    if not something['subject']:
                        logging.critical( f"Missing subject field from {lgDict['identifier']} {something['title']}" )
                    elif something['subject'] not in door43Bibles.subjectNameList:
                        logging.critical( f"Unknown '{something['subject']}' subject field from {lgDict['identifier']} {something['title']}" )
                if 'category_labels' in lgDict:
                    if BibleOrgSysGlobals.verbosityLevel > 2:
                        print( '    category_labels', lgDict['category_labels'] )
                if 'versification_labels' in lgDict:
                    if BibleOrgSysGlobals.verbosityLevel > 2:
                        print( '    versification_labels', lgDict['versification_labels'] )

        if 0:
            door43Bibles.fetchAllVersions()
            print( "\nVersion list ({}):".format( len(door43Bibles.versionList) ) )
            for j, verDict in enumerate( door43Bibles.versionList ):
                print( 'Ver', j, repr(verDict) )


        if 0:
            door43Bibles.fetchAllEnglishTextVolumes()
            print( "\nEnglish volume name dict ({}):".format( len(door43Bibles.EnglishVolumeNameDict) ) )
            for j, someName in enumerate( door43Bibles.EnglishVolumeNameDict ):
                #if 'English' in someName:
                    #print( "English:", repr(someName), repr(door43Bibles.EnglishVolumeNameDict[someName]) )
                print( "  {}/ {!r} {!r}".format( j, someName, door43Bibles.EnglishVolumeNameDict[someName] ) )
                #if 'English' in someName:
                    #print( "  English:", repr(someName), repr(door43Bibles.EnglishVolumeNameDict[someName]) )


    testRefs = ( ('GEN','1','1'), ('JER','33','3'), ('MAL','4','6'), ('MAT','1','1'), ('JHN','3','16'), ('JDE','1','14'), ('REV','22','21'), )

    if 0: # Test the Door43Bible class with the ESV
        print()
        Door43Bible1 = Door43Bible( "ENGESV" )
        print( Door43Bible1 )
        for testRef in testRefs:
            verseKey = SimpleVerseKey( *testRef )
            print( verseKey )
            print( " ", Door43Bible1.getVerseDataList( verseKey ) )
         # Now test the Door43Bible class caching
        for testRef in testRefs:
            verseKey = SimpleVerseKey( *testRef )
            print( verseKey, "cached" )
            print( " ", Door43Bible1.getVerseDataList( verseKey ) )


    if 1: # Test the Door43Bible class with the MS
        print()
        Door43Bible2 = Door43Bible( "MBTWBT" )
        print( Door43Bible2 )
        for testRef in testRefs:
            verseKey = SimpleVerseKey( *testRef )
            print( verseKey )
            print( " ", Door43Bible2.getVerseDataList( verseKey ) )
# end of demo

if __name__ == '__main__':
    #from multiprocessing import freeze_support
    #freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of Door43Online.py
