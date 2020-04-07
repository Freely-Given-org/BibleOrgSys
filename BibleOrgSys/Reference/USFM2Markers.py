#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFM2Markers.py
#
# Module handling Unified Standard Format Markers (USFMs)
#
# Copyright (C) 2011-2020 Robert Hunt
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
Module handling USFM2Markers.
    See http://ubsicap.github.io/usfm/
        (and the old http://paratext.org/about/usfm)

Contains functions:
    removeUSFMCharacterField( marker, originalText, closedFlag )
    replaceUSFMCharacterFields( replacements, originalText )

Contains the singleton class: USFM2Markers
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-04-05' # by RJH
SHORT_PROGRAM_NAME = "USFM2Markers"
PROGRAM_NAME = "USFM2 Markers handler"
PROGRAM_VERSION = '0.75'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals


# STATIC USFM TABLES
OFTEN_IGNORED_USFM_HEADER_MARKERS = ( 'id','ide', 'sts','h', 'toc1','toc2','toc3', 'cl¤', 'rem' )
# NOTE: the following sets include unnumbered markers, e.g., q, as well as q1
USFM_ALL_TITLE_MARKERS = ( 'mt','mt1','mt2','mt3','mt4', 'mte','mte1','mte2','mte3','mte4',
                      'imt','imt1','imt2','imt3','imt4', 'imte','imte1','imte2','imte3','imte4' )
USFM_INTRODUCTION_PARAGRAPH_MARKERS = ( 'ip','ipi', 'im','imi', 'ipq','imq','ipr',
                            'iq','iq1','iq2','iq3','iq4',
                           'iot', 'io','io1','io2','io3','io4', 'ili','ili1','ili2','ili3','ili4',
                           'iex','iqt' ) # Doesn't include ie
USFM_ALL_INTRODUCTION_MARKERS = ( 'imt','imt1','imt2','imt3','imt4', 'imte','imte1','imte2','imte3','imte4',
                            'is','is1','is2','is3','is4', ) + USFM_INTRODUCTION_PARAGRAPH_MARKERS
USFM_ALL_SECTION_HEADING_MARKERS = ( 's','s1','s2','s3','s4', 'is','is1','is2','is3','is4', 'qa' )
USFM_BIBLE_PARAGRAPH_MARKERS = ( 'p','pc','pr', 'm','mi', 'pm','pmo','pmc','pmr', 'cls',
                            'pi','pi1','pi2','pi3','pi4', 'ph','ph1','ph2','ph3','ph4',
                            'q','q1','q2','q3','q4', 'qr','qc', 'qm','qm1','qm2','qm3','qm4',
                            'li','li1','li2','li3','li4' ) # (37) Doesn't include nb and qa and sp -- WHY NOT???
                                                            #   but does include q, qm, li, pi, and ph
USFM_ALL_BIBLE_PARAGRAPH_MARKERS = USFM_INTRODUCTION_PARAGRAPH_MARKERS + USFM_BIBLE_PARAGRAPH_MARKERS

USFM_PRECHAPTER_MARKERS = OFTEN_IGNORED_USFM_HEADER_MARKERS + USFM_ALL_TITLE_MARKERS + USFM_ALL_INTRODUCTION_MARKERS + ('ie',)
USFM_PRINTABLE_MARKERS = ('v','r','ms1',) + USFM_ALL_TITLE_MARKERS + USFM_ALL_INTRODUCTION_MARKERS \
                            + USFM_ALL_SECTION_HEADING_MARKERS + USFM_BIBLE_PARAGRAPH_MARKERS
                        # What about 'b' ???

# The following are used for error checks
USFM3_NEW_PARAGRAPH_MARKERS = ( 'usfm', 'toca', 'po', 'lh', 'lf', 'lim', 'lik', 'liv', 'litl',
                                'qd', 'sd', 'jmp', 'ts', )
USFM3_NEW_CHARACTER_MARKERS = ( 'wa', 'png', 'xta', 'xop', 'rb',
                                'qt-s','qt-e', 'qt1-s','qt1-e', 'qt2-s','qt2-e', 'fw', 'sup', )
USFM3_ALL_NEW_MARKERS = USFM3_NEW_PARAGRAPH_MARKERS + USFM3_NEW_CHARACTER_MARKERS


def removeUSFMCharacterField( marker, originalText, closedFlag ):
    """
    Removes all instances of the marker (if it exists) and its contents from the originalText.

    marker parameter should not contain the backslash or the following space.

    If closedFlag=True, expects a close marker (otherwise does nothing )
    If closedFlag=False, goes to the next marker or end of line.
    If closedFlag=None (unknown), stops at the first of closing marker, next marker, or end of line.
    """
    #print( "removeUSFMCharacterField( {}, {}, {} )".format( originalText, marker, closedFlag ) )
    assert '\\' not in marker and ' ' not in marker and '*' not in marker
    text = originalText
    mLen = len( marker )
    ix = text.find( '\\'+marker+' ' )
    while ix != -1:
        tLen = len( text )
        if closedFlag is None:
            ixEnd = text.find( '\\', ix+mLen+2 )
            if ixEnd == -1: # remove until end of line
                text = text[:ix]
            elif text[ixEnd:].startswith( '\\'+marker+'*' ): # remove the end marker also
                text = text[:ix] + text[ixEnd+mLen+2:]
            else: # leave the next marker in place
                text = text[:ix] + text[ixEnd:]
            #print( "                         ", text ); halt
        elif closedFlag == True:
            ixEnd = text.find( '\\'+marker+'*', ix+mLen+2 )
            if ixEnd == -1:
                logging.error( "removeUSFMCharacterField: no end marker for {!r} in {!r}".format( marker, originalText ) )
                break
            text = text[:ix] + text[ixEnd+mLen+2:]
        elif closedFlag == False:
            ixEnd = text.find( '\\', ix+mLen+2 )
            if ixEnd == -1: # remove until end of line
                text = text[:ix]
            elif ixEnd<tLen-1 and text[ixEnd+1]=='+': # We've hit an embedded marker
                logging.critical( "removeUSFMCharacterField: doesn't handle embedded markers yet with {!r} in {!r}".format( marker, originalText ) )
                if BibleOrgSysGlobals.debugFlag: halt
            else:
                text = text[:ix] + text[ixEnd:]
        ix = text.find( '\\'+marker+' ' )
    return text
# end of removeUSFMCharacterField



def replaceUSFMCharacterFields( replacements, originalText ):
    """
    Makes a series of replacements to a line of USFM text.
        This is designed for USFM character formatting fields that are explicitly closed
            so it doesn't work with footnote or cross-reference fields where
            the next open marker implicitly closes the previous marker.

    Parameter 1 is a list of 3-tuples of the replacements to be made:
        1/ The set of markers
        2/ The replacement text for the opening marker
        3/ The replacement text for the closing marker
    Parameter 2 is the original text.

    Produces warning messages if the opening and close markers don't match.

    Returns the adjusted text.
    """
    text = originalText
    for markers, openReplacement, closeReplacement in replacements:
        for marker in markers:
            assert '\\' not in marker and ' ' not in marker and '*' not in marker

            # Handle the traditional USFM markers
            openMarker, closeMarker = '\\'+marker+' ', '\\'+marker+'*'
            openCount, closedCount = originalText.count( openMarker ), originalText.count( closeMarker )
            if openCount > closedCount:
                logging.warning( "replaceUSFMCharacterFields: missing close marker for {!r} in {!r}".format( openMarker, originalText ) )
            elif openCount < closedCount:
                logging.warning( "replaceUSFMCharacterFields: superfluous {!r} close marker in {!r}".format( closeMarker, originalText ) )
            text = text.replace( openMarker, openReplacement ).replace( closeMarker, closeReplacement )

            # Handle the new v2.4 nested markers
            openMarker, closeMarker = '\\+'+marker+' ', '\\+'+marker+'*'
            openCount, closedCount = originalText.count( openMarker ), originalText.count( closeMarker )
            if openCount > closedCount:
                logging.warning( "replaceUSFMCharacterFields: missing nested close marker for {!r} in {!r}".format( openMarker, originalText ) )
            elif openCount < closedCount:
                logging.warning( "replaceUSFMCharacterFields: superfluous {!r} nested close marker in {!r}".format( closeMarker, originalText ) )
            text = text.replace( openMarker, openReplacement ).replace( closeMarker, closeReplacement )
    return text
# end of replaceUSFMCharacterFields



# Define commonly used sets of footnote and xref markers
footnoteSets = (
    ['fr', 'fr*'],
    ['fr', 'ft'], ['fr', 'ft', 'ft*'],
    ['fr', 'fq'], ['fr', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq'], ['fr', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft'], ['fr', 'fq', 'ft', 'ft*'], \
    ['fr', 'ft', 'fv'], ['fr', 'ft', 'fv', 'fv*'], \
    ['fr', 'fk', 'ft'], ['fr', 'fk', 'ft', 'ft*'], \
    ['fr', 'ft', 'fq', 'ft'], ['fr', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'fv'], ['fr', 'ft', 'fq', 'fv', 'fv*'], \
    ['fr', 'ft', 'ft', 'fq'], ['fr', 'ft', 'ft', 'fq', 'fq*'], \
    ['fr', 'fk', 'ft', 'fq'], ['fr', 'fk', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'ft', 'fq'], ['fr', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft'], ['fr', 'fq', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'fv'], ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'fv', 'fq'], ['fr', 'ft', 'fq', 'fv', 'fq', 'fq*'], \
    ['fr', 'fk', 'ft', 'fq', 'ft'], ['fr', 'fk', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'ft', 'fq', 'ft', 'ft'], ['fr', 'ft', 'fq', 'ft', 'ft', 'ft*'], \
    ['fr', 'ft', 'fv', 'fv*', 'fq'], ['fr', 'ft', 'fv', 'fv*', 'fq', 'fq*'], \
    ['fr', 'ft', 'fv', 'fv*', 'fv'], ['fr', 'ft', 'fv', 'fv*', 'fv', 'fv*'], \
    ['fr', 'ft', 'fq', 'ft', 'fq', 'ft'], ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'fv', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fv', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'fv', 'fv*', 'fq'], ['fr', 'ft', 'fq', 'fv', 'fv*', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'fv', 'fv*', 'fv'], ['fr', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*'], \
    ['fr', 'ft', 'fq', 'ft', 'fv', 'fv', 'fq'], ['fr', 'ft', 'fq', 'ft', 'fv', 'fv', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fv'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fv', 'fv*'], \
    ['fr', 'ft', 'fq', 'fv', 'fq', 'fv', 'fq'], ['fr', 'ft', 'fq', 'fv', 'fq', 'fv', 'fq', 'fq*'], \
    ['fr', 'fk', 'ft', 'fq', 'ft', 'fq', 'ft'], ['fr', 'fk', 'ft', 'fq', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*', 'fv'], ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*'], \
    ['fr', 'ft', 'fq', 'ft', 'fv', 'fv*', 'fq'], ['fr', 'ft', 'fq', 'ft', 'fv', 'fv*', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*', 'ft'], ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*', 'ft', 'ft*'], \
    ['fr', 'ft', 'fq', 'fq', 'fv', 'fv*', 'ft'], ['fr', 'ft', 'fq', 'fq', 'fv', 'fv*', 'ft', 'ft*'], \
    ['fr', 'ft', 'fq', 'fq', 'fv', 'fv*', 'fq'], ['fr', 'ft', 'fq', 'fq', 'fv', 'fv*', 'fq', 'fq*'], \
    ['fr', 'fq', 'fv', 'fv*', 'ft', 'fq', 'fv'], ['fr', 'fq', 'fv', 'fv*', 'ft', 'fq', 'fv', 'fv*'], \
    ['fr', 'ft', 'fk', 'ft', 'fk', 'ft', 'fk', 'ft'], ['fr', 'ft', 'fk', 'ft', 'fk', 'ft', 'fk', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fv'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fv', 'fv*'], \
    ['fr', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq'], ['fr', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft'], ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'fv', 'fq', 'ft', 'fq', 'fv', 'fq'], ['fr', 'fq', 'fv', 'fq', 'ft', 'fq', 'fv', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'ft', 'fv', 'fv*', 'fq', 'ft'], ['fr', 'ft', 'fq', 'ft', 'fv', 'fv*', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fv', 'fq', 'ft', 'fv', 'fq', 'fv', 'fq'], ['fr', 'ft', 'fv', 'fq', 'ft', 'fv', 'fq', 'fv', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'ft*'], \
    ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fv', 'fv*', 'fq', 'ft', 'fv', 'fv*', 'fq'], ['fr', 'ft', 'fv', 'fv*', 'fq', 'ft', 'fv', 'fv*', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft'], ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'ft*'], \
    ['fr', 'ft', 'fq', 'fv', 'fv*', 'ft', 'fq', 'fv', 'fv*', 'fv'], ['fr', 'ft', 'fq', 'fv', 'fv*', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*'], \
    ['fr', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv'], ['fr', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'ft', 'fv', 'fv*', 'fq', 'ft', 'fv', 'fv*', 'fq'], ['fr', 'ft', 'fq', 'ft', 'fv', 'fv*', 'fq', 'ft', 'fv', 'fv*', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq'], ['fr', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*', 'ft', 'fq', 'fv', 'fv*', 'fv'], ['fr', 'fq', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*'], \
    ['fr', 'ft', 'fv', 'fv*', 'fq', 'ft', 'fv', 'fv*', 'fq', 'ft', 'fv', 'fv*', 'fq'], ['fr', 'ft', 'fv', 'fv*', 'fq', 'ft', 'fv', 'fv*', 'fq', 'ft', 'fv', 'fv*', 'fq', 'fq*'], \
    ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq'], ['fr', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq', 'ft', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq'], ['fr', 'ft', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fv', 'fq', 'fq*'], \
    ['fr', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv'], ['fr', 'ft', 'fq', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*', 'fv', 'fv*'],
    )
xrefSets = (
    ['xo', 'xdc'], ['xo', 'xdc', 'xdc*'], \
    ['xo', 'xt'],['xo', 'xt', 'xt*'], \
    ['xo', 'xt', 'xk'], \
    ['xo', 'xt', 'xdc'], ['xo', 'xt', 'xdc*'], \
    ['xo', 'xdc', 'xt'], ['xo', 'xdc', 'xt', 'xt*'], \
    ['xo', 'xt', 'xo', 'xt'], ['xo', 'xt', 'xo', 'xt', 'xt*'], \
    ['xo', 'xt', 'xk', 'xt'], ['xo', 'xt', 'xk', 'xt', 'xt*'], \
    ['xo', 'xt', 'xdc', 'xt'], ['xo', 'xt', 'xdc', 'xt', 'xt*'], \
    ['xo', 'xt', 'xt', 'xo', 'xt'], ['xo', 'xt', 'xt', 'xo', 'xt', 'xt*'], \
    ['xo', 'xt', 'xo', 'xt', 'xdc'], ['xo', 'xt', 'xo', 'xt', 'xdc', 'xdc*'], \
    ['xo', 'xt', 'xo', 'xt', 'xo', 'xt'], ['xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xt*'], \
    ['xo', 'xdc', 'xt', 'xt', 'xo', 'xt'], ['xo', 'xdc', 'xt', 'xt', 'xo', 'xt', 'xt*'], \
    ['xo', 'xt', 'xdc', 'xt', 'xo', 'xt'], ['xo', 'xt', 'xdc', 'xt', 'xo', 'xt', 'xt*'], \
    ['xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt'], ['xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xt*'], \
    ['xo', 'xt', 'xdc', 'xt', 'xo', 'xt', 'xo', 'xt'], ['xo', 'xt', 'xdc', 'xt', 'xo', 'xt', 'xo', 'xt', 'xt*'], \
    ['xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt'], ['xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xt*'], \
    ['xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt'], ['xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xo', 'xt', 'xt*'],
    )
for thisSet in footnoteSets: assert footnoteSets.count(thisSet) == 1 # Check there's no duplicates above
for thisSet in xrefSets: assert xrefSets.count(thisSet) == 1



@singleton # Can only ever have one instance
class USFM2Markers:
    """
    Class for handling USFM2Markers.
    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor:
        """
        self.__DataDict = None # We'll import into this in loadData
    # end of USFM2Markers.__init__


    def loadData( self, XMLFileOrFilepath=None ):
        """ Loads the XML data file and imports it to dictionary format (if not done already). """
        if not self.__DataDict: # We need to load them once -- don't do this unnecessarily
            if XMLFileOrFilepath is None:
                # See if we can load from the pickle file (faster than loading from the XML)
                standardXMLFileOrFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( "USFM2Markers.xml" )
                standardPickleFilepath = BibleOrgSysGlobals.BOS_DERIVED_DATA_FILES_FOLDERPATH.joinpath( "USFM2Markers_Tables.pickle" )
                try:
                    pickleIsNewer = os.stat(standardPickleFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime \
                                and os.stat(standardPickleFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime
                except FileNotFoundError as e:
                    pickleIsNewer = 'xml' in str(e) # Couldn't find xml file -- these aren't included in PyPI package
                # and os.access( standardPickleFilepath, os.R_OK ) \
                # and os.stat(standardPickleFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime \
                # and os.stat(standardPickleFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime: # There's a newer pickle file
                if pickleIsNewer:
                    import pickle
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "Loading pickle file {}…".format( standardPickleFilepath ) )
                    with open( standardPickleFilepath, 'rb') as pickleFile:
                        self.__DataDict = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
                    return self # So this command can be chained after the object creation
            # else: # We have to load the XML (much slower)
            if XMLFileOrFilepath is not None: logging.warning( _("USFM markers are already loaded -- your given filepath of {!r} was ignored").format(XMLFileOrFilepath) )
            from BibleOrgSys.Reference.Converters.USFM2MarkersConverter import USFM2MarkersConverter
            umc = USFM2MarkersConverter()
            umc.loadAndValidate( XMLFileOrFilepath ) # Load the XML (if not done already)
            self.__DataDict = umc.importDataToPython() # Get the various dictionaries organised for quick lookup
        return self # So this command can be chained after the object creation
    # end of USFM2Markers.loadData


    def __str__( self ):
        """
        This method returns the string representation of the USFM markers object.

        @return: the name of a USFM markers object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "USFM Markers object"
        result += ('\n' if result else '') + ' '*indent + _("Number of entries = {}").format( len(self.__DataDict['rawMarkerDict']) )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            indent = 4
            result += ('\n' if result else '') + ' '*indent + _("Number of raw new line markers = {}").format( len(self.__DataDict['newlineMarkersList']) )
            result += ('\n' if result else '') + ' '*indent + _("Number of internal markers = {}").format( len(self.__DataDict["internalMarkersList"]) )
            result += ('\n' if result else '') + ' '*indent + _("Number of note markers = {}").format( len(self.__DataDict["noteMarkersList"]) )
        return result
    # end of USFM2Markers.__str__


    def __len__( self ):
        """ Return the number of available markers. """
        return len(self.__DataDict['combinedMarkerDict'])


    def __contains__( self, marker ):
        """ Returns True or False. """
        return marker in self.__DataDict['combinedMarkerDict']


    def __getitem__( self, keyIndex ):
        """ Returns a marker according to an integer index. """
        return self.__DataDict["numberedMarkerList"][keyIndex]


    def isValidMarker( self, marker ):
        """ Returns True or False. """
        return marker in self.__DataDict['combinedMarkerDict']


    def isNewlineMarker( self, marker ):
        """ Return True or False. """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        return self.toRawMarker(marker) in self.__DataDict['combinedNewlineMarkersList']


    def isInternalMarker( self, marker ):
        """ Return True or False. """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        return self.toRawMarker(marker) in self.__DataDict["internalMarkersList"]


    def isNoteMarker( self, marker ):
        """ Return True or False. """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        return self.toRawMarker(marker) in self.__DataDict["noteMarkersList"]


    def isDeprecatedMarker( self, marker ):
        """ Return True or False. """
        return marker in self.__DataDict["deprecatedMarkersList"]


    def isCompulsoryMarker( self, marker ):
        """ Return True or False. """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        return self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]['compulsoryFlag']


    def isNumberableMarker( self, marker ):
        """ Return True or False. """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        return self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]['highestNumberSuffix'] != 'None'


    def isNestingMarker( self, marker ):
        """ Return True or False. """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        return self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]['nestsFlag']


    def isPrinted( self, marker ):
        """ Return True or False. """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        return self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]['printedFlag']


    def getMarkerClosureType( self, marker ):
        """
        Return 'N', 'O', 'A' for "never", "optional", "always".

        Raises KeyError for an invalid marker.
        """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        closed = self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]['closed']
        #if closed is None: return 'N'
        if closed == "No": return 'N'
        if closed == "Always": return 'A'
        if closed == "Optional": return 'O'
        print( 'msbc {}'.format( closed ))
        raise KeyError # Should be something better here
    # end of USFM2Markers.getMarkerClosureType


    def getMarkerContentType( self, marker ):
        """
        Return "N", "S", "A" for "never", "sometimes", "always".

        Raises KeyError for an invalid marker.
        """
        if marker not in self.__DataDict['combinedMarkerDict']: return False
        hasContent = self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]["hasContent"]
        #if hasContent is None: return "N"
        if hasContent == "Never": return "N"
        if hasContent == "Always": return "A"
        if hasContent == "Sometimes": return "S"
        print( 'mshc {}'.format( hasContent ))
        raise KeyError # Should be something better here
    # end of USFM2Markers.getMarkerContentType


    def toRawMarker( self, marker ):
        """ Returns a marker without numerical suffixes, i.e., s1->s, q1->q, etc. """
        return self.__DataDict['combinedMarkerDict'][marker]


    def toStandardMarker( self, marker ):
        """ Returns a standard marker, i.e., s->s1, q->q1, etc. """
        if marker in self.__DataDict['conversionDict']: return self.__DataDict['conversionDict'][marker]
        #else
        if marker in self.__DataDict['combinedMarkerDict']: return marker
        #else must be something wrong
        raise KeyError
    # end of USFM2Markers.toStandardMarker


    def markerOccursIn( self, marker ):
        """ Return a short string, e.g. "Introduction", "Text". """
        return self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]["occursIn"]


    def getMarkerEnglishName( self, marker ):
        """ Returns the English name for a marker.
                Use getOccursInList() to get a list of all possibilities. """
        return self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]["nameEnglish"]


    def getMarkerDescription( self, marker ):
        """ Returns the description for a marker (or None). """
        return self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]["description"]


    def getOccursInList( self ):
        """ Returns a list of strings which markerOccursIn can return. """
        oiList = []
        for marker in self.__DataDict['rawMarkerDict']:
            occursIn = self.__DataDict['rawMarkerDict'][marker]['occursIn']
            if occursIn not in oiList: oiList.append( occursIn )
        return oiList
    # end of USFM2Markers.getOccursInList


    def getNewlineMarkersList( self, option ):
        """
        Returns a list of all possible new line markers depending on the parameter:
            'Raw'
            'Numbered'
            'Combined'
            'CanonicalText'
        """
        assert option in ('Raw','Numbered','Combined','CanonicalText')
        if option=='Combined': return self.__DataDict['combinedNewlineMarkersList'] # Includes q, q1, q2, …
        elif option=='Raw': return self.__DataDict['newlineMarkersList'] # Doesn't include q1, q2, …
        elif option=='Numbered': return self.__DataDict['numberedNewlineMarkersList'] # Doesn't include q
        elif option=='CanonicalText':
            return [m for m in self.__DataDict['numberedNewlineMarkersList'] if self.markerOccursIn(m)=='Canonical Text'] # Doesn't include id, h1, b, q
    # end of getNewlineMarkersList


    def getInternalMarkersList( self ):
        """
        Returns a list of all possible internal markers.
        This includes character markers, but not footnote and xref markers.
        """
        return self.__DataDict["internalMarkersList"]
    # end of USFM2Markers.getInternalMarkersList


    def getCharacterMarkersList( self, includeBackslash=False, includeEndMarkers=False, includeNestedMarkers=False, expandNumberableMarkers=False ):
        """
        Returns a list of all possible character markers.
        These are fields that need to be displayed inline with the text, albeit with special formatting.
        This excludes footnote and xref markers.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "getCharacterMarkersList( {}, {}, {}, {} )".format( includeBackslash, includeEndMarkers, includeNestedMarkers, expandNumberableMarkers ) )
        result = []
        for marker in self.__DataDict["internalMarkersList"]:
            #print( marker, self.markerOccursIn(marker) )
            if self.markerOccursIn(marker) in ("Text","Canonical Text","Poetry","Table row","Introduction",):
                adjMarker = '\\'+marker if includeBackslash else marker
                result.append( adjMarker )
                if includeNestedMarkers:
                    nestedMarker = '\\+'+marker if includeBackslash else '+'+marker
                    result.append( nestedMarker )
                if includeEndMarkers:
                    assert self.getMarkerClosureType( marker )=='A' or self.markerOccursIn(marker)=="Table row"
                    result.append( adjMarker + '*' )
                    if includeNestedMarkers: result.append( nestedMarker + '*' )
                if expandNumberableMarkers and self.isNumberableMarker( marker ):
                    for digit in range(1, int(self.__DataDict['rawMarkerDict'][self.toRawMarker(marker)]['highestNumberSuffix'])+1):
                        str_digit = str(digit)
                        result.append( adjMarker+str_digit )
                        if includeNestedMarkers: result.append( nestedMarker+str_digit )
                        if includeEndMarkers:
                            result.append( adjMarker + str_digit + '*' )
                            if includeNestedMarkers: result.append( nestedMarker + str_digit + '*' )
        return result
    # end of USFM2Markers.getCharacterMarkersList


    def getNoteMarkersList( self ):
        """
        Returns a list of all possible note markers.
            This includes figure, footnote and xref markers.
            These are fields that should not normally be displayed inline with the text.
        """
        return self.__DataDict["noteMarkersList"]
    # end of USFM2Markers.getNoteMarkersList


    def getTypicalNoteSets( self, select='All' ):
        """ Returns a container of typical footnote and xref sets. """
        if select=='fn': return footnoteSets
        elif select=='xr': return xrefSets
        elif select=='All': return footnoteSets + xrefSets
    # end of USFM2Markers.getTypicalNoteSets


    def getMarkerListFromText( self, text, includeInitialText=False, verifyMarkers=False ):
        """
        Given a text, return a dict of the actual markers
            (along with their positions and other useful derived information).

        Returns a list of seven-tuples containing:
            1: marker or None for initial text (if includeInitialText)
            2: indexOfBackslashCharacter in text string
            3: nextSignificantChar
                ' ' for normal opening marker
                '+' for nested opening marker
                '-' for nested closing marker
                '*' for normal closing marker
                '' for end of line.
            4: full marker text including the backslash (can be used to search for)
            5: character context for the following text (list of markers, including this one)
            6: index (to the result list of this function) of the
                marker which closes this opening marker (or None if it's not an opening marker)
            7: text field from the marker until the next USFM
                but any text preceding the first USFM is not returned anywhere unless includeInitialText is set.
        """
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "USFM2Markers.getMarkerListFromText( {}, {} )".format( repr(text), verifyMarkers ) )
        if not text: return []
        firstResult = [] # A list of 4-tuples containing ( 1, 2, 3, 4 ) above
        textLength = len( text )
        ixBS = text.find( '\\' )
        while ixBS != -1: # Find backslashes
            #print( ixBS, firstResult )
            marker = ''
            iy = ixBS + 1
            if iy<textLength:
                c1 = text[iy]
                if c1==' ': logging.error( _("USFM2Markers.getMarkerListFromText found invalid '\\' in {!r}").format( text ) )
                elif c1=='\\': logging.error( _("USFM2Markers.getMarkerListFromText found invalid '\\\\' in {!r}").format( text ) )
                elif c1=='*': logging.error( _("USFM2Markers.getMarkerListFromText found invalid '\\*' in {!r}").format( text ) )
                elif c1=='+': # it's a nested USFM 2.4 marker
                    iy += 1 # skip past the +
                    if iy<textLength:
                        c1 = text[iy]
                        if c1==' ': logging.error( _("USFM2Markers.getMarkerListFromText found invalid '\\+' in {!r}").format( text ) )
                        elif c1=='*': logging.error( _("USFM2Markers.getMarkerListFromText found invalid '\\+*' in {!r}").format( text ) )
                        elif c1=='+': logging.error( _("USFM2Markers.getMarkerListFromText found invalid '\\++' in {!r}").format( text ) )
                        else: # it's probably a letter which is part of the actual marker
                            marker += c1
                            iy += 1
                            while iy < textLength:
                                c = text[iy]
                                if c==' ': firstResult.append( (marker,ixBS,'+','\\+'+marker+' ') ); break
                                elif c=='*': firstResult.append( (marker,ixBS,'-','\\+'+marker+'*') ); break
                                else: # it's probably ok
                                    marker += c
                                iy += 1
                            else: firstResult.append( (marker,ixBS,'+','\\+'+marker) ) # How do we indicate the end of line here?
                    else: # it was a backslash then plus at the end of the line
                        firstResult.append( ('\\',ixBS,'+','\\+') )
                        logging.error( _("USFM2Markers.getMarkerListFromText found invalid '\\+' at end of {!r}").format( text ) )
                else: # it's probably a letter which is part of the actual marker
                    marker += c1
                    iy += 1
                    while iy < textLength:
                        c = text[iy]
                        if c==' ': firstResult.append( (marker,ixBS,' ','\\'+marker+' ') ); break
                        elif c=='*': firstResult.append( (marker,ixBS,'*','\\'+marker+'*') ); break
                        else: # it's probably ok
                            marker += c
                        iy += 1
                    else: firstResult.append( (marker,ixBS,'','\\'+marker) )
            else: # it was a backslash at the end of the line
                firstResult.append( ('\\',ixBS,'','\\') )
                logging.error( _("USFM2Markers.getMarkerListFromText found invalid '\\' at end of {!r}").format( text ) )
            ixBS = text.find( '\\', ixBS+1 )
        if debuggingThisModule:
            print("Got first result:", firstResult )

        # Now that we have found all the markers and where they are, get the text fields between them
        rLen = len( firstResult )
        secondResult = []  # A list of 6-tuples containing ( 1, 2, 3, 4, 5, 7 ) above
        cx = []
        for j, (m, ix, x, mx) in enumerate(firstResult):
            if self.isNewlineMarker( m ): cx = [] #; print( "rst", cx )
            elif x==' ' or x=='': # Open marker in line or at end of line
                cx = [m] #; print( "set", cx )
            elif x=='+': cx.append( m ) #; print( "add", m, cx )
            elif x=='-': cx.pop() #; print( "del", m, cx )
            elif x=='*': cx = [] #; print( "clr", cx )
            else:
                print( "USFM2Markers.getMarkerListFromText: Shouldn't happen", firstResult, secondResult,
                      '\n', j, repr(m), ix, repr(x), mx, cx )
                if BibleOrgSysGlobals.debugFlag: halt
            if j>= rLen-1: tx = text[ix+len(mx):]
            else: tx=text[ix+len(mx):firstResult[j+1][1]]
            #print( 'second', j, m, ix, repr(x), repr(mx), cx, repr(tx) )
            secondResult.append( (m, ix, x, mx, cx[:], tx,) )

        # And now find where they are closed (the index to the result array, not to the text string)
        thirdResult = [] # The near-final list of 7-tuples (inserting #6 here)
        for j, (m, ix, x, mx, cx, tx) in enumerate(secondResult):
            ixEnd = None
            if x in (' ','+') and len(cx)>0: # i.e., a character start marker
                # Find where this marker is closed
                cxi = len(cx) - 1
                assert cx[cxi] == m
                for k in range( j+1, rLen ):
                    m2, ix2, x2, mx2, cx2, tx2 = secondResult[k]
                    if len(cx2)<=cxi or cx2[cxi] != m: ixEnd = k; break
            #print( 'final', j, m, ix, repr(x), repr(mx), cx, repr(tx), ixEnd )
            thirdResult.append( (m, ix, x, mx, cx[:], ixEnd, tx,) )

        finalResult = thirdResult # The final list of 7-tuples
        if thirdResult and includeInitialText:
            ix1 = thirdResult[0][1] # index of first marker in text
            if ix1 != 0:
                finalResult = [] # The final list of 7-tuples (inserting a new entry #0 below)
                finalResult.append( (None,0,None,None,None,1,text[:ix1]) )
                for m, ix, x, mx, cx[:], ixEnd, tx in thirdResult: # Shift the end index (#6) by one
                    finalResult.append( (m, ix, x, mx, cx[:], None if ixEnd is None else ixEnd+1, tx,) )

        #if finalResult: print( finalResult )
        if verifyMarkers:
            for j, (m, ix, x, mx, cx, ixEnd, tx,) in enumerate(finalResult):
                #print( 'verify', j, m, ix, repr(x), repr(mx), cx, ixEnd, repr(tx) )
                assert ix < textLength
                assert x in (' ','+','-','*','',) or ( includeInitialText and j==0 and x is None )
                if m is None:
                    assert j==0 and ix==0 and x is None
                else:
                    if j == 0:
                        if not self.isNewlineMarker( m ): logging.error( _("USFM2Markers.getMarkerListFromText found possible invalid first marker {!r} in {!r}").format( m, text ) )
                    elif not self.isInternalMarker( m ): logging.error( _("USFM2Markers.getMarkerListFromText found possible invalid marker {!r} at position {} in {!r}").format( m, j+1, text ) )

        return finalResult
    # end of USFM2Markers.getMarkerListFromText


    # This function is faulty and not actually used except in the demo below
    def XXXgetMarkerDictFromText( self, text, includeInitialText=False, verifyMarkers=False ):
        """
        Given a text, return a dict of the actual markers
            (along with their positions and other useful derived information).

        Returns a dictionary of six-tuples containing:
            key: marker or None for initial text (if includeInitialText)
            1: indexOfBackslashCharacter in text string
            2: nextSignificantChar
                ' ' for normal opening marker
                '+' for nested opening marker
                '-' for nested closing marker
                '*' for normal closing marker
                '' for end of line.
            3: full marker text including the backslash (can be used to search for)
            4: character context for the following text (list of markers, including this one)
            5: index (to the result list of this function) of the
                marker which closes this opening marker (or None if it's not an opening marker)
            6: STRIPPED text field from the marker until the next USFM
                but any text preceding the first USFM is not returned anywhere unless includeInitialText is set.

        NOTE: Does not work if text contains any duplicated markers
        NOTE: text is stripped in this function
        """
        myList = self.getMarkerListFromText( text, includeInitialText, verifyMarkers )
        myDict = {}
        for marker, ixBS, nextSignificantChar, fullMarkerText, context, ixEnd, txt in myList:
            if marker in myDict: logging.critical( "USFM2Markers.getMarkerDictFromText is losing (overwriting) information for repeated {} fields in {}".format( marker, repr(text) ) )
            myDict[marker] = (ixBS, nextSignificantChar, fullMarkerText, context, ixEnd, txt.strip())
        return myDict
    # end of USFM2Markers.getMarkerDictFromText
# end of USFM2Markers class



def demo() -> None:
    """
    Demonstration program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    # Demo the USFM2Markers object
    um = USFM2Markers().loadData() # Doesn't reload the XML unnecessarily :)
    print( um ) # Just print a summary
    print( 'c' in um, 'p' in um, 'tr' in um )
    print( "\nMarkers can occur in", um.getOccursInList() )
    pm = um.getNewlineMarkersList( 'Raw' )
    print( "\nRaw New line markers are", len(pm), pm )
    pm = um.getNewlineMarkersList( 'Numbered' )
    print( "\nNumbered New line markers are", len(pm), pm )
    for m in pm:
        print( m, um.markerOccursIn( m ) )
    pm = um.getNewlineMarkersList( 'Combined' )
    print( "\nCombined New line markers are", len(pm), pm )
    pm = um.getNewlineMarkersList( 'CanonicalText' )
    print( "\nCanonical text New line markers are", len(pm), pm )
    im = um.getInternalMarkersList()
    print( "\nInternal (character) markers are", len(im), im )

    cm = um.getCharacterMarkersList()
    print( "\nCharacter markers (standard) are", len(cm), cm )
    cm = um.getCharacterMarkersList( includeNestedMarkers=True )
    print( "\nCharacter markers (incl. nested) are", len(cm), cm )

    nm = um.getNoteMarkersList()
    print( "\nNote markers are", len(nm), nm )
    for m in ('ab', 'h', 'toc1', 'toc4', 'toc5', 'q', 'q1', 'q2', 'q3', 'q4', 'q5', 'p', 'p1', 'P', 'f', 'f1', 'f*' ):
        print( _("{} is {}a valid marker").format( m, "" if um.isValidMarker(m) else _("not")+' ' ) )
        if um.isValidMarker(m):
            print( '  ' + "{}: {}".format( um.getMarkerEnglishName(m), um.getMarkerDescription(m) ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( '  ' + _("Compulsory:{}, Numberable:{}, Occurs in: {}").format( um.isCompulsoryMarker(m), um.isNumberableMarker(m), um.markerOccursIn(m) ) )
                print( '  ' + _("{} is {}a new line marker").format( m, "" if um.isNewlineMarker(m) else _("not")+' ' ) )
                print( '  ' + _("{} is {}an internal (character) marker").format( m, "" if um.isInternalMarker(m) else _("not")+' ' ) )
    for text in ('This is a bit of plain text',
                 '\\v 1 This is some \\it italicised\\it* text.',
                 '\\v 2 This \\it is\\it* \\bd more\\bd* complicated.\\f + \\fr 2 \\ft footnote.\\f*',
                 '\\v 3 This \\add contains \\+it embedded\\+it* codes\\add* with everything closed separately.',
                 '\\v 4 This \\add contains \\+it embedded codes\\+it*\\add* with an simultaneous closure of the two fields.',
                 '\\v 5 This \\add contains \\+it embedded codes\\add* with an assumed closure of the inner field.',
                 '\\v 6 This \\add contains \\+it embedded codes with all closures missing.',
                 '- \\xo 1:3: \\xt 2Kur 4:6.', # A cross-reference
                 '\\v 7 \\wj \+nd Jesus said \+add this \+em nested\+em*\+add*\+nd* \+bd 3 levels\+bd*.\wj* maybe.'
                 ):
        print( "\nFor text {!r} got markers:".format( text ) )
        print( "         A-L {}".format( um.getMarkerListFromText( text, verifyMarkers=True ) ) )
        print( "         B-L {}".format( um.getMarkerListFromText( text, includeInitialText=True ) ) )
        print( "         C-L {}".format( um.getMarkerListFromText( text, includeInitialText=True, verifyMarkers=True ) ) )
        #print( "         A-D {}".format( um.getMarkerDictFromText( text, verifyMarkers=True ) ) )
        #print( "         B-D {}".format( um.getMarkerDictFromText( text, includeInitialText=True ) ) )
        #print( "         C-D {}".format( um.getMarkerDictFromText( text, includeInitialText=True, verifyMarkers=True ) ) )


    text = "\\v~ \\x - \\xo 12:13 \\xt Cross \wj \wj*reference text.\\x*Main \\add actual\\add* verse text.\\f + \\fr 12:13\\fr* \\ft with footnote.\\f*"
    print( "\nFor text: {!r}".format( text ) )
    print( "  remove whole xref = {!r}".format( removeUSFMCharacterField( 'x', text, closedFlag=True ) ) )
    print( "  remove xo = {!r}".format( removeUSFMCharacterField( 'xo', text, closedFlag=False ) ) )
    print( "  remove xref part = {!r}".format( removeUSFMCharacterField( 'x', text, closedFlag=None ) ) )
    print( "  remove fr = {!r}".format( removeUSFMCharacterField( 'fr', text, closedFlag=None ) ) )
    print( "  remove ft = {!r}".format( removeUSFMCharacterField( 'ft', text, closedFlag=None ) ) )
    print( "  remove ft = {!r}".format( removeUSFMCharacterField( 'ft', text, closedFlag=False ) ) )
    print( "  remove wj = {!r}".format( removeUSFMCharacterField( 'wj', text, closedFlag=True ) ) )

    print( "\nFor text: {!r}".format( text ) )
    replacements = ( (('add',),'<span>','</span>'), (('wj',),'<i>','</i>'), )
    print( "  replace = {!r}".format( replaceUSFMCharacterFields( replacements, text ) ) )
# end of demo

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USFM2Markers.py
