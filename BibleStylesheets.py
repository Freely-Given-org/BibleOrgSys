#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleStylesheets.py
#
# Module handling Bible (including Paratext) stylesheets
#
# Copyright (C) 2013-2016 Robert Hunt
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

LastModifiedDate = '2016-05-18' # by RJH
ShortProgName = "BibleStylesheets"
ProgName = "Bible stylesheet handler"
ProgVersion = '0.08'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


#from singleton import singleton
import os, logging

import BibleOrgSysGlobals
import SFMFile



def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
# end of exp



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
DEFAULT_FONTNAME = 'helvetica'

VERSENUMBER_FONTSIZE = 6
CURRENT_VERSE_FONTSIZE = 12
CHAPTERNUMBER_FONTSIZE = 13
DEFAULT_FONTSIZE = 9
HEADING_FONTSIZE = 11
SUBHEADING_FONTSIZE = 10

VERSENUMBER_COLOUR = 'blue'
CHAPTERNUMBER_COLOUR = 'orange'
HEADING_COLOUR = 'red'
SUBHEADING_COLOUR = 'sienna1'
SECTION_REFERENCE_COLOUR = 'green'
EXTRA_COLOUR = 'royalBlue1'

SUPERSCRIPT_OFFSET = '4'

# Asterisk in front of a tag name indicates the currently selected verse
DEFAULT_STYLE_DICT = { # earliest entries have the highest priority
    'id': {},
    'h': {},
    's1': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    's2': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    's3': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    's4': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':HEADING_COLOUR, 'justify':'center', },
    'd': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, SUBHEADING_FONTSIZE ), 'foreground':SUBHEADING_COLOUR, },
    'sp': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, SUBHEADING_FONTSIZE ), 'foreground':EXTRA_COLOUR, },
    'c': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, CHAPTERNUMBER_FONTSIZE ), 'foreground':CHAPTERNUMBER_COLOUR, },
    'r': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, HEADING_FONTSIZE ), 'foreground':SECTION_REFERENCE_COLOUR, 'justify':'center', },
    'c#': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, CHAPTERNUMBER_FONTSIZE ), 'foreground':CHAPTERNUMBER_COLOUR, },
    'c~': { 'font':'{} {} bold'.format( DEFAULT_FONTNAME, CHAPTERNUMBER_FONTSIZE ), 'foreground':CHAPTERNUMBER_COLOUR, },
    #'v-': { 'font':'{} {}'.format( DEFAULT_FONTNAME, VERSENUMBER_FONTSIZE ), 'offset':SUPERSCRIPT_OFFSET, },
    'v': { 'font':'{} {}'.format( DEFAULT_FONTNAME, VERSENUMBER_FONTSIZE ), 'foreground':VERSENUMBER_COLOUR, 'offset':SUPERSCRIPT_OFFSET, },
    #'v+': { 'font':'{} {}'.format( DEFAULT_FONTNAME, VERSENUMBER_FONTSIZE ), 'offset':SUPERSCRIPT_OFFSET, },
    'v~': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), }, #'background':'orange', },
    '*v~': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), }, #'background':'pink', },
    'q1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'pink', },
    'q2': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'pink', },
    'q3': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'pink', },
    'q4': { 'font':'{} {}'.format( DEFAULT_FONTNAME, DEFAULT_FONTSIZE ), 'background':'pink', },
    '*q1': { 'font':'{} {}'.format( DEFAULT_FONTNAME, CURRENT_VERSE_FONTSIZE ), 'background':'pink', },
    }


class BibleStylesheet():
    """
    Class to load a Paratext stylesheet into a dictionary.
    """
    def __init__( self ):
        self.dataDict = None
        self.filepath = None
        self.smallestSize = self.largestSize = self.markerList = self.markerSets = None
    # end of BibleStylesheet.__init__


    def loadDefault( self ):
        self.dataDict = DEFAULT_STYLE_DICT
        self.name = 'Default'
        self.validate()
        return self  # So this command can be chained after the object creation
    # end of BibleStylesheet.loadDefault


    def load( self, sourceFolder, filename ):
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
        from InternalBibleInternals import BOS_ALL_ADDED_MARKERS
        for USFMMarker, styleData in self.dataDict.items():
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("validate"), USFMMarker, styleData )
            if USFMMarker[0] == '*': USFMMarker = USFMMarker[1:] # Remove any leading asterisk for the check
            assert USFMMarker in BibleOrgSysGlobals.USFMMarkers or USFMMarker in BOS_ALL_ADDED_MARKERS
    # end of BibleStylesheet.load


    def importParatextStylesheet( self, folder, filename, encoding='utf-8' ):
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Importing {} Paratext stylesheet…".format( filename ) )
        PTSS = ParatextStylesheet().load( folder, filename, encoding )
        self.name = PTSS.name
        self.filepath = PTSS.filepath
        self.dataDict = {}
        for marker in BibleOrgSysGlobals.USFMMarkers:
            #print( marker )
            try: PTFormatting = PTSS.getDict( marker )
            except KeyError: PTFormatting = None # Just ignore the error
            if PTFormatting:
                formatSpecification = ''
                for field, value in PTFormatting.items():
                    print( marker, field, value )
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
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + ProgVersion
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
    def __init__( self ):
        self.sourceFolder = self.filename = self.encoding = None
        self.filepath = self.name = None
        self.recordsDB = self.dataDict = None
        self.smallestSize = self.largestSize = self.markerList = self.markerSets = None
    # end of ParatextStylesheet.__init__


    def load( self, sourceFolder, filename, encoding='utf-8' ):
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
            if USFMMarker not in BibleOrgSysGlobals.USFMMarkers:
                logging.warning( exp("ParatextStylesheet validate: found unexpected {!r} marker").format( USFMMarker ) )
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
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + ProgVersion
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



def demo():
    """
    Short program to demonstrate/test the above class(es).
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    if 1: # Try the default one
        print( "\nTrying default Bible stylesheet…" )
        #folder = "../../../../../Data/Work/VirtualBox_Shared_Folder/PTStylesheets/"
        #filename = "LD.sty"
        ss = BibleStylesheet()
        #print( ss )
        #ss.importParatextStylesheet( folder, filename, encoding='latin-1' )
        ss.loadDefault()
        print( ss )
        print( ss.getTKStyleDict( 'h' ) )
        #print( ss.getValue( 'h', 'FontSize' ) )
        try: print( ss.getTKStyleDict( 'hijkl' ) )
        except KeyError: print( "No hijkl in stylesheet!" )
        try: print( ss.getValue( 'h', 'FontSizeImaginary' ) )
        except KeyError: print( "No h or FontSizeImaginary in stylesheet!" )

    if 1: # Try a small one
        print( "\nTrying small PT stylesheet…" )
        folder = "../../../../../Data/Work/VirtualBox_Shared_Folder/PTStylesheets/"
        filename = "LD.sty"
        ss = ParatextStylesheet().load( folder, filename, encoding='latin-1' )
        print( ss )
        print( 'h', ss.getDict( 'h' ) )
        print( ss.getValue( 'h', 'FontSize' ) )
        try: print( ss.getDict( 'hijkl' ) )
        except KeyError: print( "No hijkl in stylesheet!" )
        try: print( ss.getValue( 'h', 'FontSizeImaginary' ) )
        except KeyError: print( "No h or FontSizeImaginary in stylesheet!" )

    if 1: # Try a full one
        print( "\nTrying full PT stylesheet…" )
        folder = "../../../../../Data/Work/VirtualBox_Shared_Folder/PTStylesheets/"
        filename = "usfm.sty"
        ss = ParatextStylesheet()
        ss.load( folder, filename )
        print( ss )
        print( ss.getDict( 'h' ) )
        print( ss.getValue( 'h', 'FontSize' ) )
        try: print( ss.getDict( 'hijkl' ) )
        except KeyError: print( "No hijkl in stylesheet!" )
        try: print( ss.getValue( 'h', 'FontSizeImaginary' ) )
        except KeyError: print( "No h or FontSizeImaginary in stylesheet!" )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of BibleStylesheets.py