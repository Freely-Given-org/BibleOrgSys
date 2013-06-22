#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UnboundBible.py
#   Last modified: 2013-06-22 by RJH (also update versionString below)
#
# Module handling Biola University "unbound" Bible files
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
Module reading and loading Biola University Unbound Bible files.
These can be downloaded from: http://unbound.biola.edu/index.cfm?method=downloads.showDownloadMain

Note that some modules have repeated lines (as at April 2013).  :-(
There also seem to be a range of other errors so these UB modules are not reliably checked.  :-(

A typical Unbound Bible file starts with lines beginning with #
    which contain some meta-data
    and then the main data lines are separated by tabs.
Different versions have different numbers of tab-separated fields.

e.g.,
    #THE UNBOUND BIBLE (www.unboundbible.org)
    #name   English: King James Version
    #filetype       Unmapped-BCVS
    #copyright      Public Domain
    #abbreviation
    #language       eng
    #note
    #columns        orig_book_index orig_chapter    orig_verse      orig_subverse   order_by        text
    01O     1       1               10      In the beginning God created the heaven and the earth.
    01O     1       2               20      And the earth was without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.
    01O     1       3               30      And God said, Let there be light: and there was light.
and
    #THE UNBOUND BIBLE (www.unboundbible.org)
    #name   English: American Standard Version
    #filetype       Unmapped-BCVS
    #copyright      Published 1901. Public Domain.
    #abbreviation
    #language       eng
    #note
    #columns        orig_book_index orig_chapter    orig_verse      orig_subverse   order_by        text
    01O     1       1               10      In the beginning God created the heavens and the earth.
    01O     1       2               20      And the earth was waste and void; and darkness was upon the face of the deep: and the Spirit of God moved upon the face of the waters
    01O     1       3               30      And God said, Let there be light: and there was light.
and
    #THE UNBOUND BIBLE (www.unboundbible.org)
    #name   Maori
    #filetype       Unmapped-BCVS
    #copyright
    #abbreviation
    #language       mbf
    #note
    #columns        orig_book_index orig_chapter    orig_verse      orig_subverse   order_by        text
    01O     1       1               10      ¶ He mea hanga na te atua i te timatanga te rangi me te whenua.
    01O     1       2               20      A kahore he ahua o te whenua, i takoto kau; he pouri ano a runga i te mata o te hohonu. Na ka whakapaho te Wairua o te Atua i runga i te kare o nga wai.
    01O     1       3               30      ¶ A ka ki te Atua, Kia marama: na ka marama.
    01O     1       4               40      A ka kite te Atua i te marama, he pai: a ka wehea e te Atua te marama i te pouri.
and
    #THE UNBOUND BIBLE (www.unboundbible.org)
    #name   Albanian
    #filetype       Unmapped-BCV
    #copyright
    #abbreviation
    #language       aln
    #note
    #columns        orig_book_index orig_chapter    orig_verse      text
    01O     1       1       Në fillim Perëndia krijoi qiejt dhe tokën.
    01O     1       2       Toka ishte pa trajtë, e zbrazët dhe errësira mbulonte sipërfaqen e humnerës; dhe Fryma e Perëndisë fluturonte mbi sipërfaqen e ujërave.
"""

progName = "Unbound Bible format handler"
versionString = "0.12"

import logging, os
from gettext import gettext as _
import multiprocessing

import Globals
from Bible import Bible, BibleBook


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX', 'STY', 'LDS', 'SSF', 'VRS',) # Must be UPPERCASE



def UnboundBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for Unbound Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one Unbound Bible is found,
        returns the loaded UnboundBible object.
    """
    if Globals.verbosityLevel > 2: print( "UnboundBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("UnboundBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("UnboundBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " UnboundBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an UnboundBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename in ('book_names.txt','Readme.txt' ): looksHopeful = True
        elif thisFilename.endswith( '_utf8.txt' ):
            if strictCheck or Globals.strictCheckingFlag:
                firstLine = Globals.peekIntoFile( thisFilename, givenFolderName )
                if firstLine != "#THE UNBOUND BIBLE (www.unboundbible.org)":
                    if Globals.verbosityLevel > 2: print( "UB (unexpected) first line was '{}' in {}".format( firstLine, thisFilename ) )
                    continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "UnboundBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and autoLoad:
            uB = UnboundBible( givenFolderName, lastFilenameFound[:-9] ) # Remove the end of the actual filename "_utf8.txt"
            uB.load() # Load and process the file
            return uB
        return numFound
    elif looksHopeful and Globals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("UnboundBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if Globals.verbosityLevel > 3: print( "    UnboundBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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

        # See if there's an UB project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if thisFilename.endswith( '_utf8.txt' ):
                if strictCheck or Globals.strictCheckingFlag:
                    firstLine = Globals.peekIntoFile( thisFilename, tryFolderName )
                    if firstLine != "#THE UNBOUND BIBLE (www.unboundbible.org)":
                        if Globals.verbosityLevel > 2: print( "UB (unexpected) first line was '{}' in {}".format( firstLine, thisFilname ) ); halt
                        continue
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "UnboundBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            if Globals.debugFlag: assert( len(foundProjects) == 1 )
            uB = UnboundBible( foundProjects[0][0], foundProjects[0][1][:-9] ) # Remove the end of the actual filename "_utf8.txt"
            uB.load() # Load and process the file
            return uB
        return numFound
# end of UnboundBibleFileCheck



class UnboundBible( Bible ):
    """
    Class for reading, validating, and converting UnboundBible files.
    """
    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "Unbound Bible object"
        self.objectTypeString = "Unbound"

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'_utf8.txt' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("UnboundBible: File '{}' is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of UnboundBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )

        lastLine, lineCount = '', 0
        BBB = None
        NRSVA_bookCode = NRSVA_chapterNumberString = NRSVA_verseNumberString = None
        subverseNumberString = sequenceNumberString = None
        lastBookCode = lastChapterNumber = lastVerseNumber = lastSequence = -1
        lastVText = ''
        with open( self.sourceFilepath, encoding=self.encoding ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                #if lineCount==1 and self.encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF
                    #logging.info( "      UnboundBible.load: Detected UTF-16 Byte Order Marker" )
                    #line = line[1:] # Remove the UTF-8 Byte Order Marker
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                #print ( 'UB file line is "' + line + '"' )
                if line[0]=='#':
                    hashBits = line[1:].split( '\t' )
                    if len(hashBits)==2 and hashBits[1]: # We have some valid meta-data
                        if hashBits[0] == 'name': self.name = hashBits[1]
                        elif hashBits[0] == 'filetype': self.filetype = hashBits[1]
                        elif hashBits[0] == 'copyright': self.copyright = hashBits[1]
                        elif hashBits[0] == 'abbreviation': self.abbreviation = hashBits[1]
                        elif hashBits[0] == 'language': self.language = hashBits[1]
                        elif hashBits[0] == 'note': self.note = hashBits[1]
                        elif hashBits[0] == 'columns': self.columns = hashBits[1]
                        logging.warning( "Unknown UnboundBible meta-data field '{}' = '{}'".format( hashBits[0], hashBits[1] ) )
                    continue # Just discard comment lines

                bits = line.split( '\t' )
                #print( self.givenName, BBB, bits )
                if len(bits) == 4:
                    bookCode, chapterNumberString, verseNumberString, vText = bits
                elif len(bits) == 6:
                    bookCode, chapterNumberString, verseNumberString, subverseNumberString, sequenceNumberString, vText = bits
                elif len(bits) == 9:
                    NRSVA_bookCode, NRSVA_chapterNumberString, NRSVA_verseNumberString, bookCode, chapterNumberString, verseNumberString, subverseNumberString, sequenceNumberString, vText = bits
                elif len(bits) == 1 and self.givenName.startswith( 'lxx_a_parsing_' ):
                    logging.warning( _("Skipping bad '{}' line in {} {} {} {}:{}").format( line, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    continue
                else: print( "Expected number of bits", self.givenName, BBB, bookCode, chapterNumberString, verseNumberString, len(bits), bits ); halt

                if NRSVA_bookCode: assert( len(NRSVA_bookCode) == 3 )
                if NRSVA_chapterNumberString: assert( NRSVA_chapterNumberString.isdigit() )
                if NRSVA_verseNumberString: assert( NRSVA_verseNumberString.isdigit() )

                if not bookCode and not chapterNumberString and not verseNumberString:
                    print( "Skipping empty line in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    continue
                if Globals.debugFlag: assert( len(bookCode) == 3 )
                if Globals.debugFlag: assert( chapterNumberString.isdigit() )
                if Globals.debugFlag: assert( verseNumberString.isdigit() )

                if subverseNumberString:
                    logging.warning( _("subverseNumberString '{}' in {} {} {}:{}").format( subverseNumberString, BBB, bookCode, chapterNumberString, verseNumberString ) )

                vText = vText.strip() # Remove leading and trailing spaces
                if not vText: continue # Just ignore blank verses I think
                if vText == '+': continue # Not sure what this means in basic_english JHN 1:38

                chapterNumber = int( chapterNumberString )
                verseNumber = int( verseNumberString )
                if sequenceNumberString:
                    if Globals.debugFlag: assert( sequenceNumberString.isdigit() )
                    sequenceNumber = int( sequenceNumberString )
                    if Globals.debugFlag: assert( sequenceNumber > lastSequence or \
                        self.givenName in ('gothic_latin', 'hebrew_bhs_consonants', 'hebrew_bhs_vowels', 'latvian_nt', 'ukrainian_1871',) ) # Why???
                    lastSequence = sequenceNumber

                if bookCode != lastBookCode: # We've started a new book
                    if lastBookCode != -1: # Better save the last book
                        self.saveBook( thisBook )
                    BBB = Globals.BibleBooksCodes.getBBBFromUnboundBibleCode( bookCode )
                    thisBook = BibleBook( BBB )
                    thisBook.objectNameString = "Unbound Bible Book object"
                    thisBook.objectTypeString = "Unbound"
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
    # end of UnboundBible.load
# end of UnboundBible class



def testUB( TUBfilename ):
    # Crudely demonstrate the Unbound Bible class
    import VerseReferences
    testFolder = "../../../../../Data/Work/Bibles/Biola Unbound modules/" # Must be the same as below

    TUBfolder = os.path.join( testFolder, TUBfilename+'/' )
    if Globals.verbosityLevel > 1: print( _("Demonstrating the Unbound Bible class...") )
    if Globals.verbosityLevel > 0: print( "  Test folder is '{}' '{}'".format( TUBfolder, TUBfilename ) )
    ub = UnboundBible( TUBfolder, TUBfilename )
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
# end of testUB


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )


    testFolder = "../../../../../Data/Work/Bibles/Biola Unbound modules/"


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = UnboundBibleFileCheck( testFolder )
        if Globals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = UnboundBibleFileCheck( testFolder, autoLoad=True )
        if Globals.verbosityLevel > 1: print( "TestA2", result2 )
        testSubfolder = os.path.join( testFolder, 'asv/' )
        result3 = UnboundBibleFileCheck( testSubfolder )
        if Globals.verbosityLevel > 1: print( "TestB1", result3 )
        result4 = UnboundBibleFileCheck( testSubfolder, autoLoad=True )
        if Globals.verbosityLevel > 1: print( "TestB2", result4 )


    if 1: # specified modules
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
            testUB( testFilename )


    if 1: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if Globals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if Globals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testUB, parameters ) # have the pool do our loads
                assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if Globals.verbosityLevel > 1: print( "\n{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testUB( someFolder )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( progName, versionString )
    Globals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( progName, versionString )
# end of UnboundBible.py