#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# OpenSongXMLBible.py
#   Last modified: 2013-12-18 by RJH (also update ProgVersion below)
#
# Module handling OpenSong XML Bibles
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
Module reading and loading OpenSong XML Bibles:
    <?xml version="1.0" encoding="ISO-8859-1"?>
    <bible>
    <b n="Genesis">
    <c n="1">
    <v n="1">In the beginning God created the heaven and the earth.</v>
    <v n="2">And the earth was without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.</v>
"""

ProgName = "OpenSong XML Bible format handler"
ProgVersion = "0.25"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os
from gettext import gettext as _
from collections import OrderedDict
from xml.etree.ElementTree import ElementTree

import Globals
from BibleOrganizationalSystems import BibleOrganizationalSystem
from Bible import Bible, BibleBook


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'OSIS', 'USX', 'STY', 'LDS', 'SSF', 'VRS', 'ASC', 'CSS', 'ODT','DOC','TXT', 'JAR', ) # Must be UPPERCASE



def OpenSongXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for OpenSong XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one OpenSong Bible is found,
        returns the loaded OpenSongXMLBible object.
    """
    if Globals.verbosityLevel > 2: print( "OpenSongXMLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("OpenSongXMLBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("OpenSongXMLBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " OpenSongXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
    #print( 'ff', foundFiles )

    # See if there's an OpenSong project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or Globals.strictCheckingFlag:
            firstLines = Globals.peekIntoFile( thisFilename, givenFolderName, numLines=2 )
            if not firstLines or len(firstLines)<2: continue
            if not firstLines[0].startswith( '<?xml version="1.0"' ) \
            and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                if Globals.verbosityLevel > 2: print( "OSB (unexpected) first line was '{}' in {}".format( firstLines, thisFilename ) )
                continue
            if not firstLines[1].startswith( '<bible>' ):
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "OpenSongXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and autoLoad:
            ub = OpenSongXMLBible( givenFolderName, lastFilenameFound )
            ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and Globals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if Globals.verbosityLevel > 3: print( "    OpenSongXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
        #print( 'fsf', foundSubfiles )

        # See if there's an OS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or Globals.strictCheckingFlag:
                firstLines = Globals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not firstLines[0].startswith( '<?xml version="1.0"' ) \
                and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                    if Globals.verbosityLevel > 2: print( "OSB (unexpected) first line was '{}' in {}".format( firstLines, thisFilename ) )
                    continue
                if not firstLines[1].startswith( '<bible>' ):
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "OpenSongXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            if Globals.debugFlag: assert( len(foundProjects) == 1 )
            ub = OpenSongXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            ub.load() # Load and process the file
            return ub
        return numFound
# end of OpenSongXMLBibleFileCheck



class OpenSongXMLBible( Bible ):
    """
    Class for reading, validating, and converting OpenSong Bible XML.
    """
    treeTag = 'bible'
    bookTag = 'b'
    chapterTag = 'c'
    verseTag = 'v'


    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the XML Bible file converter object.
        """
        # Setup and initialise the base class first
        if Globals.debugFlag: print( "OpenSongXMLBible( {}, {}, {} )".format( sourceFolder, givenName, encoding ) )
        Bible.__init__( self )
        self.objectNameString = "OpenSong XML Bible object"
        self.objectTypeString = "OpenSong"

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName )

        self.tree = None # Will hold the XML data

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "OpenSongXMLBible: File '{}' is unreadable".format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of OpenSongXMLBible.__init__


    def load( self ):
        """
        Load a single source XML file and load book elements.
        """
        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )
        self.tree = ElementTree().parse( self.sourceFilepath )
        if Globals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        # Find the main (bible) container
        if self.tree.tag == OpenSongXMLBible.treeTag:
            location = "XML file"
            Globals.checkXMLNoText( self.tree, location, '4f6h' )
            Globals.checkXMLNoTail( self.tree, location, '1wk8' )

            name = shortName = None
            for attrib,value in self.tree.items():
                if attrib=="n":
                    name = value
                elif attrib=="sn":
                    shortName = value
                else: logging.warning( "Unprocessed '{}' attribute ({}) in main element".format( attrib, value ) )

            # Find the submain (book) containers
            for element in self.tree:
                if element.tag == OpenSongXMLBible.bookTag:
                    sublocation = "book in " + location
                    Globals.checkXMLNoText( element, sublocation, 'g3g5' )
                    Globals.checkXMLNoTail( element, sublocation, 'd3f6' )
                    self.__validateAndExtractBook( element )
                elif element.tag == 'OT':
                    pass
                elif element.tag == 'NT':
                    pass
                else: logging.error( "Expected to find '{}' but got '{}'".format( OpenSongXMLBible.bookTag, element.tag ) )
        else: logging.error( "Expected to load '{}' but got '{}'".format( OpenSongXMLBible.treeTag, self.tree.tag ) )
    # end of OpenSongXMLBible.load


    def __validateAndExtractBook( self, book ):
        """
        Check/validate and extract book data from the given XML book record
            finding chapter subelements.
        """

        if Globals.verbosityLevel > 3: print( _("Validating OpenSong XML book...") )

        # Process the div attributes first
        BBB = bookName = None
        for attrib,value in book.items():
            if attrib=="n":
                bookName = value
            else: logging.warning( "Unprocessed '{}' attribute ({}) in book element".format( attrib, value ) )
        if bookName:
            BBB = self.genericBOS.getBBB( bookName )
            if BBB:
                if Globals.verbosityLevel > 2: print( _("Validating {} {}...").format( BBB, bookName ) )
                thisBook = BibleBook( self.name, BBB )
                thisBook.objectNameString = "OpenSong XML Bible Book object"
                thisBook.objectTypeString = "OpenSong"
                #thisBook.sourceFilepath = self.sourceFilepath
                for element in book:
                    if element.tag == OpenSongXMLBible.chapterTag:
                        sublocation = "chapter in {}".format( BBB )
                        Globals.checkXMLNoText( element, sublocation, 'j3jd' )
                        Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                        self.__validateAndExtractChapter( BBB, thisBook, element )
                    else: logging.error( "Expected to find '{}' but got '{}'".format( OpenSongXMLBible.chapterTag, element.tag ) )
                if Globals.verbosityLevel > 2: print( "  Saving {} into results...".format( BBB ) )
                self.saveBook( thisBook )
            logging.error( _("OpenSong load doesn't recognize book name: '{}'").format( bookName ) )
        logging.error( _("OpenSong load can't find a book name") )
    # end of OpenSongXMLBible.__validateAndExtractBook


    def __validateAndExtractChapter( self, BBB, thisBook, chapter ):
        """
        Check/validate and extract chapter data from the given XML book record
            finding and saving chapter numbers and
            finding and saving verse elements.
        """

        if Globals.verbosityLevel > 3: print( _("Validating XML chapter...") )

        # Process the div attributes first
        chapterNumber = numVerses = None
        for attrib,value in chapter.items():
            if attrib=="n":
                chapterNumber = value
            elif attrib=="VERSES":
                numVerses = value
            else: logging.warning( "Unprocessed '{}' attribute ({}) in chapter element".format( attrib, value ) )
        if chapterNumber:
            #print( BBB, 'c', chapterNumber )
            chapterNumber = chapterNumber.replace( 'of Solomon ', '' ) # Fix a mistake in the Chinese_SU module
            thisBook.appendLine( 'c', chapterNumber )
        else: logging.error( "Missing 'n' attribute in chapter element for BBB".format( BBB ) )

        for element in chapter:
            if element.tag == OpenSongXMLBible.verseTag:
                sublocation = "verse in {} {}".format( BBB, chapterNumber )
                Globals.checkXMLNoTail( element, sublocation, 'l5ks' )
                Globals.checkXMLNoSubelements( element, sublocation, '5f7h' )
                verseNumber = toVerseNumber = None
                for attrib,value in element.items():
                    if attrib=="n":
                        verseNumber = value
                    elif attrib=="t":
                        toVerseNumber = value
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in verse element".format( attrib, value ) )
                if Globals.debugFlag: assert( verseNumber )
                #thisBook.appendLine( 'v', verseNumber )
                vText = element.text
                if not vText:
                    logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, verseNumber ) )
                if vText: # This is the main text of the verse (follows the verse milestone)
                    #print( "{} {}:{} '{}'".format( BBB, chapterNumber, verseNumber, vText ) )
                    if '\n' in vText: # This is how they represent poety
                        #print( "vText", repr(vText), repr(element.text) )
                        for j, textBit in enumerate( vText.split( '\n' ) ):
                            if j==0:
                                thisBook.appendLine( 'q1', '' )
                                thisBook.appendLine( 'v', verseNumber + ' ' + textBit )
                            else: thisBook.appendLine( 'q1', textBit )
                    else: # Just one verse line
                        thisBook.appendLine( 'v', verseNumber + ' ' + vText )
            else: logging.error( "Expected to find '{}' but got '{}'".format( OpenSongXMLBible.verseTag, element.tag ) )
    # end of OpenSongXMLBible.__validateAndExtractChapter
# end of OpenSongXMLBible class


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    testFolder = "../../../../../Data/Work/Bibles//OpenSong Bibles/"
    single1 = ( "KJV.xmm", )
    single2 = ( "BIBLIA warszawska", )
    good = ( "KJV.xmm", "AMP.xmm", "Chinese_SU.xmm", "Contemporary English Version.xmm", "ESV", "MKJV", \
        "MSG.xmm", "NASB.xmm", "NIV", "NKJV.xmm", "NLT", "telugu.xmm", )
    nonEnglish = ( "BIBLIA warszawska", "Chinese Union Version Simplified.txt", "hun_karoli", "KNV_HU", "LBLA.xmm", \
        "Nowe Przymierze", "NVI.xmm", "NVI_PT", "PRT-IBS.xmm", "RV1960", "SVL.xmm", "UJPROT_HU", "vdc", \
        "Vietnamese Bible.xmm", )
    bad = ( "EPS99", )
    allOfThem = good + nonEnglish + bad


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        resultA1 = OpenSongXMLBibleFileCheck( testFolder )
        if Globals.verbosityLevel > 0: print( "TestA1", resultA1 )
        resultA2 = OpenSongXMLBibleFileCheck( testFolder, autoLoad=True )
        if Globals.verbosityLevel > 0: print( "TestA2", resultA2 )
        testSubfolder = os.path.join( testFolder, 'nrsv_update/' )
        resultB1 = OpenSongXMLBibleFileCheck( testSubfolder )
        if Globals.verbosityLevel > 0: print( "TestB1", resultB1 )
        resultB2 = OpenSongXMLBibleFileCheck( testSubfolder, autoLoad=True )
        if Globals.verbosityLevel > 0: print( "TestB2", resultB2 )


    if 1:
        for j, testFilename in enumerate( allOfThem ):
            if Globals.verbosityLevel > 0: print( "\n\nOpnSng B{}/ {}".format( j+1, testFilename ) )
            testFilepath = os.path.join( testFolder, testFilename )

            # Demonstrate the OpenSong XML Bible class
            if Globals.verbosityLevel > 1: print( "Demonstrating the OpenSong XML Bible class..." )
            if Globals.verbosityLevel > 0: print( "  Test filepath is '{}'".format( testFilepath ) )
            xb = OpenSongXMLBible( testFolder, testFilename )
            xb.load() # Load and process the XML
            if Globals.verbosityLevel > 0: print( xb ) # Just print a summary
            #print( xb.books['JDE']._processedLines )
            if 1: # Test verse lookup
                import VerseReferences
                for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                    ('OT','DAN','1','21'),
                                    ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                    ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                    (t, b, c, v) = reference
                    if t=='OT' and len(xb)==27: continue # Don't bother with OT references if it's only a NT
                    if t=='NT' and len(xb)==39: continue # Don't bother with NT references if it's only a OT
                    if t=='DC' and len(xb)<=66: continue # Don't bother with DC references if it's too small
                    svk = VerseReferences.SimpleVerseKey( b, c, v )
                    #print( svk, ob.getVerseDataList( reference ) )
                    if Globals.verbosityLevel > 1: print( reference, svk.getShortText(), xb.getVerseText( svk ) )
            if Globals.debugFlag and not xb: halt # if no books
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of OpenSongXMLBible.py