#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFMBibleBook.py
#
# Module handling the importation of USFM Bible books
#
# Copyright (C) 2010-2023 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module for defining and manipulating USFM Bible books.

CHANGELOG:
    2022-06-10 Make uw alignment loading more robust to handle formatting errors
"""
from gettext import gettext as _
from typing import Dict, List, Tuple, Any, Optional
import os
from pathlib import Path
import logging

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.InputOutput.USFMFile import USFMFile
from BibleOrgSys.Bible import Bible, BibleBook


LAST_MODIFIED_DATE = '2023-01-27' # by RJH
SHORT_PROGRAM_NAME = "USFMBibleBook"
PROGRAM_NAME = "USFM Bible book handler"
PROGRAM_VERSION = '0.59'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


sortedNLMarkers = None



class USFMBibleBook( BibleBook ):
    """
    Class to load and manipulate a single USFM file / book.
    """

    def __init__( self, containerBibleObject:Bible, BBB:str ) -> None:
        """
        Create the USFM Bible book object.
        """
        super().__init__( containerBibleObject, BBB ) # Initialise the base class
        self.objectNameString = 'USFM Bible Book object'
        self.objectTypeString = 'USFM'

        global sortedNLMarkers
        if sortedNLMarkers is None:
            sortedNLMarkers = sorted( BibleOrgSysGlobals.loadedUSFMMarkers.getNewlineMarkersList('Combined'), key=len, reverse=True )
    # end of USFMBibleBook.__init__


    def load( self, filename:str, folder:Optional[str]=None, encoding:Optional[str]=None ) -> None:
        """
        Load the USFM Bible book from a file.

        Tries to combine physical lines into logical lines,
            i.e., so that all lines begin with a USFM paragraph marker.

        Uses the addLine function of the base class to save the lines.

        Note: the base class later on will try to break apart lines with a paragraph marker in the middle --
                we don't need to worry about that here.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"USFMBibleBook.load( filename={filename}, folder={folder}, encoding={encoding} )…" )


        def doaddLine( addMarker:str, addText:str ) -> None:
            """
            Check for newLine markers within the line (if so, break the line) and save the information in our database.

            Also convert ~ to a proper non-break space.

            Note: for uwAligned data, calls will look something like this:
                    doaddLine( 'p~', '\\w Simon|x-occurrence="1" x-occurrences="1"\\w*' )
                    doaddLine( 'p~', '\\w of|x-occurrence="1" x-occurrences="2"\\w* \\w Cyrene|x-occurrence="1" x-occurrences="1"\\w* (\\w the|x-occurrence="1" x-occurrences="2"\\w*' )
            """
            fnPrint( DEBUGGING_THIS_MODULE, f"doaddLine( '{addMarker}', '{addText}' )" )
            # assert addText.count('\\w ') == addText.count('\\w*') # Logged around line 445
            # The below is a false assumption
            #   See: \w='480|x-occurrence="1" x-occurrences="1"\w*\w th|x-occurrence="1" x-occurrences="1"\w*' after ULT KI1 6:1
            # assert '\\w*\\w' not in addText

            marker, text = addMarker, addText.replace( '~', ' ' ) # NBSP = Non-breaking space
            if self.workName == 'UST': # UST uses braces to indicate added text
                text = text.replace( '{', '\\add ' ).replace( '}', '\\add*' )

            if '\\' in text: # Check markers inside the lines
                markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( text )
                ix = 0
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
                    if insideMarker == '\\': # it's a free-standing backspace
                        loadErrors.append( _("{} {}:{} Improper free-standing backspace character within line in \\{}: {!r}").format( self.BBB, C, V, marker, text ) )
                        logging.error( _("Improper free-standing backspace character within line after {} {}:{} in \\{}: {!r}").format( self.BBB, C, V, marker, text ) ) # Only log the first error in the line
                        self.addPriorityError( 100, C, V, _("Improper free-standing backspace character inside a line") )
                    elif BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker(insideMarker) \
                    or insideMarker == 'zaln-e': # Need to split the line for everything else to work properly
                        if ix==0:
                            loadErrors.append( _("{} {}:{} NewLine marker {!r} shouldn't appear within line in \\{}: {!r}").format( self.BBB, C, V, insideMarker, marker, text ) )
                            logging.error( _("NewLine marker {!r} shouldn't appear within line after {} {}:{} in \\{}: {!r}").format( insideMarker, self.BBB, C, V, marker, text ) ) # Only log the first error in the line
                            self.addPriorityError( 96, C, V, _("NewLine marker \\{} shouldn't be inside a line").format( insideMarker ) )
                        thisText = text[ix:iMIndex].rstrip()
                        self.addLine( marker, thisText )
                        ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Did a split from {}:{!r} to {}:{!r} leaving {}:{!r}".format( addMarker, addText, marker, thisText, insideMarker, text[ix:] ) )
                        marker = insideMarker # setup for the next line
                if ix != 0: # We must have separated multiple lines
                    text = text[ix:] # Get the final bit of the line

            self.addLine( marker, text ) # Call the function in the base class to save the line (or the remainder of the line if we split it above)
        # end of doaddLine


        MAX_EXPECTED_NESTING_LEVELS = 20 # Don't allow unlimited nesting

        def handleUWEncoding( givenMarker:str, givenText:str, variables:Dict[str,Any] ) -> Tuple[str,str]:
            """
            Extracts all of the uW alignment information from a translation.
                This uses custom \\zaln fields (with complex nesting)
                    and also \\w fields.

            Alters variables dict as a side-effect.

            Returns a new marker and text with uW alignment markers (zaln-s and zaln-e) removed
                (but \\w markers left in the text)
            """
            debuggingThisFunction = DEBUGGING_THIS_MODULE or False # (99 if self.BBB=='NEH' and C=='1' else False)
            # if self.BBB=='NEH' and C=='1' and V=='2': halt
            fnPrint( debuggingThisFunction, f"'{self.workName}' {self.BBB}_{C}:{V} handleUWEncoding( {givenMarker}={givenText!r}\n              level={variables['level']}, aText='{variables['text']}', aWords='{variables['words']}' )…" )
            if variables['text']:
                assert variables['text'].startswith( 'x-strong="' )
                assert variables['text'].endswith( '"' )
                assert 'zaln' not in variables['text']
            if variables['words']:
                if not BibleOrgSysGlobals.strictCheckingFlag:
                    variables['words'] = variables['words'].rstrip() # Shouldn't really be necessary
                #assert variables['words'].startswith( '\\w ' ) # Not currently true (e.g., might have verse number)
                dPrint( 'Verbose', debuggingThisFunction, f"{self.workName} {self.BBB}_{C}:{V} words={variables['words']}=")
                dPrint( 'Verbose', debuggingThisFunction, f"-1={variables['words'][-1]} -2={variables['words'][-2]}" )
                # dPrint( 'Quiet', debuggingThisFunction, f"-5:-1={variables['words'][-5:-1]} -6:-2={variables['words'][-6:-2]}" )
                if variables['words'].endswith( '"\\w**' ):
                    vPrint( 'Quiet', debuggingThisFunction, "Drop final double asterisk!!!! (for Hindi IRV ???)")
                    variables['words'] = variables['words'][:-1]
                if not ( variables['words'].endswith( '"\\w*' )
                or variables['words'].endswith( '\\w*{' ) # UST Act 1:18 (or should this have been handled earlier)
                or ((variables['words'][-1] in '-\u200c' # Zero-width non-joiner (for Kannada IEV)
                    or variables['words'][-1] in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS)
                        and variables['words'][-5:-1] == '"\\w*' ) \
                or (variables['words'][-1] in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS
                    and variables['words'][-2] in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS
                    and variables['words'][-6:-2] == '"\\w*' ) ):
                        logging.critical( f"handleUWEncoding({givenMarker=} {givenText=} {variables['level']=} {variables['maxLevel']=}) got a problem at {self.BBB}_{C}:{V} with {variables['words']=}" )
                        # ['words']=' \\w the|x-occurrence="2" x-occurrences="3"\\w* {\\w head|x-occurrence="2" x-occurrences="2"\\w*|'
                assert 'zaln' not in variables['words']
            if variables['level'] > MAX_EXPECTED_NESTING_LEVELS:
                logging.critical( f"handleUWEncoding: exceeded maximum nesting levels ({givenMarker=} {givenText=} {variables['level']=} {variables['maxLevel']=}) got a problem at {self.BBB}_{C}:{V} with {variables['words']=}" )


            def saveAlignment( C:str, V:str, textStr:str, wordsStr:str ) -> None:
                """
                A new alignment is a 4-tuple: C, V, (Heb/Grk) textStr, (translated) wordStr.

                Normally a new alignment is just appended to the variables['saved'] list.

                However, some alignments are discontiguous, i.e., the Heb/Grk words aren't side-by-side
                    so we have to append this alignment (with a joiner ' & ') to a previously saved alignment in this case.
                """
                fnPrint( debuggingThisFunction, f"  saveAlignment( {C}:{V}, '{textStr}', '{wordsStr}' ) for {self.BBB} with {len(variables['saved'])} entries…" )
                assert '\\w' not in textStr
                assert wordsStr.count('\\w ') == wordsStr.count('\\w*')

                for j,entry in enumerate( reversed( variables['saved'] ) ):
                    oldC, oldV, oldTextStr, oldWordsStr = entry
                    # if self.BBB=='NEH' and C=='1' and V=='1': dPrint( 'Quiet', debuggingThisFunction, f"saveAlignment() got previously saved {self.BBB} {oldC}:{oldV}, {oldTextStr}, {oldWordsStr}")
                    if oldV != V or oldC != C: break
                    # if self.BBB=='NEH' and C=='1' and V=='1': dPrint( 'Quiet', debuggingThisFunction, f"saveAlignment() still in same {self.BBB} verse {C}:{V} @ -{j}!" )
                    if oldTextStr == textStr: # we have a discontiguous alignment
                        ix = len(variables['saved']) - j - 1
                        # if self.BBB=='NEH' and C=='1' and V=='1': dPrint( 'Quiet', debuggingThisFunction, f"saveAlignment() discontiguous still have same {self.BBB}_{C}:{V} original word @ {ix}!" )
                        # if self.BBB=='NEH' and C=='1' and V=='1': dPrint( 'Quiet', debuggingThisFunction, "saveAlignment() discontiguous check:", variables['saved'][ix] )
                        discard = variables['saved'].pop( ix ) # Remove old entry from list
                        assert discard == entry
                        # Append non-contiguous join to oldWordsStr and insert where we deleted
                        #   We use a joiner ' & ' that can easily be detected
                        # if self.BBB=='NEH' and C=='1' and V=='1': dPrint( 'Quiet', debuggingThisFunction, f"    saveAlignment: Combined {self.BBB}_{C}:{V} discontiguous will be: '{oldWordsStr} & {wordsStr}'" )
                        variables['saved'].insert( ix, (C,V, textStr, f'{oldWordsStr} & {wordsStr}') )
                        return

                # if not appended: # Just add a normal new entry
                variables['saved'].append( (C,V, textStr, wordsStr) )
                # if self.BBB=='NEH' and C=='1' and V=='1': dPrint( 'Quiet', debuggingThisFunction, f"    saveAlignment: Appended new alignment 4-tuple to variables for {self.BBB}_{C}:{V} to get saved({len(variables['saved'])})={variables['saved']}" )
            # end of saveAlignment helper function inside handleUWEncoding


            def findInternalStarts( marker:str, text:str, variables:Dict[str,Any] ) -> Tuple[str,str]:
                """
                Finds self-closed \\zaln-s alignment start markers that may occur inside the line.

                Removes the markers, and incrementes variables['level']
                    and appends the enclosed text to the variables['text'] variable
                Thus alters variables dict as a side-effect.

                Returns a new marker and text with uW start alignment markers removed.
                """
                fnPrint( debuggingThisFunction, f"  findInternalStarts( {marker!r}, {text!r}, level={variables['level']}, aText='{variables['text']}', aWords='{variables['words']}' )…" )
                assert marker not in ('zaln-s','zaln-e')

                for numFound in range( 99 ):
                    dPrint( 'Never', debuggingThisFunction, f"    findInternalStarts: Loop {numFound} with text='{text}'" )
                    ixAlignmentStart = text.find( '\\zaln-s |' )
                    if ixAlignmentStart == -1:
                        if text.find('zaln-s') > 0:
                            logging.error( f"Found unexpected 'zaln-s' without backslash in {self.BBB}_{C}:{V} {marker}='{text}'" )
                        break # Didn't find it
                    #else: # Found zaln-s alignment start marker
                    lookForCount = max( 1, variables['level'] ) # How many consecutive self-closed end-markers to search for
                    ixAlignmentEnd = text.find( '\\zaln-e\\*' * lookForCount )
                    if ixAlignmentEnd!=-1 and ixAlignmentEnd < ixAlignmentStart:
                        # Usually this happens around punctuation such as Hebrew maqqef (where spaces aren't wanted)
                        # We have to process the end of the previous field first
                        assert variables['level'] > 0
                        dPrint( 'Never', debuggingThisFunction, f"        findInternalStarts: Found {lookForCount} preceding level {variables['level']} end marker(s) inside line" )
                        assert variables['text']
                        if marker == 'INLINE': assert not variables['words']
                        text = text.replace( '\\zaln-e\\*' * lookForCount, '', 1 ) # Remove whatever we found above
                        while ixAlignmentEnd<len(text) and text[ixAlignmentEnd] in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS:
                            #dPrint( 'Quiet', debuggingThisFunction, f"        findInternalStarts: Appended punctuation {text[ixAlignmentEnd]} to '{variables['words']}'" )
                            # variables['words'] += text[ixAlignmentEnd+9] # Append the punctuation
                            ixAlignmentEnd += 1 # Account for the punctuation or space
                        variables['words'] += text[:ixAlignmentEnd] if marker=='INLINE' \
                                                else f' \\{marker} {text[:ixAlignmentEnd]}'
                        assert variables['words']
                        #dPrint( 'Quiet', debuggingThisFunction, "words1", variables['words'] )
                        saveAlignment( C, V, variables['text'], variables['words'] )
                        # if marker=='v' or f'\\{marker}*' in text[:ixAlignmentEnd]: # the bit we're about to drop
                        #     marker = 'INLINE' # not totally sure that this is the right thing to do
                        # 9 below is len('\zaln-e\*')
                        # if text[:ixAlignmentEnd+9*lookForCount]: dPrint( 'Never', debuggingThisFunction, f"{self.workName} {self.BBB}_{C}:{V} {marker} findInternalStarts: Dropped '{text[:ixAlignmentEnd+9*lookForCount]}' before '{text[ixAlignmentEnd+9*lookForCount:]}' with text={variables['text']} and words={variables['words']}" )
                        # text = text[ixAlignmentEnd+9*lookForCount:] # 9=len('\zaln-e\*')
                        variables['text'] = variables['words'] = ''
                        variables['level'] = 0
                        dPrint( 'Never', debuggingThisFunction, f"      findInternalStarts: Decreased level to {variables['level']}" )
                        assert variables['level'] >= 0
                        dPrint( 'Never', debuggingThisFunction, f"      Now got rest1 text='{text}'" )
                        continue
                    assert 'zaln-e' not in text[:ixAlignmentStart] # Make sure our nesting isn't confused
                    ixAlignmentStartEnding = text.find( '\\*' ) # Even start marker should be (self-)closed
                    if ixAlignmentStartEnding == -1: # Wasn't self-closing
                        loadErrors.append( _("{} {}:{} Unclosed '\\{}' Door43 custom alignment marker at beginning of line (with no text)") \
                                        .format( self.BBB, C, V, marker ) )
                        logging.warning( _("Unclosed '\\{}' Door43 custom alignment marker after {} {}:{} at beginning of line (with no text)") \
                                        .format( marker, self.BBB, C, V ) )
                        dPrint( 'Info', debuggingThisFunction, "The above warnings and error messages need fixing!")
                        if debuggingThisFunction or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: halt # Error messages need fixing
                    else: # self-closing was ok
                        variables['level'] += 1
                        if variables['level'] > variables['maxLevel']: variables['maxLevel'] = variables['level']
                        if variables['level'] > MAX_EXPECTED_NESTING_LEVELS: halt
                        dPrint( 'Never', debuggingThisFunction, f"      findInternalStarts: Increased level to {variables['level']}" )
                        variables['text'] += ('|' if variables['text'] else '') \
                                    + text[ixAlignmentStart+9:ixAlignmentStartEnding].strip() # Can still be a space after the |
                        dPrint( 'Never', debuggingThisFunction, f"      Now got alignmentText='{variables['text']}'" )
                        text = text[:ixAlignmentStart] + text[ixAlignmentStartEnding+2:]
                        dPrint( 'Never', debuggingThisFunction, f"      Now got rest2 text='{text}'" )

                #if variables['level'] > 0:
                    #variables['words'] += f'{marker} {text}'

                dPrint( 'Never', debuggingThisFunction, f"    findInternalStarts returning {marker}='{text}' with lev={variables['level']}, aText='{variables['text']}', aWords='{variables['words']}'" )
                if 'zaln-s' in text:
                    logging.critical( f"findInternalStarts() missed processing a zaln-s marker in {self.BBB}_{C}:{V} {marker}='{text}'" )
                return marker, text
            # end of findInternalStarts function


            # handleUWEncoding function main code
            marker, text = givenMarker, givenText
            if marker == 'zaln-s':
                assert not variables['text']
                assert text.startswith('|')
                # Put marker into line then we can use the same function for inline milestone starts
                marker, text = findInternalStarts( 'INLINE', f'\\{marker} {text}', variables )
            elif marker == 'zaln-e': # unexpected
                logging.critical( "Didn't expect zaln-e marker at beginning of line" )
                halt

            # Could be v, w, etc. -- now look inside the text
            marker, text = findInternalStarts( marker, text, variables ) # Could be more

            # Look for any self-closed end-alignment milestones
            if variables['level'] > 0:
                dPrint( 'Never', debuggingThisFunction, f"     handleUWEncoding:  Looking for {variables['level']} end marker(s)…" )
                endMarkers = '\\zaln-e\\*' * variables['level']
                ixEndMarkers = text.find( endMarkers )
                assert ixEndMarkers != 0 # Not expected at the beginning of a line
                if ixEndMarkers > 0: # Found end alignment marker(s)
                    dPrint( 'Never', debuggingThisFunction, f"        handleUWEncoding: Found {variables['level']} end marker(s)" )
                    assert variables['text']
                    if marker == 'INLINE': assert not variables['words']
                    adjustedText = text.replace( endMarkers, '', 1 ) # Remove whatever we found above
                    punctCount = 0
                    while (ixEndMarkers+punctCount)<len(adjustedText) and adjustedText[ixEndMarkers+punctCount] in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS:
                        #dPrint( 'Quiet', debuggingThisFunction, f"        findInternalStarts: Appended punctuation {text[ixAlignmentEnd]} to '{variables['words']}'" )
                        # variables['words'] += text[ixAlignmentEnd+9] # Append the punctuation
                        punctCount += 1 # Account for the punctuation or space
                    variables['words'] += adjustedText[:ixEndMarkers+punctCount] if marker=='INLINE' \
                                            else f' \\{marker} {adjustedText[:ixEndMarkers+punctCount]}'
                    dPrint( 'Never', debuggingThisFunction, f"{marker}='{text}' GOT1 variables['words']='{variables['words']}'" )
                    assert variables['words']
                    assert variables['words'].count('\\w ') == variables['words'].count('\\w*')
                    #dPrint( 'Quiet', debuggingThisFunction, "words2", variables['words'] )
                    saveAlignment( C, V, variables['text'], variables['words'] )
                    text = text[:ixEndMarkers] + text[ixEndMarkers+len(endMarkers):] # Could be punctuation or more on the end
                    variables['text'] = variables['words'] = ''
                    dPrint( 'Never', debuggingThisFunction, f"      handleUWEncoding: Reset level from {variables['level']} to zero" )
                    variables['level'] = 0
                    #dPrint( 'Never', debuggingThisFunction, f"      Decreased level to {variables['level']}" )
                    #assert variables['level'] >= 0
                elif '\\zaln-e' in text:
                    logging.critical( f"Not enough zaln-e markers (expected {variables['level']}) in {marker}={text}" )
                    halt # Not enough zaln-e markers
                else: # end marker(s) must be on a following line
                    #dPrint( 'Quiet', debuggingThisFunction, self.wordName, self.BBB, C, V, "words3a", variables['words'] )
                    #dPrint( 'Quiet', debuggingThisFunction, f"{marker}={text}" )
                    if marker == 'INLINE': assert not variables['words']
                    variables['words'] += text if marker=='INLINE' else f' \\{marker} {text}'
                    #dPrint( 'Quiet', debuggingThisFunction, "words3b", variables['words'] )
                    dPrint( 'Never', debuggingThisFunction, f"{marker}='{text}' GOT2 variables['words']='{variables['words']}'" )
                    assert variables['words']
                    assert variables['words'].count('\\w ') == variables['words'].count('\\w*')

            dPrint( 'Never', debuggingThisFunction, f"handleUWEncoding: Got near end1 with {marker}='{text}'" )
            #dPrint( 'Quiet', debuggingThisFunction, "rawLines", self._rawLines[-4:] )
            if 'zaln' in text: # error because we have no open levels
                logging.critical( f"Why is zaln in '{self.BBB}' {marker}='{text}' with no open levels" )
            if marker == 'INLINE': # then we need to supply a remaining marker
                dPrint( 'Never', debuggingThisFunction, f"handleUWEncoding: Find a new marker to replace {marker}='{text}'" )
                # if text.startswith( '\\w ' ) \
                # or text[1:].startswith( '\\w ' ): # There may be preceding punctuation (actually, maybe something like ', “\w Then...')
                if text[0]=='\\' and text[1]!='w' and text[2]==' ': # e.g., startswith( '\\p ') or startswith( '\\q ') or startswith( '\\v ') or startswith( '\\f ')
                    marker, text = text[1], text[3:]
                elif text[0]=='\\' and text[3]==' ': # e.g., startswith( '\\pi ') or startswith( '\\q1 ')
                    marker, text = text[1:3], text[4:]
                else:
                    if text[0] not in ',:;.?!”’} -—[‘"' and not text.startswith( '\\w '): dPrint( 'Never', debuggingThisFunction, f"handleUWEncoding '{self.workName}' {self.BBB}_{C}:{V}: handled INLINE '{text}'" )
                    marker = 'p~'
            if marker == 'INLINE':
                logging.critical( f"Programming error in {self.BBB} handleUWEncoding() with INLINE='{text}'" )

            dPrint( 'Never', debuggingThisFunction, f"  handleUWEncoding returning {marker}='{text}' with level={variables['level']}, aText='{variables['text']}', aWords='{variables['words']}'" )
            assert 'zaln' not in variables['text']
            assert '\\w' not in variables['text']
            assert 'zaln' not in variables['words']
            if givenText and givenText[-1] in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS:
                assert text[-1] == givenText[-1]
            return marker, text
        # end of handleUWEncoding


        # Main code for USFMBibleBook.load()
        issueLinePositioningErrors = True # internal markers at beginning of line, etc.
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "OBNS", self.containerBibleObject.objectNameString )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, dir(self.containerBibleObject) )

        gotUWEncoding = False
        alignmentVariables = { 'level':0, 'maxLevel':0, 'text':'', 'words':'', 'saved':[] }
        try:
            if self.containerBibleObject.uWencoded:
                gotUWEncoding = True
                issueLinePositioningErrors = False
        except AttributeError: pass # Don't worry about it

        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + _("Loading {}…").format( filename ) )
        #self.BBB = BBB
        #self.isSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( BBB )
        self.sourceFilename = filename
        self.sourceFolder = folder
        self.sourceFilepath = os.path.join( folder, filename ) if folder else filename
        originalBook = USFMFile()
        if encoding is None: encoding = 'utf-8'
        originalBook.read( self.sourceFilepath, encoding=encoding )

        # Do some important cleaning up before we save the data
        C, V = '-1', '-1' # So first/id line starts at -1:0
        lastMarker = lastText = None
        loadErrors:List[str] = []
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "USFMBibleBook.load():", type(originalBook), type(originalBook.lines), len(originalBook.lines), originalBook.lines[0] )
        for marker,text in originalBook.lines: # Always process a line behind in case we have to combine lines
            # if self.BBB == 'EZR':
            #     if C == '5': DEBUGGING_THIS_MODULE = False
            #     if C == '6': halt
            if DEBUGGING_THIS_MODULE and gotUWEncoding:
                dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''\n'{self.workName}' {self.BBB} USFMBible.load() loop for line {marker}='{text}' for alignment level = {alignmentVariables['level']} (Max so far = {alignmentVariables['maxLevel']})
    Alignment text = {alignmentVariables['text']!r}{chr(10) if alignmentVariables['text'] else ''}    Alignment words = {alignmentVariables['words']!r}''' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Alignments ({len(alignmentVariables['saved'])}) = {alignmentVariables['saved']}" )
                dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Num saved alignments = {len(alignmentVariables['saved']):,}:" )
                if len(alignmentVariables['saved']) >= 3:
                    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Saved -3 is {alignmentVariables['saved'][-3][0]}:{alignmentVariables['saved'][-3][1]} with {alignmentVariables['saved'][-3][2]}='{alignmentVariables['saved'][-3][3]}'" )
                if len(alignmentVariables['saved']) >= 2:
                    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Saved -2 is {alignmentVariables['saved'][-2][0]}:{alignmentVariables['saved'][-2][1]} with {alignmentVariables['saved'][-2][2]}='{alignmentVariables['saved'][-2][3]}'" )
                if len(alignmentVariables['saved']) >= 1:
                    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Saved -1 is {alignmentVariables['saved'][-1][0]}:{alignmentVariables['saved'][-1][1]} with {alignmentVariables['saved'][-1][2]}='{alignmentVariables['saved'][-1][3]}'" )

            # Check for lines like:
            #   \w='480|x-occurrence="1" x-occurrences="1"\w*\w th|x-occurrence="1" x-occurrences="1"\w*' after ULT KI1 6:1
            if '\\w*\\w ' in text: # two separate words with no space or punctuation between them
                if marker in ('w','v','p','zaln-s'):
                    ixWordEndIndex = text.index( '|' )
                    firstWord = text[:ixWordEndIndex]
                    if not firstWord.isdigit():
                        loadErrors.append( _("{} {}:{} Found suspect concatenated w fields in \\{}='{}'") \
                                    .format( self.BBB, C, V, marker, text ) )
                        logging.warning( _("Found suspect concatenated w fields in \\{}='{}' after {} {} {}:{}") \
                                    .format( marker, text, self.workName, self.BBB, C, V ) )
                    # else: print( f"handleUWEncoding(): Got '{text[ixWordEndIndex+1:]}' immediately following '{firstWord}' in '{self.workName}' {self.BBB}_{C}:{V}")
                else: print( f"Mismatched in \\w fields {marker}='{text}'" ); halt # Some other marker

            if (marker=='w' and text.count('\\w ')+1 !=  text.count('\\w*')) \
            or (marker!='w' and text.count('\\w ') !=  text.count('\\w*')):
                loadErrors.append( _("{} {}:{} Found wrongly coded w fields in \\{}='{}'") \
                                    .format( self.BBB, C, V, marker, text ) )
                logging.error( _("Found wrongly coded w fields in \\{}='{}' after {} {} {}:{}") \
                                    .format( marker, text, self.workName, self.BBB, C, V ) )
                text = f'{text}\\w*' if marker=='w' else ' '
            if (marker == 'w' and text.count('\\w ')+1 !=  text.count('\\w*')) \
            or (marker != 'w' and  text.count('\\w ') !=  text.count('\\w*')):
                loadErrors.append( _("{} {}:{} Found mismatched w fields in \\{}='{}'") \
                            .format( self.BBB, C, V, marker, text ) )
                logging.critical( _("Found mismatched w fields in \\{}='{}' after {} {} {}:{}") \
                            .format( marker, text, self.workName, self.BBB, C, V ) )

            if marker == 's5': # it's a Door43 translatable section, i.e., obsolete chunking marker
                # We remove these
                if text:
                    if text.strip():
                        loadErrors.append( _("{} {}:{} Removed '\\{}' Door43 custom marker at beginning of line (WITH text)") \
                                            .format( self.BBB, C, V, marker ) )
                        logging.error( _("Removed '\\{}' Door43 custom marker after {} {} {}:{} at beginning of line (WITH text)") \
                                            .format( marker, self.workName, self.BBB, C, V ) )
                        text = text.lstrip() # Can be an extra space in here!!! (eg., ULT MAT 12:17)
                        if text.startswith( '\\v ' ):
                            marker, text = 'v', text[3:] # Drop s5 and adjust marker
                        else:
                            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"s5 text='{text}'" )
                            halt
                    else: # was just whitespace
                        loadErrors.append( _("{} {}:{} Removed '\\{}' Door43 custom marker at beginning of line (with following whitespace)") \
                                            .format( self.BBB, C, V, marker ) )
                        logging.warning( _("Removed '\\{}' Door43 custom marker after {} {}:{} at beginning of line (with following whitespace)") \
                                            .format( marker, self.BBB, C, V ) )
                        continue # so it just gets ignored, effectively deleted
                else: # have s5 field without text!
                    loadErrors.append( _("{} {}:{} Removed '\\{}' Door43 custom marker at beginning of line (with no text)") \
                                        .format( self.BBB, C, V, marker ) )
                    logging.warning( _("Removed '\\{}' Door43 custom marker after {} {}:{} at beginning of line (with no text)") \
                                        .format( marker, self.BBB, C, V ) )
                    continue # so it just gets ignored, effectively deleted
            elif marker == 'ts\\*': # it's a Door43 translatable section, i.e., self-closed chunking marker
                # We remove these
                if text:
                    if text.strip():
                        loadErrors.append( _("{} {}:{} Removed '\\{}' Door43 chunking marker at beginning of line (WITH text)") \
                                            .format( self.BBB, C, V, marker ) )
                        logging.error( _("Removed '\\{}' Door43 chunking marker after {} {} {}:{} at beginning of line (WITH text)") \
                                            .format( marker, self.workName, self.BBB, C, V ) )
                        text = text.lstrip() # Can be an extra space in here!!! (eg., ULT MAT 12:17)
                        if text.startswith( '\\v ' ):
                            marker, text = 'v', text[3:] # Drop \ts\\* and adjust marker
                        elif text.startswith( '\\w ' ):
                            marker, text = 'w', text[3:] # Drop \ts\\* and adjust marker
                        elif text.startswith( '{\\w ' ): # uW UST Exo 17:10 (probably bad USFM???)
                            marker = 'p~' # Drop \ts\\* -- try a continuation paragraph???
                        else:
                            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ts\\* text='{text}'" )
                            halt
                    else: # was just whitespace
                        loadErrors.append( _("{} {}:{} Removed '\\{}' Door43 chunking marker at beginning of line (with following whitespace)") \
                                            .format( self.BBB, C, V, marker ) )
                        logging.warning( _("Removed '\\{}' Door43 chunking marker after {} {}:{} at beginning of line (with following whitespace)") \
                                            .format( marker, self.BBB, C, V ) )
                        continue # so it just gets ignored, effectively deleted
                else: # have \\ts\\* field without text!
                    loadErrors.append( _("{} {}:{} Removed '\\{}' Door43 chunking marker at beginning of line (with no text)") \
                                        .format( self.BBB, C, V, marker ) )
                    logging.warning( _("Removed '\\{}' Door43 chunking marker after {} {}:{} at beginning of line (with no text)") \
                                        .format( marker, self.BBB, C, V ) )
                    continue # so it just gets ignored, effectively deleted

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "bits", text.split() )
                try: C = text.split()[0]
                except IndexError: # Seems we had a \c field that's just whitespace
                    loadErrors.append( _("{} {}:{} Found {!r} invalid chapter field") \
                                        .format( self.BBB, C, V, text ) )
                    logging.critical( _("Found {!r} invalid chapter field after {} {}:{}") \
                                        .format( text, self.BBB, C, V ) )
                    self.addPriorityError( 100, C, V, _("Found invalid/empty chapter field in file") )
                V = '0'
            elif marker=='v' and text:
                newV = text.split()[0]
                if V=='0' and not ( newV=='1' or newV.startswith( '1-' ) ):
                    loadErrors.append( _("{} {}:{} Expected v1 after chapter marker not {!r}") \
                                        .format( self.BBB, C, V, newV ) )
                    logging.error( _("Unexpected {!r} verse number immediately after chapter field after {} {}:{}") \
                                        .format( newV, self.BBB, C, V ) )
                    self.addPriorityError( 100, C, V, _("Got unexpected chapter number") )
                V = newV
                if C == '-1': C = '1' # Some single chapter books don't have an explicit chapter 1 marker
            elif C == '-1' and marker not in ('headers','intro'): V = str( int(V) + 1 )
            elif marker=='restore': continue # Ignore these lines completely

            # Now load the actual Bible book data
            if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                if lastMarker:
                    #  dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Add1")
                    doaddLine( lastMarker, lastText )
                    lastMarker = lastText = None
                if gotUWEncoding:
                    marker, text = handleUWEncoding( marker, text, alignmentVariables )
            elif BibleOrgSysGlobals.loadedUSFMMarkers.isInternalMarker( marker ) \
            or marker.endswith('*') and BibleOrgSysGlobals.loadedUSFMMarkers.isInternalMarker( marker[:-1] ): # the line begins with an internal marker -- append it to the previous line
                if issueLinePositioningErrors \
                and (not gotUWEncoding or marker!='w'):
                    if text:
                        loadErrors.append( _("{} {}:{} Found '\\{}' internal marker at beginning of line with text: {!r}").format( self.BBB, C, V, marker, text ) )
                        logging.warning( _("Found '\\{}' internal marker after {} {}:{} at beginning of line with text: {!r}").format( marker, self.BBB, C, V, text ) )
                    else: # no text
                        loadErrors.append( _("{} {}:{} Found '\\{}' internal marker at beginning of line (with no text)").format( self.BBB, C, V, marker ) )
                        logging.warning( _("Found '\\{}' internal marker after {} {}:{} at beginning of line (with no text)").format( marker, self.BBB, C, V ) )
                    self.addPriorityError( 27, C, V, _("Found \\{} internal marker on new line in file").format( marker ) )
                if gotUWEncoding:
                    #  dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "HERE1", lastMarker, lastText, "now", marker, text)
                    marker, text = handleUWEncoding( marker, text, alignmentVariables )
                    #  dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "HERE2", lastMarker, lastText, "now", marker, text)
                    if marker in BibleOrgSysGlobals.USFMCharacterMarkers and (lastMarker in ('c', 'v', 'p~', 'd', 'q','pi','qm','li') or lastMarker in BibleOrgSysGlobals.USFMParagraphMarkers):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"HereXX with {lastMarker} now {marker}" )
                        if not lastText.endswith(' '): lastText += ' ' # Not always good to add a space, but it's their fault!
                        lastText +=  '\\' + marker + ' ' + text
                        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"{self.BBB} {C} {V} Appended1a {marker}='{text}' to get combined line {lastMarker}='{lastText}'" )
                        marker = text = None # Seems to make no difference
                    elif marker=='p~' and (lastMarker in ('v', 'p~', 'q','pi','qm','li') or lastMarker in BibleOrgSysGlobals.USFMParagraphMarkers):
                        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"HereYY with {lastMarker} now {marker}='{text}'" )
                        if not lastText.endswith(' '): lastText += ' ' # Not always good to add a space, but it's their fault!
                        lastText += text
                        vPrint( 'Never', DEBUGGING_THIS_MODULE, f"{self.BBB} {C} {V} Appended1b {marker}='{text}' to get combined line {lastMarker}='{lastText}'" )
                        marker = text = None # Seems to make no difference
                    elif marker == 'w' and lastMarker in ('ts','sp'): # \\ts: A common unfoldingWord USFM encoding error; \\sp in Hindu SNG
                        logging.error( f"USFMBibleBook.load() '{self.workName}' {self.BBB}_{C}:{V} added new paragraph for encoding error after '{lastMarker}': {marker}='{text}'" )
                        marker, text = 'p', '\\w {text}'
                    elif marker == 'p~' and lastMarker == 'ts': # A common unfoldingWord USFM encoding error
                        logging.error( f"USFMBibleBook.load() '{self.workName}' {self.BBB}_{C}:{V} added new paragraph for encoding error after '{lastMarker}': {marker}='{text}'" )
                        marker = 'p'
                    elif marker=='qs*' and not text.strip(): # selah character ending marker on its own line
                        pass
                    elif marker=='qa' and text: # Hebrew letters in Psalm 119
                        pass
                    else:
                        #dPrint( 'Never', debuggingThisFunction, 'USFM Para Markers', BibleOrgSysGlobals.USFMParagraphMarkers )
                        logging.critical( f"Programming error ¬ZALN: USFMBibleBook.load() lost '{self.workName}' {self.BBB}_{C}:{V} text after '{lastMarker}': {marker}='{text}'" )
                        if self.doExtraChecking: halt
            elif BibleOrgSysGlobals.loadedUSFMMarkers.isNoteMarker( marker ) \
            or marker.endswith('*') and BibleOrgSysGlobals.loadedUSFMMarkers.isNoteMarker( marker[:-1] ): # the line begins with a note marker -- append it to the previous line
                if text:
                    loadErrors.append( _("{} {}:{} Found '\\{}' note marker at beginning of line with text: {!r}").format( self.BBB, C, V, marker, text ) )
                    logging.warning( _("Found '\\{}' note marker after {} {}:{} at beginning of line with text: {!r}").format( marker, self.BBB, C, V, text ) )
                else: # no text
                    loadErrors.append( _("{} {}:{} Found '\\{}' note marker at beginning of line (with no text)").format( self.BBB, C, V, marker ) )
                    logging.warning( _("Found '\\{}' note marker after {} {}:{} at beginning of line (with no text)").format( marker, self.BBB, C, V ) )
                self.addPriorityError( 26, C, V, _("Found \\{} note marker on new line in file").format( marker ) )
                if not lastText.endswith(' ') and marker!='f': lastText += ' ' # Not always good to add a space, but it's their fault! Don't do it for footnotes, though.
                lastText +=  '\\' + marker + ' ' + text
                dPrint( 'Never', DEBUGGING_THIS_MODULE, f"{self.BBB} {C} {V} Appended2 {marker}='{text}' to get combined line {lastMarker}='{lastText}'" )
            else: # the line begins with an unknown marker
                # if lastMarker:
                #     dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Add2", marker)
                #     doaddLine( lastMarker, lastText )
                #     lastMarker = lastText = None
                if marker in ('zaln-s','zaln-e'): # it's a Door43 translation alignment marker (should be self-closed)
                    gotUWEncoding = True
                    marker, text = handleUWEncoding( marker, text, alignmentVariables )
                    if marker=='p~' and (lastMarker in ('v', 'p~', 'q','pi','qm','li') or lastMarker in BibleOrgSysGlobals.USFMParagraphMarkers):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"HereYY with {lastMarker} now {marker}" )
                        if not lastText.endswith(' '): lastText += ' ' # Not always good to add a space, but it's their fault!
                        lastText +=  text
                        vPrint( 'Never', DEBUGGING_THIS_MODULE, f"{self.BBB} {C} {V} Appended3 {marker}='{text}' to get combined line {lastMarker}='{lastText}'" )
                        marker = text = None # Seems to make no difference
                    elif marker == 'p~' and lastMarker in ('ts','sp','d'): # A common unfoldingWord USFM encoding error
                        logging.error( f"USFMBibleBook.load() '{self.workName}' {self.BBB}_{C}:{V} added new paragraph for encoding error after '{lastMarker}': {marker}='{text}'" )
                        marker = 'p'
                    else:
                        # print( 'USFM Para Markers', BibleOrgSysGlobals.USFMParagraphMarkers )
                        logging.critical( f"Programming error ZALN: USFMBibleBook.load() lost '{self.workName}' {self.BBB}_{C}:{V} text after '{lastMarker}': {marker}='{text}'" )
                        if self.doExtraChecking: halt
                elif marker and marker[0] == 'z': # it's a custom marker
                    if text:
                        loadErrors.append( _("{} {}:{} Found '\\{}' unknown custom marker at beginning of line with text: {!r}") \
                                            .format( self.BBB, C, V, marker, text ) )
                        logging.warning( _("Found '\\{}' unknown custom marker after {} {}:{} at beginning of line with text: {!r}") \
                                            .format( marker, self.BBB, C, V, text ) )
                    else: # no text
                        loadErrors.append( _("{} {}:{} Found '\\{}' unknown custom marker at beginning of line (with no text)") \
                                            .format( self.BBB, C, V, marker ) )
                        logging.warning( _("Found '\\{}' unknown custom marker after {} {}:{} at beginning of line (with no text)") \
                                            .format( marker, self.BBB, C, V ) )
                    self.addPriorityError( 80, C, V, _("Found \\{} unknown custom marker on new line in file").format( marker ) )
                else: # it's an unknown marker
                    if text:
                        loadErrors.append( _("{} {}:{} Found '\\{}' unknown marker at beginning of line with text: {!r}") \
                                            .format( self.BBB, C, V, marker, text ) )
                        logging.error( _("Found '\\{}' unknown marker after {} {}:{} at beginning of line with text: {!r}") \
                                            .format( marker, self.BBB, C, V, text ) )
                    else: # no text
                        loadErrors.append( _("{} {}:{} Found '\\{}' unknown marker at beginning of line (with no text)") \
                                            .format( self.BBB, C, V, marker ) )
                        logging.error( _("Found '\\{}' unknown marker after {} {}:{} at beginning of line (with no text)") \
                                            .format( marker, self.BBB, C, V ) )
                    self.addPriorityError( 100, C, V, _("Found \\{} unknown marker on new line in file").format( marker ) )
                    # TODO: Should the following code be disabled by the 'strict' flag????
                    for tryMarker in sortedNLMarkers: # Try to do something intelligent here -- it might be just a missing space
                        if marker.startswith( tryMarker ): # Let's try changing it
                            if lastMarker:
                                #  dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Add3")
                                doaddLine( lastMarker, lastText )
                                lastMarker = lastText = None
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"TM={tryMarker} LM={lastMarker!r} LT={lastText!r} M={marker!r} T={text!r}")
                            # Move the extra appendage to the marker into the actual text
                            marker, text = tryMarker, marker[len(tryMarker):] + ' ' + text
                            if text:
                                loadErrors.append( _("{} {}:{} Changed '\\{}' unknown marker to {!r} at beginning of line: {}").format( self.BBB, C, V, marker, tryMarker, text ) )
                                logging.warning( _("Changed '\\{}' unknown marker to {!r} after {} {}:{} at beginning of line: {}").format( marker, tryMarker, self.BBB, C, V, text ) )
                            else:
                                loadErrors.append( _("{} {}:{} Changed '\\{}' unknown marker to {!r} at beginning of otherwise empty line").format( self.BBB, C, V, marker, tryMarker ) )
                                logging.warning( _("Changed '\\{}' unknown marker to {!r} after {} {}:{} at beginning of otherwise empty line").format( marker, tryMarker, self.BBB, C, V ) )
                            break
                    # Otherwise, don't bother processing this line -- it'll just cause more problems later on
            if marker and not lastMarker:
                lastMarker, lastText = marker, text

        if not originalBook.lines: # There were no lines!!!
            assert not lastMarker and not lastText
            loadErrors.append( _("{} This USFM file was totally empty: {}").format( self.BBB, self.sourceFilename ) )
            logging.error( _("USFM file for {} was totally empty: {}").format( self.BBB, self.sourceFilename ) )
            marker, text = 'rem', 'This (USFM) file was completely empty' # Save something since we had a file at least

        if lastMarker: doaddLine( lastMarker, lastText ) # Process the final line
        # if marker: print("2", marker, text);doaddLine( marker, text ) # Process the final line

        if gotUWEncoding or alignmentVariables['saved']:
            assert alignmentVariables['level'] == 0 # no left-overs
            assert not alignmentVariables['text'] # no left-overs
            assert not alignmentVariables['words'] # no left-overs
            if alignmentVariables['saved']:
                self.uWalignments = alignmentVariables['saved']
                self.containerBibleObject.uWencoded = True
                if DEBUGGING_THIS_MODULE:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nGot {len(self.uWalignments):,} alignments for '{self.workName}' {self.BBB}" )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Alignments max level was {alignmentVariables['maxLevel']}" )
                    #for j, (C,V,text,words) in enumerate( self.uWalignments, start=1 ):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{j} {self.BBB}_{C}:{V} '{text}'\n    = {words}" )
                        #if j > 8: break
            #if self.BBB == 'GEN': halt
        if loadErrors: self.checkResultsDictionary['Load Errors'] = loadErrors
        #if debugging: dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self._rawLines ); halt
    # end of USFMBibleBook.load
# end of class USFMBibleBook



def briefDemo() -> None:
    """
    Demonstrate reading and processing some USFM Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    def demoFile( name, filename, folder, BBB ):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading {} from {}{}…").format( BBB, filename, f" from {folder}" if BibleOrgSysGlobals.verbosityLevel > 2 else '' ) )
        UBB = USFMBibleBook( name, BBB )
        UBB.load( filename, folder, encoding )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  ID is {!r}".format( UBB.getField( 'id' ) ) )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Header is {!r}".format( UBB.getField( 'h' ) ) )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Main titles are {!r} and {!r}".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UBB )
        UBB.validateMarkers()
        UBBVersification = UBB.getVersification()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBVersification )
        UBBAddedUnits = UBB.getAddedUnits()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBAddedUnits )
        discoveryDict = UBB._discover()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "discoveryDict", discoveryDict )
        UBB.checkBook()
        UBErrors = UBB.getCheckResults()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBErrors )
    # end of demoFile


    from BibleOrgSys.InputOutput import USFMFilenames

    if 1: # Test individual files -- choose one of these or add your own
        name, encoding, testFolder, filename, BBB = "USFM3Test", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/'), '81-COLeng-amp.usfm', 'COL' # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', Path( '/mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "06-JOS.usfm", "JOS" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', Path( '/mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "44-SIR.usfm", "SIR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT102SA.SCP", "SA2" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT15EZR.SCP", "EZR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT41MAT.SCP", "MAT" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT67REV.SCP", "REV" # You can put your test file here
        if os.access( testFolder, os.R_OK ):
            demoFile( name, filename, testFolder, BBB )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Sorry, test folder '{}' doesn't exist on this computer.").format( testFolder ) )

    if 0: # Test a whole folder full of files
        name, encoding, testFolder = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
        #name, encoding, testFolder = "WEB", 'utf-8', Path( '/mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/' ) # You can put your test folder here
        if os.access( testFolder, os.R_OK ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Scanning {} from {}…").format( name, testFolder ) )
            fileList = USFMFilenames.USFMFilenames( testFolder ).getMaximumPossibleFilenameTuples()
            for BBB,filename in fileList:
                demoFile( name, filename, testFolder, BBB )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Sorry, test folder '{}' doesn't exist on this computer.").format( testFolder ) )

    if 0: # Test with translationCore test files
        testFolder = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../ExternalPrograms/usfm-js/__tests__/resources/' )
        for filename in os.listdir( testFolder ):
            if filename.endswith( '.usfm' ):
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nLoading translationCore test file: {filename}…" )
                #filepath = os.path.join( testFolder, filename )
                UBB = USFMBibleBook( 'test', 'TST' )
                UBB.load( filename, testFolder )
# end of USFMBibleBook.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    def demoFile( name, filename, folder, BBB ):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading {} from {}{}…").format( BBB, filename, f" from {folder}" if BibleOrgSysGlobals.verbosityLevel > 2 else '' ) )
        UBB = USFMBibleBook( name, BBB )
        UBB.load( filename, folder, encoding )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  ID is {!r}".format( UBB.getField( 'id' ) ) )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Header is {!r}".format( UBB.getField( 'h' ) ) )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Main titles are {!r} and {!r}".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UBB )
        UBB.validateMarkers()
        UBBVersification = UBB.getVersification()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBVersification )
        UBBAddedUnits = UBB.getAddedUnits()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBAddedUnits )
        discoveryDict = UBB._discover()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "discoveryDict", discoveryDict )
        UBB.checkBook()
        UBErrors = UBB.getCheckResults()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBErrors )
    # end of demoFile


    from BibleOrgSys.InputOutput import USFMFilenames

    if 1: # Test individual files -- choose one of these or add your own
        name, encoding, testFolder, filename, BBB = "USFM3Test", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/'), '81-COLeng-amp.usfm', 'COL' # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', Path( '/mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "06-JOS.usfm", "JOS" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "WEB", 'utf-8', Path( '/mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/'), "44-SIR.usfm", "SIR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT102SA.SCP", "SA2" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT15EZR.SCP", "EZR" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT41MAT.SCP", "MAT" # You can put your test file here
        #name, encoding, testFolder, filename, BBB = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'), "MBT67REV.SCP", "REV" # You can put your test file here
        if os.access( testFolder, os.R_OK ):
            demoFile( name, filename, testFolder, BBB )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Sorry, test folder '{}' doesn't exist on this computer.").format( testFolder ) )

    if 0: # Test a whole folder full of files
        name, encoding, testFolder = "Matigsalug", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
        #name, encoding, testFolder = "WEB", 'utf-8', Path( '/mnt/SSDs/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/' ) # You can put your test folder here
        if os.access( testFolder, os.R_OK ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Scanning {} from {}…").format( name, testFolder ) )
            fileList = USFMFilenames.USFMFilenames( testFolder ).getMaximumPossibleFilenameTuples()
            for BBB,filename in fileList:
                demoFile( name, filename, testFolder, BBB )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Sorry, test folder '{}' doesn't exist on this computer.").format( testFolder ) )

    if 0: # Test with translationCore test files
        testFolder = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../ExternalPrograms/usfm-js/__tests__/resources/' )
        for filename in os.listdir( testFolder ):
            if filename.endswith( '.usfm' ):
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nLoading translationCore test file: {filename}…" )
                #filepath = os.path.join( testFolder, filename )
                UBB = USFMBibleBook( 'test', 'TST' )
                UBB.load( filename, testFolder )
# end of USFMBibleBook.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USFMBibleBook.py
