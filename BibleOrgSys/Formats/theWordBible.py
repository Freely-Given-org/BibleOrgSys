#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# theWordBible.py
#
# Module handling "theWord" Bible module files
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
Module reading and loading theWord Bible files.
These can be downloaded from: http://www.theword.net/index.php?downloads.modules

A theWord Bible module file has one verse per line (KJV versification)
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

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-05-12' # by RJH
SHORT_PROGRAM_NAME = "theWordBible"
PROGRAM_NAME = "theWord Bible format handler"
PROGRAM_VERSION = '0.55'
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
from BibleOrgSys.Internals.InternalBible import OT39_BOOKLIST, NT27_BOOKLIST
from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS
from BibleOrgSys.Reference.USFM3Markers import OFTEN_IGNORED_USFM_HEADER_MARKERS, removeUSFMCharacterField, replaceUSFMCharacterFields
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Bible import Bible, BibleBook


BOS = None

filenameEndingsToAccept = ('.OT','.NT','.ONT','.OTX','.NTX','.ONTX',) # Must be UPPERCASE


# These are the verses per book in the traditional KJV versification (but only for the 66 books)
#       (They must precede the Bible import)
theWordOTBookCount = 39
theWordOTBooks = OT39_BOOKLIST
assert len( theWordOTBooks ) == theWordOTBookCount
theWordOTTotalLines = 23145
theWordOTBookLines = ( 1533, 1213, 859, 1288, 959, 658, 618, 85, 810, 695, 816, 719, 942, 822, 280, 406, 167, 1070, 2461,
                        915, 222, 117, 1292, 1364, 154, 1273, 357, 197, 73, 146, 21, 48, 105, 47, 56, 53, 38, 211, 55 )
assert len( theWordOTBookLines ) == theWordOTBookCount
total=0
for count in theWordOTBookLines: total += count
assert total == theWordOTTotalLines

theWordNTBookCount = 27
theWordNTBooks = NT27_BOOKLIST
assert len( theWordNTBooks ) == theWordNTBookCount
theWordNTTotalLines = 7957
theWordNTBookLines = ( 1071, 678, 1151, 879, 1007, 433, 437, 257, 149, 155, 104, 95, 89, 47, 113, 83, 46, 25, 303, 108, 105, 61, 105, 13, 14, 25, 404 )
assert len( theWordNTBookLines ) == theWordNTBookCount
total=0
for count in theWordNTBookLines: total += count
assert total == theWordNTTotalLines

theWordBookCount = 66
theWordTotalLines = 31102
theWordBooks = theWordOTBooks + theWordNTBooks
assert len( theWordBooks ) == theWordBookCount
theWordBookLines = theWordOTBookLines + theWordNTBookLines
assert len( theWordBookLines ) == theWordBookCount
total=0
for count in theWordBookLines: total += count
assert total == theWordTotalLines


def theWordBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for theWord Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one theWord Bible is found,
        returns the loaded theWordBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "theWordBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("theWordBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("theWordBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " theWordBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
            #ignore = False
            #for ending in filenameEndingsToIgnore:
                #if somethingUpper.endswith( ending): ignore=True; break
            #if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
            if somethingUpperExt in filenameEndingsToAccept:
                foundFiles.append( something )

    # See if there's an theWordBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "theWordBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            twB = theWordBible( givenFolderName, lastFilenameFound )
            if autoLoadBooks: twB.load() # Load and process the file
            return twB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("theWordBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    theWordBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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

        # See if there's an tW project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "theWordBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            twB = theWordBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoadBooks: twB.load() # Load and process the file
            return twB
        return numFound
# end of theWordBibleFileCheck



def theWordGetBBBCV( lineNumber, volumeType='BOTH' ):
    """
    Given a line number (0… )
        return BBB, C, V 3-tuple.

    volumeType is 'OT', 'NT', or 'Both'.

    if lineNumber is beyond the verse lines, returns BBB='MDA' for metadata
    """
    assert 0 <= lineNumber < 32000
    assert volumeType in ('OT','NT','BOTH',)

    global BOS
    if BOS is None: BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

    if volumeType == 'OT':
        bookCount, books, totalLines, bookLines = theWordOTBookCount, theWordOTBooks, theWordOTTotalLines, theWordOTBookLines
    elif volumeType == 'NT':
        bookCount, books, totalLines, bookLines = theWordNTBookCount, theWordNTBooks, theWordNTTotalLines, theWordNTBookLines
    elif volumeType == 'BOTH':
        bookCount, books, totalLines, bookLines = theWordBookCount, theWordBooks, theWordTotalLines, theWordBookLines

    if lineNumber >= totalLines: return 'MDA', 0, lineNumber - totalLines

    # Find the book chapter and verse
    runningTotal = 0
    for BBB, lines in zip( books, bookLines ):
        if lineNumber < (runningTotal + lines): # we're in this book
            verseList = BOS.getNumVersesList( BBB )
            verseTotal = 0
            for j, verseCount in enumerate( verseList ):
                C = j + 1
                if lineNumber < (runningTotal + verseTotal + verseCount ):
                    return BBB, C, lineNumber - runningTotal - verseTotal + 1
                verseTotal += verseCount
            halt # programming error
        runningTotal += lines
# end of theWordGetBBBCV



def theWordFileCompare( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 ):
    """
    Compare the two files.
    """
    filepath1 = os.path.join( folder1, filename1 ) if folder1 else filename1
    filepath2 = os.path.join( folder2, filename2 ) if folder2 else filename2
    if BibleOrgSysGlobals.verbosityLevel > 1:
        if filename1==filename2:
            print( "Comparing {} files in folders {} and {}…".format( repr(filename1), repr(folder1), repr(folder2) ) )
        else: print( "Comparing files {} and {}…".format( repr(filename1), repr(filename2) ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        logging.error( "theWordFileCompare: File1 {!r} is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( "theWordFileCompare: File2 {!r} is unreadable".format( filepath2 ) )
        return None

    # Read the files
    lineCount, lines1 = 0, []
    with open( filepath1, 'rt', encoding='utf-8' ) as file1:
        for line in file1:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "      theWordFileCompare: Detected Unicode Byte Order Marker (BOM) in file1" )
                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            #if not line: continue # Just discard blank lines
            lines1.append( line )
    lineCount, lines2 = 0, []
    with open( filepath2, 'rt', encoding='utf-8' ) as file2:
        for line in file2:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "      theWordFileCompare: Detected Unicode Byte Order Marker (BOM) in file2" )
                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            #if not line: continue # Just discard blank lines
            line = line.replace( "ʼ", "'" ) # Change back to a straight apostrophe for comparison
            lines2.append( line )

    len1, len2 = len(lines1), len(lines2 )
    equalFlag = True
    if len1 != len2:
        if printFlag: print( "Count of lines differ: file1={}, file2={}".format( len1, len2 ) )
        equalFlag = False

    testament = 'BOTH'
    if filename1.lower().endswith( '.nt' ): testament = 'NT'
    elif filename1.lower().endswith( '.ot' ): testament = 'OT'
    diffCount = 0
    for k in range( min( len1, len2 ) ):
        if lines1[k] != lines2[k]:
            if printFlag:
                BBB, C, V = theWordGetBBBCV( k, testament )
                print( "  {} {}:{} {}:{} ({} chars)\n  {} {}:{} {}:{} ({} chars)" \
                        .format( BBB, C, V, k+1, repr(lines1[k]), len(lines1[k]), \
                                BBB, C, V, k+1, repr(lines2[k]), len(lines2[k]) ) )
            if printFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                for x in range( min( len(lines1[k]), len(lines2[k]) ) ):
                    if lines1[k][x] != lines2[k][x]:
                        print( "      Differ at position {} {!r} vs {!r}".format( x+1, lines1[k][x], lines2[k][x] ) )
                        break
            equalFlag = False
            diffCount += 1
            if diffCount > exitCount:
                if printFlag and BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "theWordfileCompare: stopped comparing after {} mismatches".format( exitCount ) )
                break

    return equalFlag
# end of theWordFileCompare


# These next three functions are used both by theWord and MySword exports
theWordIgnoredIntroMarkers = OFTEN_IGNORED_USFM_HEADER_MARKERS + (
    'imt1','imt2','imt3','imt4', 'imte1','imte2','imte3','imte4', 'is1','is2','is3','is4',
    'ip','ipi','im','imi','ipq','imq','ipr', 'iq1','iq2','iq3','iq4', 'ib', 'ili1','ili2','ili3','ili4',
    'iot','io1','io2','io3','io4', 'ir','iex','iqt', 'ie', )

def theWordHandleIntroduction( BBB, bookData, ourGlobals ):
    """
    Go through the book introduction (if any) and extract main titles for theWord export.

    Parameters are BBB (for error messages),
        the actual book data, and
        ourGlobals dictionary for persistent variables.

    Returns the information in a composed line string.
    """
    intC, intV = -1, 0
    composedLine = ''
    while True:
        #print( "theWordHandleIntroduction", BBB, intC, intV )
        try: result = bookData.getContextVerseData( (BBB,str(intC),str(intV),) ) # Currently this only gets one line
        except KeyError: break # Reached the end of the introduction
        verseData, context = result
        if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(verseData) == 1 # in the introductory section (each individual line is a "verse")
        marker, text = verseData[0].getMarker(), verseData[0].getFullText()
        if marker not in theWordIgnoredIntroMarkers and '¬' not in marker and marker not in BOS_ADDED_NESTING_MARKERS: # don't need end markers here either
            if marker in ('mt1','mte1'): composedLine += '<TS1>'+theWordAdjustLine(BBB,intC,intV,text)+'<Ts>'
            elif marker in ('mt2','mte2'): composedLine += '<TS2>'+theWordAdjustLine(BBB,intC,intV,text)+'<Ts>'
            elif marker in ('mt3','mte3'): composedLine += '<TS3>'+theWordAdjustLine(BBB,intC,intV,text)+'<Ts>'
            elif marker in ('mt4','mte4'): composedLine += '<TS3>'+theWordAdjustLine(BBB,intC,intV,text)+'<Ts>'
            elif marker=='ms1': composedLine += '<TS2>'+theWordAdjustLine(BBB,intC,intV,text)+'<Ts>'
            elif marker in ('ms2','ms3','ms4'): composedLine += '<TS3>'+theWordAdjustLine(BBB,intC,intV,text)+'<Ts>'
            elif marker=='mr': composedLine += '<TS3>'+theWordAdjustLine(BBB,intC,intV,text)+'<Ts>'
            else:
                logging.warning( "theWordHandleIntroduction: doesn't handle {} {!r} yet".format( BBB, marker ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "theWordHandleIntroduction: doesn't handle {} {!r} yet".format( BBB, marker ) )
                    halt
                ourGlobals['unhandledMarkers'].add( marker + ' (in intro)' )
        intV += 1 # Step to the next introductory section "verse"

    # Check what's left at the end
    if '\\' in composedLine:
        logging.warning( "theWordHandleIntroduction: Doesn't handle formatted line yet: {} {!r}".format( BBB, composedLine ) )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "theWordHandleIntroduction: Doesn't handle formatted line yet: {} {!r}".format( BBB, composedLine ) )
            halt
    return composedLine
# end of theWordHandleIntroduction


def theWordAdjustLine( BBB, C, V, originalLine ):
    """
    Handle pseudo-USFM markers within the line (cross-references, footnotes, and character formatting).

    Parameters are the Scripture reference (for error messsages)
        and the line (string) containing the backslash codes.

    Returns a string with the backslash codes replaced by theWord formatting codes.
    """
    line = originalLine # Keep a copy of the original line for error messages

    if '\\x' in line: # Remove cross-references completely (why???)
        #line = line.replace('\\x ','<RX>').replace('\\x*','<Rx>')
        line = removeUSFMCharacterField( 'x', line, closedFlag=True ).lstrip() # Remove superfluous spaces

    if '\\f' in line: # Handle footnotes
        for marker in ( 'fr', 'fm', ): # simply remove these whole field
            line = removeUSFMCharacterField( marker, line, closedFlag=None )
        for marker in ( 'fq', 'fqa', 'fl', 'fk', ): # italicise these ones
            while '\\'+marker+' ' in line:
                #print( BBB, C, V, marker, line.count('\\'+marker+' '), line )
                #print( "was", "'"+line+"'" )
                ix = line.find( '\\'+marker+' ' )
                assert ix != -1
                ixEnd = line.find( '\\', ix+len(marker)+2 )
                if ixEnd == -1: # no following marker so assume field stops at the end of the line
                    line = line.replace( '\\'+marker+' ', '<i>' ) + '</i>'
                elif line[ixEnd:].startswith( '\\'+marker+'*' ): # replace the end marker also
                    line = line.replace( '\\'+marker+' ', '<i>' ).replace( '\\'+marker+'*', '</i>' )
                else: # leave the next marker in place
                    line = line[:ixEnd].replace( '\\'+marker+' ', '<i>' ) + '</i>' + line[ixEnd:]
        for marker in ( 'ft', ): # simply remove these markers (but leave behind the text field)
            line = line.replace( '\\'+marker+' ', '' ).replace( '\\'+marker+'*', '' )
        #for caller in '+*abcdefghijklmnopqrstuvwxyz': line.replace('\\f '+caller+' ','<RF>') # Handle single-character callers
        line = re.sub( r'(\\f [a-z+*]{1,3} )', '<RF>', line ) # Handle one to three character callers
        line = line.replace('\\f ','<RF>').replace('\\f*','<Rf>') # Must be after the italicisation
        #if '\\f' in originalLine:
            #print( "o", originalLine )
            #print( "n", line )
            #halt

    if '\\' in line: # Handle character formatting fields
        line = removeUSFMCharacterField( 'fig', line, closedFlag=True ) # Remove figures
        line = removeUSFMCharacterField( 'str', line, closedFlag=True ) # Remove Strong's numbers
        line = removeUSFMCharacterField( 'sem', line, closedFlag=True ) # Remove semantic tagging
        replacements = (
            ( ('add',), '<FI>','<Fi>' ),
            ( ('qt',), '<FO>','<Fo>' ),
            ( ('wj',), '<FR>','<Fr>' ),
            ( ('va',), '(',')' ),
            ( ('bdit',), '<b><i>','</i></b>' ),
            ( ('bd','em','k','w'), '<b>','</b>' ),
            ( ('it','rq','bk','dc','qs','sig','sls','tl',), '<i>','</i>' ),
            ( ('nd','sc',), '<font size=-1>','</font>' ),
            ( ('pn','ord',), '','' ),
            )
        line = replaceUSFMCharacterFields( replacements, line ) # This function also handles USFM 2.4 nested character markers
        if '\\nd' not in originalLine and '\\+nd' not in originalLine:
            line = line.replace('LORD', '<font size=-1>LORD</font>')
            #line = line.replace('\\nd ','<font size=-1>',).replace('\\nd*','</font>').replace('\\+nd ','<font size=-1>',).replace('\\+nd*','</font>')
        #else:
            #line = line.replace('LORD', '<font size=-1>LORD</font>')
        #line = line.replace('\\add ','<FI>').replace('\\add*','<Fi>').replace('\\+add ','<FI>').replace('\\+add*','<Fi>')
        #line = line.replace('\\qt ','<FO>').replace('\\qt*','<Fo>').replace('\\+qt ','<FO>').replace('\\+qt*','<Fo>')
        #line = line.replace('\\wj ','<FR>').replace('\\wj*','<Fr>').replace('\\+wj ','<FR>').replace('\\+wj*','<Fr>')

    #if '\\' in line: # Output simple HTML tags (with no semantic info)
        #line = line.replace('\\bdit ','<b><i>').replace('\\bdit*','</i></b>').replace('\\+bdit ','<b><i>').replace('\\+bdit*','</i></b>')
        #for marker in ( 'it', 'rq', 'bk', 'dc', 'qs', 'sig', 'sls', 'tl', ): # All these markers are just italicised
            #line = line.replace('\\'+marker+' ','<i>').replace('\\'+marker+'*','</i>').replace('\\+'+marker+' ','<i>').replace('\\+'+marker+'*','</i>')
        #for marker in ( 'bd', 'em', 'k', ): # All these markers are just bolded
            #line = line.replace('\\'+marker+' ','<b>').replace('\\'+marker+'*','</b>').replace('\\+'+marker+' ','<b>').replace('\\+'+marker+'*','</b>')
        #line = line.replace('\\sc ','<font size=-1>',).replace('\\sc*','</font>').replace('\\+sc ','<font size=-1>',).replace('\\+sc*','</font>')

    # Check what's left at the end
    if '\\' in line:
        logging.warning( "theWordAdjustLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, line ) )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "theWordAdjustLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, line ) )
            halt
    return line
# end of theWordAdjustLine


def resettheWordMargins( ourGlobals, setKey=None ):
    """
    Reset all of our persistent margin variables.

    If a key name is given, just set that one to True.
    """
    #nonlocal ourGlobals
    #was = ourGlobals['pi1']
    ourGlobals['pi1'] = ourGlobals['pi2'] = ourGlobals['pi3'] = ourGlobals['pi4'] = ourGlobals['pi5'] = ourGlobals['pi6'] = ourGlobals['pi7'] = False
    ourGlobals['title'] = False # not sure yet if we need this one
    if setKey: ourGlobals[setKey] = True
    #if was and not ourGlobals['pi1']:
        #print( "Went off at", BBB, C, V, marker, text )
        #if BBB=='MAT' and C==4 and V==17: halt
# end of resettheWordMargins


def handleRTFLine( myName, BBB, C, V, originalLine, bookObject, myGlobals ):
    """
    Adjusts the formatting of the line for Bible reference BBB C:V
        and then writes it to the bookObject.

    Try to convert display formatting to semantic formatting as much as possible

    myGlobals dict contains flags.

    Appends pseudo-USFM results to the supplied bookObject.

    NOTE: There are no checks in here yet to discover nested character-formatting markers.  :-(
    """
    if BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            print( "theWordBible.handleRTFLine( {} {} {}:{} {} … {}".format( myName, BBB, C, V, repr(originalLine), myGlobals ) )
        if originalLine: assert '\n' not in originalLine and '\r' not in originalLine
    line = originalLine

    writtenV = False
    if V==1: appendedCFlag = False
    if C!=1 and V==1: bookObject.addLine( 'c', str(C) ); appendedCFlag = True

    if line is None: # We don't have an entry for this C:V
        return

    if line.startswith( '<CM>' ) and debuggingThisModule:
        print( "Why does theWord line start with <CM>?", myName, BBB, C, V, repr(originalLine) )

    # Fix apparent encoding errors in particular modules
    line = line.replace( ' >', '>' ) # fpr1933
    if line.endswith( '<CM' ): line += '>' # asv.ont
    if line.startswith( '>  ' ): line = line[3:] # pinyin.ont
    line = line.replace( '<TS><Ts>', '' ) # Fixes a module bug (has an empty field)
    line = line.replace( '<PF0><PF0>', '<PF0>' ) # 20cNT
    line = line.replace( '<PF0><PF1>', '<PF1>' ) # 20cNT
    line = line.replace( '<CM><CI>', '<CI>' ) # 20cNT
    line = line.replace( '<CI><CI>', '<CI>' ) # Tanakh1917.ot
    line = line.replace( '<CM><TS', '<TS' ) # 20cNT, gertextbibel
    line = line.replace( '(<12>) ', '' ).replace( '(<13>) ', '' ) # afr1953
    match = re.search( '<CT>(.+?)<CG> ', line ) # Lots found in alb
    if match:
        logging.warning( "Removed {} {} {}:{} unknown field {} from {}" \
            .format( myName, BBB, C, V, repr(line[match.start():match.end()]), repr(originalLine) ) )
        line = line[:match.start()] + line[match.end():]
    line = line.replace( ' <CLX>', '' ) # Undocumented what this means
    line = line.replace( '</<sup>>', '</sup>' ) # aleppo
    if line.endswith( '<CI><PI2>' ): line = line[:-5] # remove <PI2> from Tanakh1917
    line = line.replace( '<26-Ezekiel.21:3>', '' ) # Tanakh1917
    #if '\xa0' in line: print( myName, BBB, C, V, repr(originalLine) ); halt
    line = line.replace( '\xa0', ' ' ) # NBSpace? Not sure what this is (in aleppo and arm1967 and others?)
    if line.endswith( ' <CM>\t' ): line = line.replace( ' <CM>\t', '<CM>' ) # asv
    line = re.sub( '<V (\d{1,3}):(\d{1,3})>', '', line ) # cpdv for some verses
    line = re.sub( '<V P:(\d{1,2})>', '', line ) # cpdv for some prologue verses
    line = re.sub( '<RX (\d{1,2})\.(\d{1,3})\.(\d{1,3})>', '', line ) # dutsv
    #line = re.sub( '<RX (\d{1,2})\.(\d{1,3})\.(\d{1,2}) >', '', line ) # fpr1933
    line = re.sub( '<RX (\d{1,2})\.(\d{1,3})\.(\d{1,3})[+-\.](\d{1,3})>', '', line ) # dutsv, fpr1933
    #line = line.replace( '<BOOK THE FIRST> ', '' ) # ebr
    line = line.replace( ' /a>', '' ) # jfa-rc(pt)
    line = line.replace( '?>> A', '? A' ).replace( 'viu>.', 'viu.' ) # romorthodox
    line = re.sub( '<V1{>(.*?)<V1}>', r'\1', line ) # tr.nt
    line = re.sub( '<V2(.+?)>', '', line ) # remove variant 2 from tr.nt
    line = line.replace( '<CM> <CM> <TS>', '<TS>' ).replace( '<CM> <CM>', '<CM>' ) # web

    # Not sure what <A represents, but it's often at the beginning of a line and messes up other tests
    #   so lets remove them here
    line = re.sub( '<AX (.+?)>', '', line ) # fpr1933
    line = re.sub( '<A(\d{1,3}):(\d{1,2})>', '', line )
    line = re.sub( '<A (\d{1,3})\.(\d{1,2})>', '', line )
    #if '<A' in line:
        #print( "line3", repr(originalLine), '\n', repr(line) )
        #if BibleOrgSysGlobals.debugFlag: halt
    line = re.sub( '<22-Song of Songs\.(\d{1,2})\.(\d{1,2})>', '', line ) # Tanakh1917
    line = line.replace( '<z1>', '' ).replace( '<z2>', '' ) # footnote referent text in leb
    line = re.sub( '<AF(.)(.*?)>', '', line ) # sblgnt.nt seems to have alternatives immediately before the word
    line = re.sub( '<AU(.)>', '', line ) # sblgnt.nt seems to have this immediately after the word
    line = re.sub( '<a href=(.+?)>(.+?)</a>', '', line ) # slt.ont has these html links
    line = re.sub( '<sync type="(.+?)" value="(.+?)" />', '', line ) # spasev.ont has these links


    # Adjust paragraph formatting at the beginning of lines
    # Don't need to include a \p before a \q1 or whatever
    if line.startswith( '<PF0>' ):
        line = line.replace( '<PF0>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PF1><PI1>' ):
        line = line.replace( '<PF1><PI1>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PF1>' ):
        line = line.replace( '<PF1>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PI>' ):
        line = line.replace( '<PI>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PI1>' ):
        line = line.replace( '<PI1>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PI2>' ):
        line = line.replace( '<PI2>', '\\q2 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PI3>' ):
        line = line.replace( '<PI3>', '\\q3 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<CI>' ):
        myGlobals['haveParagraph'] = False
        if line.startswith( '<CI><PI2>' ):
            line = line.replace( '<CI><PI2>', '<CI><PI2>\\NL*', 1 ) # This will cause the first q to be followed by a v
    elif line.startswith( '<CL>' ):
        myGlobals['haveParagraph'] = False

    # Handle some special cases
    line = line.replace('<TS3><i>(','\\NL*\\r (').replace(')</i>',')') # The TS3 ending will be covered below

    # Adjust line formatting
    if C==1 and V==1 and originalLine and originalLine[0]=='<': # These are right at the beginning of the book
        line = line.replace('<TS>','\\NL*\\mt1 ').replace('<Ts>','\\NL*')
        line = line.replace('<TS1>','\\NL*\\mt1 ').replace('<Ts1>','\\NL*') # Start marker and then a newline at end
        line = line.replace('<TS2>','\\NL*\\mt2 ').replace('<Ts2>','\\NL*')
        line = line.replace('<TS3>','\\NL*\\mt3 ').replace('<Ts3>','\\NL*')
    else: # we'll assume that they're section headings
        if line.startswith( '<TS' ): myGlobals['haveParagraph'] = False # Don't need a paragraph marker before a section heading
        line = line.replace('<TS>','\\NL*\\s1 ').replace('<Ts>','\\NL*')
        line = line.replace('<TS1>','\\NL*\\s1 ').replace('<Ts1>','\\NL*') # Start marker and then a newline at end
        line = line.replace('<TS2>','\\NL*\\s2 ').replace('<Ts2>','\\NL*')
        line = line.replace('<TS3>','\\NL*\\s3 ').replace('<Ts3>','\\NL*')
    # Some (poor) modules end even the numbered TS fields with just <Ts>!!!

    # Adjust character formatting with USFM equivalents
    line = line.replace('<FI>','\\add ').replace('<Fi>','\\add*')
    line = line.replace('<FO>','\\qt ').replace('<Fo>','\\qt*')
    line = line.replace('<CI><FR><PF1><PI1>','\\NL*\\q1 \\wj ') # in 20cNT
    line = line.replace('<CI><FR><PF1>','\\NL*\\p \\wj ') # in 20cNT
    line = line.replace('<FR>','\\wj ').replace('<Fr>','\\wj*')
    line = line.replace('<FU>','\\ul ').replace('<Fu>','\\ul*') # Not USFM
    line = line.replace('<RF>','\\f \\ft ').replace('<Rf>','\\f*')
    line = line.replace('<RX>','\\x ').replace('<Rx>','\\x*')

    #Now the more complex ones that need regexs
    #line = line.replace('<RF q=*>','\\f * \\ft ').replace('<Rf>','\\f*')
    #if '<RF' in line:
        #print( "line1", repr(originalLine), '\n', repr(line) )
    line = re.sub( '<RF q=(.)>', r'\\f \1 \\ft ', line )
        #print( "line2", repr(originalLine), '\n', repr(line) )
    line = re.sub( '<WH(\d{1,4})>', '', line )
    line = line.replace( '<wh>','' )
    if '<WH' in line or '<wh' in line:
        print( "line4", repr(originalLine), '\n', repr(line) )
        #halt
    line = re.sub( '<l=(.+?)>', '', line )
    if '<l=' in line:
        print( "line5", repr(originalLine), '\n', repr(line) )
        #halt

    # Simple HTML tags (with no semantic info)
    line = line.replace('<b>','\\bd ').replace('</b>','\\bd*')
    line = line.replace('<i>','\\it ').replace('</i>','\\it*')
    line = line.replace('<u>','\\ul ').replace('</u>','\\ul*') # Not USFM
    line = line.replace( ' <BR> ', '\\NL*\\m ' ).replace( '<BR> ', '\\NL*\\m ' ).replace( '<BR>', '\\NL*\\m ' )
    line = line.replace( ' <br> ', '\\NL*\\m ' ).replace( '<br> ', '\\NL*\\m ' ).replace( '<br>', '\\NL*\\m ' )
    line = line.replace('<sup>','\\ord ').replace('</sup>','\\ord*') # Not proper USFM meaning
    line = re.sub('<font size=-1>(.+?)</font>', r'\\sc \1\\sc*', line ) # This causes nested markers in aleppo
    line = re.sub('<font size=\+1>(.+?)</font>', r'\\em \1\\em*', line )
    line = re.sub( '<font color=(.+?)>(.+?)</font>', r'\2', line )
    line = re.sub( '<font color=(.+?)>', '', line ).replace( '</font>','' ) # asv has <font color="850000"> with the closing on the next line
    line = re.sub( '<HEB>(.+?)<heb>', r'\\qac \1\\qac*', line ) # acrostic letter in asv
    line = re.sub( '<HEB>(.+?)<Heb>', r'\\nd \1\\nd*', line ) # divine name in rnkjv

    # Handle the paragraph at the end of the previous line
    if myGlobals['haveParagraph']: # from the end of the previous line
        bookObject.addLine( 'p', '' )
        myGlobals['haveParagraph'] = False

    # Adjust paragraph formatting at the end of lines
    line = line.replace( '<CM><CM>', '\\NL*\\b<CM>' ) # 20cNT
    assert not myGlobals['haveParagraph']
    if line.endswith( '<CM>' ): # Means start a new paragraph after this line
        line = line[:-4] # Remove the marker
        myGlobals['haveParagraph'] = 'CM'
    elif line.endswith( '<CI>' ): # Means start a new paragraph (without a space before it) after this line
        line = line[:-4] # Remove the marker
        myGlobals['haveParagraph'] = 'CI'
    elif line.endswith( '<CL>' ): # Means start on a new line
        line = line[:-4] # Remove the marker
        myGlobals['haveParagraph'] = 'CL'

    # Paragraph markers (not at the end of the line)
    #line = re.sub('<CI><PI(\d)>',r'\\NL*\\q\1 ',line).replace('<Ci>','')
    #line = re.sub('<CI><PF(\d)>',r'\\NL*\\q\1 ',line)
    line = line.replace( '<CI><PF0>','\\NL*\\p ' )
    line = line.replace( '<CI><PF1><PI1>','\\NL*\\q1 ' )
    line = line.replace( '<CI><PF1>','\\NL*\\p ' )
    line = line.replace( '<CI><PF2><PI2>', '\\NL*\\q2 ' )
    line = line.replace( '<CI><PF3><PI3>', '\\NL*\\q3 ' )
    line = line.replace( '<CI><PI>','\\NL*\\q1 ' )
    line = line.replace( '<CI><PI0>','\\NL*\\p ' )
    line = line.replace( '<CI><PI1>','\\NL*\\q1 ' )
    line = line.replace( '<CI><PI2>','\\NL*\\q2 ' ).replace('<Ci>','')
    line = line.replace( '<CI><PI3>','\\NL*\\q3 ' )
    line = line.replace( '<CI><PI4>','\\NL*\\q4 ' )
    #line = line.replace( '<CI><PI5>','\\NL*\\q4 ' )
    line = line.replace( '<CL><PI2>','\\NL*\\q2 ' )
    line = line.replace( '<CL>','\\NL*\\m ' )
    line = line.replace( '<CM><PI>','\\NL*\\q1 ' )
    line = line.replace( '<CM><PI5>','\\NL*\\q4 ' )
    line = line.replace( '<CM><PI6>','\\NL*\\q4 ' )
    line = line.replace( '<CM><PF1><PI1>', '\\NL*\\q1 ' )
    line = line.replace( '<CM><PF2><PI2>', '\\NL*\\q2 ' )
    line = line.replace( '<CM><PF3><PI3>', '\\NL*\\q3 ' )
    #line = line.replace( '<CM><PF4><PI4>', '\\NL*\\q4 ' )
    line = line.replace( '<CM><PF0>', '\\NL*\\m ' )
    line = line.replace( '<CM>', '\\NL*\\p ' )
    line = line.replace( '<PF0>','\\NL*\\p ')
    line = line.replace( '<PF1><PI1>','\\NL*\\q1 ' )
    line = line.replace( '<PI2>', '\\NL*\\q2 ' )

    line = line.replace( '<K>','').replace('<k>','')
    line = line.replace( '<R>','').replace('<r>','')
    line = line.replace( '<sub>','').replace('</sub>','')

    if myName == 'ebr': line = line.replace( '<', '\\em ' ).replace( '>', '\\em*' )

    # Check what's left at the end
    if ('<' in line or '>' in line) and myName not in ('ckjv-sc','ckjv-tc',):
        # NOTE: some modules can use these as speech marks so they might be part of the text!
        if '<WT' not in line and '<WG' not in line and '<WH' not in line:
            # Don't yet handle lines like this: βιβλος<WG976><WTN-NSF> γενεσεως<WG1078><WTN-GSF> ιησου<WG2424><WTN-GSM> χριστου<WG5547><WTN-GSM> υιου<WG5207><WTN-GSM> δαυιδ<WG1138><WTN-PRI> υιου<WG5207><WTN-GSM> αβρααμ<WG11><WTN-PRI>
            logging.error( "{} original line: {}".format( myName, repr(originalLine) ) )
            logging.error( "theWordBible.load: Doesn't handle {} {}:{} formatted line yet: {}".format( BBB, C, V, repr(line) ) )
            if 1: # Unhandled stuff -- not done properly yet……
                line = re.sub( '<(.+?)>', '', line ) # Remove all remaining sets of angle brackets
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt


    line = line.replace( '\\NL*\\NL*', '\\NL*' ) # Don't need double-ups
    if line.startswith( '\\NL*' ): line = line[4:] # Don't need nl at start of line
    if line.endswith( '\\p \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\q1 \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\q2 \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\q3 \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\q4 \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\NL*' ): line = line[:-4] # Don't need nl at end of line
    if '\\NL*' in line: # We need to break the original line into different USFM markers
        #print( "\nMessing with segments: {} {}:{} {!r}".format( BBB, C, V, line ) )
        segments = line.split( '\\NL*' )
        assert len(segments) >= 2
        #print( " segments (split by backslash):", segments )
        leftovers = ''
        for segment in segments:
            if segment and segment[0] == '\\':
                bits = segment.split( None, 1 )
                #print( " bits", bits )
                marker = bits[0][1:]
                if len(bits) == 1:
                    #if bits[0] in ('\\p','\\b'):
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                        if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
                        bookObject.addLine( marker, '' )
                    else:
                        logging.error( "It seems that we had a blank {!r} field in {!r}".format( bits[0], originalLine ) )
                        #halt
                else:
                    assert len(bits) == 2
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "\n{} {}:{} {!r}".format( BBB, C, V, originalLine ) )
                        print( "line", repr(line) )
                        print( "seg", repr(segment) )
                        print( "segments:", segments )
                        print( "bits", bits )
                        print( "marker", marker )
                        print( "leftovers", repr(leftovers) )
                        assert marker in ('mt1','mt2','mt3', 's1','s2','s3', 'q1','q2','q3', 'r')
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                        bookObject.addLine( marker, bits[1] )
                    elif not writtenV:
                        bookObject.addLine( 'v', '{} {}'.format( V, segment ) )
                        writtenV = True
                    else: leftovers += segment
            else: # What is segment is blank (\\NL* at end of line)???
                if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
                if not writtenV:
                    bookObject.addLine( 'v', '{} {}'.format( V, leftovers+segment ) )
                    writtenV = True
                else:
                    bookObject.addLine( 'v~', leftovers+segment )
                leftovers = ''
                #if myGlobals['haveParagraph']:
                    #bookObject.addLine( 'p', '' )
                    #myGlobals['haveParagraph'] = False
        if leftovers: logging.critical( "Had leftovers {}".format( repr(leftovers) ) )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert not leftovers
        #halt
    else: # no newlines in the middle
        if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
        bookObject.addLine( 'v', '{} {}'.format( V, line ) )
        #if myGlobals['haveParagraph']:
            #bookObject.addLine( 'p', '' )
            #myGlobals['haveParagraph'] = False
# end of theWordBible.handleRTFLine




class theWordBible( Bible ):
    """
    Class for reading, validating, and converting theWordBible files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'theWord Bible object'
        self.objectTypeString = 'theWord'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("theWordBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        filenameBits = os.path.splitext( self.sourceFilename )
        self.name = filenameBits[0]
        self.fileExtension = filenameBits[1]

        if self.fileExtension.upper().endswith('X'):
            logging.warning( _("theWordBible: File {!r} is encrypted").format( self.sourceFilepath ) )
    # end of theWordBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )

        global BOS
        if BOS is None: BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['theWord'] = {}

        fileExtensionUpper = self.fileExtension.upper()
        assert fileExtensionUpper in filenameEndingsToAccept
        if fileExtensionUpper.endswith('X'):
            logging.error( _("theWordBible: File {!r} is encrypted").format( self.sourceFilepath ) )
            return

        if fileExtensionUpper in ('.ONT','.ONTX',):
            testament, BBB = 'BOTH', 'GEN'
            booksExpected, textLineCountExpected = theWordBookCount, theWordTotalLines
        elif fileExtensionUpper in ('.OT','.OTX',):
            testament, BBB = 'OT', 'GEN'
            booksExpected, textLineCountExpected = theWordOTBookCount, theWordOTTotalLines
        elif fileExtensionUpper in ('.NT','.NTX',):
            testament, BBB = 'NT', 'MAT'
            booksExpected, textLineCountExpected = theWordNTBookCount, theWordOTTotalLines

        # Create the first book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'theWord Bible Book object'
        thisBook.objectTypeString = 'theWord'
        consecutiveBlankLineCount, hadText = 0, False

        verseList = BOS.getNumVersesList( BBB )
        numC, numV = len(verseList), verseList[0]
        C = V = 1

        lastLine, lineCount, bookCount = '', 0, 0
        ourGlobals = {}
        continued = ourGlobals['haveParagraph'] = False
        encodings = ['utf-8', 'ISO-8859-1', 'ISO-8859-15']
        encodings.remove( self.encoding ) # Remove the given encoding if included
        if self.encoding: encodings.insert( 0, self.encoding ) # Put the given encoding back in in the first position
        for encoding in encodings: # Start by trying the given encoding
            try:
                with open( self.sourceFilepath, 'rt', encoding=encoding ) as myFile: # Automatically closes the file when done
                    for sourceLine in myFile:
                        originalLine = sourceLine
                        lineCount += 1
                        if lineCount==1 and self.encoding.lower()=='utf-8' and originalLine[0]==chr(65279): #U+FEFF
                            logging.info( "      theWordBible.load: Detected Unicode Byte Order Marker (BOM)" )
                            originalLine = originalLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                        if originalLine and originalLine[-1]=='\n': originalLine=originalLine[:-1] # Removing trailing newline character
                        line = originalLine
                        #lastLine = line

                        if lineCount <= textLineCountExpected: # assume it's verse text
                            #print ( lineCount, BBB, C, V, 'tW file line is "' + line + '"' )
                            if line:
                                hadText = True
                                consecutiveBlankLineCount = 0
                            else:
                                if consecutiveBlankLineCount < 5:
                                    logging.warning( "theWordBible.load: Found blank verse line at {} {} {}:{}".format( lineCount, BBB, C, V ) )
                                elif consecutiveBlankLineCount == 5:
                                    logging.warning( 'theWordBible.load: Additional {} "Found blank verse line" messages suppressed…'.format( BBB ) )
                                consecutiveBlankLineCount += 1

                            handleRTFLine( self.name, BBB, C, V, line, thisBook, ourGlobals )
                            V += 1
                            if V > numV:
                                C += 1
                                if C > numC: # Save this book now
                                    if hadText:
                                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", BBB, bookCount+1 )
                                        self.stashBook( thisBook )
                                    else: logging.warning( "theWordBible.load: Didn't save {} because it was blank".format( BBB ) )

                                    bookCount += 1
                                    if bookCount >= booksExpected: break
                                    BBB = BOS.getNextBookCode( BBB )
                                    # Create the next book
                                    thisBook = BibleBook( self, BBB )
                                    thisBook.objectNameString = 'theWord Bible Book object'
                                    thisBook.objectTypeString = 'theWord'

                                    verseList = BOS.getNumVersesList( BBB )
                                    numC, numV = len(verseList), verseList[0]
                                    C = V = 1
                                    # Don't append c 1 yet, because there might be a book heading to precede it
                                    consecutiveBlankLineCount, hadText = 0, False
                                else: # next chapter only
                                    #thisBook.addLine( 'c', str(C) )
                                    numV = verseList[C-1]
                                    V = 1
                                #thisBook.addLine( 'cc', str(C) ) # All chapter numbers except the first

                            #if ourGlobals['haveParagraph']:
                                #thisBook.addLine( 'p', '' )
                                #ourGlobals['haveParagraph'] = False

                        else: # Should be module info at end of file (after all of the verse lines)
                            #print ( lineCount, 'tW file line is "' + line + '"' )
                            if not line: continue # Just discard additional blank lines
                            if line[0] == '#': continue # Just discard comment lines
                            if not continued:
                                if '=' not in line:
                                    logging.warning( "Missing equals sign from info line (ignored): {} {!r}".format( lineCount, line ) )
                                else: # Seems like a field=something type line
                                    bits = line.split( '=', 1 )
                                    assert len(bits) == 2
                                    fieldName = bits[0]
                                    fieldContents = bits[1]
                                    if line.endswith( '\\' ): continued = True
                                    else: self.suppliedMetadata['theWord'][fieldName] = fieldContents
                            else: # continued
                                fieldContents += line
                                if not line.endswith( '\\' ):
                                    self.suppliedMetadata['theWord'][fieldName] = fieldContents
                                    continued = False
                        #if lineCount > 3:
                            #self.stashBook( thisBook )
                            #break

                if lineCount < textLineCountExpected:
                    logging.error( _("theWord Bible module file seems too short: {}").format( self.sourceFilename ) )
                self.encoding = encoding
                break # Get out of decoding loop because we were successful
            except UnicodeDecodeError:
                logging.critical( _("theWord Bible module file fails with encoding: {} {}").format( self.sourceFilename, self.encoding ) )

        #print( self.suppliedMetadata['theWord'] ); halt
        #if 'description' in self.suppliedMetadata['theWord'] and len(self.suppliedMetadata['theWord']['description'])<40: self.name = self.suppliedMetadata['theWord']['description']
        #if 'short.title' in self.suppliedMetadata['theWord']: self.shortName = self.suppliedMetadata['theWord']['short.title']

        self.applySuppliedMetadata( 'theWord' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of theWordBible.load
# end of theWordBible class



def theWordComposeVerseLine( BBB, C, V, verseData, ourGlobals ):
    """
    Composes a single line representing a verse.

    Parameters are the Scripture reference (for error messages),
        the verseData (a list of InternalBibleEntries: pseudo-USFM markers and their contents),
        and a ourGlobals dictionary for holding persistent variables (between calls).

    This function handles the paragraph/new-line markers;
        theWordAdjustLine (above) is called to handle internal/character markers.

    Returns the composed line.
    """
    #print( "theWordComposeVerseLine( {} {}:{} {} {}".format( BBB, C, V, verseData, ourGlobals ) )
    composedLine = ourGlobals['line'] # We might already have some book headings to precede the text for this verse
    ourGlobals['line'] = '' # We've used them so we don't need them any more
    #marker = text = None

    vCount = 0
    lastMarker = None
    #if BBB=='MAT' and C==4 and 14<V<18: print( BBB, C, V, ourGlobals, verseData )
    for verseDataEntry in verseData:
        marker, text = verseDataEntry.getMarker(), verseDataEntry.getFullText()
        #print( '{} {}:{} {}={}'.format( BBB, C, V, marker, text ) )
        if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS: continue # Just ignore added markers -- not needed here
        if marker in ('c','c#','cl','cp','rem',): lastMarker = marker; continue  # ignore all of these for this

        if marker == 'v': # handle versification differences here
            vCount += 1
            if vCount == 1: # Handle verse bridges
                if text != str(V):
                    composedLine += ' <sup>({})</sup> '.format( text ) # Put the additional verse number into the text in parenthesis
            elif vCount > 1: # We have an additional verse number
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert text != str(V)
                composedLine += ' <sup>({})</sup>'.format( text ) # Put the additional verse number into the text in parenthesis
            lastMarker = marker
            continue

        #print( "theWordComposeVerseLine:", BBB, C, V, marker, text )
        if marker in theWordIgnoredIntroMarkers:
            logging.error( "theWordComposeVerseLine: Found unexpected {} introduction marker at {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
            print( "theWordComposeVerseLine:", BBB, C, V, marker, text, verseData )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert marker not in theWordIgnoredIntroMarkers # these markers shouldn't occur in verses

        if marker in ('mt1','mte1'): composedLine += '<TS1>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker in ('mt2','mte2'): composedLine += '<TS2>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker in ('mt3','mte3'): composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker in ('mt4','mte4'): composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker=='ms1': composedLine += '<TS2>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker in ('ms2','ms3','ms4'): composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker=='mr': composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker == 's1':
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<CM>' # append the new paragraph marker to the previous line
            composedLine += '<TS1>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker == 's2': composedLine += '<TS2>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker in ( 's3', 's4', 'sr', 'd', ): composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker in ( 'qa', 'r', ):
            if marker=='r' and text and text[0]!='(' and text[-1]!=')': # Put parenthesis around this if not already there
                text = '(' + text + ')'
            composedLine += '<TS3><i>'+theWordAdjustLine(BBB,C,V,text)+'</i><Ts>'
        elif marker in ( 'm', ):
            assert not text
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<CL>' # append the new paragraph marker to the previous line
            #if text:
                #print( 'm', repr(text), verseData )
                #composedLine += '<CL>'+theWordAdjustLine(BBB,C,V,text)
                #if ourGlobals['pi1'] or ourGlobals['pi2'] or ourGlobals['pi3'] or ourGlobals['pi4'] or ourGlobals['pi5'] or ourGlobals['pi6'] or ourGlobals['pi7']:
                    #composedLine += '<CL>'
                #else: composedLine += '<CM>'
            #else: # there is text
                #composedLine += '<CL>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'p', 'b', ):
            #print( marker, text )
            assert not text
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<CM>' # append the new paragraph marker to the previous line
            #else: composedLine += '<CM>'
            #composedLine += theWordAdjustLine(BBB,C,V,text)
            resettheWordMargins( ourGlobals )
        elif marker in ( 'pi1', ):
            assert not text
            resettheWordMargins( ourGlobals, 'pi1' ); composedLine += '<CM><PI>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pi2', ):
            assert not text
            resettheWordMargins( ourGlobals, 'pi2' ); composedLine += '<CM><PI2>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pi3', 'pmc', ):
            assert not text
            resettheWordMargins( ourGlobals, 'pi3' ); composedLine += '<CM><PI3>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pi4', ):
            assert not text
            resettheWordMargins( ourGlobals, 'pi4' ); composedLine += '<CM><PI4>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pc', ):
            assert not text
            resettheWordMargins( ourGlobals, 'pi5' ); composedLine += '<CM><PI5>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pr', 'pmr', 'cls', ):
            assert not text
            resettheWordMargins( ourGlobals, 'pi6' ); composedLine += '<CM><PI6>'+theWordAdjustLine(BBB,C,V,text) # Originally right-justified
        elif marker in ( 'b', 'mi', 'pm', 'pmo', ):
            assert not text
            resettheWordMargins( ourGlobals, 'pi7' ); composedLine += '<CM><PI7>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'q1', 'qm1', ):
            assert not text
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] += '<CI>' # append the new quotation paragraph marker to the previous line
            else: composedLine += '<CI>'
            if not ourGlobals['pi1']: composedLine += '<PI>'
            resettheWordMargins( ourGlobals, 'pi1' )
            #composedLine += theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'q2', 'qm2', ):
            assert not text
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] += '<CI>' # append the new quotation paragraph marker to the previous line
            else: composedLine += '<CI>'
            if not ourGlobals['pi2']: composedLine += '<PI2>'
            resettheWordMargins( ourGlobals, 'pi2' )
            #composedLine += '<CI><PI2>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'q3', 'qm3', ):
            assert not text
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] += '<CI>' # append the new quotation paragraph marker to the previous line
            else: composedLine += '<CI>'
            if not ourGlobals['pi3']: composedLine += '<PI3>'
            resettheWordMargins( ourGlobals, 'pi3' )
            #composedLine += '<CI><PI3>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'q4', 'qm4', ):
            assert not text
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] += '<CI>' # append the new quotation paragraph marker to the previous line
            else: composedLine += '<CI>'
            if not ourGlobals['pi4']: composedLine += '<PI4>'
            resettheWordMargins( ourGlobals, 'pi4' )
            #composedLine += '<CI><PI4>'+theWordAdjustLine(BBB,C,V,text)
        elif marker == 'li1': resettheWordMargins( ourGlobals, 'pi1' ); composedLine += '<PI>• '+theWordAdjustLine(BBB,C,V,text)
        elif marker == 'li2': resettheWordMargins( ourGlobals, 'pi2' ); composedLine += '<PI2>• '+theWordAdjustLine(BBB,C,V,text)
        elif marker == 'li3': resettheWordMargins( ourGlobals, 'pi3' ); composedLine += '<PI3>• '+theWordAdjustLine(BBB,C,V,text)
        elif marker == 'li4': resettheWordMargins( ourGlobals, 'pi4' ); composedLine += '<PI4>• '+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'cd', 'sp', ): composedLine += '<i>'+theWordAdjustLine(BBB,C,V,text)+'</i>'
        elif marker in ( 'v~', 'p~', ):
            #print( lastMarker )
            if lastMarker == 'p': composedLine += '<CM>' # We had a continuation paragraph
            elif lastMarker == 'm': composedLine += '<CL>' # We had a continuation paragraph
            elif lastMarker in BibleOrgSysGlobals.USFMParagraphMarkers: pass # Did we need to do anything here???
            elif lastMarker != 'v':
                composedLine += theWordAdjustLine(BBB,C,V, text )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "theWordComposeVerseLine:", BBB, C, V, marker, lastMarker, verseData )
                    halt # This should never happen -- probably a b marker with text
            #if ourGlobals['pi1']: composedLine += '<PI>'
            #elif ourGlobals['pi2']: composedLine += '<PI2>'
            #elif ourGlobals['pi3']: composedLine += '<PI3>'
            #elif ourGlobals['pi4']: composedLine += '<PI4>'
            #elif ourGlobals['pi5']: composedLine += '<PI5>'
            #elif ourGlobals['pi6']: composedLine += '<PI6>'
            #elif ourGlobals['pi7']: composedLine += '<PI7>'
            composedLine += theWordAdjustLine(BBB,C,V, text )
        elif marker in ('nb',): # Just ignore these ones
            pass
        else:
            logging.warning( "theWordComposeVerseLine: doesn't handle {!r} yet".format( marker ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "theWordComposeVerseLine: doesn't handle {!r} yet".format( marker ) ); halt
            ourGlobals['unhandledMarkers'].add( marker )
        lastMarker = marker

    # Final clean-up
    composedLine = composedLine.replace( '<CM><CI>', '<CM>' ) # paragraph mark not needed when following a title close marker
    while '  ' in composedLine: # remove double spaces
        composedLine = composedLine.replace( '  ', ' ' )

    # Check what's left at the end
    if '\\' in composedLine:
        logging.warning( "theWordComposeVerseLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, composedLine ) )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "theWordComposeVerseLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, composedLine ) )
            halt
    return composedLine.rstrip()
# end of theWordComposeVerseLine



def createTheWordModule( self, outputFolder, controlDict ):
    """
    Create a SQLite3 database module for the program MySword.

    self here is a Bible object with _processedLines
    """
    from datetime import datetime
    import zipfile


    def writetWBook( writerObject, BBB, ourGlobals ):
        """
        Writes a book to the theWord writerObject file.
        """
        nonlocal lineCount
        bkData = self.books[BBB] if BBB in self.books else None
        #print( bkData._processedLines )
        verseList = BOS.getNumVersesList( BBB )
        numC, numV = len(verseList), verseList[0]

        resettheWordMargins( ourGlobals )
        if bkData: # write book headings (stuff before chapter 1)
            ourGlobals['line'] = theWordHandleIntroduction( BBB, bkData, ourGlobals )

        # Write the verses (whether or not they're populated)
        C = V = 1
        ourGlobals['lastLine'] = None
        while True:
            verseData, composedLine = None, ''
            if bkData:
                try:
                    result = bkData.getContextVerseData( (BBB,str(C),str(V),) )
                    verseData, context = result
                except KeyError:
                    logging.warning( "BibleWriter.totheWord: missing source verse at {} {}:{}".format( BBB, C, V ) )
                    composedLine = '(-)' # assume it was a verse bridge (or something)
                # Handle some common versification anomalies
                if (BBB,C,V) == ('JN3',1,14): # Add text for v15 if it exists
                    try:
                        result15 = bkData.getContextVerseData( ('JN3','1','15',) )
                        verseData15, context15 = result15
                        verseData.extend( verseData15 )
                    except KeyError: pass #  just ignore it
                elif (BBB,C,V) == ('REV',12,17): # Add text for v15 if it exists
                    try:
                        result18 = bkData.getContextVerseData( ('REV','12','18',) )
                        verseData18, context18 = result18
                        verseData.extend( verseData18 )
                    except KeyError: pass #  just ignore it
            if verseData: composedLine = theWordComposeVerseLine( BBB, C, V, verseData, ourGlobals )
            assert '\n' not in composedLine # This would mess everything up
            #print( BBB, C, V, repr(composedLine) )
            if C!=1 or V!=1: # Stay one line behind (because paragraph indicators get appended to the previous line)
                assert '\n' not in ourGlobals['lastLine'] # This would mess everything up
                writerObject.write( ourGlobals['lastLine'] + '\n' ) # Write it whether or not we got data
                lineCount += 1
            ourGlobals['lastLine'] = composedLine
            V += 1
            if V > numV:
                C += 1
                if C > numC:
                    break
                else: # next chapter only
                    numV = verseList[C-1]
                    V = 1
        # Write the last line of the file
        assert '\n' not in ourGlobals['lastLine'] # This would mess everything up
        writerObject.write( ourGlobals['lastLine'] + '\n' ) # Write it whether or not we got data
        lineCount += 1
    # end of totheWord.writetWBook


    # Set-up their Bible reference system
    BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )
    #BRL = BibleReferenceList( BOS, BibleObject=None )

    # Try to figure out if it's an OT/NT or what (allow for up to 6 extra books like FRT,GLS, etc.)
    if len(self) <= (39+6) and self.containsAnyOT39Books() and not self.containsAnyNT27Books():
        testament, extension, startBBB, endBBB = 'OT', '.ot', 'GEN', 'MAL'
        booksExpected, textLineCountExpected, checkTotals = 39, 23145, theWordOTBookLines
    elif len(self) <= (27+6) and self.containsAnyNT27Books() and not self.containsAnyOT39Books():
        testament, extension, startBBB, endBBB = 'NT', '.nt', 'MAT', 'REV'
        booksExpected, textLineCountExpected, checkTotals = 27, 7957, theWordNTBookLines
    else: # assume it's an entire Bible
        testament, extension, startBBB, endBBB = 'BOTH', '.ont', 'GEN', 'REV'
        booksExpected, textLineCountExpected, checkTotals = 66, 31102, theWordBookLines

    if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to theWord format…") )
    mySettings = {}
    mySettings['unhandledMarkers'] = set()
    handledBooks = []

    if 'theWordOutputFilename' in controlDict: filename = controlDict['theWordOutputFilename']
    elif self.sourceFilename: filename = self.sourceFilename
    elif self.shortName: filename = self.shortName
    elif self.abbreviation: filename = self.abbreviation
    elif self.name: filename = self.name
    else: filename = 'export'
    if not filename.endswith( extension ): filename += extension # Make sure that we have the right file extension
    filepath = os.path.join( outputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( '  writetWBook: ' + _("Writing {!r}…").format( filepath ) )
    with open( filepath, 'wt', encoding='utf-8' ) as myFile:
        try: myFile.write('\ufeff') # theWord needs the BOM
        except UnicodeEncodeError: # why does this fail on Windows???
            logging.critical( _("totheWord: Unable to write BOM to file") )
        BBB, bookCount, lineCount, checkCount = startBBB, 0, 0, 0
        while True: # Write each Bible book in the KJV order
            writetWBook( myFile, BBB, mySettings )
            checkCount += checkTotals[bookCount]
            bookCount += 1
            if lineCount != checkCount:
                logging.critical( "Wrong number of lines written: {} {} {} {}".format( bookCount, BBB, lineCount, checkCount ) )
                if BibleOrgSysGlobals.debugFlag: halt
            handledBooks.append( BBB )
            if BBB == endBBB: break
            BBB = BOS.getNextBookCode( BBB )

        # Now append the various settings if any
        written = []
        for keyName in ('id','lang','charset','title','short.title','title.english','description','author',
                        'status','publish.date','version.date','isbn','r2l','font','font.size',
                        'version.major','version.minor','publisher','about','source','creator','keywords',
                        'verse.rule',):
            field = self.getSetting( keyName )
            if field: # Copy non-blank matches
                myFile.write( "{}={}\n".format( keyName, field ) )
                written.append( keyName )
            elif BibleOrgSysGlobals.verbosityLevel > 2: print( "BibleWriter.totheWord: ignored {!r} setting ({})".format( keyName, field ) )
        # Now do some adaptions
        keyName = 'short.title'
        if self.abbreviation and keyName not in written:
            myFile.write( "{}={}\n".format( keyName, self.abbreviation ) )
            written.append( keyName )
        if self.name and keyName not in written:
            myFile.write( "{}={}\n".format( keyName, self.name ) )
            written.append( keyName )
        # Anything useful in the settingsDict?
        for keyName, fieldName in (('title','FullName'),):
            fieldContents = self.getSetting( fieldName )
            if fieldContents and keyName not in written:
                myFile.write( "{}={}\n".format( keyName, fieldContents ) )
                written.append( keyName )
        keyName = 'publish.date'
        if keyName not in written:
            myFile.write( "{}={}\n".format( keyName, datetime.now().strftime('%Y') ) )
            written.append( keyName )

    if mySettings['unhandledMarkers']:
        logging.warning( "BibleWriter.totheWord: Unhandled markers were {}".format( mySettings['unhandledMarkers'] ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled totheWord markers were {}").format( mySettings['unhandledMarkers'] ) )
    unhandledBooks = []
    for BBB in self.getBookList():
        if BBB not in handledBooks: unhandledBooks.append( BBB )
    if unhandledBooks:
        logging.warning( "totheWord: Unhandled books were {}".format( unhandledBooks ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled totheWord books were {}").format( unhandledBooks ) )

    # Now create a zipped version
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} theWord file…".format( filename ) )
    zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
    zf.write( filepath, filename )
    zf.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        print( "  BibleWriter.totheWord finished successfully." )
    return True
# end of createTheWordModule



def testtWB( indexString, twBfolder, twBfilename ):
    """
    Crudely demonstrate the theWord Bible class.
    """
    from BibleOrgSys.Reference import VerseReferences
    #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/theWord modules/' ) # Must be the same as below

    #TUBfolder = os.path.join( twBfolder, twBfilename )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the theWord Bible class {}…").format( indexString) )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( twBfolder, twBfilename ) )
    tWb = theWordBible( twBfolder, twBfilename )
    tWb.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( tWb ) # Just print a summary
    if tWb is not None:
        if BibleOrgSysGlobals.strictCheckingFlag: tWb.check()
        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                            ('OT','DAN','1','21'),
                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
            (t, b, c, v) = reference
            if t=='OT' and len(tWb)==27: continue # Don't bother with OT references if it's only a NT
            if t=='NT' and len(tWb)==39: continue # Don't bother with NT references if it's only a OT
            if t=='DC' and len(tWb)<=66: continue # Don't bother with DC references if it's too small
            svk = VerseReferences.SimpleVerseKey( b, c, v )
            #print( svk, ob.getVerseDataList( reference ) )
            try:
                shortText, verseText = svk.getShortText(), tWb.getVerseText( svk )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
            except KeyError:
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, "not found!!!" )

        # Now export the Bible and compare the round trip
        tWb.totheWord()
        #doaResults = tWb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
        if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the derived USX XML files
            outputFolder = "OutputFiles/BOS_theWord_Reexport/"
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported theWord files…" )
            result = BibleOrgSysGlobals.fileCompare( twBfilename, twBfilename, twBfolder, outputFolder )
            if BibleOrgSysGlobals.debugFlag:
                if not result: halt
# end of testtWB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    if 1: # demo the functions
        #print( theWordGetBBBCV( 1532 ) )
        assert theWordGetBBBCV( 0 ) == ('GEN', 1, 1)
        assert theWordGetBBBCV( 1532 ) == ('GEN', 50, 26)
        assert theWordGetBBBCV( 1533 ) == ('EXO', 1, 1)



    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/theWord modules/' )
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordTest/' )
        result1 = theWordBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = theWordBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA2", result2 )
        result3 = theWordBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA3", result3 )


    if 1: # all discovered modules in the round-trip folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/' )
        foundFolders, foundFiles = [], []
        if os.access( testFolder, os.R_OK ):
            for something in sorted( os.listdir( testFolder ) ):
                somepath = os.path.join( testFolder, something )
                if os.path.isdir( somepath ): foundFolders.append( something )
                elif os.path.isfile( somepath ):
                    if somepath.endswith('.ont') or somepath.endswith('.ot') or somepath.endswith('.nt'):
                        foundFiles.append( something )

            if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
                parameters = [('C'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.starmap( testtWB, parameters ) # have the pool do our loads
                    assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                for j, someFile in enumerate( sorted( foundFiles ) ):
                    indexString = 'C{}'.format( j+1 )
                    if BibleOrgSysGlobals.verbosityLevel > 1: print( "\ntW C{}/ Trying {}".format( indexString, someFile ) )
                    #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                    testtWB( indexString, testFolder, someFile )
                    #break # only do the first one……temp
        else: print( f"Sorry, test folder '{testFolder}' is not readable on this computer." )

    if 1: # all discovered modules in the test folder
        testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/theWord modules/' )
        foundFolders, foundFiles = [], []
        if os.access( testFolder, os.R_OK ):
            for something in sorted( os.listdir( testFolder ) ):
                somepath = os.path.join( testFolder, something )
                if os.path.isdir( somepath ): foundFolders.append( something )
                elif os.path.isfile( somepath ): foundFiles.append( something )

            if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
                parameters = [('D'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.starmap( testtWB, parameters ) # have the pool do our loads
                    assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                for j, someFile in enumerate( sorted( foundFiles ) ):
                    indexString = 'D{}'.format( j+1 )
                    #if 'web' not in someFile: continue # Just try this module
                    if BibleOrgSysGlobals.verbosityLevel > 1: print( "\ntW {}/ Trying {}".format( indexString, someFile ) )
                    #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                    testtWB( indexString, testFolder, someFile )
                    #break # only do the first one…temp
        else: print( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of theWordBible.py
