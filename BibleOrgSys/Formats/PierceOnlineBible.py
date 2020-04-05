#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# PierceOnlineBible.py
#
# Module handling Larry Pierce's "Online Bible" files
#
# Copyright (C) 2015-2019 Robert Hunt
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
Module reading and loading Larry Pierce's Online Bible undocumented binary files.
    NOTE: This is NOT an "online" Bible (but preceded widespread internet)

Files are usually:
    Copyrite.Dat (a text file),
    Text.Dat, TextNdx.Dat, TextOpt.Dat, Tokens.Dat, Version.Dat
    Version.Ext (a text file),
    Xref.Dat, xRefNdx.Dat
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-10-03' # by RJH
SHORT_PROGRAM_NAME = "PierceOnlineBible"
PROGRAM_NAME = "Pierce Online Bible format handler"
PROGRAM_VERSION = '0.21'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, struct
from binascii import hexlify
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem


compulsoryFiles = ( 'VERSION.DAT', 'TEXT.DAT', 'TEXTNDX.DAT', ) # Must be UPPPERCASE



def PierceOnlineBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Online Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one Online Bible is found,
        returns the loaded PierceOnlineBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "PierceOnlineBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("PierceOnlineBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("PierceOnlineBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " PierceOnlineBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PierceOnlineBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = PierceOnlineBible( givenFolderName )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("PierceOnlineBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    PierceOnlineBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                if somethingUpper in compulsoryFiles: foundFileCount += 1
        if foundFileCount >= len(compulsoryFiles):
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PierceOnlineBibleFileCheck foundProjects", numFound, foundProjects )
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
    def __init__( self, sourceFolder, encoding=None ):
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
            logging.critical( _("PierceOnlineBible: Folder {!r} is unreadable").format( self.sourceFolder ) )

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
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("\nLoading from {}…").format( self.sourceFolder ) )


        def loadPierceOnlineBibleMetadata():
            """
            Version.Ext contains lines of text.
            """
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading metadata from {}…").format( self.sourceFolder ) )

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
                            if lineCount==1 and encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF
                                logging.info( "loadPierceOnlineBibleMetadata: Detected Unicode Byte Order Marker (BOM) in {}".format( filepath ) )
                                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                            #if not line: continue # Just discard blank lines
                            lines.append( line )
                            lastLine = line
                except UnicodeDecodeError:
                    logging.error( _("loadPierceOnlineBibleMetadata fails with encoding: {}{}").format( encoding, {} if encoding==encodings[-1] else ' -- trying again' ) )

            if self.encoding is None and lines:
                self.encoding = encoding

            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    {} metadata lines read".format( len(lines) ) ) # 16 expected

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
                ##print( t("getBinaryString( {}, {} )").format( binary, numBytes ) )
            #if len(binary) < numBytes: halt # Too few bytes provided
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
                #print( t("getFileString( {}, {} )").format( thisFile, numBytes ) )
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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading main version data from {}…").format( self.sourceFolder ) )
            filename = 'Version.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading version from {} {}…").format( self.sourceFolder, filename ) )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                versionBytes = myFile.read()
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {:,} version bytes read".format( len(versionBytes) ) )
            #print( "vB {} {}".format( len(versionBytes), versionBytes ) )

            key, size = versionBytes[0], versionBytes[1]
            #print( "  prelude length = {:04x} {}".format( size, size ) )
            #print( "    Key={}, line entry size={}".format( key, size ) )
            assert key == 8

            index, length = 1, 12
            vHeader1 = versionBytes[index:index+length]; index += length
            if BibleOrgSysGlobals.debugFlag:
                print( "    {} vBH1 {} {}".format( self.abbreviation, len(vHeader1), hexlify(vHeader1) ) )
                VBH1s[self.abbreviation] = hexlify(vHeader1)
            unknown1, = struct.unpack( "<H", vHeader1[3:5] )
            if BibleOrgSysGlobals.debugFlag:
                print( "      unknown1 is {:04x}={:,}".format( unknown1, unknown1 ) )
                #assert ntOffset == 23146
            unknown2, = struct.unpack( "<H", vHeader1[5:7] )
            if BibleOrgSysGlobals.debugFlag:
                print( "      unknown2 is {:04x}={:,}".format( unknown2, unknown2 ) )
                #assert ntOffset == 23146
            ntOffset, = struct.unpack( "<H", vHeader1[7:9] )
            if BibleOrgSysGlobals.debugFlag:
                print( "      NT offset is {:04x}={:,}".format( ntOffset, ntOffset ) )
                assert ntOffset == 23146
            unknownFlag1 = vHeader1[-1]
            if BibleOrgSysGlobals.debugFlag:
                print( "      Unknown flag1 is {}".format( unknownFlag1 ) )
                assert unknownFlag1 in (0,1)

            length = 10 # 1 length byte and 9 max characters
            strings1 = []
            self.characterBitSize = 8
            while index < len(versionBytes):
                vBytes = versionBytes[index:index+length]
                #print( "  vB {} {}".format( hexlify(vBytes), vBytes ) )
                if vBytes[-2] == 0 and vBytes[-1] > 0x7F: break
                vLen = vBytes[0]
                if vLen > 0 and vBytes[1]:
                    vString = vBytes[1:vLen+1].decode()
                    #print( 'Vstring', vString )
                    #print( "    vBl1 {} {!r}".format( vLen, vString ), end='' )
                    assert not vString[0].islower()
                    strings1.append( vString )
                index += length
            numStrings1 = len( strings1 )
            if BibleOrgSysGlobals.debugFlag:
                print( "    {}={:04x} 8-bit capitalized common words loaded".format( numStrings1, numStrings1 ) )
                print( '     ', strings1 )
            #print( "  index = {:04x}={}".format( index, index ) )
            assert 118 <= numStrings1 <= 123

            assert index == 0x4db
            length = 137
            vHeader2 = versionBytes[index:index+length]; index += length
            assert vHeader2[0] == 5
            for ix in range( 1, 8+1 ): assert vHeader2[ix] == 0
            vHeader2 = vHeader2[9:]
            if BibleOrgSysGlobals.debugFlag:
                print( "    {} vBH2 {} {}".format( self.abbreviation, len(vHeader2), hexlify(vHeader2) ) )
                VBH2s[self.abbreviation] = hexlify(vHeader2)

            assert index == 0x564
            length = 44
            vHeader3 = versionBytes[index:index+length]; index += length
            #print( "    vBH3 {} {}".format( len(vHeader3), hexlify(vHeader3) ) )
            assert vHeader3[0] == 8
            vHeaderDate = vHeader3[1:8+1]
            #print( "      vHeaderDate {} {}".format( len(vHeaderDate), vHeaderDate ) )
            year, month, date = int(vHeaderDate[:4]), int(vHeaderDate[4:6]), int(vHeaderDate[6:])
            if BibleOrgSysGlobals.debugFlag:
                print( "    vHeaderDate {}-{:02}-{:02}".format( year, month, date ) )
            vHeader3 = vHeader3[9:]
            for ix in range( 11+1 ): assert vHeader3[ix] == 0
            vHeader3 = vHeader3[12:]
            if BibleOrgSysGlobals.debugFlag:
                print( "    {} vBH3 {} {}".format( self.abbreviation, len(vHeader3), hexlify(vHeader3) ) )
                VBH3s[self.abbreviation] = hexlify(vHeader3)
            self.StrongsOffset, = struct.unpack( "<H", vHeader3[0:2] )
            if BibleOrgSysGlobals.debugFlag:
                print( "      Strongs' offset is {:04x}={:,}".format( self.StrongsOffset, self.StrongsOffset ) )
                assert self.StrongsOffset in ( 0xffff, 0x5d5c )
            self.haveStrongsFlag = vHeader3[4] != 0
            if BibleOrgSysGlobals.debugFlag:
                print( "      Have Strongs flag is {}".format( self.haveStrongsFlag ) )
                assert self.haveStrongsFlag in (0,1)
            numBooks, = struct.unpack( "<H", vHeader3[5:7] )
            if BibleOrgSysGlobals.debugFlag:
                print( "      numBooks is {:04x}={:,}".format( numBooks, numBooks ) )
                assert numBooks == 66
            numChapters, = struct.unpack( "<H", vHeader3[9:11] )
            if BibleOrgSysGlobals.debugFlag:
                print( "      numChapters is {:04x}={:,}".format( numChapters, numChapters ) )
                assert numChapters == 1189
            numVerses, = struct.unpack( "<H", vHeader3[17:19] )
            if BibleOrgSysGlobals.debugFlag:
                print( "      numVerses is {:04x}={:,}".format( numVerses, numVerses ) )
                assert numVerses == 31102
            unknownFlag2 = vHeader3[-2]
            if BibleOrgSysGlobals.debugFlag:
                print( "      Unknown flag2 is {:1x}".format( unknownFlag2 ) )
                assert unknownFlag2 in (1,15)

            #vHeader3 = versionBytes[0x4db:0x564]
            #print( "    vBH3 {} {}".format( len(vHeader3), hexlify(vHeader3) ) )
            #assert versionBytes[0x564] == 8
            #vHeaderDate = versionBytes[0x565:0x56d]
            ##print( "      vHeaderDate {} {}".format( len(vHeaderDate), vHeaderDate ) )
            #year, month, date = int(vHeaderDate[:4]), int(vHeaderDate[4:6]), int(vHeaderDate[6:])
            #print( "    vHeaderDate {}-{:02}-{:02}".format( year, month, date ) )
            #vHeader4 = versionBytes[0x56d:index]
            #print( "    vBH4 {} {}".format( len(vHeader3), hexlify(vHeader4) ) )
            #print( "  index = {:04x}={}".format( index, index ) )

            assert index == 0x590
            length = 19 # 1 length byte and 9 max characters
            strings2 = []
            while index < len(versionBytes):
                vBytes = versionBytes[index:index+length]
                #print( "  vB {} {}".format( hexlify(vBytes), vBytes ) )
                vLen, = struct.unpack( ">H", vBytes[0:2] )
                vLen = vBytes[0]
                #print( "vL2", repr(vLen) )
                vString = ''
                for j in range( int(vLen/2) ):
                    #print( vBytes[2*j+1:2*j+3] )
                    char16, = struct.unpack( "<H", vBytes[2*j+1:2*j+3] )
                    #print( char16 )
                    vString += chr( char16 )
                #vString = vBytes[2:vLen+1].decode( 'utf-16' )
                #print( "    vBl2 {}/{} {!r}".format( vLen, int(vLen/2), vString ), end='' )
                assert not vString[0].islower()
                strings2.append( vString )
                index += length
            numStrings2 = len( strings2 )
            if numStrings2 > 0: self.characterBitSize = 16
            if BibleOrgSysGlobals.debugFlag:
                print( "    {}={:04x} 16-bit capitalized common words loaded".format( numStrings2, numStrings2 ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( '     ', strings2 )
                ix = -1
                for j, word in enumerate( trings2 ):
                    if word in ( 'Genesis', 'In', 'The', 'God', ):
                        print( '      {!r} {}={:04x}'.format( word, j, j ) )

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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading dictionary characters from {}…").format( self.sourceFolder ) )
            filename = 'Tokens.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading token characters from {} {}…").format( self.sourceFolder, filename ) )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                tokenBytes = myFile.read()
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {:,} token bytes read".format( len(tokenBytes) ) )
            #print( "vB {} {}".format( len(tokenBytes), hexlify(tokenBytes[:40]) ) )
            assert tokenBytes[0] == 32
            assert tokenBytes[1] in (0,32)
            if BibleOrgSysGlobals.debugFlag:
                if self.characterBitSize == 8: assert tokenBytes[1] == 32 # Space
                elif self.characterBitSize == 16: assert tokenBytes[1] == 0
                else: halt

            index = 0
            #self.tokenBytes = []
            self.tokenString = ''
            while index < len(tokenBytes):
                if self.characterBitSize == 8:
                    token = tokenBytes[index]; index += 1
                elif self.characterBitSize == 16:
                    try: token, = struct.unpack( "<H", tokenBytes[index:index+2] ); index += 2
                    except struct.error: logging.critical( "Struct ERROR" ); break
                #print( chr(token), end=' ' )
                #self.tokenBytes.append( token )
                tokenChar = chr( token )
                self.tokenString += tokenChar
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    {:,} {}-bit token characters loaded".format( len(self.tokenString), self.characterBitSize ) )
        # end of load.loadTokenCharacters


        def loadVerseTextIndex():
            """
            Seems to have a header and then 972 3+32-byte or 3+48-byte (CEV) entry lines.
                972 * 32 = 31,104 = 31,102 verses in KJV + 2 blank at end.
            """
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading verse index info from {}…").format( self.sourceFolder ) )
            filename = 'TextNdx.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading verse text index from {} {}…").format( self.sourceFolder, filename ) )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                textIndexBytes = myFile.read()
            numTextIndexBytes = len(textIndexBytes)
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {:,} text index bytes read".format( numTextIndexBytes ) )
            #print( "tIB {} {}".format( len(textIndexBytes), hexlify(textIndexBytes[:99]) ) )
            assert numTextIndexBytes in (34055,49623,) # Divisible by 35 or 51 = 973

            key, size = textIndexBytes[0], textIndexBytes[1]
            #print( "  prelude length = {:04x} {}".format( size, size ) )
            #print( "    Key={}, line entry size={}".format( key, size ) )
            assert key == 1
            assert size in (35,51,) # 35-3=32, 51-3=48
            vTIHeader = textIndexBytes[3:size+3]
            #print( "tIB header {} {}".format( len(vTIHeader), hexlify(vTIHeader) ) )
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
                #print( '{} iE={} lastIE={} lineOffset={} total={}'.format( len(self.textIndex), iE, lastIE, lineOffset, total ) )
                assert total == lineOffset
                #print( '{:3} +{:4}={:4} {} {}'.format( len(self.textIndex), lineOffset, iE, hexlify(indexEntry), indexEntry ) )
                total = 0
                if size == 35: # One byte per entry (handles offsets in range 0..256)
                    for something in indexEntry: # KJV G
                        if something > 0:
                            total += something
                            #print( "something={} total={}".format( something, total ) ) # Each one adds another 35-145 for KJV, 20-70+ for YLT
                            pointer = total + iE
                            #print( "pointer={} lastPointer={}".format( pointer, lastPointer ) )
                            assert pointer > lastPointer
                            self.textIndex.append( pointer )
                            lastPointer = pointer
                        #else:
                            #print( "Skipped zero entry at {}".format( pointer ) )
                elif size == 51: # 1.5 bytes per entry (handles offsets in range 0..4,095 -- 256 is not enough for long verses)
                    nibbleIndex = 0
                    for nibbles in indexEntry: # KJV G
                        if nibbleIndex == 0: n1, n2 = nibbles & 0x0F, (nibbles & 0xF0) >> 4; nibbleIndex = 2
                        elif nibbleIndex == 1: n2, n3 = nibbles & 0x0F, (nibbles & 0xF0) >> 4; nibbleIndex = 3
                        elif nibbleIndex == 2: n3, n4 = nibbles & 0x0F, (nibbles & 0xF0) >> 4; nibbleIndex = 4
                        else: halt
                        if nibbleIndex >= 3:
                            something = (n3<<8) + (n2<<4) + n1
                            #print( "nibbles1 {} {:02x} {:02x} {:02x} {:02x} {:04x}".format( nibbleIndex, n1, n2, n3, n4, something ) )
                            if nibbleIndex == 3: nibbleIndex = 0
                            elif nibbleIndex == 4: n1 = n4; nibbleIndex = 1
                            #print( "nibbles2 {} {:02x} {:02x} {:02x} {:02x} {:04x}".format( nibbleIndex, n1, n2, n3, n4, something ) )
                            if something > 0:
                                total += something
                                #print( "something={} total={}".format( something, total ) ) # Each one adds another 35-145 for KJV, 20-70+ for YLT
                                pointer = total + iE
                                #print( "pointer={} lastPointer={}".format( pointer, lastPointer ) )
                                assert pointer > lastPointer
                                self.textIndex.append( pointer )
                                lastPointer = pointer
                            #else:
                                #print( "Skipped zero entry at {}".format( pointer ) )
                else: halt
                lastIE = iE
                count += 1
            assert index == numTextIndexBytes

            numTextIndexEntries = len(self.textIndex)
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    {:,} text-index entries loaded from {} lines".format( numTextIndexEntries, count ) )
            if BibleOrgSysGlobals.debugFlag:
                assert numTextIndexEntries == 31102 or self.abbreviation in ( 'Darby','Wey', 'Williams',) # Darby has 31,099 (3 less)
                print( "    Final accumulated total was {:,} (should equal length of Text.Dat)".format( total + iE ) )
                #for index in (0, 1, 2, 3, 23145, -4, -3, -2, -1 ): print( "      {}={}".format( index, self.textIndex[index] ) )
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
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( _("  Loading verse text data from {}…").format( self.sourceFolder ) )
            filename = 'Text.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )

            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading text from {} {}…").format( self.sourceFolder, filename ) )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                self.textBytes = myFile.read()
            numTextBytes = len(self.textBytes)
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {:,} text bytes read".format( numTextBytes ) )
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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading textOpt data from {}…").format( self.sourceFolder ) )
            filename = 'TextOpt.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading text opts from {} {}…").format( self.sourceFolder, filename ) )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                optBytes = myFile.read()
            if BibleOrgSysGlobals.debugFlag: print( "    {:,} optBytes bytes read".format( len(optBytes) ) )

            index = 0
            key, size, zero1, zero2 = optBytes[0], optBytes[1], optBytes[2], optBytes[3]
            if BibleOrgSysGlobals.debugFlag: print( "    TextOpt: key={} size={}".format( key, size ) )
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
                #print( "      {} {:04x} {} pointer={:04x}={}".format( len(self.optStuff1), index, hexlify(stuff), pointer, pointer ) )
                if stuff[2]!=0 or stuff[3]!=0: break # something changes here
                assert pointer > lastPointer
                if lastPointer == -1: firstPointer = pointer
                index += 4
                self.optStuff1.append( pointer )
                if len(self.optStuff1) > 1000: halt
                lastPointer = pointer
            if BibleOrgSysGlobals.debugFlag:
                print( "    {}={:04x} (seems to match number of words below) increasing 16-bit pointers (or are they bigger?) {}={:04x}..{}={:04x} loaded from {:04x} onwards".format( len(self.optStuff1), len(self.optStuff1), firstPointer, firstPointer, lastPointer, lastPointer, startIndex ) )
                for ix in (0, 1, 2, 3, -4, -3, -2, -1 ):
                    print( "      {}={:04x}={}".format( ix, self.optStuff1[ix], self.optStuff1[ix] ) )
                #print( self.optStuff1 )
                assert len(self.optStuff1) == 896

            # Load more stuff -- what does it mean?
            #print( 'index={}={:04x}'.format( index, index ) )
            assert index == 0xe04
            startIndex = index
            self.optStuff2 = []
            while True:
                stuff = optBytes[index]; index += 1
                #print( "      {} {:04x} {}".format( len(self.optStuff2), index, hexlify(stuff) ) )
                assert stuff==0 or stuff==1
                self.optStuff2.append( stuff )
                if len(self.optStuff2) >= len(self.optStuff1): break
            if BibleOrgSysGlobals.debugFlag:
                print( "    {} unknown 1-bit flags loaded from {:04x} onwards".format( len(self.optStuff2), startIndex ) )
                #print( "  index = {:04x}={}".format( index, index ) )
                #print( self.optStuff2 )
                for ix in (0, 1, 2, -2, -1 ): print( "      {}: {:02x}={!r}".format( ix, self.optStuff2[ix], self.optStuff2[ix] ) )
                assert len(self.optStuff2) == len(self.optStuff1)

            # Now load these capitalized commonish words -- how are they referenced?
            # (Don't seem to overlap with the more common capitalized words in Version.Dat)
            # Seems that ASV has 8-bit chars, but most others have 16-bit chars
            assert index == 0x1184
            startIndex = index
            self.optWords = []
            while index < len(optBytes):
                #print( "  vB {} {}".format( hexlify(vBytes), vBytes ) )
                #vLen, = struct.unpack( ">H", vBytes[0:2] )
                vLen = optBytes[index]
                #print( "vL2", repr(vLen) )
                vString = ''
                if self.characterBitSize == 8:
                    # Nine 8-bit chars filled with rubbish past the specified number
                    for j in range( vLen ):
                        #print( vBytes[2*j+1:2*j+3] )
                        char8 = optBytes[index+j+1]
                        #print( vLen, j, char8 )
                        vString += chr( char8 )
                    #print( 'vString', repr(vString) )
                    index += 10
                    assert not vString[0].islower()
                    self.optWords.append( vString )
                elif self.characterBitSize == 16:
                    # Nine 16-bit characters
                    vBytes = optBytes[index+1:index+19]
                    for j in range( int(vLen/2) ):
                        #print( vBytes[2*j+1:2*j+3] )
                        try: char16, = struct.unpack( "<H", vBytes[2*j:2*j+2] )
                        except struct.error: logging.critical( "Struct error" ); index += 999999; break
                        #print( char16 )
                        vString += chr( char16 )
                    #vString = vBytes[2:vLen+1].decode( 'utf-16' )
                    #print( "    tO {}/{} {!r}".format( vLen, int(vLen/2), vString ), end='' )
                    index += 19
                    assert not vString[0].islower()
                    self.optWords.append( vString )
            numOptWords = len( self.optWords )
            if BibleOrgSysGlobals.debugFlag:
                print( "    {}={:04x} 19-byte text-opt capitalized words loaded from {:04x} onwards".format( numOptWords, numOptWords, startIndex ) )
                print( '     ', self.optWords )
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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading cross-reference index data from {}…").format( self.sourceFolder ) )
            filename = 'XrefNdx.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading xref index from {} {}…").format( self.sourceFolder, filename ) )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                xrefIndexBytes = myFile.read()
            numXrefIndexBytes = len(xrefIndexBytes)
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {:,} xref index bytes read".format( numXrefIndexBytes ) )
            #print( "tIB {} {}".format( len(xrefIndexBytes), hexlify(xrefIndexBytes[:99]) ) )

            #header = xrefIndexBytes[0:35]
            #print( "xIB1 header {} {}".format( len(header), hexlify(header) ) )
            key, size0, size1, indexSize, tokenBlkSize = struct.unpack( "<BBBHH", xrefIndexBytes[0:7] )
            size = size0 + size1
            #print( "  prelude length = {:04x} {}".format( size, size ) )
            if BibleOrgSysGlobals.debugFlag:
                print( "    Key={}, line entry size {}+{}={} index size={} tokenBlkSize={}*2={}".format( key, size0, size1, size, indexSize, tokenBlkSize, tokenBlkSize*2 ) )
            assert key == 2
            assert size0 == 35 # 35-3=32
            assert size1 == 67 # 67-3=64
            assert size == 102
            assert indexSize == 0
            assert 90 <= tokenBlkSize <= 215 # AV=195, YLT=206, CEV=186
            index = 7
            header = xrefIndexBytes[index:size]
            if BibleOrgSysGlobals.debugFlag:
                print( "xIB2 header {} {}".format( len(header), hexlify(header) ) )
            index = size

            assert index == 102
            self.xrefIndex = []
            lastPointer = total = count = 0
            while index < numXrefIndexBytes:
                indexEntry = xrefIndexBytes[index:index+size]; index += size
                #print( '{:4} {} {} {}'.format( len(self.xrefIndex), len(indexEntry), hexlify(indexEntry), indexEntry ) )
                assert len(indexEntry) == size
                indexEntry1, indexEntry2 = indexEntry[:size0], indexEntry[size0:]
                assert len(indexEntry1)==size0 and len(indexEntry2)==size1
                # Seems part a starts with a 3-byte pointer to something
                diskPointer1 = (indexEntry1[2]<<16) + (indexEntry1[1]<<8) + indexEntry1[0]
                diskPointer2 = (indexEntry2[2]<<16) + (indexEntry2[1]<<8) + indexEntry2[0]
                assert diskPointer2 == total
                count1 = indexEntry1[3]
                if 0 and len(self.xrefIndex) < 10:
                    print( '  {} {:06x}={} {}'.format( len(self.xrefIndex), diskPointer1, diskPointer1, count1 ) )
                    print( '    a {} {} {}'.format( len(indexEntry1), hexlify(indexEntry1), indexEntry1[3:] ) )
                    print( '     {:06x}={}'.format( diskPointer2, diskPointer2 ) )
                    print( '    b {} {} {}'.format( len(indexEntry2), hexlify(indexEntry2), indexEntry2[3:] ) )
                for x in range( 32 ):
                    b1, w2 = indexEntry1[x+3], (indexEntry2[2*x+3+1]<<8) + indexEntry2[2*x+3]
                    if b1 == 0:
                        assert w2 == 0
                        break
                    #print( 'b1={:02x}={} w2={:04x}={}'.format( b1, b1, w2, w2 ) )
                    total += w2
                    self.xrefIndex.append( (b1,diskPointer2+w2) )
                #if len(self.xrefIndex) > 10: print(); halt
                count += 1
            assert index == numXrefIndexBytes
            numXrefIndexEntries = len(self.xrefIndex)
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    {:,} xref index duples loaded from {} double lines".format( numXrefIndexEntries, count ) )
            #print( self.xrefIndex )
            assert 231 <= count <= 428 # AV=417, YLT=385, CEV=338
            assert 7365 <= numXrefIndexEntries <= 13694 # AV=13,316, YLT=12,289, CEV=10,796
            #print( "    Final total was {} (should equal length of Text.Dat)".format( total + iE ) )
            #for index in range( 150 ):
                #print( "      {}: {:02x} @ {:04x}={}".format( index, self.xrefIndex[index][0], self.xrefIndex[index][1], self.xrefIndex[index][1] ) )
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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading Strongs index data from {}…").format( self.sourceFolder ) )
            filename = 'XrefNdxs.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                try: del self.StrongsIndex
                except AttributeError: pass
                return False
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading Strongs reference index from {} {}…").format( self.sourceFolder, filename ) )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                xrefIndexBytes = myFile.read()
            numXrefIndexBytes = len(xrefIndexBytes)
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    {:,} Strongs index bytes read".format( numXrefIndexBytes ) )
            #print( "tIB {} {}".format( len(xrefIndexBytes), hexlify(xrefIndexBytes[:99]) ) )

            #header = xrefIndexBytes[0:35]
            #print( "xsIB1 header {} {}".format( len(header), hexlify(header) ) )
            key, size0, size1, indexSize, tokenBlkSize = struct.unpack( "<BBBHH", xrefIndexBytes[0:7] )
            #print( "  prelude length = {:04x} {}".format( size, size ) )
            if BibleOrgSysGlobals.debugFlag:
                print( "    Key={}, line entry size {}".format( key, size0 ) )
            assert key == 1
            assert size0 == 67 # 67-3=64
            assert size1 == 0
            assert indexSize == 0
            assert tokenBlkSize == 0
            index = 7
            header = xrefIndexBytes[index:size0]
            #print( "xIB2 header {} {}".format( len(header), hexlify(header) ) )
            for something in header: assert something == 0 # It's just filler
            index = size0

            assert index == 67
            self.StrongsIndex = []
            lastPointer = total = count = 0
            while index < numXrefIndexBytes:
                indexEntry = xrefIndexBytes[index:index+size0]; index += size0
                #print( '{:4} {} {} {}'.format( len(self.xrefIndex), len(indexEntry), hexlify(indexEntry), indexEntry ) )
                assert len(indexEntry) == size0
                # Seems part a starts with a 3-byte pointer to something
                diskPointer = (indexEntry[2]<<16) + (indexEntry[1]<<8) + indexEntry[0]
                if total == 0: total = diskPointer # Starts part way through
                assert diskPointer == total
                if 0 and len(self.xrefIndex) < 10:
                    print( '  {} {:06x}={}'.format( len(self.xrefIndex), diskPointer, diskPointer ) )
                    print( '    {} {} {}'.format( len(indexEntry), hexlify(indexEntry), indexEntry[3:] ) )
                for x in range( 32 ):
                    w2 = (indexEntry[2*x+3+1]<<8) + indexEntry[2*x+3]
                    #print( '    {} w2={:04x}={} @ {}'.format( x, w2, w2, len(self.StrongsIndex) ) )
                    if w2 == 0 and len(self.StrongsIndex)>8849: break
                    total += w2
                    self.StrongsIndex.append( (total) )
                #if len(self.xrefIndex) > 10: print(); halt
                count += 1
            assert index == numXrefIndexBytes
            numStrongsIndexEntries = len(self.StrongsIndex)
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    {:,} Strongs index entries loaded from {} lines".format( numStrongsIndexEntries, count ) )
            if BibleOrgSysGlobals.debugFlag:
                #print( self.StrongsIndex )
                assert count == 277
                assert numStrongsIndexEntries == 8850
                #print( "    Final total was {} (should equal length of Text.Dat)".format( total + iE ) )
                for index in (0, 1, 2, 3, -4, -3, -2, -1 ): print( "      {}={}".format( index, self.StrongsIndex[index] ) )
        # end of load.loadStrongsIndex


        def loadXrefData():
            """
            0.6-1.1MB
            """
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading cross-reference data from {}…").format( self.sourceFolder ) )
            filename = 'Xref.Dat'
            filepath = os.path.join( self.sourceFolder, filename )
            if not os.access( filepath, os.R_OK ):
                filename = filename.lower() # Some modules (e.g., WEBSTER) seem to have lower case names for some files
                filepath = os.path.join( self.sourceFolder, filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading xref data from {} {}…").format( self.sourceFolder, filename ) )
            with open( filepath, 'rb' ) as myFile: # Automatically closes the file when done
                self.xrefBytes = myFile.read()
            numXrefBytes = len(self.xrefBytes)
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {:,} xref bytes read".format( numXrefBytes ) )
            if BibleOrgSysGlobals.debugFlag:
                if 'StrongsIndex' in self.__dict__: assert numXrefBytes == self.StrongsIndex[-1]
                else: # Not all versions have Strongs
                    print( "lastXref", self.xrefIndex[-1], self.xrefIndex[-2] )
                    # XXXXX Why does this fail for CEVUK?
                    if self.abbreviation not in ('ASV', 'AKJV', 'CEVUK', 'Darby', 'KJ21', 'Webster', 'Wey', 'Williams', ):
                        assert numXrefBytes == self.xrefIndex[-1][1]

            if 0:
                lastPointer = 0
                for j, pointer in enumerate( self.textIndex ):
                    strip = self.xrefBytes[lastPointer:pointer]
                    print( "{:5} {:5} {:5} {} {}".format( j, lastPointer, pointer, hexlify(strip), strip ) )
                    lastPointer = pointer
                    if j > 10: break
        # end of load.loadXrefData


        def createDictionary():
            """
            """
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Creating dictionary…") )
            self.dictionary = {}

            # Put the short common words into the dictionary
            startWordIndex = 5
            wordIndex = startWordIndex
            for word in self.commonWords: # These are ALL capitalized!
                if word not in ('I','Israel','Jesus','Jehovah'):
                    word = word.lower() # Not sure what I don't understand here
                self.dictionary[wordIndex] = (word,None)
                wordIndex += 1
            #print( 'wi', wordIndex )
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                print( '    {:,} common words added to dictionary from {} to {}={:02x}'.format( len(self.commonWords), startWordIndex, wordIndex-1, wordIndex-1 ) )
            assert wordIndex == 128
            del self.commonWords

            # Add in the compressed words
            tokenIndex = 0
            startWordIndex = 257
            wordIndex = startWordIndex
            word = ''
            for bitCodes, xrefPointer in self.xrefIndex:
                #print( 'tI={} wI={} bc={:02x} p={:04x}'.format( tokenIndex, wordIndex, bitCodes, xrefPointer ) )
                commonChars, addChars = bitCodes >> 5, bitCodes & 0x1f
                #print( 'eW={!r} cc={} {!r} ac={} {!r}'.format( word, commonChars, word[:commonChars], addChars, self.tokenString[tokenIndex:tokenIndex+addChars] ) )
                word = word[:commonChars] + self.tokenString[tokenIndex:tokenIndex+addChars]
                #print( repr(word) )
                self.dictionary[wordIndex] = (word,xrefPointer)
                tokenIndex += addChars
                wordIndex += 1
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                print( '    {:,} regular words added to dictionary from {}={:02x} to {:,}={:04x}'.format( len(self.xrefIndex), startWordIndex, startWordIndex, wordIndex-1, wordIndex-1 ) )
            del self.xrefIndex

            if 0 and self.haveStrongsFlag:
                startWordIndex = self.StrongsOffset
                wordIndex = startWordIndex
                for j, xrefPointer in enumerate( self.StrongsIndex ):
                    assert j < 14298
                    word = '\\str {}\\str*'.format( j )
                    self.dictionary[wordIndex] = (word,xrefPointer)
                    wordIndex += 1
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "    {:,} Strongs' numbers added to dictionary from {:,}={:04x} to {:,}={:02x}".format( len(self.StrongsIndex), startWordIndex, startWordIndex, wordIndex-1, wordIndex-1 ) )
        # end of load.createDictionary


        def getVerseBytes( absoluteVerseNumber ):
            """
            Given a verse number from 0..31,101, return the encoded bytes
            """
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "getVerseBytes( {} {} ) = {}".format( self.abbreviation, absoluteVerseNumber, BOS.convertAbsoluteVerseNumber( absoluteVerseNumber+1 ) ) )
                #assert 0 <= absoluteVerseNumber < len(self.textIndex)
            startAt = 0 if absoluteVerseNumber==0 else self.textIndex[absoluteVerseNumber-1]
            endAt = self.textIndex[absoluteVerseNumber]
            assert endAt > startAt
            byteStrip = self.textBytes[startAt:endAt]
            #print( 'Verse {} {} {} {}'.format( absoluteVerseNumber, len(byteStrip), hexlify(byteStrip), byteStrip[-1] ) )
            return byteStrip
        #end of load.getVerseBytes


        #self.missingWordNumbers = set()
        def getWord( wordIndex, capsFlag ):
            """
            """
            if BibleOrgSysGlobals.debugFlag:
                #print( "getWord( {}={:04x} )".format( wordIndex, wordIndex ) )
                assert 5 <= wordIndex <= 0x7FFF

            if self.haveStrongsFlag and wordIndex >= self.StrongsOffset:
                return '\\str {}\\str*'.format( wordIndex - self.StrongsOffset )

            try: dictionaryWord = self.dictionary[wordIndex][0] #+ '({})'.format( self.dictionary[wordIndex][1] )
            except KeyError:
                dictionaryWord = '«{:04x}»'.format( wordIndex )
                if BibleOrgSysGlobals.debugFlag:
                    print( '{} missing word {:04x} -- have {}={:04x} words'.format( self.abbreviation, wordIndex, len(self.dictionary), len(self.dictionary) ) )
                    #self.missingWordNumbers.add( wordIndex )

            return dictionaryWord.title() if capsFlag else dictionaryWord
        #end of load.getWord


        def findWordInDictionary( searchWord ):
            """
            A diagnostic reverse dictionary lookup.
            """
            if BibleOrgSysGlobals.debugFlag:
                print( "findWordInDictionary( {!r} )".format( searchWord ) )

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
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "getBibleText( {} ) {} {}".format( hexlify(verseBytes), self.abbreviation, reference ) )
            resultString = ''
            capsFlag = footnoteFlag = headingFlag = False
            saved = None
            for something in verseBytes:
                #print( 'a {:02x} {} {} {!r}'.format( something, saved, capsFlag, resultString ) )
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
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                assert not capsFlag # Should be off at the end of the verse
                assert not footnoteFlag # Should be off at the end of the verse
                assert not headingFlag # Should be off at the end of the verse

            # Now scan for open and close fields
            #if reference==('SA2','23','8'): print( reference, repr(resultString) ); halt
            for openCode,newOpenCode,closeCode,newCloseCode in ( ('\x1c','STARTC','\x1c','ENDC'),
                                                                ('\x1e','STARTE','\x1e','ENDE'),
                                                                ('\x1f','STARTF','\x1f','ENDF'),
                                                                ('[','\\add',']','\\add*'),
                                                                #('\\\\  #','\\xt','\\\\',''),
                                                                ):
                ix = resultString.find( openCode )
                while ix != -1:
                    #print( '{} {!r}->{!r} {!r}->{!r} in {!r}'.format( ix, openCode,newOpenCode,closeCode,newCloseCode, resultString ) )
                    resultString = resultString.replace( openCode, newOpenCode, 1 )
                    ixEnd = resultString.find( closeCode, ix )
                    if ixEnd == -1:
                        #print( 'Missing {!r} close code'.format( closeCode ) )
                        pass
                    else:
                        resultString = resultString.replace( closeCode, newCloseCode, 1 )
                    ix = resultString.find( openCode, ix )
                if resultString.find( closeCode, ix ) != -1:
                    print( 'Unexpected {!r} close code'.format( closeCode )  ); halt
            #if BibleOrgSysGlobals.debugFlag: # final check
                #print( reference, repr(resultString), resultString )
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
                #print( repr(resultString) )
                assert '  ' not in resultString

            return resultString.strip()
        #end of load.getBibleText


        def getStrongsBytes( StrongsNumber ):
            """
            The StrongsNumber must be in the range 1..8,850.

            Strongs printed numbers are Hebrew 1..8,674 plus Greek 1..5,624 = total = 14,298
            """
            if BibleOrgSysGlobals.debugFlag:
                #print( "getStrongsBytes( {} )".format( StrongsNumber ) )
                assert 1 <= StrongsNumber <= 8850
            startAt = self.StrongsIndex[StrongsNumber-1]
            endAt = startAt + 120
            #try: endAt = self.StrongsIndex[StrongsNumber]
            #except IndexError: endAt = startAt + 999
            assert endAt > startAt
            byteStrip = self.xrefBytes[startAt:endAt]
            #print( StrongsNumber, startAt, endAt, byteStrip )
            #print( 'Strongs {} {} {} {!r}'.format( StrongsNumber, len(byteStrip), hexlify(byteStrip), byteStrip ) )
            return byteStrip
        # end of getStrongsBytes


        def loadBooks():
            """
            """
            if BibleOrgSysGlobals.verbosityLevel > 1: print( 'Loading books…' )

            bookCount = 0
            currentBBB = None
            for n in range( 31102 ):
                BCVRef = BOS.convertAbsoluteVerseNumber( n+1 )
                BBB, C, V = BCVRef
                if BBB != currentBBB:
                    if currentBBB is not None: # Save the last book
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", BBB, bookCount+1 )
                        self.stashBook( thisBook )
                    # Create the new book
                    if BibleOrgSysGlobals.verbosityLevel > 2:  print( '  Loading {}…'.format( BBB ) )
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
                    logging.warning( "No verse information for {} {} {}:{}".format( self.abbreviation, BBB, C, V ) )

            if currentBBB is not None: # Save the very last book
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", BBB, bookCount+1 )
                self.stashBook( thisBook )
        # end of load.loadBooks


        def test():
            """
            """
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( '\nDEBUG TEST:' )

            if 1:
                for n in ( 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 123, 23144, 23145, 23146, 31101, ):
                    BCVRef = BOS.convertAbsoluteVerseNumber( n+1 )
                    try:
                        verseStuff = getVerseBytes( n )
                        #print( "\n{} {} = {} {} {}".format( self.abbreviation, BCVRef, len(verseStuff), hexlify(verseStuff), verseStuff ) )
                        verseString = getBibleText( verseStuff, BCVRef )
                        print( "\n{} {} {} = {}".format( self.abbreviation, n, BCVRef, repr(verseString) ) )
                        if 0:
                            for j in range( int( len(verseStuff)/2 ) ):
                                w2 = (verseStuff[2*j+1]<<8) + verseStuff[2*j]
                                print( '   {} {:04x}={} {!r}'.format( j, w2, w2, self.tokenString[w2:w2+3] ) )
                    except IndexError:
                        print( "No such verse: {} {} {}".format( self.abbreviation, n, BCVRef ) )

            if 0:
                for n in range( 31102 ):
                    BCVRef = BOS.convertAbsoluteVerseNumber( n+1 )
                    try:
                        verseString = getBibleText( getVerseBytes( n ), BCVRef )
                        printFlag = False
                        for something in ('<<000', '<<01', '<<02', '<<031', '<<032', '<<033', '<<034', ):
                            if something in verseString: printFlag = True
                        if printFlag or debuggingThisModule:
                            print( "\n{} {} {} = {!r}".format( self.abbreviation, n, BCVRef, verseString ) )
                            if '<<020' in verseString: halt
                            #if '<<62' in verseString: halt
                        #if BCVRef == ('GEN','20','2'): halt
                    except IndexError:
                        print( "No such verse: {} {} {}".format( self.abbreviation, n, BCVRef ) )

            if 1 and self.haveStrongsFlag:
                for word in ( 'from', 'the', 'same' ):
                    print( '{!r} -> {}'.format( word, findWordInDictionary( word ) ) )
                for strongs in ( 7225, 430, 1254, 853, 8064, 1, 2, 8849, 8850 ):
                    xrefStuff = getStrongsBytes( strongs )
                    print( "\nStrongs {} = {} {} {}".format( strongs, len(xrefStuff), hexlify(xrefStuff), xrefStuff ) )
                    print( "         {} = {!r}".format( strongs, getBibleText( xrefStuff ) ) )

            #if self.missingWordNumbers:
                #print( 'missingWordNumbers', sorted(self.missingWordNumbers) ); halt
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
            for vbh in VBH1s: print( '{:10} = {} {}'.format( vbh, len(VBH1s[vbh]), VBH1s[vbh] ) )
            for vbh in VBH2s: print( '{:10} = {} {}'.format( vbh, len(VBH2s[vbh]), VBH2s[vbh] ) )
            for vbh in VBH3s: print( '{:10} = {} {}'.format( vbh, len(VBH3s[vbh]), VBH3s[vbh] ) )
            halt

        self.doPostLoadProcessing()
    # end of PierceOnlineBible.load
# end of PierceOnlineBible class



def testOB( TOBfilename ):
    # Crudely demonstrate the Online Bible class
    from BibleOrgSys.Reference import VerseReferences
    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/' )

    TOBfolder = os.path.join( testFolder, TOBfilename+'/' )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the Online Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( TOBfolder, TOBfilename ) )
    olb = PierceOnlineBible( TOBfolder )
    olb.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( olb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        olb.check()
        #print( UsfmB.books['GEN']._processedLines[0:40] )
        olbErrors = olb.getErrors()
        # print( olbErrors )
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
        #print( svk, olb.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = olb.getVerseText( svk )
            fullVerseText = olb.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( reference, shortText, verseText )
            if BibleOrgSysGlobals.debugFlag: print( '  {}'.format( fullVerseText ) )
# end of testOB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = PierceOnlineBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Online TestA1", result1 )
        result2 = PierceOnlineBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Online TestA2", result2 )
        result3 = PierceOnlineBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Online TestA3", result3 )

        testSubfolder = os.path.join( testFolder, 'AV/' )
        result3 = PierceOnlineBibleFileCheck( testSubfolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Online TestB1", result3 )
        result4 = PierceOnlineBibleFileCheck( testSubfolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Online TestB2", result4 )
        result5 = PierceOnlineBibleFileCheck( testSubfolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Online TestB3", result5 )


    if 0: # specified module
        singleModule = 'AV'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nOnline C/ Trying {}".format( singleModule ) )
        #myTestFolder = os.path.join( testFolder, singleModule+'/' )
        #testFilepath = os.path.join( testFolder, singleModule+'/', singleModule+'_utf8.txt' )
        testOB( singleModule )

    if 0: # specified modules
        good = ('AV','ASV','AKJV','CEVUK','Darby','KJ21','RWebster','WEBSTER','Wey','Williams','YLT',) # 'MART_1707',
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nOnline D{}/ Trying {}".format( j+1, testFilename ) )
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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testOB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nOnline E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testOB( someFolder )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of PierceOnlineBible.py
