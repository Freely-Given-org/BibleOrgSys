#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# MySwordBible.py
#
# Module handling "MySword" Bible module files
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
Module reading and loading MySword Bible files.
These can be downloaded from: http://www.theword.net/index.php?downloads.modules

A MySword Bible module file has one verse per SQLite3 table row (KJV versification)
    OT (.ot file) has 23145 lines
    NT (.nt file) has 7957 lines
    Bible (.ont file) has 31102 lines.

Some basic HTML-style tags are recognised: <u></u>, <i></i>, <b></b>, <s></s>, <br>, <p>, <sup></sup>, <sub></sub>

Also, custom tags:
    <FI><Fi> for added words
    <CL> = new line (usually at the end of lines)
    <CM> = new paragraph (usually at the end of lines)

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

LAST_MODIFIED_DATE = '2019-09-07' # by RJH
SHORT_PROGRAM_NAME = "MySwordBible"
PROGRAM_NAME = "MySword Bible format handler"
PROGRAM_VERSION = '0.36'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os
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
from BibleOrgSys.Formats.theWordBible import handleRTFLine



FILENAME_ENDINGS_TO_ACCEPT = ('.MYBIBLE',) # Must be UPPERCASE
BIBLE_FILENAME_ENDINGS_TO_ACCEPT = ('.BBL.MYBIBLE',) # Must be UPPERCASE



def MySwordBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for MySword Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one MySword Bible is found,
        returns the loaded MySwordBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "MySwordBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag:
        assert givenFolderName and isinstance( givenFolderName, str )
        assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("MySwordBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("MySwordBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " MySwordBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
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

    # See if there's an MySwordBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "MySwordBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            MySwB = MySwordBible( givenFolderName, lastFilenameFound )
            if autoLoad or autoLoadBooks: MySwB.preload()
            if autoLoadBooks: MySwB.load() # Load and process the database
            return MySwB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("MySwordBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    MySwordBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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

        # See if there's an MySword project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "MySwordBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            MySwB = MySwordBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoad or autoLoadBooks: MySwB.preload()
            if autoLoadBooks: MySwB.load() # Load and process the database
            return MySwB
        return numFound
# end of MySwordBibleFileCheck



class MySwordBible( Bible ):
    """
    Class for reading, validating, and converting MySwordBible files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'MySword Bible object'
        self.objectTypeString = 'MySword'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("MySwordBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        filenameBits = os.path.splitext( self.sourceFilename )
        self.name = filenameBits[0]
        self.fileExtension = filenameBits[1]

        #if self.fileExtension.upper().endswith('X'):
            #logging.warning( _("MySwordBible: File {!r} is encrypted").format( self.sourceFilepath ) )
    # end of MySwordBible.__init__


    def preload( self ):
        """
        Load the metadata from the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("preload()") )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Preloading {}…").format( self.sourceFilepath ) )

        fileExtensionUpper = self.fileExtension.upper()
        if fileExtensionUpper not in FILENAME_ENDINGS_TO_ACCEPT:
            logging.critical( "{} doesn't appear to be a MySword file".format( self.sourceFilename ) )
        elif not self.sourceFilename.upper().endswith( BIBLE_FILENAME_ENDINGS_TO_ACCEPT[0] ):
            logging.critical( "{} doesn't appear to be a MySword Bible file".format( self.sourceFilename ) )

        connection = sqlite3.connect( self.sourceFilepath )
        connection.row_factory = sqlite3.Row # Enable row names
        self.cursor = connection.cursor()

        # First get the settings
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['MySword'] = {}
        self.cursor.execute( 'select * from Details' )
        row = self.cursor.fetchone()
        for key in row.keys():
            self.suppliedMetadata['MySword'][key] = row[key]
        #print( self.suppliedMetadata['MySword'] ); halt
        #if 'Description' in self.settingsDict and len(self.settingsDict['Description'])<40: self.name = self.settingsDict['Description']
        #if 'Abbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['Abbreviation']
        if 'encryption' in self.suppliedMetadata['MySword']:
            logging.critical( "{} is encrypted: level {}".format( self.sourceFilename, self.suppliedMetadata['MySword']['encryption'] ) )

        self.BibleOrganisationalSystem = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        self.preloadDone = True
    # end of MySwordBible.preload


    def load( self ):
        """
        Load all the books out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("load()") )
        assert self.preloadDone

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )


        if self.suppliedMetadata['MySword']['OT'] and self.suppliedMetadata['MySword']['NT']:
            testament, BBB = 'BOTH', 'GEN'
            booksExpected, textLineCountExpected = 66, 31102
        elif self.suppliedMetadata['MySword']['OT']:
            testament, BBB = 'OT', 'GEN'
            booksExpected, textLineCountExpected = 39, 23145
        elif self.suppliedMetadata['MySword']['NT']:
            testament, BBB = 'NT', 'MAT'
            booksExpected, textLineCountExpected = 27, 7957

        # Create the first book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'MySword Bible Book object'
        thisBook.objectTypeString = 'MySword'

        verseList = self.BibleOrganisationalSystem.getNumVersesList( BBB )
        numC, numV = len(verseList), verseList[0]
        nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
        C = V = 1

        bookCount = 0
        ourGlobals = {}
        continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        while True:
            self.cursor.execute('select Scripture from Bible where Book=? and Chapter=? and Verse=?', (nBBB,C,V) )
            try:
                row = self.cursor.fetchone()
                line = row[0]
            except TypeError: # This reference is missing (row is None)
                #print( "something wrong at", BBB, C, V )
                #if BibleOrgSysGlobals.debugFlag: halt
                #print( row )
                line = None
            #print ( nBBB, BBB, C, V, 'MySw file line is "' + line + '"' )
            if line is None: logging.warning( "MySwordBible.load: Have missing verse line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not isinstance( line, str ):
                    if 'encryption' in self.suppliedMetadata['MySword']:
                        logging.critical( "MySwordBible.load: Unable to decrypt verse line at {} {}:{} {!r}".format( BBB, C, V, line ) )
                        break
                    else:
                        logging.critical( "MySwordBible.load: Unable to decode verse line at {} {}:{} {!r} {}".format( BBB, C, V, line, self.suppliedMetadata['MySword'] ) )
                elif not line: logging.warning( "MySwordBible.load: Found blank verse line at {} {}:{}".format( BBB, C, V ) )
                else:
                    haveLines = True

                    # Some modules end lines with \r\n or have it in the middle!
                    #   (We just ignore these for now)
                    while line and line[-1] in '\r\n': line = line[:-1]
                    if '\r' in line or '\n' in line: # (in the middle)
                        logging.warning( "MySwordBible.load: Found CR or LF characters in verse line at {} {}:{}".format( BBB, C, V ) )
                    line = line.replace( '\r\n', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' )

            #print( "MySword.load", BBB, C, V, repr(line) )
            handleRTFLine( self.name, BBB, C, V, line, thisBook, ourGlobals )
            V += 1
            if V > numV:
                C += 1
                if C > numC: # Save this book now
                    if haveLines:
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "  MySword saving", BBB, bookCount+1 )
                        self.stashBook( thisBook )
                    #else: print( "Not saving", BBB )
                    bookCount += 1 # Not the number saved but the number we attempted to process
                    if bookCount >= booksExpected: break
                    BBB = self.BibleOrganisationalSystem.getNextBookCode( BBB )
                    # Create the next book
                    thisBook = BibleBook( self, BBB )
                    thisBook.objectNameString = 'MySword Bible Book object'
                    thisBook.objectTypeString = 'MySword'
                    haveLines = False

                    verseList = self.BibleOrganisationalSystem.getNumVersesList( BBB )
                    numC, numV = len(verseList), verseList[0]
                    nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
                    C = V = 1
                    #thisBook.addLine( 'c', str(C) )
                else: # next chapter only
                    #thisBook.addLine( 'c', str(C) )
                    numV = verseList[C-1]
                    V = 1

            if ourGlobals['haveParagraph']:
                thisBook.addLine( 'p', '' )
                ourGlobals['haveParagraph'] = False

        self.cursor.close()
        del self.cursor
        self.applySuppliedMetadata( 'MySword' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of MySwordBible.load


    def loadBook( self, BBB ):
        """
        Load the requested book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("loadBook( {} )").format( BBB ) )
        assert self.preloadDone

        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading MySwordBible {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("MySwordBible: Loading {} from {}…").format( BBB, self.sourceFilepath ) )

        #if self.suppliedMetadata['MySword']['OT'] and self.suppliedMetadata['MySword']['NT']:
            #testament, BBB = 'BOTH', 'GEN'
            #booksExpected, textLineCountExpected = 1, 31102
        #elif self.suppliedMetadata['MySword']['OT']:
            #testament, BBB = 'OT', 'GEN'
            #booksExpected, textLineCountExpected = 1, 23145
        #elif self.suppliedMetadata['MySword']['NT']:
            #testament, BBB = 'NT', 'MAT'
            #booksExpected, textLineCountExpected = 1, 7957


        # Create the first book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'MySword Bible Book object'
        thisBook.objectTypeString = 'MySword'

        verseList = self.BibleOrganisationalSystem.getNumVersesList( BBB )
        numC, numV = len(verseList), verseList[0]
        nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
        C = V = 1

        #bookCount = 0
        ourGlobals = {}
        continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        while True:
            self.cursor.execute('select Scripture from Bible where Book=? and Chapter=? and Verse=?', (nBBB,C,V) )
            try:
                row = self.cursor.fetchone()
                line = row[0]
            except TypeError: # This reference is missing (row is None)
                #print( "something wrong at", BBB, C, V )
                #if BibleOrgSysGlobals.debugFlag: halt
                #print( row )
                line = None
            #print ( nBBB, BBB, C, V, 'MySw file line is "' + line + '"' )
            if line is None: logging.warning( "MySwordBible.load: Have missing verse line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not isinstance( line, str ):
                    if 'encryption' in self.suppliedMetadata['MySword']:
                        logging.critical( "MySwordBible.load: Unable to decrypt verse line at {} {}:{} {!r}".format( BBB, C, V, line ) )
                        break
                    else:
                        logging.critical( "MySwordBible.load: Unable to decode verse line at {} {}:{} {!r} {}".format( BBB, C, V, line, self.suppliedMetadata['MySword'] ) )
                elif not line: logging.warning( "MySwordBible.load: Found blank verse line at {} {}:{}".format( BBB, C, V ) )
                else:
                    haveLines = True

                    # Some modules end lines with \r\n or have it in the middle!
                    #   (We just ignore these for now)
                    while line and line[-1] in '\r\n': line = line[:-1]
                    if '\r' in line or '\n' in line: # (in the middle)
                        logging.warning( "MySwordBible.load: Found CR or LF characters in verse line at {} {}:{}".format( BBB, C, V ) )
                    line = line.replace( '\r\n', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' )

            #print( "MySword.load", BBB, C, V, repr(line) )
            handleRTFLine( self.name, BBB, C, V, line, thisBook, ourGlobals )
            V += 1
            if V > numV:
                C += 1
                if C <= numC: # next chapter only
                    #thisBook.addLine( 'c', str(C) )
                    numV = verseList[C-1]
                    V = 1
                else: # Save this book now
                    if haveLines:
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  MySword saving", BBB )
                        self.stashBook( thisBook )
                    #else: print( "Not saving", BBB )
                    break

            if ourGlobals['haveParagraph']:
                thisBook.addLine( 'p', '' )
                ourGlobals['haveParagraph'] = False
    # end of MySwordBible.loadBook
# end of MySwordBible class



def createMySwordModule( self, outputFolder, controlDict ):
    """
    Create a SQLite3 database module for the program MySword.

    self here is a Bible object with _processedLines
    """
    import tarfile
    from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS, BOS_NESTING_MARKERS
    from BibleOrgSys.Formats.theWordBible import theWordOTBookLines, theWordNTBookLines, theWordBookLines, theWordHandleIntroduction, theWordComposeVerseLine

    def writeMSBook( sqlObject, BBB, ourGlobals ):
        """
        Writes a book to the MySword sqlObject file.
        """
        nonlocal lineCount
        bkData = self.books[BBB] if BBB in self.books else None
        #print( bkData._processedLines )
        verseList = BOS.getNumVersesList( BBB )
        nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
        numC, numV = len(verseList), verseList[0]

        ourGlobals['line'], ourGlobals['lastLine'] = '', None
        ourGlobals['pi1'] = ourGlobals['pi2'] = ourGlobals['pi3'] = ourGlobals['pi4'] = ourGlobals['pi5'] = ourGlobals['pi6'] = ourGlobals['pi7'] = False
        if bkData:
            # Write book headings (stuff before chapter 1)
            ourGlobals['line'] = theWordHandleIntroduction( BBB, bkData, ourGlobals )

            # Write the verses
            C = V = 1
            ourGlobals['lastLine'] = ourGlobals['lastBCV'] = None
            while True:
                verseData = None
                if bkData:
                    try:
                        result = bkData.getContextVerseData( (BBB,str(C),str(V),) )
                        verseData, context = result
                    except KeyError: # Missing verses
                        logging.warning( "BibleWriter.createMySwordModule: missing source verse at {} {}:{}".format( BBB, C, V ) )
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
                    if verseData: composedLine = theWordComposeVerseLine( BBB, C, V, verseData, ourGlobals )
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
    # end of createMySwordModule.writeMSBook


    # Set-up their Bible reference system
    BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )
    #BRL = BibleReferenceList( BOS, BibleObject=None )

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
    extension = '.bbl.mybible'

    if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to MySword format…") )
    mySettings = {}
    mySettings['unhandledMarkers'] = set()
    handledBooks = []

    if 'MySwordOutputFilename' in controlDict: filename = controlDict['MySwordOutputFilename']
    elif self.sourceFilename: filename = self.sourceFilename
    elif self.shortName: filename = self.shortName
    elif self.abbreviation: filename = self.abbreviation
    elif self.name: filename = self.name
    else: filename = 'export'
    if not filename.endswith( extension ): filename += extension # Make sure that we have the right file extension
    filepath = os.path.join( outputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
    if os.path.exists( filepath ): os.remove( filepath )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( '  createMySwordModule: ' + _("Writing {!r}…").format( filepath ) )
    conn = sqlite3.connect( filepath )
    cursor = conn.cursor()

    # First write the settings Details table
    exeStr = 'CREATE TABLE Details(Description NVARCHAR(255), Abbreviation NVARCHAR(50), Comments TEXT, Version TEXT, VersionDate DATETIME, PublishDate DATETIME, RightToLeft BOOL, OT BOOL, NT BOOL, Strong BOOL' # incomplete
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
    #if BibleOrgSysGlobals.debugFlag: cursor.execute( exeStr, values )
    #else: # Not debugging
        #try: cursor.execute( exeStr, values )
        #except sqlite3.InterfaceError:
            #logging.critical( "SQLite3 Interface error executing {} with {}".format( exeStr, values ) )

    # Now create and fill the Bible table
    cursor.execute( 'CREATE TABLE Bible(Book INT, Chapter INT, Verse INT, Scripture TEXT, Primary Key(Book,Chapter,Verse))' )
    conn.commit() # save (commit) the changes
    BBB, lineCount = startBBB, 0
    while True: # Write each Bible book in the KJV order
        writeMSBook( cursor, BBB, mySettings )
        conn.commit() # save (commit) the changes
        handledBooks.append( BBB )
        if BBB == endBBB: break
        BBB = BOS.getNextBookCode( BBB )
    conn.commit() # save (commit) the changes
    cursor.close()

    if mySettings['unhandledMarkers']:
        logging.warning( "BibleWriter.createMySwordModule: Unhandled markers were {}".format( mySettings['unhandledMarkers'] ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled createMySwordModule markers were {}").format( mySettings['unhandledMarkers'] ) )
    unhandledBooks = []
    for BBB in self.getBookList():
        if BBB not in handledBooks: unhandledBooks.append( BBB )
    if unhandledBooks:
        logging.warning( "createMySwordModule: Unhandled books were {}".format( unhandledBooks ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled createMySwordModule books were {}").format( unhandledBooks ) )

    # Now create the gzipped file
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Compressing {} MySword file…".format( filename ) )
    tar = tarfile.open( filepath+'.gz', 'w:gz' )
    tar.add( filepath )
    tar.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        print( "  BibleWriter.createMySwordModule finished successfully." )
    return True
# end of createMySwordModule



def testMySwB( indexString, MySwBfolder, MySwBfilename ):
    """
    Crudely demonstrate the MySword Bible class.
    """
    #print( "tMSB", MySwBfolder )
    from BibleOrgSys.Reference import VerseReferences
    #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/MySword modules/' ) # Must be the same as below

    #TUBfolder = os.path.join( MySwBfolder, MySwBfilename )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the MySword Bible class {}…").format( indexString) )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( MySwBfolder, MySwBfilename ) )
    MySwB = MySwordBible( MySwBfolder, MySwBfilename )
    MySwB.preload()
    #MySwB.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( MySwB ) # Just print a summary
    #print( MySwB.suppliedMetadata['MySword'] )
    if MySwB is not None:
        if BibleOrgSysGlobals.strictCheckingFlag: MySwB.check()
        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                            ('OT','DAN','1','21'),
                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
            (t, b, c, v) = reference
            if t=='OT' and len(MySwB)==27: continue # Don't bother with OT references if it's only a NT
            if t=='NT' and len(MySwB)==39: continue # Don't bother with NT references if it's only a OT
            if t=='DC' and len(MySwB)<=66: continue # Don't bother with DC references if it's too small
            svk = VerseReferences.SimpleVerseKey( b, c, v )
            #print( svk, ob.getVerseDataList( reference ) )
            try:
                shortText, verseText = svk.getShortText(), MySwB.getVerseText( svk )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
            except KeyError:
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, "not found!!!" )

        if 0: # Now export the Bible and compare the round trip
            MySwB.createMySwordModule()
            #doaResults = MySwB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                outputFolder = "OutputFiles/BOS_MySword_Reexport/"
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported MySword files…" )
                result = BibleOrgSysGlobals.fileCompare( MySwBfilename, MySwBfilename, MySwBfolder, outputFolder )
                if BibleOrgSysGlobals.debugFlag:
                    if not result: halt
# end of testMySwB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MySwordTest/' )
        result1 = MySwordBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = MySwordBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA2", result2 )
        result3 = MySwordBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA3", result3 )


    if 1: # individual modules in the test folder
        testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/MySword modules/' )
        names = ('nheb-je','nko','ts1998',)
        for j, name in enumerate( names):
            fullname = name + '.bbl.mybible'
            pathname = os.path.join( testFolder, fullname )
            if os.path.exists( pathname ):
                indexString = 'B' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMySw {}/ Trying {}".format( indexString, fullname ) )
                testMySwB( indexString, testFolder, fullname )


    if 1: # individual modules in the output folder
        testFolder = "OutputFiles/BOS_MySwordExport"
        names = ("Matigsalug",)
        for j, name in enumerate( names):
            fullname = name + '.bbl.mybible'
            pathname = os.path.join( testFolder, fullname )
            if os.path.exists( pathname ):
                indexString = 'C' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMySw {}/ Trying {}".format( indexString, fullname ) )
                testMySwB( indexString, testFolder, fullname )


    if 1: # all discovered modules in the test folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.mybible'):
                if something != 'acc.bbl.mybible': # has a corrupted file it seems
                    foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [('D'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( testMySwB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ) ):
                indexString = 'D' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMySw {}/ Trying {}".format( indexString, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testMySwB( indexString, testFolder, someFile )
                #break # only do the first one…temp

    if 1: # all discovered modules in the test folder
        testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/MySword modules/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.mybible'): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [('E'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( testMySwB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ) ):
                indexString = 'E' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMySw {}/ Trying {}".format( indexString, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testMySwB( indexString, testFolder, someFile )
                #break # only do the first one…temp
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of MySwordBible.py
