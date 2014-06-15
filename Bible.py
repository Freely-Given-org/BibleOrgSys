#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Bible.py
#   Last modified: 2014-06-15 (also update ProgVersion below)
#
# Module handling a internal Bible object
#
# Copyright (C) 2010-2014 Robert Hunt
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
Module handling an internal Bible object.
"""

ProgName = "Bible object handler"
ProgVersion = "0.07"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os.path
from gettext import gettext as _
from xml.etree.ElementTree import ElementTree

import Globals
from InternalBibleBook import InternalBibleBook
from BibleWriter import BibleWriter


#class BibleExtra:
    #"""
    #Class for handling Bible front and back matter.
    #"""

    #def __init__( self ):
        #"""
        #Constructor: creates an empty Bible extra object.
        #"""
        #self.sections = []
    ## end of __init__

    #def __str__( self ):
        #"""
        #This method returns the string representation of a Bible extra section.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #result = _("BibleExtra object")
        #result += ('\n' if result else '') + "  " + _("Number of sections = {}").format(len(self.sections) )
        #return result
    ## end of __str__
## end of class BibleExtra


#class BibleDivision:
    #"""
    #Class for handling Bible divisions (like Old Testament and New Testament).
    #"""

    #def __init__( self ):
        #"""
        #Constructor: creates an empty Bible extra object.
        #"""
        #self.shortName, self.longName = '', ''
        #self.inputAbbreviations = []
        #self.bookCodes = []
    ## end of __init__

    #def __str__( self ):
        #"""
        #This method returns the string representation of a Bible division.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #result = _("BibleDivision object")
        #result += ('\n' if result else '') + "  {} ({})".format(self.longName, self.shortName )
        #return result
    ## end of __str__
## end of class BibleDivision



class BibleBook ( InternalBibleBook ):
    """
    Class for handling a single Bible book.
        A Bible book consists of a list of tuples.
            Each tuple has two strings:
                a code to label information like section headings, paragraph text, etc.
                the content
        Chapter/Verse information is stored separately in an index (a dictionary)
            The dictionary index is a (C,V) tuple.
            The data is a tuple of
                index into data tuple (0..)
                offset into data tuple (0..)
            This means that the index has to be updated if the data is updated.
    """

    def __init__( self, name, BBB ):
        """
        Constructor: creates an empty Bible book.
        """
        InternalBibleBook.__init__( self, name, BBB )

        # Define our added data stores
        self.shortName, self.longName = '', ''
        self.inputAbbreviations = []
        self.text = []
        self.index = {}
        #self.textCodes = ( "ID", "RH1", "MT1", "MT2", "MS1", "MS2", "IOT", "IO1", "IO2", "IS1", "IS2", "InP", "SH1", "SH2", "SXR", "Pgr", "Chp", "Vrs", "Txt", "Qu1", "Qu2", "Qu3", "Qu4", "Blk", "Mar", "FNt", "XRf", "MR" )
    # end of __init__

    def __str__( self ):
        """
        This method returns the string representation of a Bible book.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = _("BibleBook object")
        result += ('\n' if result else '') + "  {} ({})".format(self.longName, self.shortName )
        for line in self.text: result += ('\n' if result else '') + "  {}".format(repr(line) )
        return result
    # end of __str__

    #def append( self, stuff ):
        #"""
        #Append the stuff tuple to a Bible book.
        #"""
        #if Globals.debugFlag: assert( len(stuff) == 2 )
        #if Globals.debugFlag: assert( stuff[0] in self.textCodes )
        #self.text.append( stuff )
    ## end of append

    #def createIndex( self ):
        #""" Create the chapter verse index for this book. """
        #self.index = {}
        #C, V = '0', '0'
        #for j,(code,text) in enumerate(self.text):
            #if code == 'Chp':
                #C, V = text, '0'
                #self.index[ (C,V) ] = j, 0
            #elif code == 'Vrs':
                #V = text
                #self.index[ (C,V) ] = j, 0
        ##print( self.index )
    ## end of createIndex
# end of class BibleBook



class Bible( BibleWriter ):
    """
    Class for handling an entire Bible.
    """

    def __init__( self ):
        """
        Constructor: creates an empty Bible object.
        """
        BibleWriter.__init__( self )
        self.objectNameString = "Bible object (generic/unknown type)"
        self.objectTypeString = "Unknown"

        # Add our own extended data stores
        #self.metadata = {}
        #self.frontMatter = []
        #self.divisions = []
        #self.actualBooks = []
        #self.backMatter = []

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData() if Globals.strictCheckingFlag else None
    # end of __init__

    #def x__str__( self ):
        #"""
        #This method returns the string representation of a Bible.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #result = _("Bible object")
        #result += ('\n' if result else '') + "  " + _("Type = {}").format( self.objectTypeString )
        #if "title" in self.metadata: result += ('\n' if result else '') + self.metadata["title"]
        #if "version" in self.metadata: result += ('\n' if result else '') + "  " + _("Version: {} ").format(self.metadata["version"] )
        #if "publicationDate" in self.metadata: result += ('\n' if result else '') + "  " + _("Date: {}").format(self.metadata["publicationDate"] )
        #if self.divisions: result += ('\n' if result else '') + "  " + _("Number of divisions = {}").format(len(self.divisions) )
        #result += ('\n' if result else '') + "  " + _("Number of books = {}").format(len(self.books) )
        #if self.frontMatter: result += ('\n' if result else '') + "  " + _("Number of front matter chunks = {}").format(len(self.frontMatter) )
        #if self.backMatter: result += ('\n' if result else '') + "  " + _("Number of back matter chunks = {}").format(len(self.backMatter) )
        #return result
    ## end of __str__

    #def xxxaddBook( self, BBB ):
        #"""
        #Adds a new book to the Bible and returns a pointer.
        #"""
        #BB = BibleBook( BBB )
        #self.books.append( BB )
        #return BB
    ## end of addBook

    #def xxxwrite( self, outputFilepath ):
        #"""
        #Write the Bible (usually to a .module file).
        #"""
        #from datetime import datetime
        #with open( outputFilepath, 'wt' ) as myFile:
            #myFile.write( "# {}\n#\n".format(outputFilepath ) )
            #myFile.write( "# This UTF-8 file was automatically generated by Bible.py V{} on {}\n#\n".format( ProgVersion, datetime.now() ) )
            #if "title" in self.metadata: myFile.write( "# {} data\n".format(self.title ) )
            ##if self.version: myFile.write( "#  Version: {}\n".format(self.version ) )
            ##if self.date: myFile.write( "#  Date: {}\n#\n".format(self.date ) )
    ## end of write


    #def xxxloadUSFMBible( self, outputFilepath=None ):
        #"""
        #Converts the USFM information to a Bible object.
        #"""
        #def verseToBible( text, store ):
            #""" Remove embedded fields and put the text in the store. """
            #adjText = text

            ## Look for initial cross-references and strip them off
            ##startString = '\\x '
            ##while adjText.startswith( startString ): # an initial cross-reference
            ##    endString = '\\x* '
            ##    eix = adjText.find( endString )
            ##    if eix == -1:
            ##        endString = endString[:-1] # without the final space
            ##        eix = adjText.find( endString )
            ##    if eix == -1: logging.error( "Can't find end of cross-reference in '{}'".format( text ) )
            ##    else: # found the beginning and the end
            ##        xref = adjText[len(startString):eix]
            ##        adjText = adjText[eix+len(endString):]
            ##        #print( "'{}' '{}'".format( xref, adjText ) )
            ##        store.append( ('XRf', xref,) )

            ## WRONG: We still have embedded footnotes and some cross-references (just not verse-initial), etc.
            #if adjText.endswith( '\\' ): logging.error( "Unexpected field ending with backslash: '{}'".format( text ) )
            #while '\\' in adjText:
                #ix = adjText.find( '\\' )
                #assert( ix != -1 )
                #ch1 = adjText[ix+1] if ix+1<len(adjText) else ''
                #ch2 = adjText[ix+2] if ix+2<len(adjText) else ''
                #if ch2 != ' ': logging.error( "Unexpected characters after backslash: '{}'".format( text ) )
                ##elif ch1 == 'f':
                ##    field = 'FNt'
                ##elif ch1 == 'x':
                ##    field = 'XRf'
                #else: logging.error( "Unexpected '{}' character after backslash: '{}'".format( ch1, text ) )
                #endString = '\\' + ch1 + '* '
                #eix = adjText.find( endString )
                #if eix == -1:
                    #endString = endString[:-1] # without the final space
                    #eix = adjText.find( endString )
                #if eix == -1: logging.error( "Can't find end of backslash field in '{}'".format( text ) )
                #part1 = adjText[:ix]; assert( part1 )
                #part2 = adjText[ix+3:eix]; assert( part2 )
                #adjText = adjText[eix+len(endString):]
                ##print( "\n'{}'  '{}'  '{}'".format( part1, part2, adjText ) )
                #store.append( ('Txt', part1,) )
                #store.append( (field, part2,) )
            #if '\\' in adjText: print( "Still have '{}'".format( adjText ) )
            #if adjText: store.append( ('Txt', adjText,) )
        ## end of verseToBible

        ##import Bible
        ##B = Bible.Bible()
        #unhandledMarkers = set()
        #for BBB,bookData in self.books.items():
            #if Globals.verbosityLevel > 2: print( bookData )
            #bk = B.addBook( BBB )
            #for marker,text,extras in bookData.lines:
                ##print( marker, text )
                #if marker == 'p': bk.append( ('Pgr', text,) )
                #elif marker=='c': bk.append( ('Chp', text,) )
                #elif marker=='v':
                    ##verseNum = text.split()[0]
                    ##verseText = text[len(verseNum)+1:]
                    #verseBits = text.split(None, 1)
                    #verseNum = verseBits[0]
                    #bk.append( ('Vrs', verseBits[0],) )
                    #if len(verseBits) > 1:
                        #verseToBible( verseBits[1], bk )
                #elif marker=='q1': bk.append( ('Qu1', text,) )
                #elif marker=='q2': bk.append( ('Qu2', text,) )
                #elif marker=='q3': bk.append( ('Qu3', text,) )
                #elif marker=='s1': bk.append( ('SH1', text,) )
                #elif marker=='s2': bk.append( ('SH2', text,) )
                #elif marker== 'r': bk.append( ('SXR', text,) )
                #elif marker== 'iot': bk.append( ('IOT', text,) )
                #elif marker== 'mt1': bk.append( ('MT1', text,) )
                #elif marker== 'mt2': bk.append( ('MT2', text,) )
                #elif marker== 'h': bk.append( ('RH1', text,) )
                #elif marker== 'is1': bk.append( ('IS1', text,) )
                #elif marker== 'is2': bk.append( ('IS2', text,) )
                #elif marker== 'm': bk.append( ('Mar', text,) )
                #elif marker== 'b': bk.append( ('Blk', text,) )
                #elif marker== 'io1': bk.append( ('IO1', text,) )
                #elif marker== 'io2': bk.append( ('IO2', text,) )
                #elif marker== 'ms1': bk.append( ('MS1', text,) )
                #elif marker== 'ip': bk.append( ('InP', text,) )
                #elif marker== 'mr': bk.append( ('MR', text,) )
                #elif marker== 'id': bk.append( ('ID', text,) )
                #else:
                    ##print( "Doesn't handle {} marker yet".format( marker ) )
                    #unhandledMarkers.add( marker )
            #bk.createIndex()
            ##print( bk)
        #print( B )
        #if outputFilepath: B.write( outputFilepath )
        #if unhandledMarkers and Globals.verbosityLevel>0: print( "  " + _("WARNING: Unhandled USFM markers were {}").format(unhandledMarkers) )
    ## end of toBible
# end of class Bible



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( "{} V{}".format(ProgName, ProgVersion ) )

    # Since this is only designed to be a base class, it can't actually do much at all
    B = Bible()
    if Globals.verbosityLevel > 0: print( B )

    if 1: # Test a single folder containing a USFM Bible
        from USFMBible import USFMBible
        name, encoding, testFolder = "Matigsalug", "utf-8", "../../../../../Data/Work/Matigsalug/Bible/MBTV/" # You can put your test folder here
        if os.access( testFolder, os.R_OK ):
            UB = USFMBible( testFolder, name, encoding )
            UB.load()
            if Globals.verbosityLevel > 0: print( UB )
            if Globals.strictCheckingFlag:
                UB.check()
            UB.doAllExports( "OutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
        else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of Bible.py