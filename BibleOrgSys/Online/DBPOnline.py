#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# DBPOnline.py
#
# Module handling online DBP resources
#
# Copyright (C) 2013-2019 Robert Hunt
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
    from Faith Comes By Hearing (FCBH).

In this module, we use:
    DBP = Digital Bible Platform
    DAM = Digital Asset Management – the software system for users to administer the volumes contained in the DBP.
    DAM ID – the unique 10-character id by which an individual volume is identified.
        1-3: Language code, e.g., ENG
        4-6: Version code, e.g., ESV
        7: Collection
            "O" Old Testament – Contains one or more books of the Old Testament.
            "N" New Testament – Contains one or more books of the New Testament.
            "C" Complete – Contains books from both the Old and New Testament. (These volumes are used primarily for content downloads, and are not generally used by the actual reader applications).
            "S" Story – Contains content that is not organised by books and chapters.
            "P" Partial – Contains only partial content, such as a few chapters from one book of the Bible.
        8: Drama type
            "1" (Audio includes only spoken text)
            "2" (Audio includes spoken text, music, and sound effects)
        9-10: Media type
            ET – Electronic Text
            DA – Digital Audio
            DV – Digital Video
        Examples for the English KJV:
            ENGKJVC1DA – Complete (for download) non-drama audio
            ENGKJVC2DA – Complete (for download) drama audio
            ENGKJVO1DA – Old Testament non-drama audio
            ENGKJVO1ET – Old Testament non-drama text
            ENGKJVO2DA – Old Testament drama audio
            ENGKJVO2ET – Old Testament drama text
            ENGKJVN1DA – New Testament non-drama audio
            ENGKJVN1ET – New Testament non-drama text
            ENGKJVN2DA – New Testament drama audio
            ENGKJVN2ET – New Testament drama text

We currently use version 2 of the DBP (2.13.1 as at Dec 2019).

More details are available from https://www.digitalbibleplatform.com/docs.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-20' # by RJH
SHORT_PROGRAM_NAME = "DigitalBiblePlatform"
PROGRAM_NAME = "Digital Bible Platform online handler"
PROGRAM_VERSION = '0.22'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging
import urllib.request
import json
from pathlib import Path

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys.Online.GenericOnlineBible import GenericOnlineBible


URL_BASE = 'http://dbt.io/'
DBP_VERSION = '2' # 2.13.1 as at Dec 2019
KEY_FILENAME = 'DBPKey.txt'
KEY_SEARCH_FILEPATHS = ( BibleOrgSysGlobals.findHomeFolderPath(), Path( KEY_FILENAME ), BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( KEY_FILENAME ) )



def getSecurityKey():
    """
    See if we can find the personal key code either in the current folder
        or in other potential folders.

    Returns the contents of the file.
    """
    for keyPath in KEY_SEARCH_FILEPATHS:
        if keyPath.is_file():
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("getSecurityKey: found key file in {!r}").format( keyPath ) )
            with open( keyPath, 'rt' ) as keyFile:
                return keyFile.read() # Our personal key
    raise FileNotFoundError( _("Cannot find key file {!r}").format( KEY_FILENAME ) )
# end of getSecurityKey



@singleton # Can only ever have one instance
class DBPBibles:
    """
    Class to download and manipulate online DBP Bibles.

    """
    def __init__( self ):
        """
        Create the internal Bibles object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("DBPBibles.__init__()") )

        self.key = getSecurityKey() # Our personal key
        self.URLFixedData = "?v={}&key={}".format( DBP_VERSION, self.key )

        # See if the site is online by making a small call to get the API version
        self.URLTest = 'api/apiversion'
        self.onlineVersion = None
        result = self.getOnlineData( self.URLTest )
        if result and 'Version' in result: self.onlineVersion = result['Version']

        self.languageList = self.versionList = self.volumeList = self.volumeNameDict = self.EnglishVolumeNameDict = None
    # end of DBPBibles.__init__


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
            print( _("DBPBibles.getOnlineData( {!r} {!r} )").format( fieldREST, additionalParameters ) )

        requestString = '{}{}{}{}'.format( URL_BASE, fieldREST, self.URLFixedData, '&'+additionalParameters if additionalParameters else '' )
        #print( "Request string is", repr(requestString) )
        try: HTTPResponseObject = urllib.request.urlopen( requestString )
        except urllib.error.URLError as err:
            #errorClass, exceptionInstance, traceback = sys.exc_info()
            #print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
            logging.error( "DBP URLError '{}' from {}".format( err, requestString ) )
            return None
        #print( "HTTPResponseObject", HTTPResponseObject )
        contentType = HTTPResponseObject.info().get( 'content-type' )
        #print( f"    contentType='{contentType}'" )
        if contentType == 'application/json':
            responseJSON = HTTPResponseObject.read()
            #print( "responseJSON", len(responseJSON), responseJSON )
            responseJSONencoding = HTTPResponseObject.info().get_content_charset( 'utf-8' )
            #print( "responseJSONencoding", responseJSONencoding )
            responseSTR = responseJSON.decode( responseJSONencoding )
            #print( "responseSTR", len(responseSTR), repr(responseSTR) )
            return json.loads( responseSTR )
        else:
            print( 'contentType', contentType )
            halt # Haven't had this contentType before
    # end of DBPBibles.getOnlineData


    def getDAM( self, refNumber ):
        """
        DAM = Digital Asset Management – the software system for users to administer the volumes contained in the DBP.
        DAM ID – the unique 10-character id by which an individual volume is identified.

        Returns the DAM ID which is typically something like: ENGNLVN2ET
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"DBPBibles.getDAM( {refNumber} )" )

        gotDAM = self.volumeList[refNumber]['dam_id']
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"  got DAM='{gotDAM}'" )
        return gotDAM
    # end of DBPBibles.getDAM


    def fetchAllLanguages( self ):
        """
        Download the language lists from FCBH.

        This can be quite slow.

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
            print( "DBPBibles.fetchAllLanguages()" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("Downloading list of available languages from FCBH…") )

        if self.onlineVersion: # Get a list of available data sets
            self.languageList = self.getOnlineData( "library/language" ) # Get an alphabetically ordered list of dictionaries -- one for each language
            if BibleOrgSysGlobals.debugFlag: print( "  languageList", len(self.languageList) )#, self.languageList )
        return self.languageList
    # end of DBPBibles.fetchAllLanguages


    def fetchAllVersions( self ):
        """
        Download the version lists from FCBH.

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
            print( "DBPBibles.fetchAllVersions()" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("Downloading list of available versions from FCBH…") )

        if self.onlineVersion: # Get a list of available data sets
            self.versionList = self.getOnlineData( 'library/version' ) # Get an alphabetically ordered list of dictionaries -- one for each version
            if BibleOrgSysGlobals.debugFlag: print( "  versionList", len(self.versionList) )#, self.versionList )
        return self.versionList
    # end of DBPBibles.fetchAllVersions


    def fetchAllVolumes( self ):
        """
        Download the volume lists from FCBH.

        This can be quite slow.

        Populates self.volumeList (1637 entries as of 2014-10)

        Each list entry is a dictionary, e.g.
            {'language_iso_1': '', 'collection_name': 'New Testament', 'language_family_iso_2B': '',
                'created_on': '2011-00-00 00:00:00', 'sku': 'N1ZTQTBL', 'language_code': 'ZTQ', 'media_type': 'Non-Drama',
                'delivery': ['mobile', 'web', 'subsplash'], 'num_sample_audio': '0', 'language_family_iso_2T': '',
                'version_name': 'The Bible League', 'media': 'text', 'expiration': '0000-00-00',
                'language_family_english': 'Zapoteco de Quioquitani', 'version_english': 'The Bible League',
                'updated_on': '2014-09-12 22:28:08', 'language_family_name': 'Zapoteco de Quioquitani',
                'language_iso_2T': '', 'language_family_code': 'ZTQ', 'volume_name': '2000 Edition',
                'dbp_agreement': 'true', 'language_english': 'Zapoteco de Quioquitani', 'language_family_iso': 'ztq',
                'dam_id': 'ZTQTBLN1ET', 'font': {'platforms': {'android': True, 'ios': True, 'web': True}, 'id': '12',
                'files': {'zip': 'all.zip', 'ttf': 'font.ttf'}, 'name': 'Charis SIL',
                'base_url': 'http://cloud.faithcomesbyhearing.com/fonts/Charis_SIL'}, 'resolution': [],
                'audio_zip_path': 'ZTQTBLN1ET/ZTQTBLN1ET.zip', 'language_iso_2B': '', 'fcbh_id': 'ZTQTBLN1ET',
                'status': 'live', 'language_family_iso_1': '', 'language_iso_name': 'Quioquitani-Quierí Zapotec',
                'language_iso': 'ztq', 'language_name': 'Zapoteco de Quioquitani', 'right_to_left': 'false',
                'num_art': '0', 'version_code': 'TBL', 'collection_code': 'NT'}
            {'language_iso_1': '', 'collection_name': 'New Testament', 'language_family_iso_2B': '',
                'created_on': '2010-09-14 17:01:29', 'sku': 'N1ZTYTBL', 'language_code': 'ZTY', 'media_type': 'Non-Drama',
                'delivery': ['mobile', 'web', 'web_streaming', 'streaming_url', 'mp3_cd', 'digital_download', 'bible_stick', 'subsplash'],
                'num_sample_audio': '1', 'language_family_iso_2T': '', 'version_name': 'The Bible League', 'media': 'audio',
                'expiration': '0000-00-00', 'language_family_english': 'Zapoteco de Yatee',
                'version_english': 'The Bible League', 'updated_on': '2014-01-03 21:36:32',
                'language_family_name': 'Zapoteco de Yatee', 'language_iso_2T': '', 'language_family_code': 'ZTY',
                'volume_name': '2002 Edition', 'dbp_agreement': 'true', 'language_english': 'Zapoteco de Yatee',
                'language_family_iso': 'zty', 'dam_id': 'ZTYTBLN1DA', 'font': None, 'resolution': [],
                'audio_zip_path': 'ZTYTBLN1DA/ZTYTBLN1DA.zip', 'language_iso_2B': '', 'fcbh_id': 'ZTYTBLN1DA',
                'status': 'live', 'language_family_iso_1': '', 'language_iso_name': 'Yatee Zapotec', 'language_iso': 'zty',
                'language_name': 'Zapoteco de Yatee', 'right_to_left': 'false', 'num_art': '3', 'version_code': 'TBL',
                'collection_code': 'NT'}
            {'language_iso_1': '', 'collection_name': 'New Testament', 'language_family_iso_2B': '',
                'created_on': '2011-00-00 00:00:00', 'sku': 'N1ZTYTBL', 'language_code': 'ZTY', 'media_type': 'Non-Drama',
                'delivery': ['mobile', 'web', 'subsplash'], 'num_sample_audio': '0', 'language_family_iso_2T': '',
                'version_name': 'The Bible League', 'media': 'text', 'expiration': '0000-00-00',
                'language_family_english': 'Zapoteco de Yatee', 'version_english': 'The Bible League',
                'updated_on': '2014-09-12 22:28:08', 'language_family_name': 'Zapoteco de Yatee', 'language_iso_2T': '',
                'language_family_code': 'ZTY', 'volume_name': '2002 Edition', 'dbp_agreement': 'true',
                'language_english': 'Zapoteco de Yatee', 'language_family_iso': 'zty', 'dam_id': 'ZTYTBLN1ET',
                'font': {'platforms': {'android': True, 'ios': True, 'web': True}, 'id': '12',
                'files': {'zip': 'all.zip', 'ttf': 'font.ttf'}, 'name': 'Charis SIL',
                'base_url': 'http://cloud.faithcomesbyhearing.com/fonts/Charis_SIL'}, 'resolution': [],
                'audio_zip_path': 'ZTYTBLN1ET/ZTYTBLN1ET.zip', 'language_iso_2B': '', 'fcbh_id': 'ZTYTBLN1ET',
                'status': 'live', 'language_family_iso_1': '', 'language_iso_name': 'Yatee Zapotec', 'language_iso': 'zty',
                'language_name': 'Zapoteco de Yatee', 'right_to_left': 'false', 'num_art': '0', 'version_code': 'TBL',
                'collection_code': 'NT'}
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "DBPBibles.fetchAllVolumes()" )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Downloading list of available volumes from FCBH…") )

        if self.onlineVersion: # Get a list of available data sets
            self.volumeList = self.getOnlineData( 'library/volume' ) # Get an alphabetically ordered list of dictionaries -- one for each volume
            if BibleOrgSysGlobals.debugFlag: print( "  volumeList", len(self.volumeList) )#, self.volumeList )
        return self.volumeList
    # end of DBPBibles.fetchAllVolumes


    def fetchAllTextVolumes( self ):
        """
        Download the volume lists from FCBH if necessary. (This can be quite slow.)

        Populates self.volumeNameDict (847 entries as of 2014-10)

        Dictionary keys are version names, entries are a list of indexes to self.volumeList, e.g.
            'Popoloca San Juan Atzingo 1982 Edition' [1143]
            'Zokam 1994 Zokam International Version' [334]
            'ಕನ್ನಡ Easy-to-Read Version' [413]
            …
            'English 2001 English Standard' [393, 395]
            'English English Version for the Deaf' [396, 397]
            'English King James' [399, 401, 403, 405]
            'English 1995 Edition' [406, 407]
            'English 1986 New Life Version (Easy to Read)' [408]
            'English World English Bible' [410, 411]
            …
            'Español La Biblia de las Americas' [1302, 1303]
            'Mam, Northern 1993 Edition' [825, 826]
            'Русский 1876 Synodal Bible' [1246, 1247]
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "DBPBibles.fetchAllTextVolumes()" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("Creating list of available text volumes from FCBH…") )

        if self.volumeList is None:
            self.fetchAllVolumes()

        self.volumeNameDict = {}
        if self.volumeList: # Create a list of resource types
            for j, volume in enumerate(self.volumeList):
                assert volume['language_name'] and volume['volume_name']
                ourName= '{} {}'.format( volume['language_name'], volume['volume_name'] )
                assert volume['media'] and volume['delivery'] and volume['collection_code']
                if volume['media'] == 'text':
                    if 'web' in volume['delivery']:
                        #ourName= '{} {}'.format( volume['language_name'], volume['volume_name'] )
                        if ourName in self.volumeNameDict:
                            #print( "\nAlready have", ourName )
                            ##print( "New", j, volume )
                            #ix = self.volumeNameDict[ourName]
                            #oldVolume = self.volumeList[ix]
                            ##print( "Old", ix, oldVolume )
                            #assert len(volume) == len(oldVolume)
                            #for someKey in volume:
                                #if volume[someKey] != oldVolume[someKey]:
                                    #if someKey not in ('dam_id','fcbh_id','sku','updated_on','collection_name',):
                                        #print( "  ", someKey, volume[someKey], oldVolume[someKey] )
                            self.volumeNameDict[ourName].append( j )
                        else: self.volumeNameDict[ourName] = [j]
                    #else: print( j, repr(volume['language_name']), repr(volume['volume_name']) )
                    elif BibleOrgSysGlobals.verbosityLevel > 2: print( "No web delivery in", repr(ourName), "only", volume['delivery'] )
                elif volume['media'] not in ('audio','video'): print( "No text in", ourName, volume['media'] )
        if BibleOrgSysGlobals.debugFlag: print( "  volumeNameDict", len(self.volumeNameDict)) #, self.volumeNameDict )
        return self.volumeNameDict
    # end of DBPBibles.fetchAllTextVolumes


    def fetchAllEnglishTextVolumes( self ):
        """
        Download the volume lists from FCBH if necessary. (This can be quite slow.)

        Populates self.EnglishVolumeNameDict (847 entries as of 2014-10)

        Dictionary keys are version names, entries are a list of indexes to self.volumeList, e.g.
            'Popoloca San Juan Atzingo 1982 Edition' [1143]
            'Zokam 1994 Zokam International Version' [334]
            'ಕನ್ನಡ Easy-to-Read Version' [413]
            …
            'English 2001 English Standard' [393, 395]
            'English English Version for the Deaf' [396, 397]
            'English King James' [399, 401, 403, 405]
            'English 1995 Edition' [406, 407]
            'English 1986 New Life Version (Easy to Read)' [408]
            'English World English Bible' [410, 411]
            …
            'Español La Biblia de las Americas' [1302, 1303]
            'Mam, Northern 1993 Edition' [825, 826]
            'Русский 1876 Synodal Bible' [1246, 1247]
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "DBPBibles.fetchAllEnglishTextVolumes()" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("Creating list of available English text volumes from FCBH…") )

        if self.volumeList is None:
            self.fetchAllVolumes()

        self.EnglishVolumeNameDict = {}
        if self.volumeList: # Create a list of resource types
            for j, volume in enumerate(self.volumeList):
                assert volume['language_family_code']
                if volume['language_family_code'] == 'ENG':
                    assert volume['volume_name']
                    ourName= '{}: {}'.format( volume['version_code'], volume['volume_name'] )
                    #ourName = volume['volume_name']
                    assert volume['media'] and volume['delivery'] and volume['collection_code']
                    if volume['media'] == 'text':
                        if 'web' in volume['delivery']:
                            self.EnglishVolumeNameDict[ourName] = volume['dam_id'][:6] # Just remember the 6-character damRoot
                            #if ourName in self.EnglishVolumeNameDict: self.EnglishVolumeNameDict[ourName].append( j )
                            #else: self.EnglishVolumeNameDict[ourName] = [j]
                        elif BibleOrgSysGlobals.verbosityLevel > 2: print( "No web delivery in", repr(ourName), "only", volume['delivery'] )
                    elif volume['media'] not in ('audio','video'): print( "No text in", ourName, volume['media'] )
        if BibleOrgSysGlobals.debugFlag: print( "EnglishVolumeNameDict", len(self.EnglishVolumeNameDict))#, self.EnglishVolumeNameDict )
        return self.EnglishVolumeNameDict
    # end of DBPBibles.fetchAllEnglishTextVolumes


    def __str__( self ):
        """
        Create a string representation of the DBPBibles object.
        """
        indent = 2
        result = "DBP online Bibles object"
        if self.onlineVersion: result += ('\n' if result else '') + ' '*indent + _("Online version: {}").format( self.onlineVersion )
        if self.languageList: result += ('\n' if result else '') + ' '*indent + _("Languages: {}").format( len(self.languageList) )
        if self.versionList: result += ('\n' if result else '') + ' '*indent + _("Versions: {}").format( len(self.versionList) )
        if self.volumeList: result += ('\n' if result else '') + ' '*indent + _("Volumes: {}").format( len(self.volumeList) )
        if self.volumeNameDict: result += ('\n' if result else '') + ' '*indent + _("Displayable volumes: {}").format( len(self.volumeNameDict) )
        return result
    # end of DBPBibles.__str__


    def searchNames( self, searchText ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("DBPBibles.searchNames( {!r} )").format( searchText ) )

        searchTextUC = searchText.upper()
        resultsList = []
        for name in self.volumeNameDict:
            if searchTextUC in name.upper():
                for refNumber in self.volumeNameDict[name]:
                    DAM = self.getDAM(refNumber)
                    if BibleOrgSysGlobals.debugFlag:
                        print( _("DAM: {}").format( DAM ) )
                        if BibleOrgSysGlobals.debugFlag:
                            assert DAM.endswith('2ET') or DAM.endswith('1ET') # O2 (OT) or N2 (NT), plus ET for text
                    resultsList.append( (refNumber,DAM,) )
        return resultsList
    # end of DBPBibles.searchNames
# end of class DBPBibles



class DBPBible( GenericOnlineBible ):
    """
    Class to download and manipulate an online DBP Bible.

    Note that this Bible class is NOT based on the Bible class
        because it's so unlike most Bibles which are local.
    """
    def __init__( self, damRoot ):
        """
        Create the Digital Bible Platform Bible object.
            Accepts a 6-character code which is the initial part of the DAM:
                1-3: Language code, e.g., ENG
                4-6: Version code, e.g., ESV
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("DBPBible.__init__( {!r} )").format( damRoot ) )
            assert damRoot and isinstance( damRoot, str ) and len(damRoot)==6

         # Setup and initialise the base class first
        GenericOnlineBible.__init__( self )

        self.damRoot = damRoot
        self.key = getSecurityKey() # Our personal key
        self.URLFixedData = '?v={}&key={}'.format( DBP_VERSION, self.key )

        # See if the site is online by making a small call to get the API version
        self.URLTest = 'api/apiversion'
        self.onlineVersion = None
        result = self.getOnlineData( self.URLTest )
        if result:
            if 'Version' in result: self.onlineVersion = result['Version']
        else:
            logging.critical( "DBPBible.__init__: Digital Bible Platform appears to be offline" )
            raise ConnectionError # What should this really be?

        #self.bookList = None
        if self.onlineVersion: # Check that this particular resource is available by getting a list of books
            bookList = self.getOnlineData( "library/book", "dam_id="+self.damRoot ) # Get an ordered list of dictionaries -- one for each book
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "DBPBible.__init__: bookList", len(bookList))#, bookList )

            #if 0:# Get all book codes and English names
                #bookCodeDictList = self.getOnlineData( "library/bookname", "language_code=ENG" )
                ## Not sure why it comes back as a dictionary in a one-element list
                #assert isinstance( bookCodeDictList, list ) and len(bookCodeDictList)==1
                #bookCodeDict = bookCodeDictList[0]
                #assert isinstance( bookCodeDict, dict )
                #print( "bookCodeDict", len(bookCodeDict), bookCodeDict )

        #self.books = {}
        if bookList: # Convert to a form that's easier for us to use later
            for bookDict in bookList:
                OSISCode = bookDict['book_id']
                #print( "OSIS", OSISCode )
                BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( OSISCode )
                if isinstance( BBB, list ): BBB = BBB[0] # Take the first one if we get something like ['EZR','EZN']
                #print( "BBB", BBB )
                #print( bookDict )
                self.books[BBB] = bookDict
            del bookList
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
            print( _("DBPBible.getOnlineData( {!r} {!r} )").format( fieldREST, additionalParameters ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "Requesting data from {} for {}…".format( URL_BASE, self.damRoot ) )
        requestString = "{}{}{}{}".format( URL_BASE, fieldREST, self.URLFixedData, '&'+additionalParameters if additionalParameters else '' )
        #print( "Request string is", repr(requestString) )
        try: responseJSON = urllib.request.urlopen( requestString )
        except urllib.error.URLError:
            if BibleOrgSysGlobals.debugFlag: logging.critical( "DBPBible.getOnlineData: error fetching {!r} {!r}".format( fieldREST, additionalParameters ) )
            return None
        responseSTR = responseJSON.read().decode('utf-8')
        return json.loads( responseSTR )
    # end of DBPBible.getOnlineData


    def getVerseDataList( self, key ):
        """
        Equivalent to the one in InternalBible, except we may have to fetch the data.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("DBPBible.getVerseDataList( {!r} ) for {!r}").format( key, self.damRoot ) )

        cachedResult = GenericOnlineBible.getCachedVerseDataList( self, key )
        if isinstance( cachedResult, list): return cachedResult

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
                GenericOnlineBible.cacheVerse( self, key, resultList )
            return resultList
        else: # This version doesn't have this book
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  getVerseDataList: {} not in {} {}".format( BBB, self.damRoot, self.books.keys() ) )
    # end of DBPBible.getVerseDataList


    #def getContextVerseData( self, key ):
        #"""
        #Given a BCV key, get the verse data.

        #(The Digital Bible Platform doesn't provide the context so an empty list is always returned.)
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( _("DBPBible.getContextVerseData( {!r} ) for {!r}").format( key, self.damRoot ) )

        #return self.getVerseDataList( key ), [] # No context
    ## end of DBPBible.getContextVerseData
# end of class DBPBible



def demo() -> None:
    """
    Demonstrate how some of the above classes can be used.
    """
    from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey

    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    if 1: # Test the DBPBibles class
        print()
        dbpBibles = DBPBibles()
        print( dbpBibles )
        #dbpBibles.load() # takes a minute
        #print( dbpBibles )

        if 0:
            dbpBibles.fetchAllLanguages()
            print( "\nLanguage list ({}):".format( len(dbpBibles.languageList) ) )
            for j, lgDict in enumerate( dbpBibles.languageList ):
                print( 'Lg', j, repr(lgDict) )

        if 0:
            dbpBibles.fetchAllVersions()
            print( "\nVersion list ({}):".format( len(dbpBibles.versionList) ) )
            for j, verDict in enumerate( dbpBibles.versionList ):
                print( 'Ver', j, repr(verDict) )

        if 0:
            dbpBibles.fetchAllVolumes()
            print( "\nVolume list ({}):".format( len(dbpBibles.volumeList) ) )
            for j, volDict in enumerate( dbpBibles.volumeList ):
                print( ' ', j, repr(volDict) )
            print( "393", dbpBibles.volumeList[393] )
            print( "394", dbpBibles.volumeList[394] )
            print( "395", dbpBibles.volumeList[395] )

        if 0:
            dbpBibles.fetchAllTextVolumes()
            print( "\nVolume name dict ({}):".format( len(dbpBibles.volumeNameDict) ) )
            for j, someName in enumerate( dbpBibles.volumeNameDict ):
                #if 'English' in someName:
                    #print( "English:", repr(someName), repr(dbpBibles.volumeNameDict[someName]) )
                print( j, repr(someName), repr(dbpBibles.volumeNameDict[someName]) )
                #if 'English' in someName:
                    #print( "  English:", repr(someName), repr(dbpBibles.volumeNameDict[someName]) )
            print( "English search", dbpBibles.searchNames( "English" ) )
            print( "MS search", dbpBibles.searchNames( "Salug" ) )

        if 1:
            dbpBibles.fetchAllEnglishTextVolumes()
            print( "\nEnglish volume name dict ({}):".format( len(dbpBibles.EnglishVolumeNameDict) ) )
            for j, someName in enumerate( dbpBibles.EnglishVolumeNameDict ):
                #if 'English' in someName:
                    #print( "English:", repr(someName), repr(dbpBibles.EnglishVolumeNameDict[someName]) )
                print( "  {}/ {!r} {!r}".format( j, someName, dbpBibles.EnglishVolumeNameDict[someName] ) )
                #if 'English' in someName:
                    #print( "  English:", repr(someName), repr(dbpBibles.EnglishVolumeNameDict[someName]) )


    testRefs = ( ('GEN','1','1'), ('JER','33','3'), ('MAL','4','6'), ('MAT','1','1'), ('JHN','3','16'), ('JDE','1','14'), ('REV','22','21'), )

    if 1: # Test the DBPBible class with the ESV
        print()
        dbpBible1 = DBPBible( 'ENGESV' )
        print( dbpBible1 )
        for testRef in testRefs:
            verseKey = SimpleVerseKey( *testRef )
            print( verseKey )
            print( " ", dbpBible1.getVerseDataList( verseKey ) )
         # Now test the DBPBible class caching
        for testRef in testRefs:
            verseKey = SimpleVerseKey( *testRef )
            print( verseKey, "cached" )
            print( " ", dbpBible1.getVerseDataList( verseKey ) )


    if 1: # Test the DBPBible class with the MS
        print()
        dbpBible2 = DBPBible( 'MBTWBT' )
        print( dbpBible2 )
        for testRef in testRefs:
            verseKey = SimpleVerseKey( *testRef )
            print( verseKey )
            print( " ", dbpBible2.getVerseDataList( verseKey ) )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of DBPOnline.py
