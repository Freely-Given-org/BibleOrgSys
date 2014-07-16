#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# HebrewWLC.py
#   Last modified: 2013-08-28 (also update ProgVersion below)
#
# Module handling HebrewWLC.xml
#
# Copyright (C) 2011-2013 Robert Hunt
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
Module handling WLCHebrew.xml to produce C and Python data tables.
"""

ProgName = "Hebrew WLC format handler"
ProgVersion = "0.04"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )


import os
from gettext import gettext as _

import Globals, Hebrew
from OSISXMLBible import OSISXMLBible
from InternalBibleBook import InternalBibleEntry, InternalBibleEntryList



class HebrewWLC( OSISXMLBible ):
    """
    Class for handling a Hebrew WLC object (which may contain one or more Bible books)

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """
    #def __init__( self, XMLFilepath ):
    #    """ Create an empty object. """
    #    OSISXMLBible.__init__( self, XMLFilepath )
    ## end of __init__


    #def __str__( self ):
        #"""
        #This method returns the string representation of a Bible book code.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #result = "Hebrew WLC object"
        ##if self.title: result += ('\n' if result else '') + self.title
        ##if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        ##if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        #if len(self.books)==1:
            #for BBB in self.books: break # Just get the first one
            #result += ('\n' if result else '') + "  " + _("Contains one book: {}").format( BBB )
        #else: result += ('\n' if result else '') + "  " + _("Number of books = {}").format( len(self.books) )
        #return result
    ## end of __str__


    #def getVerseData( self, reference ):
        #""" Return the text for the verse with some adjustments. """
        #data = OSISXMLBible.getVerseData( self, reference )
        ##print( data );halt
        #if data:
            #myData = InternalBibleEntryList()
            #for dataLine in data:
                #print( "dL", dataLine )
                #if dataLine.getMarker() == 'v~':
                    #cT = dataLine.getCleanText().replace('/','=')
                    #myData.append( InternalBibleEntry( dataLine[0], dataLine[1], dataLine[2], cT, dataLine[4] ) )
                #else: myData.append( dataLine )
            #return myData
        #else: print( "oops. empty verse data for", reference )


    #def xgetVerseText( self, reference ):
        #""" Return the text for the verse with some adjustments. """
        #self.originalText = OSISXMLBible.getVerseText( self, reference )
        #if self.originalText is None: self.originalText = ''
        #if self.originalText: self.originalText = self.originalText.replace(' '+'־'+' ','־') # Remove spaces around the maqqef
        #if self.originalText: self.originalText = self.originalText.replace('/','=') # We use = for morpheme break character not /
        #self.currentText = self.originalText
        ##print( self.currentText ); halt
        #if self.originalText: return self.originalText
        #else: print( "oops. empty verse text for", reference )


    def removeMorphemeBreaks( self, text=None ):
        """ Return the text with morpheme break marks removed. """
        if text is None:
            self.currentText = self.currentText.replace('=', '')
            return self.currentText
        # else we were passed a text string
        return text.replace('=', '')
    # end of HebrewWLC.removeMorphemeBreaks

    def removeCantillationMarks( self, text=None, removeMetegOrSiluq=False ):
        """ Return the text with cantillation marks removed. """
        if text is None:
            self.currentText = self.removeCantillationMarks( self.currentText ) # recursive call
            return self.currentText
        # else we were passed a text string
        h = Hebrew.Hebrew ( text )
        return h.removeCantillationMarks( None, removeMetegOrSiluq )
    # end of HebrewWLC.removeCantillationMarks

    def removeVowelPointing( self, text=None, removeMetegOrSiluq=False ):
        """ Return the text with cantillation marks removed. """
        if text is None:
            self.currentText = self.removeVowelPointing( self.currentText ) # recursive call
            return self.currentText
        # else we were passed a text string
        h = Hebrew.Hebrew ( text )
        return h.removeVowelPointing( None, removeMetegOrSiluq )
    # end of HebrewWLC.removeVowelPointing
# end of HebrewWLC class



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    from VerseReferences import SimpleVerseKey

    # Demonstrate the Hebrew WLC class
    #testFile = "../morphhb/wlc/Ruth.xml" # Hebrew Ruth
    testFile = "../morphhb/wlc/Dan.xml" # Hebrew Daniel
    testReference = ('DAN', '1', '5')
    testKey = SimpleVerseKey( testReference[0], testReference[1], testReference[2] )
    if Globals.verbosityLevel > 1: print( "\nDemonstrating the Hebrew WLC class..." )
    #print( testFile, testReference )
    wlc = HebrewWLC( testFile )
    wlc.load() # Load and process the XML
    print( wlc ) # Just print a summary
    print()
    print( wlc.getVerseData( testKey ) )
    print()

    verseText = wlc.getVerseText( testKey )
    wlc.currentText = verseText
    print( "These all display left-to-right in the terminal unfortunately  :-(" )
    print( verseText )
    verseText = wlc.removeMorphemeBreaks()
    print()
    print( verseText )
    verseText = wlc.removeCantillationMarks()
    print()
    print( verseText )
    consonantalVerseText = wlc.removeVowelPointing()
    print()
    print( consonantalVerseText )
    print()
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of HebrewWLC.py