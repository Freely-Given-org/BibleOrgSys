#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# DrupalBible.py
#   Last modified: 2013-12-21 by RJH (also update ProgVersion below)
#
# Module handling Drupal Bible files
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
Module reading and loading Drupal Bible files.


http://drupalbible.org/node/47

http://drupalbible.mikelee.idv.tw/?q=node/27


e.g.,
    ...

Limitations:
    ...
"""

ProgName = "Drupal Bible format handler"
ProgVersion = "0.01"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os, struct
from gettext import gettext as _
import multiprocessing
from collections import OrderedDict

import Globals
from Bible import Bible, BibleBook


filenameEndingsToAccept = ('.BC',) # Must be UPPERCASE
#filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
#extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX', 'STY', 'LDS', 'SSF', 'VRS', 'ASC', 'CSS', 'ODT','DOC','TXT', 'JAR', ) # Must be UPPERCASE



def DrupalBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for Drupal Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one Drupal Bible is found,
        returns the loaded DrupalBible object.
    """
    if Globals.verbosityLevel > 2: print( "DrupalBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("DrupalBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("DrupalBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " DrupalBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            if somethingUpperExt in filenameEndingsToAccept:
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an DrupalBible project here in this given folder
    numFound = 0
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename.endswith( '.Drupal' ):
            if strictCheck or Globals.strictCheckingFlag:
                firstLine = Globals.peekIntoFile( thisFilename, givenFolderName )
                if not firstLine.startswith( "*Bible"):
                    if Globals.verbosityLevel > 2: print( "DrupalBible (unexpected) first line was '{}' in {}".format( firstLine, thisFilename ) )
                    continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "DrupalBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and autoLoad:
            uB = DrupalBible( givenFolderName, lastFilenameFound[:-4] ) # Remove the end of the actual filename ".Drupal"
            uB.load() # Load and process the file
            return uB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("DrupalBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if Globals.verbosityLevel > 3: print( "    DrupalBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
            if thisFilename.endswith( '.Drupal' ):
                if strictCheck or Globals.strictCheckingFlag:
                    firstLine = Globals.peekIntoFile( thisFilename, tryFolderName )
                    if not firstLine.startswith( "*Bible"):
                        if Globals.verbosityLevel > 2: print( "DrupalBible (unexpected) first line was '{}' in {}".format( firstLine, thisFilname ) ); halt
                        continue
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "DrupalBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            if Globals.debugFlag: assert( len(foundProjects) == 1 )
            uB = DrupalBible( foundProjects[0][0], foundProjects[0][1][:-9] ) # Remove the end of the actual filename "_utf8.txt"
            uB.load() # Load and process the file
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
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "Drupal Bible object"
        self.objectTypeString = "Drupal"

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'.Drupal' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("DrupalBible: File '{}' is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of DrupalBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )
        mainIndex = []

        def readRecord( recordNumber, thisFile ):
            """
            Uses mainIndex to read in the specified Drupal record.
            """
            assert( recordNumber < len(mainIndex) )
            dataOffset = mainIndex[recordNumber] # Offset from the beginning of the file
            thisFile.seek( dataOffset )
            recordLength = 99999 if recordNumber==len(mainIndex)-1 else (mainIndex[recordNumber+1] - dataOffset)
            print( "Reading {} bytes from record {} at offset {}".format( recordLength, recordNumber, dataOffset ) )
            binaryInfo = thisFile.read( recordLength )
            if recordNumber < len(mainIndex)-1: assert( len(binaryInfo) == recordLength )
            return binaryInfo
        # end of readRecord

        def getBinaryString( binary, numBytes ):
            """
            """
            if len(binary) < numBytes: halt # Too few bytes provided
            result = ''
            for j, value in enumerate( binary ):
                if j>=numBytes or value==0: break
                result += chr( value )
            return result
        # end of getBinaryString

        def getFileString( thisFile, numBytes ):
            """
            Used for reading the Drupal header information from the file.
            """
            return getBinaryString( thisFile.read( numBytes ), numBytes )
        # end of getFileString

        with open( self.sourceFilepath, 'rb' ) as myFile: # Automatically closes the file when done
            # Read the Drupal header info
            name = getFileString( myFile, 32 )
            binary4 = myFile.read( 4 )
            attributes, version = struct.unpack( ">hh", binary4 )
            binary12 = myFile.read( 12 )
            creationDate, lastModificationDate, lastBackupDate = struct.unpack( ">III", binary12 )
            binary12 = myFile.read( 12 )
            modificationNumber, appInfoID, sortInfoID = struct.unpack( ">III", binary12 )
            appType = getFileString( myFile, 4 )
            creator = getFileString( myFile, 4 )
            print( name, appType, creator )
            binary4 = myFile.read( 4 )
            uniqueIDseed = struct.unpack( ">I", binary4 )
            binary6 = myFile.read( 6 )
            nextRecordListID, numRecords = struct.unpack( ">IH", binary6 )
            print( "numRecords =", numRecords )
            for n in range( 0, numRecords ):
                binary8 = myFile.read( 8 )
                dataOffset, recordAttributes, id0, id1, id2 = struct.unpack( ">IBBBB", binary8 )
                #print( '', dataOffset, recordAttributes, id0, id1, id2 )
                mainIndex.append( dataOffset )

            # Now read the first record of actual Bible data which is the Bible header info
            binary = readRecord( 0, myFile )
            byteOffset = 0
            versionName = getBinaryString( binary, 16 ); byteOffset += 16
            versionInfo = getBinaryString( binary[byteOffset:], 128 ); byteOffset += 128
            separatorCharacter = getBinaryString( binary[byteOffset:], 1 ); byteOffset += 1
            print( repr(versionName), repr(versionInfo), repr(separatorCharacter) )
            versionAttribute, wordIndexIndex, numWordListRecords, numBooks = struct.unpack( ">BHHH",  binary[byteOffset:byteOffset+7] ); byteOffset += 7
            print( "versionAttribute =",versionAttribute )
            if versionAttribute & 1: print( " Copy protected!" ); halt
            if versionAttribute & 2: print( " Not byte shifted." )
            else: halt # What does byte shifted mean???
            if versionAttribute & 4: print( " Right-aligned!" ); halt
            print( "wordIndexIndex = ",wordIndexIndex, "numWordListRecords =",numWordListRecords, "numBooks =",numBooks )
            bookIndexMetadata = []
            for n in range(  0, numBooks ):
                bookNumber, bookRecordLocation, numBookRecords = struct.unpack( ">HHH",  binary[byteOffset:byteOffset+6] ); byteOffset += 6
                shortName = getBinaryString( binary[byteOffset:], 8 ); byteOffset += 8
                longName = getBinaryString( binary[byteOffset:], 32 ); byteOffset += 32
                print( '  BOOK:', n+1, shortName, longName, bookNumber, bookRecordLocation, numBookRecords )
                bookIndexMetadata.append( (shortName, longName, bookNumber, bookRecordLocation, numBookRecords) )
            assert( byteOffset == len(binary) )

            # Now read the word index info
            binary = readRecord( wordIndexIndex, myFile )
            byteOffset = 0
            totalIndicesCount, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
            print( "totalIndicesCount =",totalIndicesCount )
            wordIndexMetadata = []
            expectedWords = 0
            for n in range( 0, totalIndicesCount ):
                wordLength, numFixedLengthWords, compressedFlag, ignored = struct.unpack( ">HHBB",  binary[byteOffset:byteOffset+6] ); byteOffset += 6
                print( "wordLength =",wordLength, "numFixedLengthWords =",numFixedLengthWords, "compressedFlag =",compressedFlag )
                wordIndexMetadata.append( (wordLength, numFixedLengthWords, compressedFlag) )
                expectedWords += numFixedLengthWords
            assert( byteOffset == len(binary) )
            print( "expectedWords =", expectedWords )

            # Now read in the word lists
            binary = readRecord( wordIndexIndex+1, myFile )
            byteOffset = 0
            words = []
            for wordLength, numFixedLengthWords, compressedFlag in wordIndexMetadata:
                for n in range( 0, numFixedLengthWords ):
                    if not compressedFlag:
                        if len(binary)-byteOffset < wordLength: # Need to continue to the next record
                            binary += myFile.read( 256 )
                        word = getBinaryString( binary[byteOffset:], wordLength ); byteOffset += wordLength
                        #print( wordLength, repr(word) )
                        if word in ( "In", "the", "beginning", "God", "created" ):
                            print( word, len(words) )
                        words.append( word )
                    else: # it's a compressed word
                        #print( binary[byteOffset:byteOffset+32] )
                        #print( "Can't understand compressed words yet" )
                        #print( "NumWords", len(words) )
                        #print( words[:256] )
                        #print( wordLength, numFixedLengthWords, compressedFlag )
                        continue
                        word = ''
                        for m in range( 0, wordLength ):
                            print( binary[byteOffset:byteOffset+3] )
                            ix, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                            print( ix )
                            print( ' ', ix, words[ix] )
                            word += words[ix]
                        print( word )
            #print( 'xyz', byteOffset, len(binary) )
            #assert( byteOffset == len(binary) )
            numWords = len(words)
            print( "numWords =", numWords )

            # Now read in the Bible book chapter/verse data
            #print( bookIndexMetadata )
            for shortName, longName, bookNumber, bookRecordLocation, numBookRecords in bookIndexMetadata:
                print( shortName, longName, "bookNumber =",bookNumber, "bookRecordLocation =",bookRecordLocation, "numBookRecords =",numBookRecords )
                #myFile.seek( mainIndex[bookRecordLocation] )
                #binary = myFile.read( 102400 )
                binary = readRecord( bookRecordLocation, myFile )
                byteOffset = 0
                #print( binary )
                numChapters, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                #print( numChapters )
                for c in range( 0, numChapters ):
                    accumulatedVerses, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                    #print( c+1, accumulatedVerses, "accumulatedVerses" )
                for c in range( 0, numChapters ):
                    accumulatedCharsPerChapter, = struct.unpack( ">I",  binary[byteOffset:byteOffset+4] ); byteOffset += 4
                    #print( c+1, accumulatedCharsPerChapter, "accumulatedCharsPerChapter" )
                for n in range( 0, accumulatedVerses ):
                    accumulatedCharsPerVerse, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                    #print( n+1, accumulatedCharsPerVerse, "accumulatedCharsPerVerse" )
                assert( byteOffset == len(binary) )

            # Now read in the Bible word data
            for shortName, longName, bookNumber, bookRecordLocation, numBookRecords in bookIndexMetadata:
                print( shortName, longName, "bookNumber =",bookNumber, "bookRecordLocation =",bookRecordLocation, "numBookRecords =",numBookRecords )
                #myFile.seek( mainIndex[bookRecordLocation] )
                #binary = myFile.read( 102400 )
                binary = readRecord( 435, myFile )
                byteOffset = 0
                print( len(binary), binary[:32] )
                for n in range( 0, 20 ):
                    #print( binary[n], words[binary[n]] )
                    ix, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                    #ix += 1
                    word = words[ix] if ix<len(words) else str(ix)+'/'+str(numWords)
                    print( ix, word )
                    if ix>expectedWords: print( "Too big" ); halt
                #print( words[:2000] )
                halt

                #print( binary[byteOffset-10:byteOffset+1] )
                #print( binary[byteOffset:byteOffset+20] )
                #display = 0
                #for n in range( 0, 5000 ):
                    ##ix, = struct.unpack( ">H",  binary[byteOffset:byteOffset+2] ); byteOffset += 2
                    #b1, b2, b3, = struct.unpack( ">BBB",  binary[byteOffset:byteOffset+3] ); byteOffset += 3
                    #ix = b1 * 65536 + b2 * 256 + b3
                    #word = str(ix)
                    #if ix<len(words): word = words[ix]
                    #if display or word=='In':
                        #print( ix, word )
                        #display += 1
                        #if display > 5: display = 0

                #halt

            halt
            if j>30: halt
        halt
    # end of DrupalBible.load
# end of DrupalBible class



def testYB( TUBfilename ):
    # Crudely demonstrate the Drupal Bible class
    import VerseReferences
    TUBfolder = "../../../../../Data/Work/Bibles/Drupal modules/" # Must be the same as below

    if Globals.verbosityLevel > 1: print( _("Demonstrating the Drupal Bible class...") )
    if Globals.verbosityLevel > 0: print( "  Test folder is '{}' '{}'".format( TUBfolder, TUBfilename ) )
    ub = DrupalBible( TUBfolder, TUBfilename )
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
        shortText = svk.getShortText()
        try:
            verseText = ub.getVerseText( svk )
        except KeyError:
            verseText = "Verse not available!"
        if Globals.verbosityLevel > 1: print( reference, shortText, verseText )
# end of testYB


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )


    testFolder = "../../../../../Data/Work/Bibles/PalmBiblePlus/"


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = DrupalBibleFileCheck( testFolder )
        if Globals.verbosityLevel > 1: print( "Drupal TestA1", result1 )
        result2 = DrupalBibleFileCheck( testFolder, autoLoad=True )
        if Globals.verbosityLevel > 1: print( "Drupal TestA2", result2 )
        #testSubfolder = os.path.join( testFolder, 'kjv/' )
        #result3 = DrupalBibleFileCheck( testSubfolder )
        #if Globals.verbosityLevel > 1: print( "Drupal TestB1", result3 )
        #result4 = DrupalBibleFileCheck( testSubfolder, autoLoad=True )
        #if Globals.verbosityLevel > 1: print( "Drupal TestB2", result4 )


    if 1: # specified modules
        single = ( "kjv", )
        good = ( "kjv", "kjv-red", "in-tsi", )
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: single, good, nonEnglish, bad
            if Globals.verbosityLevel > 1: print( "\nDrupal C{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testYB( testFilename )


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
                results = pool.map( testYB, parameters ) # have the pool do our loads
                assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if Globals.verbosityLevel > 1: print( "\nDrupal D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testYB( someFolder )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of DrupalBible.py