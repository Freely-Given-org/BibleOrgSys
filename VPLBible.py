#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# VPLBible.py
#
# Module handling verse-per-line text Bible files
#
# Copyright (C) 2014-2015 Robert Hunt
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

e.g.,
    Ge 1:1 En el principio creó Dios el cielo y la tierra.
    Ge 1:2 Y la tierra estaba desordenada y vacía, y las tinieblas [estaban] sobre la faz del abismo, y el Espíritu de Dios se movía sobre la faz de las aguas.
    Ge 1:3 Y dijo Dios: Sea la luz; y fue la luz.
    ...
    Re 22:19 Y si alguno quitare de las palabras del libro de esta profecía, Dios quitará su parte del libro de la vida, y de la santa ciudad, y de las cosas que están escritas en este libro.
    Re 22:20 El que da testimonio de estas cosas, dice: <Ciertamente vengo en breve.> Amén, así sea. Ven: Señor Jesús.
    Re 22:21 La gracia de nuestro Señor Jesucristo [sea] con todos vosotros. Amén.
"""

from gettext import gettext as _

LastModifiedDate = '2015-02-03' # by RJH
ShortProgName = "VPLBible"
ProgName = "VPL Bible format handler"
ProgVersion = '0.26'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os
import multiprocessing

import BibleOrgSysGlobals
from Bible import Bible, BibleBook


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX', 'STY', 'LDS', 'SSF', 'VRS', 'ASC', 'CSS', 'ODT','DOC', 'JAR', ) # Must be UPPERCASE


def t( messageString ):
    """
    Prepends the module name to a error or warning message string if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )
# end of t



def VPLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for VPL Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one VPL Bible is found,
        returns the loaded VPLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "VPLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if BibleOrgSysGlobals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if BibleOrgSysGlobals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("VPLBibleFileCheck: Given {} folder is unreadable").format( repr(givenFolderName) ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("VPLBibleFileCheck: Given {} path is not a folder").format( repr(givenFolderName) ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " VPLBibleFileCheck: Looking for files in given {}".format( repr(givenFolderName) ) )
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

    # See if there's an VPLBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename in ('book_names.txt','Readme.txt' ): looksHopeful = True
        elif thisFilename.endswith( '.txt' ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName )
                if firstLine is None: continue # seems we couldn't decode the file
                if not firstLine.startswith( "Ge 1:1 " ):
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "VPLBibleFileCheck: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                    continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "VPLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = VPLBible( givenFolderName, lastFilenameFound[:-4] ) # Remove the end of the actual filename ".txt"
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
            logging.warning( _("VPLBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    VPLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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

        # See if there's an VPLBible here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if thisFilename.endswith( '.txt' ):
                if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                    firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName )
                    if firstLine is None: continue # seems we couldn't decode the file
                    if not firstLine.startswith( "Ge 1:1 " ):
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "VPLBibleFileCheck: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                        if debuggingThisModule: halt
                        continue
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "VPLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert( len(foundProjects) == 1 )
            uB = VPLBible( foundProjects[0][0], foundProjects[0][1][:-4] ) # Remove the end of the actual filename ".txt"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of VPLBibleFileCheck



class VPLBible( Bible ):
    """
    Class for reading, validating, and converting VPLBible files.
    """
    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "VPL Bible object"
        self.objectTypeString = "VPL"

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'.txt' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("VPLBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of VPLBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )

        lastLine, lineCount = '', 0
        BBB = None
        lastBookCode = lastChapterNumber = lastVerseNumber = -1
        lastVText = ''
        with open( self.sourceFilepath, encoding=self.encoding ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                if lineCount==1 and self.encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF
                    logging.info( "      VPLBible.load: Detected UTF-16 Byte Order Marker" )
                    line = line[1:] # Remove the UTF-8 Byte Order Marker
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                #print ( 'VLP file line is "' + line + '"' )
                if line[0]=='#': continue # Just discard comment lines

                bits = line.split( ' ', 2 )
                #print( self.givenName, BBB, bits )
                if len(bits) == 3 and ':' in bits[1]:
                    bookCode, CVString, vText = bits
                    chapterNumberString, verseNumberString = CVString.split( ':' )
                else: print( "Unexpected number of bits", self.givenName, BBB, bookCode, chapterNumberString, verseNumberString, len(bits), bits )

                if not bookCode and not chapterNumberString and not verseNumberString:
                    print( "Skipping empty line in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    continue
                if BibleOrgSysGlobals.debugFlag: assert( 2  <= len(bookCode) <= 4 )
                if BibleOrgSysGlobals.debugFlag: assert( chapterNumberString.isdigit() )
                if not verseNumberString.isdigit():
                    logging.error( "Invalid verse number field at {}/{} {}:{!r}".format( bookCode, BBB, chapterNumberString, verseNumberString ) )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert( verseNumberString.isdigit() )
                    continue
                chapterNumber = int( chapterNumberString )
                verseNumber = int( verseNumberString )

                if bookCode != lastBookCode: # We've started a new book
                    if lastBookCode != -1: # Better save the last book
                        self.saveBook( thisBook )
                    #if bookCode in ('Ge',): BBB = 'GEN'
                    #elif bookCode in ('Le',): BBB = 'LEV'
                    ##elif bookCode in ('Jud',): BBB = 'JDG'
                    #elif bookCode in ('Es',): BBB = 'EST'
                    #elif bookCode in ('Pr',): BBB = 'PRO'
                    #elif bookCode in ('So',): BBB = 'SNG'
                    #elif bookCode in ('La',): BBB = 'LAM'
                    #elif bookCode in ('Jude',): BBB = 'JDE'
                    BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBB( bookCode )  # Try to guess
                    if BBB:
                        thisBook = BibleBook( self, BBB )
                        thisBook.objectNameString = "VPL Bible Book object"
                        thisBook.objectTypeString = "VPL"
                        lastBookCode = bookCode
                        lastChapterNumber = lastVerseNumber = -1
                    else:
                        logging.critical( "VPLBible could not figure out {!r} book code".format( bookCode ) )
                        if BibleOrgSysGlobals.debugFlag: halt

                if chapterNumber != lastChapterNumber: # We've started a new chapter
                    if BibleOrgSysGlobals.debugFlag: assert( chapterNumber > lastChapterNumber or BBB=='ESG' ) # Esther Greek might be an exception
                    if chapterNumber == 0:
                        logging.info( "Have chapter zero in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    thisBook.addLine( 'c', chapterNumberString )
                    lastChapterNumber = chapterNumber
                    lastVerseNumber = -1

                # Handle special formatting
                #   [brackets] are for Italicized words
                #   <brackets> are for the Words of Christ in Red
                #   «brackets»  are for the Titles in the Book  of Psalms.
                vText = vText.replace( '[', '\\add ' ).replace( ']', '\\add*' ) \
                    .replace( '<', '\\wj ' ).replace( '>', '\\wj*' )
                if vText and vText[0]=='«':
                    #print( "Oh!", BBB, chapterNumberString, verseNumberString, repr(vText) )
                    if BBB=='PSA' and verseNumberString=='1': # Psalm title
                        vBits = vText[1:].split( '»' )
                        #print( "vBits", vBits )
                        thisBook.addLine( 'd', vBits[0] ) # Psalm title
                        vText = vBits[1].lstrip()

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
                thisBook.addLine( 'v', verseNumberString + ' ' + vText )
                lastVText = vText
                lastVerseNumber = verseNumber

        # Save the final book
        self.saveBook( thisBook )
        self.doPostLoadProcessing()
    # end of VPLBible.load
# end of VPLBible class



def testVPL( VPLfolder ):
    # Crudely demonstrate the VPL Bible class
    import VerseReferences

    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the VPL Bible class...") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r}".format( VPLfolder ) )
    vb = VPLBible( VPLfolder, "demo" )
    vb.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( vb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        vb.check()
        #print( UsfmB.books['GEN']._processedLines[0:40] )
        vBErrors = vb.getErrors()
        # print( vBErrors )
    if BibleOrgSysGlobals.commandLineOptions.export:
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
# end of testVPL


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )


    testFolder = "Tests/DataFilesForTests/VPLTest1/"


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = VPLBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "VPL TestA1", result1 )

        result2 = VPLBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "VPL TestA2", result2 )
        result2.loadMetadataFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result2.check()
            #print( UsfmB.books['GEN']._processedLines[0:40] )
            vBErrors = result2.getErrors()
            # print( vBErrors )
        if BibleOrgSysGlobals.commandLineOptions.export:
            ##result2.toDrupalBible()
            result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testVPL, parameters ) # have the pool do our loads
                assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nVPL D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testVPL( someFolder )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of VPLBible.py