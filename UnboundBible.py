#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UnboundBible.py
#   Last modified: 2013-04-15 by RJH (also update versionString below)
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
"""

progName = "Unbound Bible format handler"
versionString = "0.11"

import logging, os
from gettext import gettext as _
from collections import OrderedDict

import Globals
from Bible import Bible, BibleBook



def UnboundBibleFileCheck( givenFolderName, autoLoad=False ):
    """
    Given a folder, search for Unbound Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one Unbound Bible is found,
        returns the loaded UnboundBible object.
    """
    if Globals.verbosityLevel > 2: print( "UnboundBibleFileCheck( {}, {} )".format( givenFolderName, autoLoad ) )
    assert( givenFolderName and isinstance( givenFolderName, str ) )
    assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("UnboundBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " UnboundBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ): foundFiles.append( something )

    # See if there's an UnboundBible project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename in ('book_names.txt','Readme.txt' ): looksHopeful = True
        elif thisFilename.endswith( '_utf8.txt' ):
            if 1 or Globals.strictCheckingFlag:
                firstLine = Globals.peekIntoFile( thisFilename, givenFolderName )
                if firstLine != "#THE UNBOUND BIBLE (www.unboundbible.org)":
                    if Globals.verbosityLevel > 2: print( "UB (unexpected) first line was '{}' in {}".format( firstLine, thisFilename ) ); halt
                    continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if numFound == 1 and autoLoad:
            ub = UnboundBible( givenFolderName, lastFilenameFound[:-9] ) # Remove the end of the actual filename
            ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and Globals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if Globals.verbosityLevel > 3: print( "    UnboundBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ): foundSubfiles.append( something )

        # See if there's an UB project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if thisFilename.endswith( '_utf8.txt' ):
                if 1 or Globals.strictCheckingFlag:
                    firstLine = Globals.peekIntoFile( thisFilename, tryFolderName )
                    if firstLine != "#THE UNBOUND BIBLE (www.unboundbible.org)":
                        if Globals.verbosityLevel > 2: print( "UB (unexpected) first line was '{}' in {}".format( firstLine, thisFilname ) ); halt
                        continue
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        if numFound == 1 and autoLoad:
            assert( len(foundProjects) == 1 )
            ub = UnboundBible( foundProjects[0][0], foundProjects[0][1][:-9] )
            ub.load() # Load and process the file
            return ub
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
                    #print( "      Detected UTF-16 Byte Order Marker" )
                    #line = line[1:] # Remove the UTF-8 Byte Order Marker
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                #print ( 'UB file line is "' + line + '"' )
                if line[0]=='#': continue # Just discard comment lines

                bits = line.split( '\t' )
                #print( self.givenName, BBB, bits )
                if len(bits) == 4:
                    bookCode, chapterNumberString, verseNumberString, vText = bits
                elif len(bits) == 6:
                    bookCode, chapterNumberString, verseNumberString, subverseNumberString, sequenceNumberString, vText = bits
                elif len(bits) == 9:
                    NRSVA_bookCode, NRSVA_chapterNumberString, NRSVA_verseNumberString, bookCode, chapterNumberString, verseNumberString, subverseNumberString, sequenceNumberString, vText = bits
                elif len(bits) == 1 and self.givenName.startswith( 'lxx_a_parsing_' ):
                    if Globals.logErrorsFlag: logging.warning( _("Skipping bad '{}' line in {} {} {} {}:{}").format( line, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    continue
                else: print( "Expected number of bits", self.givenName, BBB, bookCode, chapterNumberString, verseNumberString, len(bits), bits ); halt

                if NRSVA_bookCode: assert( len(NRSVA_bookCode) == 3 )
                if NRSVA_chapterNumberString: assert( NRSVA_chapterNumberString.isdigit() )
                if NRSVA_verseNumberString: assert( NRSVA_verseNumberString.isdigit() )

                if not bookCode and not chapterNumberString and not verseNumberString:
                    print( "Skipping empty line in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    continue
                assert( len(bookCode) == 3 )
                assert( chapterNumberString.isdigit() )
                assert( verseNumberString.isdigit() )

                if subverseNumberString:
                    if Globals.logErrorsFlag: logging.warning( _("subverseNumberString '{}' in {} {} {}:{}").format( subverseNumberString, BBB, bookCode, chapterNumberString, verseNumberString ) )

                vText = vText.strip() # Remove leading and trailing spaces
                if not vText: continue # Just ignore blank verses I think
                if vText == '+': continue # Not sure what this means in basic_english JHN 1:38

                chapterNumber = int( chapterNumberString )
                verseNumber = int( verseNumberString )
                if sequenceNumberString:
                    assert( sequenceNumberString.isdigit() )
                    sequenceNumber = int( sequenceNumberString )
                    assert( sequenceNumber > lastSequence or \
                        self.givenName in ('gothic_latin', 'hebrew_bhs_consonants', 'hebrew_bhs_vowels', 'latvian_nt', 'ukrainian_1871',) ) # Why???
                    lastSequence = sequenceNumber

                if bookCode != lastBookCode: # We've started a new book
                    if lastBookCode != -1: # Better save the last book
                        self.saveBook( BBB, thisBook )
                    BBB = Globals.BibleBooksCodes.getBBBFromUnboundBibleCode( bookCode )
                    thisBook = BibleBook( BBB )
                    thisBook.objectNameString = "Unbound Bible Book object"
                    thisBook.objectTypeString = "Unbound"
                    lastBookCode = bookCode
                    lastChapterNumber = lastVerseNumber = -1

                if chapterNumber != lastChapterNumber: # We've started a new chapter
                    assert( chapterNumber > lastChapterNumber or BBB=='ESG' ) # Esther Greek might be an exception
                    if chapterNumber == 0:
                        if Globals.logErrorsFlag: logging.info( "Have chapter zero in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    thisBook.appendLine( 'c', chapterNumberString )
                    lastChapterNumber = chapterNumber
                    lastVerseNumber = -1

                # Handle the verse info
                if verseNumber==lastVerseNumber and vText==lastVText:
                    if Globals.logErrorsFlag: logging.warning( _("Ignored duplicate verse line in {} {} {} {}:{}").format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    continue
                if BBB=='PSA' and verseNumberString=='1' and vText.startswith('&lt;') and self.givenName=='basic_english':
                    # Move Psalm titles to verse zero
                    verseNumber = 0
                if verseNumber < lastVerseNumber:
                    if Globals.logErrorsFlag: logging.warning( _("Ignored receding verse number (from {} to {}) in {} {} {} {}:{}").format( lastVerseNumber, verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                elif verseNumber == lastVerseNumber:
                    if vText == lastVText:
                        if Globals.logErrorsFlag: logging.warning( _("Ignored duplicated {} verse in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    else:
                        if Globals.logErrorsFlag: logging.warning( _("Ignored duplicated {} verse number in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                thisBook.appendLine( 'v', verseNumberString + ' ' + vText )
                lastVText = vText
                lastVerseNumber = verseNumber

        # Save the final bookCode
        self.saveBook( BBB, thisBook )
    # end of UnboundBible.load
# end of UnboundBible class



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the data file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )


    import VerseReferences
    def testUB( TUBfolder, TUBfilename ):
        # Demonstrate the Unbound Bible class
        if Globals.verbosityLevel > 1: print( _("Demonstrating the Unbound Bible class...") )
        if Globals.verbosityLevel > 2: print( "  Test folder is '{}' '{}'".format( TUBfolder, TUBfilename ) )
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
            print( reference, svk.getShortText(), ub.getVerseText( svk ) )


    testFolder = "../../../../../Data/Work/Bibles/Biola Unbound modules/"

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        print( "TestA1", UnboundBibleFileCheck( testFolder ) )
        print( "TestA2", UnboundBibleFileCheck( testFolder, autoLoad=True ) )
        testSubfolder = os.path.join( testFolder, 'asv/' )
        print( "TestB1", UnboundBibleFileCheck( testSubfolder ) )
        print( "TestB2", UnboundBibleFileCheck( testSubfolder, autoLoad=True ) )


    if 1: # specified modules
        single = ( "kjv_apocrypha", )
        good = ( "afrikaans_1953", "albanian", "aleppo", "amharic", "arabic_svd", "armenian_eastern", \
                "armenian_western_1853", "asv", "basic_english", "danish", "darby", "douay_rheims", "dutch_svv", \
                "esperanto", "estonian", "kjv_apocrypha", "korean", "manx_gaelic", "maori", "myanmar_judson_1835", \
                "norwegian", "peshitta", "portuguese", "potawatomi", "romani", )
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( single ): # Choose one of the above: single, good, nonEnglish, bad
            print( "\n{}/ Trying {}".format( j+1, testFilename ) )
            myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testUB( myTestFolder, testFilename )


    if 1: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
        for j, someFolder in enumerate( sorted( foundFolders ) ):
            print( "\n{}/ Trying {}".format( j+1, someFolder ) )
            myTestFolder = os.path.join( testFolder, someFolder+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testUB( myTestFolder, someFolder )
# end of demo

if __name__ == '__main__':
    demo()
# end of UnboundBible.py