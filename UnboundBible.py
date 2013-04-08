#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UnboundBible.py
#   Last modified: 2013-04-09 by RJH (also update versionString below)
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
versionString = "0.01"

import logging, os
from gettext import gettext as _
from collections import OrderedDict

import Globals
from BibleOrganizationalSystems import BibleOrganizationalSystem
from InternalBible import InternalBible
from InternalBibleBook import InternalBibleBook


class UnboundBible( InternalBible ):
    """
    Class for reading, validating, and converting UnboundBible files.
    """
    treeTag = 'bible'
    bookTag = 'b'
    chapterTag = 'c'
    verseTag = 'v'


    def __init__( self, sourceFolder, givenName, encoding='utf-8', logErrorsFlag=False  ):
        """
        Constructor: just sets up the Bible object.
        """
        self.sourceFolder, self.givenName, self.encoding, self.logErrorsFlag = sourceFolder, givenName, encoding, logErrorsFlag
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'_utf8.txt' )

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "UnboundBible: File '{}' is unreadable".format( self.sourceFilepath ) )
            return # No use continuing

        self.name = self.givenName
        if self.name is None:
            pass

         # Setup and initialise the base class
        self.objectType = "Unbound"
        self.objectNameString = "Unbound Bible object"
        InternalBible.__init__( self, self.name, self.logErrorsFlag )

        self.sourceFolder, self.givenName, self.encoding, self.logErrorsFlag = sourceFolder, givenName, encoding, logErrorsFlag
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'_utf8.txt' )
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
                else: halt

                if NRSVA_bookCode: assert( len(NRSVA_bookCode) == 3 )
                if NRSVA_chapterNumberString: assert( NRSVA_chapterNumberString.isdigit() )
                if NRSVA_verseNumberString: assert( NRSVA_verseNumberString.isdigit() )

                assert( len(bookCode) == 3 )
                assert( chapterNumberString.isdigit() )
                assert( verseNumberString.isdigit() )

                if subverseNumberString:
                    print( "subverseNumberString '{}' in {} {} {}:{}".format( subverseNumberString, BBB, bookCode, chapterNumberString, verseNumberString ) )

                vText = vText.strip() # Remove leading and trailing spaces
                if not vText: continue # Just ignore blank verses I think
                if vText == '+': continue # Not sure what this means in basic_english JHN 1:38

                chapterNumber = int( chapterNumberString )
                verseNumber = int( verseNumberString )
                if sequenceNumberString:
                    assert( sequenceNumberString.isdigit() )
                    sequenceNumber = int( sequenceNumberString )
                    assert( sequenceNumber > lastSequence )
                    lastSequence = sequenceNumber

                if bookCode != lastBookCode: # We've started a new book
                    if lastBookCode != -1: # Better save the last book
                        self.saveBook( BBB, thisBook )
                    BBB = Globals.BibleBooksCodes.getBBBFromUnboundBible( bookCode )
                    thisBook = InternalBibleBook( BBB, self.logErrorsFlag )
                    thisBook.objectType = "Unbound"
                    thisBook.objectNameString = "Unbound Bible Book object"
                    lastBookCode = bookCode
                    lastChapterNumber = lastVerseNumber = -1

                if chapterNumber != lastChapterNumber: # We've started a new chapter
                    assert( chapterNumber > lastChapterNumber or BBB=='ESG' ) # Esther Greek might be an exception
                    if chapterNumber == 0:
                        print( "Note: Have chapter zero in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    thisBook.appendLine( 'c', chapterNumberString )
                    lastChapterNumber = chapterNumber
                    lastVerseNumber = -1

                # Handle the verse info
                if verseNumber==lastVerseNumber and vText==lastVText:
                    print( "Ignored duplicate verse line in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    continue
                if BBB=='PSA' and verseNumberString=='1' and vText.startswith('&lt;') and self.givenName=='basic_english':
                    # Move Psalm titles to verse zero
                    verseNumber = 0
                if verseNumber < lastVerseNumber:
                    print( "Ignored receding verse number (from {} to {}) in {} {} {} {}:{}".format( lastVerseNumber, verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                elif verseNumber == lastVerseNumber:
                    print( "Ignored duplicated {} verse number in {} {} {} {}:{}".format( verseNumber, self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                thisBook.appendLine( 'v', verseNumberString + ' ' + vText )
                lastVText = vText
                lastVerseNumber = verseNumber

        # Save the final bookCode
        self.saveBook( BBB, thisBook )
    # end of UnboundBible.load
# end of UnboundBible class


def main():
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

    testFolder = "/mnt/Data/Work/Bibles/Biola Unbound modules/"
    single = ( "kjv_apocrypha", )
    good = ( "afrikaans_1953", "albanian", "aleppo", "amharic", "arabic_svd", "armenian_eastern", "armenian_western_1853", "asv", "basic_english", "danish", "darby", "douay_rheims", "dutch_svv", "esperanto", "estonian", "kjv_apocrypha", "korean", "manx_gaelic", "maori", "myanmar_judson_1835", "norwegian", "peshitta", "portuguese", "potawatomi", "romani", )
    nonEnglish = (  )
    bad = ( )

    for testFilename in good:
        myTestFolder = os.path.join( testFolder, testFilename+'/' )
        #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )

        # Demonstrate the Unbound Bible class
        if Globals.verbosityLevel > 1: print( "\nDemonstrating the Unbound Bible class..." )
        if Globals.verbosityLevel > 0: print( "  Test folder is '{}' '{}'".format( testFolder, testFilename ) )
        ub = UnboundBible( myTestFolder, testFilename )
        ub.load() # Load and process the file
        print( ub ) # Just print a summary
        #print( xb.books['JDE']._processedLines )
        if 1: # Test verse lookup
            import VerseReferences
            for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                ('OT','DAN','1','21'),
                                ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                (t, b, c, v) = reference
                if t=='OT' and len(ub)==27: continue # Don't bother with OT references if it's only a NT
                if t=='NT' and len(ub)==39: continue # Don't bother with NT references if it's only a OT
                if t=='DC' and len(ub)<=66: continue # Don't bother with DC references if it's too small
                svk = VerseReferences.simpleVerseKey( b, c, v )
                #print( svk, ob.getVerseDataList( reference ) )
                print( reference, svk.getShortText(), ub.getVerseText( svk ) )
# end of main

if __name__ == '__main__':
    main()
# end of UnboundBible.py