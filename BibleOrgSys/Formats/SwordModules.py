#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SwordModules.py
#
# Module handling Sword modules directly
#
# Copyright (C) 2012-2020 Robert Hunt
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
Module directly handling content modules produced for Crosswire Sword.
It does not use the Sword engine -- see SwordResources.py for that.
(The advantage of this module is that there are less installation complications.)

This code does not include a Sword module installer.
That is in SwordInstallManager.py
Alternatively, you can use a program like Xiphos to install the Sword modules on your system.
Also our Biblelator provides a SwordManager (GUI) that's a front end for SwordInstallManager.

Caching is not yet implemented.

This implementation is a prototype and intended for machines with large memory resources --
    bo optimizations have been attempted yet!

Contains four classes:
    1/ SwordModuleConfiguration
        Loads a .conf file
    2/ SwordModule
        Loads a Sword module
    3/ SwordBibleModule (based on a SwordModule and a Bible)
        Loads a Sword module that has Chapter/Verse divisions
    4/ SwordModules
        Loads all the .conf files it can find
        Then loads the collection of SwordModules and/or SwordBibleModules.

TODO: Do we want to replace 'replace' with something more helpful (e.g., 'backslashreplace' or 'namereplace') ???
TODO: I think this entire module is very messy and needs to be completely rewritten! ???
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-01-05' # by RJH
SHORT_PROGRAM_NAME = "SwordModules"
PROGRAM_NAME = "Sword module handler"
PROGRAM_VERSION = '0.49'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging, time
import multiprocessing
import struct, zlib

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
#from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys.Internals.InternalBible import OT39_BOOKLIST, NT27_BOOKLIST
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
from BibleOrgSys.Online.SwordInstallManager import processConfLines, ALL_SWORD_CONF_FIELD_NAMES, \
                                    TECHNICAL_SWORD_CONF_FIELD_NAMES, DEFAULT_SWORD_CONF_ENCODING



# Folders where to try looking for modules
#   These should be the folders that contain mods.d and modules folders inside them
DEFAULT_SWORD_SEARCH_FOLDERS = ( '/usr/share/sword/',
                        os.path.join( os.path.expanduser('~'), '.sword/'),
                        'C:\\Users\\{}\\AppData\\Roaming\\Sword\\'.format( os.getlogin() ),
                        'C:\\Users\\{}\\AppData\\Local\\VirtualStore\\Program Files\\BPBible\\resources\\'.format( os.getlogin() ),
                        'C:\\Program Files\\BPBible\\resources\\', 'C:\\Program Files (x86)\\BPBible\\resources\\',
                        'TestData/', )
SwordSearchFolders = list( DEFAULT_SWORD_SEARCH_FOLDERS )


GENERIC_SWORD_MODULE_TYPE_NAMES = { 'RawText':'Biblical Texts', 'zText':'Biblical Texts',
                'RawCom':'Commentaries', 'RawCom4':'Commentaries', 'zCom':'Commentaries',
                'RawLD':'Lexicons / Dictionaries', 'RawLD4':'Lexicons / Dictionaries', 'zLD':'Lexicons / Dictionaries',
                'RawGenBook':'Generic Books',
                'RawFiles':'Commentaries' }



class SwordModuleConfiguration:
    """
    A class that loads, processes, and stores a Sword .conf file.
    """
    def __init__( self, moduleAbbreviation, swordFolder ):
        """
        Create the config object.

        Looks in loadFolder (should be the sword folder that contains the mods.d and modules folders)
            and attempts to load moduleAbbreviation.conf.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModuleConfiguration.__init__( {!r}, {} )".format( moduleAbbreviation, swordFolder ) )

        # Set our defaults
        self.abbreviation = moduleAbbreviation # a string like 'ylt'
        self.swordFolder = swordFolder
        self.encoding = DEFAULT_SWORD_CONF_ENCODING # seems to be the default

        # Things we'll fill up later when we load the data
        self.name = self.modType = self.modCategory = self.locked = None
        self.confDict = {}
    # end of SwordModuleConfiguration.__init__


    def loadConf( self ):
        """
        Load the Sword module conf file into a dictionary.

        Also sets:
            self.name (from […name…] entry)
            self.modType (from ModDrv entry)
            self.modCategory (from ModDrv, Category, Features entries)
            self.encoding (from Encoding entry)
            self.locked (from CipherKey)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModuleConfiguration.loadConf()" )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  Loading Sword config file for {}…".format( self.abbreviation ) )
        filename = self.abbreviation + '.conf'
        self.confPath = os.path.join( self.swordFolder, 'mods.d/', filename )
        self.confDict = {}
        #lastLine, lineCount, continuationFlag, result = None, 0, False, []
        if not os.path.exists( self.confPath) and filename.lower()!=filename: # Try a lower case
            logging.info( "loadConf: Trying {!r} instead of {!r}".format( filename.lower(), filename ) )
            self.confPath = os.path.join( self.swordFolder, 'mods.d/', filename.lower() )
        with open( self.confPath, 'rt', encoding=DEFAULT_SWORD_CONF_ENCODING ) as myFile: # Automatically closes the file when done
            processConfLines( self.abbreviation, myFile, self.confDict )
        #print( self.confDict )

        # Fix known module bugs or inconsistencies
        if 'BlockType' in self.confDict and self.confDict['BlockType'] == 'Book': # Fix an inconsistency (in at least the Clarke commentary)
            self.confDict['BlockType'] = 'BOOK'
        if 'ModDrv' in self.confDict:
            if self.confDict['ModDrv'] == 'ztext': # Fix an inconsistency (in at least the CzeB21 Bible)
                self.confDict['ModDrv'] = 'zText'
            elif self.confDict['ModDrv'] == 'zld': # Fix an inconsistency (in at least FreDAW dictionary)
                self.confDict['ModDrv'] = 'zLD'

        # Tidy things up
        if 'Name' in self.confDict: self.name = self.confDict['Name']
        else:
            logging.error( _("Missing '[…name…]' line at beginning of {} conf file").format( self.abbreviation ) )
            self.name = self.abbreviation
        if 'ModDrv' in self.confDict:
            self.modType = self.confDict['ModDrv']
            if self.modType in ('RawText','zText',): self.modCategory = 'Bible' # versified
            elif self.modType in ('RawCom','RawCom4','zCom',): self.modCategory = 'Commentary' # versified
            elif self.modType in ('RawLD','RawLD4','zLD',): self.modCategory = 'Dictionary'
            elif self.modType in ('RawGenBook','RawFiles',): self.modCategory = 'General'
            else: logging.critical( "Unclassified {!r} module type".format( self.modType ) )
        else:
            logging.critical( _("Missing 'ModDrv=' line in {} conf file").format( self.abbreviation ) )
        if 'Encoding' in self.confDict:
            #print( self.confDict['Encoding']); halt
            assert self.confDict['Encoding'] in ('UTF-8',)
            #self.encoding = 'utf-8' # override the default
            if self.abbreviation in ('ab','barnes','navelinked','dandettebiblen',): self.encoding = 'iso-8859-15' # Not sure how/why they got this wrong!

        # See if we have any new fields
        for key in self.confDict:
            if key not in ALL_SWORD_CONF_FIELD_NAMES:
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "SwordModuleConfiguration.loadConf: Unexpected {} {!r} Sword conf key ({})" \
                                            .format( self.abbreviation, key, self.confDict[key] ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

        # See if we have to inform the user about anything
        if 'Font' in self.confDict and BibleOrgSysGlobals.debugFlag: logging.warning( "This program does not load {!r} font yet.".format( self.confDict['Font'] ) )

        # Checked for locked modules
        if 'CipherKey' in self.confDict:
            if self.confDict['CipherKey']:
                if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "SwordModuleConfiguration: {} {} module is unlocked!".format( self.name, self.modCategory ) )
                self.locked = False
            else:
                if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "SwordModuleConfiguration: {} {} module is locked!".format( self.name, self.modCategory ) )
                self.locked = True

        # Check we got everything we should have
        assert self.name
        if self.name != 'Globals': # special case
            assert self.modType
            assert self.modCategory
    # end of SwordModuleConfiguration.loadConf


    def __str__( self ):
        """
        This method returns the string representation of a Sword module configuration object.

        @return: the name of a Sword object formatted as a string
        @rtype: string
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModuleConfiguration.__str__()" )

        result = "SwordModuleConfiguration for {}".format( self.abbreviation )
        #if self.abbreviation: result += ('\n' if result else '') + "  " + _("Abbreviation: ") + self.abbreviation
        if self.swordFolder: result += ('\n' if result else '') + "  " + _("Folder: {}").format( self.swordFolder )
        for key,value in self.confDict.items():
            adjKey = "LCSH (Library of Congress Subject Headings)" if key=="LCSH" else key
            if key == "History":
                result += ('\n' if result else '') + "      " + _("History:")
                #print( "value", repr(value) )
                if not isinstance( value, list ): value = [value]
                for something in value:
                    if isinstance( something, tuple ): version,historyDescription = something
                    elif BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        logging.error( "SwordModuleConfiguration: Got a malformed History string: {!r}".format( something ) )
                        if BibleOrgSysGlobals.strictCheckingFlag: halt
                    result += ('\n' if result else '') + "        {}: {}".format( version, historyDescription )
            elif key not in TECHNICAL_SWORD_CONF_FIELD_NAMES or BibleOrgSysGlobals.verbosityLevel > 2: # Don't bother printing some of the technical keys
                result += ('\n' if result else '') + "      {}: {}".format( adjKey, value )
        return result
    # end of SwordModuleConfiguration:__str__


    def get( self, fieldName ):
        """
        Return the value for fieldname (str) if it's in the configDict (loading from the Sword module .conf file).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModuleConfiguration.get( {} )".format( fieldName ) )

        if fieldName in self.confDict: return self.confDict[fieldName]
    # end of SwordModuleConfiguration.get
# end of SwordModuleConfiguration



class SwordModule():
    """
    Class to load and manipulate a Sword module.
    """

    def __init__( self, loadedSwordModuleConfiguration ):
        """
        Create the Sword Module object.
        """
        # Stored the preloading configuration stuff
        self.SwordModuleConfiguration = loadedSwordModuleConfiguration
        #if BibleOrgSysGlobals.debugFlag:
            #print( self.SwordModuleConfiguration.modCategory )
            #assert self.SwordModuleConfiguration.modCategory not in ('Bible','Commentary' ) # Fails for calls from subclass
        self.name = self.SwordModuleConfiguration.name

        # Memory tuning parameters
        self.inMemoryFlag = None # Load module parameter will set this to True or False
        self.autoMemoryMaxSize = 40000 # If module is less than this size (40K), we'll load it into memory (set to None to disable)

        # Things we'll fill up later when we load the data
        self.versifiedFlag = None # Set to true if we have book,chapter,verse structuring
        self.dataFilepath = None # Can be a string or a list of strings (indexed in self.swordIndex below)
        # For the following, key is BBB if versified, else it's an UPPER-CASE word or title
        self.swordIndex = {} # Used only if the inMemoryFlag is False
        self.cache = {} # Only used if the inMemoryFlag is False
        self.swordData = {} # Used only if the inMemoryFlag is True
        self.store = None # After load(), points to either self.swordIndex or self.swordData

        # Look how big our data is
        if self.autoMemoryMaxSize and not self.inMemoryFlag:
            if 'InstallSize' in self.SwordModuleConfiguration.confDict:
                installSize = int( self.SwordModuleConfiguration.confDict['InstallSize'] )
                if installSize <= self.autoMemoryMaxSize:
                    self.inMemoryFlag = True
                    if BibleOrgSysGlobals.verbosityLevel > 1: print( "    Autoloading small ({}) module into memory".format( installSize ) )
                elif BibleOrgSysGlobals.verbosityLevel > 3: print( "    Module is too large ({}) for autoloading into memory (>{})".format( installSize, self.autoMemoryMaxSize ) )
            elif BibleOrgSysGlobals.verbosityLevel > 3: print( "    " + _("Module not autoloaded into memory because no InstallSize specified") )
    # end of SwordModule.__init__


    def getName( self ):
        return self.SwordModuleConfiguration.name


    def loadRawLD( self ):
        """
        Load an uncompressed lexicon / dictionary type module.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.loadRawLD()" )

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading {} from {}…".format( self.SwordModuleConfiguration.modCategory, self.dataFolder ) )
        assert self.SwordModuleConfiguration.modType in ('RawLD','RawLD4',)
        assert self.SwordModuleConfiguration.modCategory in ('Dictionary',)
        assert 'CompressType' not in self.SwordModuleConfiguration.confDict
        lengthsize = 4 if self.SwordModuleConfiguration.modType=='RawLD4' else 2
        # Load the index file
        ldData = []
        with open( os.path.join( self.dataFolder, self.filename+'.idx' ), 'rb') as indexFile:
            while True:
                binaryBlock = indexFile.read( 4+lengthsize) # Offset size is always 4
                if not binaryBlock: break # at the end of the file
                offset, length = struct.unpack( 'ii' if self.SwordModuleConfiguration.modType=='RawLD4' else 'ih', binaryBlock )
                ldData.append( (offset, length) )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} index entries read".format( len(ldData), 'map' if 'Category' in self.SwordModuleConfiguration.confDict and self.SwordModuleConfiguration.confDict['Category']=='Maps' else 'dictionary' ) )
        # Load the data file
        self.dataFilepath = os.path.join( self.dataFolder, self.filename+'.dat' )
        with open( self.dataFilepath, 'rt', encoding=self.SwordModuleConfiguration.encoding ) as textFile:
            for j, (offset, length) in enumerate(ldData):
                if length:
                    #print( j, offset, length )
                    textFile.seek( offset )
                    chunk = textFile.read( length )
                    chunks = chunk.split( '\n', 1 )
                    assert len(chunks) == 2
                    key, entry = chunks[0].strip().upper(), chunks[1].strip() # Remove unwanted trailing CR/LF chars and make keys UPPER CASE only
                    if key and key[-1]=='\\': key = key[:-1]
                    if self.SwordModuleConfiguration.abbreviation in ('greekhebrew','hebrewgreek','strongsgreek','strongsrealgreek','strongshebrew','strongsrealhebrew',):
                        if len(key)==5 and key.isdigit():
                            #print( "adjusting", key )
                            if self.SwordModuleConfiguration.abbreviation in ('greekhebrew','strongsgreek','strongsrealgreek',): key = 'G' + key
                            elif self.SwordModuleConfiguration.abbreviation in ('hebrewgreek','strongshebrew','strongsrealhebrew',): key = 'H' + key
                        elif BibleOrgSysGlobals.debugFlag: print( "not adjusting", key )
                    if not self.inMemoryFlag: entry = (offset+chunk.index(entry),len(entry),) # Store the reference, not the actual information
                    if key in self.store: # we've encountered a duplicate
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "      Found duplicate {!r} key in {}".format( key, self.SwordModuleConfiguration.name ) )
                        try: self.store[key].append( entry )
                        except AttributeError: self.store[key] = [self.store[key], entry ]
                    else: self.store[key] = entry # Most keys only occur once
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} entries read".format( len(self.store), 'map' if 'Category' in self.SwordModuleConfiguration.confDict and self.SwordModuleConfiguration.confDict['Category']=='Maps' else 'dictionary' ) )
        if 'Category' in self.SwordModuleConfiguration.confDict and self.SwordModuleConfiguration.confDict['Category']=='Maps':
            print( "We should really be storing these {} maps somewhere else!".format( self.SwordModuleConfiguration.name ) )
        self.expandLD()
    # end of SwordModule.loadRawLD


    def decompressChunk( self, compressedChunk ):
        """
        Decrypt if necessary, and then decompress (using zlib) a chunk of a work.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( "SwordModule.decompressChunk( … )" )


        # The following decryption code is adapted from sapphire.cpp -- the Saphire II stream cipher class.
        #    Dedicated to the Public Domain the author and inventor:
        #    (Michael Paul Johnson).  This code comes with no warranty. Use it at your own risk.
        #    Ported from the Pascal implementation of the Sapphire Stream Cipher 9 December 1994.
        #    Added hash pre- and post-processing 27 December 1994.
        #    Modified initialization to make index variables key dependent,
        #    made the output function more resistant to cryptanalysis, and renamed to Sapphire II 2 January 1995
        # Global decryption variables
        cards = bytearray( 256 )
        rotor = ratchet = avalanche = lastPlain = lastCipher = 0

        #def hashInit():
        #    nonlocal cards, rotor, ratchet, avalanche, lastPlain, lastCipher
        #    rotor, ratchet, avalanche, lastPlain, lastCipher = 1, 3, 5, 7, 11
        #    for j,k in zip( range(0,256), range(255,-1,-1) ): cards[j] = k # Start with cards all in inverse order
        ## end of hashInit

        def keyRand( limit, userKey, keySize, rsum, keyPos ):
            #assert 0 <= keySize < 256
            #assert 0 <= rsum < 256
            #assert 0 <= keyPos < keySize
            if not limit: return 0, rsum, keyPos # Avoid divide by zero error
            retryLimiter, mask = 0, 1
            while mask < limit:
                mask = (mask << 1) + 1
            while True:
                rsum = (cards[rsum] + userKey[keyPos]) & 0xFF
                keyPos += 1
                if keyPos >= keySize:
                    keyPos = 0 # Recycle the user key
                    rsum = (rsum + keySize) & 0xFF # key "aaaa" != key "aaaaaaaa"
                u = mask & rsum
                retryLimiter += 1
                if retryLimiter > 11: u %= limit # Prevent very rare long loops
                if u <= limit: break
            return u, rsum, keyPos
        # end of keyRand

        def initialize( key ):
            nonlocal cards, rotor, ratchet, avalanche, lastPlain, lastCipher
            # Key size may be up to 256 bytes.
            # Pass phrases may be used directly, with longer length compensating for the low entropy expected in such keys.
            # Alternatively, shorter keys hashed from a pass phrase or generated randomly may be used.
            # For random keys, lengths of from 4 to 16 bytes are recommended, depending on how secure you want this to be.
            if not key: hashInit(); return # If we have been given no key, assume the default hash setup
            cards = bytearray( range( 256 ) ) # Start with cards all in order -- one of each
            #print( len(cards), cards ); halt
            # Swap the card at each position with some other card
            keyPos = rsum = 0
            for j in range( 255, -1, -1 ):
                toSwap, rsum, keyPos = keyRand( j, key, len(key), rsum, keyPos )
                cards[j], cards[toSwap] = cards[toSwap], cards[j] # Note the j might equal toSwap
            # Initialise the indices and data dependencies
            #   Indices are set to different values instead of all zero to reduce what is
            #     known about the state of the cards when the first byte is emitted.
            rotor, ratchet, avalanche, lastPlain, lastCipher = cards[1], cards[3], cards[5], cards[7], cards[rsum]
        # end of initialize

        def decryptByte( thisByte ):
            nonlocal cards, rotor, ratchet, avalanche, lastPlain, lastCipher
            # Shuffle the deck a little more
            ratchet = (ratchet + cards[rotor]) & 0xFF
            rotor = (rotor + 1) & 0xFF
            swapTemp = cards[lastCipher]
            cards[lastCipher] = cards[ratchet]
            cards[ratchet] = cards[lastPlain]
            cards[lastPlain] = cards[rotor]
            cards[rotor] = swapTemp
            avalanche = (avalanche + cards[swapTemp]) & 0xFF
            # Output one byte from the state in such a way as to make it
            #   very hard to figure out which one you are looking at
            lastPlain = thisByte ^ cards[(cards[ratchet]+cards[rotor]) & 0xFF] \
                                 ^ cards[cards[(cards[lastPlain] + cards[lastCipher] + cards[avalanche]) & 0xFF]]
            #assert 0 <= lastPlain < 256
            lastCipher = thisByte
            return lastPlain
        # end of decryptByte

        def decryptBlock( thisBytes, keyStr ):
            initialize( str.encode( keyStr ) )
            result = bytearray()
            for thisByte in thisBytes:
                result.append( decryptByte( thisByte ) )
            return result
        # end of decryptBlock

        if 'CipherKey' in self.SwordModuleConfiguration.confDict and self.SwordModuleConfiguration.confDict['CipherKey']:
            compressedChunk = decryptBlock( compressedChunk, self.SwordModuleConfiguration.confDict['CipherKey'] )
        return zlib.decompress( compressedChunk )
    # end of SwordModule.decompressChunk


    def loadCompressedLD( self ):
        """
        Load a compressed lexicon / dictionary type module.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.loadCompressedLD()" )

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading compressed {} from {}…".format( self.SwordModuleConfiguration.modCategory, self.dataFolder ) )
        assert self.SwordModuleConfiguration.modType in ('zLD',)
        assert self.SwordModuleConfiguration.modCategory in ('Dictionary',)
        assert 'CompressType' in self.SwordModuleConfiguration.confDict
        count, idxData = 0, []
        filepath = os.path.join( self.dataFolder, self.filename+'.idx' )
        if os.path.isfile( filepath ):
            with open( filepath, 'rb') as indexFile:
                while True:
                    count += 1
                    binary8 = indexFile.read(8)
                    if not binary8: break # at the end of the file
                    offset, mixedEntryLength = struct.unpack( "II", binary8 )
                    #print( count, 'is', offset, mixedEntryLength )
                    idxData.append( (offset, mixedEntryLength) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} index pointer entries read".format( len(idxData), self.SwordModuleConfiguration.modCategory ) )
        else:
            logging.critical( "Oops, cannot find {} for {} module".format( filepath, self.SwordModuleConfiguration.name ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            return
        if idxData:
            blankCount, LDIndex = 0, {}
            byteCount = 0
            #min1 = min2 = 9999999
            #max1 = max2 = 0
            with open( os.path.join( self.dataFolder, self.filename+'.dat' ), 'rb') as mixedIndexFile:
                for j, (offset, mixedEntryLength) in enumerate(idxData):
                    if mixedEntryLength:
                        mixedIndexFile.seek( offset )
                        mixedChunk = mixedIndexFile.read( mixedEntryLength )
                        #print( j, offset, mixedEntryLength, mixedChunk )
                        stringBit, binaryBit = mixedChunk[:-10], mixedChunk[-8:] # There's a variable length string, then a CRLF, then eight bytes of data
                        #print( stringBit, binaryBit )
                        assert len(binaryBit) == 8
                        blockNumber, blockChunkNumber = struct.unpack( 'II', binaryBit )
                        indexString = stringBit.decode( self.SwordModuleConfiguration.encoding )
                        #if indexString[0]=='N': print( indexString )
                        #print( "'"+indexString+"'", blockNumber, blockChunkNumber )
                        #print( "chunk is", "'"+chunk+"'" )
                        #if blockNumber==2: print( blockNumber, blockChunkNumber )
                        #if j>50: halt
                        if indexString in LDIndex:
                            try: LDIndex[indexString].append( (blockNumber,blockChunkNumber,) ) # it's already a list
                            except AttributeError: LDIndex[indexString] = [LDIndex[indexString], (blockNumber,blockChunkNumber,)] # Start a new list with two entries
                        else: LDIndex[indexString] = (blockNumber,blockChunkNumber,)
                        #if blockNumber<min1: min1=blockNumber
                        #if blockNumber>max1: max1=blockNumber
                        #if blockChunkNumber<min2: min2=blockChunkNumber
                        #if blockChunkNumber>max2: max2=blockChunkNumber
                    else:
                        blankCount += 1
                        chunk = ''
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} index entries read{}".format( len(LDIndex), self.SwordModuleConfiguration.modCategory, " ({} were blank)".format(blankCount) if blankCount else '' ) )
            #print( "    ", min1, max1, min2, max2 )
            assert blankCount == 0
            #for test in ("A","ABRAHAM","DAVID",):
            #    print( test, LDIndex[test] )
        if idxData and LDIndex:
            count, dataIndex = 0, []
            filepath = os.path.join( self.dataFolder, self.filename+'.zdx' )
            with open( filepath, 'rb') as indexFile:
                while True:
                    count += 1
                    binary8 = indexFile.read(8)
                    if not binary8: break # at the end of the file
                    offset, compressedLength = struct.unpack( "II", binary8 )
                    #print( count, 'is', offset, compressedLength )
                    dataIndex.append( (offset, compressedLength) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} block index entries read".format( len(dataIndex), self.SwordModuleConfiguration.modCategory ) )
        if idxData and LDIndex and dataIndex:
            blankCount, LDStuffList = 0, []
            byteCount = 0
            if self.inMemoryFlag:
                with open( os.path.join( self.dataFolder, self.filename+'.zdt' ), 'rb') as compressedTextFile:
                    for j, (offset, compressedLength) in enumerate(dataIndex):
                        strings = []
                        if compressedLength:
                            compressedTextFile.seek( offset )
                            compressedChunk = compressedTextFile.read( compressedLength )
                            byteCount += compressedLength
                            uncompressedChunk = self.decompressChunk( compressedChunk )
                            thisCount, = struct.unpack( 'I', uncompressedChunk[0:4])
                            ix = 4
                            for c in range(0, thisCount):
                                offset3, length3 = struct.unpack( 'II', uncompressedChunk[ix:ix+8] )
                                ix += 8
                                thisUncompressedChunk = uncompressedChunk[offset3:offset3+length3-1] # We don't want the NULL on the end
                                try:
                                    thisString = thisUncompressedChunk.decode( self.SwordModuleConfiguration.encoding )
                                except KeyError:
                                    for key, (blockNumber, blockChunkNumber) in LDIndex.items(): # By a slow loop, find the key which points to this entry
                                        if blockNumber==j and blockChunkNumber==c: thisKey = key; break
                                    logging.warning( "Unable to properly decode {} {} {} {} chunk for {}".format( self.SwordModuleConfiguration.encoding, self.SwordModuleConfiguration.name, j, c, thisKey ) )
                                    if BibleOrgSysGlobals.debugFlag: print( "  ", thisUncompressedChunk[:40] )
                                    thisString = thisUncompressedChunk.decode( self.SwordModuleConfiguration.encoding, 'replace' )
                                assert isinstance( thisString, str )
                                strings.append( thisString )
                        else:
                            blankCount += 1
                        LDStuffList.append( strings )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "    {} compressed {} blocks read{}".format( len(LDStuffList), self.SwordModuleConfiguration.modCategory, " ({} were blank)".format(blankCount) if blankCount else '' ) )
                assert blankCount == 0
                # Now save the lexicon/dictionary data in an easily accessible format
                for key, value in LDIndex.items():
                    # print( f"key='{key}' value={value}" )
                    if isinstance( value, list ): # This key has two entries
                        for j, (blockNumber, blockChunkNumber) in enumerate(value):
                            try:
                                chunk = LDStuffList[blockNumber][blockChunkNumber]
                            except IndexError:
                                logging.error( "Compressed {} {} skipped non-existing chunk {} / {} for {!r}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, blockNumber, len(LDStuffList), key ) )
                                chunk = ''
                            adjKey = f'{key} ({j+1})' if key in self.swordData else key
                            if adjKey in self.swordData:
                                logging.critical( "About to overwrite data in {} for {}".format( self.SwordModuleConfiguration.name, adjKey ) )
                                #print( j, key, adjKey, '\n', self.swordData[key] if key in self.swordData else None, '\n', self.swordData[adjKey], '\n', chunk ); halt
                            assert isinstance( chunk, str )
                            self.swordData[adjKey] = chunk
                            #print( "   ", adjKey, "->", chunk )
                    else:
                        blockNumber, blockChunkNumber = value
                        #if blockNumber==311: print( "Converted blocknumber" ); blockNumber = 'what?' # Special code for isbe commentary
                        #print( key, blockNumber, blockChunkNumber )
                        #if blockNumber>=len(LDStuffList): print( "Why is blockNumber {} too big for {}".format( blockNumber, len(LDStuffList) ) )
                        #elif blockChunkNumber>=len(LDStuffList[blockNumber]): print( "Why is blockChunkNumber {} too big for {}".format( blockChunkNumber, len(LDStuffList[blockNumber]) ) )
                        try:
                            chunk = LDStuffList[blockNumber][blockChunkNumber]
                            assert isinstance( chunk, str )
                            adjKey = f'{key} ({j+1})' if key in self.swordData else key
                            if adjKey in self.swordData:
                                logging.critical( "About to overwrite data in {} for {}".format( self.SwordModuleConfiguration.name, adjKey ) )
                                # print( j, key, adjKey, '\n', self.swordData[key] if key in self.swordData else None, '\n', self.swordData[adjKey], '\n', chunk ); halt
                            self.swordData[adjKey] = chunk.strip()
                            # print( "   ", adjKey, "->", chunk )
                        except IndexError:
                            logging.error( "Compressed {} {} skipped non-existing chunk {} / {} for {!r}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, blockNumber, blockChunkNumber, key ) )
            else: # we're just loading the index, not the data
                self.dataFilepath = os.path.join( self.dataFolder, self.filename+'.zdt' )
                #print( "\nLDIndex", len(LDIndex), LDIndex )
                #print( "\ndataIndex", len(dataIndex), dataIndex )
                for j, (key, value) in enumerate(LDIndex.items()):
                    #print( "jkv", j, key, value )
                    if isinstance( value, list ): # This key has two entries
                        for k, (blockNumber, blockChunkNumber) in enumerate(value):
                            #print( "knc", k, blockNumber, blockChunkNumber )
                            try:
                                stuff = dataIndex[blockNumber]
                                entry = (stuff[0], stuff[1], blockNumber, blockChunkNumber,)
                                #try:
                                adjKey = "{} ({})".format( key, k+1 ) if key in self.swordIndex else key
                                if adjKey in self.swordIndex:
                                    print( "About to overwrite data in {} for {}".format( self.SwordModuleConfiguration.name, key ) )
                                    #print( j, key, adjKey, '\n', self.swordData[key] if key in self.swordData else None, '\n', self.swordData[adjKey], '\n', chunk ); halt
                                self.swordIndex[adjKey] = entry
                            except IndexError:
                                logging.error( "YYCompressed {} {} skipped non-existing entry {} / {} for {!r}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, blockNumber, blockChunkNumber, key ) )
                    else:
                        blockNumber, blockChunkNumber = value
                        #if self.SwordModuleConfiguration.abbreviation == 'invstrongsrealgreek': print( self.SwordModuleConfiguration.abbreviation, j, key, value, blockNumber, blockChunkNumber, len(dataIndex), len(LDIndex) )
                        try:
                            stuff = dataIndex[blockNumber]
                            entry = (stuff[0], stuff[1], blockNumber, blockChunkNumber,)
                            adjKey = f'{key} ({j+1})' if key in self.swordData else key
                            if adjKey in self.swordIndex:
                                logging.critical( "About to overwrite data in {} for {}".format( self.SwordModuleConfiguration.name, adjKey ) )
                                # print( j, key, adjKey, '\n', self.swordData[key] if key in self.swordData else None, '\n', self.swordData[adjKey], '\n', chunk ); halt
                            self.swordIndex[adjKey] = entry
                        except IndexError:
                            logging.error( "Compressed {} {} skipped non-existing chunk {} / {} for {!r}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, blockNumber, blockChunkNumber, key ) )
        self.expandLD()
    # end of SwordModule.loadCompressedLD


    def expandLD( self ):
        """
        Expand a lexicon / dictionary.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.expandLD()" )

        # Make cross-references
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Auto-adding cross-references for {} {}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory ) )
        assert self.store
        newKeys = {}
        for key,data in self.store.items():
            if ';' in key:
                bits = key.split( ';' )
                for bit in bits:
                    newKey = bit.strip()
                    if newKey in self.store:
                        #print( "Went to add {} (from {!r}) but it was already there".format( newKey, key ) )
                        pass
                    elif newKey in newKeys:
                        #print( "Went to add {} (from {!r}) but already added it".format( newKey, key ) )
                        oldEntry = newKeys[newKey][:-13] # Remove the ' (auto-added)' bit from the end
                        #print( "'"+oldEntry+"'" )
                        newEntry = "{} or '{!r}' (auto-added)".format( oldEntry, key ) # Use a double single-quote '' so looks not too terrible but can be parsed again later
                        newKeys[newKey] = newEntry
                    else:
                        newKeys[newKey] = "See '{!r}' (auto-added)".format( key )
                        #print( "Auto-added: {} -> {}".format( newKey, newKeys[newKey] ) )
            elif ' ' in key or ',' in key or '-' in key:
                for j, char in enumerate(key):
                    if char in ( ' ,-' ): break
                #if j==0 or j==len(key)-1: print( "'"+key+"'", j )
                newKey = key[:j]
                if newKey in self.store:
                    #print( "Went to add {} (from {!r}) but it was already there".format( newKey, key ) )
                    pass
                elif newKey in newKeys:
                    #print( "Went to add {} (from {!r}) but already added it".format( newKey, key ) )
                    oldEntry = newKeys[newKey][:-13] # Remove the ' (auto-added)' bit from the end
                    #print( "'"+oldEntry+"'" )
                    newEntry = "{} or '{!r}' (auto-added)".format( oldEntry, key )
                    newKeys[newKey] = newEntry
                else:
                    newKeys[newKey] = "See '{!r}' (auto-added)".format( key )
                    #print( "Auto-added: {} -> {}".format( newKey, newKeys[newKey] ) )
        for key in newKeys:
            assert key not in self.store
            self.store[key] = newKeys[key] # Add the new keys
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "    {} new cross-reference keys added to lexicon / dictionary".format( len(newKeys) ) )
    # end of SwordModule.expandLD


    def loadRawGenBook( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.loadRawGenBook()" )

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading raw general book from {}…".format( self.dataFolder ) )
        assert 'CompressType' not in self.SwordModuleConfiguration.confDict
        count, gbIndexIndex = 0, []
        filepath = os.path.join( self.dataFolder, self.filename+'.idx' )
        if os.path.isfile( filepath ):
            with open( filepath, 'rb') as indexFile:
                while True:
                    count += 1
                    binary4 = indexFile.read(4)
                    if not binary4: break # at the end of the file
                    indexOffset, = struct.unpack( "I", binary4 )
                    gbIndexIndex.append( indexOffset )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} genbook index pointer entries read".format( len(gbIndexIndex), self.SwordModuleConfiguration.name ) )
        else:
            logging.critical( "Oops, cannot find {} for {} module".format( filepath, self.SwordModuleConfiguration.name ) )
            return
        if gbIndexIndex:
            blankCount, gbIndex = 0, {}
            with open( os.path.join( self.dataFolder, self.filename+'.dat' ), 'rb') as dataFile:
                for j, indexOffset in enumerate(gbIndexIndex):
                    #print( j, indexOffset )
                    dataFile.seek( indexOffset )
                    chunk = dataFile.read( 210 ) # 150 wasn't enough
                    #print( j, chunk )
                    num1, num2, num3 = struct.unpack( "iii", chunk[:12] )
                    #print( j, num1, num2, num3 )
                    if j == 0:
                        assert num1 == -1
                        assert num3 == 4 # Not sure what this means
                    else:
                        if 'Category' in self.SwordModuleConfiguration.confDict and self.SwordModuleConfiguration.confDict['Category']=='Maps':
                            assert num1==0 or num1>=4 # Mostly 0, but else divisible by 4
                            assert num3==-1 or num3>=8 # Mostly -1, but else divisible by 4
                        else: # Not maps
                            assert num1==0 or num1>=4 or num1==-1 # 0 or divisible by 4 or -1
                            assert num3==-1 or num3>=8 # -1 or divisible by 4
                    ix = chunk[12:].find( b'\x00' )
                    something = chunk[12:12+ix]
                    endbit, num4, offset, length = b'', -1, -1, -1 # defaults that don't usually occur
                    if something != b'':
                        try:
                            indexString = something.decode( self.SwordModuleConfiguration.encoding )
                        except KeyError:
                            logging.warning( "Unable to properly decode {} {} {} chunk #{} {}->{}".format( self.SwordModuleConfiguration.encoding, self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, j, offset, length ) )
                            if BibleOrgSysGlobals.debugFlag: print( "  ", uncompressedChunk[:40] )
                            indexString = something.decode( self.SwordModuleConfiguration.encoding, 'replace' )
                        #if len(indexString)>100: print( j, "indexString = ", indexString )
                        endbit = chunk[12+ix+1:12+ix+10+1]
                        assert len(endbit) == 10 # Can occur if the buffer length above is too short
                        #print( "endbit", endbit )
                        num4, = struct.unpack( "h", endbit[:2] )
                        #print( j, "num4 =", num4 )
                        if num4 == 8:
                            offset, length = struct.unpack( "ii", endbit[2:] )
                            #num4, offseta, offsetb, lengtha, lengthb = struct.unpack( "h Hh Hh", endbit ) # To get over a Python bug
                            #offset = offsetb*256 + offseta
                            #length = lengthb*256 + lengtha
                            assert offset >= 0
                            assert length >= 0
                        elif num4 == 0:
                            if BibleOrgSysGlobals.verbosityLevel > 0:
                                print( "What does num4==0 mean?" )
                            offset = length = None
                        else:
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        #print( j, "num4 =", num4, "offset = ", offset, "length =", length )
                    else: indexString = ''
                    #print( j, chunk, ix, endbit )
                    #print( j, "num1 =", num1, "num2 =", num2, "num3 =", num3, "'"+indexString+"'", "num4 =", num4, "offset =", offset, "length =", length ) # What do these other numbers mean?
                    if indexString: gbIndex[indexString] = (num1, num2, num3, num4, offset, length,) # ignore the first one
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} genbook index entries read".format( len(gbIndex), self.SwordModuleConfiguration.name ) )
            if gbIndex: # Load the data file
                if self.inMemoryFlag:
                    with open( os.path.join( self.dataFolder, self.filename+'.bdt' ), 'rt', encoding=self.SwordModuleConfiguration.encoding ) as textFile:
                        for j, key in enumerate(gbIndex):
                            num1, num2, num3, num4, offset, length = gbIndex[key]
                            #print( key, num1, num2, num3, num4 ) # usually num1==0 for map, num1==1280 for others, num2 is div by 4, num3==-1 num4==8
                            if num4 == 8:
                                textFile.seek( offset )
                                entry = textFile.read( length ).strip()
                                #print( entry )
                                if 0: # Save this processing for later
                                    if entry.startswith( key ): entry = entry[len(key):] # Remove the key since we've already got that
                                    entry = entry.lstrip() # Remove spurious CRLFs
                                    if entry.startswith( "<br />"): entry = entry[6:]
                                    entry = entry.strip() # Remove spurious CRLFs
                                    assert entry.startswith( '<img src="/' ) and entry.endswith( '"/>' )
                                    entry = entry[11:-3] # Should now be a relative filename
                                    print( entry )
                                    filepath = os.path.join( self.dataFolder, entry )
                                    print( filepath )
                                    assert os.path.isfile( filepath )
                                adjKey = key.upper()
                                if adjKey in self.swordData: # This is a duplicate
                                    if BibleOrgSysGlobals.verbosityLevel > 1: print( "      Found duplicate genbook {!r} (from {!r}) key in {}".format( adjKey, key, self.SwordModuleConfiguration.name ) )
                                    try: self.swordData[adjKey].append( entry )
                                    except KeyError: self.swordData[adjKey] = [self.swordData[adjKey], entry ]
                                else: self.swordData[adjKey] = entry # Most keys only occur once
                            elif BibleOrgSysGlobals.verbosityLevel > 0:
                                print( "What does num4==0 mean here?" )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} genbook entries loaded".format( len(self.swordData) ) )
                else: # we just need to load the index
                    self.dataFilepath = os.path.join( self.dataFolder, self.filename+'.bdt' )
                    for j, key in enumerate(gbIndex):
                        num1, num2, num3, num4, offset, length = gbIndex[key]
                        #print( key, num1, num2, num3, num4 ) # usually num1==0 for map, num1==1280 for others, num2 is div by 4, num3==-1 num4==8
                        entry = offset, length
                        if num4 == 8:
                            adjKey = key.upper()
                            if adjKey in self.swordIndex: # This is a duplicate
                                if BibleOrgSysGlobals.verbosityLevel > 1: print( "      Found duplicate genbook {!r} (from {!r}) key in {}".format( adjKey, key, self.SwordModuleConfiguration.name ) )
                                try: self.swordIndex[adjKey].append( entry )
                                except AttributeError: self.swordIndex[adjKey] = [self.swordIndex[adjKey], entry ]
                            else: self.swordIndex[adjKey] = entry # Most keys only occur once
                        elif BibleOrgSysGlobals.verbosityLevel > 0:
                            print( "What does num4==0 mean here?" )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} genbook index entries loaded".format( len(self.swordIndex) ) )
    # end of SwordModule.loadRawGenBook


    def createChapterOffsets( self, versificationString ):
        """
        Create a list of chapter offsets (organised by book) to allow direct access to the chapter information.

        Each entry consists of a 3-tuple:
            0: OTNTOffset = offset if 39 OT books and 27 NT books included
            1: OTOffset = offset if only 39 OT books included
            2: NTOffset = offset if only 27 NT books included
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.createChapterOffsets( {} )".format( versificationString ) )

        # Now build an index for each book:
        #   0 is the work header
        #   1 is the first book intro
        #   2 is the first chapter header
        #   3 is the first verse in the first chapter, etc.
        #
        # The offsets are stored by BBB, then by chapter (starting with 0) and then you add the verse number less 1

        # Setup filled containers for the object
        # TODO: Create a separate mapping table for these versification systems
        if versificationString == 'KJV': BOSname = 'GENERIC-KJV-80'
        elif versificationString == 'KJVA': BOSname = 'GENERIC-KJV-80'
        elif versificationString == 'NRSV': BOSname = 'GENERIC-NRSV-80'
        elif versificationString == 'MT': BOSname = 'GENERIC-Original-80'
        elif versificationString == 'Vulg': BOSname = 'GENERIC-Vulgate-82'
        elif versificationString == 'Synodal': BOSname = 'GENERIC-Synodal-80'
        elif versificationString == 'SynodalProt': BOSname = 'GENERIC-Synodal-80'
        elif versificationString == 'Catholic': BOSname = 'GENERIC-Catholic-80'
        elif versificationString == 'Catholic2': BOSname = 'GENERIC-CatholicEsther16-80'
        elif versificationString == 'German': BOSname = 'GENERIC-German-80'
        elif versificationString == 'Leningrad': BOSname = 'GENERIC-Leningrad-80'
        elif versificationString == 'LXX': BOSname = 'LXX'
        else:
            logging.critical( _("Unknown {!r} versification scheme for {}").format( versificationString, self.SwordModuleConfiguration.abbreviation ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        self.BibleOrgSystem = BibleOrganisationalSystem( BOSname )

        # Setup containers that we will fill
        self.chapterOffsets = {}
        self.OTIndex, self.NTIndex = [], []

        # Default to KJV versification
        self.OTList = OT39_BOOKLIST
        assert len(self.OTList) == 39
        self.NTList = NT27_BOOKLIST
        assert len(self.NTList) == 27
        if 'Versification' in self.SwordModuleConfiguration.confDict:
            if self.SwordModuleConfiguration.confDict['Versification'] == 'KJVA':
                self.OTList = self.OTList + ('GES','LES','TOB','JDT','ESA','WIS','SIR','BAR','PAZ','SUS','BEL','MAN','MA1','MA2',)
                assert len(self.OTList) == 53
            elif self.SwordModuleConfiguration.confDict['Versification'] == 'Vulg':
                self.OTList = ( 'GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', 'SA1', 'SA2', 'KI1', 'KI2', 'CH1', 'CH2', \
                            'EZR', 'NEH', 'TOB', 'JDT', 'EST', 'JOB', 'PSA', 'PRO', 'ECC', 'SNG', 'WIS', 'SIR', \
                            'ISA', 'JER', 'LAM', 'BAR', 'EZE', 'DAN', 'HOS', 'JOL', 'AMO', 'OBA', \
                            'JNA', 'MIC', 'NAH', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL', 'MA1', 'MA2' )
                assert len(self.OTList) == 46
                self.NTList = self.NTList + ('MAN','GES','LES','PS2','LAO',)
                assert len(self.NTList) == 32
            elif self.SwordModuleConfiguration.confDict['Versification'] == 'Rahlfs':
                self.OTList = ( 'GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JSA', 'JGB', 'RUT', 'SA1', 'SA2', 'KI1', 'KI2', \
                            'CH1', 'CH2', 'EZR', 'NEH', 'TOB', 'JDT', 'EST', 'JOB', 'PSA', 'PRO', 'ECC', 'SNG', \
                            'WIS', 'SIR', 'ISA', 'JER', 'LAM', 'BAR', 'EZE', 'DAN', 'HOS', 'JOL', 'AMO', 'OBA', \
                            'JNA', 'MIC', 'NAH', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL', 'MA1', 'MA2' )
                assert len(self.OTList) == 46

        # Do the OT
        NTOffset = None
        OTOffset = 1+1 # Allow for heading of work
        self.OTIndex.append( ('FRT','0','0',) ); self.OTIndex.append( ('FRT','0','0',) )

        for BBB in self.OTList:
            #print("BOSname", BOSname, "BBB", BBB )
            bookVerseList = self.BibleOrgSystem.getNumVersesList( BBB, allowAlternatives=True ) # Note: BBB might get substituted!!!
            OTOffset += 1 # Allow for heading of book
            #self.OTIndex.append( (BBB,'0','0',) )
            chapterOffsets = [(OTOffset,OTOffset,NTOffset,)] # Entry #0 is for the book introduction
            lastNumVerses = 0
            C = 0
            for numVerses in bookVerseList: # step through each chapter
                self.OTIndex.append( (BBB,str(C),'0',) )
                OTOffset += 1 + lastNumVerses # 1 is for the chapter entry
                chapterOffsets.append( (OTOffset,OTOffset,NTOffset,) )
                for v in range(1,lastNumVerses+1):
                    self.OTIndex.append( (BBB,str(C),str(v),) )
                C += 1
                lastNumVerses = numVerses
            self.OTIndex.append( (BBB,str(C),'0',) )
            for v in range(1,lastNumVerses+1):
                self.OTIndex.append( (BBB,str(C),str(v),) )
            OTOffset += lastNumVerses
            self.chapterOffsets[BBB] = chapterOffsets
        #for j, (BBB,C,V,) in enumerate(self.OTIndex):
        #    if BBB=='MAL': print( j, BBB, C, V )

        # Do the NT
        OTNTOffset = OTOffset + 1+1 # Allow for heading of work
        NTOffset = 1+1 # Allow for heading of work
        OTOffset = None
        self.NTIndex.append( ('FRT','0','0',) ); self.NTIndex.append( ('FRT','0','0',) )
        for BBB in self.NTList:
            bookVerseList = self.BibleOrgSystem.getNumVersesList( BBB, allowAlternatives=True )
            OTNTOffset += 1 # Allow for heading of book
            NTOffset += 1 # Allow for heading of book
            chapterOffsets = [(OTNTOffset,OTOffset,NTOffset,)] # Entry #0 is for the book introduction
            lastNumVerses = 0
            C = 0
            for numVerses in bookVerseList: # step through each chapter
                self.NTIndex.append( (BBB,str(C),'0',) )
                OTNTOffset += 1 + lastNumVerses # 1 is for the chapter entry
                NTOffset += 1 + lastNumVerses # 1 is for the chapter entry
                chapterOffsets.append( (OTNTOffset,OTOffset,NTOffset,) )
                for v in range(1,lastNumVerses+1):
                    self.NTIndex.append( (BBB,str(C),str(v),) )
                C += 1
                lastNumVerses = numVerses
            self.NTIndex.append( (BBB,str(C),'0',) )
            for v in range(1,lastNumVerses+1):
                self.NTIndex.append( (BBB,str(C),str(v),) )
            OTNTOffset += lastNumVerses
            NTOffset += lastNumVerses
            self.chapterOffsets[BBB] = chapterOffsets
        #for j, (BBB,C,V,) in enumerate(self.NTIndex):
        #    if BBB=='REV': print( j, BBB, C, V )
        #print( "OTNTOffset", OTNTOffset, len(self.chapterOffsets) )
    # end of SwordModule.createChapterOffsets


    def loadVersifiedBibleData( self, requestedBBB=None ):
        """
        Loads data from a Sword module that is structured into chapters and verses.

        Can load either one or all (if requestedBBB=None) books.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.loadVersifiedBibleData( {} ) with {}".format( requestedBBB, self.inMemoryFlag ) )
            assert self.SwordModuleConfiguration.modType in ('RawText','zText','RawCom','RawCom4','zCom','RawFiles',)
            assert self.SwordModuleConfiguration.modCategory in ('Bible','Commentary','General',)

        self.versifiedFlag = True
        #if 'Versification' in self.SwordModuleConfiguration.confDict and self.SwordModuleConfiguration.confDict['Versification']!='KJV':
            #print( "Versification:", self.SwordModuleConfiguration.confDict['Versification'] )
        self.createChapterOffsets( self.SwordModuleConfiguration.confDict['Versification'] if 'Versification' in self.SwordModuleConfiguration.confDict else 'KJV' )
        processTestaments = (('ot','OT',),('nt','NT',),)

        if requestedBBB:
            if requestedBBB not in self.chapterOffsets:
                logging.critical( "No data available for {} book {}".format( self.SwordModuleConfiguration.name, requestedBBB ) )
                return
            # Find the book offset
            #print( "cOs", len(self.chapterOffsets), self.chapterOffsets ) # A dictionary for each BBB containing a list of 3-tuples (length = numChapters + 1)
            #print( "book cOs", len(self.chapterOffsets[requestedBBB]), self.chapterOffsets[requestedBBB] ) # A 3-tuples (length = numChapters + 1)
            #print( "OTIndex", len(self.OTIndex), self.OTIndex ) # A list of 3-tuples of all possible BBB,C,V combinations
            #print( "NTIndex", len(self.NTIndex), self.NTIndex )
            processTestaments = (('ot','OT',),) if requestedBBB in self.OTList else (('nt','NT',),)

        if 'CompressType' in self.SwordModuleConfiguration.confDict:
            assert self.SwordModuleConfiguration.confDict['CompressType'] in ('ZIP',) # LZSS not tested yet with zlib
            if self.SwordModuleConfiguration.confDict['BlockType'] == 'BOOK':
                unit, letter = 'book', 'b'
            elif self.SwordModuleConfiguration.confDict['BlockType'] == 'CHAPTER':
                unit, letter = 'chapter', 'c'
                if self.SwordModuleConfiguration.abbreviation in ('byz','tr','whnu',): letter = 'b' # Seems like a module bug
            else:
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

            totalIdxCount = 0
            for testament,Testament in processTestaments: # load OT then NT files
                idxCount, bookData = 0, []
                bookIndexFilepath = os.path.join( self.dataFolder, "{}.{}zs".format( testament, letter ) )
                if os.path.isfile( bookIndexFilepath ):
                    with open( bookIndexFilepath, 'rb') as indexFile1: # These are book index entries
                        while True:
                            idxCount += 1
                            binary12 = indexFile1.read(12)
                            if not binary12: break # at the end of the file
                            blockOffset, compressedLength, uncompressedLength = struct.unpack( "III", binary12 )
                            #if count==1 and bookNum!=0:
                            #    print( "Seem to be lacking booknum zero for {}".format( self.SwordModuleConfiguration.name ) ) # This will mess up our indexing
                            #    vssData.append( (0, 0, 0) )
                            bookData.append( (blockOffset, compressedLength, uncompressedLength) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} {} book index entries read".format( len(bookData), Testament, self.SwordModuleConfiguration.modCategory ) )
                    #assert len(bookData) == 1+39
                    totalIdxCount += idxCount
                logging.info( "No {} data available for {} module".format( Testament, self.SwordModuleConfiguration.name ) )
                if bookData:
                    count, vssData = 0, []
                    verseIndexFilepath = os.path.join( self.dataFolder, "{}.{}zv".format( testament, letter ) ) # These are verse index entries
                    minBN, maxBN = 99999, -1
                    with open( verseIndexFilepath, 'rb') as indexFile2:
                        while True:
                            count += 1
                            binary10 = indexFile2.read(10)
                            if not binary10: break # at the end of the file
                            blockNumber, verseOffset, verseLength = struct.unpack( "iih", binary10 ) # Book block number sometimes starts at 0, 1 is usually Genesis for OT
                            if blockNumber < minBN: minBN = blockNumber
                            if blockNumber > maxBN: maxBN = blockNumber
                            vssData.append( (blockNumber, verseOffset, verseLength) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} {} verse index entries read".format( len(vssData), Testament, self.SwordModuleConfiguration.modCategory ) )
                    #print( self.SwordModuleConfiguration.abbreviation, testament, minBN, maxBN )
                    #self.SwordModuleConfiguration.confDict['MinimumBlockNumber'] = minBN
                    #self.SwordModuleConfiguration.confDict['MaximumBlockNumber'] = maxBN
                    assert minBN == 0
                    if 0 and self.SwordModuleConfiguration.confDict['BlockType'] == 'CHAPTER':
                        if self.SwordModuleConfiguration.abbreviation == 'barnes':
                            assert maxBN <= (0 if testament=='ot' else 259) # What is all this extra stuff???
                        elif self.SwordModuleConfiguration.abbreviation == 'calvincommentaries':
                            assert maxBN <= (795 if testament=='ot' else 438)
                        elif self.SwordModuleConfiguration.abbreviation == 'clarke':
                            assert maxBN <= (928 if testament=='ot' else 259)
                        elif self.SwordModuleConfiguration.abbreviation == 'dutkant':
                            assert maxBN <= (926 if testament=='ot' else 259)
                        elif self.SwordModuleConfiguration.abbreviation == 'gerelb1871':
                            assert maxBN <= (134864294 if testament=='ot' else 134864294) # Massive!!! I wonder if this is -1 or something???
                        elif self.SwordModuleConfiguration.abbreviation == 'jfb':
                            assert maxBN <= (968 if testament=='ot' else 282)
                        elif self.SwordModuleConfiguration.abbreviation == 'kd':
                            assert maxBN <= (54 if testament=='ot' else 27)
                        elif self.SwordModuleConfiguration.abbreviation == 'kretzmann':
                            assert maxBN <= (965 if testament=='ot' else 287)
                        elif self.SwordModuleConfiguration.abbreviation == 'luther':
                            assert maxBN <= (122 if testament=='ot' else 122)
                        elif self.SwordModuleConfiguration.abbreviation == 'lxx':
                            assert maxBN <= (928 if testament=='ot' else 0)
                        elif self.SwordModuleConfiguration.abbreviation == 'mhc':
                            assert maxBN <= (967 if testament=='ot' else 286)
                        elif self.SwordModuleConfiguration.abbreviation == 'netnotes':
                            assert maxBN <= (920 if testament=='ot' else 27)
                        elif self.SwordModuleConfiguration.abbreviation == 'netnotesfree':
                            assert maxBN <= (920 if testament=='ot' else 259)
                        elif self.SwordModuleConfiguration.abbreviation == 'rwp':
                            assert maxBN <= (286 if testament=='ot' else 286)
                        elif self.SwordModuleConfiguration.abbreviation == 'scofield':
                            assert maxBN <= (38 if testament=='ot' else 134546869)
                        elif self.SwordModuleConfiguration.abbreviation == 'tdavid':
                            assert maxBN <= (150 if testament=='ot' else 0)
                        elif self.SwordModuleConfiguration.abbreviation == 'vulgate_clem':
                            assert maxBN <= (44 if testament=='ot' else 26)
                    if vssData:
                        blankCount = 0
                        lastBBB = None
                        thisBookCVData = {}
                        filepath = os.path.join( self.dataFolder, "{}.{}zz".format( testament, letter ) )
                        if self.inMemoryFlag:
                            blockStuff = []
                            byteCount = 0
                            with open( filepath, 'rb') as compressedTextFile: # This is the compressed verse data (in book size chunks)
                                for j, (blockOffset, compressedLength, uncompressedLength) in enumerate(bookData):
                                    #print( Testament, j, blockOffset, compressedLength, uncompressedLength )
                                    if compressedLength:
                                        compressedTextFile.seek( blockOffset )
                                        compressedChunk = compressedTextFile.read( compressedLength )
                                        byteCount += compressedLength
                                        #try:
                                        uncompressedChunk = self.decompressChunk( compressedChunk )
                                        #except:
                                        #    logging.error( "Unable to decompress {} {} {} {} chunk #{} {}->{}".format( self.SwordModuleConfiguration.name, Testament, self.SwordModuleConfiguration.modCategory, unit, j, compressedLength, uncompressedLength ) )
                                        #    uncompressedLength, uncompressedChunk = 0, b''
                                        assert len(uncompressedChunk) == uncompressedLength
                                        try:
                                            chunk = uncompressedChunk.decode( self.SwordModuleConfiguration.encoding )
                                            #if testament=='nt' and j>250: print( '\n', j, chunk )
                                        except KeyError:
                                            logging.warning( "Unable to properly decode {} {} {} {} {} chunk #{} {}->{}".format( self.SwordModuleConfiguration.encoding, self.SwordModuleConfiguration.name, Testament, self.SwordModuleConfiguration.modCategory, unit, j, compressedLength, uncompressedLength ) )
                                            if BibleOrgSysGlobals.debugFlag: print( "  ", uncompressedChunk[:40] )
                                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                                            chunk = uncompressedChunk.decode( self.SwordModuleConfiguration.encoding, 'replace' )
                                            #print( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.encoding, chunk )
                                    else:
                                        blankCount += 1
                                        chunk = ''
                                    blockStuff.append( chunk )
                            assert blankCount == 0
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} {} book entries read{}".format( len(blockStuff), Testament, self.SwordModuleConfiguration.modCategory, " ({} were blank)".format(blankCount) if blankCount else '' ) )
                            blankCount = 0
                            for k, (blockNumber,verseOffset,verseLength,) in enumerate(vssData):
                                ref = self.convertOTIndexToReference( k ) if testament=='ot' else self.convertNTIndexToReference( k )
                                #print( k, verseOffset, verseLength, ref )
                                assert ref is not None
                                BBB, C, V = ref
                                if BBB != lastBBB: # we're on to a new book
                                    if thisBookCVData:
                                        self.swordData[lastBBB] = thisBookCVData
                                        thisBookCVData = {}
                                    lastBBB = BBB
                                if requestedBBB and BBB != requestedBBB: continue # Ignore other books
                                if verseLength:
                                    try: chunk = blockStuff[blockNumber][verseOffset:verseOffset+verseLength]
                                    except IndexError:
                                        logging.error( "Compressed {} {} {} skipped non-existing chunk {} / {} for {!r}" \
                                            .format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, unit, blockNumber, verseOffset, verseLength ) )
                                        chunk = ''
                                    if len(chunk)!=verseLength: print( "PROBLEM:", ref, len(chunk), verseLength )
                                    #assert len(chunk) == verseLength
                                else:
                                    blankCount += 1
                                    chunk = ''
                                thisBookCVData[(C,V,)] = chunk.strip()
                            if thisBookCVData: self.swordData[BBB] = thisBookCVData # Save final entry
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} {} entries loaded{}".format( len(vssData), Testament, self.SwordModuleConfiguration.modCategory, " ({} were blank)".format(blankCount) if blankCount else '' ) )
                        else: # we're just making an index
                            for k, (blockNumber,verseOffset,verseLength,) in enumerate(vssData):
                                ref = self.convertOTIndexToReference( k ) if testament=='ot' else self.convertNTIndexToReference( k )
                                #if k>8240: print( k, verseOffset, verseLength, ref ) # Rev 22:21 is k=8245
                                if ref is not None: # it's valid
                                    BBB, C, V = ref
                                    if BBB != lastBBB: # we're on to a new book
                                        if thisBookCVData:
                                            self.swordIndex[lastBBB] = (filepath,thisBookCVData,)
                                            thisBookCVData = {}
                                        lastBBB = BBB
                                    if requestedBBB and BBB != requestedBBB: continue # Ignore other books
                                    #thisBookCVData[(C,V,)] = (bookData[blockNumber][0],bookData[blockNumber][1],bookData[blockNumber][2],verseOffset,verseLength,)
                                    try:
                                        thisBookCVData[(C,V,)] = (bookData[blockNumber][0],bookData[blockNumber][1],bookData[blockNumber][2],verseOffset,verseLength,)
                                    except IndexError:
                                        logging.error( "Ignored invalid CV info for {} {} {} {} {}:{}" \
                                            .format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, Testament, BBB, C, V ) )
                                else: logging.critical( "Ignored invalid vss info for {} {} {} {} {}:{}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, Testament, BBB, C, V ) )
                            if thisBookCVData: self.swordIndex[BBB] = (filepath,thisBookCVData,) # Save final entry
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} {} index entries loaded".format( len(vssData), Testament, self.SwordModuleConfiguration.modCategory ) )
            if not totalIdxCount:
                logging.critical( "No data available for compressed {} module".format( self.SwordModuleConfiguration.name ) )

        else: # module is not compressed
            lengthsize = 4 if self.SwordModuleConfiguration.modType=='RawCom4' else 2
            totalCount = 0
            for testament,Testament in processTestaments: # load OT then NT files
                vssCount, vssData = 0, []
                filepath = os.path.join( self.dataFolder, testament+'.vss' )
                if os.path.isfile( filepath ):
                    with open( filepath, 'rb') as indexFile: # This file contains offset,verseLength indexes into the main data file
                        while True:
                            vssCount += 1
                            binaryBlock = indexFile.read( 4+lengthsize) # Offset size is always 4
                            if not binaryBlock: break # at the end of the file
                            verseOffset, verseLength = struct.unpack( 'Ii' if self.SwordModuleConfiguration.modType=='RawCom4' else 'Ih', binaryBlock )
                            vssData.append( (verseOffset, verseLength) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} {} index entries read".format( len(vssData), Testament, self.SwordModuleConfiguration.modCategory ) )
                    totalCount += vssCount
                else:
                    logging.info( "No {} data available for {} module".format( Testament, self.SwordModuleConfiguration.name ) )
                if vssData:
                    blankCount = 0
                    thisBookCVData = {}
                    lastBBB = None
                    filepath = os.path.join( self.dataFolder, testament )
                    if self.inMemoryFlag:
                        with open( filepath, 'rt', encoding=self.SwordModuleConfiguration.encoding ) as textFile: # Load all the Bible text into self.swordData
                            for j, (verseOffset, verseLength) in enumerate(vssData):
                                if verseLength:
                                    textFile.seek( verseOffset )
                                    chunk = textFile.read( verseLength )
                                else:
                                    blankCount += 1
                                    chunk = ''
                                ref = self.convertOTIndexToReference( j ) if testament=='ot' else self.convertNTIndexToReference( j )
                                if ref is None:
                                    print( "ref is None:", self.SwordModuleConfiguration.abbreviation, testament, j, verseOffset, verseLength )
                                    logging.error( "Ignoring {} entry".format( Testament ) )
                                else:
                                    BBB, C, V = ref
                                    if BBB != lastBBB: # we're on to a new book
                                        if thisBookCVData:
                                            self.swordData[lastBBB] = thisBookCVData
                                            thisBookCVData = {}
                                        lastBBB = BBB
                                    if requestedBBB and BBB != requestedBBB: continue # Ignore other books
                                    thisBookCVData[(C,V,)] = chunk.strip()
                            if thisBookCVData: self.swordData[lastBBB] = thisBookCVData
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} {} entries loaded{}".format( j+1-blankCount, Testament, self.SwordModuleConfiguration.modCategory, " ({} were blank)".format(blankCount) if blankCount else '' ) )
                    else: # we're just making an index
                        for j, (verseOffset, verseLength,) in enumerate(vssData):
                            #print( j, verseOffset, verseLength )
                            ref = self.convertOTIndexToReference( j ) if testament=='ot' else self.convertNTIndexToReference( j )
                            #print( j, verseOffset, verseLength, ref )
                            if ref is None:
                                print( "ref is None:", self.SwordModuleConfiguration.abbreviation, testament, j, verseOffset, verseLength )
                                logging.error( "Ignoring {} entry".format( Testament ) )
                            else:
                                BBB, C, V = ref
                                if BBB != lastBBB: # we're on to a new book
                                    if thisBookCVData:
                                        self.swordIndex[lastBBB] = (filepath,thisBookCVData,)
                                        thisBookCVData = {}
                                    lastBBB = BBB
                                if requestedBBB and BBB != requestedBBB: continue # Ignore other books
                                thisBookCVData[(C,V,)] = (verseOffset,verseLength,)
                        if thisBookCVData: self.swordIndex[lastBBB] = (filepath,thisBookCVData,) # Save final entry
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    {} {} {} index entries loaded".format( j+1, Testament, self.SwordModuleConfiguration.modCategory ) )
            if not totalCount:
                logging.critical( "No data available for {} module".format( self.SwordModuleConfiguration.name ) )
    # end of SwordModule.loadVersifiedBibleData


    def loadBooks( self, inMemoryFlag=False ):
        """
        Load the Sword module index into memory (and possibly also the data)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.loadBooks( {} )".format( inMemoryFlag ) )
            #print( "\n\nSwIndex", self.swordIndex )
            #print( "\n\nSwData", self.swordData )
            assert not self.swordIndex and not self.swordData # Shouldn't be loaded already

        self.inMemoryFlag = inMemoryFlag

        if BibleOrgSysGlobals.verbosityLevel > 0: print( "Loading {!r} module…".format( self.SwordModuleConfiguration.abbreviation ) )
        self.store = self.swordData if self.inMemoryFlag else self.swordIndex
        if self.SwordModuleConfiguration.locked:
            logging.critical( "Program doesn't handle locked modules yet: {}".format( self.SwordModuleConfiguration.abbreviation ) )
            return
        if not self.SwordModuleConfiguration.modType: return # Assume an error of some sort is already given in loadConf()
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "    Module name is {}.".format( self.SwordModuleConfiguration.name ) )
            print( "    Module type is {}.".format( self.SwordModuleConfiguration.modType ) )
            if 'Versification' in self.SwordModuleConfiguration.confDict: print( "    Versification scheme is {}.".format( self.SwordModuleConfiguration.confDict['Versification'] ) )
            if BibleOrgSysGlobals.verbosityLevel > 3 or BibleOrgSysGlobals.debugFlag:
                print( "    Category is {}.".format( self.SwordModuleConfiguration.confDict['Category'] ) if 'Category' in self.SwordModuleConfiguration.confDict else "    " + _("No category.") )
                print( "    Feature is {}.".format( self.SwordModuleConfiguration.confDict['Feature'] ) if 'Feature' in self.SwordModuleConfiguration.confDict else "    " + _("No feature.") )
                print( "    Module encoding is {}.".format( self.SwordModuleConfiguration.encoding ) )

        self.dataFolder = os.path.normpath( os.path.join( self.SwordModuleConfiguration.swordFolder, self.SwordModuleConfiguration.confDict['DataPath'] ) )
        self.filename = ''
        if not os.path.isdir( self.dataFolder ):
            self.dataFolder = os.path.normpath( os.path.join( self.dataFolder, '../' ) ) # Seems that some modules put the filename here also
            ix = self.SwordModuleConfiguration.confDict['DataPath'].rfind( '/' )
            self.filename = self.SwordModuleConfiguration.confDict['DataPath'][ix+1:]
        if self.dataFolder[-1] not in ('/','\\',): self.dataFolder += os.sep # We like folder names to end with the separator character

        if self.SwordModuleConfiguration.modType == 'RawText' or self.SwordModuleConfiguration.modType=='RawFiles': # it's an uncompressed Bible
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading uncompressed Bible from {}…".format( self.dataFolder ) )
            assert 'CompressType' not in self.SwordModuleConfiguration.confDict
            if 'BlockType' in self.SwordModuleConfiguration.confDict: assert self.SwordModuleConfiguration.confDict['BlockType'] in ('BOOK',)
            if self.SwordModuleConfiguration.modType!='RawFiles':
                try: assert self.SwordModuleConfiguration.confDict['SourceType'] in ('OSIS','ThML','Plain',)
                except KeyError: pass # Doesn't seem to matter if it's missing
            self.loadVersifiedBibleData()

        elif self.SwordModuleConfiguration.modType == 'zText': # it's a compressed Bible
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading compressed Bible from {}…".format( self.dataFolder ) )
            assert 'CompressType' in self.SwordModuleConfiguration.confDict
            assert self.SwordModuleConfiguration.confDict['CompressType'] in ('ZIP',)
            assert self.SwordModuleConfiguration.confDict['BlockType'] in ('BOOK','CHAPTER',)
            if 'SourceType' in self.SwordModuleConfiguration.confDict: assert self.SwordModuleConfiguration.confDict['SourceType'] in ('OSIS','ThML','GBF','Plaintext',)
            self.loadVersifiedBibleData()

        elif self.SwordModuleConfiguration.modType in ('RawCom','RawCom4',): # it's an uncompressed commentary
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading uncompressed commentary from {}…".format( self.dataFolder ) )
            assert 'CompressType' not in self.SwordModuleConfiguration.confDict
            self.loadVersifiedBibleData()

        elif self.SwordModuleConfiguration.modType == 'zCom': # it's a compressed commentary
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading compressed commentary from {}…".format( self.dataFolder ) )
            assert 'CompressType' in self.SwordModuleConfiguration.confDict
            self.loadVersifiedBibleData()

        elif self.SwordModuleConfiguration.modType in ('RawLD','RawLD4',): # it's an uncompressed lexicon/dictionary
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading uncompressed dictionary from {}…".format( self.dataFolder ) )
            assert 'CompressType' not in self.SwordModuleConfiguration.confDict
            self.loadRawLD()

        elif self.SwordModuleConfiguration.modType == 'zLD': # it's a compressed lexicon/dictionary
            self.loadCompressedLD()

        elif self.SwordModuleConfiguration.modType == 'RawGenBook': # it's an uncompressed commentary
            self.loadRawGenBook()

        else:
            logging.critical( "Unknown {!r} module type".format( self.SwordModuleConfiguration.modType ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( self )
            print( "      Index size: {}".format( BibleOrgSysGlobals.totalSize( self.swordIndex ) ) )
            print( "      Data size: {}".format( BibleOrgSysGlobals.totalSize( self.swordData ) ) )

        if self.store: return True
    # end of SwordModule.loadBooks


    def loadBook( self, BBB, inMemoryFlag=False ):
        """
        Load the Sword module index into memory (and possibly also the data)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.loadBook( {}, {} )".format( BBB, inMemoryFlag ) )
            #print( "\n\nSwIndex", self.swordIndex )
            #print( "\n\nSwData", self.swordData )
            assert not self.swordIndex and not self.swordData # Shouldn't be loaded already

        self.inMemoryFlag = inMemoryFlag

        if BibleOrgSysGlobals.verbosityLevel > 0: print( "Loading {!r} book {}…".format( self.SwordModuleConfiguration.abbreviation, BBB ) )
        self.store = self.swordData if self.inMemoryFlag else self.swordIndex
        if self.SwordModuleConfiguration.locked:
            logging.critical( "Program doesn't handle locked modules yet: {}".format( self.SwordModuleConfiguration.abbreviation ) )
            return
        if not self.SwordModuleConfiguration.modType: return # Assume an error of some sort is already given in loadConf()
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "    Module name is {}.".format( self.SwordModuleConfiguration.name ) )
            print( "    Module type is {}.".format( self.SwordModuleConfiguration.modType ) )
            if 'Versification' in self.SwordModuleConfiguration.confDict: print( "    Versification scheme is {}.".format( self.SwordModuleConfiguration.confDict['Versification'] ) )
            if BibleOrgSysGlobals.verbosityLevel > 3 or BibleOrgSysGlobals.debugFlag:
                print( "    Category is {}.".format( self.SwordModuleConfiguration.confDict['Category'] ) if 'Category' in self.SwordModuleConfiguration.confDict else "    " + _("No category.") )
                print( "    Feature is {}.".format( self.SwordModuleConfiguration.confDict['Feature'] ) if 'Feature' in self.SwordModuleConfiguration.confDict else "    " + _("No feature.") )
                print( "    Module encoding is {}.".format( self.SwordModuleConfiguration.encoding ) )

        self.dataFolder = os.path.normpath( os.path.join( self.SwordModuleConfiguration.swordFolder, self.SwordModuleConfiguration.confDict['DataPath'] ) )
        self.filename = ''
        if not os.path.isdir( self.dataFolder ):
            self.dataFolder = os.path.normpath( os.path.join( self.dataFolder, '../' ) ) # Seems that some modules put the filename here also
            ix = self.SwordModuleConfiguration.confDict['DataPath'].rfind( '/' )
            self.filename = self.SwordModuleConfiguration.confDict['DataPath'][ix+1:]
        if self.dataFolder[-1] not in ('/','\\',): self.dataFolder += os.sep # We like folder names to end with the separator character

        if self.SwordModuleConfiguration.modType == 'RawText' or self.SwordModuleConfiguration.modType=='RawFiles': # it's an uncompressed Bible
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading uncompressed Bible from {}…".format( self.dataFolder ) )
            assert 'CompressType' not in self.SwordModuleConfiguration.confDict
            if 'BlockType' in self.SwordModuleConfiguration.confDict: assert self.SwordModuleConfiguration.confDict['BlockType'] in ('BOOK',)
            if self.SwordModuleConfiguration.modType!='RawFiles':
                try: assert self.SwordModuleConfiguration.confDict['SourceType'] in ('OSIS','ThML','Plain',)
                except KeyError: pass # Doesn't seem to matter if it's missing
            self.loadVersifiedBibleData( BBB )

        elif self.SwordModuleConfiguration.modType == 'zText': # it's a compressed Bible
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading compressed Bible from {}…".format( self.dataFolder ) )
            assert 'CompressType' in self.SwordModuleConfiguration.confDict
            assert self.SwordModuleConfiguration.confDict['CompressType'] in ('ZIP',)
            assert self.SwordModuleConfiguration.confDict['BlockType'] in ('BOOK','CHAPTER',)
            if 'SourceType' in self.SwordModuleConfiguration.confDict: assert self.SwordModuleConfiguration.confDict['SourceType'] in ('OSIS','ThML','GBF','Plaintext',)
            self.loadVersifiedBibleData( BBB )

        elif self.SwordModuleConfiguration.modType in ('RawCom','RawCom4',): # it's an uncompressed commentary
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading uncompressed commentary from {}…".format( self.dataFolder ) )
            assert 'CompressType' not in self.SwordModuleConfiguration.confDict
            self.loadVersifiedBibleData( BBB )

        elif self.SwordModuleConfiguration.modType == 'zCom': # it's a compressed commentary
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loading compressed commentary from {}…".format( self.dataFolder ) )
            assert 'CompressType' in self.SwordModuleConfiguration.confDict
            self.loadVersifiedBibleData( BBB )

        elif self.SwordModuleConfiguration.modType in ('RawLD','RawLD4','zLD',): # it's a lexicon/dictionary
            logging.critical( "Lexicons/Dictionaries don't have Bible books!" )

        elif self.SwordModuleConfiguration.modType == 'RawGenBook': # it's an uncompressed commentary
            logging.critical( "Genbooks don't have Bible books!" )

        else:
            logging.critical( "Unknown {!r} module type".format( self.SwordModuleConfiguration.modType ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( self )
            print( "      Index size: {}".format( BibleOrgSysGlobals.totalSize( self.swordIndex ) ) )
            print( "      Data size: {}".format( BibleOrgSysGlobals.totalSize( self.swordData ) ) )

        if self.store: return True
    # end of SwordModule.loadBook


    def __str__( self ):
        """
        This method returns the string representation of a Sword module object.

        @return: the name of a Sword object formatted as a string
        @rtype: string
        """
        result = "SwordModule for {}".format( self.SwordModuleConfiguration.abbreviation )
        #if self.SwordModuleConfiguration.abbreviation: result += ('\n' if result else '') + "  " + _("Abbreviation: ") + self.SwordModuleConfiguration.abbreviation
        if self.SwordModuleConfiguration.swordFolder: result += ('\n' if result else '') + "  " + _("Folder: {}").format( self.SwordModuleConfiguration.swordFolder )
        result += ('\n' if result else '') + "  " + _("Loaded into memory: {}").format( self.inMemoryFlag )
        for key,value in self.SwordModuleConfiguration.confDict.items():
            adjKey = "LCSH (Library of Congress Subject Headings)" if key=="LCSH" else key
            if key == "History":
                result += ('\n' if result else '') + "      " + _("History:")
                if not isinstance( value, list ): value = [value]
                for version,historyDescription in value:
                    result += ('\n' if result else '') + "        {}: {}".format( version, historyDescription )
            elif key not in TECHNICAL_SWORD_CONF_FIELD_NAMES or BibleOrgSysGlobals.verbosityLevel > 2: # Don't bother printing some of the technical keys
                result += ('\n' if result else '') + "      {}: {}".format( adjKey, value )
        return result
    # end of SwordModule.__str__


    def getType( self ):
        return self.SwordModuleConfiguration.modType
    def getMarkup( self ):
        return self.SwordModuleConfiguration.confDict['SourceType']
    def getEncoding( self ):
        return self.SwordModuleConfiguration.encoding


    def getDescription( self ):
        """
        """
        return "XYZ!"
    # end of SwordModule.getDescription


    def convertOTIndexToReference( self, indexNumber ):
        """
        Given an OT index number, convert it to a BBB,C,V reference (no suffix field)

        Returns the 3-tuple or None.
        """
        try: return self.OTIndex[indexNumber]
        except IndexError:
            logging.critical( "convertOTIndexToReference: No {} indexNumber in OTIndex of length {}".format( indexNumber, len(self.OTIndex) ) )
    # end of SwordModule.convertOTIndexToReference


    def convertNTIndexToReference( self, indexNumber ):
        """
        Given an NT index number, convert it to a BBB,C,V reference (no suffix field)

        Returns the 3-tuple or None.
        """
        try: return self.NTIndex[indexNumber]
        except IndexError:
            logging.critical( "convertNTIndexToReference: No {} indexNumber in NTIndex of length {}".format( indexNumber, len(self.NTIndex) ) )
    # end of SwordModule.convertNTIndexToReference


    def getVersifiedOffset( self, BBB, C, V, offsetType=0 ): # The 0 selects the OTNTOffset (1 is OTOffset, 2 is NTOffset)
        """
        Get the OTNTOffset for a given reference. (All parameters must be strings.)

        Chapter and Verse numbers start from 1.

        Automatically skips over the work and chapter introductions.
        """
        assert self.chapterOffsets
        assert len(BBB) == 3
        assert C.isdigit()
        assert V.isdigit()
        return self.chapterOffsets[BBB][int(c)][offsetType] + int(v)-1 # The offset type selects: [0] is OTNTOffset, [1] is OTOffset, [2] is NTOffset
    # end of SwordModule.getVersifiedOffset


    def getRawVersifiedData( self, reference ):
        """
        Returns the raw data for the given Bible reference.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( "SwordModule.getRawVersifiedData( {} )".format( reference ) )
            assert self.versifiedFlag
            assert self.SwordModuleConfiguration.modType in ('RawText','zText','RawCom','RawCom4','zCom','RawFiles',)

        #print( "getRawVersifiedData:", reference )
        if len(reference)==3: (BBB,c,v), s = reference, ''
        else: BBB,c,v, s = reference
        assert (BBB,c,v=='FRT','0','0') or self.BibleOrgSystem.isValidBCVRef( reference, "getRawVersifiedData", True )
        if self.inMemoryFlag: # it's easy -- we already have all the data
            try: return self.swordData[BBB][(c,v,)]
            except KeyError: return None
        elif BBB in self.swordIndex: # ok, we have to load the data from the file (or maybe from cache)
            try: filepath,indexData = self.swordIndex[BBB]
            except KeyError:
                logging.warning( "Book {} doesn't seem to be included in {} {}".format( BBB, self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                return None # if the book isn't included in this module
            try: indexInfo = indexData[(c,v,)]
            except KeyError:
                logging.error( "Reference {}:{} doesn't seem to exist in book {} of {} {}".format( c, v, BBB, self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory ) )
                return None
            if 'CompressType' in self.SwordModuleConfiguration.confDict:
                if self.SwordModuleConfiguration.confDict['BlockType'] == 'BOOK':
                    unit = "book"
                elif self.SwordModuleConfiguration.confDict['BlockType'] == 'CHAPTER':
                    unit = "chapter"
                else:
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                #print( indexInfo )
                fileOffset, compressedLength, uncompressedLength, verseOffset, verseLength = indexInfo
                if compressedLength and verseLength:
                    if (BBB,fileOffset) in self.cache:
                        uncompressedChunk, cachedTime = self.cache[(BBB,fileOffset)]
                    else: # it's not cached
                        with open( filepath, 'rb') as compressedTextFile: # This is the compressed verse data (in book or chapter size chunks)
                            compressedTextFile.seek( fileOffset )
                            compressedChunk = compressedTextFile.read( compressedLength )
                        #try:
                        uncompressedChunk = self.decompressChunk( compressedChunk )
                        self.cache[(BBB,fileOffset)] = (uncompressedChunk,time.time(),)
                        #except:
                        #    logging.error( "Unable to decompress {} {} chunk {}->{}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, compressedLength, uncompressedLength ) )
                        #    uncompressedLength, uncompressedChunk = 0, b''
                        #    halt
                    assert len(uncompressedChunk) == uncompressedLength
                    try:
                        textChunk = uncompressedChunk.decode( self.SwordModuleConfiguration.encoding )
                    except UnicodeDecodeError:
                        logging.warning( "Unable to properly decode {} {} {} {} book chunk #{} {}->{}".format( self.SwordModuleConfiguration.encoding, self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, unit, fileOffset, compressedLength, uncompressedLength ) )
                        if BibleOrgSysGlobals.debugFlag: print( "  ", uncompressedChunk[:40] )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        textChunk = uncompressedChunk.decode( self.SwordModuleConfiguration.encoding, 'replace' )
                    verseText = textChunk[verseOffset:verseOffset+verseLength]
                    if len(verseText)!=verseLength:
                        print( "WHY!", reference, len(verseText), verseLength )
                    #assert len(verseText) == verseLength
                    return verseText
                return ''
            else: # it's not compressed
                verseOffset, verseLength = indexInfo
                if verseLength:
                    with open( filepath, 'rt', encoding=self.SwordModuleConfiguration.encoding ) as textFile:
                        textFile.seek( verseOffset )
                        verseText = textFile.read( verseLength )
                    return verseText
                else: return ''
    # end of SwordModule.getRawVersifiedData


    def getRawDictData( self, word ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.getRawDictData( {} )".format( word ) )

        if self.inMemoryFlag: # it's easy -- we already have all the data
            try: result = self.swordData[word]
            except KeyError: return None
            assert isinstance( result, str ) or isinstance( result, list )
            return result
        else: # we only have the index in memory
            try: indexInfo = self.swordIndex[word]
            except KeyError: return None
            if isinstance( indexInfo, str ) and indexInfo.endswith( ' (auto-added)' ): return indexInfo # This extra cross-referencing was added by us
            if 'CompressType' in self.SwordModuleConfiguration.confDict:
                #print( indexInfo )
                fileOffset, compressedLength, blockNumber, blockChunkNumber = indexInfo
                if compressedLength:
                    if fileOffset in self.cache:
                        uncompressedChunk, cachedTime = self.cache[fileOffset]
                    else: # it's not cached
                        with open( self.dataFilepath, 'rb') as compressedTextFile: # This is the compressed data (in book size chunks)
                            compressedTextFile.seek( fileOffset )
                            compressedChunk = compressedTextFile.read( compressedLength )
                        uncompressedChunk = self.decompressChunk( compressedChunk )
                        #print( uncompressedChunk )
                        self.cache[fileOffset] = (uncompressedChunk,time.time(),)
                    thisCount, = struct.unpack( 'I', uncompressedChunk[0:4])
                    ix = 4
                    for c in range(0, thisCount):
                        offset3, length3 = struct.unpack( 'II', uncompressedChunk[ix:ix+8] )
                        ix += 8
                        thisUncompressedChunk = uncompressedChunk[offset3:offset3+length3-1] # We don't want the NULL on the end
                        try:
                            thisString = thisUncompressedChunk.decode( self.SwordModuleConfiguration.encoding )
                        except KeyError:
                            #for key, (fO, cL, blockNumber, blockChunkNumber) in self.swordIndex.items(): # By a slow loop, find the key which points to this entry
                            #    if blockNumber==j and blockChunkNumber==c: thisKey = key; break
                            logging.warning( "Unable to properly decode {} {} chunk for {}".format( self.SwordModuleConfiguration.encoding, self.SwordModuleConfiguration.name, word ) )
                            if BibleOrgSysGlobals.debugFlag: print( "  ", thisUncompressedChunk[:40] )
                            thisString = thisUncompressedChunk.decode( self.SwordModuleConfiguration.encoding, 'replace' )
                        #print( c, ix, thisString )
                        if c == blockChunkNumber: break
                        # Spurious??? chunk = uncompressedChunk.decode( self.SwordModuleConfiguration.encoding, 'replace' )
                    assert isinstance( thisString, str )
                    return thisString.strip()
                return ''
            else: # it's not compressed
                #print( indexInfo )
                if isinstance( indexInfo, list ):
                    chunks = []
                    for offset, length in indexInfo:
                        if length:
                            with open( self.dataFilepath, 'rt', encoding=self.SwordModuleConfiguration.encoding ) as textFile:
                                textFile.seek( offset )
                                chunk = textFile.read( length )
                            assert isinstance( chunk, str )
                            chunks.append( chunk.strip() )
                    return chunks
                else:
                    offset, length = indexInfo
                    if length:
                        try:
                            with open( self.dataFilepath, 'rt', encoding=self.SwordModuleConfiguration.encoding ) as textFile:
                                textFile.seek( offset )
                                chunk = textFile.read( length )
                        except IOError:
                            logging.critical( "Chunk read error for {} {} looking for {!r}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory, word ) )
                            if self.SwordModuleConfiguration.abbreviation=='zhhanzi': # my bug here somewhere??? XXXX
                                chunk = ''
                            else:
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        assert isinstance( chunk, str )
                        return chunk.strip()
                    else: return ''
    # end of SwordModule.getRawDictData


    #def XXXpreprocessRawGenBookEntry( self, key, rawEntry ):
        #halt # Not used coz should be part of filtering
        #def preprocessRawGenBookEntryHelper( key, rawEntry ):
            #entry = rawEntry
            #if entry.startswith( key ): entry = entry[len(key):] # Remove the key since we've already got that
            #entry = entry.lstrip() # Remove spurious CRLFs
            #if entry.startswith( "<br />"): entry = entry[6:]
            #entry = entry.strip() # Remove spurious CRLFs
            #if entry.startswith('<img src="/') and entry.endswith('"/>'):
                #entry = entry[11:-3] # Should now be a relative filename
                #print( entry )
                #filepath = os.path.join( self.dataFolder, entry )
                #print( filepath )
                #assert os.path.isfile( filepath )
            #else: filepath = None
            #if entry!=rawEntry or filepath is not None:
                #print( "\nRaw entry in {} for {}: {}".format( self.SwordModuleConfiguration.abbreviation, key, rawEntry ) )
                #print( filepath, entry )
                #halt
            #return entry, filepath
        ## end of SwordModule.preprocessRawGenBookEntryHelper

        #print( "\nRaw entry in {} for {}: {}".format( self.SwordModuleConfiguration.abbreviation, key, rawEntry ) )
        #if isinstance( rawEntry, list ):
            #results = []
            #for entry in rawEntry:
                #results.append( preprocessRawGenBookEntryHelper( key, entry ) )
            #return results
        #else: return preprocessRawGenBookEntryHelper( key, rawEntry )
    ## end of SwordModule.preprocessRawGenBookEntry


    def filterToHTML( self, rawData, BBB=None, C=None, V=None ):
        """
        Does preprocessing on the raw data from the module.

        Note: not all module types have BCV references.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModule.filterToHTML( {} )".format( rawData ) )

        #assert not self.versifiedFlag # for now
        if rawData is None: return None
        if isinstance( rawData, list ):
            results = []
            for rawEntry in rawData:
                results.append( self.filterToHTML( rawEntry ) ) # recursive call
            return results

        # This is where the real work is done
        elif isinstance( rawData, str ):
            data = rawData.strip()
            if 'SourceType' in self.SwordModuleConfiguration.confDict:
                if self.SwordModuleConfiguration.confDict['SourceType'] == 'ThML':
                    # What do we do here??? …… XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxxxxxxxxxxxxxxxxxxxx
                    return data
                elif self.SwordModuleConfiguration.confDict['SourceType'] == 'OSIS':
                    # What do we do here??? …… XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxxxxxxxxxxxxxxxxxxxx
                    return data
                elif self.SwordModuleConfiguration.confDict['SourceType'] == 'GBF':
                    # What do we do here??? …… XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxxxxxxxxxxxxxxx
                    return data
                else:
                    logging.critical( "Missing filterToHTML SourceType code for {}".format( self.SwordModuleConfiguration.confDict['SourceType'] ) )
                    return data
            # else
            logging.critical( "Missing SourceType field for filterToHTML for {}".format( self.name ) )
            return data

        else:
            print( "filterToHTML rawData is ", rawData ) # unexpected data type
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
    # end of SwordModule.filterToHTML


    def filterToUSFM( self, rawData, BBB, C, V ):
        """
        Does preprocessing on the raw data from the module.
        """
        from BibleOrgSys.Formats.SwordResources import filterOSISVerseLine, filterGBFVerseLine, filterTHMLVerseLine

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( "SwordModule.filterToUSFM( {} )".format( rawData ) )
            assert self.versifiedFlag # only makes sense for versified data
            assert self.SwordModuleConfiguration.modCategory == 'Bible' # USFM doesn't really make sense for commentaries

        if rawData is None: return None
        if isinstance( rawData, list ):
            results = []
            for rawEntry in rawData:
                results.append( self.filterToUSFM( rawEntry ) ) # recursive call
            return results

        # This is where the real work is done
        elif isinstance( rawData, str ):
            data = rawData.strip()
            if 'SourceType' in self.SwordModuleConfiguration.confDict:
                if self.SwordModuleConfiguration.confDict['SourceType'] == 'OSIS':
                    ## What do we do here??? …… XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxxxxxxxxxxxxxxxxxxxx
                    #return data
                    return filterOSISVerseLine( data, self.SwordModuleConfiguration.abbreviation, BBB, C, V )
                elif self.SwordModuleConfiguration.confDict['SourceType'] == 'GBF':
                    #if data: data = data.replace('<FI>','\\add ').replace('<Fi>','\\add*')
                    #if data: data = data.replace('<CM>','') # What is this?
                    ##if '<' in data: print( "{!r} is now {!r}".format( rawData, data ) ); halt
                    #return data
                    return filterGBFVerseLine( data, self.SwordModuleConfiguration.abbreviation, BBB, C, V )
                elif self.SwordModuleConfiguration.confDict['SourceType'] == 'ThML':
                ##    #if data: print( "ThML data is", data )
                    ## What do we do here??? … XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxxxxxxxxxxxxxxxxxxxx
                    #return data
                    return filterTHMLVerseLine( data, self.SwordModuleConfiguration.abbreviation, BBB, C, V )
                elif self.SwordModuleConfiguration.confDict['SourceType'] in ('Plaintext','Plain',):
                    # Should be nothing to do here
                    return data
                else:
                    logging.critical( "Missing filterToUSFM SourceType code for {}".format( self.SwordModuleConfiguration.confDict['SourceType'] ) )
                    return data
            # else
            # We need to display less of these errors
            #logging.critical( "Missing SourceType field for filterToUSFM for {}".format( self.name ) )
            return data

        else:
            print( "filterToUSFM rawData is ", rawData ) # unexpected data type
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
    # end of SwordModule.filterToUSFM



    def test( self, testArray=None ):
        """
        Temporary code (should be in test suite).

        Determines the type of module and tries to run an appropriate test.

        If the testArray is given, compares the results with those in the dictionary.
        """
        foundAny = False
        if testArray is None: ourTestArray = {}
        if self.versifiedFlag:
            assert self.SwordModuleConfiguration.modType in ('RawText','zText','RawCom','zCom','RawFiles',)
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTest Results:" )
            shortTest = (('GEN','1','1',''),('GEN','1','2',''),('GEN','1','3',''),('MAT','1','1',''),('JHN','3','16',''),('REV','1','1','', ),('REV','22','20','', ),('REV','22','21','', ),)
            longTest  = (('GEN','1','1',''),('GEN','1','2',''),('GEN','1','3',''),('PSA','1','1',''),('PSA','150','2',''),('DAN','1','1',''),('MAL','4','5',''),('MAL','4','6',''), \
                        ('SIR','1','1',''),
                        ('MAT','1','1',''),('MAT','1','2',''),('MAT','2','1',''),('MAT','3','1',''),('MAT','28','20',''), \
                        ('MRK','1','1',''),('MRK','1','2',''),('MRK','2','1',''),('MRK','16','20',''), \
                        ('JHN','1','1',''),('JHN','3','16',''), \
                        ('LUK','1','1',''),('ACT','1','1',''),('ROM','1','1',''),('TH1','1','1',''), \
                        ('PE1','1','1',''),('JN1','1','1',''),('JN2','1','1',''),('JN3','1','1',''),('JN3','1','14',''),('JDE','1','1',''), \
                        ('REV','1','1',''),('REV','1','2',''),('REV','1','3',''),('REV','22','1',''),('REV','22','20',''),('REV','22','21',''),('LAO','1','1',''),)
            #specificTest = (('REV','1','2',''),)
            specificTest = (('MAT','3','15',''),('MAT','3','16',''),('MAT','3','17',''),('MAT','4','1',''),('MAT','4','2',''),)
            ourFilter = self.filterToUSFM if self.SwordModuleConfiguration.modCategory=='Bible' else self.filterToHTML
            for ref in specificTest:
                if self.BibleOrgSystem.isValidBCVRef( ref, "SwordModule. test references", True ): # Some versification systems don't contain all of the test references
                    BBB,c,v,s = ref
                    assert not s
                    result = ourFilter( self.getRawVersifiedData( ref ), BBB, c, v )
                    if result: foundAny = True
                    if (result and BibleOrgSysGlobals.verbosityLevel > 1) or BibleOrgSysGlobals.verbosityLevel > 2: print( "{}{} {} {}:{}={}".format( '\n' if result and len(result)>500 else '', self.SwordModuleConfiguration.name, BBB, c, v, result ) )
                    if testArray is None: ourTestArray[ref] = result
                    elif result != testArray[ref]:
                        logging.error( "test gave different result for {}:\n  was {}\n  now {}".format( ref, testArray[ref], result ) )
                else: logging.warning( "This BCV reference {} is not valid in the {} versification system." \
                            .format( ref, self.SwordModuleConfiguration.confDict['Versification'] if 'Versification' in self.SwordModuleConfiguration.confDict else 'KJV' ) )
            if not foundAny:
                print( len(self.store), sorted(self.store.keys()) )
                logging.warning( "Couldn't find any relevant information in the {} {}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory ) )
                if self.SwordModuleConfiguration.abbreviation in ('personal',): pass # Personal module can be empty
                else:
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        elif self.SwordModuleConfiguration.modType in ('RawLD','RawLD4','zLD','RawGenBook',):
            EnglishTestWords = ('ADAM','BAPTISM','BETHLEHEM','CAMEL','CONSUL','DAY','FAITH','GARDEN OF EDEN','GOLD','INSPIRE', \
                                'MAGGI','MOSES','NOAH','PALESTINE','REPENT','SABBATH','TARSHISH','UR','WOLF','ZUZIM', )
            # This next one has less usual words and foreign language words
            extraTestWords = ('1','1. BEGINNINGS','1. KAPITEL','50', \
                                'A','ABOUT','ABIDE_WITH_ME','AF','ARCHY','BANANA','BOOK I','CHAPTER 2','CONTENTS','DEN','DOCTOR','DOS','EIGHT','END', \
                                'FOR','GAN','GOAT','HE_LEADETH_ME','HERETICS','HIMMELFAHRT','I','INDEX','INTRODUCTION','KITAB','LLAMA','LONG', \
                                'MAP','MATA','NUN','ONION','PREFACE','RADAR','RIGNA','SERMON','SONNTAG','SOURCE','TABLE OF CONTENTS', \
                                'THE DEAD SEA','THESES','TILA','TITRE','UNA','V','VISA','WOMAN','YAHUDI','YARD','YEBO','YOD','ZOHAR','ZOPHAI', \
                                ':CE=O','鹅卵石', \
                                'مشر و سینا' )
            GreekTestWords = ('Α','ἈΑΡΏΝ','ἈΒΡΑΆΜ','ἌΦΕΝΟΣ','ΔΙΆΒΟΛΟΣ','ἸΑΚΏΒ','ὈΦΘΑΛΜΟΔΟΥΛΕΊΑ','ΣΥΝΤΕΛΈΩ','ΦΥΣΆΩ','ὨΤΊΟΝ','ὨΦΈΛΕΙΑ','ὨΦΕΛΈΩ','ὨΦΈΛΙΜΟΣ',)
            StrongsGreekNumbers = ('G00000','G00001','G01001','G02002','G03003','G04004','G05005','G05624','G06006',)
            GreekParsings = ('A-NSN','I-NPF','S-2DPM','V-ADS-3P','X-NSN',)
            HebrewTestWords = ('אב','אבגתא','זעם','כּמהם','מרעה','עריף','שׁמם','תּשׁעה','תּשׁעים','תּתּני',)
            StrongsHebrewNumbers = ('H00000','H00001','H01001','H02002','H03003','H04004','H05005','H06006','H07007','H08008','H08674','H09009',)
            StrongTest = ('G1234','H1234','ἌΣΤΟΡΓΟΣ','ΠΡΟΈΡΧΟΜΑΙ','צלוּלO','תּענית',)
            Dates = ('01.01','02.02','02.29','03.03','04.04','05.05','06.06','07.07','08.08','09.09','10.10','11.11','12.12','12.31',)
            testWords = EnglishTestWords # default
            if self.SwordModuleConfiguration.abbreviation == 'autenrieth': testWords = GreekTestWords
            elif self.SwordModuleConfiguration.abbreviation == 'greekhebrew': testWords = StrongsGreekNumbers
            elif self.SwordModuleConfiguration.abbreviation == 'hebrewgreek': testWords = StrongsHebrewNumbers
            elif self.SwordModuleConfiguration.abbreviation == 'liddellscott': testWords = GreekTestWords
            elif self.SwordModuleConfiguration.abbreviation == 'strong': testWords = StrongTest
            elif 'Feature' in self.SwordModuleConfiguration.confDict:
                if self.SwordModuleConfiguration.confDict['Feature']=='GreekDef':
                    testWords = GreekTestWords
                    if self.SwordModuleConfiguration.abbreviation in ('strongsgreek','strongsrealgreek',): testWords = StrongsGreekNumbers
                elif self.SwordModuleConfiguration.confDict['Feature']=='GreekParse': testWords = GreekParsings
                elif self.SwordModuleConfiguration.confDict['Feature']=='HebrewDef':
                    testWords = HebrewTestWords
                    if self.SwordModuleConfiguration.abbreviation in ('strongshebrew','strongsrealhebrew',): testWords = StrongsHebrewNumbers
                elif self.SwordModuleConfiguration.confDict['Feature']=='DailyDevotion': testWords = Dates
            for word in testWords:
                entry = self.filterToHTML( self.getRawDictData( word ) )
                if testArray is None: ourTestArray[word] = entry
                elif entry != testArray[word]:
                    logging.error( "{} test gave different result for {}:\n  was {}\n  now {}".format( self.SwordModuleConfiguration.name, word, testArray[word], entry ) )
                if entry is None:
                    if BibleOrgSysGlobals.verbosityLevel>2: print( "Sorry, no entry in {} for {!r}".format( self.SwordModuleConfiguration.name, word ) )
                else:
                    foundAny = True
                    #print( word, entry )
                    if isinstance( entry, list ):
                        #print( word, stuff ); halt
                        if BibleOrgSysGlobals.verbosityLevel > 1:
                            print( "\n{} {}:".format( self.SwordModuleConfiguration.name, word ) )
                            for j,string in enumerate( entry ):
                                print( "{}/ {}: {}".format( j+1, word, string ) )
                    elif entry.endswith( ' (auto-added)' ): # It goes something like "See 'ARCHY (2)' or 'ARCHY (1)' (auto-added)"
                        bits = entry.split( "''" )
                        #print( len(bits), bits )
                        if BibleOrgSysGlobals.verbosityLevel > 1:
                            print( "\n{}:".format( word ) )
                            count = 1
                            for i in range(1, len(bits), 2): # Display all the referred entries
                                #print( i, bits[i] )
                                print( "{}/ {}: {}".format( count, bits[i], self.store[bits[i]] ) )
                                count += 1
                    elif BibleOrgSysGlobals.verbosityLevel > 1: print( "\n{}: {}".format( word, entry ) )
            if not foundAny:
                for word in extraTestWords:
                    entry = self.filterToHTML( self.getRawDictData( word ) )
                    if testArray is None: ourTestArray[word] = entry
                    elif entry != testArray[word]:
                        logging.error( "{} test gave different result for {}:\n  was {}\n  now {}".format( self.SwordModuleConfiguration.name, word, testArray[word], entry ) )
                    if entry is None:
                        if BibleOrgSysGlobals.verbosityLevel>2: print( "Sorry, no entry in {} for {!r}".format( self.SwordModuleConfiguration.name, word ) )
                    else:
                        foundAny = True
                        #if self.SwordModuleConfiguration.modType=='RawGenBook': entry = self.preprocessRawGenBookEntry( word, entry )
                        if isinstance( entry, list ):
                            #print( word, stuff ); halt
                            if BibleOrgSysGlobals.verbosityLevel > 1:
                                print( "\n{} {}:".format( self.SwordModuleConfiguration.name, word ) )
                                for j,string in enumerate( entry ):
                                    #if self.SwordModuleConfiguration.modType=='RawGenBook': filename, string = string # unpack the tuple for this case
                                    print( "{}/ {}: {}".format( j+1, word, string ) )
                        elif isinstance( entry, str) and entry.endswith( ' (auto-added)' ): # It goes something like "See 'ARCHY (2)' or 'ARCHY (1)' (auto-added)"
                            bits = entry.split( "''" )
                            #print( len(bits), bits )
                            if BibleOrgSysGlobals.verbosityLevel > 1:
                                print( "\n{}:".format( word ) )
                                count = 1
                                for i in range(1, len(bits), 2): # Display all the referred entries
                                    #print( i, bits[i] )
                                    print( "{}/ {}: {}".format( count, bits[i], self.store[bits[i]] ) )
                                    count += 1
                        elif BibleOrgSysGlobals.verbosityLevel > 1: print( "\n{}: {}".format( word, entry ) )
            if not foundAny:
                if BibleOrgSysGlobals.verbosityLevel > 2: print( len(self.store), sorted(self.store.keys()) )
                logging.warning( "Couldn't find any relevant information in the {} {}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory ) )
                #halt
        else:
            logging.error( "Don't know how to test {!r} module type".format( self.SwordModuleConfiguration.modType ) ); halt
        if testArray is None: return ourTestArray
    # end of SwordModule.test
# end of class SwordModule



class SwordBibleModule( SwordModule, Bible ):
    """
    A Sword module for a Bible or commentary that has versification.
    """
    def __init__( self, loadedSwordModuleConfiguration ):
        """
        Create the Sword Module object.
        """
        assert loadedSwordModuleConfiguration.modCategory in ('Bible','Commentary',)

        # Initialise the SwordModule base class
        SwordModule.__init__( self, loadedSwordModuleConfiguration )
        self.objectNameString = 'SwordBibleModule object'
        self.objectTypeString = 'SwordBibleModule'

        # Initialise the InternalBible base class
        Bible.__init__( self )
        self.name = self.SwordModuleConfiguration.name
        self.sourceFolder = loadedSwordModuleConfiguration.swordFolder
    # end of SwordBibleModule.__init__


    def loadBooks( self, inMemoryFlag=False ):
        """
        Loads a versified Sword module indexes into memory
            and then reads the data and saves it all in our internal format.

        Dummy inMemoryFlag (unused) is to make the parameters identical to the SwordModule.loadBooks() routine.

        TODO: This should be faster if both the above actions were done together.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordBibleModule.loadBooks( ({}) )".format( inMemoryFlag ) )

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  Loading Sword Bible module {}…".format( self.SwordModuleConfiguration.abbreviation ) )

        SwordModule.loadBooks( self, inMemoryFlag=False ) # Load the Sword module index
        if self.store: # we loaded something
            ourFilter = self.filterToUSFM if self.SwordModuleConfiguration.modCategory=='Bible' else self.filterToHTML
            # Now we have to iterate through each book, chapter and verse and load into our internal format
            for BBB in self.store:
                if BBB=='FRT': # special case for the front matter
                    #print( self.swordIndex[BBB] )
                    result = ourFilter( self.getRawVersifiedData( ('FRT','0','0') ), 'FRT', '0', '0' )
                    if result:
                        logging.warning( "Didn't process FRT: "+"'"+result+"'" )
                        #halt # Need to process this
                else:
                    thisBook = BibleBook( self, BBB )
                    thisBook.objectNameString = 'SwordBibleModule book object'
                    thisBook.objectTypeString = self.objectTypeString
                    thisBook.sourceFilepath = self.dataFilepath
                    #thisBook.BBB = BBB
                    thisBook.isSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( BBB )
                    #thisBook.replaceAngleBracketsFlag = self.SwordModuleConfiguration.modCategory == 'Bible'
                    thisBook.replaceAngleBracketsFlag = False
                    bookVerseList = self.BibleOrgSystem.getNumVersesList( BBB, allowAlternatives=True )
                    #print( BBB, bookVerseList )
                    intC = 0 # Get incremented so starts at chapter 1
                    for numVerses in bookVerseList:
                        intC += 1
                        C = str( intC )
                        thisBook.addLine( 'c', C )
                        for intV in range( numVerses+1 ):
                            V = str( intV )
                            #print( BBB, intC, intV )
                            #thisBook.addLine( 'v', str(intV) )
                            result = ourFilter( self.getRawVersifiedData( (BBB,C,V) ), BBB, C, V )
                            #if result: result = result.replace('<FI>','\\add ').replace('<Fi>','\\add*')
                            #if result: result = result.replace('<CM>','') # What is this?
                            if result:
                                if '\n' in result or '\r' in result:
                                    logging.warning( "SwordBibleModule.loadBooks: Result with CR or LF {} {}:{} {}".format( self.name, BBB, C, intV, repr(result) ) )
                                #thisBook.addLine( 'v', "{} {}".format( intV, result ) )
                                thisBook.addLine( 'v', "{}".format( intV ) )
                                thisBook.addLine( 'v~', "{}".format( result.replace( '\n', '' ) ) )
                            elif intV!=0 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                                print( "Why doesn't {} have any text for {} {}:{}".format( self.name, BBB, C, intV ) )
                    self.books[BBB] = thisBook
            del self.store # The original module information is no longer required
            self.cache = {}
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {}.".format( self.name ) )
            return True
        elif BibleOrgSysGlobals.verbosityLevel > 2: print( "  Nothing loaded for {}.".format( self.name ) )
    # end of SwordBibleModule.loadBooks


    def loadBook( self, BBB ):
        """
        Loads a versified Sword module indexes into memory
            and then reads the data and saves it all in our internal format.

        TODO: This should be faster if both the above actions were done together.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordBibleModule.loadBook( ({}) )".format( BBB ) )

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  Loading Sword Bible book {} {}…".format( self.SwordModuleConfiguration.abbreviation, BBB ) )

        SwordModule.loadBook( self, BBB ) # Load the Sword module index
        if self.store: # we loaded something
            ourFilter = self.filterToUSFM if self.SwordModuleConfiguration.modCategory=='Bible' else self.filterToHTML
            # Now we have to iterate through each book, chapter and verse and load into our internal format
            for BBB in self.store:
                if BBB=='FRT': # special case for the front matter
                    #print( self.swordIndex[BBB] )
                    result = ourFilter( self.getRawVersifiedData( ('FRT','0','0') ), 'FRT', '0', '0' )
                    if result:
                        logging.warning( "Didn't process FRT: "+"'"+result+"'" )
                        #halt # Need to process this
                else:
                    thisBook = BibleBook( self, BBB )
                    thisBook.objectNameString = 'SwordBibleModule book object'
                    thisBook.objectTypeString = self.objectTypeString
                    thisBook.sourceFilepath = self.dataFilepath
                    #thisBook.BBB = BBB
                    thisBook.isSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( BBB )
                    #thisBook.replaceAngleBracketsFlag = self.SwordModuleConfiguration.modCategory == 'Bible'
                    thisBook.replaceAngleBracketsFlag = False
                    bookVerseList = self.BibleOrgSystem.getNumVersesList( BBB, allowAlternatives=True )
                    #print( BBB, bookVerseList )
                    intC = 0 # Get incremented so starts at chapter 1
                    for numVerses in bookVerseList:
                        intC += 1
                        C = str( intC )
                        thisBook.addLine( 'c', C )
                        for intV in range( numVerses+1 ):
                            V = str( intV )
                            #print( BBB, intC, intV )
                            #thisBook.addLine( 'v', str(intV) )
                            result = ourFilter( self.getRawVersifiedData( (BBB,C,V) ), BBB, C, V )
                            #if result: result = result.replace('<FI>','\\add ').replace('<Fi>','\\add*')
                            #if result: result = result.replace('<CM>','') # What is this?
                            if result:
                                if '\n' in result or '\r' in result:
                                    logging.warning( "SwordBibleModule.loadBook: Result with CR or LF {} {}:{} {}".format( self.name, BBB, C, intV, repr(result) ) )
                                #thisBook.addLine( 'v', "{} {}".format( intV, result ) )
                                thisBook.addLine( 'v', "{}".format( intV ) )
                                thisBook.addLine( 'v~', "{}".format( result.replace( '\n', '' ) ) )
                            elif intV!=0 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                                print( "Why doesn't {} have any text for {} {}:{}".format( self.name, BBB, C, intV ) )
                    self.books[BBB] = thisBook
            del self.store # The original module information is no longer required
            self.cache = {}
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {}.".format( self.name ) )
            return True
        elif BibleOrgSysGlobals.verbosityLevel > 2: print( "  Nothing loaded for {}.".format( self.name ) )
    # end of SwordBibleModule.loadBook


    def __str__( self ):
        """
        This method returns the string representation of a Sword modules object.

        @return: the name of a Sword object formatted as a string
        @rtype: string
        """
        result = "SwordBibleModule object"
        result += '\n' + SwordModule.__str__( self )
        #from BibleOrgSys.Internals.InternalBible import __str__ as IB__str__
        #result += '\n' + IB__str__( self )
        return result
    # end of SwordBibleModule.__str__


    def test( self, testArray=None ):
        """
        Temporary code (should be in test suite).

        Determines the type of module and tries to run an appropriate test.

        If the testArray is given, compares the results with those in the dictionary.
        """
        foundAny = False
        if testArray is None: ourTestArray = {}
        assert self.versifiedFlag
        assert self.SwordModuleConfiguration.modType in ('RawText','zText','RawCom','RawCom4','zCom','RawFiles',)
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTest Results:" )
        shortTest = (('GEN','1','1',''),('GEN','1','2',''),('GEN','1','3',''),('MAT','1','1',''),('JHN','3','16',''),('REV','1','1','', ),('REV','22','20','', ),('REV','22','21','', ),)
        longTest  = (('GEN','1','1',''),('GEN','1','2',''),('GEN','1','3',''),('PSA','1','1',''),('DAN','1','1',''),('MAL','4','5',''),('MAL','4','6',''), \
                    ('SIR','1','1',''),
                    ('MAT','1','1',''),('MAT','1','2',''),('MAT','2','1',''),('MAT','3','1',''),('MAT','28','20',''), \
                    ('MRK','1','1',''),('MRK','1','2',''),('MRK','2','1',''),('MRK','16','20',''), \
                    ('JHN','1','1',''), \
                    ('LUK','1','1',''),('ACT','1','1',''),('ROM','1','1',''),('TH1','1','1',''), \
                    ('PE1','1','1',''),('JN1','1','1',''),('JN2','1','1',''),('JN3','1','1',''),('JN3','1','14',''),('JDE','1','1',''), \
                    ('REV','1','1',''),('REV','22','1',''),('REV','22','20',''),('REV','22','21',''),('LAO','1','1',''),)
        for ref in longTest:
            if self.BibleOrgSystem.isValidBCVRef( ref, "SwordBibleModule: test references", True ): # May not be true for some versification schemes
                BBB,c,v,s = ref
                assert not s
                vK = SimpleVerseKey( BBB, c, v, s )
                results = self.getContextVerseData( vK )
                if results:
                    result, context = results
                    if result:
                        #print( vK, "result is ", result )
                        foundAny = True
                else: result = context = None
                if (result and BibleOrgSysGlobals.verbosityLevel > 2) or BibleOrgSysGlobals.verbosityLevel > 3: print( "{} {} {}:{} {}".format( self.SwordModuleConfiguration.name, BBB, c, v, result ) )
                if result and BibleOrgSysGlobals.verbosityLevel > 1:
                    formattedResult = ''
                    for entry in result:
                        marker, cleanText, extras = entry.getMarker(), entry.getCleanText(), entry.getExtras()
                        if marker=='v' and cleanText==v: continue
                        if marker=='v~': formattedResult += cleanText.replace('<br />','\n')
                        else: formattedResult += "{}: {}".format( marker, cleanText )
                        if extras: formattedResult += str(extras)
                    print( "{} {}:{} {}".format( BBB, c, v, formattedResult ) )
                if testArray is None: ourTestArray[ref] = result
                elif result != testArray[ref]:
                    logging.error( "{} test gave different result for {}:\n  was {}\n  now {}".format( self.SwordModuleConfiguration.name, ref, testArray[ref], result ) )
            else: logging.warning( "This BCV reference {} is not valid in the {} versification system." \
                        .format( ref, self.SwordModuleConfiguration.confDict['Versification'] if 'Versification' in self.SwordModuleConfiguration.confDict else 'KJV' ) )
        if not foundAny:
            #print( len(self.store), sorted(self.store.keys()) )
            logging.warning( "Couldn't find any relevant information in the {} {}".format( self.SwordModuleConfiguration.name, self.SwordModuleConfiguration.modCategory ) )
            if self.SwordModuleConfiguration.abbreviation in ('personal',): pass # Personal module can be empty
            elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt # Why didn't we find any info in the module???
    # end of SwordBibleModule:test
# end of SwordBibleModule



#@singleton # Can only ever have one instance (but doesn't work for multiprocessing)
class SwordModules:
    """
    This class searches common places in the computer to find and load any Sword modules.
    """


    def __init__( self ): # This can't take other parameters for a singleton
        """
        Creates the object and then loads all the .conf files we can find.

        Doesn't load the actual modules.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModules.__init__()" )

        self.searchFolders = SwordSearchFolders
        self.inMemoryFlag = True

        # Go find them and load them all!
        self.__loadAllConfs()

        #print( "\nindex", len(self.index), self.index )
        #print( "\ncategories", len(self.categories), self.categories.keys(), self.categories )
        assert None not in self.categories
        assert len(self.categories) <= 4 # Expect Commentary, Dictionary, Bible, General
        #print( "\nmodTypes", len(self.modTypes), self.modTypes )
        assert len(self.modTypes) <= 10 # Expect RawText, zText, RawLD, RawLD4, zLD, RawCom, RawCom4, zCom, RawGenBook, RawFiles
        #print( "\nlanguages", len(self.languages), self.languages.keys(), self.languages )
        #print( "\nfeatures", len(self.features), self.features.keys(), self.features )
    # end of SwordModules.__init__


    def augmentModules( self, newPath, someFlag ):
        """
        Adds another path to search for modules in.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModules.augmentModules( {}, {} )".format( newPath, someFlag ) )
            #assert newPath not in self.searchFolders

        global SwordSearchFolders # Saved between object instances
        if newPath not in SwordSearchFolders:
            SwordSearchFolders.append( newPath )
        self.searchFolders = SwordSearchFolders # (now augmented)

        self.__loadAllConfs() # Reload them
    # end of SwordModules.augmentModules


    def __loadAllConfs( self ):
        """
        Load all the conf files that we can find.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModules.__loadAllConfs()" )

        # Things to fill later
        self.folders = [] # Folders where we actually found modules
        self.confs = {} # The SwordModuleConfiguration objects
        self.confKeys = {}
        self.modules = {} # The SwordModule objects
        self.index, self.categories, self.modTypes, self.languages, self.features = {}, {}, {}, {}, {}

        # Go find them and load them all!
        totalFolders = totalCount = 0
        for folder in self.searchFolders:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( '  ' + "__loadAllConfs: checking {}".format( folder ) )
            if os.path.isdir( folder ):
                loadCount = self.__loadConfs( folder ) # Also updates self.confs, self.confKeys, self.index, etc.
                if loadCount:
                    self.folders.append( (folder,loadCount,) )
                    totalCount += loadCount
                    totalFolders += 1
        #print( len(self.confs) ); halt
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Loaded {} Sword .conf files from {} different folders".format( totalCount, totalFolders ) )
    # end of SwordModules.__loadAllConfs


    def __loadConfs( self, loadFolder ):
        """
        Loads the .conf files for all the Sword modules that we can find.

        Called automatically by the __init__ routine.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModules.__loadConfs( {} )".format( loadFolder ) )

        count = 0
        for moduleConfFilename in sorted( os.listdir( os.path.join( loadFolder, 'mods.d/' ) ) ):
            #print( 'moduleConfFilename', repr(moduleConfFilename), repr(loadFolder) )
            if debuggingThisModule: assert moduleConfFilename.endswith( '.conf' ) # Should only be conf files in here
            if not moduleConfFilename.endswith( '.conf' ):
                #if BibleOrgSysGlobals.verbosityLevel > 1:
                logging.warning( _("SwordModules found unexpected file in conf folder: {!r}").format( moduleConfFilename ) )
                continue
            moduleRoughName = moduleConfFilename[:-5] # Remove the .conf from the name
            if moduleRoughName == 'globals': continue # Not a real module, so not wanted here
            #if moduleRoughName not in ('gerhfa2002','oxfordtr','personal','tagalog','tr',): continue # Used for testing specific modules
            count += 1
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "#{}".format( count ), end='' )
            swMC = SwordModuleConfiguration( moduleRoughName, loadFolder )
            swMC.loadConf()
            if BibleOrgSysGlobals.verbosityLevel > 2: print( swMC )
            self.confs[moduleRoughName] = swMC
            self.confKeys[swMC.name] = moduleRoughName

            if moduleRoughName in self.index:
                logging.critical( _("SwordModules found a duplicate {!r} module name -- ignored").format( moduleRoughName ) )
            else: # Add to our indexes
                assert moduleRoughName not in self.index # Don't expect duplicates
                self.index[moduleRoughName] = moduleRoughName
                self.index[moduleRoughName.upper()] = moduleRoughName
                self.index[swMC.name] = moduleRoughName
                self.index[swMC.name.upper()] = moduleRoughName
                try: self.categories[swMC.modCategory].append( moduleRoughName ) # Append to the list
                except KeyError: self.categories[swMC.modCategory] = [ moduleRoughName ] # Start a list
                try: self.modTypes[swMC.modType].append( moduleRoughName ) # Append to the list
                except KeyError: self.modTypes[swMC.modType] = [ moduleRoughName ] # Start a list
                language = swMC.confDict['Lang'] if 'Lang' in swMC.confDict else None
                if language is not None: assert isinstance( language, str )
                #if language is not None: assert 2 <= len(language) <= 3
                try: self.languages[language].append( moduleRoughName ) # Append to the list
                except KeyError: self.languages[language] = [ moduleRoughName ] # Start a list
                features = swMC.confDict['Feature'] if 'Feature' in swMC.confDict else None
                if features is not None:
                    #print( "features", repr(features) )
                    assert isinstance( features, str ) or isinstance( features, list )
                    if isinstance( features, str ): features = [features] # Make it a list of one
                    #or should we just have put the whole list in??? XXXXXXXXXXXXXXXXXXXXXX
                    assert isinstance( features, list )
                    for feature in features:
                        #print( "feature", repr(feature) )
                        assert isinstance( feature, str )
                        try: self.features[feature].append( moduleRoughName ) # Append to the list
                        except KeyError: self.features[feature] = [ moduleRoughName ] # Start a list

        if count:
            if BibleOrgSysGlobals.verbosityLevel > 2 : print( "{} module configurations loaded from {}".format( count, loadFolder ) )
        elif BibleOrgSysGlobals.verbosityLevel > 2: print( "No module configurations found in {}".format( loadFolder ) )
        return count
    # end of SwordModules.__loadConfs


    def __str__( self ):
        """
        This method returns the string representation of a SwordModules object.

        @return: the name of a Sword object formatted as a string
        @rtype: string
        """
        result = "SwordModules object"
        if self.modules: result += ('\n' if result else '') + "  " + _("{} modules loaded ").format( len(self.modules) )
        if self.folders: result += ('\n' if result else '') + "  " + _("Loaded folders: {}").format( self.folders )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if self.modules:
                result += ('\n' if result else '') + "    " + _("Loaded modules: {}").format( [module.name for module in self.modules.values()] )
                if BibleOrgSysGlobals.verbosityLevel > 3:
                    for moduleRoughName,module in sorted(self.modules.items()):
                        result += "\n{}".format( module )
            elif self.confs:
                result += ('\n' if result else '') + "    " + _("Loaded module summaries: {}").format( [module.name for module in self.confs.values()] )
                if BibleOrgSysGlobals.verbosityLevel > 3:
                    for moduleRoughName,module in sorted(self.confs.items()):
                        result += "\n{}".format( module )
        return result
    # end of __str__


    def getModules( self ):
        """
        For Sword compatibility
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModules.getModules()" )

        if self.modules:
            halt # not written yet
        elif self.confs:
            result = []
            for moduleRoughName in sorted(self.confs.keys(), key=str.lower):
                swMC = self.confs[moduleRoughName]
                #print( repr(swMC.modType) )
                result.append( moduleRoughName )
            return result
    # end of SwordModules.getModules


    def getAvailableModuleCodes( self, onlyModuleTypes=None ):
        """
        Module type is a list of strings for the type(s) of modules to include.

        Returns a list of available module codes.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModules.getAvailableModuleCodes( {} )".format( onlyModuleTypes ) )

        if self.modules:
            print( "getAvailableModuleCodes: modules" )
            for j, (moduleRoughName,module) in enumerate( sorted(self.modules.items()) ):
                print( "  ", j, moduleRoughName )
            return [moduleRoughName for moduleRoughName,module in sorted(self.modules.items())]
        elif self.confs:
            print( "getAvailableModuleCodes: confs" )
            #for j, (moduleRoughName,module) in enumerate( sorted(self.confs.items()) ):
                #print( "  ", j, moduleRoughName )
            result = []
            for moduleRoughName in sorted(self.confs.keys(), key=str.lower):
                swMC = self.confs[moduleRoughName]
                #print( repr(swMC.modType) )
                if onlyModuleTypes is None or swMC.modType in onlyModuleTypes:
                    result.append( moduleRoughName )
            return result
            #return [moduleRoughName for moduleRoughName in sorted(self.confs.keys(), key=str.lower)]
    # end of SwordModules.getAvailableModuleCodes


    def getAvailableModuleCodeDuples( self, onlyModuleTypes=None ):
        """
        Module type is a list of strings for the type(s) of modules to include.

        Returns a list of 2-tuples (duples) containing module abbreviation and type
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModules.getAvailableModuleCodeDuples( {} )".format( onlyModuleTypes ) )

        if self.modules:
            print( "getAvailableModuleCodeDuples--modules" )
            for j, (moduleRoughName,module) in enumerate( sorted(self.modules.items()) ):
                print( "  ", j, moduleRoughName )
            for moduleRoughName,module in sorted(self.modules.items()):
                swMC = self.confs[moduleRoughName]
                #print( repr(swMC.modType) )
                if onlyModuleTypes is None or swMC.modType in onlyModuleTypes:
                    result.append( (moduleRoughName,swMC.modType) )
            return result
            #return [moduleRoughName for moduleRoughName,module in sorted(self.modules.items())]
        elif self.confs:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "getAvailableModuleCodeDuples--confs" )
            #for j, (moduleRoughName,module) in enumerate( sorted(self.confs.items()) ):
                #print( "  ", j, moduleRoughName )
            result = []
            for moduleRoughName in sorted(self.confs.keys(), key=str.lower):
                swMC = self.confs[moduleRoughName]
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "  {} {}".format( moduleRoughName, swMC.modType ) )
                #print( repr(swMC.modType), repr(GENERIC_SWORD_MODULE_TYPE_NAMES[swMC.modType]) )
                if onlyModuleTypes is None \
                or swMC.modType in onlyModuleTypes or GENERIC_SWORD_MODULE_TYPE_NAMES[swMC.modType] in onlyModuleTypes:
                    result.append( (moduleRoughName,swMC.modType) )
            return result
    # end of SwordModules.getAvailableModuleCodeDuples


    def getModule( self, moduleRoughName ):
        """
        For Sword compatibility
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SwordModules.getModule( {} )".format( moduleRoughName ) )

        try: swMC = self.confs[moduleRoughName] # Get the correct conf object
        except KeyError: swMC = self.confs[moduleRoughName.lower()] # Get the correct conf object
        #print( "SwordModules.loadModule: modCategory", repr(swMC.modCategory) )
        swM = SwordBibleModule( swMC ) if swMC.modCategory in ('Bible','Commentary',) else SwordModule( swMC )
        return swM
    # end of SwordModules.getModules


    def loadModule( self, moduleRoughName ):
        """
        Loads the requested module indexes or data into memory.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "SwordModules.loadModule( {} )".format( moduleRoughName ) )

        #print( [key for key in self.confs.keys()] )
        try: swMC = self.confs[moduleRoughName] # Get the correct conf object
        except KeyError: swMC = self.confs[moduleRoughName.lower()] # Get the correct conf object
        #print( "SwordModules.loadModule: modCategory", repr(swMC.modCategory) )
        swM = SwordBibleModule( swMC ) if swMC.modCategory in ('Bible','Commentary',) else SwordModule( swMC )
        result = swM.loadBooks( self.inMemoryFlag )
        return result, swM
    # end of SwordModules.loadModule


    def loadAllModules( self, inMemoryFlag=False ):
        """
        Loads all the module indexes or data into memory.

        Used for testing/debugging only.
        """
        MAX_MODULES = 0 # Set to around 300 with 32GB RAM, or set to zero to load all modules without storing them

        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "SwordModules.loadModule( {} )".format( inMemoryFlag ) )

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSwordModules.loadAllModules()…" )
        self.inMemoryFlag = inMemoryFlag
        displayCount = loadCount = 0
        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            parameters = [moduleRoughName for moduleRoughName in self.confs]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self.loadModule, parameters ) # have the pool do our loads
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "SwordModules.loadAllModules: Have results from pool now" )
                assert len(results) == len(parameters)
                for j, theseResults in enumerate( results ):
                    print( j )
                    moduleRoughName = parameters[j]
                    print( " SwordModules.loadAllModules:", j, moduleRoughName )
                    result, swM = theseResults
                    print( " ", " SwordModules.loadAllModules:", j, moduleRoughName, result )
                    displayCount += 1
                    if result:
                        loadCount += 1
                        self.modules[moduleRoughName] = swM
                print( "SwordModules.loadAllModules: All done here1" )
            BibleOrgSysGlobals.alreadyMultiprocessing = False
            print( "SwordModules.loadAllModules: All done here2" )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "SwordModules.loadAllModules here", displayCount, loadCount )
        else: # Just single threaded
            for moduleRoughName, swMC in self.confs.items():
                #if moduleRoughName < 'p': continue # Used for starting load part way through
                #if moduleRoughName not in ('augustin',): continue # Used for testing specific modules
                #if moduleRoughName in ('2tgreek',): continue # Used for avoiding testing specific modules
                #if moduleRoughName > 'a': continue # Use for just testing the first few modules
                if BibleOrgSysGlobals.verbosityLevel > 0: print( "SwordModules.loadAllModules", moduleRoughName )
                displayCount += 1
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSwMod #{}".format( displayCount ) )
                if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 1: print( "#{} again".format( displayCount ) )
                swM = SwordBibleModule( swMC ) if swMC.modCategory in ('Bible','Commentary',) else SwordModule( swMC )
                if swM.loadBooks( self.inMemoryFlag ):
                    loadCount += 1
                    if MAX_MODULES == 0: # Don't bother saving it so memory doesn't fill up
                        self.modules[moduleRoughName] = swM
                if MAX_MODULES > 0 and loadCount >= MAX_MODULES:
                    print( "Break in loading modules after reaching {} (to prevent machine overload)".format( loadCount ) )
                    break

        if loadCount and BibleOrgSysGlobals.verbosityLevel > -1 : print( "{} modules loaded".format( loadCount ) )
        return loadCount
    # end of SwordModules.loadAllModules


    def testAll( self ):
        """
        Runs the module test function on each module.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTesting {} Sword modules…".format( len(self.modules) ) )
        for j, moduleRoughName in enumerate( self.modules ):
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\n#{} Testing {} Sword module…".format( j+1, moduleRoughName ) )
            swM = self.modules[moduleRoughName]
            if not swM.SwordModuleConfiguration.locked: swM.test()
    # end testAll
# end of SwordModules class



def demo() -> None:
    """
    Sword Modules
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    if 0:
        startTime = time.time()

    if 1: # test one module dictionary twice -- loaded into memory, and just indexed
        swordFolder = os.path.join( os.path.expanduser('~'), '.sword/')
        moduleCode = 'webster1913'

        swMC = SwordModuleConfiguration( moduleCode, swordFolder )
        swMC.loadConf()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( swMC )

        swM = SwordModule( swMC )
        swM.loadBooks( inMemoryFlag=True )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( swM )
        if not swM.SwordModuleConfiguration.locked: swM.test()

        swM = SwordModule( swMC )
        swM.loadBooks( inMemoryFlag=False )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( swM )
        if not swM.SwordModuleConfiguration.locked: swM.test()

        del swM

    if 0: # test one (versified) Bible module twice -- loaded into memory, and just indexed
        swordFolder = os.path.join( os.path.expanduser('~'), '.sword/')
        moduleCode = '2tgreek'
        #moduleCode = "finbiblia"
        #moduleCode = "vulgate_hebps"
        #moduleCode = "ylt"

        swMC = SwordModuleConfiguration( moduleCode, swordFolder )
        swMC.loadConf()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( swMC )

        swM = SwordModule( swMC )
        swM.loadBooks( inMemoryFlag=True )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( swM )
        if not swM.SwordModuleConfiguration.locked: swM.test()

        swM = SwordModule( swMC )
        swM.loadBooks( inMemoryFlag=False )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( swM )
        if not swM.SwordModuleConfiguration.locked: swM.test()

        del swM

    if 0: # test one (versified) commentary module twice -- loaded into memory, and just indexed
        swordFolder = os.path.join( os.path.expanduser('~'), '.sword/')
        moduleCode = 'barnes'

        swMC = SwordModuleConfiguration( moduleCode, swordFolder )
        swMC.loadConf()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( swMC )

        if 1:
            swM = SwordModule( swMC )
            swM.loadBooks( inMemoryFlag=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( swM )
            if not swM.SwordModuleConfiguration.locked: swM.test()

        if 1:
            swM = SwordModule( swMC )
            swM.loadBooks( inMemoryFlag=False )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( swM )
            if not swM.SwordModuleConfiguration.locked: swM.test()

        del swM

    if 0: # test one imported Bible (or Bible commentary) module
        swordFolder = os.path.join( os.path.expanduser('~'), '.sword/')
        #moduleCode = '2tgreek'
        moduleCode = 'sahidicbible'
        #moduleCode = 'barnes'
        #moduleCode = 'finbiblia'
        #moduleCode = 'ylt'

        swMC = SwordModuleConfiguration( moduleCode, swordFolder )
        swMC.loadConf()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( swMC )

        swBM = SwordBibleModule( swMC )
        if not swBM.SwordModuleConfiguration.locked:
            swBM.loadBooks()
            if BibleOrgSysGlobals.verbosityLevel > 1: print( swBM )
            #swBM.discover()
            #swBM.check()
            swBM.test()

        del swBM

    if 0: # test lots of modules
        swMs = SwordModules()
        swMs.loadAllModules( inMemoryFlag = False )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( '\n\n{}'.format( swMs ) )
        if BibleOrgSysGlobals.strictCheckingFlag: swMs.testAll()

    if 0 and BibleOrgSysGlobals.verbosityLevel > 0:
        endTime = time.time()
        elapsedTime = endTime - startTime
        print( "Elapsed time was", elapsedTime )
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of SwordModules.py
