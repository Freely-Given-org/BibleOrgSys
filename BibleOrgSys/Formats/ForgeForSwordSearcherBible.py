#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ForgeForSwordSearcherBible.py
#
# Module handling verse-per-line text Bible files
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
Module reading and loading verse-per-line text Bible files.

Forge for SwordSearcher -- see http://www.swordsearcher.com/forge/index.html
    ; TITLE: Some new version
    ; ABBREVIATION: SNV
    ; HAS ITALICS
    ; HAS FOOTNOTES
    ; HAS REDLETTER
    $$ {AUTHORDETAIL}
    <p>Translated by me, myself and I.</p>
    <p>Copyright © 2006-2015.</p>
    <p>That's all!</p>

    $$ Ge 1:1
    ¶ In the beginning God{Heb: Elohim} made the heavens and the earth.
    $$ Ge 1:2
    And everything was great.
    $$ Ge 1:3
    And God rested.

Formatting includes:
    [added words]
    {footnotes}
    <scriptref>Cross references</scripref>
    +r/This text is red-letter-r/
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "ForgeForSwordSearcherBible"
PROGRAM_NAME = "Forge for SwordSearcher Bible format handler"
PROGRAM_VERSION = '0.37'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, re
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem


BOS66 = BOS81 = BOSx = None

filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX',
                      'STY', 'LDS', 'SSF', 'VRS', 'ASC', 'CSS', 'ODT','DOC', 'JAR', 'SAV', 'SAVE', ) # Must be UPPERCASE


def ForgeForSwordSearcherBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for ForgeForSwordSearcher Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one ForgeForSwordSearcher Bible is found,
        returns the loaded ForgeForSwordSearcherBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "ForgeForSwordSearcherBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ForgeForSwordSearcherBibleFileCheck: Given {} folder is unreadable").format( repr(givenFolderName) ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ForgeForSwordSearcherBibleFileCheck: Given {} path is not a folder").format( repr(givenFolderName) ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " ForgeForSwordSearcherBibleFileCheck: Looking for files in given {}".format( repr(givenFolderName) ) )
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
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )

    # See if there's an ForgeForSwordSearcherBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename in ('book_names.txt','Readme.txt' ): looksHopeful = True
        elif thisFilename.endswith( '.txt' ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName )
                #print( '1', repr(firstLine) )
                if firstLine is None: continue # seems we couldn't decode the file
                if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                    logging.info( "ForgeForSwordSearcherBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( thisFilename ) )
                    firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                match = re.search( '^; TITLE:\\s', firstLine )
                if match:
                    if BibleOrgSysGlobals.debugFlag:
                        print( "ForgeForSwordSearcherBibleFileCheck First line got {!r} match from {!r}".format( match.group(0), firstLine ) )
                else:
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "ForgeForSwordSearcherBibleFileCheck: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                    continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ForgeForSwordSearcherBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = ForgeForSwordSearcherBible( givenFolderName, lastFilenameFound[:-4] ) # Remove the end of the actual filename ".txt"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("ForgeForSwordSearcherBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    ForgeForSwordSearcherBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    foundSubfiles.append( something )

        # See if there's an ForgeForSwordSearcherBible here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if thisFilename.endswith( '.txt' ):
                if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                    firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName )
                    #print( '2', repr(firstLine) )
                    if firstLine is None: continue # seems we couldn't decode the file
                    if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                        logging.info( "ForgeForSwordSearcherBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( thisFilename ) )
                        firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                    match = re.search( '^; TITLE:\\s', firstLine )
                    if match:
                        if BibleOrgSysGlobals.debugFlag:
                            print( "ForgeForSwordSearcherBibleFileCheck First line got type {!r} match from {!r}".format( match.group(0), firstLine ) )
                    else:
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "ForgeForSwordSearcherBibleFileCheck: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        continue
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ForgeForSwordSearcherBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            uB = ForgeForSwordSearcherBible( foundProjects[0][0], foundProjects[0][1][:-4] ) # Remove the end of the actual filename ".txt"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of ForgeForSwordSearcherBibleFileCheck



class ForgeForSwordSearcherBible( Bible ):
    """
    Class for reading, validating, and converting ForgeForSwordSearcherBible files.
    """
    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Forge for SwordSearcher Bible object'
        self.objectTypeString = 'Forge4SS'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'.txt' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("ForgeForSwordSearcherBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of ForgeForSwordSearcherBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )

        global BOS66, BOS81, BOSx
        if BOS66 is None: BOS66 = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )
        if BOS81 is None: BOS81 = BibleOrganisationalSystem( 'GENERIC-KJV-80-ENG' )
        if BOSx is None: BOSx = BibleOrganisationalSystem( 'GENERIC-ENG' )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}

        lastLine, lineCount = '', 0
        bookCode = BBB = metadataName = None
        lastBookCode = lastChapterNumber = lastVerseNumber = -1
        lastVText = ''
        thisBook = None
        settingsDict = {}
        with open( self.sourceFilepath, encoding=self.encoding ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                if lineCount==1:
                    if self.encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF or \ufeff
                        logging.info( "      ForgeForSwordSearcherBible.load: Detected Unicode Byte Order Marker (BOM)" )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    match = re.search( '^; TITLE:\\s', line )
                    if match:
                        if BibleOrgSysGlobals.debugFlag:
                            print( "First line got type {!r} match from {!r}".format( match.group(0), line ) )
                    else:
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "ForgeForSwordSearcherBible.load: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        continue

                #print ( 'ForgeForSwordSearcher file line is "' + line + '"' )
                lastLine = line

                # Process header stuff
                if line.startswith( '; TITLE:' ):
                    string = line[8:].strip()
                    if string: settingsDict['TITLE'] = string
                    continue
                elif line.startswith( '; ABBREVIATION:' ):
                    string = line[15:].strip()
                    if string: settingsDict['ABBREVIATION'] = string
                    continue
                elif line.startswith( '; HAS ITALICS' ):
                    string = line[14:].strip()
                    if string: settingsDict['HAS_ITALICS'] = string
                    continue
                elif line.startswith( '; HAS FOOTNOTES:' ):
                    string = line[15:].strip()
                    if string: settingsDict['HAS_FOOTNOTES'] = string
                    continue
                elif line.startswith( '; HAS FOOTNOTES' ):
                    string = line[14:].strip()
                    if string: settingsDict['HAS_FOOTNOTES'] = string
                    continue
                elif line.startswith( '; HAS REDLETTER' ):
                    string = line[14:].strip()
                    if string: settingsDict['HAS_REDLETTER'] = string
                    continue
                elif line[0]==';':
                    logging.warning( "ForgeForSwordSearcherBible.load is skipping unknown header/comment line: {}".format( line ) )
                    continue # Just discard comment lines

                # Process the main segment
                if line.startswith( '$$ ' ):
                    if metadataName and metadataContents:
                        settingsDict[metadataName] = metadataContents
                        metadataName = None
                    pointer = line[3:]
                    #print( "pointer", repr(pointer) )
                    if pointer and pointer[0]=='{' and pointer[-1]=='}':
                        metadataName = pointer[1:-1]
                        if metadataName:
                            #print( "metadataName", repr(metadataName) )
                            metadataContents = ''
                    else: # let's assume it's a BCV reference
                        pointer = pointer.replace( '1 K','1K' ).replace( '2 K','2K' ) \
                                        .replace( '1 Chr','1Chr' ).replace( '2 Chr','2Chr' ) \
                                        .replace( '1 Cor','1Cor' ).replace( '2 Cor','2Cor' ) \
                                        .replace( '1 Thess','1Thess' ).replace( '2 Thess','2Thess' ) \
                                        .replace( '1 Tim','1Tim' ).replace( '2 Tim','2Tim' ) \
                                        .replace( '1 Pet','1Pet' ).replace( '2 Pet','2Pet' ) \
                                        .replace( '1 J','1J' ).replace( '2 J','2J' ).replace( '3 J','3J' )
                        B_CV_Bits = pointer.split( ' ', 1 )
                        if len(B_CV_Bits) == 2 and ':' in B_CV_Bits[1]:
                            bookCode, CVString = B_CV_Bits
                            chapterNumberString, verseNumberString = CVString.split( ':' )
                            chapterNumber = int( chapterNumberString )
                            verseNumber = int( verseNumberString )
                            if bookCode != lastBookCode: # We've started a new book
                                if bookCode in ('Ge',): BBB = 'GEN'
                                elif bookCode in ('Le',): BBB = 'LEV'
                                elif bookCode in ('La',): BBB = 'LAM'
                                ##elif bookCode in ('Es',): BBB = 'EST'
                                ##elif bookCode in ('Pr',): BBB = 'PRO'
                                #elif bookCode in ('So',): BBB = 'SNG'
                                #elif bookCode in ('La',): BBB = 'LAM'
                                #elif bookCode in ('Jude',): BBB = 'JDE'
                                else:
                                    #print( "4BookCode =", repr(bookCode) )
                                    #BBB = BOS.getBBBFromText( bookCode )  # Try to guess
                                    BBB = BOS66.getBBBFromText( bookCode )  # Try to guess
                                    if not BBB: BBB = BOS81.getBBBFromText( bookCode )  # Try to guess
                                    if not BBB: BBB = BOSx.getBBBFromText( bookCode )  # Try to guess
                                    #print( "4BBB =", repr(BBB) )
                        else: print( "Unexpected number of bits", self.givenName, BBB, bookCode, chapterNumberString, verseNumberString, len(bits), bits )
                    continue # Just save the pointer information which refers to the text on the next line
                else: # it's not a $$ line
                    text = line
                    #print( "text", repr(text) )
                    if metadataName:
                        metadataContents += ('\n' if metadataContents else '') + text
                        continue
                    else:
                        vText = text
                        # Handle bits like (<scripref>Pr 2:7</scripref>)
                        vText = vText.replace( '(<scripref>', '\\x - \\xt ' ).replace( '</scripref>)', '\\x*' )
                        vText = vText.replace( '<scripref>', '\\x - \\xt ' ).replace( '</scripref>', '\\x*' )
                        #if '\\' in vText: print( 'ForgeForSwordSearcher vText', repr(vText) )
                        #print( BBB, chapterNumber, verseNumber, repr(vText) )
                        # Convert {stuff} to footnotes
                        match = re.search( '\\{(.+?)\\}', vText )
                        while match:
                            footnoteText = '\\f + \\fr {}:{} \\ft {}\\f*'.format( chapterNumber, verseNumber, match.group(1) )
                            vText = vText[:match.start()] + footnoteText + vText[match.end():] # Replace this footnote
                            #print( BBB, chapterNumber, verseNumber, repr(vText) )
                            match = re.search( '\\{(.+?)\\}', vText )
                        # Convert [stuff] to added fields
                        match = re.search( '\\[(.+?)\\]', vText )
                        while match:
                            addText = '\\add {}\\add*'.format( match.group(1) )
                            vText = vText[:match.start()] + addText + vText[match.end():] # Replace this chunk
                            #print( BBB, chapterNumber, verseNumber, repr(vText) )
                            match = re.search( '\\[(.+?)\\]', vText )
                        # Convert +r/This text is red-letter-r/ to wj fields
                        match = re.search( '\\+r/(.+?)-r/', vText )
                        while match:
                            addText = '\\wj {}\\wj*'.format( match.group(1) )
                            vText = vText[:match.start()] + addText + vText[match.end():] # Replace this chunk
                            #print( BBB, chapterNumber, verseNumber, repr(vText) )
                            match = re.search( '\\+r/(.+?)-r/', vText )
                        # Final check for unexpected remaining formatting
                        for badChar in '{}[]/':
                            if badChar in vText:
                                logging.warning( "Found remaining braces,brackets or slashes in SwordSearcher Forge VPL {} {}:{} {!r}".format( BBB, chapterNumberString, verseNumberString, vText ) )
                                break


                if bookCode:
                    if bookCode != lastBookCode: # We've started a new book
                        if lastBookCode != -1: # Better save the last book
                            self.stashBook( thisBook )
                        if BBB:
                            if BBB in self:
                                logging.critical( "Have duplicated {} book in {}".format( self.givenName, BBB ) )
                            if BibleOrgSysGlobals.debugFlag: assert BBB not in self
                            thisBook = BibleBook( self, BBB )
                            thisBook.objectNameString = 'ForgeForSwordSearcher Bible Book object'
                            thisBook.objectTypeString = 'ForgeForSwordSearcher'
                            verseList = BOSx.getNumVersesList( BBB )
                            numChapters, numVerses = len(verseList), verseList[0]
                            lastBookCode = bookCode
                            lastChapterNumber = lastVerseNumber = -1
                        else:
                            logging.critical( "ForgeForSwordSearcherBible could not figure out {!r} book code".format( bookCode ) )
                            if BibleOrgSysGlobals.debugFlag: halt

                    if BBB:
                        if chapterNumber != lastChapterNumber: # We've started a new chapter
                            if BibleOrgSysGlobals.debugFlag: assert chapterNumber > lastChapterNumber or BBB=='ESG' # Esther Greek might be an exception
                            if chapterNumber == 0:
                                logging.info( "Have chapter zero in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                            elif chapterNumber > numChapters:
                                logging.error( "Have high chapter number in {} {} {} {}:{} (expected max of {})".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString, numChapters ) )
                            thisBook.addLine( 'c', chapterNumberString )
                            lastChapterNumber = chapterNumber
                            lastVerseNumber = -1

                        # Handle the verse info
                        if verseNumber==lastVerseNumber and vText==lastVText:
                            logging.warning( _("Ignored duplicate verse line in {} {} {} {}:{}").format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                            continue
                        if verseNumber < lastVerseNumber:
                            logging.warning( _("Ignored receding verse number (from {} to {}) in {} {} {} {}:{}").format( lastVerseNumber, verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                        elif verseNumber == lastVerseNumber:
                            if vText == lastVText:
                                logging.warning( _("Ignored duplicated {} verse in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                            else:
                                logging.warning( _("Ignored duplicated {} verse number in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )

                        # Check for paragraph markers
                        if vText and vText[0]=='¶':
                            thisBook.addLine( 'p', '' )
                            vText = vText[1:].lstrip()

                        #print( '{} {}:{} = {!r}'.format( BBB, chapterNumberString, verseNumberString, vText ) )
                        thisBook.addLine( 'v', verseNumberString + ' ' + vText )
                        lastVText = vText
                        lastVerseNumber = verseNumber

                else: # No bookCode yet
                    logging.warning( "ForgeForSwordSearcherBible.load is skipping unknown pre-book line: {}".format( line ) )

        # Save the final book
        if thisBook is not None: self.stashBook( thisBook )

        # Clean up
        if settingsDict:
            #print( "ForgeForSwordSearcher settingsDict", settingsDict )
            if self.suppliedMetadata is None: self.suppliedMetadata = {}
            self.suppliedMetadata['Forge4SS'] = settingsDict
            self.applySuppliedMetadata( 'Forge4SS' ) # Copy some to self.settingsDict

        self.doPostLoadProcessing()
    # end of ForgeForSwordSearcherBible.load
# end of ForgeForSwordSearcherBible class



def testForge4SS( F4SSFolder ):
    # Crudely demonstrate the Forge for SwordSearcher Bible class
    from BibleOrgSys.Reference import VerseReferences

    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the Forge for SwordSearcher Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r}".format( F4SSFolder ) )
    vb = ForgeForSwordSearcherBible( F4SSFolder, "demo" )
    vb.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( vb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        vb.check()
        #print( UsfmB.books['GEN']._processedLines[0:40] )
        vBErrors = vb.getErrors()
        # print( vBErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##vb.toDrupalBible()
        vb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(vb)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(vb)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(vb)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #print( svk, ob.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = vb.getVerseText( svk )
        except KeyError:
            verseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
# end of testForge4SS


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for testFolder in (
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest2/' ),
                    ):
            result1 = ForgeForSwordSearcherBibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nForgeForSwordSearcher TestA1", result1 )

            result2 = ForgeForSwordSearcherBibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "ForgeForSwordSearcher TestA2", result2 )
            if result2 is not None:
                try: result2.loadMetadataTextFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )
                except FileNotFoundError: pass # it's not compulsory
                if BibleOrgSysGlobals.strictCheckingFlag:
                    result2.check()
                    #print( UsfmB.books['GEN']._processedLines[0:40] )
                    vBErrors = result2.getErrors()
                    # print( vBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##result2.toDrupalBible()
                    result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

            result3 = ForgeForSwordSearcherBibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "ForgeForSwordSearcher TestA3", result3 )
            if result3 is not None:
                try: result3.loadMetadataTextFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )
                except FileNotFoundError: pass # it's not compulsory
                if BibleOrgSysGlobals.strictCheckingFlag:
                    result3.check()
                    #print( UsfmB.books['GEN']._processedLines[0:40] )
                    vBErrors = result3.getErrors()
                    # print( vBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##result3.toDrupalBible()
                    result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


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
                results = pool.map( testForge4SS, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nForgeForSwordSearcher D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testForge4SS( someFolder )
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
# end of ForgeForSwordSearcherBible.py
