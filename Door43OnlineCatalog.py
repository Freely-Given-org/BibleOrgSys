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

LastModifiedDate = '2019-02-16' # by RJH
ShortProgName = "Door43OnlineCatalog"
ProgName = "Door43 Online Catalog online handler"
ProgVersion = '0.04'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


from singleton import singleton
import os, logging
import urllib.request, json
import tempfile, zipfile

import BibleOrgSysGlobals
from USFMBible import USFMBible
from VerseReferences import SimpleVerseKey


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
            print( "Door43CatalogResources.__init__()" )

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
            print( f"Door43CatalogResources.getOnlineData( {fieldREST!r}, {additionalParameters!r} )…" )

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
        else: # old code -- many individual downloads
            # Download the subject lists from Door43 (around 700 bytes in 2019-02)
            subjectJsonList = self.getOnlineData( 'subjects' ) # Get a normalised, alphabetically ordered list of subject strings
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "    subjectJsonList", len(subjectJsonList), subjectJsonList )
                assert len(subjectJsonList) >= 12 # Otherwise we are losing stuff
                assert isinstance( subjectJsonList, list )
            if subjectJsonList:
                # Extract the subject names
                jsonFilenameList, self.subjectNameList = [], []
                for subjectJsonURL in subjectJsonList:
                    assert isinstance( subjectJsonURL, str ) # e.g., 'https://api.door43.org/v3/subjects/Translation_Words.json'
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "      subjectJsonURL", subjectJsonURL )
                    bits1 = subjectJsonURL.split('/')
                    assert len(bits1) == 6 # e.g., ['https:', '', 'api.door43.org', 'v3', 'subjects', 'Hebrew_Old_Testament.json']
                    # print( "      bits1", bits1 )
                    jsonFilenameList.append( bits1[-1] )
                    subjectName = bits1[-1].split('.')[0] # e.g., 'Translation_Academy'
                    self.subjectNameList.append( subjectName.replace( '_', ' ' ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "    subjectNameList", len(self.subjectNameList), self.subjectNameList )
                    assert len(self.subjectNameList) == len(subjectJsonList) # Otherwise we are losing stuff
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( f"    Downloaded {len(self.subjectNameList)} Door43 subject fields" )

                # Now load the individual subject files
                self.totalEntryCount = 0
                self.subjectDict = {}
                for subjectName, subjectJsonFilename in zip(self.subjectNameList, jsonFilenameList):
                    self.subjectDict[subjectName] = self.getOnlineData( f'subjects/{subjectJsonFilename}' )
                    if BibleOrgSysGlobals.verbosityLevel > 1:
                        print( f"      Downloaded {len(self.subjectDict[subjectName])} Door43 '{subjectName}' subject entries" )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( f"{subjectName}: {self.subjectDict[subjectName]}" )
                    self.totalEntryCount += len( self.subjectDict[subjectName] )
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    print( f"    Downloaded {len(self.subjectDict)} sets of Door43 subject entries ({self.totalEntryCount} total entries)" )
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

        #self.fetchSubjects() # Seems to cover the same info

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
            print( f"    Found {len(self.resourceList)} Door43 resources (of which {len(self.BibleList)} are BCV structured)" )
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
        if self.BibleList: result += ('\n' if result else '') + ' '*indent + _("BCV resources: {}").format( len(self.BibleList) )
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


    def searchBibles( self, languageCode, BibleTitle ):
        """
        Search thru the list of available online Bibles to find
            a match of the language and title.

        Returns the dictionary for the resource
            (or a list of dictionaries if there's multiple matches
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"Door43CatalogResources.searchBibles( {languageCode!r}, {BibleTitle!r} )" )

        resultsList = []
        for entry in self.BibleList:
            #print( 'entry', type(entry), len(entry), repr(entry), '\n' )
            assert entry and isinstance( entry, tuple) and len(entry)==3
            lg, title, entryDict = entry
            if lg==languageCode and title==BibleTitle:
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
    Class to download and manipulate an online Door43 Bible.
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

        #print( 'formats', resourceDict['formats'] )
        for formatDict in resourceDict['formats']:
            #print( 'formatDict', formatDict )
            formatString = formatDict['format']
            if 'application/zip;' in formatString and 'usfm' in formatString:
                size, zipURL = formatDict['size'], formatDict['url']
                break
        else:
            logging.critical( f"No zip URL found for '{resourceDict['language']}' '{resourceDict['title']}'" )
            return

        # TODO: See if files already exist and are current (so don't download again)
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "Downloading {:,} bytes from '{}'…".format( size, zipURL ) )
        try: HTTPResponseObject = urllib.request.urlopen( zipURL )
        except urllib.error.URLError as err:
            #errorClass, exceptionInstance, traceback = sys.exc_info()
            #print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
            logging.error( "Door43 URLError '{}' from {}".format( err, requestString ) )
            return None
        # print( "  HTTPResponseObject", HTTPResponseObject )
        contentType = HTTPResponseObject.info().get( 'content-type' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "    contentType", contentType )
        unzippedFolder = None
        if contentType == 'application/zip':
            myTempFile = tempfile.SpooledTemporaryFile()
            myTempFile.write( HTTPResponseObject.read() )
            unzippedFolder = os.path.join( BibleOrgSysGlobals.DOWNLOADED_RESOURCES_FOLDER,
                                    'Door43Catalog/', f"{resourceDict['language']}_{resourceDict['title']}" )
            try: os.makedirs( unzippedFolder )
            except FileExistsError: pass
            with zipfile.ZipFile( myTempFile ) as myzip:
                # NOTE: Could be a security risk here
                myzip.extractall( unzippedFolder )

        # There's probably a folder inside this folder
        folders = os.listdir( unzippedFolder )
        #print( 'folders', folders )
        assert len(folders) == 1
        desiredFolder = folders[0]
        #print( 'desiredFolder', desiredFolder )

        USFMBible.__init__( self, os.path.join( unzippedFolder, desiredFolder ),
                                    givenName=resourceDict['title'], givenAbbreviation=resourceDict['identifier'] )
        self.objectNameString = 'Door43 USFM Bible object'
    # end of Door43CatalogBible.__init__
# end of class Door43CatalogBible



def demo():
    """
    Demonstrate how some of the above classes can be used.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    # Test the Door43CatalogResources class
    door43Resources = Door43CatalogResources()
    if BibleOrgSysGlobals.verbosityLevel > 0: print( door43Resources )
    #Door43CatalogResources.load() # takes a minute
    #print( Door43CatalogResources )

    door43Resources.fetchCatalog()
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print()
        print( door43Resources )

    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( f"\nLanguage list ({len(door43Resources.languageDict)}):" )
        for j, (lg,lgDict) in enumerate( door43Resources.languageDict.items() ):
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
                elif door43Resources.subjectNameList and something['subject'] not in door43Resources.subjectNameList:
                    logging.critical( f"Unknown '{something['subject']}' subject field from {lgDict['identifier']} {something['title']}" )
            if 'category_labels' in lgDict:
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( '    category_labels', lgDict['category_labels'] )
            if 'versification_labels' in lgDict:
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( '    versification_labels', lgDict['versification_labels'] )

    if BibleOrgSysGlobals.verbosityLevel > 2:
        # Neatly list all available resources
        print( f"\n  Resource list ({len(door43Resources.resourceList)}):" )
        for j, (lg, resourceTitle, resourceEntry) in enumerate( door43Resources.resourceList ):
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
        print( f"\n  Bible list ({len(door43Resources.BibleList)}):" )
        for j, (lg, resourceTitle, resourceEntry) in enumerate( door43Resources.BibleList ):
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
        lgCode = 'en'
        for desiredTitle in ('unfoldingWord Literal Text', 'unfoldingWord Simplified Text'):
            if BibleOrgSysGlobals.verbosityLevel > 0: print()
            USTDict = door43Resources.searchBibles( lgCode, desiredTitle )
            if USTDict:
                Door43CatalogBible1 = Door43CatalogBible( USTDict )
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


    if 1: # Test the Door43CatalogBible class again
        if BibleOrgSysGlobals.verbosityLevel > 0: print()
        lgCode = 'fr'
        desiredTitle = 'unfoldingWord Literal Text'
        USTDict = door43Resources.searchBibles( lgCode, desiredTitle )
        if USTDict:
            Door43CatalogBible1 = Door43CatalogBible( USTDict )
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
    #from multiprocessing import freeze_support
    #freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of Door43OnlineCatalog.py
