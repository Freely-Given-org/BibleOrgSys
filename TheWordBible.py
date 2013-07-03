#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# TheWordBible.py
#   Last modified: 2013-07-03 by RJH (also update ProgVersion below)
#
# Module handling "TheWord" Bible module files
#
# Copyright (C) 2013 Robert Hunt
# Author: Robert Hunt <robert316@users.sourceforge.net>
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
Module reading and loading TheWord Bible files.
These can be downloaded from: http://www.theword.net/index.php?downloads.modules

A TheWord Bible module file has one verse per line (KJV versification)
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

ProgName = "TheWord Bible format handler"
ProgVersion = "0.01"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )


import logging, os
from gettext import gettext as _
import multiprocessing

import Globals
from Bible import Bible, BibleBook


filenameEndingsToAccept = ('.OT','.NT','.ONT','.ONTX',) # Must be UPPERCASE
#filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
#extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX', 'STY', 'LDS', 'SSF', 'VRS',) # Must be UPPERCASE



def TheWordBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for TheWord Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one TheWord Bible is found,
        returns the loaded TheWordBible object.
    """
    if Globals.verbosityLevel > 2: print( "TheWordBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("TheWordBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("TheWordBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " TheWordBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            #ignore = False
            #for ending in filenameEndingsToIgnore:
                #if somethingUpper.endswith( ending): ignore=True; break
            #if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
            if somethingUpperExt in filenameEndingsToAccept:
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an TheWordBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "TheWordBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and autoLoad:
            twB = TheWordBible( givenFolderName, lastFilenameFound )
            twB.load() # Load and process the file
            return twB
        return numFound
    elif looksHopeful and Globals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("TheWordBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if Globals.verbosityLevel > 3: print( "    TheWordBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
                if somethingUpperExt in filenameEndingsToAccept:
                    foundSubfiles.append( something )

        # See if there's an TW project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "TheWordBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            if Globals.debugFlag: assert( len(foundProjects) == 1 )
            twB = TheWordBible( foundProjects[0][0], foundProjects[0][1] )
            twB.load() # Load and process the file
            return twB
        return numFound
# end of TheWordBibleFileCheck



class TheWordBible( Bible ):
    """
    Class for reading, validating, and converting TheWordBible files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "TheWord Bible object"
        self.objectTypeString = "TheWord"

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.givenName = os.path.splitext( self.sourceFilename )[0]
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("TheWordBible: File '{}' is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
    # end of TheWordBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )

        fileExtensionUpper = os.path.splitext( self.sourceFilename )[1].upper()
        assert( fileExtensionUpper in filenameEndingsToAccept )

        if fileExtensionUpper == '.ONT':
            testament = 'BOTH'
            textLineCount = 31102
        elif fileExtensionUpper == '.OT':
            testament = 'OT'
            textLineCount = 23145
        elif fileExtensionUpper == '.NT':
            testament = 'NT'
            textLineCount = 7957

        lastLine, lineCount = '', 0
        BBB = lastBBB = None
        lastVText = ''
        with open( self.sourceFilepath, encoding=self.encoding ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                #if lineCount==1 and self.encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF
                    #logging.info( "      TheWordBible.load: Detected UTF-16 Byte Order Marker" )
                    #line = line[1:] # Remove the UTF-8 Byte Order Marker
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                print ( 'TW file line is "' + line + '"' )

                continue # temp

                if '=' in line: # This is module info (and should be at the end after all the Biblical text)
                    assert( lineCount > textLineCount )
                    print( "Have module info:", line )
                else: # assume it's verse text
                    assert( lineCount <= textLineCount )
                    if BBB != lastBBB: # We've started a new book
                        if lastBBBB: # Better save the last book
                            self.saveBook( thisBook )
                        BBB = Globals.BibleBooksCodes.getBBBFromTheWordBibleCode( bookCode )
                        thisBook = BibleBook( BBB )
                        thisBook.objectNameString = "TheWord Bible Book object"
                        thisBook.objectTypeString = "TheWord"
                        lastBookCode = bookCode
                        lastChapterNumber = lastVerseNumber = -1

                    if chapterNumber != lastChapterNumber: # We've started a new chapter
                        if Globals.debugFlag: assert( chapterNumber > lastChapterNumber or BBB=='ESG' ) # Esther Greek might be an exception
                        if chapterNumber == 0:
                            logging.info( "Have chapter zero in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                        thisBook.appendLine( 'c', chapterNumberString )
                        lastChapterNumber = chapterNumber
                        lastVerseNumber = -1

                    # Handle the verse info
                    if verseNumber==lastVerseNumber and vText==lastVText:
                        logging.warning( _("Ignored duplicate verse line in {} {} {} {}:{}").format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                        continue
                    if BBB=='PSA' and verseNumberString=='1' and vText.startswith('&lt;') and self.givenName=='basic_english':
                        # Move Psalm titles to verse zero
                        verseNumber = 0
                    if verseNumber < lastVerseNumber:
                        logging.warning( _("Ignored receding verse number (from {} to {}) in {} {} {} {}:{}").format( lastVerseNumber, verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    elif verseNumber == lastVerseNumber:
                        if vText == lastVText:
                            logging.warning( _("Ignored duplicated {} verse in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                        else:
                            logging.warning( _("Ignored duplicated {} verse number in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    thisBook.appendLine( 'v', verseNumberString + ' ' + vText )
                    lastVText = vText
                    lastVerseNumber = verseNumber

        # Save the final bookCode
        self.saveBook( thisBook )
    # end of TheWordBible.load
# end of TheWordBible class



def testTWB( TUBfilename ):
    # Crudely demonstrate the TheWord Bible class
    import VerseReferences
    #testFolder = "../../../../../Data/Work/Bibles/TheWord modules/" # Must be the same as below

    TUBfolder = os.path.join( testFolder, TUBfilename+'/' )
    if Globals.verbosityLevel > 1: print( _("Demonstrating the TheWord Bible class...") )
    if Globals.verbosityLevel > 0: print( "  Test folder is '{}' '{}'".format( TUBfolder, TUBfilename ) )
    ub = TheWordBible( TUBfolder, TUBfilename )
    ub.load() # Load and process the file
    if Globals.verbosityLevel > 1: print( ub ) # Just print a summary
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(ub)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(ub)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(ub)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #print( svk, ob.getVerseDataList( reference ) )
        shortText, verseText = svk.getShortText(), ub.getVerseText( svk )
        if Globals.verbosityLevel > 1: print( reference, shortText, verseText )
# end of testTWB


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )


    #testFolder = "../../../../../Data/Work/Bibles/TheWord modules/"
    testFolder = "Tests/DataFilesForTests/TheWordTest/"


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = TheWordBibleFileCheck( testFolder )
        if Globals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = TheWordBibleFileCheck( testFolder, autoLoad=True )
        if Globals.verbosityLevel > 1: print( "TestA2", result2 )


    if 0: # specified modules
        single = ( "kjv_apocrypha", )
        good = ( "afrikaans_1953", "albanian", "aleppo", "amharic", "arabic_svd", "armenian_eastern", \
                "armenian_western_1853", "asv", "basic_english", "danish", "darby", "douay_rheims", "dutch_svv", \
                "esperanto", "estonian", "kjv_apocrypha", "korean", "manx_gaelic", "maori", "myanmar_judson_1835", \
                "norwegian", "peshitta", "portuguese", "potawatomi", "romani", )
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( single ): # Choose one of the above: single, good, nonEnglish, bad
            if Globals.verbosityLevel > 1: print( "\n{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testTWB( testFilename )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if Globals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if Globals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testTWB, parameters ) # have the pool do our loads
                assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if Globals.verbosityLevel > 1: print( "\n{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testTWB( someFolder )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of TheWordBible.py