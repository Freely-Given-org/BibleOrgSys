#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Door43OnlineCatalog.py
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

LAST_MODIFIED_DATE = '2019-07-15' # by RJH
SHORT_PROGRAM_NAME = "Door43OnlineCatalog"
PROGRAM_NAME = "Door43 Online Catalog online handler"
PROGRAM_VERSION = '0.08'
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
    import re
import logging # Append the containing folder to the path to search for the BOS
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys.Formats.USFMBible import USFMBible


URL_BASE = 'https://api.door43.org'
Door43_API_Version = '3'
URL_FULL_BASE = f'{URL_BASE}/v{Door43_API_Version}/'



@singleton # Can only ever have one instance
class Door43CatalogResources:
    """
    Class to download and manipulate online Door43 Bibles.

    """
    def __init__( self ):
        """
        Create the internal Bibles object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43CatalogResources.__init__()…" )

        self.subjectJsonList = self.subjectNameList = self.subjectsJsonList = self.subjectDict = None
        self.catalogDict = self.languageDict = self.resourceList = self.BibleList = None
    # end of Door43CatalogResources.__init__


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
            print( f"Door43CatalogResources.getOnlineData( '{fieldREST}', '{additionalParameters}' )…" )

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
            print( f"    contentType='{contentType}'" )
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
    # end of Door43CatalogResources.getOnlineData


    def fetchSubjects( self ):
        """
        self.subjectNameList will contain a list/set of the actual subject names (no underscores, only spaces).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43CatalogResources.fetchSubjects()…" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  Downloading list of available subjects from Door43…" )

        if 1: # new code -- only one large download
            # Download the pivoted subject lists from Door43 (around 1.3MB in 2019-02)
            pivotedSubjectJsonList = self.getOnlineData( 'subjects/pivoted.json' )
            assert isinstance( pivotedSubjectJsonList, dict )
            assert 'catalogs' in pivotedSubjectJsonList and 'subjects' in pivotedSubjectJsonList
            assert len(pivotedSubjectJsonList) == 2 # Otherwise we are losing stuff

            # Populates self.catalogDict (4 entries as of 2019-02):
            #                        langnames, temp-langnames, approved-temp-langnames, new-language-questions
            assert isinstance( pivotedSubjectJsonList['catalogs'], list )
            self.catalogDict = {}
            for entry in pivotedSubjectJsonList['catalogs']: # 4 entries: langnames, temp-langnames, approved-temp-langnames, new-language-questions
                assert isinstance( entry, dict )
                self.catalogDict[entry['identifier']] = entry
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "\n    catalogDict", len(self.catalogDict), self.catalogDict )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( f"    Downloaded {len(self.catalogDict)} Door43 catalogs" )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( f"      {list(self.catalogDict.keys())}" )

            assert isinstance( pivotedSubjectJsonList['subjects'], list )
            self.totalEntryCount = len( pivotedSubjectJsonList['subjects'] )
            #print( self.totalEntryCount ) # 163
            assert self.totalEntryCount >= 163 # Otherwise we are losing stuff
            #print( pivotedSubjectJsonList['subjects'][0] )
            self.subjectNameList, self.subjectDict = set(), {}
            for subjectEntry in pivotedSubjectJsonList['subjects']:
                #print( subjectEntry )
                assert isinstance( subjectEntry, dict )
                subject = subjectEntry['subject']
                self.subjectNameList.add( subject )
                if subject not in self.subjectDict: self.subjectDict[subject] = []
                self.subjectDict[subject].append( subjectEntry )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( f"    Discovered {len(self.subjectNameList)} Door43 subject fields" )
                print( f"    Discovered {len(self.subjectDict)} sets of Door43 subject entries ({self.totalEntryCount} total entries)" )
        #else: # old code -- many individual downloads
            ## Download the subject lists from Door43 (around 700 bytes in 2019-02)
            #subjectJsonList = self.getOnlineData( 'subjects' ) # Get a normalised, alphabetically ordered list of subject strings
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( "    subjectJsonList", len(subjectJsonList), subjectJsonList )
                #assert len(subjectJsonList) >= 12 # Otherwise we are losing stuff
                #assert isinstance( subjectJsonList, list )
            #if subjectJsonList:
                ## Extract the subject names
                #jsonFilenameList, self.subjectNameList = [], []
                #for subjectJsonURL in subjectJsonList:
                    #assert isinstance( subjectJsonURL, str ) # e.g., 'https://api.door43.org/v3/subjects/Translation_Words.json'
                    #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        #print( "      subjectJsonURL", subjectJsonURL )
                    #bits1 = subjectJsonURL.split('/')
                    #assert len(bits1) == 6 # e.g., ['https:', '', 'api.door43.org', 'v3', 'subjects', 'Hebrew_Old_Testament.json']
                    ## print( "      bits1", bits1 )
                    #jsonFilenameList.append( bits1[-1] )
                    #subjectName = bits1[-1].split('.')[0] # e.g., 'Translation_Academy'
                    #self.subjectNameList.append( subjectName.replace( '_', ' ' ) )
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    #print( "    subjectNameList", len(self.subjectNameList), self.subjectNameList )
                    #assert len(self.subjectNameList) == len(subjectJsonList) # Otherwise we are losing stuff
                #if BibleOrgSysGlobals.verbosityLevel > 1:
                    #print( f"    Downloaded {len(self.subjectNameList)} Door43 subject fields" )

                ## Now load the individual subject files
                #self.totalEntryCount = 0
                #self.subjectDict = {}
                #for subjectName, subjectJsonFilename in zip(self.subjectNameList, jsonFilenameList):
                    #self.subjectDict[subjectName] = self.getOnlineData( f'subjects/{subjectJsonFilename}' )
                    #if BibleOrgSysGlobals.verbosityLevel > 1:
                        #print( f"      Downloaded {len(self.subjectDict[subjectName])} Door43 '{subjectName}' subject entries" )
                    #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        #print( f"{subjectName}: {self.subjectDict[subjectName]}" )
                    #self.totalEntryCount += len( self.subjectDict[subjectName] )
                    ##print( f"\n\n\n{subjectName}" )
                    ##for something in self.subjectDict[subjectName]:
                        ##assert isinstance( something, dict )
                        ##if something['language'] == 'ru':
                            ##print( f'\n{something}' )
                #if BibleOrgSysGlobals.verbosityLevel > 0:
                    #print( f"    Downloaded {len(self.subjectDict)} sets of Door43 subject entries ({self.totalEntryCount} total entries)" )
    # end of Door43CatalogResources.fetchSubjects


    def fetchCatalog( self ):
        """
        Download the catalog lists from Door43.

        This can be quite slow (around 1.4 MB in 2019-02)

        Populates self.catalogDict (4 entries as of 2019-02):
                                    langnames, temp-langnames, approved-temp-langnames, new-language-questions
            and self.languageDict (55 entries as of 2019-02)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "Door43CatalogResources.fetchCatalog()…" )

        #self.fetchSubjects() # Seems to cover the same info just from a different perspective

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  Downloading catalog of available resources from Door43…" )

        catalog = self.getOnlineData( 'catalog.json' ) # Get an alphabetically ordered list of dictionaries -- one for each language
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "  catalog", len(catalog), catalog.keys() )
            assert 'catalogs' in catalog and 'languages' in catalog
            assert len(catalog) == 2 # Otherwise we are losing stuff
        if not catalog:
            return
        assert isinstance( catalog, dict )

        assert isinstance( catalog['catalogs'], list )
        self.catalogDict = {}
        for catalogEntry in catalog['catalogs']: # 4 entries: langnames, temp-langnames, approved-temp-langnames, new-language-questions
            assert isinstance( catalogEntry, dict )
            self.catalogDict[catalogEntry['identifier']] = catalogEntry
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "\n    catalogDict", len(self.catalogDict), self.catalogDict )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( f"    Downloaded {len(self.catalogDict)} Door43 catalogs" )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( f"      {list(self.catalogDict.keys())}" )

        assert isinstance( catalog['languages'], list )
        #self.totalEntryCount = 0
        self.languageDict = {}
        for languageEntry in catalog['languages']:
            assert isinstance( languageEntry, dict )
            self.languageDict[languageEntry['identifier']] = languageEntry
            #print( 'lE', languageEntry.keys() )
            #for resource in languageEntry['resources']:
                #self.totalEntryCount += 1
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "\n    languageDict", len(self.languageDict), self.languageDict['en'] )
        #for something in self.languageDict['ru']['resources']:
            #assert isinstance( something, dict )
            #print( f'\n{something}' )

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( f"    Downloaded {len(self.languageDict)} Door43 languages" )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( f"      {list(self.languageDict.keys())}" )

        self.resourceList, self.BibleList = [], [] # By Bible, we mean USFM resources (with BCV structuring)
        for lg, lgEntry in self.languageDict.items():
            for resourceEntry in lgEntry['resources']:
                assert isinstance( resourceEntry, dict )
                resourceTuple = lg, resourceEntry['title'], resourceEntry
                self.resourceList.append( resourceTuple )
                #if resourceEntry['subject'] in ('Bible', 'Aligned Bible', 'Translation Notes', ):
                    #self.BibleList.append( resourceTuple )
                if 'formats' in resourceEntry:
                    formats = resourceEntry['formats']
                else:
                    assert len(resourceEntry['projects']) == 1
                    formats = resourceEntry['projects'][0]['formats']
                for formatDict in formats:
                    assert isinstance( formatDict, dict )
                    formatString = formatDict['format']
                    if 'application/zip;' in formatString and 'usfm' in formatString:
                        self.BibleList.append( resourceTuple )
                        break
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( f"    Found {len(self.resourceList)} Door43 resources (of which {len(self.BibleList)} are USFM)" )
        #assert len(self.resourceList) == self.totalEntryCount
    # end of Door43CatalogResources.fetchCatalog


    def __str__( self ):
        """
        Create a string representation of the Bibles object.
        """
        indent = 2
        result = f"Door43 v{Door43_API_Version} online catalog object"
        if self.subjectNameList: result += ('\n' if result else '') + ' '*indent + _("Subjects: {}").format( len(self.subjectNameList) )
        if self.catalogDict: result += ('\n' if result else '') + ' '*indent + _("Catalogs: {}").format( len(self.catalogDict) )
        if self.languageDict: result += ('\n' if result else '') + ' '*indent + _("Languages: {}").format( len(self.languageDict) )
        if self.resourceList: result += ('\n' if result else '') + ' '*indent + _("Resources: {}").format( len(self.resourceList) )
        if self.BibleList: result += ('\n' if result else '') + ' '*indent + _("USFM resources: {}").format( len(self.BibleList) )
        return result
    # end of Door43CatalogResources.__str__


    def getResourceDict( self, resourceIndex ):
        """
        Given an index into self.resourceList,
            returns the resource dict
        """
        assert self.resourceList
        return self.resourceList[resourceIndex]
    # end of Door43CatalogResources.getResourceDict


    def getBibleResourceDict( self, resourceIndex ):
        """
        Given an index into self.BibleList,
            returns the resource dict
        """
        assert self.BibleList
        return self.BibleList[resourceIndex]
    # end of Door43CatalogResources.getBibleResourceDict


    def searchBibles( self, languageCode=None, BibleTitle=None ):
        """
        Search thru the list of available online Bibles to find
            a match of the optional language and optional title.

        Returns the dictionary for the resource
            (or a list of dictionaries if there's multiple matches)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"Door43CatalogResources.searchBibles( {languageCode!r}, {BibleTitle!r} )" )

        resultsList = []
        for entry in self.BibleList:
            #print( 'entry', type(entry), len(entry), repr(entry), '\n' )
            assert entry and isinstance( entry, tuple) and len(entry)==3
            lg, title, entryDict = entry
            if (languageCode is None or languageCode in lg) \
            and (BibleTitle is None or BibleTitle in title):
                assert isinstance( entryDict, dict )
                if 'language' not in entryDict:
                    entryDict['language'] = lg
                assert 'title' in entryDict and entryDict['title']==title
                resultsList.append( entryDict )
        if len(resultsList) == 1: return resultsList[0]
        return resultsList
    # end of Door43CatalogResources.searchBibles
# end of class Door43CatalogResources



class Door43CatalogBible( USFMBible ):
    """
    Class to download and manipulate an online Door43 Bible from the catalog.

    The interface provides a link to a zip file containing all of the USFM books.
    """
    def __init__( self, parameterOne, resourcesObject=None ):
        """
        Create the Door43 cataloged Bible object.

        parameterOne can be:
            a catalog dictionary entry (and second parameter must be None)
        or
            an index into the BibleList in the resourcesObject passed as the second parameter
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"Door43CatalogBible.__init__( {parameterOne}, {resourcesObject} )…" )

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

        if debuggingThisModule: print( 'formats', resourceDict['formats'] )
        if 'formats' in resourceDict:
            formats = resourceDict['formats']
        else:
            assert len(resourceDict['projects']) == 1
            formats = resourceDict['projects'][0]['formats']
        assert formats
        for formatDict in formats:
            #print( 'formatDict', formatDict )
            formatString = formatDict['format']
            if 'application/zip;' in formatString and 'usfm' in formatString:
                size, zipURL = formatDict['size'], formatDict['url']
                break
        else:
            logging.critical( f"No zip URL found for '{resourceDict['language']}' '{resourceDict['title']}'" )
            return

        # See if files already exist and are current (so don't download again)
        alreadyDownloadedFlag = False
        unzippedFolderPath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH.joinpath(
                                'Door43Catalog/', f"{resourceDict['language']}_{resourceDict['title']}/" )
        if os.path.isdir( unzippedFolderPath ):
            #print( f"Issued: {resourceDict['issued']}" )
            issuedDatetime = datetime.strptime( resourceDict['issued'], '%Y-%m-%dT%H:%M:%S+00:00' )
            #print( f"issuedDatetime: {issuedDatetime}" )
            #print( f"folder: {os.stat(unzippedFolderPath).st_mtime}" )
            folderModifiedDatetime = datetime.fromtimestamp(os.stat(unzippedFolderPath).st_mtime)
            #print( f"folderModifiedDatetime: {folderModifiedDatetime}" )
            alreadyDownloadedFlag = folderModifiedDatetime > issuedDatetime
            #print( f"alreadyDownloadedFlag: {alreadyDownloadedFlag}" )

        if alreadyDownloadedFlag:
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "Skipping download because folder '{}' already exists.".format( unzippedFolderPath ) )
        else: # Download the zip file (containing all the USFM files, LICENSE.md, manifest.yaml, etc.)
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "Downloading {:,} bytes from '{}'…".format( size, zipURL ) )
            try: HTTPResponseObject = urllib.request.urlopen( zipURL )
            except urllib.error.URLError as err:
                #errorClass, exceptionInstance, traceback = sys.exc_info()
                #print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
                logging.critical( "Door43 URLError '{}' from {}".format( err, zipURL ) )
                return None
            # print( "  HTTPResponseObject", HTTPResponseObject )
            contentType = HTTPResponseObject.info().get( 'content-type' )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "    contentType", contentType )
            if contentType == 'application/zip':
                try: os.makedirs( unzippedFolderPath )
                except FileExistsError: pass
                # Bug in Python up to 3.7 makes this not work for large aligned Bibles (3+ MB)
                # myTempFile = tempfile.SpooledTemporaryFile()
                myTempFile = tempfile.TemporaryFile()
                myTempFile.write( HTTPResponseObject.read() )
                with zipfile.ZipFile( myTempFile ) as myzip:
                    # NOTE: Could be a security risk here
                    myzip.extractall( unzippedFolderPath )
            else: halt # unknown content type

        # There's probably a folder inside this folder
        folders = os.listdir( unzippedFolderPath )
        #print( 'folders', folders )
        assert len(folders) == 1
        desiredFolderName = folders[0] + '/'
        #print( 'desiredFolderName', desiredFolderName )

        USFMBible.__init__( self, os.path.join( unzippedFolderPath, desiredFolderName ),
                                    givenName=resourceDict['title'], givenAbbreviation=resourceDict['identifier'] )
        self.objectNameString = 'Door43 USFM Bible object'
    # end of Door43CatalogBible.__init__
# end of class Door43CatalogBible



def demo() -> None:
    """
    Demonstrate how some of the above classes can be used.
    """
    from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey

    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion, end='\n\n' )

    # Test the Door43CatalogResources class
    door43CatalogResources = Door43CatalogResources()
    if BibleOrgSysGlobals.verbosityLevel > 0: print( door43CatalogResources )
    #Door43CatalogResources.load() # takes a minute
    #print( Door43CatalogResources )

    door43CatalogResources.fetchCatalog()
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print()
        print( door43CatalogResources )

    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( f"\nLanguage list ({len(door43CatalogResources.languageDict)}):" )
        for j, (lg,lgDict) in enumerate( door43CatalogResources.languageDict.items() ):
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( '  Lg', j+1, lg, lgDict['direction'], lgDict['title'] )
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
                elif door43CatalogResources.subjectNameList and something['subject'] not in door43CatalogResources.subjectNameList:
                    logging.critical( f"Unknown '{something['subject']}' subject field from {lgDict['identifier']} {something['title']}" )
            if 'category_labels' in lgDict:
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( '    category_labels', lgDict['category_labels'] )
            if 'versification_labels' in lgDict:
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( '    versification_labels', lgDict['versification_labels'] )

    if BibleOrgSysGlobals.verbosityLevel > 2: # Neatly list all available resources
        print( f"\n  Resource list ({len(door43CatalogResources.resourceList)}):" )
        for j, (lg, resourceTitle, resourceEntry) in enumerate( door43CatalogResources.resourceList ):
            print( f"    {j+1:3}/ {lg:5} '{resourceTitle}'   ({resourceEntry['subject']})" )
            if 'formats' in resourceEntry:
                formats = resourceEntry['formats']
            else:
                assert len(resourceEntry['projects']) == 1
                formats = resourceEntry['projects'][0]['formats']
            assert formats
            for formatEntry in formats:
                assert isinstance( formatEntry, dict )
                print( f"            '{formatEntry['format']}'  {formatEntry['url']}" )

    if BibleOrgSysGlobals.verbosityLevel > 1:
        # List all Bibles (i.e., all USFM format)
        print( f"\n  Bible list ({len(door43CatalogResources.BibleList)}):" )
        for j, (lg, resourceTitle, resourceEntry) in enumerate( door43CatalogResources.BibleList ):
            print( f"    {j+1:3}/ {lg:5} '{resourceTitle}'   ({resourceEntry['subject']})" )
            if 'formats' in resourceEntry:
                formats = resourceEntry['formats']
            else:
                assert len(resourceEntry['projects']) == 1
                formats = resourceEntry['projects'][0]['formats']
            assert formats
            for formatEntry in formats:
                assert isinstance( formatEntry, dict )
                print( f"            '{formatEntry['format']}'  {formatEntry['url']}" )

        # List all Open Bible Stories
        OBSList = []
        for lg, lgEntry in door43CatalogResources.languageDict.items():
            for resourceEntry in lgEntry['resources']:
                assert isinstance( resourceEntry, dict )
                resourceTuple = lg, resourceEntry['title'], resourceEntry
                if 'Bible Stories' in resourceEntry['subject']:
                    OBSList.append( resourceTuple )
        print( f"\n  Bible Stories list ({len(OBSList)}):" )
        for j, (lg, resourceTitle, resourceEntry) in enumerate( OBSList ):
            print( f"    {j+1:3}/ {lg:5} '{resourceTitle}'   ({resourceEntry['subject']})" )
            if 'formats' in resourceEntry:
                formats = resourceEntry['formats']
            else:
                assert len(resourceEntry['projects']) == 1
                formats = resourceEntry['projects'][0]['formats']
            assert formats
            for formatEntry in formats:
                assert isinstance( formatEntry, dict )
                print( f"            '{formatEntry['format']}'  {formatEntry['url']}" )


    testRefs = ( ('GEN','1','1'), ('PSA','150','6'), ('JER','33','3'), ('MAL','4','6'),
                 ('MAT','1','1'), ('JHN','3','16'), ('TIT','2','2'), ('JDE','1','14'), ('REV','22','21'), )

    if 1: # Test the Door43CatalogBible class by finding a Bible
        for lgCode, desiredTitle in (
                                        ('ru','Russian Synodal Bible'),
                                        ('ru','Russian Unlocked Literal Bible'),
                                        ('ru','Russian Open Bible'),
                                        ('ru','Russion Literal Bible'),
                                        ('en','unfoldingWord Literal Text'),
                                        ('en', 'unfoldingWord Simplified Text'),
                                        ('fr','unfoldingWord Literal Text'),
                                        ('el-x-koine','unfoldingWord Greek New Testament'),
                                    ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print()
            searchResultDict = door43CatalogResources.searchBibles( lgCode, desiredTitle )
            if searchResultDict:
                Door43CatalogBible1 = Door43CatalogBible( searchResultDict )
                if BibleOrgSysGlobals.verbosityLevel > 0: print( Door43CatalogBible1 )
                Door43CatalogBible1.preload()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( Door43CatalogBible1 )
                for testRef in testRefs:
                    verseKey = SimpleVerseKey( *testRef )
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        print( verseKey )
                        print( " ", Door43CatalogBible1.getVerseDataList( verseKey ) )
                if BibleOrgSysGlobals.verbosityLevel > 0: print( Door43CatalogBible1 )
            elif BibleOrgSysGlobals.verbosityLevel > 0:
                print( f"{lgCode} '{desiredTitle}' was not found!" )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of Door43OnlineCatalog.py
