#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# PierceOnlineBible.py
#
# Module handling Larry Pierce's "Online Bible" files
#
# Copyright (C) 2015-2022 Robert Hunt
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
Module reading and loading Larry Pierce's Online Bible undocumented binary files.
    NOTE: This is NOT an "online" Bible (but preceded widespread internet)

Files are usually:
    Copyrite.Dat (a text file),
    Text.Dat, TextNdx.Dat, TextOpt.Dat, Tokens.Dat, Version.Dat
    Version.Ext (a text file),
    Xref.Dat, xRefNdx.Dat
"""
from pathlib import Path
import logging
import os
import struct
from binascii import hexlify
import multiprocessing

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem


LAST_MODIFIED_DATE = '2022-07-12' # by RJH
SHORT_PROGRAM_NAME = "PierceOnlineBible"
PROGRAM_NAME = "Pierce Online Bible format handler"
PROGRAM_VERSION = '0.22'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


compulsoryFiles = ( 'VERSION.DAT', 'TEXT.DAT', 'TEXTNDX.DAT', ) # Must be UPPERCASE



def PierceOnlineBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for Online Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one Online Bible is found,
        returns the loaded PierceOnlineBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"PierceOnlineBibleFileCheck( {givenFolderName}, {strictCheck}, {autoLoad}, {autoLoadBooks} )" )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, (str,Path) )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( f"PierceOnlineBibleFileCheck: Given {givenFolderName!r} folder is unreadable" )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( f"PierceOnlineBibleFileCheck: Given {givenFolderName!r} path is not a folder" )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f" PierceOnlineBibleFileCheck: Looking for files in given {givenFolderName}" )
    foundFolders, foundFiles = [], []
    numFound = foundFileCount = 0
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            if somethingUpper in compulsoryFiles: foundFileCount += 1
    if foundFileCount >= len(compulsoryFiles):
        numFound = 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "PierceOnlineBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = PierceOnlineBible( givenFolderName )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( f"PierceOnlineBibleFileCheck: {tryFolderName!r} subfolder is unreadable" )
            continue
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    PierceOnlineBibleFileCheck: Looking for files in {tryFolderName}" )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ): foundSubfolders.append( something )
                elif os.path.isfile( somepath ):
                    somethingUpper = something.upper()
                    if somethingUpper in compulsoryFiles: foundFileCount += 1
            if foundFileCount >= len(compulsoryFiles):
                foundProjects.append( tryFolderName )
                numFound += 1
        except PermissionError: pass # can't read folder, e.g., system folder
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "PierceOnlineBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            oB = PierceOnlineBible( foundProjects[0] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
# end of PierceOnlineBibleFileCheck


BOS = None


class PierceOnlineBible( Bible ):
    """
    Class for reading, validating, and converting PierceOnlineBible files.

    KJV OT has 23,145 verses = 5A69
        NT has  7,957 verses = 1F15
        Total  31,102 verses = 797E
    """
    def __init__( self, sourceFolder, encoding=None ) -> None:
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Online Bible object'
        self.objectTypeString = 'OLB'

        # Now we can set our object variables
        self.sourceFolder, self.encoding = sourceFolder, encoding
        #self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'_utf8.txt' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFolder, os.R_OK ):
            logging.critical( f"PierceOnlineBible: Folder {self.sourceFolder!r} is unreadable" )

        global BOS
        if BOS is None: BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )
        #self.name = self.givenName
        #if self.name is None:
            #pass
    # end of PierceOnlineBible.__init__


    def load( self ):
        """
        Load the compressed data file and import book elements.
        """
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nLoading from {self.sourceFolder}…" )


        def loadPierceOnlineBibleMetadata():
            """
            Version.Ext contains lines of text.
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading metadata from {self.sourceFolder}…" )

            if self.suppliedMetadata is None: self.suppliedMetadata = {}
            self.suppliedMetadata['Online'] = {}

            lines = []
            lineCount = 0
            filepath = os.path.join( self.sourceFolder, 'Version.Ext' )
            if self.encoding: encodings = [self.encoding]
            else: encodings = ['utf-8', 'ISO-8859-1', 'ISO-8859-15']
            for encoding in encodings: # Start by trying the given encoding
                try:
                    with open( filepath, 'rt', encoding=encoding ) as myFile: # Automatically closes the file when done
                        for line in myFile:
                            lineCount += 1
                            if lineCount==1 and encoding.lower()=='utf-8' and line[0]==BibleOrgSysGlobals.BOM:
                                logging.info( f"loadPierceOnlineBibleMetadata: Detected Unicode Byte Order Marker (BOM) in {filepath}" )
                                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                            #if not line: continue # Just discard blank lines
                            lines.append( line )
                            lastLine = line
                except UnicodeDecodeError:
                    logging.error( f"loadPierceOnlineBibleMetadata fails with encoding: {encoding}{' -- trying again' if encoding!=encodings[-1] else ''}" )

            if self.encoding is None and lines:
                self.encoding = encoding

            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(lines)} metadata lines read" ) # 16 expected

            self.suppliedMetadata['Online']['Abbreviation'] = lines[0]
            self.suppliedMetadata['Online']['VersificationScheme'] = lines[1]
            self.suppliedMetadata['Online']['LongName'] = lines[2]
            self.suppliedMetadata['Online']['Copyright'] = lines[3]
            #self.name = self.longName

            self.applySuppliedMetadata( 'Online' ) # Copy some to self.settingsDict
        # end of load.loadPierceOnlineBibleMetadata


        #def getBinaryString( binary, numBytes ):
            #"""
            #Gets bytes out of the binary and converts them to characters.
            #Stops when numBytes is reached, or a NULL is encountered.

            #Returns the string.
            #"""
            ##if BibleOrgSysGlobals.debugFlag:
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, t("getBinaryString( {}, {} )").format( binary, numBytes ) )
            #if len(binary) < numBytes: assert False, "We want to stop here" # Too few bytes provided
            #result = ''
            #for j, value in enumerate( binary ):
                #if j>=numBytes or value==0: break
                #result += chr( value )
            #return result
        ## end of getBinaryString


        #def getFileString( thisFile, numBytes ):
            #"""
            #Used for reading the PalmDB header information from the file.
            #"""
            #if BibleOrgSysGlobals.debugFlag:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, t("getFileString( {}, {} )").format( thisFile, numBytes ) )
            #return getBinaryString( thisFile.read( numBytes ), numBytes )
        ## end of getFileString


        chars = ( (129,252), (130,233), (131,226), (133,224), (135,231), (136,234), (137,235), (138,232),
                    (139,239), (140,238), (144,201), (147,244), (150,251), (151,249), (160,225), (161,237),
                    (162,243), (163,250), (164,241), (168,191), (173,161), )
        def convertChar( intChar ):
            """
            """
            for oldChar,newChar in chars:
                if oldChar == intChar: return chr(newChar)
            return chr(intChar)
        # end of convertChar


        VBH1s,VBH2s, VBH3s = {}, {}, {}
        def loadVersion():
            """
            Seems to contain two sets of the most common words, one in 8-bit characters and one in 16-bit.
            Maximum character length is 9 characters.

            Starts with punctuation:
                  !   ,   -   .   .\\*\\   .\\}   .}   /   :   :]   ;   ?   \\   \\)   \\*\\  +  +  +-  -(\\  -\\  -{[  -{\\ # #1
            Then common words (all have first letter capitalized)
                  A About All Am And Are As At Be Because But By Can Cevuk Come David Day Did Do Don Even Everyone
                  For From Go God Had Has Have He Hebrew Him His I If Ii In Is Israel It Jerusalem Jesus King
                  Let Like Lord Made Make Me Must My No Not Now Of On One Or Other Our Out People
                  S Said See So Some Son T That The Their Them Then There These They This To Told Up Us
                  Was We Went Were What When Who Will With Would You Your
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading main version data from {self.sourceFolder}…" )
            filename = 'Version.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading version from {self.sourceFolder} {filename}…" )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                versionBytes = myFile.read()
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(versionBytes):,} version bytes read" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"vB {len(versionBytes)} {versionBytes}" )

            key, size = versionBytes[0], versionBytes[1]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  prelude length = {size:04x} {size}" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Key={key}, line entry size={size}" )
            assert key == 8

            index, length = 1, 12
            vHeader1 = versionBytes[index:index+length]; index += length
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {self.abbreviation} vBH1 {len(vHeader1)} {hexlify(vHeader1)}" )
                VBH1s[self.abbreviation] = hexlify(vHeader1)
            unknown1, = struct.unpack( "<H", vHeader1[3:5] )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      unknown1 is {unknown1:04x}={unknown1:,}" )
                #assert ntOffset == 23146
            unknown2, = struct.unpack( "<H", vHeader1[5:7] )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      unknown2 is {unknown2:04x}={unknown2:,}" )
                #assert ntOffset == 23146
            ntOffset, = struct.unpack( "<H", vHeader1[7:9] )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      NT offset is {ntOffset:04x}={ntOffset:,}" )
                assert ntOffset == 23146
            unknownFlag1 = vHeader1[-1]
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Unknown flag1 is {unknownFlag1}" )
                assert unknownFlag1 in (0,1)

            length = 10 # 1 length byte and 9 max characters
            strings1 = []
            self.characterBitSize = 8
            while index < len(versionBytes):
                vBytes = versionBytes[index:index+length]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  vB {hexlify(vBytes)} {vBytes}" )
                if vBytes[-2] == 0 and vBytes[-1] > 0x7F: break
                vLen = vBytes[0]
                if vLen > 0 and vBytes[1]:
                    vString = vBytes[1:vLen+1].decode()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'Vstring', vString )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    vBl1 {vLen} {vString!r}", end='' )
                    # assert not vString[0].islower()
                    strings1.append( vString )
                index += length
            numStrings1 = len( strings1 )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {numStrings1}={numStrings1:04x} 8-bit capitalized common words loaded" )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '     ', strings1 )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  index = {index:04x}={index}" )
            assert 118 <= numStrings1 <= 123

            assert index == 0x4db
            length = 137
            vHeader2 = versionBytes[index:index+length]; index += length
            assert vHeader2[0] == 5
            for ix in range( 1, 8+1 ): assert vHeader2[ix] == 0
            vHeader2 = vHeader2[9:]
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {self.abbreviation} vBH2 {len(vHeader2)} {hexlify(vHeader2)}" )
                VBH2s[self.abbreviation] = hexlify(vHeader2)

            assert index == 0x564
            length = 44
            vHeader3 = versionBytes[index:index+length]; index += length
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    vBH3 {len(vHeader3)} {hexlify(vHeader3)}" )
            assert vHeader3[0] == 8
            vHeaderDate = vHeader3[1:8+1]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      vHeaderDate {len(vHeaderDate)} {vHeaderDate}" )
            year, month, date = int(vHeaderDate[:4]), int(vHeaderDate[4:6]), int(vHeaderDate[6:])
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    vHeaderDate {year}-{month:02}-{date:02}" )
            vHeader3 = vHeader3[9:]
            for ix in range( 11+1 ): assert vHeader3[ix] == 0
            vHeader3 = vHeader3[12:]
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {self.abbreviation} vBH3 {len(vHeader3)} {hexlify(vHeader3)}" )
                VBH3s[self.abbreviation] = hexlify(vHeader3)
            self.StrongsOffset, = struct.unpack( "<H", vHeader3[0:2] )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Strongs' offset is {self.StrongsOffset:04x}={self.StrongsOffset:,}" )
                assert self.StrongsOffset in ( 0xffff, 0x5d5c )
            self.haveStrongsFlag = vHeader3[4] != 0
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Have Strongs flag is {self.haveStrongsFlag}" )
                assert self.haveStrongsFlag in (0,1)
            numBooks, = struct.unpack( "<H", vHeader3[5:7] )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      numBooks is {numBooks:04x}={numBooks:,}" )
                assert numBooks == 66
            numChapters, = struct.unpack( "<H", vHeader3[9:11] )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      numChapters is {numChapters:04x}={numChapters:,}" )
                assert numChapters == 1189
            numVerses, = struct.unpack( "<H", vHeader3[17:19] )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      numVerses is {numVerses:04x}={numVerses:,}" )
                assert numVerses == 31102
            unknownFlag2 = vHeader3[-2]
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Unknown flag2 is {unknownFlag2:1x}" )
                assert unknownFlag2 in (1,15)

            #vHeader3 = versionBytes[0x4db:0x564]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    vBH3 {len(vHeader3)} {hexlify(vHeader3)}" )
            #assert versionBytes[0x564] == 8
            #vHeaderDate = versionBytes[0x565:0x56d]
            ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      vHeaderDate {len(vHeaderDate)} {vHeaderDate}" )
            #year, month, date = int(vHeaderDate[:4]), int(vHeaderDate[4:6]), int(vHeaderDate[6:])
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    vHeaderDate {year}-{month:02}-{date:02}" )
            #vHeader4 = versionBytes[0x56d:index]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    vBH4 {len(vHeader3)} {hexlify(vHeader4)}" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  index = {index:04x}={index}" )

            assert index == 0x590
            length = 19 # 1 length byte and 9 max characters
            strings2 = []
            while index < len(versionBytes):
                vBytes = versionBytes[index:index+length]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  vB {hexlify(vBytes)} {vBytes}" )
                vLen, = struct.unpack( ">H", vBytes[0:2] )
                vLen = vBytes[0]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "vL2", repr(vLen) )
                vString = ''
                for j in range( int(vLen/2) ):
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, vBytes[2*j+1:2*j+3] )
                    char16, = struct.unpack( "<H", vBytes[2*j+1:2*j+3] )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, char16 )
                    vString += chr( char16 )
                #vString = vBytes[2:vLen+1].decode( 'utf-16' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    vBl2 {vLen}/{int(vLen/2)} {vString!r}", end='' )
                # assert not vString[0].islower()
                strings2.append( vString )
                index += length
            numStrings2 = len( strings2 )
            if numStrings2 > 0: self.characterBitSize = 16
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {numStrings2}={numStrings2:04x} 16-bit capitalized common words loaded" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '     ', strings2 )
            if DEBUGGING_THIS_MODULE:
                ix = -1
                for j, word in enumerate( strings2 ):
                    if word in ( 'Genesis', 'In', 'The', 'God', ):
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'      {word!r} {j}={j:04x}' )

            self.commonWords = strings2 if strings2 else strings1
        # end of load.loadVersion


        def loadTokenCharacters():
            """
            Seem to be sequences of 8-bit or 16-bit characters (sometimes whole words, sometimes not) with no delimitation
            e.g.,
                  !:]\\*\\†\\’”\\†\\”:]\\*\\†\\}),.}”}:];\\}”,\\*\\†\\](’”\\*\\-.)  .)\\†\\\\*\\\)}†\\](}’\\*\\”\\†\\}”)\\†\\:]?\\*\\\\)†\\}/:\\*\\\\†\\†\\];?:]\\*\\  ?\\†\\’”}”\\*\\†\\}\@,.\\*\\”\\*\\\),.};}*\\,,.};†\\}—’,.  ’.”}:]?\\†\\”\\*\\”;”),.}:];?\\*\\\\*\\†\\…](”}+!!\\*\\†\\—\\†\\(-?…\@: +\@;\\*\\\*\\†\\’…-(\\“\@\{(\\[‘“\@\(—‘“(‘…#000172334#052667100234567891012567820\\)ab302567#13940134650137672869\\)ab200122347546#2738930071225374\\b5860789\\(lxx40051253#43\\)ab450865785695001223094506602786#594586001359123034025069758179700#7034510567201263056840235608139800#81282346708699091130456789\\(lxx
                  100101021223608389428th5036th6078892001820332455676893002034834556072892840581410253055048658569500158206306894952460562701385678991236786005912137842852566367975678170111520125733468423560758080032458599314557038a
                  Aaronbaddongthanaabandoned
                    hiahedahrahshthioruahbbabeliahthamnrusiabaeoniahZichriddimhaklagllahethaipahmmahraninaonrphahionronporahvzaoanrbahebahhareleththphahi
                    Zopharimrahthitetesitesuarphri
                    elshaddaizites
            Counters for these sequences are in XrefNdx.Dat.
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading dictionary characters from {self.sourceFolder}…" )
            filename = 'Tokens.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading token characters from {self.sourceFolder} {filename}…" )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                tokenBytes = myFile.read()
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(tokenBytes):,} token bytes read" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"vB {len(tokenBytes)} {hexlify(tokenBytes[:40])}" )
            assert tokenBytes[0] == 32
            assert tokenBytes[1] in (0,32)
            if BibleOrgSysGlobals.debugFlag:
                if self.characterBitSize == 8: assert tokenBytes[1] == 32 # Space
                elif self.characterBitSize == 16: assert tokenBytes[1] == 0
                else: assert False, "We want to stop here"

            index = 0
            #self.tokenBytes = []
            self.tokenString = ''
            while index < len(tokenBytes):
                if self.characterBitSize == 8:
                    token = tokenBytes[index]; index += 1
                elif self.characterBitSize == 16:
                    try: token, = struct.unpack( "<H", tokenBytes[index:index+2] ); index += 2
                    except struct.error: logging.critical( "Struct ERROR" ); break
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, chr(token), end=' ' )
                #self.tokenBytes.append( token )
                tokenChar = chr( token )
                self.tokenString += tokenChar
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(self.tokenString):,} {self.characterBitSize}-bit token characters loaded" )
        # end of load.loadTokenCharacters


        def loadVerseTextIndex():
            """
            Seems to have a header and then 972 3+32-byte or 3+48-byte (CEV) entry lines.
                972 * 32 = 31,104 = 31,102 verses in KJV + 2 blank at end.
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading verse index info from {self.sourceFolder}…" )
            filename = 'TextNdx.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading verse text index from {self.sourceFolder} {filename}…" )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                textIndexBytes = myFile.read()
            numTextIndexBytes = len(textIndexBytes)
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {numTextIndexBytes:,} text index bytes read" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"tIB {len(textIndexBytes)} {hexlify(textIndexBytes[:99])}" )
            assert numTextIndexBytes in (34055,49623,) # Divisible by 35 or 51 = 973

            key, size = textIndexBytes[0], textIndexBytes[1]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  prelude length = {size:04x} {size}" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Key={key}, line entry size={size}" )
            assert key == 1
            assert size in (35,51,) # 35-3=32, 51-3=48
            vTIHeader = textIndexBytes[3:size+3]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"tIB header {len(vTIHeader)} {hexlify(vTIHeader)}" )
            for something in vTIHeader: assert something == 0 # It's just filler
            index = size

            self.textIndex = []
            lastIE = total = count = 0
            lastPointer = -1
            while index < numTextIndexBytes:
                indexEntry = textIndexBytes[index:index+size]; index += size
                assert len(indexEntry) == size
                iE0, iE1, iE2 = indexEntry[0], indexEntry[1], indexEntry[2]
                iE = (iE2<<16) + (iE1<<8) + iE0 # IE starts at 0, increases by 1200-1800 each time, up to 1,393,772
                assert iE > lastIE or ( iE==0 and lastIE==0)
                indexEntry = indexEntry[3:]
                lineOffset = iE - lastIE
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{len(self.textIndex)} iE={iE} lastIE={lastIE} lineOffset={lineOffset} total={total}' )
                assert total == lineOffset
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{len(self.textIndex):3} +{lineOffset:4}={iE:4} {hexlify(indexEntry)} {indexEntry}' )
                total = 0
                if size == 35: # One byte per entry (handles offsets in range 0..256)
                    for something in indexEntry: # KJV G
                        if something > 0:
                            total += something
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"something={something} total={total}" ) # Each one adds another 35-145 for KJV, 20-70+ for YLT
                            pointer = total + iE
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"pointer={pointer} lastPointer={lastPointer}" )
                            assert pointer > lastPointer
                            self.textIndex.append( pointer )
                            lastPointer = pointer
                        #else:
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Skipped zero entry at {pointer}" )
                elif size == 51: # 1.5 bytes per entry (handles offsets in range 0..4,095 -- 256 is not enough for long verses)
                    nibbleIndex = 0
                    for nibbles in indexEntry: # KJV G
                        if nibbleIndex == 0: n1, n2 = nibbles & 0x0F, (nibbles & 0xF0) >> 4; nibbleIndex = 2
                        elif nibbleIndex == 1: n2, n3 = nibbles & 0x0F, (nibbles & 0xF0) >> 4; nibbleIndex = 3
                        elif nibbleIndex == 2: n3, n4 = nibbles & 0x0F, (nibbles & 0xF0) >> 4; nibbleIndex = 4
                        else: assert False, "We want to stop here"
                        if nibbleIndex >= 3:
                            something = (n3<<8) + (n2<<4) + n1
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"nibbles1 {nibbleIndex} {n1:02x} {n2:02x} {n3:02x} {n4:02x} {something:04x}" )
                            if nibbleIndex == 3: nibbleIndex = 0
                            elif nibbleIndex == 4: n1 = n4; nibbleIndex = 1
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"nibbles2 {nibbleIndex} {n1:02x} {n2:02x} {n3:02x} {n4:02x} {something:04x}" )
                            if something > 0:
                                total += something
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"something={something} total={total}" ) # Each one adds another 35-145 for KJV, 20-70+ for YLT
                                pointer = total + iE
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"pointer={pointer} lastPointer={lastPointer}" )
                                assert pointer > lastPointer
                                self.textIndex.append( pointer )
                                lastPointer = pointer
                            #else:
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Skipped zero entry at {pointer}" )
                else: assert False, "We want to stop here"
                lastIE = iE
                count += 1
            assert index == numTextIndexBytes

            numTextIndexEntries = len(self.textIndex)
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {numTextIndexEntries:,} text-index entries loaded from {count} lines" )
            if BibleOrgSysGlobals.debugFlag:
                assert numTextIndexEntries == 31102 or self.abbreviation in ( 'Darby','Wey', 'Williams',) # Darby has 31,099 (3 less)
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Final accumulated total was {total + iE:,} (should equal length of Text.Dat)" )
                #for index in (0, 1, 2, 3, 23145, -4, -3, -2, -1 ): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      {index}={self.textIndex[index]}" )
                #assert self.textIndex[-2]==self.textIndex[-3] and self.textIndex[-1]==self.textIndex[-3] # Two zero entries at end
        # end of load.loadVerseTextIndex


        def loadBibleText():
            """
            1.6-2.4MB = about 52-80 average bytes per verse.
            Doesn't contain any text -- it's pointers to dictionary words plus some control codes.

                01 means capitalize the next word
                05..7F is an index to the common words in Version.Dat
                80..FF means use the next byte as well as an index to the dictionary.
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading verse text data from {self.sourceFolder}…" )
            filename = 'Text.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )

            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading text from {self.sourceFolder} {filename}…" )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                self.textBytes = myFile.read()
            numTextBytes = len(self.textBytes)
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {numTextBytes:,} text bytes read" )
            if BibleOrgSysGlobals.debugFlag: assert numTextBytes == self.textIndex[-1]
        # end of load.loadBibleText


        def loadTextOpt():
            """
            Seems to be a 4-byte binary header
                then a series of 896 16-bit pointers
                then a series of 896 ones and zeroes
                then a series of 896 16-bit strings with an initial length byte
                    and the first letter capitalized:
                '  !”'    tO 10/5 '  ).}'    tO 16/8 '  ,\\\\*\\\\'    tO 16/8 '  ,\\\\†\\\\'    tO 8/4 '  ,”'    tO 18/9 '  .”\\\\*\\\\'    tO 18/9 '  .”\\\\†\\\\'    tO 10/5 '  :\\\\'    tO 16/8 '  :\\\\†\\\\'    tO 8/4 '  ?”'    tO 14/7 '  \\\\).}'    tO 12/6 '  \\\\)}'    tO 12/6 '  \\\\.}'    tO 14/7 '  \\\\†\\\\'    tO 6/3 '  ’'    tO 6/3 '  ”'    tO 18/9 ' +!!\\\\†\\\\'    tO 10/5 ' +!!—'    tO 6/3 ' +…'    tO 6/3 ' -('    tO 8/4 ' -\\@'    tO 12/6 ' -{(\\\\'    tO 6/3 ' -‘'    tO 6/3 '#10'    tO 6/3 '#11'    tO 6/3 '#12'    tO 6/3 '#13'    tO 6/3 '#14'    tO 6/3 '#15'    tO 6/3 '#16'    tO 6/3 '#17'    tO 6/3 '#18'    tO 6/3 '#19'    tO 4/2 '#2'    tO 6/3 '#20'    tO 6/3 '#21'    tO 6/3 '#22'    tO 6/3 '#23'    tO 6/3 '#24'    tO 6/3 '#25'    tO 6/3 '#26'    tO 6/3 '#27'    tO 6/3 '#28'    tO 6/3 '#29'    tO 4/2 '#3'    tO 6/3 '#30'    tO 6/3 '#31'    tO 6/3 '#32'    tO 6/3 '#33'    tO 6/3 '#34'    tO 6/3 '#35'    tO 6/3 '#36'    tO 6/3 '#37'    tO 6/3 '#38'    tO 6/3 '#39'    tO 4/2 '#4'    tO 6/3 '#40'    tO 6/3 '#43'    tO 4/2 '#5'    tO 4/2 '#6'    tO 4/2 '#7'    tO 4/2 '#8'    tO 4/2 '#9'    tO 2/1 '1'    tO 2/1 '2'
                Aaron Able Above Abraham
                …
                Years Yes Yet Young Yourself Zedekiah Zion
            Doesn't include the capitalized words from Version.Dat.
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading textOpt data from {self.sourceFolder}…" )
            filename = 'TextOpt.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading text opts from {self.sourceFolder} {filename}…" )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                optBytes = myFile.read()
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {len(optBytes):,} optBytes bytes read" )

            index = 0
            key, size, zero1, zero2 = optBytes[0], optBytes[1], optBytes[2], optBytes[3]
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    TextOpt: key={key} size={size}" )
            assert key == 255
            assert size == 3
            assert zero1 == 0
            assert zero2 == 0
            index += 4

            # Load pointers -- what do they mean?
            startIndex = index
            self.optStuff1 = []
            lastPointer = -1
            while True:
                stuff = optBytes[index:index+4]
                pointer = (stuff[1]<<8) + stuff[0]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      {len(self.optStuff1)} {index:04x} {hexlify(stuff)} pointer={pointer:04x}={pointer}" )
                if stuff[2]!=0 or stuff[3]!=0: break # something changes here
                assert pointer > lastPointer
                if lastPointer == -1: firstPointer = pointer
                index += 4
                self.optStuff1.append( pointer )
                if len(self.optStuff1) > 1000: assert False, "We want to stop here"
                lastPointer = pointer
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {len(self.optStuff1)}={len(self.optStuff1):04x} (seems to match number of words below) increasing 16-bit pointers (or are they bigger?) {firstPointer}={firstPointer:04x}..{lastPointer}={lastPointer:04x} loaded from {startIndex:04x} onwards" )
                for ix in (0, 1, 2, 3, -4, -3, -2, -1 ):
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      {ix}={self.optStuff1[ix]:04x}={self.optStuff1[ix]}" )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.optStuff1 )
                assert len(self.optStuff1) == 896

            # Load more stuff -- what does it mean?
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'index={index}={index:04x}' )
            assert index == 0xe04
            startIndex = index
            self.optStuff2 = []
            while True:
                stuff = optBytes[index]; index += 1
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      {len(self.optStuff2)} {index:04x} {hexlify(stuff)}" )
                assert stuff==0 or stuff==1
                self.optStuff2.append( stuff )
                if len(self.optStuff2) >= len(self.optStuff1): break
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {len(self.optStuff2)} unknown 1-bit flags loaded from {startIndex:04x} onwards" )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  index = {index:04x}={index}" )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.optStuff2 )
                for ix in (0, 1, 2, -2, -1 ): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      {ix}: {self.optStuff2[ix]:02x}={self.optStuff2[ix]!r}" )
                assert len(self.optStuff2) == len(self.optStuff1)

            # Now load these capitalized commonish words -- how are they referenced?
            # (Don't seem to overlap with the more common capitalized words in Version.Dat)
            # Seems that ASV has 8-bit chars, but most others have 16-bit chars
            assert index == 0x1184
            startIndex = index
            self.optWords = []
            while index < len(optBytes):
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  vB {hexlify(vBytes)} {vBytes}" )
                #vLen, = struct.unpack( ">H", vBytes[0:2] )
                vLen = optBytes[index]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "vL2", repr(vLen) )
                vString = ''
                if self.characterBitSize == 8:
                    # Nine 8-bit chars filled with rubbish past the specified number
                    for j in range( vLen ):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, vBytes[2*j+1:2*j+3] )
                        char8 = optBytes[index+j+1]
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, vLen, j, char8 )
                        vString += chr( char8 )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'vString', repr(vString) )
                    index += 10
                    assert not vString[0].islower()
                    self.optWords.append( vString )
                elif self.characterBitSize == 16:
                    # Nine 16-bit characters
                    vBytes = optBytes[index+1:index+19]
                    for j in range( int(vLen/2) ):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, vBytes[2*j+1:2*j+3] )
                        try: char16, = struct.unpack( "<H", vBytes[2*j:2*j+2] )
                        except struct.error: logging.critical( "Struct error" ); index += 999999; break
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, char16 )
                        vString += chr( char16 )
                    #vString = vBytes[2:vLen+1].decode( 'utf-16' )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    tO {vLen}/{int(vLen/2)} {vString!r}", end='' )
                    index += 19
                    # assert not vString[0].islower()
                    self.optWords.append( vString )
            numOptWords = len( self.optWords )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {numOptWords}={numOptWords:04x} 19-byte text-opt capitalized words loaded from {startIndex:04x} onwards" )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '     ', self.optWords )
                assert numOptWords == len(self.optStuff1)
        # end of load.loadTextOpt


        def loadXrefIndex():
            """
            Seems to have a double header and then 417 double entry lines.
                Line A seems to start with a 3-byte pointer 0..90280 and then 32 bytes
                Line B seems to start with a 3-byte pointer 0..640,565 to Xref.Dat and then 32 words
                    The final bytes/words in the final lines are zeroes (fillers).

            12,289 2-tuples in self.xrefIndex seem to be
                a count (3..226)
                a not always increasing pointer (0..640.567) to Xref.Dat
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading cross-reference index data from {self.sourceFolder}…" )
            filename = 'XrefNdx.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading xref index from {self.sourceFolder} {filename}…" )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                xrefIndexBytes = myFile.read()
            numXrefIndexBytes = len(xrefIndexBytes)
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {numXrefIndexBytes:,} xref index bytes read" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"tIB {len(xrefIndexBytes)} {hexlify(xrefIndexBytes[:99])}" )

            #header = xrefIndexBytes[0:35]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"xIB1 header {len(header)} {hexlify(header)}" )
            key, size0, size1, indexSize, tokenBlkSize = struct.unpack( "<BBBHH", xrefIndexBytes[0:7] )
            size = size0 + size1
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  prelude length = {size:04x} {size}" )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Key={key}, line entry size {size0}+{size1}={size} index size={indexSize} tokenBlkSize={tokenBlkSize}*2={tokenBlkSize*2}" )
            assert key == 2
            assert size0 == 35 # 35-3=32
            assert size1 == 67 # 67-3=64
            assert size == 102
            assert indexSize == 0
            # assert 90 <= tokenBlkSize <= 215 # AV=195, YLT=206, CEV=186
            index = 7
            header = xrefIndexBytes[index:size]
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"xIB2 header {len(header)} {hexlify(header)}" )
            index = size

            assert index == 102
            self.xrefIndex = []
            lastPointer = total = count = 0
            while index < numXrefIndexBytes:
                indexEntry = xrefIndexBytes[index:index+size]; index += size
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{len(self.xrefIndex):4} {len(indexEntry)} {hexlify(indexEntry)} {indexEntry}' )
                assert len(indexEntry) == size
                indexEntry1, indexEntry2 = indexEntry[:size0], indexEntry[size0:]
                assert len(indexEntry1)==size0 and len(indexEntry2)==size1
                # Seems part a starts with a 3-byte pointer to something
                diskPointer1 = (indexEntry1[2]<<16) + (indexEntry1[1]<<8) + indexEntry1[0]
                diskPointer2 = (indexEntry2[2]<<16) + (indexEntry2[1]<<8) + indexEntry2[0]
                assert diskPointer2 == total
                count1 = indexEntry1[3]
                if 0 and len(self.xrefIndex) < 10:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'  {len(self.xrefIndex)} {diskPointer1:06x}={diskPointer1} {count1}' )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    a {len(indexEntry1)} {hexlify(indexEntry1)} {indexEntry1[3:]}' )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'     {diskPointer2:06x}={diskPointer2}' )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    b {len(indexEntry2)} {hexlify(indexEntry2)} {indexEntry2[3:]}' )
                for x in range( 32 ):
                    b1, w2 = indexEntry1[x+3], (indexEntry2[2*x+3+1]<<8) + indexEntry2[2*x+3]
                    if b1 == 0:
                        assert w2 == 0
                        break
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'b1={b1:02x}={b1} w2={w2:04x}={w2}' )
                    total += w2
                    self.xrefIndex.append( (b1,diskPointer2+w2) )
                #if len(self.xrefIndex) > 10: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' ); assert False, "We want to stop here"
                count += 1
            assert index == numXrefIndexBytes
            numXrefIndexEntries = len(self.xrefIndex)
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {numXrefIndexEntries:,} xref index duples loaded from {count} double lines" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.xrefIndex )
            # assert 231 <= count <= 428 # AV=417, YLT=385, CEV=338
            # assert 7365 <= numXrefIndexEntries <= 13694 # AV=13,316, YLT=12,289, CEV=10,796
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Final total was {total + iE} (should equal length of Text.Dat)" )
            #for index in range( 150 ):
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      {index}: {self.xrefIndex[index][0]:02x} @ {self.xrefIndex[index][1]:04x}={self.xrefIndex[index][1]}" )
        # end of load.loadXrefIndex


        def loadStrongsIndex():
            """
            Seems to have a header and then 277 entry lines.
                Each line has a 3-byte pointer to Xref.Dat
                    followed by 32 16-bit offsets
                277 * 32 = 8,864 entries.
                The last superfluous entries are zeroes.

            Strongs' numbers must be in range 0..8,849.

            Strongs printed numbers are Hebrew 1..8,674 plus Greek 1..5,624 = total = 14,298
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading Strongs index data from {self.sourceFolder}…" )
            filename = 'XrefNdxs.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                try: del self.StrongsIndex
                except AttributeError: pass
                return False
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading Strongs reference index from {self.sourceFolder} {filename}…" )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                xrefIndexBytes = myFile.read()
            numXrefIndexBytes = len(xrefIndexBytes)
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {numXrefIndexBytes:,} Strongs index bytes read" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"tIB {len(xrefIndexBytes)} {hexlify(xrefIndexBytes[:99])}" )

            #header = xrefIndexBytes[0:35]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"xsIB1 header {len(header)} {hexlify(header)}" )
            key, size0, size1, indexSize, tokenBlkSize = struct.unpack( "<BBBHH", xrefIndexBytes[0:7] )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  prelude length = {size:04x} {size}" )
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Key={key}, line entry size {size0}" )
            assert key == 1
            assert size0 == 67 # 67-3=64
            assert size1 == 0
            assert indexSize == 0
            assert tokenBlkSize == 0
            index = 7
            header = xrefIndexBytes[index:size0]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"xIB2 header {len(header)} {hexlify(header)}" )
            for something in header: assert something == 0 # It's just filler
            index = size0

            assert index == 67
            self.StrongsIndex = []
            lastPointer = total = count = 0
            while index < numXrefIndexBytes:
                indexEntry = xrefIndexBytes[index:index+size0]; index += size0
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{len(self.xrefIndex):4} {len(indexEntry)} {hexlify(indexEntry)} {indexEntry}' )
                assert len(indexEntry) == size0
                # Seems part a starts with a 3-byte pointer to something
                diskPointer = (indexEntry[2]<<16) + (indexEntry[1]<<8) + indexEntry[0]
                if total == 0: total = diskPointer # Starts part way through
                assert diskPointer == total
                if 0 and len(self.xrefIndex) < 10:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'  {len(self.xrefIndex)} {diskPointer:06x}={diskPointer}' )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    {len(indexEntry)} {hexlify(indexEntry)} {indexEntry[3:]}' )
                for x in range( 32 ):
                    w2 = (indexEntry[2*x+3+1]<<8) + indexEntry[2*x+3]
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    {x} w2={w2:04x}={w2} @ {len(self.StrongsIndex)}' )
                    if w2 == 0 and len(self.StrongsIndex)>8849: break
                    total += w2
                    self.StrongsIndex.append( (total) )
                #if len(self.xrefIndex) > 10: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' ); assert False, "We want to stop here"
                count += 1
            assert index == numXrefIndexBytes
            numStrongsIndexEntries = len(self.StrongsIndex)
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {numStrongsIndexEntries:,} Strongs index entries loaded from {count} lines" )
            if BibleOrgSysGlobals.debugFlag:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.StrongsIndex )
                assert count == 277
                assert numStrongsIndexEntries == 8850
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Final total was {total + iE} (should equal length of Text.Dat)" )
                for index in (0, 1, 2, 3, -4, -3, -2, -1 ): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      {index}={self.StrongsIndex[index]}" )
        # end of load.loadStrongsIndex


        def loadXrefData():
            """
            0.6-1.1MB
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading cross-reference data from {self.sourceFolder}…" )
            filename = 'Xref.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading xref data from {self.sourceFolder} {filename}…" )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                self.xrefBytes = myFile.read()
            numXrefBytes = len(self.xrefBytes)
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {numXrefBytes:,} xref bytes read" )
            if BibleOrgSysGlobals.debugFlag:
                if 'StrongsIndex' in self.__dict__: assert numXrefBytes == self.StrongsIndex[-1]
                else: # Not all versions have Strongs
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "lastXref", self.xrefIndex[-1], self.xrefIndex[-2] )
                    # XXXXX Why does this fail for CEVUK?
                    if self.abbreviation not in ('ASV', 'AKJV', 'CEVUK', 'Darby', 'KJ21', 'Webster', 'Wey', 'Williams', ):
                        assert numXrefBytes == self.xrefIndex[-1][1]

            if 0:
                lastPointer = 0
                for j, pointer in enumerate( self.textIndex ):
                    strip = self.xrefBytes[lastPointer:pointer]
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{j:5} {lastPointer:5} {pointer:5} {hexlify(strip)} {strip}" )
                    lastPointer = pointer
                    if j > 10: break
        # end of load.loadXrefData


        def createDictionary():
            """
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Creating dictionary…" )
            self.dictionary = {}

            # Put the short common words into the dictionary
            startWordIndex = 5
            wordIndex = startWordIndex
            for word in self.commonWords: # These are ALL capitalized!
                if word not in ('I','Israel','Jesus','Jehovah'):
                    word = word.lower() # Not sure what I don't understand here
                self.dictionary[wordIndex] = (word,None)
                wordIndex += 1
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'wi', wordIndex )
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    {len(self.commonWords):,} common words added to dictionary from {startWordIndex} to {wordIndex-1}={wordIndex-1:02x}' )
            assert wordIndex == 128
            del self.commonWords

            # Add in the compressed words
            tokenIndex = 0
            startWordIndex = 257
            wordIndex = startWordIndex
            word = ''
            for bitCodes, xrefPointer in self.xrefIndex:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'tI={tokenIndex} wI={wordIndex} bc={bitCodes:02x} p={xrefPointer:04x}' )
                commonChars, addChars = bitCodes >> 5, bitCodes & 0x1f
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'eW={word!r} cc={commonChars} {word[:commonChars]!r} ac={addChars} {self.tokenString[tokenIndex:tokenIndex+addChars]!r}' )
                word = word[:commonChars] + self.tokenString[tokenIndex:tokenIndex+addChars]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(word) )
                self.dictionary[wordIndex] = (word,xrefPointer)
                tokenIndex += addChars
                wordIndex += 1
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    {len(self.xrefIndex):,} regular words added to dictionary from {startWordIndex}={startWordIndex:02x} to {wordIndex-1:,}={wordIndex-1:04x}' )
            del self.xrefIndex

            if 0 and self.haveStrongsFlag:
                startWordIndex = self.StrongsOffset
                wordIndex = startWordIndex
                for j, xrefPointer in enumerate( self.StrongsIndex ):
                    assert j < 14298
                    word = f'\\str {j}\\str*'
                    self.dictionary[wordIndex] = (word,xrefPointer)
                    wordIndex += 1
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    {len(self.StrongsIndex):,} Strongs' numbers added to dictionary from {startWordIndex:,}={startWordIndex:04x} to {wordIndex-1:,}={wordIndex-1:02x}" )
        # end of load.createDictionary


        def getVerseBytes( absoluteVerseNumber ):
            """
            Given a verse number from 0..31,101, return the encoded bytes
            """
            fnPrint( DEBUGGING_THIS_MODULE, f"getVerseBytes( {self.abbreviation} {absoluteVerseNumber} ) = {BOS.convertAbsoluteVerseNumber( absoluteVerseNumber+1 )}" )
                #assert 0 <= absoluteVerseNumber < len(self.textIndex)
            startAt = 0 if absoluteVerseNumber==0 else self.textIndex[absoluteVerseNumber-1]
            endAt = self.textIndex[absoluteVerseNumber]
            assert endAt > startAt
            byteStrip = self.textBytes[startAt:endAt]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Verse {absoluteVerseNumber} {len(byteStrip)} {hexlify(byteStrip)} {byteStrip[-1]}' )
            return byteStrip
        #end of load.getVerseBytes


        #self.missingWordNumbers = set()
        def getWord( wordIndex, capsFlag ):
            """
            """
            if BibleOrgSysGlobals.debugFlag:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"getWord( {wordIndex}={wordIndex:04x} )" )
                assert 5 <= wordIndex <= 0x7FFF

            if self.haveStrongsFlag and wordIndex >= self.StrongsOffset:
                return f'\\str {wordIndex - self.StrongsOffset}\\str*'

            try: dictionaryWord = self.dictionary[wordIndex][0] #+ f'({self.dictionary[wordIndex][1]})'
            except KeyError:
                dictionaryWord = f'«{wordIndex:04x}»'
                if BibleOrgSysGlobals.debugFlag:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{self.abbreviation} missing word {wordIndex:04x} -- have {len(self.dictionary)}={len(self.dictionary):04x} words' )
                    #self.missingWordNumbers.add( wordIndex )

            return dictionaryWord.title() if capsFlag else dictionaryWord
        #end of load.getWord


        def findWordInDictionary( searchWord ):
            """
            A diagnostic reverse dictionary lookup.
            """
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"findWordInDictionary( {searchWord!r} )" )

            results = []
            lcSearchWord = searchWord.lower()
            for wordIndex,(dictWord,dictPointer) in self.dictionary.items():
                if dictWord.lower() == lcSearchWord:
                    results.append( (dictWord,wordIndex) )

            return results
        #end of load.findWordInDictionary


        def getBibleText( verseBytes, reference=None ):
            """
            Given a verse number from 0..31,101, return the encoded bytes
            """
            fnPrint( DEBUGGING_THIS_MODULE, f"getBibleText( {hexlify(verseBytes)} ) {self.abbreviation} {reference}" )
            resultString = ''
            capsFlag = footnoteFlag = headingFlag = False
            saved = None
            for something in verseBytes:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'a {something:02x} {saved} {capsFlag} {resultString!r}' )
                word = None
                if saved is None:
                    if something > 0x7F: assert saved is None; saved = something & 0x7F
                    elif something == 0: footnoteFlag = not footnoteFlag; word = '\\f' if footnoteFlag else '\\f*'
                    elif something == 1: capsFlag = True
                    elif something == 2:
                        headingFlag = not headingFlag
                        if footnoteFlag:
                            word = '\\fq' if headingFlag else '\\ft'
                        else:
                            word = '\\HEAD' if headingFlag else '\\HEAD*'
                    elif something == 3: unknownFlag3 = True; word = '«3»'
                    elif something == 4: unknownFlag4 = True; word = '«4»'
                    else: word = getWord( something, capsFlag ) # 8-bit index
                else:
                    something = (something << 7) + saved
                    saved = None
                    word = getWord( something, capsFlag ) # 15-bit index
                if word:
                    assert saved is None
                    resultString += (' ' if resultString else '') + (word.title() if capsFlag else word)
                    capsFlag = False
            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                assert not capsFlag # Should be off at the end of the verse
                assert not footnoteFlag # Should be off at the end of the verse
                assert not headingFlag # Should be off at the end of the verse

            # Now scan for open and close fields
            #if reference==('SA2','23','8'): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, repr(resultString) ); assert False, "We want to stop here"
            for openCode,newOpenCode,closeCode,newCloseCode in ( ('\x1c','STARTC','\x1c','ENDC'),
                                                                ('\x1e','STARTE','\x1e','ENDE'),
                                                                ('\x1f','STARTF','\x1f','ENDF'),
                                                                ('[','\\add',']','\\add*'),
                                                                #('\\\\  #','\\xt','\\\\',''),
                                                                ):
                ix = resultString.find( openCode )
                while ix != -1:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{ix} {openCode!r}->{newOpenCode!r} {closeCode!r}->{newCloseCode!r} in {resultString!r}' )
                    resultString = resultString.replace( openCode, newOpenCode, 1 )
                    ixEnd = resultString.find( closeCode, ix )
                    if ixEnd == -1:
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Missing {closeCode!r} close code' )
                        pass
                    else:
                        resultString = resultString.replace( closeCode, newCloseCode, 1 )
                    ix = resultString.find( openCode, ix )
                if resultString.find( closeCode, ix ) != -1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Unexpected {closeCode!r} close code'  ); assert False, "We want to stop here"
            #if BibleOrgSysGlobals.debugFlag: # final check
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, repr(resultString), resultString )
                #assert '\\x' not in repr(resultString)  Makes no sense for special characters

            # Now do our final clean-up
            for old,new in ( ('   ',''), ('  ',''),
                            (' .','.'), (' ,',','),
                            (' ’ s ','’s '), ('‘ ','‘'), (' ’','’'),
                            ('+',' '), ('-',' '),
                            ('\\\\',''),
                            #('[','\\add'), (']','\\add*'),
                            (' \\str ','\\str '), (' \\f ','\\f ' ), (' \\f*','\\f*' ),
                            ('\\HEAD lord','\\nd Lord\\nd*'),
                            ): #('( ','('), ):
                resultString = resultString.replace( old, new )
            for toDelete in ( 'STARTC','ENDC', ' STARTE','STARTE',' ENDE','ENDE', ' STARTF','STARTF',' ENDF','ENDF', ):
                resultString = resultString.replace( toDelete, '' )
            while '  ' in resultString: # Reduce double spaces
                resultString = resultString.replace( '  ', ' ' )
            if BibleOrgSysGlobals.debugFlag: # final check
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(resultString) )
                assert '  ' not in resultString

            return resultString.strip()
        #end of load.getBibleText


        def getStrongsBytes( StrongsNumber ):
            """
            The StrongsNumber must be in the range 1..8,850.

            Strongs printed numbers are Hebrew 1..8,674 plus Greek 1..5,624 = total = 14,298
            """
            if BibleOrgSysGlobals.debugFlag:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"getStrongsBytes( {StrongsNumber} )" )
                assert 1 <= StrongsNumber <= 8850
            startAt = self.StrongsIndex[StrongsNumber-1]
            endAt = startAt + 120
            #try: endAt = self.StrongsIndex[StrongsNumber]
            #except IndexError: endAt = startAt + 999
            assert endAt > startAt
            byteStrip = self.xrefBytes[startAt:endAt]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, StrongsNumber, startAt, endAt, byteStrip )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Strongs {StrongsNumber} {len(byteStrip)} {hexlify(byteStrip)} {byteStrip!r}' )
            return byteStrip
        # end of getStrongsBytes


        def loadBooks():
            """
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, 'Loading books…' )

            bookCount = 0
            currentBBB = None
            for n in range( 31102 ):
                BCVRef = BOS.convertAbsoluteVerseNumber( n+1 )
                BBB, C, V = BCVRef
                if BBB != currentBBB:
                    if currentBBB is not None: # Save the last book
                        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "Saving", BBB, bookCount+1 )
                        self.stashBook( thisBook )
                    # Create the new book
                    if BibleOrgSysGlobals.verbosityLevel > 2:  vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'  Loading {BBB}…' )
                    thisBook = BibleBook( self, BBB )
                    thisBook.objectNameString = 'Online Bible Book object'
                    thisBook.objectTypeString = 'Online Bible'
                    currentBBB, currentC = BBB, '0'
                    bookCount += 1
                if C != currentC:
                    thisBook.addLine( 'c', C )
                    currentC = C

                try:
                    verseString = getBibleText( getVerseBytes( n ), BCVRef )
                    thisBook.addLine( 'v', V + ' ' + verseString )
                except IndexError: # That verse doesn't seem to exist
                    logging.warning( f"No verse information for {self.abbreviation} {BBB} {C}:{V}" )

            if currentBBB is not None: # Save the very last book
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "Saving", BBB, bookCount+1 )
                self.stashBook( thisBook )
        # end of load.loadBooks


        def test():
            """
            """
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, '\nDEBUG TEST:' )

            if 1:
                for n in ( 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 123, 23144, 23145, 23146, 31101, ):
                    BCVRef = BOS.convertAbsoluteVerseNumber( n+1 )
                    try:
                        verseStuff = getVerseBytes( n )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n{self.abbreviation} {BCVRef} = {len(verseStuff)} {hexlify(verseStuff)} {verseStuff}" )
                        verseString = getBibleText( verseStuff, BCVRef )
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n{self.abbreviation} {n} {BCVRef} = {repr(verseString)}" )
                        if 0:
                            for j in range( int( len(verseStuff)/2 ) ):
                                w2 = (verseStuff[2*j+1]<<8) + verseStuff[2*j]
                                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'   {j} {w2:04x}={w2} {self.tokenString[w2:w2+3]!r}' )
                    except IndexError:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"No such verse: {self.abbreviation} {n} {BCVRef}" )

            if 0:
                for n in range( 31102 ):
                    BCVRef = BOS.convertAbsoluteVerseNumber( n+1 )
                    try:
                        verseString = getBibleText( getVerseBytes( n ), BCVRef )
                        printFlag = False
                        for something in ('<<000', '<<01', '<<02', '<<031', '<<032', '<<033', '<<034', ):
                            if something in verseString: printFlag = True
                        if printFlag or DEBUGGING_THIS_MODULE:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n{self.abbreviation} {n} {BCVRef} = {verseString!r}" )
                            if '<<020' in verseString: assert False, "We want to stop here"
                            #if '<<62' in verseString: assert False, "We want to stop here"
                        #if BCVRef == ('GEN','20','2'): assert False, "We want to stop here"
                    except IndexError:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"No such verse: {self.abbreviation} {n} {BCVRef}" )

            if 1 and self.haveStrongsFlag:
                for word in ( 'from', 'the', 'same' ):
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{word!r} -> {findWordInDictionary( word )}' )
                for strongs in ( 7225, 430, 1254, 853, 8064, 1, 2, 8849, 8850 ):
                    xrefStuff = getStrongsBytes( strongs )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nStrongs {strongs} = {len(xrefStuff)} {hexlify(xrefStuff)} {xrefStuff}" )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"         {strongs} = {getBibleText( xrefStuff )!r}" )

            #if self.missingWordNumbers:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'missingWordNumbers', sorted(self.missingWordNumbers) ); assert False, "We want to stop here"
        # end of load.test


        if 1:
            loadPierceOnlineBibleMetadata()
            loadVersion()
            loadTokenCharacters()
            loadVerseTextIndex()
            loadBibleText()
            loadTextOpt()
            loadXrefIndex()
            loadStrongsIndex()
            loadXrefData()

            createDictionary()
            loadBooks()

            if BibleOrgSysGlobals.debugFlag:
                test()
        else: # for testing/debugging
            for something in ('AV','ASV','AKJV','CEVUK','Darby','KJ21','RWebster','WEBSTER','Wey','Williams','YLT',): # 'MART_1707',
                self.abbreviation = something
                self.sourceFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/', something+'/' )
                loadPierceOnlineBibleMetadata()
            for something in ('AV','ASV','AKJV','CEVUK','Darby','KJ21','RWebster','WEBSTER','Wey','Williams','YLT',): # 'MART_1707',
                self.abbreviation = something
                self.sourceFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/', something+'/' )
                loadVersion()
            for vbh in VBH1s: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{vbh:10} = {len(VBH1s[vbh])} {VBH1s[vbh]}' )
            for vbh in VBH2s: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{vbh:10} = {len(VBH2s[vbh])} {VBH2s[vbh]}' )
            for vbh in VBH3s: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'{vbh:10} = {len(VBH3s[vbh])} {VBH3s[vbh]}' )
            assert False, "We want to stop here"

        self.doPostLoadProcessing()
    # end of PierceOnlineBible.load
# end of PierceOnlineBible class



def testOB( TOBfilename ):
    # Crudely demonstrate the Online Bible class
    from BibleOrgSys.Reference import VerseReferences
    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/' )

    TOBfolder = os.path.join( testFolder, TOBfilename+'/' )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Demonstrating the Online Bible class…" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Test folder is {TOBfolder!r} {TOBfilename!r}" )
    olb = PierceOnlineBible( TOBfolder )
    olb.load() # Load and process the file
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, olb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        olb.check()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
        olbErrors = olb.getCheckResults()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, olbErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##olb.toDrupalBible()
        olb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(olb)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(olb)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(olb)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, svk, olb.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = olb.getVerseText( svk )
            fullVerseText = olb.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, shortText, verseText )
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'  {fullVerseText}' )
# end of testOB


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = PierceOnlineBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestA1", result1 )
        result2 = PierceOnlineBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestA2", result2 )
        result3 = PierceOnlineBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestA3", result3 )

        testSubfolder = os.path.join( testFolder, 'AV/' )
        result3 = PierceOnlineBibleFileCheck( testSubfolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestB1", result3 )
        result4 = PierceOnlineBibleFileCheck( testSubfolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestB2", result4 )
        result5 = PierceOnlineBibleFileCheck( testSubfolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestB3", result5 )


    if 0: # specified module
        singleModule = 'AV'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nOnline C/ Trying {singleModule}" )
        #myTestFolder = os.path.join( testFolder, singleModule+'/' )
        #testFilepath = os.path.join( testFolder, singleModule+'/', singleModule+'_utf8.txt' )
        testOB( singleModule )

    if 0: # specified modules
        good = ('AV','ASV','AKJV','CEVUK','Darby','KJ21','RWebster','WEBSTER','Wey','Williams','YLT',) # 'MART_1707',
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nOnline D{j+1}/ Trying {testFilename}" )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testOB( testFilename )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testOB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nOnline E{j+1}/ Trying {someFolder}" )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testOB( someFolder )
# end of PierceOnlineBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = PierceOnlineBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestA1", result1 )
        result2 = PierceOnlineBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestA2", result2 )
        result3 = PierceOnlineBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestA3", result3 )

        testSubfolder = os.path.join( testFolder, 'AV/' )
        result3 = PierceOnlineBibleFileCheck( testSubfolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestB1", result3 )
        result4 = PierceOnlineBibleFileCheck( testSubfolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestB2", result4 )
        result5 = PierceOnlineBibleFileCheck( testSubfolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Online TestB3", result5 )


    if 0: # specified module
        singleModule = 'AV'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nOnline C/ Trying {singleModule}" )
        #myTestFolder = os.path.join( testFolder, singleModule+'/' )
        #testFilepath = os.path.join( testFolder, singleModule+'/', singleModule+'_utf8.txt' )
        testOB( singleModule )

    if 0: # specified modules
        good = ('AV','ASV','AKJV','CEVUK','Darby','KJ21','RWebster','WEBSTER','Wey','Williams','YLT',) # 'MART_1707',
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nOnline D{j+1}/ Trying {testFilename}" )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testOB( testFilename )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testOB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nOnline E{j+1}/ Trying {someFolder}" )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testOB( someFolder )
# end of PierceOnlineBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of PierceOnlineBible.py
