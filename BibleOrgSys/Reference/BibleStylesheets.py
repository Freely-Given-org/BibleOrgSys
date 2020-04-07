#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleStylesheets.py
#
# Module handling Bible (including Paratext) stylesheets
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
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-10-09' # by RJH
SHORT_PROGRAM_NAME = "BibleStylesheets"
PROGRAM_NAME = "Bible stylesheet handler"
PROGRAM_VERSION = '0.16'
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
from BibleOrgSys import BibleOrgSysGlobals
#from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys.InputOutput import SFMFile



#self.textBox.tag_configure( 'verseNumberFormat', foreground='blue', font='helvetica 8', relief='raised', offset='3' )
#self.textBox.tag_configure( 'versePreSpaceFormat', background='pink', font='helvetica 8' )
#self.textBox.tag_configure( 'versePostSpaceFormat', background='pink', font='helvetica 4' )
#self.textBox.tag_configure( 'verseTextFormat', font='sil-doulos 12' )
#self.textBox.tag_configure( 'otherVerseTextFormat', font='sil-doulos 9' )
#self.textBox.tag_configure( 'heading1Format', foreground='red', font='sil-doulos 10' )
#self.textBox.tag_configure( 'verseText', background='yellow', font='helvetica 14 bold', relief='raised' )
#"background", "bgstipple", "borderwidth", "elide", "fgstipple", "font", "foreground", "justify", "lmargin1",
#"lmargin2", "offset", "overstrike", "relief", "rmargin", "spacing1", "spacing2", "spacing3",
#"tabs", "tabstyle", "underline", and "wrap".
INDENT_SIZE = 12

DEFAULT_FONTNAME = 'helvetica'
DEFAULT_HEBREW_FONTNAME = 'Ezra' # 'Ezra SIL' seems to fail later when used in a text box

VERSENUMBER_FONTSIZE = 6
CURRENT_VERSE_FONTSIZE = 12
CHAPTERNUMBER_FONTSIZE = 13
DEFAULT_FONTSIZE = 9
HEADING_FONTSIZE = 11
SUBHEADING_FONTSIZE = HEADING_FONTSIZE - 1
TITLE_FONTSIZE = HEADING_FONTSIZE + 2

VERSENUMBER_COLOUR = 'blue'
CHAPTERNUMBER_COLOUR = 'orange'
HEADING_COLOUR = 'red'
SUBHEADING_COLOUR = 'sienna1'
SECTION_REFERENCE_COLOUR = 'green'
EXTRA_COLOUR = 'royalBlue1'

SUPERSCRIPT_OFFSET = '4'

# NOTE: Should we add fields from "leadingText", "trailingText" ???

# These are the styles for formatted mode
# Asterisk in front of a tag name indicates the currently selected verse
# Hash sign after a tag name indicates "unformatted" mode
DEFAULT_STYLE_DICT = { # earliest entries have the highest priority
# The following fields from InternalBible all contain their own (self-contained) text (in _processedLines)
# File beginning
    'id': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'firebrick1', },
    'ide': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'tan1', },
    'h': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'foreground':'green4', },
    'rem': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'foreground':'lightBlue', },
    'toc1': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'ivory2', },
    'toc2': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'ivory3', },
    'toc3': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'ivory4', },
# Our added fields
    'intro': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'lightYellow', },
    'chapters': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'lightYellow', },
# Headings
    'mt1': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, TITLE_FONTSIZE ), 'foreground':'gold', 'justify':'center', },
    'mt2': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, TITLE_FONTSIZE ), 'foreground':'gold2', 'justify':'center', },
    'mt3': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, TITLE_FONTSIZE ), 'foreground':'gold3', 'justify':'center', },
    'mt4': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, TITLE_FONTSIZE ), 'foreground':'gold4', 'justify':'center', },
    's1': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    's2': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    's3': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    's4': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    'ms1': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    'ms2': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    'ms3': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    'ms4': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    'cl': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
# Other
    'd': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, SUBHEADING_FONTSIZE ), 'foreground':SUBHEADING_COLOUR, },
    'sp': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, SUBHEADING_FONTSIZE ), 'foreground':EXTRA_COLOUR, },
    'c': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, CHAPTERNUMBER_FONTSIZE ), 'foreground':CHAPTERNUMBER_COLOUR, },
    'r': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':SECTION_REFERENCE_COLOUR, 'justify':'center', },
    'mr': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':SECTION_REFERENCE_COLOUR, 'justify':'center', },
    'sr': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':SECTION_REFERENCE_COLOUR, 'justify':'center', },
    'c#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, CHAPTERNUMBER_FONTSIZE ), 'foreground':CHAPTERNUMBER_COLOUR, },
    'c~': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, CHAPTERNUMBER_FONTSIZE ), 'foreground':CHAPTERNUMBER_COLOUR, },
    'v': { 'font':'{} {}'.format( DEFAULT_FONTNAME, VERSENUMBER_FONTSIZE ), 'foreground':VERSENUMBER_COLOUR, 'offset':SUPERSCRIPT_OFFSET, },

# Introduction
    'iq1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':1*INDENT_SIZE, 'lmargin2':1*INDENT_SIZE, },
    'iq2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':2*INDENT_SIZE, 'lmargin2':2*INDENT_SIZE, },
    'iq3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':3*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    'iq4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':4*INDENT_SIZE, 'lmargin2':4*INDENT_SIZE, },
    '*iq1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':1*INDENT_SIZE, 'lmargin2':1*INDENT_SIZE, },
    '*iq2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':2*INDENT_SIZE, 'lmargin2':2*INDENT_SIZE, },
    '*iq3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':3*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    '*iq4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':4*INDENT_SIZE, 'lmargin2':4*INDENT_SIZE, },

# The next two should theoretically never be used in formatted Bibles
#  (because v~ fields should take on the previous paragraph tag)
    'v~': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), },
    '*v~': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'lightYellow', },

# The following paragraph level fields can contain text, or can influence the next v~/p~ text
# These are for formatted view
    'p': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':1*INDENT_SIZE, 'lmargin2':0*INDENT_SIZE, },
    '*p': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':1*INDENT_SIZE, 'lmargin2':0*INDENT_SIZE, },
    'q1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':1*INDENT_SIZE, 'lmargin2':1*INDENT_SIZE, },
    'q2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':2*INDENT_SIZE, 'lmargin2':2*INDENT_SIZE, },
    'q3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':3*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    'q4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':4*INDENT_SIZE, 'lmargin2':4*INDENT_SIZE, },
    '*q1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':1*INDENT_SIZE, 'lmargin2':1*INDENT_SIZE, 'background':'yellow', },
    '*q2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':2*INDENT_SIZE, 'lmargin2':2*INDENT_SIZE, },
    '*q3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':3*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    '*q4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':4*INDENT_SIZE, 'lmargin2':4*INDENT_SIZE, },
    'm': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':0*INDENT_SIZE, 'lmargin2':0*INDENT_SIZE, },
    '*m': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':0*INDENT_SIZE, 'lmargin2':0*INDENT_SIZE, },
    'mi': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ),  'background':'pink', 'lmargin1':1*INDENT_SIZE, 'lmargin2':1*INDENT_SIZE, },
    '*mi': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ),  'background':'pink', 'lmargin1':1*INDENT_SIZE, 'lmargin2':1*INDENT_SIZE, },
    'pi1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'pink', 'lmargin1':2*INDENT_SIZE, 'lmargin2':1*INDENT_SIZE, },
    'pi2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'purple', 'lmargin1':3*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    'pi3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'green', 'lmargin1':4*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    'pi4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'brown', 'lmargin1':5*INDENT_SIZE, 'lmargin2':4*INDENT_SIZE, },
    '*pi1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'pink', 'lmargin1':2*INDENT_SIZE, 'lmargin2':1*INDENT_SIZE, },
    '*pi2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'purple', 'lmargin1':3*INDENT_SIZE, 'lmargin2':2*INDENT_SIZE, },
    '*pi3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'green', 'lmargin1':4*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    '*pi4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'brown', 'lmargin1':5*INDENT_SIZE, 'lmargin2':4*INDENT_SIZE, },

# Lists (for formatted view)
    'li1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':1*INDENT_SIZE, 'lmargin2':2*INDENT_SIZE, },
    '*li1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':1*INDENT_SIZE, 'lmargin2':2*INDENT_SIZE, },
    'li2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':2*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    '*li2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':2*INDENT_SIZE, 'lmargin2':3*INDENT_SIZE, },
    'li3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':3*INDENT_SIZE, 'lmargin2':4*INDENT_SIZE, },
    '*li3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':3*INDENT_SIZE, 'lmargin2':4*INDENT_SIZE, },
    'li4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'lmargin1':4*INDENT_SIZE, 'lmargin2':5*INDENT_SIZE, },
    '*li4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'lmargin1':4*INDENT_SIZE, 'lmargin2':5*INDENT_SIZE, },


# These are the styles for unformatted mode that are different from above
# Headings (for unformatted view)
    'mt1#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, TITLE_FONTSIZE ), 'foreground':'gold', },
    'mt2#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, TITLE_FONTSIZE ), 'foreground':'gold2', },
    'mt3#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, TITLE_FONTSIZE ), 'foreground':'gold3', },
    'mt4#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, TITLE_FONTSIZE ), 'foreground':'gold4', },
    's1#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },
    's2#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },
    's3#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },
    's4#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },
    'ms1#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },
    'ms2#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },
    'ms3#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },
    'ms4#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },
    'cl#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, },

# Other (for unformatted view)
    'r#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':SECTION_REFERENCE_COLOUR, },
    'mr#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':SECTION_REFERENCE_COLOUR, },
    'sr#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':SECTION_REFERENCE_COLOUR, },

# Paragraph level fields can contain text, or can influence the next v~ text (for unformatted view)
    'p#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), },
    '*p#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), },
    'q1#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), },
    'q2#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), },
    'q3#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), },
    'q4#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), },
    '*q1#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), },
    '*q2#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), },
    '*q3#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), },
    '*q4#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), },
    'mi#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ),  'background':'pink', },
    '*mi#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ),  'background':'pink', },
    'pi1#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'pink', },
    'pi2#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'purple', },
    'pi3#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'green', },
    'pi4#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'brown', },
    '*pi1#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'pink', },
    '*pi2#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'purple', },
    '*pi3#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'green', },
    '*pi4#': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'brown', },

# Lines without markers (continuation lines)
    '###': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'foreground':'blue', },

# Hebrew interlinear fields
    'WordRef': { 'font':'{} {}'.format( DEFAULT_HEBREW_FONTNAME, DEFAULT_FONTSIZE ) },
    'HebWord': { 'font':'{} {}'.format( DEFAULT_HEBREW_FONTNAME, DEFAULT_FONTSIZE + 4 ), 'foreground':'brown', },
    'HebStrong': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), },
    'HebMorph': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), },
    'HebGenericGloss': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE + 2 ), 'foreground':'green', },
    'HebSpecificGloss': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE + 2 ), 'foreground':'orange', },
    'WordRefSelected': { 'font':'{} {}'.format( DEFAULT_HEBREW_FONTNAME, DEFAULT_FONTSIZE + 1 ) },
    'HebWordSelected': { 'font':'{} {}'.format( DEFAULT_HEBREW_FONTNAME, CURRENT_VERSE_FONTSIZE + 4 ), 'background':'yellow', },
    'HebStrongSelected': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'yellow', },
    'HebMorphSelected': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'yellow', },
    'HebGenericGlossSelected': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE + 2 ), 'background':'yellow', },
    'HebSpecificGlossSelected': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE + 2 ), 'background':'yellow', },
    }



class BibleStylesheet():
    """
    Class to load a Bible stylesheet into a dictionary.
    """
    def __init__( self ):
        """
        """
        self.dataDict = None
        self.filepath = None
        self.smallestSize = self.largestSize = self.markerList = self.markerSets = None
        self.name = None
        self.recordsDB = None
    # end of BibleStylesheet.__init__


    def loadDefault( self ):
        """
        Load the above styles
            and copy any unformatted styles not explicitly declared.
        """
        self.dataDict = DEFAULT_STYLE_DICT
        self.name = 'Default'

        for marker,style in self.dataDict.copy().items():
            if marker[0]!='*' and marker[-1]!='#':
                if marker+'#' not in self.dataDict:
                    self.dataDict[marker+'#'] = style

        self.validate()
        return self  # So this command can be chained after the object creation
    # end of BibleStylesheet.loadDefault


    def load( self, sourceFolder, filename ):
        """
        """
        self.sourceFolder = sourceFolder
        self.filename = filename
        assert os.path.exists( self.sourceFolder )
        assert os.path.exists( self.sourceFolder )
        self.filepath = os.path.join( self.sourceFolder, self.filename )
        assert os.path.exists( self.filepath )
        assert os.path.exists( self.filepath )
        self.name = os.path.splitext( self.filename )[0]

        recordsDB = SFMFile.SFMRecords()
        recordsDB.read( self.filepath, 'Marker' ) #, encoding=self.encoding )
        #print( "\nRecords", recordsDB.records )
        self.smallestSize, self.largestSize, self.markerList, self.markerSets = recordsDB.analyze()
        self.dataDict = recordsDB.copyToDict( "dict" )
        #print( "\nData", self.dataDict )
        self.validate()
        return self  # So this command can be chained after the object creation
    # end of BibleStylesheet.load


    def validate( self ):
        """
        """
        from BibleOrgSys.Internals.InternalBibleInternals import BOS_ALL_ADDED_MARKERS
        for USFMMarker, styleData in self.dataDict.items():
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( _("validate"), USFMMarker, styleData )
            if USFMMarker.startswith( 'Heb' ) or USFMMarker.startswith( 'WordRef' ): continue
            if USFMMarker in ( '###', ): continue # ignore
            if USFMMarker[0] == '*': USFMMarker = USFMMarker[1:] # Remove any leading asterisk for the check
            if USFMMarker[-1] == '#': USFMMarker = USFMMarker[:-1] # Remove any trailing hash for the check
            #print( USFMMarker )
            assert USFMMarker in BibleOrgSysGlobals.loadedUSFMMarkers or USFMMarker in BOS_ALL_ADDED_MARKERS
    # end of BibleStylesheet.load


    def importParatextStylesheet( self, folder, filename:str, encoding:str='utf-8' ) -> None:
        """
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Importing {} Paratext stylesheet…".format( filename ) )
        PTSS = ParatextStylesheet().load( folder, filename, encoding )
        self.name = PTSS.name
        self.filepath = PTSS.filepath
        self.dataDict = {}
        for marker in BibleOrgSysGlobals.loadedUSFMMarkers:
            #print( marker )
            try: PTFormatting = PTSS.getDict( marker )
            except KeyError: PTFormatting = None # Just ignore the error
            if PTFormatting:
                formatSpecification = {}
                for field, value in PTFormatting.items():
                    #print( marker, field, repr(value) )
                    formatSpecification[field] = value
                self.dataDict[marker] = formatSpecification
            elif BibleOrgSysGlobals.debugFlag: print( "USFM {} marker not included in {} Paratext stylesheet".format( marker, filename ) )
            #export the marker
    # end of BibleStylesheet.importParatextStylesheet

    def __eq__( self, other ):
        if type( other ) is type( self ): return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other): return not self.__eq__(other)

    def __len__( self ):
        if self.recordsDB: return len( self.recordsDB.records )
        return 0
    # end of BibleStylesheet.__len__

    def __str__( self ):
        """
        This method returns the string representation of a USFM stylesheet object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleStylesheet object"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        if self.name: result += ('\n' if result else '') + "  Name: " + self.name
        if self.filepath: result += ('\n' if result else '') + "  From: " + self.filepath
        if self.dataDict:
            result += ('\n' if result else '') + "  Number of records = " + str( len(self.dataDict) )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            if self.smallestSize:
                result += ('\n' if result else '') + "  Smallest record size: {} markers".format( self.smallestSize )
            if self.largestSize:
                result += ('\n' if result else '') + "  Largest record size: {} markers".format( self.largestSize )
            if self.markerList: result += ('\n' if result else '') + "  Marker list: {}".format( self.markerList )
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                if self.markerSets: result += ('\n' if result else '') + "  Marker sets: {}".format( self.markerSets )
        return result
    # end of BibleStylesheet.__str__

    def getTKStyleDict( self, USFMKey ):
        """
        Returns the dictionary with the information for the given USFM marker key.

        Raises a KeyError if the key is not specified in the stylesheet.
        """
        return self.dataDict[USFMKey]
    # end of BibleStylesheet.getDict

    def getValue( self, USFMKey, StyleKey ):
        """
        Returns the value (string) with the information for the given USFM marker key and the requested stylename.

        Raises a KeyError if either key is not specified in the stylesheet.
        """
        return self.dataDict[USFMKey][StyleKey]
    # end of BibleStylesheet.getValue

    def getTKStyles( self ):
        """
        Returns a dictionary of USFM codes paired with the corresponding tkinter style dictionary.
        """
        results = {}
        for USFMKey in self.dataDict:
            results[USFMKey] = self.getTKStyleDict( USFMKey )
        return results
    # end of BibleStylesheet.getTKStyles
# end of class BibleStylesheet



class ParatextStylesheet():
    """
    Class to load a Paratext stylesheet into a dictionary.
    """
    def __init__( self ) -> None:
        self.sourceFolder = self.filename = self.encoding = None
        self.filepath = self.name = None
        self.recordsDB = self.dataDict = None
        self.smallestSize = self.largestSize = self.markerList = self.markerSets = None
    # end of ParatextStylesheet.__init__


    def load( self, sourceFolder, filename:str, encoding='utf-8' ):
        self.sourceFolder = sourceFolder
        self.filename = filename
        self.encoding = encoding
        assert os.path.exists( self.sourceFolder )
        assert os.path.exists( self.sourceFolder )
        self.filepath = os.path.join( self.sourceFolder, self.filename )
        assert os.path.exists( self.filepath )
        assert os.path.exists( self.filepath )
        self.name = os.path.splitext( self.filename )[0]
        recordsDB = SFMFile.SFMRecords()
        recordsDB.read( self.filepath, 'Marker', encoding=self.encoding )
        #print( "\nRecords", recordsDB.records )
        self.smallestSize, self.largestSize, self.markerList, self.markerSets = recordsDB.analyze()
        self.dataDict = recordsDB.copyToDict( "dict" )
        #print( "\nData", self.dataDict )
        self.validate()
        return self # So this command can be chained after the object creation
    # end of ParatextStylesheet.load


    def validate( self ):
        for USFMMarker in self.dataDict:
            #print( USFMMarker )
            if USFMMarker not in BibleOrgSysGlobals.loadedUSFMMarkers:
                logging.warning( "ParatextStylesheet validate: found unexpected {!r} marker".format( USFMMarker ) )
    # end of ParatextStylesheet.load


    def __eq__( self, other ):
        if type( other ) is type( self ): return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other): return not self.__eq__(other)

    def __len__( self ):
        if self.recordsDB: return len( self.recordsDB.records )
        return 0
    # end of ParatextStylesheet.__len__

    def __str__( self ):
        """
        This method returns the string representation of a USFM stylesheet object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "ParatextStylesheet object"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        if self.name: result += ('\n' if result else '') + "  Name: " + self.name
        if self.filepath: result += ('\n' if result else '') + "  From: " + self.filepath
        if self.dataDict:
            result += ('\n' if result else '') + "  Number of records = " + str( len(self.dataDict) )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            if self.smallestSize:
                result += ('\n' if result else '') + "  Smallest record size: {} markers".format( self.smallestSize )
            if self.largestSize:
                result += ('\n' if result else '') + "  Largest record size: {} markers".format( self.largestSize )
            if self.markerList: result += ('\n' if result else '') + "  Marker list: {}".format( self.markerList )
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                if self.markerSets: result += ('\n' if result else '') + "  Marker sets: {}".format( self.markerSets )
        return result
    # end of ParatextStylesheet.__str__

    def getDict( self, USFMKey ):
        """
        Returns the dictionary with the information for the given USFM marker key.

        Raises a KeyError if the key is not specified in the stylesheet.
        """
        return self.dataDict[USFMKey]
    # end of ParatextStylesheet.getDict

    def getValue( self, USFMKey, StyleKey ):
        """
        Returns the value (string) with the information for the given USFM marker key and the requested stylename.

        Raises a KeyError if either key is not specified in the stylesheet.
        """
        return self.dataDict[USFMKey][StyleKey]
    # end of ParatextStylesheet.getValue
# end of class ParatextStylesheet



def demo() -> None:
    """
    Short program to demonstrate/test the above class(es).
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    if 1: # Try the default one
        print( "\nTrying default Bible stylesheet…" )
        #folder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PTStylesheets/' )
        #filename = "LD.sty"
        ss = BibleStylesheet()
        #print( ss )
        #ss.importParatextStylesheet( folder, filename, encoding='latin-1' )
        ss.loadDefault()
        print( ss )
        print( "h style:", ss.getTKStyleDict( 'h' ) )
        try: print( "s1 font:", ss.getValue( 's1', 'font' ) )
        except KeyError: print( "No s1 or font in stylesheet!" )
        try: print( ss.getTKStyleDict( 'hijkl' ) )
        except KeyError: print( "No hijkl in stylesheet!" )
        try: print( ss.getValue( 'h', 'FontSizeImaginary' ) )
        except KeyError: print( "No h or FontSizeImaginary in stylesheet!" )
        if debuggingThisModule: print( ss.dataDict )

    if 1: # Try importing one
        print( "\nTrying Bible stylesheet import…" )
        folder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PTStylesheets/' )
        filename = "LD.sty"
        ss = BibleStylesheet()
        print( ss )
        ss.importParatextStylesheet( folder, filename, encoding='latin-1' )
        print( ss )
        if debuggingThisModule: print( ss.dataDict )
        print( "h style:", ss.getTKStyleDict( 'h' ) )
        try: print( "h FontSize:", ss.getValue( 'h', 'FontSize' ) )
        except KeyError: print( "No h or FontSize in stylesheet!" )

    if 1: # Try a small one
        print( "\nTrying small PT stylesheet…" )
        folder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PTStylesheets/' )
        filename = "LD.sty"
        ss = ParatextStylesheet().load( folder, filename, encoding='latin-1' )
        print( ss )
        print( "h style:", ss.getDict( 'h' ) )
        print( "h fontsize:", ss.getValue( 'h', 'FontSize' ) )
        if debuggingThisModule: print( ss.dataDict )

    if 1: # Try a full one
        print( "\nTrying full PT stylesheet…" )
        folder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PTStylesheets/' )
        filename = "usfm.sty"
        ss = ParatextStylesheet()
        ss.load( folder, filename )
        print( ss )
        print( "h style:", ss.getDict( 'h' ) )
        print( "h fontsize:", ss.getValue( 'h', 'FontSize' ) )
        if debuggingThisModule: print( ss.dataDict )
# end of demo

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleStylesheets.py
