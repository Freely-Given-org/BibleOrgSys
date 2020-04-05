#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CSVBible.py
#
# Module handling comma-separated-values text Bible files
#
# Copyright (C) 2014-2019 Robert Hunt
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
Module reading and loading comma-separated-values text Bible files.

e.g.,
    "Book","Chapter","Verse","Scripture"
    "1","1","1","Cuando Dios, en el principio, creó* los cielos y la tierra,"
    "1","1","2","la tierra era una masa caótica* y las tinieblas cubrían el abismo, mientras un viento impetuoso sacudía la superficie de las aguas."
    "1","1","3","Entonces dijo Dios: — ¡Que exista la luz! Y la luz existió."
    …
    "66","22","19","Si suprime algo del mensaje profético del libro, Dios lo desgajará del árbol de la vida y lo excluirá de la ciudad santa descritos en este libro."
    "66","22","20","El que da fe de todo esto proclama: — Sí, estoy a punto de llegar. ¡Amén! ¡Ven, Señor Jesús!"
    "66","22","21","Que la gracia de Jesús, el Señor, esté con todos. Amén."
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "CSVBible"
PROGRAM_NAME = "CSV Bible format handler"
PROGRAM_VERSION = '0.32'
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


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX',
                      'STY', 'LDS', 'SSF', 'VRS', 'ASC', 'CSS', 'ODT','DOC', 'JAR', 'SAVE', 'SAV' ) # Must be UPPERCASE



def CSVBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for CSV Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one CSV Bible is found,
        returns the loaded CSVBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "CSVBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("CSVBibleFileCheck: Given {} folder is unreadable").format( repr(givenFolderName) ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("CSVBibleFileCheck: Given {} path is not a folder").format( repr(givenFolderName) ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " CSVBibleFileCheck: Looking for files in given {}".format( repr(givenFolderName) ) )
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

    # See if there's an CSV Bible here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename in ('book_names.txt','Readme.txt' ): looksHopeful = True
        elif thisFilename.endswith( '.txt' ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName )
                if firstLine is None: continue # seems we couldn't decode the file
                if not firstLine.startswith( '"Book","Chapter","Verse",' ) and not firstLine.startswith( '"1","1","1",') \
                and not firstLine.startswith( 'Book,Chapter,Verse,' ) and not firstLine.startswith( '1,1,1,'):
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "CSVBibleFileCheck: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                    continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "CSVBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = CSVBible( givenFolderName, lastFilenameFound[:-4] ) # Remove the end of the actual filename ".txt"
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
            logging.warning( _("CSVBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    CSVBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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

        # See if there's an CSV Bible here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if thisFilename.endswith( '.txt' ):
                if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                    firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName )
                    if firstLine is None: continue # seems we couldn't decode the file
                    if not firstLine.startswith( "Ge 1:1 " ):
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "CSVBibleFileCheck: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                        if debuggingThisModule: halt
                        continue
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "CSVBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            uB = CSVBible( foundProjects[0][0], foundProjects[0][1][:-4] ) # Remove the end of the actual filename ".txt"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of CSVBibleFileCheck



class CSVBible( Bible ):
    """
    Class for reading, validating, and converting CSVBible files.
    """
    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'CSV Bible object'
        self.objectTypeString = 'CSV'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+'.txt' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("CSVBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of CSVBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )

        lastLine, lineCount = '', 0
        BBB = None
        lastBookNumber = lastChapterNumber = lastVerseNumber = -1
        lastVText = ''
        quoted = None
        with open( self.sourceFilepath, encoding=self.encoding ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                #if lineCount==1 and self.encoding.lower()=='utf-8' and line[0]==chr(65279): #U+FEFF
                    #logging.info( "      CSVBible.load: Detected Unicode Byte Order Marker (BOM)" )
                    #line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                if line==' ': continue # Handle special case which has blanks on every second line -- HACK
                lastLine = line
                #print ( "CSV file line {} is {}".format( lineCount, repr(line) ) )
                if line[0]=='#': continue # Just discard comment lines
                if lineCount==1:
                    if line.startswith( '"Book",' ):
                        quoted = True
                        continue # Just discard header line
                    elif line.startswith( 'Book,' ):
                        quoted = False
                        continue # Just discard header line

                bits = line.split( ',', 3 )
                #print( lineCount, self.givenName, BBB, bits )
                if len(bits) == 4:
                    bString, chapterNumberString, verseNumberString, vText = bits
                    #print( "bString, chapterNumberString, verseNumberString, vText", bString, chapterNumberString, verseNumberString, vText )
                else:
                    logging.critical( "Unexpected number of bits {} {} {} {}:{} {!r} {} {}".format( self.givenName, BBB, bString, chapterNumberString, verseNumberString, vText, len(bits), bits ) )

                # Remove quote marks from these strings
                if quoted:
                    if len(bString)>=2 and bString[0]==bString[-1] and bString[0] in '"\'': bString = bString[1:-1]
                    if len(chapterNumberString)>=2 and chapterNumberString[0]==chapterNumberString[-1] and chapterNumberString[0] in '"\'': chapterNumberString = chapterNumberString[1:-1]
                    if len(verseNumberString)>=2 and verseNumberString[0]==verseNumberString[-1] and verseNumberString[0] in '"\'': verseNumberString = verseNumberString[1:-1]
                    if len(vText)>=2 and vText[0]==vText[-1] and vText[0] in '"\'': vText = vText[1:-1]
                    #print( "bString, chapterNumberString, verseNumberString, vText", bString, chapterNumberString, verseNumberString, vText )

                #if not bookCode and not chapterNumberString and not verseNumberString:
                    #print( "Skipping empty line in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    #continue
                #if BibleOrgSysGlobals.debugFlag: assert 2  <= len(bookCode) <= 4
                #if BibleOrgSysGlobals.debugFlag: assert chapterNumberString.isdigit()
                #if BibleOrgSysGlobals.debugFlag: assert verseNumberString.isdigit()
                bookNumber = int( bString )
                chapterNumber = int( chapterNumberString )
                verseNumber = int( verseNumberString )

                if bookNumber != lastBookNumber: # We've started a new book
                    if lastBookNumber != -1: # Better save the last book
                        self.stashBook( thisBook )
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bookNumber )  # Try to guess
                    assert BBB
                    thisBook = BibleBook( self, BBB )
                    thisBook.objectNameString = 'CSV Bible Book object'
                    thisBook.objectTypeString = 'CSV'
                    lastBookNumber = bookNumber
                    lastChapterNumber = lastVerseNumber = -1

                if chapterNumber != lastChapterNumber: # We've started a new chapter
                    if BibleOrgSysGlobals.debugFlag: assert chapterNumber > lastChapterNumber or BBB=='ESG' # Esther Greek might be an exception
                    if chapterNumber == 0:
                        logging.info( "Have chapter zero in {} {} {} {}:{}".format( self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                    thisBook.addLine( 'c', chapterNumberString )
                    lastChapterNumber = chapterNumber
                    lastVerseNumber = -1

                # Now we have to convert any possible RTF codes to our internal codes
                vTextOriginal = vText
                # First do special characters
                vText = vText.replace( '\\ldblquote', '“' ).replace( '\\rdblquote', '”' ).replace( '\\lquote', '‘' ).replace( '\\rquote', '’' )
                vText = vText.replace( '\\emdash', '—' ).replace( '\\endash', '–' )
                # Now do Unicode characters
                while True: # Find patterns like \\'d3
                    match = re.search( r"\\'[0-9a-f][0-9a-f]", vText )
                    if not match: break
                    i = int( vText[match.start()+2:match.end()], 16 ) # Convert two hex characters to decimal
                    vText = vText[:match.start()] + chr( i ) + vText[match.end():]
                while True: # Find patterns like \\u253?
                    match = re.search( r"\\u[1-2][0-9][0-9]\?", vText )
                    if not match: break
                    i = int( vText[match.start()+2:match.end()-1] ) # Convert three digits to decimal
                    vText = vText[:match.start()] + chr( i ) + vText[match.end():]
                #if vText != vTextOriginal: print( repr(vTextOriginal) ); print( repr(vText) )

                ## Handle special formatting
                ##   [brackets] are for Italicized words
                ##   <brackets> are for the Words of Christ in Red
                ##   «brackets»  are for the Titles in the Book  of Psalms.
                #vText = vText.replace( '[', '\\add ' ).replace( ']', '\\add*' ) \
                    #.replace( '<', '\\wj ' ).replace( '>', '\\wj*' )
                #if vText and vText[0]=='«':
                    #assert BBB=='PSA' and verseNumberString=='1'
                    #vBits = vText[1:].split( '»' )
                    ##print( "vBits", vBits )
                    #thisBook.addLine( 'd', vBits[0] ) # Psalm title
                    #vText = vBits[1].lstrip()

                # Handle the verse info
                if verseNumber==lastVerseNumber and vText==lastVText:
                    logging.warning( _("Ignored duplicate verse line in {} {} {} {}:{}").format( self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                    continue
                if BBB=='PSA' and verseNumberString=='1' and vText.startswith('&lt;') and self.givenName=='basic_english':
                    # Move Psalm titles to verse zero
                    verseNumber = 0
                if verseNumber < lastVerseNumber:
                    logging.warning( _("Ignored receding verse number (from {} to {}) in {} {} {} {}:{}").format( lastVerseNumber, verseNumber, self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                elif verseNumber == lastVerseNumber:
                    if vText == lastVText:
                        logging.warning( _("Ignored duplicated {} verse in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                    else:
                        logging.warning( _("Ignored duplicated {} verse number in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                thisBook.addLine( 'v', verseNumberString + ' ' + vText )
                lastVText = vText
                lastVerseNumber = verseNumber

        # Save the final book
        self.stashBook( thisBook )
        self.doPostLoadProcessing()
    # end of CSVBible.load
# end of CSVBible class



def testCSV( CSVfolder ):
    # Crudely demonstrate the CSV Bible class
    from BibleOrgSys.Reference import VerseReferences

    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the CSV Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r}".format( CSVfolder ) )
    vb = CSVBible( CSVfolder, "demo" )
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
# end of testCSV


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    testFolders =  ( BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest1/'),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest2/') )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for testFolder in testFolders:
            result1 = CSVBibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "CSV TestA1", result1 )

            result2 = CSVBibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "CSV TestA2", result2 )

            result3 = CSVBibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "CSV TestA3", result3 )
            #result3.loadMetadataFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )

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
                results = pool.map( testCSV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nCSV D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testCSV( someFolder )
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
# end of CSVBible.py
