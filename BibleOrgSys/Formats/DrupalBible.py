#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# DrupalBible.py
#
# Module handling DrupalBible Bible files
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
Module reading and loading DrupalBible Bible files.


http://drupalbible.org/node/47

http://drupalbible.mikelee.idv.tw/?q=node/27


e.g.,
    *Bible
    #shortname fullname language
    KJaV1|King James(en)|en

    *Chapter
    #book,fullname,shortname,chap-count
    GEN|Genesis|GEN|50
    EXO|Exodus|EXO|40
    LEV|Leviticus|LEV|27
    NUM|Numbers|NUM|36
    …
    JUD|Jude|JUD|1
    REV|Revelation|REV|22

    *Context
    #Book,Chapter,Verse,LineMark,Context
    GEN|1|1||In the beginning God created the heaven and the earth.
    GEN|1|2||And the earth was without form, and void; and darkness [was] upon the face of the deep. And the Spirit of God moved upon the face of the waters.
    GEN|1|3||And God said, Let there be light: and there was light.
    GEN|1|4||And God saw the light, that [it was] good: and God divided the light from the darkness.
    GEN|1|5||And God called the light Day, and the darkness he called Night. And the evening and the morning were the first day.
    …
    PS|2|12||Kiss the Son, lest he be angry, and ye perish [from] the way, when his wrath is kindled but a little. Blessed [are] all they that put their trust in him.
    PS|3|1||<A Psalm of David, when he fled from Absalom his son.> LORD, how are they increased that trouble me! many [are] they that rise up against me.
    PS|3|2||Many [there be] which say of my soul, [There is] no help for him in God. Selah.
    …
    ROM|16|26||But now is made manifest, and by the scriptures of the prophets, according to the commandment of the everlasting God, made known to all nations for the obedience of faith:
    ROM|16|27||To God only wise, [be] glory through Jesus Christ for ever. Amen. <Written to the Romans from Corinthus, [and sent] by Phebe servant of the church at Cenchrea.>
    1CO|1|1||Paul, called [to be] an apostle of Jesus Christ through the will of God, and Sosthenes [our] brother,
    …
    REV|22|19||And if any man shall take away from the words of the book of this prophecy, God shall take away his part out of the book of life, and out of the holy city, and [from] the things which are written in this book.
    REV|22|20||He which testifieth these things saith, Surely I come quickly. Amen. Even so, come, Lord Jesus.
    REV|22|21||The grace of our Lord Jesus Christ [be] with you all. Amen.

Limitations:
    Only checked one one file so far kjv.bc
    <…> were converted to \\it …\\it* (Psalms and signatures to Paul's letters.)
    Need to do Bible books codes properly -- current implementation is just a hack
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "DrupalBible"
PROGRAM_NAME = "DrupalBible Bible format handler"
PROGRAM_VERSION = '0.13'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook


filenameEndingsToAccept = ('.BC',) # Must be UPPERCASE



def DrupalBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for DrupalBible Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one DrupalBible Bible is found,
        returns the loaded DrupalBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "DrupalBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("DrupalBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("DrupalBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " DrupalBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
            if somethingUpperExt in filenameEndingsToAccept:
                foundFiles.append( something )

    # See if there's an DrupalBible project here in this given folder
    numFound = 0
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename.endswith( '.bc' ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName )
                if firstLine is None: continue # seems we couldn't decode the file
                if ( not firstLine.startswith( '\ufeff*Bible' ) ) and ( not firstLine.startswith( "*Bible" ) ):
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "DrupalBible (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                    continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "DrupalBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = DrupalBible( givenFolderName, lastFilenameFound[:-3] ) # Remove the end of the actual filename ".bc"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("DrupalBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    DrupalBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                if somethingUpperExt in filenameEndingsToAccept:
                    foundSubfiles.append( something )

        # See if there's an DrupalBible project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if thisFilename.endswith( '.bc' ):
                if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                    firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName )
                    if firstLine is None: continue # seems we couldn't decode the file
                    if ( not firstLine.startswith( '\ufeff*Bible' ) ) and ( not firstLine.startswith( "*Bible" ) ):
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "DrupalBible (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) ); halt
                        continue
                #print( "BFC_here", repr(tryFolderName), repr(thisFilename) )
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "DrupalBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            uB = DrupalBible( foundProjects[0][0], foundProjects[0][1][:-3] ) # Remove the end of the actual filename ".bc"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of DrupalBibleFileCheck



class DrupalBible( Bible ):
    """
    Class for reading, validating, and converting DrupalBible files.
    """
    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("DrupalBible__init__ ( {!r}, {!r}, {!r} )").format( sourceFolder, givenName, encoding ) )
        assert sourceFolder
        assert givenName

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'DrupalBible Bible object'
        self.objectTypeString = 'DrupalBible'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'.bc' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("DrupalBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of DrupalBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )

        status = 0 # 1 = getting chapters, 2 = getting verse data
        lastLine, lineCount = '', 0
        BBB = lastBBB = None
        bookDetails = {}
        with open( self.sourceFilepath, encoding=self.encoding ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                if lineCount==1:
                    if line[0]==chr(65279): #U+FEFF
                        logging.info( "DrupalBible.load1: Detected Unicode Byte Order Marker (BOM) in {}".format( self.sourceFilepath ) )
                        line = line[1:] # Remove the UTF-16 Unicode Byte Order Marker (BOM)
                    elif line[:3] == 'ï»¿': # 0xEF,0xBB,0xBF
                        logging.info( "DrupalBible.load2: Detected Unicode Byte Order Marker (BOM) in {}".format( self.sourceFilepath ) )
                        line = line[3:] # Remove the UTF-8 Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines

                #print ( 'DB file line is "' + line + '"' )
                if line[0] == '#': continue # Just discard comment lines
                lastLine = line
                if lineCount == 1:
                    if line != '*Bible':
                        logging.warning( "Unknown DrupalBible first line: {}".format( repr(line) ) )

                elif status == 0:
                    if line == '*Chapter': status = 1
                    else: # Get the version name details
                        bits = line.split( '|' )
                        shortName, fullName, language = bits
                        self.name = fullName

                elif status == 1:
                    if line == '*Context': status = 2
                    else: # Get the book name details
                        bits = line.split( '|' )
                        bookCode, bookFullName, bookShortName, numChapters = bits
                        assert bookShortName == bookCode
                        BBBresult = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromDrupalBibleCode( bookCode )
                        BBB = BBBresult if isinstance( BBBresult, str ) else BBBresult[0] # Result can be string or list of strings (best guess first)
                        bookDetails[BBB] = bookFullName, bookShortName, numChapters

                elif status == 2: # Get the verse text
                    bits = line.split( '|' )
                    bookCode, chapterNumberString, verseNumberString, lineMark, verseText = bits
                    #chapterNumber, verseNumber = int( chapterNumberString ), int( verseNumberString )
                    if lineMark: print( repr(lineMark) ); halt
                    BBBresult = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromDrupalBibleCode( bookCode )
                    BBB = BBBresult if isinstance( BBBresult, str ) else BBBresult[0] # Result can be string or list of strings (best guess first)
                    if BBB != lastBBB:
                        if lastBBB is not None:
                            self.stashBook( thisBook )
                        thisBook = BibleBook( self, BBB )
                        thisBook.objectNameString = 'DrupalBible Bible Book object'
                        thisBook.objectTypeString = 'DrupalBible'
                        lastChapterNumberString = None
                        lastBBB = BBB
                    if chapterNumberString != lastChapterNumberString:
                        thisBook.addLine( 'c', chapterNumberString )
                        lastChapterNumberString = chapterNumberString
                    verseText = verseText.replace( '<', '\\it ' ).replace( '>', '\\it*' )
                    thisBook.addLine( 'v', verseNumberString + ' ' + verseText )

                else: halt

        # Save the final book
        self.stashBook( thisBook )
        self.doPostLoadProcessing()
    # end of DrupalBible.load
# end of DrupalBible class



def testDB( TUBfilename ):
    # Crudely demonstrate the DrupalBible class
    from BibleOrgSys.Reference import VerseReferences
    TUBfolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DrupalTest/') # Must be the same as below

    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the DrupalBible Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( TUBfolder, TUBfilename ) )
    db = DrupalBible( TUBfolder, TUBfilename )
    db.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( db ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag: db.check()
    if BibleOrgSysGlobals.commandLineArguments.export: db.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(db)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(db)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(db)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #print( svk, ob.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = db.getVerseText( svk )
        except KeyError:
            verseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
# end of testDB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DrupalTest/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = DrupalBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "DrupalBible TestA1", result1 )
        result2 = DrupalBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "DrupalBible TestA2", result2 )
        result3 = DrupalBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "DrupalBible TestA3", result3 )
        #testSubfolder = os.path.join( testFolder, 'kjv/' )
        #result3 = DrupalBibleFileCheck( testSubfolder )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "DrupalBible TestB1", result3 )
        #result4 = DrupalBibleFileCheck( testSubfolder, autoLoad=True )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "DrupalBible TestB2", result4 )


    if 1: # specified modules
        single = ( 'kjv', )
        good = ( 'kjv', )
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: single, good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDrupalBible C{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testDB( testFilename )


    if 1: # all discovered modules in the test folder
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
                results = pool.map( testDB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDrupalBible D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testDB( someFolder )
# end of demo


if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of DrupalBible.py
