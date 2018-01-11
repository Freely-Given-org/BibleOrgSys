#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# EasyWorshipBible.py
#
# Module handling EasyWorship Bible files
#
# Copyright (C) 2015-2018 Robert Hunt
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
Module reading and loading EasyWorship Bible undocumented binary files.

Filenames usually end with .ewb and contain some header info
    including a table of book abbreviations with numbers of chapters and verses
    followed by compressed blobs of basic book data (no headings, footnotes, etc.)
"""

from gettext import gettext as _

LastModifiedDate = '2018-01-11' # by RJH
ShortProgName = "EasyWorshipBible"
ProgName = "EasyWorship Bible format handler"
ProgVersion = '0.05'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os, struct
from binascii import hexlify
import multiprocessing

import BibleOrgSysGlobals
from Bible import Bible, BibleBook
from BibleOrganizationalSystems import BibleOrganizationalSystem



def EasyWorshipBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for EasyWorship Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one EasyWorship Bible is found,
        returns the loaded EasyWorshipBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "EasyWorshipBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("EasyWorshipBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("EasyWorshipBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " EasyWorshipBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    numFound = foundFileCount = 0
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something == '__MACOSX': continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            if somethingUpper.endswith( '.EWB' ):
                foundFiles.append( something )
                numFound += 1
    #if foundFileCount >= len(compulsoryFiles):
        #numFound = 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "EasyWorshipBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = EasyWorshipBible( givenFolderName, foundFiles[0] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("EasyWorshipBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    EasyWorshipBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                if somethingUpper.endswith( '.EWB' ):
                    foundProjects.append( (tryFolderName,something) )
                    numFound += 1
        #if foundFileCount >= len(compulsoryFiles):
            #foundProjects.append( tryFolderName )
            #numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "EasyWorshipBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            oB = EasyWorshipBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
# end of EasyWorshipBibleFileCheck


BOS = None


class EasyWorshipBible( Bible ):
    """
    Class for reading, validating, and converting EasyWorshipBible files.

    KJV OT has 23,145 verses = 5A69 in 39 = 27 books
        NT has  7,957 verses = 1F15 in 27 = 1B books
        Total  31,102 verses = 797E in 66 = 42 books
    """
    def __init__( self, sourceFolder, sourceFilename, encoding=None ):
        """
        Constructor: just sets up the Bible object.

        encoding is irrelevant because it's a binary format.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'EasyWorship Bible object'
        self.objectTypeString = 'EWB'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, sourceFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("EasyWorshipBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        global BOS
        if BOS is None: BOS = BibleOrganizationalSystem( 'GENERIC-KJV-66-ENG' )

        self.abbreviation = self.sourceFilename[:-4] # Remove file extension
    # end of EasyWorshipBible.__init__


    def load( self ):
        """
        Load the compressed data file and import book elements.
        """
        import zlib
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("\nLoading {}…").format( self.sourceFilepath ) )
        with open( self.sourceFilepath, 'rb' ) as myFile: # Automatically closes the file when done
            fileBytes = myFile.read()
        if BibleOrgSysGlobals.debugFlag: print( "  {:,} bytes read".format( len(fileBytes) ) )

        keep = {}
        index = 0
        #print( 'block1', hexlify( fileBytes[index:index+32] ), fileBytes[index:index+32] )
        keep['block1'] = fileBytes[index:index+32]
        hString = ''
        for j in range( 0, 32 ):
            char8 = fileBytes[index+j]
            #print( char8, repr(char8) )
            if char8 < 0x20: break
            hString += chr( char8 )
        if BibleOrgSysGlobals.debugFlag: print( 'block1b', hexlify( fileBytes[index+j:index+32] ) )
        # Skipped some (important?) binary here
        index += 32
        if BibleOrgSysGlobals.debugFlag: print( 'hString', repr(hString), index )
        if BibleOrgSysGlobals.strictCheckingFlag: assert hString == 'EasyWorship Bible Text'

        #print( 'block2', hexlify( fileBytes[index:index+56] ), fileBytes[index:index+56] )
        keep['block2'] = fileBytes[index:index+56]
        nString = ''
        for j in range( 0, 32 ):
            char8 = fileBytes[index+j]
            #print( char8, repr(char8) )
            if char8 < 0x20: break
            nString += chr( char8 )
        # Skipped some zeroes here
        index += 56
        if BibleOrgSysGlobals.debugFlag: print( 'nString', repr(nString), index )
        self.name = nString

        rawBooks = []
        for b in range( 1, 66+1 ):
            bookAbbrev = ''
            for j in range( 0, 32 ):
                char8 = fileBytes[index+j]
                #print( char8, repr(char8) )
                if char8 < 0x20: break
                bookAbbrev += chr( char8 )
            # Skipped some zeroes here
            index += 51
            if bookAbbrev and bookAbbrev[-1] == '.': bookAbbrev = bookAbbrev[:-1] # Remove final period
            if BibleOrgSysGlobals.verbosityLevel > 2: print( 'bookAbbrev', repr(bookAbbrev) )
            numChapters = fileBytes[index]
            numVerses = []
            for j in range( 0, numChapters ):
                numVerses.append( fileBytes[index+j+1] )
            # Skipped some zeroes here
            index += 157
            if BibleOrgSysGlobals.debugFlag:
                print( ' ', numChapters, numVerses )
            bookStart, = struct.unpack( "<I", fileBytes[index:index+4] )
            # Skipped some zeroes here
            index += 8
            if BibleOrgSysGlobals.debugFlag:
                print( '  bookStart', bookStart )
            bookLength, = struct.unpack( "<I", fileBytes[index:index+4] )
            # Skipped some zeroes here
            index += 8
            if BibleOrgSysGlobals.debugFlag:
                print( '  bookLength', bookLength, bookStart+bookLength )
            bookBytes = fileBytes[bookStart:bookStart+bookLength]
            assert bookBytes[0]==0x78 and bookBytes[1]==0xda # Zlib compression header
            rawBooks.append( (bookAbbrev, numChapters, numVerses, bookStart, bookLength, bookBytes) )

        if BibleOrgSysGlobals.debugFlag: print( 'unknown block3', index, hexlify( fileBytes[index:index+30] ) )
        keep['block3'] = fileBytes[index:index+30]
        length3, = struct.unpack( "<I", fileBytes[index:index+4] )
        if length3:
            block3 = fileBytes[index+4:index+4+length3-4]
            byteResult = zlib.decompress( block3 )
            textResult = byteResult.decode( 'utf8' )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "Got", len(textResult), textResult, 'from', length3 )
            keep['block3n'] = textResult
            if self.name: print( 'Overwriting module name {!r} with {!r}'.format( self.name, textResult ) )
            self.name = textResult
        index += length3
        if BibleOrgSysGlobals.debugFlag: print( 'end of contents', index, hexlify( fileBytes[index:index+60] ) )
        keep['block4'] = rawBooks[0][3]

        block5 = fileBytes[index:rawBooks[0][3]]
        keep['block5'] = block5
        index += len( block5 )
        #if self.abbreviation in ( 'TB', ): # Why don't the others work
        assert index == rawBooks[0][3] # Should now be at the start of the first book (already fetched above)

        assert len(rawBooks) == 66
        # Look at extra stuff at end
        endBytes = fileBytes[bookStart+bookLength:]
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'endBytes', len(endBytes), hexlify(endBytes), endBytes )
        assert len(endBytes) == 16
        keep['block9'] = endBytes
        # Skipped some binary and some text here
        del fileBytes

        # Now we have to decode the book text (compressed about 4x with zlib)
        for j, BBB in enumerate( BOS.getBookList() ):
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  Decoding {}…'.format( BBB ) )
            bookAbbrev, numChapters, numVerses, bookStart, bookLength, bookBytes = rawBooks[j]
            byteResult = zlib.decompress( bookBytes )
            textResult = byteResult.decode( 'utf8' )
            if '\t' in textResult:
                logging.warning( "Replacing tab characters in {} = {}".format( BBB, bookAbbrev ) )
                textResult = textResult.replace( '\t', ' ' )
            #print( textResult )
            if BibleOrgSysGlobals.strictCheckingFlag: assert '  ' not in textResult

            thisBook = BibleBook( self, BBB )
            thisBook.objectNameString = 'EasyWorship Bible Book object'
            thisBook.objectTypeString = 'EasyWorship Bible'
            if bookAbbrev: thisBook.addLine( 'toc3', bookAbbrev )

            C, V = '0', '-1' # So first/id line starts at 0:0
            for line in textResult.split( '\r\n' ):
                if not line: continue # skip blank lines
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( 'Processing {} {} line: {!r}'.format( self.abbreviation, BBB, line ) )
                assert line[0].isdigit()
                assert ':' in line[:4]
                CV,verseText = line.split( ' ', 1 )
                newC,newV = CV.split( ':' )
                #print( newC, V, repr(verseText) )
                if newC != C:
                    if self.abbreviation=='hcsb' and BBB in ('SA2',): # Handle a bad bug -- chapter 24 has verses out of order
                        print( "Skipping error for out-of-order chapters in {}!".format( BBB ) )
                    else: assert int(newC) > int(C)
                    C, V = newC, '0'
                    thisBook.addLine( 'c', C )
                if self.abbreviation=='TB' and BBB=='JOL': # Handle a bug -- chapter 3 repeats
                    if int(newV) < int(V): break
                elif self.abbreviation=='rsv' and BBB in ('EXO','HAG',): # Handle a bug -- chapter 22 has verses out of order
                    print( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                elif self.abbreviation=='gnt' and BBB in ('ISA','ZEC','MRK',): # Handle a bug -- chapter 38 has verses out of order
                    print( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                elif self.abbreviation=='hcsb' and BBB in ('SA2',): # Handle a bug -- chapter 24 has verses out of order
                    print( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                elif self.abbreviation=='msg' and BBB in ('NUM','JDG','SA2','CH2','EZE','ACT',): # Handle a bug -- chapter 24 has verses out of order
                    print( "Skipping error for out-of-order verses in {} {}".format( self.abbreviation, BBB ) )
                else:
                    try: assert int(newV) > int(V)
                    except ValueError:
                        if BibleOrgSysGlobals.debugFlag:
                            print( "Something's not an integer around {} {}:{} {}".format( BBB, C, V, verseText ) )
                V = newV
                thisBook.addLine( 'v', V + ' ' + verseText )

            if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", BBB )
            self.stashBook( thisBook )

        self.doPostLoadProcessing()
        return keep
    # end of EasyWorshipBible.load
# end of EasyWorshipBible class



def testEWB( TEWBfilename ):
    # Crudely demonstrate the EasyWorship Bible class
    import VerseReferences
    #testFolder = 'Tests/DataFilesForTests/EasyWorshipBible/'
    testFolder = '../../../../../Data/Work/Bibles/EasyWorship Bibles/'

    #TEWBfolder = os.path.join( testFolder, TEWBfilename+'/' )
    TEWBfolder = testFolder
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the EasyWorship Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( TEWBfolder, TEWBfilename ) )
    ewb = EasyWorshipBible( TEWBfolder, TEWBfilename )
    keep = ewb.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( ewb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        ewb.check()
        #print( UsfmB.books['GEN']._processedLines[0:40] )
        ewbErrors = ewb.getErrors()
        # print( ewbErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##ewb.toDrupalBible()
        ewb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(ewb)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(ewb)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(ewb)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #print( svk, ewb.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = ewb.getVerseText( svk )
            fullVerseText = ewb.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( reference, shortText, verseText )
            if BibleOrgSysGlobals.debugFlag: print( '  {}'.format( fullVerseText ) )
    return keep
# end of testEWB


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )


    #testFolder = 'Tests/DataFilesForTests/EasyWorshipBible/'
    testFolder = '../../../../../Data/Work/Bibles/EasyWorship Bibles/'


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = EasyWorshipBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestA1", result1 )
        result2 = EasyWorshipBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestA2", result2 )
        result3 = EasyWorshipBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestA3", result3 )

        #testSubfolder = os.path.join( testFolder, 'AV/' )
        #result3 = EasyWorshipBibleFileCheck( testSubfolder )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestB1", result3 )
        #result4 = EasyWorshipBibleFileCheck( testSubfolder, autoLoad=True )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestB2", result4 )
        #result5 = EasyWorshipBibleFileCheck( testSubfolder, autoLoadBooks=True )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "EasyWorship TestB3", result5 )


    if 0: # specified module
        singleModule = 'MBTV.ewb'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nEasyWorship C/ Trying {}".format( singleModule ) )
        #myTestFolder = os.path.join( testFolder, singleModule+'/' )
        #testFilepath = os.path.join( testFolder, singleModule+'/', singleModule+'_utf8.txt' )
        testEWB( singleModule )

    if 1: # specified modules
        keepDict = {}
        good = ( 'amp.ewb','darby.ewb', 'esv.ewb','esv.ewb_0','esv.ewb_2',
                'gnt.ewb','kjv.ewb','maori.ewb',
                'MBTV.ewb', 'msg.ewb','nasb.ewb','niv.ewb','nkjv.ewb','TB.ewb','ylt.ewb',)
        nonEnglish = (  )
        bad = ( 'aa.ewb','hcsb.ewb','rsv.ewb' )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nEasyWorship D{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            keepDict[testFilename] = testEWB( testFilename )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            for part in ('block1','block2','block3','block3n','block4','block5','block9'):
                print()
                for fn,stuff in sorted( keepDict.items() ):
                    if part in stuff:
                        if part == 'block3': print( part, len(stuff[part]), stuff[part][0], hexlify(stuff[part]), fn, )
                        elif part == 'block3n': print( part, len(stuff[part]), stuff[part], fn )
                        elif part == 'block4': print( part, stuff[part], fn )
                        else: print( part, len(stuff[part]), hexlify(stuff[part]), stuff[part], fn, )


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
                results = pool.map( testEWB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nEasyWorship E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testEWB( someFolder )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of EasyWorshipBible.py
