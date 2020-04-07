#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Door43ContentServiceOnline.py
#
# Module handling online DCS resources
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
This module interfaces with the online Bible versions available
    from Door43 content service (unfoldingWord) API.

In this module, we use:
    DCS = Door43 content service

This module is up-to-date for version 1.9.5 of the DCS/Gitea.

More details are available from https://api-info.readthedocs.io/en/latest/dcs.html
                            and https://git.door43.org/api/swagger.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-18' # by RJH
SHORT_PROGRAM_NAME = "Door43ContentService"
PROGRAM_NAME = "Door43 Content Service online handler"
PROGRAM_VERSION = '0.04'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging
import urllib.request
import json
import tempfile, zipfile
from datetime import datetime

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys.Formats.USFMBible import USFMBible


URL_BASE = 'https://git.door43.org/api/' # API endpoint
DCS_API_VERSION = '1'
URL_FULL_BASE = f'{URL_BASE}/v{DCS_API_VERSION}/'
DEFAULT_DOWNLOAD_FOLDERPATH = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH.joinpath( 'Door43ContentServiceOnline/' )



@singleton # Can only ever have one instance
class DCSBibles:
    """
    Class to download and manipulate online DCS Bibles.

    """
    def __init__( self ):
        """
        Create the internal Bibles object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("DCSBibles.__init__()…") )

        # See if the site is online by making a small call to get the API version
        self.onlineVersion = None
        result = self.getOnlineData( 'version' )
        #print( "version result", result )
        if result and isinstance( result, dict) and 'version' in result:
            self.onlineVersion = result['version']
            if debuggingThisModule and BibleOrgSysGlobals.verbosityLevel > 3:
                print( f"DCS API version {self.onlineVersion} is online." )
        self.languageList = self.versionList = self.volumeList = self.volumeNameDict = self.EnglishVolumeNameDict = None
    # end of DCSBibles.__init__


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
            print( f"DCSBibles.getOnlineData( '{fieldREST}', '{additionalParameters}' )…" )

        requestString = f'{URL_FULL_BASE}{fieldREST}'
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Request string is", repr(requestString) )
        try: HTTPResponseObject = urllib.request.urlopen( requestString )
        except urllib.error.URLError as err:
            #errorClass, exceptionInstance, traceback = sys.exc_info()
            #print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
            logging.error( "DCS URLError '{}' from {}".format( err, requestString ) )
            return None
        #print( "  HTTPResponseObject", HTTPResponseObject )
        contentType = HTTPResponseObject.info().get( 'content-type' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"    contentType='{contentType}'" )
        if 'application/json' in contentType:
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
    # end of DCSBibles.getOnlineData


    def fetchAllBibles( self ):
        """
        Download the Bible lists from DCS.

        This can be quite slow.

        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "DCSBibles.fetchAllBibles()…" )

        limit = 500 # Documentation says 50, but larger numbers seem to work ok
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( f"Downloading list of available Bibles from DCS ({limit} at a time)…" )

        if self.onlineVersion: # Get a list of available data sets
            self.BibleList = []
            # Does a case-insensitive search
            for searchText in ('ULT', 'UST', 'Bible', 'ULB', 'UDB'): # 7,227 if these are all included!!!
                pageNumber = 1
                while True:
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        print( f"  Getting '{searchText}' page {pageNumber}…" )
                    resultDict = self.getOnlineData( f'repos/search?q={searchText}&page={pageNumber}&limit={limit}' )
                    #print( f"  Result {type(resultDict)} {len(resultDict)} = {resultDict}" )
                    # resultDict should be a dict of length 2 with keys 'ok'(=True) and 'data'
                    assert resultDict and isinstance( resultDict, dict) and  len(resultDict) == 2 \
                                    and resultDict['ok']==True
                    if not resultDict['data']: break # no more data
                    if BibleOrgSysGlobals.verbosityLevel > 1:
                        print( f"    Got {len(resultDict['data'])} entries" )
                    self.BibleList.extend( resultDict['data'] )
                    if pageNumber > 1 \
                    and len(resultDict['data']) < limit: # must be finished
                        break
                    pageNumber += 1
            if BibleOrgSysGlobals.debugFlag: print( "  BibleList", len(self.BibleList) , self.BibleList )
        return self.BibleList
    # end of DCSBibles.fetchAllBibles


    #def fetchAllVersions( self ):
        #"""
        #Download the version lists from unfoldingWord.

        #This can be quite slow.

        #Populates self.versionList (323 entries as of 2014-10)

        #Each list entry is a dictionary, e.g.
            #{'version_name': '', 'version_code': 'ABB', 'english_name': ''}
            #{'version_name': '', 'version_code': 'ABM', 'english_name': ''}
            #{'version_name': '', 'version_code': 'ABS', 'english_name': ''}
            #…
            #{'version_name': 'Biblia de América', 'version_code': 'BDA', 'english_name': ' Biblia de America'}
            #{'version_name': 'Hermanos Libres del Ecuador', 'version_code': 'HLE', 'english_name': ' Hermanos Libres del Ecuador'}
            #{'version_name': '1545 Luther Bibel', 'version_code': 'L45', 'english_name': '1545 Luther Bibel'}
            #…
            #{'version_name': 'Yessan-Mayo Yamano Version', 'version_code': 'YYV', 'english_name': 'Yessan-Mayo Yamano Version'}
            #{'version_name': 'Yessan-Mayo Yawu', 'version_code': 'YWV', 'english_name': 'Yessan-Mayo Yawu'}
            #{'version_name': 'Ze Zoo Zersion', 'version_code': 'ZZQ', 'english_name': 'Ze Zoo Zersion'}
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( _("DCSBibles.fetchAllVersions()") )

        #if BibleOrgSysGlobals.verbosityLevel > 2:
            #print( _("Downloading list of available versions from unfoldingWord…") )

        #if self.onlineVersion: # Get a list of available data sets
            #self.versionList = self.getOnlineData( 'library/version' ) # Get an alphabetically ordered list of dictionaries -- one for each version
            #if BibleOrgSysGlobals.debugFlag: print( "  versionList", len(self.versionList) )#, self.versionList )
        #return self.versionList
    ## end of DCSBibles.fetchAllVersions


    def __str__( self ):
        """
        Create a string representation of the DCSBibles object.
        """
        indent = 2
        result = "DCS online Bibles object"
        if self.onlineVersion: result += ('\n' if result else '') + ' '*indent + _("Online version: {}").format( self.onlineVersion )
        if self.languageList: result += ('\n' if result else '') + ' '*indent + _("Languages: {}").format( len(self.languageList) )
        if self.versionList: result += ('\n' if result else '') + ' '*indent + _("Versions: {}").format( len(self.versionList) )
        if self.volumeList: result += ('\n' if result else '') + ' '*indent + _("Volumes: {}").format( len(self.volumeList) )
        if self.volumeNameDict: result += ('\n' if result else '') + ' '*indent + _("Displayable volumes: {}").format( len(self.volumeNameDict) )
        return result
    # end of DCSBibles.__str__


    #def searchNames( self, searchText ):
        #"""
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( _("DCSBibles.searchNames( {!r} )").format( searchText ) )

        #searchTextUC = searchText.upper()
        #resultsList = []
        #for name in self.volumeNameDict:
            #if searchTextUC in name.upper():
                #for refNumber in self.volumeNameDict[name]:
                    #DAM = self.getDAM(refNumber)
                    #if BibleOrgSysGlobals.debugFlag:
                        #print( _("DAM: {}").format( DAM ) )
                        #if BibleOrgSysGlobals.debugFlag:
                            #assert DAM.endswith('2ET') or DAM.endswith('1ET') # O2 (OT) or N2 (NT), plus ET for text
                    #resultsList.append( (refNumber,DAM,) )
        #return resultsList
    ## end of DCSBibles.searchNames


    def searchReposExact( self, wantedRepoOwner=None, wantedRepoTitle=None ):
        """
        Search thru the list of available online Bibles to find
            a match of the optional title and optional owner.

        Returns the dictionary for the resource
            (or a list of dictionaries if there's multiple matches)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"DCSBibles.searchReposExact( {wantedRepoOwner!r}, {wantedRepoTitle!r} )…" )

        resultsList = []
        for entryDict in self.BibleList:
            #print( 'entryDict', type(entryDict), len(entryDict), repr(entryDict), '\n' )
            assert entryDict and isinstance( entryDict, dict) and len(entryDict)>=23
            ownerName = entryDict['owner']['full_name']
            if not ownerName: ownerName = entryDict['owner']['username']
            if (wantedRepoOwner is None or wantedRepoOwner==ownerName) \
            and (wantedRepoTitle is None or wantedRepoTitle==entryDict['name']):
                resultsList.append( entryDict )
        if len(resultsList) == 1: return resultsList[0]
        return resultsList
    # end of DCSBibles.searchReposExact


    def searchReposFuzzy( self, wantedRepoOwner=None, wantedRepoTitle=None ):
        """
        Search thru the list of available online Bibles to find
            a match of the optional title and optional owner.

        Returns the dictionary for the resource
            (or a list of dictionaries if there's multiple matches)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"DCSBibles.searchReposFuzzy( {wantedRepoOwner!r}, {wantedRepoTitle!r} )…" )

        resultsList = []
        for entryDict in self.BibleList:
            #print( 'entryDict', type(entryDict), len(entryDict), repr(entryDict), '\n' )
            assert entryDict and isinstance( entryDict, dict) and len(entryDict)>=23
            ownerName = entryDict['owner']['full_name']
            if not ownerName: ownerName = entryDict['owner']['username']
            if (wantedRepoOwner is None or wantedRepoOwner in ownerName) \
            and (wantedRepoTitle is None or wantedRepoTitle in entryDict['name']):
                resultsList.append( entryDict )
        if len(resultsList) == 1: return resultsList[0]
        return resultsList
    # end of DCSBibles.searchReposFuzzy
# end of class DCSBibles



class DCSBible( USFMBible ):
    """
    Class to download and manipulate an online Door43 Bible from the catalog.

    The interface provides a link to a zip file containing all of the USFM books.
    """
    def __init__( self, parameterOne, resourcesObject=None, downloadAllBooks=False ):
        """
        Create the Door43 cataloged Bible object.

        parameterOne can be:
            a catalog dictionary entry (and second parameter must be None)
        or
            an index into the BibleList in the resourcesObject passed as the second parameter
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"DCSBible.__init__( {parameterOne}, {resourcesObject}, {downloadAllBooks} )…" )

        if isinstance( parameterOne, dict ):
            assert resourcesObject is None
            resourceDict = parameterOne
        else:
            assert isinstance( parameterOne, int )
            assert resourcesObject # why ??? and isinstance( resourcesObject, Door43CatalogResources )
            resourceDict = resourcesObject.getBibleResourceDict( parameterOne )
        assert resourceDict and isinstance( resourceDict, dict )
        #print( 'resourceDict', resourceDict )
        #print( 'resourceDict', resourceDict.keys() )

        self.baseURL = resourceDict['html_url']
        #print( 'self.baseURL', self.baseURL )
        adjustedRepoName = resourceDict['full_name'].replace( '/', '--' )
        #print( 'adjustedRepoName', adjustedRepoName )
        desiredFolderName = BibleOrgSysGlobals.makeSafeFilename( adjustedRepoName )
        unzippedFolderPath = DEFAULT_DOWNLOAD_FOLDERPATH.joinpath( f'{adjustedRepoName}/' )

        if downloadAllBooks:
            # See if files already exist and are current (so don't download again)
            alreadyDownloadedFlag = False
            if os.path.isdir( unzippedFolderPath ):
                #print( f"Issued: {resourceDict['issued']}" )
                updatedDatetime = datetime.strptime( resourceDict['updated_at'], '%Y-%m-%dT%H:%M:%SZ' )
                #print( f"updatedDatetime: {updatedDatetime}" )
                #print( f"folder: {os.stat(unzippedFolderPath).st_mtime}" )
                folderModifiedDatetime = datetime.fromtimestamp(os.stat(unzippedFolderPath).st_mtime)
                #print( f"folderModifiedDatetime: {folderModifiedDatetime}" )
                alreadyDownloadedFlag = folderModifiedDatetime > updatedDatetime
                #print( f"alreadyDownloadedFlag: {alreadyDownloadedFlag}" )

            if alreadyDownloadedFlag:
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Skipping download because folder '{}' already exists.".format( unzippedFolderPath ) )
            else: # Download the zip file (containing all the USFM files, README.md, LICENSE.md, manifest.yaml, etc.)
                # TODO: Change to .tar.gz instead of zip
                zipURL = self.baseURL + '/archive/master.zip' # '/archive/master.tar.gz'
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Downloading entire repo from '{}'…".format( zipURL ) )
                try: HTTPResponseObject = urllib.request.urlopen( zipURL )
                except urllib.error.URLError as err:
                    #errorClass, exceptionInstance, traceback = sys.exc_info()
                    #print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
                    logging.critical( "DCS URLError '{}' from {}".format( err, zipURL ) )
                    return
                # print( "  HTTPResponseObject", HTTPResponseObject )
                contentType = HTTPResponseObject.info().get( 'content-type' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "    contentType", repr(contentType) )
                if contentType == 'application/octet-stream':
                    try: os.makedirs( unzippedFolderPath )
                    except FileExistsError: pass
                    downloadedData = HTTPResponseObject.read()
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        print( f"  Downloaded {len(downloadedData):,} bytes from '{zipURL}'" )
                    # Bug in Python up to 3.7 makes this not work for large aligned Bibles (3+ MB)
                    # myTempFile = tempfile.SpooledTemporaryFile()
                    myTempFile = tempfile.TemporaryFile()
                    myTempFile.write( downloadedData )
                    with zipfile.ZipFile( myTempFile ) as myzip:
                        # NOTE: Could be a security risk here
                        myzip.extractall( unzippedFolderPath )
                    myTempFile.close() # Automatically deletes the file
                else:
                    print( "    contentType", repr(contentType) )
                    halt # unknown content type
            self.downloadedAllBooks = True

            # There's probably a folder inside this folder
            folders = os.listdir( unzippedFolderPath )
            #print( 'folders', folders )
            assert len(folders) == 1 # else maybe a previous download failed -- just manually delete the folder
            desiredFolderName = folders[0] + '/'
            #print( 'desiredFolderName', desiredFolderName )
            USFMBible.__init__( self, os.path.join( unzippedFolderPath, desiredFolderName ),
                                                            givenName=resourceDict['name'] )
        else: # didn't request all books to be downloaded at once
            self.downloadedAllBooks = False
            self.attemptedDownload = {}
            try: os.makedirs( unzippedFolderPath )
            except FileExistsError: pass
            USFMBible.__init__( self, unzippedFolderPath, givenName=resourceDict['name'] )
        self.objectNameString = 'DCS USFM Bible object'
        self.uWaligned = True
    # end of DCSBible.__init__


    def loadBookIfNecessary( self, BBB ):
        """
        Download the book if necessary.

        TODO: This function doesn't check if the USFM book was downloaded by a previous run
                (and is still up-to-date)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"DCSBible.loadBookIfNecessary( {BBB} )…" )

        if not self.downloadedAllBooks:
            if BBB not in self.attemptedDownload or not self.attemptedDownload[BBB]:
                self.attemptedDownload[BBB] = True

                # TODO: Change to .tar.gz instead of zip
                nn = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
                if nn > 39: nn += 1 # DSC uses #41 for MAT (not 39)
                uBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper()
                USFMfilename = f'{nn:02}-{uBBB}.usfm'
                zipURL = f'{self.baseURL}/raw/branch/master/{USFMfilename}'
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Downloading {} file from '{}'…".format( BBB, zipURL ) )
                try: HTTPResponseObject = urllib.request.urlopen( zipURL )
                except urllib.error.HTTPError as err:
                    #errorClass, exceptionInstance, traceback = sys.exc_info()
                    #print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
                    logging.critical( "DCS HTTPError '{}' from {}".format( err, zipURL ) )
                    return
                except urllib.error.URLError as err:
                    #errorClass, exceptionInstance, traceback = sys.exc_info()
                    #print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
                    logging.critical( "DCS URLError '{}' from {}".format( err, zipURL ) )
                    return
                # print( "  HTTPResponseObject", HTTPResponseObject )
                contentType = HTTPResponseObject.info().get( 'content-type' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "    contentType", repr(contentType) )
                if contentType == 'text/plain; charset=utf-8':
                    downloadedData = HTTPResponseObject.read()
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        print( f"  Downloaded {len(downloadedData):,} bytes from '{zipURL}'" )
                    with open( os.path.join( self.sourceFolder, USFMfilename ), 'wt' ) as ourUSFMfile:
                        ourUSFMfile.write( downloadedData.decode( 'utf-8' ) )
                else:
                    print( "    contentType", repr(contentType) )
                    halt # unknown content type
                if not self.preloadDone:
                    self.preload()
            else:
                if BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule or BibleOrgSysGlobals.debugFlag:
                    print( f"{BBB} was already downloaded (or attempted)" )
                return

        USFMBible.loadBookIfNecessary( self, BBB )
    # end of DCSBible.loadBookIfNecessary
# end of class DCSBible



def demo() -> None:
    """
    Demonstrate how some of the above classes can be used.
    """
    from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey

    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion, end='\n\n' )

    # Test the DCSBibles class (also used later)
    if BibleOrgSysGlobals.verbosityLevel > 0: print("\n\nA/ DCSBibles class test…")
    dcsBibles = DCSBibles()
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print( dcsBibles, end='\n\n' )
    #dcsBibles.load() # takes a minute
    #print( dcsBibles )
    dcsBibles.fetchAllBibles()

    if 0: # print the list
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "Bible list ({}):".format( len(dcsBibles.BibleList) ) )
        for j, BibleDict in enumerate( dcsBibles.BibleList, start=1 ):
            ownerName = BibleDict['owner']['full_name']
            if not ownerName: ownerName = BibleDict['owner']['username']
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( f"  Entry {j:3} '{BibleDict['name']}'  '{ownerName}'" )


    testRefs = ( ('GEN','1','1'), ('GEN','2','2'), ('JER','33','3'), ('MAL','4','6'),
                 ('MAT','1','1'), ('JHN','3','16'), ('JDE','1','14'), ('REV','22','21'), )

    def processSearchResult( searchResult:dict, downloadAllBooks:bool=False ) -> None:
        if searchResult and isinstance( searchResult, dict ):
            dcsBible1 = DCSBible( searchResult, downloadAllBooks=downloadAllBooks )
            try: dcsBible1.preload()
            except FileNotFoundError: assert downloadAllBooks == False
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( dcsBible1, end='\n\n' )
            for testRef in testRefs:
                verseKey = SimpleVerseKey( *testRef )
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    print( verseKey )
                    print( " ", dcsBible1.getVerseDataList( verseKey ) )
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            print( f"Unexpected search result: {searchResult}" )
    # end of processSearchResult function

    if 1: # Test the DCSBible class with the ULT
        if BibleOrgSysGlobals.verbosityLevel > 0: print("\n\nB/ ULT test")
        downloadAllBooks = True
        searchResult = dcsBibles.searchReposExact( 'unfoldingWord', 'en_ult' )
        if searchResult:
            #print( 'searchResult', type(searchResult), len(searchResult), searchResult )
            if isinstance(searchResult, dict):
                processSearchResult( searchResult, downloadAllBooks )
            elif isinstance(searchResult, list):
                if BibleOrgSysGlobals.verbosityLevel > 0: print( f"Found {len(searchResult)} 'en_ult' repos!" )
                searchResults = searchResult
                for searchResult in searchResults:
                    processSearchResult( searchResult, downloadAllBooks )
            else:
                logging.critical( f"Bad search result {type(searchResult)} ({len(searchResult)}): {searchResult}" )
        else:
            logging.critical( f"Empty search result: {searchResult}" )

    if 1: # Test the DCSBible class with the UST
        if BibleOrgSysGlobals.verbosityLevel > 0: print("\n\nC/ UST test")
        downloadAllBooks = False
        searchResult = dcsBibles.searchReposExact( 'unfoldingWord', 'en_ust' )
        if searchResult:
            #print( 'searchResult', type(searchResult), len(searchResult), searchResult )
            if isinstance(searchResult, dict):
                processSearchResult( searchResult, downloadAllBooks )
            elif isinstance(searchResult, list):
                if BibleOrgSysGlobals.verbosityLevel > 0: print( f"Found {len(searchResult)} 'en_ust' repos!" )
                searchResults = searchResult
                for searchResult in searchResults:
                    processSearchResult( searchResult, downloadAllBooks )
            else:
                logging.critical( f"Bad search result {type(searchResult)} ({len(searchResult)}): {searchResult}" )
        else:
            logging.critical( f"Empty search result: {searchResult}" )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of Door43ContentServiceOnline.py
