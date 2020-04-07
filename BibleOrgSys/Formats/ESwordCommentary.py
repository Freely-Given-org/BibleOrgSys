#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ESwordCommentary.py
#
# Module handling "e-Sword" Bible commentary module files
#
# Copyright (C) 2013-2018 Robert Hunt
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
Module reading and loading e-Sword Bible commentary files.
These can be downloaded from: http://www.BibleSupport.com and http://www.biblemodulesresource.com.

e-Sword Bible commentary modules use RTF internally for formatting.
    See http://en.wikipedia.org/wiki/Rich_Text_Format
    and http://e-sword-users.org/users/node/3969

    Database has one verse per entry (KJV versification)
    OT has 23145 lines
    NT has 7957 lines
    Bible has 31102 lines.

e.g.,
    In the beginning of God's preparing the heavens and the earth--
    the earth hath existed waste and void, and darkness <FI>is<Fi> on the face of the deep, and the Spirit of God fluttering on the face of the waters,<CM>
    and God saith, `Let light be;' and light is.
    And God seeth the light that <FI>it is<Fi> good, and God separateth between the light and the darkness,
    and God calleth to the light `Day,' and to the darkness He hath called `Night;' and there is an evening, and there is a morning--day one.<CM>
    And God saith, `Let an expanse be in the midst of the waters, and let it be separating between waters and waters.'
    And God maketh the expanse, and it separateth between the waters which <FI>are<Fi> under the expanse, and the waters which <FI>are<Fi> above the expanse: and it is so.
    And God calleth to the expanse `Heavens;' and there is an evening, and there is a morning--day second.<CM>
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2018-12-12' # by RJH
SHORT_PROGRAM_NAME = "e-SwordCommentary"
PROGRAM_NAME = "e-Sword Commentary format handler"
PROGRAM_VERSION = '0.07'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, re
import sqlite3
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Formats.ESwordBible import handleESwordLine



FILENAME_ENDINGS_TO_ACCEPT = ('.CMTI','.CMTX') # Must be UPPERCASE here
COMMENTARY_FILENAME_ENDINGS_TO_ACCEPT = ('.CMTI','.CMTX') # Must be UPPERCASE here



def ESwordCommentaryFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for e-Sword Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one e-Sword Bible is found,
        returns the loaded ESwordCommentary object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordCommentaryFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ESwordCommentaryFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ESwordCommentaryFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " ESwordCommentaryFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS: continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            #ignore = False
            #for ending in filenameEndingsToIgnore:
                #if somethingUpper.endswith( ending): ignore=True; break
            #if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
            if somethingUpperExt in FILENAME_ENDINGS_TO_ACCEPT:
                foundFiles.append( something )

    # See if there's an ESwordCommentary project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordCommentaryFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "{} doing autoload of {}…".format( programNameVersion, lastFilenameFound ) )
            eSB = ESwordCommentary( givenFolderName, lastFilenameFound )
            if autoLoad or autoLoadBooks: eSB.preload()
            if autoLoadBooks: eSB.load() # Load and process the database
            return eSB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("ESwordCommentaryFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    ESwordCommentaryFileCheck: Looking for files in {!r}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                #ignore = False
                #for ending in filenameEndingsToIgnore:
                    #if somethingUpper.endswith( ending): ignore=True; break
                #if ignore: continue
                #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                if somethingUpperExt in FILENAME_ENDINGS_TO_ACCEPT:
                    foundSubfiles.append( something )

        # See if there's an e-Sword project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordCommentaryFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad and autoLoadBooks):
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "{} doing autoload of {}…".format( programNameVersion, foundProjects[0][1] ) )
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            eSB = ESwordCommentary( foundProjects[0][0], foundProjects[0][1] )
            if autoLoad or autoLoadBooks: eSB.preload()
            if autoLoadBooks: eSB.load() # Load and process the database
            return eSB
        return numFound
# end of ESwordCommentaryFileCheck



class ESwordCommentary( Bible ):
    """
    Class for reading, validating, and converting ESwordCommentary files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "ESwordCommentary.init( {!r}, {!r}, {!r} )".format( sourceFolder, givenFilename, encoding ) )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'e-Sword Commentary object'
        self.objectTypeString = 'e-Sword-Commentary'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("ESwordCommentary: File {!r} is unreadable").format( self.sourceFilepath ) )

        filenameBits = os.path.splitext( self.sourceFilename )
        self.name = filenameBits[0]
        self.fileExtension = filenameBits[1]
        #print( "fileExtension", self.fileExtension )
        self.tableNames = ('Books','Chapters','Verses') if self.fileExtension.upper()=='.CMTX' else ('BookCommentary','ChapterCommentary','VerseCommentary')

        #if self.fileExtension.upper().endswith('X'):
            #logging.warning( _("ESwordCommentary: File {!r} is encrypted").format( self.sourceFilepath ) )
        self.preloaded = False
    # end of ESwordCommentary.__init__


    #def checkForExtraMaterial( self, cursor, BOS ):
        #"""
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( _("checkForExtraMaterial( …, … )") )

        #if BibleOrgSysGlobals.verbosityLevel > 0: print( _("Checking {} for extra material…").format( self.sourceFilepath ) )

        #cursor.execute('select * from Bible' )
        #for row in cursor:
            #assert len(row) == 4
            #BBBn, C, V, text = row # First three are integers, the last is a string
            ##print( repr(BBBn), repr(C), repr(V), repr(text) )
            #if BBBn<1 or BBBn>66: print( "Found book number {}".format( BBBn ) )
            #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( BBBn )
            #if not BOS.isValidBCVRef( (BBB,str(C),str(V),''), 'checkForExtraMaterial' ):
                #logging.error( "checkForExtraMaterial: {} contains {} {}:{} {!r}".format( self.name, BBB, C, V, text ) )
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    #print( "checkForExtraMaterial: {} contains {} {}:{} {!r}".format( self.name, BBB, C, V, text ) )
                    ##halt
    ## end of ESwordCommentary.checkForExtraMaterial


    def preload( self ):
        """
        Load Bible details out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("ESwordCommentary.preload()") )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Preloading {}…").format( self.sourceFilepath ) )
        loadErrors = []

        fileExtensionUpper = self.fileExtension.upper()
        if fileExtensionUpper not in FILENAME_ENDINGS_TO_ACCEPT:
            logging.critical( "{} doesn't appear to be a e-Sword file".format( self.sourceFilename ) )
        elif not self.sourceFilename.upper().endswith( COMMENTARY_FILENAME_ENDINGS_TO_ACCEPT[0] ):
            logging.critical( "{} doesn't appear to be a e-Sword Commentary file".format( self.sourceFilename ) )

        connection = sqlite3.connect( self.sourceFilepath )
        connection.row_factory = sqlite3.Row # Enable row names
        self.cursor = connection.cursor()

        # First get the settings
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['e-Sword-Commentary'] = {}
        self.cursor.execute( 'select * from Details' )
        row = self.cursor.fetchone()
        for key in row.keys():
            self.suppliedMetadata['e-Sword-Commentary'][key] = row[key]
        #print( self.suppliedMetadata['e-Sword-Commentary'] ); halt
        #if 'Description' in self.settingsDict and len(self.settingsDict['Description'])<40: self.name = self.settingsDict['Description']
        #if 'Abbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['Abbreviation']
        if 'encryption' in self.suppliedMetadata['e-Sword-Commentary']:
            logging.critical( "{} is encrypted: level {}".format( self.sourceFilename, self.suppliedMetadata['e-Sword-Commentary']['encryption'] ) )


        ## Just get some information from the file
        #self.cursor.execute( 'select * from Bible' )
        #rows = self.cursor.fetchall()
        #numRows = len(rows)
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( '{} rows found'.format( numRows ) )
        #BBBn1 = rows[0][0]
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( 'First book number is {}'.format( BBBn1 ) )
        #del rows
        #BBB1 = None
        #if BBBn1 <= 66: BBB1 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( BBBn1 )


        #testament = BBB = None
        #booksExpected = textLineCountExpected = 0
        #if self.suppliedMetadata['e-Sword-Commentary']['OT'] and self.suppliedMetadata['e-Sword-Commentary']['NT']:
            #testament, BBB = 'BOTH', 'GEN'
            #booksExpected, textLineCountExpected = 66, 31102
        #elif self.suppliedMetadata['e-Sword-Commentary']['OT']:
            #testament, BBB = 'OT', 'GEN'
            #booksExpected, textLineCountExpected = 39, 23145
        #elif self.suppliedMetadata['e-Sword-Commentary']['NT']:
            #testament, BBB = 'NT', 'MAT'
            #booksExpected, textLineCountExpected = 27, 7957
        #elif self.suppliedMetadata['e-Sword-Commentary']['Abbreviation'] == 'VIN2011': # Handle encoding error
            #logging.critical( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Commentary'] ) )
            #loadErrors.append( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Commentary'] ) )
            #testament, BBB = 'BOTH', 'GEN'
            #booksExpected, textLineCountExpected = 66, 31102
        #elif self.suppliedMetadata['e-Sword-Commentary']['Apocrypha']: # incomplete
            #testament, BBB = 'AP', 'XXX'
            #booksExpected, textLineCountExpected = 99, 999999
            #halt
        #if not BBB:
            #logging.critical( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Commentary'] ) )
            #loadErrors.append( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Commentary'] ) )
            #if 0:
                #cursor.execute( 'select * from Bible' )
                #rows = cursor.fetchall()
                #print( "rows", len(rows) )
                #for row in rows:
                    #assert len(row) == 4
                    #BBBn, C, V, text = row # First three are integers, the last is a string
                    #print( BBBn, C, V, repr(text) )
                    #if C==2: break
                #del rows # Takes a lot of memory
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            #print( "Testament={} BBB={} BBB1={}, bE={}, tLCE={} nR={}".format( testament, BBB, BBB1, booksExpected, textLineCountExpected, numRows ) )
        #if BBB1 != BBB:
            #logging.critical( "First book seems wrong: {} instead of {}".format( BBB1, BBB ) )
            #loadErrors.append( "First book seems wrong: {} instead of {}".format( BBB1, BBB ) )
            #if not BBB: BBB = BBB1
        #if numRows != textLineCountExpected:
            #logging.critical( "Row count for {} seems wrong: {} instead of {}".format( self.sourceFilename, numRows, textLineCountExpected ) )
            #loadErrors.append( "Row count for {} seems wrong: {} instead of {}".format( self.sourceFilename, numRows, textLineCountExpected ) )
        ##halt

        self.BibleOrganisationalSystem = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )
        assert self.BibleOrganisationalSystem is not None
        self.preloaded = True
    # end of ESwordCommentary.preload


    def load( self ):
        """
        Load all the books out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("load()") )
        if not self.preloaded: self.preload()

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )
        loadErrors = []

        #fileExtensionUpper = self.fileExtension.upper()
        #if fileExtensionUpper not in FILENAME_ENDINGS_TO_ACCEPT:
            #logging.critical( "{} doesn't appear to be a e-Sword file".format( self.sourceFilename ) )
        #elif not self.sourceFilename.upper().endswith( COMMENTARY_FILENAME_ENDINGS_TO_ACCEPT[0] ):
            #logging.critical( "{} doesn't appear to be a e-Sword Commentary file".format( self.sourceFilename ) )

        #connection = sqlite3.connect( self.sourceFilepath )
        #connection.row_factory = sqlite3.Row # Enable row names
        #cursor = connection.cursor()

        ## First get the settings
        #if self.suppliedMetadata is None: self.suppliedMetadata = {}
        #self.suppliedMetadata['e-Sword-Commentary'] = {}
        #cursor.execute( 'select * from Details' )
        #row = cursor.fetchone()
        #for key in row.keys():
            #self.suppliedMetadata['e-Sword-Commentary'][key] = row[key]
        ##print( self.suppliedMetadata['e-Sword-Commentary'] ); halt
        ##if 'Description' in self.settingsDict and len(self.settingsDict['Description'])<40: self.name = self.settingsDict['Description']
        ##if 'Abbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['Abbreviation']
        #if 'encryption' in self.suppliedMetadata['e-Sword-Commentary']:
            #logging.critical( "{} is encrypted: level {}".format( self.sourceFilename, self.suppliedMetadata['e-Sword-Commentary']['encryption'] ) )


        # Get the data out of the sqlite database
        # NOTE: There may or may not be data in the book and chapter tables
        # Start with the book table
        self.cursor.execute( 'select * from {}'.format( self.tableNames[0] ) )
        bookRows = self.cursor.fetchall()
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            print( '{} book rows found'.format( len(bookRows) ) )
        BBBn1 = BBB1 = None
        BBBList = []
        if bookRows:
            BBBn1 = bookRows[0][0]
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
                print( '  First book number is {}'.format( BBBn1 ) )
            if BBBn1 <= 66: BBB1 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( BBBn1 )

            bookCommentary = {}
            for bkNum,line in bookRows:
                BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bkNum )
                BBBList.append( BBB )
                #print( "Bk={} BBB={} Line: {!r}…".format( bkNum, BBB, line[:120] ) )
                bookCommentary[BBB] = line
        del bookRows

        # Now the chapter table
        BBBChList = []
        chapterCommentary = {}
        self.cursor.execute( 'select * from {}'.format( self.tableNames[1] ) )
        chapterRows = self.cursor.fetchall()
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            print( '{} chapter rows found'.format( len(chapterRows) ) )
        for bkNum,chNum,line in chapterRows:
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bkNum )
            if BBBn1 is None:
                BBBn1, BBB1 = bkNum, BBB
            if BBB not in BBBList:
                BBBList.append( BBB )
            BBBChList.append( (BBB,chNum) )
            #print( "BBB={} Ch={} Line: {!r}…".format( BBB, chNum, line[:120] ) )
            if BBB not in chapterCommentary: chapterCommentary[BBB] = {}
            chapterCommentary[BBB][chNum] = line
        del chapterRows

        # Now the verse table (we always expect data here)
        verseCommentary = {}
        self.cursor.execute( 'select * from {}'.format( self.tableNames[2] ) )
        verseRows = self.cursor.fetchall()
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            print( '{} verse rows found'.format( len(verseRows) ) )
        for bkNum,chBegin,chEnd,vBegin,vEnd,line in verseRows:
            #print( bkNum,chBegin,chEnd,vBegin,vEnd )
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bkNum )
            if BBBn1 is None:
                BBBn1, BBB1 = bkNum, BBB
            if BBB not in BBBList:
                BBBList.append( BBB )
            #assert (BBB,chBegin) in BBBChList # Not always true
            #assert chEnd == chBegin # Not true in John Darby's Synopsis of the New Testament
            #if vEnd == vBegin:
                #print( "{} {}:{} Line: {!r}…".format( BBB, chBegin, vBegin, line[:120] ) )
            #else: print( "{} {}:{}-{} Line: {!r}…".format( BBB, chBegin, vBegin, vEnd, line[:120] ) )
            if BBB not in verseCommentary: verseCommentary[BBB] = {}
            if chBegin not in verseCommentary[BBB]: verseCommentary[BBB][chBegin] = {}
            verseCommentary[BBB][chBegin][vBegin] = (chBegin,chEnd,vBegin,vEnd,line)
        del verseRows

        # Create and process the books
        if BibleOrgSysGlobals.verbosityLevel>1: print( "Processing {} books…".format( len(BBBList) ) )
        ourGlobals = {}
        for bookCount,BBB in enumerate( BBBList ):
            if BibleOrgSysGlobals.verbosityLevel>2: print( "  Processing {}…".format( BBB ) )
            thisBook = BibleBook( self, BBB )
            thisBook.objectNameString = 'e-Sword Commentary Book object'
            thisBook.objectTypeString = 'e-Sword-Commentary'

            verseList = self.BibleOrganisationalSystem.getNumVersesList( BBB )

            try:
                if BBB in bookCommentary:
                    handleESwordLine( self, self.name, BBB, '0', '0', bookCommentary[BBB], thisBook, ourGlobals )
            except UnboundLocalError: pass # no bookCommentary
            numC = len(verseList)
            for C in range( 1, numC+1 ):
                if BBB in chapterCommentary and C in chapterCommentary[BBB]:
                    handleESwordLine( self, self.name, BBB, C, '0', chapterCommentary[BBB][C], thisBook, ourGlobals )
                numV = verseList[C-1]
                for V in range( 1, numV+1 ):
                    if BBB in verseCommentary and C in verseCommentary[BBB] \
                    and V in verseCommentary[BBB][C]:
                        chBegin,chEnd,vBegin,vEnd,line = verseCommentary[BBB][C][V]
                        #assert chEnd == chBegin # Not guaranteed (obviously)
                        assert vBegin == V
                        VV = vBegin if (vEnd==vBegin or chEnd!=chBegin) else '{}-{}'.format( vBegin, vEnd )
                        handleESwordLine( self, self.name, BBB, C, VV, line, thisBook, ourGlobals )

            if BibleOrgSysGlobals.verbosityLevel > 3: print( "  e-Sword saving", BBB, bookCount+1 )
            self.stashBook( thisBook )

        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
            #self.checkForExtraMaterial( self.cursor, self.BibleOrganisationalSystem )
        self.cursor.close()
        del self.cursor
        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
        self.applySuppliedMetadata( 'e-Sword-Commentary' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of ESwordCommentary.load


    def loadBook( self, BBB ):
        """
        Load the requested book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("loadBook( {} )").format( BBB ) )

        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading e-Sword-Commentary {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} from {}…").format( BBB, self.sourceFilepath ) )
        loadErrors = []

        # Create the book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'e-Sword Bible Commentary object'
        thisBook.objectTypeString = 'e-Sword-Commentary'

        verseList = self.BibleOrganisationalSystem.getNumVersesList( BBB )
        nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )

        ourGlobals = {}
        #continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        displayedEncryptError = False

        C = V = '0'
        self.cursor.execute('select Comments from {} where Book=?'.format( self.tableNames[0] ), (nBBB,) )
        try:
            row = self.cursor.fetchone()
            assert len(row) == 1
            line = row[0]
        except TypeError: # This reference is missing (row is None)
            #logging.info( "ESwordCommentary.load: No book commentary for {}".format( BBB ) )
            line = None
        #print ( nBBB, BBB, C, V, 'e-Sw file line is "' + line + '"' )
        if line is None:
            logging.warning( "ESwordCommentary.load: Have missing commentary book line at {} {}:{}".format( BBB, C, V ) )
        else: # line is not None
            if not isinstance( line, str ):
                if 'encryption' in self.suppliedMetadata['e-Sword-Commentary']:
                    logging.critical( "ESwordCommentary.load: Unable to decrypt commentary book line at {} {}:{} {!r}".format( BBB, C, V, line ) )
                    displayedEncryptError = True
                else:
                    logging.critical( "ESwordCommentary.load: Probably encrypted module: Unable to decode commentary book line at {} {}:{} {!r} {}".format( BBB, C, V, line, self.suppliedMetadata['e-Sword-Commentary'] ) )
                    displayedEncryptError = True
            elif not line:
                logging.warning( "ESwordCommentary.load: Found blank commentary book line at {} {}:{}".format( BBB, C, V ) )
            else:
                handleESwordLine( self, self.name, BBB, '0', '0', line, thisBook, ourGlobals )
                haveLines = True

        numC = len(verseList)
        for C in range( 1, numC+1 ):
            self.cursor.execute('select Comments from {} where Book=? and Chapter=?'.format( self.tableNames[1] ), (nBBB,C) )
            try:
                row = self.cursor.fetchone()
                assert len(row) == 1
                line = row[0]
            except TypeError: # This reference is missing (row is None)
                #logging.info( "ESwordCommentary.load: No chapter commentary for {} {}".format( BBB, C ) )
                line = None
            #print ( nBBB, BBB, C, V, 'e-Sw file line is "' + line + '"' )
            if line is None:
                logging.warning( "ESwordCommentary.load: Have missing commentary chapter line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not isinstance( line, str ):
                    if 'encryption' in self.suppliedMetadata['e-Sword-Commentary']:
                        if not displayedEncryptError:
                            logging.critical( "ESwordCommentary.load: Unable to decrypt commentary chapter line at {} {}:{} {!r}".format( BBB, C, V, line ) )
                            displayedEncryptError = True
                        break
                    else:
                        if not displayedEncryptError:
                            logging.critical( "ESwordCommentary.load: Probably encrypted module: Unable to decode commentary chapter line at {} {}:{} {!r} {}".format( BBB, C, V, line, self.suppliedMetadata['e-Sword-Commentary'] ) )
                            displayedEncryptError = True
                        break
                elif not line:
                    logging.warning( "ESwordCommentary.load: Found blank commentary chapter line at {} {}:{}".format( BBB, C, V ) )
                else:
                    handleESwordLine( self, self.name, BBB, C, '0', line, thisBook, ourGlobals )
                    haveLines = True

            numV = verseList[C-1]
            for V in range( 1, numV+1 ):
                self.cursor.execute('select * from {} where Book=? and ChapterBegin=? and VerseBegin=?'.format( self.tableNames[2] ), (nBBB,C,V) )
                try:
                    row = self.cursor.fetchone()
                    bkNum,chBegin,chEnd,vBegin,vEnd,line = row
                except TypeError: # This reference is missing (row is None)
                    #logging.info( "ESwordCommentary.load: No verse commentary for {} {}".format( BBB, C, V ) )
                    line = None
                #print ( nBBB, BBB, C, V, 'e-Sw file line is "' + line + '"' )
                if line is None:
                    logging.warning( "ESwordCommentary.load: Have missing commentary verse line at {} {}:{}".format( BBB, C, V ) )
                else: # line is not None
                    if not isinstance( line, str ):
                        if 'encryption' in self.suppliedMetadata['e-Sword-Commentary']:
                            if not displayedEncryptError:
                                logging.critical( "ESwordCommentary.load: Unable to decrypt commentary verse line at {} {}:{} {!r}".format( BBB, C, V, line ) )
                                displayedEncryptError = True
                            break
                        else:
                            if not displayedEncryptError:
                                logging.critical( "ESwordCommentary.load: Probably encrypted module: Unable to decode commentary verse line at {} {}:{} {!r} {}".format( BBB, C, V, line, self.suppliedMetadata['e-Sword-Commentary'] ) )
                                displayedEncryptError = True
                            break
                    elif not line:
                        logging.warning( "ESwordCommentary.load: Found blank commentary verse line at {} {}:{}".format( BBB, C, V ) )
                    else:
                        # NOTE: vEnd and chEnd are not handled that same here as in .load() above XXXXXXXXXXXXXXX
                        handleESwordLine( self, self.name, BBB, C, V, line, thisBook, ourGlobals )
                        haveLines = True
                #if BBB in verseCommentary and C in verseCommentary[BBB] \
                #and V in verseCommentary[BBB][C]:
                    #chBegin,chEnd,vBegin,vEnd,line = verseCommentary[BBB][C][V]
                    #assert chEnd == chBegin
                    #assert vBegin == V
                    #VV = vBegin if vEnd == vBegin else '{}-{}'.format( vBegin, vEnd )
                    #self.handleLine( self.name, BBB, C, VV, line, thisBook, ourGlobals )

        if haveLines:
            if BibleOrgSysGlobals.verbosityLevel > 3: print( "  ESwordCommentary saving", BBB )
            self.stashBook( thisBook )
    # end of ESwordCommentary.loadBook
# end of ESwordCommentary class



def createESwordCommentaryModule( self, outputFolder, controlDict ):
    """
    Create a SQLite3 database module for the Windows program e-Sword.

    self here is a Bible object with _processedLines
    """
    import zipfile
    from BibleOrgSys.Reference.USFM3Markers import OFTEN_IGNORED_USFM_HEADER_MARKERS, USFM_ALL_INTRODUCTION_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS, removeUSFMCharacterField, replaceUSFMCharacterFields
    from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS, BOS_NESTING_MARKERS
    from BibleOrgSys.Formats.theWordBible import theWordOTBookLines, theWordNTBookLines, theWordBookLines, theWordIgnoredIntroMarkers

    def adjustLine( BBB, C, V, originalLine ):
        """
        Handle pseudo-USFM markers within the line (cross-references, footnotes, and character formatting).

        Parameters are the Scripture reference (for error messsages)
            and the line (string) containing the backslash codes.

        Returns a string with the backslash codes replaced by e-Sword RTF formatting codes.
        """
        line = originalLine # Keep a copy of the original line for error messages

        if '\\x' in line: # Remove cross-references completely (why???)
            #line = line.replace('\\x ','<RX>').replace('\\x*','<Rx>')
            line = removeUSFMCharacterField( 'x', line, closedFlag=True ).lstrip() # Remove superfluous spaces

        if '\\f' in line: # Handle footnotes
            line = removeUSFMCharacterField( 'f', line, closedFlag=True ).lstrip() # Remove superfluous spaces
            #for marker in ( 'fr', 'fm', ): # simply remove these whole field
                #line = removeUSFMCharacterField( marker, line, closedFlag=None )
            #for marker in ( 'fq', 'fqa', 'fl', 'fk', ): # italicise these ones
                #while '\\'+marker+' ' in line:
                    ##print( BBB, C, V, marker, line.count('\\'+marker+' '), line )
                    ##print( "was", "'"+line+"'" )
                    #ix = line.find( '\\'+marker+' ' )
                    #assert ix != -1
                    #ixEnd = line.find( '\\', ix+len(marker)+2 )
                    #if ixEnd == -1: # no following marker so assume field stops at the end of the line
                        #line = line.replace( '\\'+marker+' ', '<i>' ) + '</i>'
                    #elif line[ixEnd:].startswith( '\\'+marker+'*' ): # replace the end marker also
                        #line = line.replace( '\\'+marker+' ', '<i>' ).replace( '\\'+marker+'*', '</i>' )
                    #else: # leave the next marker in place
                        #line = line[:ixEnd].replace( '\\'+marker+' ', '<i>' ) + '</i>' + line[ixEnd:]
            #for marker in ( 'ft', ): # simply remove these markers (but leave behind the text field)
                #line = line.replace( '\\'+marker+' ', '' ).replace( '\\'+marker+'*', '' )
            ##for caller in '+*abcdefghijklmnopqrstuvwxyz': line.replace('\\f '+caller+' ','<RF>') # Handle single-character callers
            #line = re.sub( r'(\\f [a-z+*]{1,4} )', '<RF>', line ) # Handle one to three character callers
            #line = line.replace('\\f ','<RF>').replace('\\f*','<Rf>') # Must be after the italicisation
            ##if '\\f' in originalLine:
                ##print( "o", originalLine )
                ##print( "n", line )
                ##halt

        if '\\' in line: # Handle character formatting fields
            line = removeUSFMCharacterField( 'fig', line, closedFlag=True ) # Remove figures
            line = removeUSFMCharacterField( 'str', line, closedFlag=True ) # Remove Strong's numbers
            line = removeUSFMCharacterField( 'sem', line, closedFlag=True ) # Remove semantic tagging
            replacements = (
                ( ('add',), '~^~cf15~^~i','~^~cf0~^~i0' ),
                ( ('qt',), '<FO>','<Fo>' ),
                ( ('wj',), '<FR>','<Fr>' ),
                ( ('ca','va',), '(',')' ),
                ( ('bdit',), '<b><i>','</i></b>' ),
                ( ('bd','em','k',), '<b>','</b>' ),
                ( ('it','rq','bk','dc','qs','sig','sls','tl',), '<i>','</i>' ),
                ( ('nd','sc',), '<font size=-1>','</font>' ),
                )
            line = replaceUSFMCharacterFields( replacements, line ) # This function also handles USFM 2.4 nested character markers
            if '\\nd' not in originalLine and '\\+nd' not in originalLine:
                line = line.replace('LORD', '<font size=-1>LORD</font>')
                #line = line.replace('\\nd ','<font size=-1>',).replace('\\nd*','</font>').replace('\\+nd ','<font size=-1>',).replace('\\+nd*','</font>')
            #else:
                #line = line.replace('LORD', '<font size=-1>LORD</font>')
            #line = line.replace('\\add ','<FI>').replace('\\add*','<Fi>').replace('\\+add ','<FI>').replace('\\+add*','<Fi>')
            #line = line.replace('\\qt ','<FO>').replace('\\qt*','<Fo>').replace('\\+qt ','<FO>').replace('\\+qt*','<Fo>')
            #line = line.replace('\\wj ','<FR>').replace('\\wj*','<Fr>').replace('\\+wj ','<FR>').replace('\\+wj*','<Fr>')

        #if '\\' in line: # Output simple HTML tags (with no semantic info)
            #line = line.replace('\\bdit ','<b><i>').replace('\\bdit*','</i></b>').replace('\\+bdit ','<b><i>').replace('\\+bdit*','</i></b>')
            #for marker in ( 'it', 'rq', 'bk', 'dc', 'qs', 'sig', 'sls', 'tl', ): # All these markers are just italicised
                #line = line.replace('\\'+marker+' ','<i>').replace('\\'+marker+'*','</i>').replace('\\+'+marker+' ','<i>').replace('\\+'+marker+'*','</i>')
            #for marker in ( 'bd', 'em', 'k', ): # All these markers are just bolded
                #line = line.replace('\\'+marker+' ','<b>').replace('\\'+marker+'*','</b>').replace('\\+'+marker+' ','<b>').replace('\\+'+marker+'*','</b>')
            #line = line.replace('\\sc ','<font size=-1>',).replace('\\sc*','</font>').replace('\\+sc ','<font size=-1>',).replace('\\+sc*','</font>')

        # Check what's left at the end
        if '\\' in line:
            logging.warning( "toESword.adjustLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, line ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "toESword.adjustLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, line ) )
                halt
        return line
    # end of toESword.adjustLine


    def handleIntroduction( BBB, bookData, ourGlobals ):
        """
        Go through the book introduction (if any) and extract main titles for e-Sword export.

        Parameters are BBB (for error messages),
            the actual book data, and
            ourGlobals dictionary for persistent variables.

        Returns the information in a composed line string.
        """
        intC, intV = -1, 0
        composedLine = ''
        while True:
            #print( "toESword.handleIntroduction", BBB, intC, intV )
            try: result = bookData.getContextVerseData( (BBB,str(intC),str(intV),) ) # Currently this only gets one line
            except KeyError: break # Reached the end of the introduction
            verseData, context = result
            if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag:
                assert len(verseData) == 1 # in the introductory section (each individual line is a "verse")
            marker, text = verseData[0].getMarker(), verseData[0].getFullText()
            if marker not in theWordIgnoredIntroMarkers and '¬' not in marker and marker not in BOS_ADDED_NESTING_MARKERS: # don't need added markers here either
                if   marker in ('mt1','mte1',): composedLine += '<TS1>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker in ('mt2','mte2',): composedLine += '<TS2>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker in ('mt3','mte3',): composedLine += '<TS3>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker in ('mt4','mte4',): composedLine += '<TS3>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker=='ms1': composedLine += '<TS2>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker in ('ms2','ms3','ms4'): composedLine += '<TS3>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker=='mr': composedLine += '<TS3>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                else:
                    logging.warning( "toESword.handleIntroduction: doesn't handle {} {!r} yet".format( BBB, marker ) )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "toESword.handleIntroduction: doesn't handle {} {!r} yet".format( BBB, marker ) )
                        halt
                    ourGlobals['unhandledMarkers'].add( marker + ' (in intro)' )
            intV += 1 # Step to the next introductory section "verse"

        # Check what's left at the end
        if '\\' in composedLine:
            logging.warning( "toESword.handleIntroduction: Doesn't handle formatted line yet: {} {!r}".format( BBB, composedLine ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "toESword.handleIntroduction: Doesn't handle formatted line yet: {} {!r}".format( BBB, composedLine ) )
                halt
        return composedLine.replace( '~^~', '\\' )
    # end of toESword.handleIntroduction


    def composeVerseLine( BBB, C, V, verseData, ourGlobals ):
        """
        Composes a single line representing a verse.

        Parameters are the Scripture reference (for error messages),
            the verseData (a list of InternalBibleEntries: pseudo-USFM markers and their contents),
            and a ourGlobals dictionary for holding persistent variables (between calls).

        This function handles the paragraph/new-line markers;
            adjustLine (above) is called to handle internal/character markers.

        Returns the composed line.
        """
        #print( "toESword.composeVerseLine( {} {}:{} {} {}".format( BBB, C, V, verseData, ourGlobals ) )
        composedLine = ourGlobals['line'] # We might already have some book headings to precede the text for this verse
        ourGlobals['line'] = '' # We've used them so we don't need them any more
        #marker = text = None

        vCount = 0
        lastMarker = gotVP = None
        #if BBB=='MAT' and C==4 and 14<V<18: print( BBB, C, V, ourGlobals, verseData )
        for verseDataEntry in verseData:
            marker, text = verseDataEntry.getMarker(), verseDataEntry.getFullText()
            if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS: continue # Just ignore added markers -- not needed here
            if marker in ('c','c#','cl','cp','rem',): lastMarker = marker; continue  # ignore all of these for this

            if marker == 'vp#': # This precedes a v field and has the verse number to be printed
                gotVP = text # Just remember it for now
            elif marker == 'v': # handle versification differences here
                vCount += 1
                if vCount == 1: # Handle verse bridges
                    if text != str(V):
                        composedLine += '<sup>('+text+')</sup> ' # Put the additional verse number into the text in parenthesis
                elif vCount > 1: # We have an additional verse number
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert text != str(V)
                    composedLine += ' <sup>('+text+')</sup>' # Put the additional verse number into the text in parenthesis
                lastMarker = marker
                continue

            #print( "toESword.composeVerseLine:", BBB, C, V, marker, text )
            if marker in theWordIgnoredIntroMarkers:
                logging.error( "toESword.composeVerseLine: Found unexpected {} introduction marker at {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                print( "toESword.composeVerseLine:", BBB, C, V, marker, text, verseData )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    assert marker not in theWordIgnoredIntroMarkers # these markers shouldn't occur in verses

            if marker == 'ms1': composedLine += '<TS2>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
            elif marker in ('ms2','ms3','ms4'): composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
            elif marker == 's1':
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~cf0~^~b0~^~i0~^~line '
            elif marker == 's2': composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~cf0~^~b0~^~i0~^~line '
            elif marker in ( 's3','s4', 'sr','mr', 'd', ): composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~b~^~i~^~f0 '
            elif marker in ( 'qa', 'r', ):
                if marker=='r' and text and text[0]!='(' and text[-1]!=')': # Put parenthesis around this if not already there
                    text = '(' + text + ')'
                composedLine += '<TS3><i>'+adjustLine(BBB,C,V,text)+'</i><Ts>'
            elif marker in ( 'm', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                #if text:
                    #print( 'm', repr(text), verseData )
                    #composedLine += '~^~line '+adjustLine(BBB,C,V,text)
                    #if ourGlobals['pi1'] or ourGlobals['pi2'] or ourGlobals['pi3'] or ourGlobals['pi4'] or ourGlobals['pi5'] or ourGlobals['pi6'] or ourGlobals['pi7']:
                        #composedLine += '~^~line '
                    #else: composedLine += '~^~line '
                #else: # there is text
                    #composedLine += '~^~line'+adjustLine(BBB,C,V,text)
            elif marker in ( 'p', 'b', ):
                #print( marker, text )
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                #else: composedLine += '~^~line '
                #composedLine += adjustLine(BBB,C,V,text)
            elif marker in ( 'pi1', ):
                assert not text
            elif marker in ( 'pi2', ):
                assert not text
            elif marker in ( 'pi3', 'pmc', ):
                assert not text
            elif marker in ( 'pi4', ):
                assert not text
            elif marker in ( 'pc', ):
                assert not text
            elif marker in ( 'pr', 'pmr', 'cls', ):
                assert not text
            elif marker in ( 'b','nb','ib', 'mi', 'pm', 'pmo', ):
                assert not text
            elif marker in ( 'q1', 'qm1', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                else: composedLine += '~^~line '
                #composedLine += adjustLine(BBB,C,V,text)
            elif marker in ( 'q2', 'qm2', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                else: composedLine += '~^~line '
                #composedLine += '~^~line<PI2>'+adjustLine(BBB,C,V,text)
            elif marker in ( 'q3', 'qm3', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                else: composedLine += '~^~line '
                #composedLine += '~^~line<PI3>'+adjustLine(BBB,C,V,text)
            elif marker in ( 'q4', 'qm4', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                else: composedLine += '~^~line '
                #composedLine += '~^~line<PI4>'+adjustLine(BBB,C,V,text)
            elif marker == 'li1': composedLine += '<PI>• '+adjustLine(BBB,C,V,text)
            elif marker == 'li2': composedLine += '<PI2>• '+adjustLine(BBB,C,V,text)
            elif marker == 'li3': composedLine += '<PI3>• '+adjustLine(BBB,C,V,text)
            elif marker == 'li4': composedLine += '<PI4>• '+adjustLine(BBB,C,V,text)
            elif marker in ( 'cd', 'sp', ): composedLine += '<i>'+adjustLine(BBB,C,V,text)+'</i>'
            elif marker in ( 'v~', 'p~', ):
                #print( lastMarker )
                if lastMarker == 'p': composedLine += '~^~line ' # We had a continuation paragraph
                elif lastMarker == 'm': composedLine += '~^~line ' # We had a continuation paragraph
                elif lastMarker in BibleOrgSysGlobals.USFMParagraphMarkers: pass # Did we need to do anything here???
                elif lastMarker != 'v':
                    print( BBB, C, V, marker, lastMarker, verseData )
                    composedLine += adjustLine(BBB,C,V, text )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt # This should never happen -- probably a b marker with text
                #if ourGlobals['pi1']: composedLine += '<PI>'
                #elif ourGlobals['pi2']: composedLine += '<PI2>'
                #elif ourGlobals['pi3']: composedLine += '<PI3>'
                #elif ourGlobals['pi4']: composedLine += '<PI4>'
                #elif ourGlobals['pi5']: composedLine += '<PI5>'
                #elif ourGlobals['pi6']: composedLine += '<PI6>'
                #elif ourGlobals['pi7']: composedLine += '<PI7>'
                composedLine += adjustLine(BBB,C,V, text )
            else:
                logging.warning( "toESword.composeVerseLine: doesn't handle {!r} yet".format( marker ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "toESword.composeVerseLine: doesn't handle {!r} yet".format( marker ) )
                    halt
                ourGlobals['unhandledMarkers'].add( marker )
            lastMarker = marker

        # Final clean-up
        #while '  ' in composedLine: # remove double spaces
            #composedLine = composedLine.replace( '  ', ' ' )

        # Check what's left at the end (but hide e-Sword \line markers first)
        if '\\' in composedLine.replace( '\\line ', '' ):
            logging.warning( "toESword.composeVerseLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, composedLine ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "toESword.composeVerseLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, composedLine ) )
                halt
        return composedLine.replace( '~^~', '\\' ).rstrip()
    # end of toESword.composeVerseLine


    def writeESwordCommentaryBook( sqlObject, BBB, ourGlobals ):
        """
        Writes a book to the e-Sword sqlObject file.
        """
        print( "toESword.writeESwordCommentaryBook( {}, {}, {}".format( sqlObject, BBB, ourGlobals ) )
        halt # Not written yet

        nonlocal lineCount
        bkData = self.books[BBB] if BBB in self.books else None
        #print( bkData._processedLines )
        verseList = BOS.getNumVersesList( BBB )
        nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
        numC, numV = len(verseList), verseList[0]

        ourGlobals['line'], ourGlobals['lastLine'] = '', None
        if bkData:
            # Write book headings (stuff before chapter 1)
            ourGlobals['line'] = handleIntroduction( BBB, bkData, ourGlobals )

            # Write the verses
            C = V = 1
            ourGlobals['lastLine'] = ourGlobals['lastBCV'] = None
            while True:
                verseData = None
                if bkData:
                    try:
                        result = bkData.getContextVerseData( (BBB,str(C),str(V),) )
                        verseData, context = result
                    except KeyError: # Just ignore missing verses
                        logging.warning( "BibleWriter.toESword: missing source verse at {} {}:{}".format( BBB, C, V ) )
                    # Handle some common versification anomalies
                    if (BBB,C,V) == ('JN3',1,14): # Add text for v15 if it exists
                        try:
                            result15 = bkData.getContextVerseData( ('JN3','1','15',) )
                            verseData15, context15 = result15
                            verseData.extend( verseData15 )
                        except KeyError: pass #  just ignore it
                    elif (BBB,C,V) == ('REV',12,17): # Add text for v15 if it exists
                        try:
                            result18 = bkData.getContextVerseData( ('REV','12','18',) )
                            verseData18, context18 = result18
                            verseData.extend( verseData18 )
                        except KeyError: pass #  just ignore it
                    composedLine = ''
                    if verseData:
                        composedLine = composeVerseLine( BBB, C, V, verseData, ourGlobals )
                        #if composedLine: # don't bother writing blank (unfinished?) verses
                            #print( "toESword: Writing", BBB, nBBB, C, V, marker, repr(line) )
                            #sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', (nBBB,C,V,composedLine) )
                        # Stay one line behind (because paragraph indicators get appended to the previous line)
                        if ourGlobals['lastBCV'] is not None \
                        and ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
                            sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', \
                                (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
                            lineCount += 1
                    ourGlobals['lastLine'] = composedLine
                ourGlobals['lastBCV'] = (nBBB,C,V)
                V += 1
                if V > numV:
                    C += 1
                    if C > numC:
                        break
                    else: # next chapter only
                        numV = verseList[C-1]
                        V = 1
            #assert not ourGlobals['line'] and not ourGlobals['lastLine'] #  We should have written everything

        # Write the last line of the file
        if ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
            sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', \
                (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
            lineCount += 1
    # end of toESword.writeESwordCommentaryBook


    # Set-up their Bible reference system
    BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )
    #BRL = BibleReferenceList( BOS, BibleObject=None )
    halt # Not written yet

    # Try to figure out if it's an OT/NT or what (allow for up to 4 extra books like FRT,GLS, etc.)
    if len(self) <= (39+4) and self.containsAnyOT39Books() and not self.containsAnyNT27Books():
        testament, startBBB, endBBB = 'OT', 'GEN', 'MAL'
        booksExpected, textLineCountExpected, checkTotals = 39, 23145, theWordOTBookLines
    elif len(self) <= (27+4) and self.containsAnyNT27Books() and not self.containsAnyOT39Books():
        testament, startBBB, endBBB = 'NT', 'MAT', 'REV'
        booksExpected, textLineCountExpected, checkTotals = 27, 7957, theWordNTBookLines
    else: # assume it's an entire Bible
        testament, startBBB, endBBB = 'BOTH', 'GEN', 'REV'
        booksExpected, textLineCountExpected, checkTotals = 66, 31102, theWordBookLines
    extension = '.bblx'

    if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to e-Sword format…") )
    mySettings = {}
    mySettings['unhandledMarkers'] = set()
    handledBooks = []

    if 'e-SwordOutputFilename' in controlDict: filename = controlDict['e-SwordOutputFilename']
    elif self.sourceFilename: filename = self.sourceFilename
    elif self.shortName: filename = self.shortName
    elif self.abbreviation: filename = self.abbreviation
    elif self.name: filename = self.name
    else: filename = 'export'
    if not filename.endswith( extension ): filename += extension # Make sure that we have the right file extension
    filepath = os.path.join( outputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
    if os.path.exists( filepath ): os.remove( filepath )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( '  writeESwordCommentaryBook: ' + _("Writing {!r}…").format( filepath ) )
    conn = sqlite3.connect( filepath )
    cursor = conn.cursor()

    # First write the settings Details table
    exeStr = 'CREATE TABLE Details (Description NVARCHAR(255), Abbreviation NVARCHAR(50), Comments TEXT, Version TEXT, VersionDate DATETIME, PublishDate DATETIME, RightToLeft BOOL, OT BOOL, NT BOOL, Strong BOOL' # incomplete
    customCSS = self.getSetting( 'CustomCSS' )
    if customCSS: exeStr += ', CustomCSS TEXT'
    exeStr += ')'
    cursor.execute( exeStr )

    values = []

    description = self.getSetting( 'Description' )
    if not description: description = self.getSetting( 'description' )
    if not description: description = self.name
    values.append( description )

    if self.abbreviation: abbreviation = self.abbreviation
    else: abbreviation = self.getSetting( 'WorkAbbreviation' )
    if not abbreviation: abbreviation = self.name[:3].upper()
    values.append( abbreviation )

    comments = self.getSetting( 'Comments' )
    values.append( comments )

    version = self.getSetting( 'Version' )
    values.append( version )

    versionDate = self.getSetting( 'VersionDate' )
    values.append( versionDate )

    publishDate = self.getSetting( 'PublishDate' )
    values.append( publishDate )

    rightToLeft = self.getSetting( 'RightToLeft' )
    values.append( rightToLeft )

    values.append( True if testament=='OT' or testament=='BOTH' else False )
    values.append( True if testament=='NT' or testament=='BOTH' else False )

    Strong = self.getSetting( 'Strong' )
    values.append( Strong if Strong else False )

    if customCSS: values.append( customCSS )

    exeStr = 'INSERT INTO "Details" VALUES(' + '?,'*(len(values)-1) + '?)'
    #print( exeStr, values )
    cursor.execute( exeStr, values )

    # Now create and fill the Bible table
    cursor.execute( 'CREATE TABLE Bible(Book INT, Chapter INT, Verse INT, Scripture TEXT)' )
    conn.commit() # save (commit) the changes
    BBB, lineCount = startBBB, 0
    while True: # Write each Bible commentary book in the KJV order
        writeESwordCommentaryBook( cursor, BBB, mySettings )
        conn.commit() # save (commit) the changes
        handledBooks.append( BBB )
        if BBB == endBBB: break
        BBB = BOS.getNextBookCode( BBB )

    # Now create the index
    cursor.execute( 'CREATE INDEX BookChapterVerseIndex ON Bible (Book, Chapter, Verse)' )
    conn.commit() # save (commit) the changes
    cursor.close()

    if mySettings['unhandledMarkers']:
        logging.warning( "BibleWriter.toESword: Unhandled markers were {}".format( mySettings['unhandledMarkers'] ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled toESword markers were {}").format( mySettings['unhandledMarkers'] ) )
    unhandledBooks = []
    for BBB in self.getBookList():
        if BBB not in handledBooks: unhandledBooks.append( BBB )
    if unhandledBooks:
        logging.warning( "toESword: Unhandled books were {}".format( unhandledBooks ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled toESword books were {}").format( unhandledBooks ) )

    # Now create a zipped version
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} e-Sword file…".format( filename ) )
    zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
    zf.write( filepath, filename )
    zf.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        print( "  BibleWriter.toESword finished successfully." )
    return True
# end of createESwordCommentaryModule



def testeSwC( indexString, eSwCfolder, eSwCfilename ):
    """
    Crudely demonstrate the e-Sword Bible commentary class
    """
    from BibleOrgSys.Reference import VerseReferences
    #BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/e-Sword modules/' ) # Must be the same as below

    #TUBfolder = os.path.join( eSwCfolder, eSwCfilename )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the e-Sword Bible class {}…").format( indexString) )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( eSwCfolder, eSwCfilename ) )
    eSwC = ESwordCommentary( eSwCfolder, eSwCfilename )
    eSwC.preload()
    #eSwC.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "testeSwC1:", eSwC ) # Just print a summary
    #print( eSwC.suppliedMetadata['e-Sword-Commentary'] )
    if eSwC is not None:
        if BibleOrgSysGlobals.strictCheckingFlag: eSwC.check()
        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                            ('OT','DAN','1','21'),
                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
            (t, b, c, v) = reference
            if t=='OT' and len(eSwC)==27: continue # Don't bother with OT references if it's only a NT
            if t=='NT' and len(eSwC)==39: continue # Don't bother with NT references if it's only a OT
            if t=='DC' and len(eSwC)<=66: continue # Don't bother with DC references if it's too small
            svk = VerseReferences.SimpleVerseKey( b, c, v )
            #print( svk, ob.getVerseDataList( reference ) )
            try:
                shortText, verseText = svk.getShortText(), eSwC.getVerseText( svk )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
            except KeyError:
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, "not found!!!" )

        eSwC.discover() # Just to test this

        if 0:# Now export the Bible and compare the round trip
            eSwC.toESword()
            #doaResults = eSwC.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                outputFolder = "OutputFiles/BOS_e-Sword_Reexport/"
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported e-Sword files…" )
                result = BibleOrgSysGlobals.fileCompare( eSwCfilename, eSwCfilename, eSwCfolder, outputFolder )
                if BibleOrgSysGlobals.debugFlag:
                    if not result: halt
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "testeSwC2:", eSwC ) # Just print a summary
# end of testeSwC


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordTest/' )
        result1 = ESwordCommentaryFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = ESwordCommentaryFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA2", result2 )
        result3 = ESwordCommentaryFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA3", result3 )


    if 1: # individual module
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordTest/' )
        filename = 'comentario_exegetico_al_texto_griego_nt_samuel_perez_millos.cmti'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSwC B/ Trying {}".format( filename ) )
        testeSwC( 'B', testFolder, filename )


    if 1: # individual modules in the same test folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordTest/' )
        names = ('King James Bible Pure Cambridge Edition','KJ3.JayPGreen','Wycliffe_New_Testament(1385)',)
        for j, name in enumerate( names):
            indexString = 'C' + str( j+1 )
            fullname = name + '.cmtx'
            if os.path.exists( os.path.join( testFolder, fullname ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, fullname ) )
                testeSwC( indexString, testFolder, fullname )
            else:
                logging.error( "{} File '{}' doesn't exist in folder '{}'".format( indexString, fullname, testFolder ) )


    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    if 1: # individual modules in the same test folder
        testFolder = BiblesFolderpath.joinpath( 'e-Sword modules/Commentaries/' )
        names = ('darby(2)','clarke(2)','Darby-John-Synopsis-of-the-New-Testament',)
        for j, name in enumerate( names):
            indexString = 'D' + str( j+1 )
            fullname = name + '.cmtx'
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, fullname ) )
            testeSwC( indexString, testFolder, fullname )


    #if 0: # individual modules in the output folder
        #testFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_e-SwordExport/' )
        #names = ("Matigsalug",)
        #for j, name in enumerate( names):
            #indexString = 'E' + str( j+1 )
            #fullname = name + '.cmtx'
            #pathname = os.path.join( testFolder, fullname )
            #if os.path.exists( pathname ):
                #if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, fullname ) )
                #testeSwC( indexString, testFolder, fullname )


    #if 0: # all discovered modules in the test folder
        #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordRoundtripTestFiles/' )
        #foundFolders, foundFiles = [], []
        #for something in os.listdir( testFolder ):
            #somepath = os.path.join( testFolder, something )
            #if os.path.isdir( somepath ): foundFolders.append( something )
            #elif os.path.isfile( somepath ) and somepath.endswith('.bblx'):
                #if something != 'acc.bblx': # has a corrupted file it seems
                    #foundFiles.append( something )

        #if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            #parameters = [('E'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            #BibleOrgSysGlobals.alreadyMultiprocessing = True
            #with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                #results = pool.map( testeSwC, parameters ) # have the pool do our loads
                #assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            #BibleOrgSysGlobals.alreadyMultiprocessing = False
        #else: # Just single threaded
            #for j, someFile in enumerate( sorted( foundFiles ) ):
                #indexString = 'E' + str( j+1 )
                #if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, someFile ) )
                ##myTestFolder = os.path.join( testFolder, someFolder+'/' )
                #testeSwC( indexString, testFolder, someFile )
                ##break # only do the first one…temp

    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    if 1: # all discovered modules in the test folder
        testFolder = BiblesFolderpath.joinpath( 'e-Sword modules/Commentaries/' ) # Put your test folder here

        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.cmtx'): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [('G'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( testeSwC, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ) ):
                indexString = 'G' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testeSwC( indexString, testFolder, someFile )
                #break # only do the first one…temp
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ESwordCommentary.py
