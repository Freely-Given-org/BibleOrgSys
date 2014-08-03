#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleLexicon.py
#   Last modified: 2014-08-04 (also update ProgVersion below)
#
# Module handling the Hebrew and Greek lexicons
#
# Copyright (C) 2014 Robert Hunt
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
Module handling the OpenScriptures Hebrew and morphgnt Greek lexicons.

    Hebrew has Strongs and BDB
    Greek has Strongs only.
"""

ProgName = "Bible Lexicon format handler"
ProgVersion = "0.20"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os.path
from gettext import gettext as _

import Globals
import HebrewLexicon, GreekLexicon



class BibleLexiconIndex:
    """
    Class for handling a Bible Lexicon (Hebrew -- not applicable yet to Greek).

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, HebrewXMLFolder, GreekXMLFolder ):
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self.HebrewXMLFolder, self.GreekXMLFolder = HebrewXMLFolder, GreekXMLFolder
        self.hIndex = HebrewLexicon.HebrewLexiconIndex( self.HebrewXMLFolder ) # Create the object
    # end of BibleLexiconIndex.__init__

    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Bible Lexicon Index object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        result += ('\n' if result else '') + "  " + _("Number of augmented Hebrew Strong's index entries = {}").format( len(self.hIndex.IndexEntries1) )
        result += ('\n' if result else '') + "  " + _("Number of Hebrew lexical index entries = {}").format( len(self.hIndex.IndexEntries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic lexical index entries = {}").format( len(self.hIndex.IndexEntries['arc']) )
        return result
    # end of BibleLexiconIndex.__str__

    def getLexiconCodeFromStrongsNumber( self, key ):
        """
        The key is a digit string like '172' (optional preceding H).

        Returns a lexicon internal code like 'acd'.
        """
        if key.startswith( 'H' ): return self.hIndex.getLexiconCodeFromStrongsNumber( key )
    # end of BibleLexiconIndex.getLexiconCodeFromStrongsNumber

    def _getStrongsNumberFromLexiconCode1( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        if key.startswith( 'H' ): return self.hIndex._getStrongsNumberFromLexiconCode1( key )
    # end of BibleLexiconIndex.getStrongsNumberFromLexiconCode1

    def _getStrongsNumberFromLexiconCode2( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        if key.startswith( 'H' ): return self.hIndex._getStrongsNumberFromLexiconCode2( key )
    # end of BibleLexiconIndex.getStrongsNumberFromLexiconCode2

    def getStrongsNumberFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        if key.startswith( 'H' ): return self.hIndex.getStrongsNumberFromLexiconCode( key )
    # end of BibleLexiconIndex.getStrongsNumberFromLexiconCode

    def getBDBCodeFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a BDB code, e.g., 'm.ba.aa'
        """
        if key.startswith( 'H' ): return self.hIndex.getBDBCodeFromLexiconCode( key )
    # end of BibleLexiconIndex.getBDBCodeFromLexiconCode

    def getTWOTCodeFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a BDB code, e.g., '4a'
        """
        if key.startswith( 'H' ): return self.hIndex.getTWOTCodeFromLexiconCode( key )
    # end of BibleLexiconIndex.getTWOTCodeFromLexiconCode

# end of BibleLexiconIndex class




class BibleLexicon:
    """
    Class for handling a Bible Lexicon (Hebrew and Greek)

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, HebrewXMLFolder, GreekXMLFolder ):
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self.HebrewXMLFolder, self.GreekXMLFolder = HebrewXMLFolder, GreekXMLFolder
        self.hLexicon = HebrewLexicon.HebrewLexicon( self.HebrewXMLFolder ) # Create the object
        self.gLexicon = GreekLexicon.GreekLexicon( self.GreekXMLFolder ) # Create the object
    # end of BibleLexicon.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Bible Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        result += ('\n' if result else '') + "  " + _("Number of Strong's Hebrew entries = {}").format( len(self.hLexicon.StrongsEntries) )
        result += ('\n' if result else '') + "  " + _("Number of BDB Hebrew entries = {}").format( len(self.hLexicon.BrownDriverBriggsEntries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of BDB Aramaic entries = {}").format( len(self.hLexicon.BrownDriverBriggsEntries['arc']) )
        result += ('\n' if result else '') + "  " + _("Number of Strong's Greek entries = {}").format( len(self.gLexicon.StrongsEntries) )
        return result
    # end of BibleLexicon.__str__


    def getStrongsEntryData( self, key ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        if key.startswith( 'H' ): return self.hLexicon.getStrongsEntryData( key )
        if key.startswith( 'G' ): return self.gLexicon.getStrongsEntryData( key )
    # end of BibleLexicon.getStrongsEntryData


    def getStrongsEntryField( self, key, fieldName ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.
        The fieldName is a name (string) like 'usage'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if key.startswith( 'H' ): return self.hLexicon.getStrongsEntryField( key, fieldName )
        if key.startswith( 'G' ): return self.gLexicon.getStrongsEntryField( key, fieldName )
    # end of BibleLexicon.getStrongsEntryField


    def getStrongsEntryHTML( self, key ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.

        Returns an HTML li entry for the given key.
        Returns None if the key is not found.

        e.g., for H1, returns:
            <li value="1" id="ot:1"><i title="{awb}" xml:lang="hbo">אָב</i> a primitive word;
                father, in a literal and immediate, or figurative and remote application):
                <span class="kjv_def">chief, (fore-)father(-less), X patrimony, principal</span>.
                Compare names in "Abi-".</li>
            <li value="165" id="ot:165"><i title="{e-hee'}" xml:lang="hbo">אֱהִי</i> apparently an
                orthographical variation for <a href="#ot:346"><i title="{ah-yay'}" xml:lang="hbo">אַיֵּה</i></a>;
                where: <span class="kjv_def">I will be (Hos</span>. 13:10, 14) (which is often the rendering of
                the same Hebrew form from <a href="#ot:1961"><i title="{haw-yaw}" xml:lang="hbo">הָיָה</i></a>).</li>

        """
        if key.startswith( 'H' ): return self.hLexicon.getStrongsEntryHTML( key )
        if key.startswith( 'G' ): return self.gLexicon.getStrongsEntryHTML( key )
    # end of BibleLexicon.getStrongsEntryHTML


    def getBDBEntryData( self, key ):
        """
        The key is a BDB number (string) like 'a.ca.ab'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        return self.hLexicon.getBDBEntryData( key )
    # end of BibleLexicon.getBDBEntryData


    def getBDBEntryField( self, key, fieldName ):
        """
        The key is a BDB number (string) like 'ah.ba.aa'.
        The fieldName is a name (string) like 'status'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        return self.hLexicon.getBDBEntryField( key, fieldName )
    # end of BibleLexicon.getBDBEntryField


    def getBDBEntryHTML( self, key ):
        """
        The key is a BDB number (string) like 'ah.ba.aa'.

        Returns an HTML entry for the given key.
        Returns None if the key is not found.
        """
        return self.hLexicon.getBDBEntryHTML( key )
    # end of BibleLexicon.getBDBEntryHTML
# end of BibleLexicon class




def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    HebrewLexiconFolder = "../HebrewLexicon/" # Open Scriptures Hebrew lexicon folder
    GreekLexiconFolder = "../../../ExternalPrograms/morphgnt/strongs-dictionary-xml/" # morphgnt Greek lexicon folder


    if 1: # demonstrate the Bible Lexicon Index class
        if Globals.verbosityLevel > 1: print( "\nDemonstrating the Bible Lexicon Index class..." )
        blix = BibleLexiconIndex( HebrewLexiconFolder, GreekLexiconFolder ) # Load and process the XML
        print( blix ) # Just print a summary
        print()
        print( "Code for 2 is", blix.getLexiconCodeFromStrongsNumber( '2' ) )
        print( "Code for H8674 is", blix.getLexiconCodeFromStrongsNumber( 'H8674' ) )
        print( "Code for H8675 is", blix.getLexiconCodeFromStrongsNumber( 'H8675' ) )
        print( "Codes for aac are", blix.getStrongsNumberFromLexiconCode('aac'), blix.getBDBCodeFromLexiconCode('aac'), blix.getTWOTCodeFromLexiconCode('aac') )
        print( "Codes for nyy are", blix.getStrongsNumberFromLexiconCode('nyy'), blix.getBDBCodeFromLexiconCode('nyy'), blix.getTWOTCodeFromLexiconCode('nyy') )
        print( "Codes for pdc are", blix.getStrongsNumberFromLexiconCode('pdc'), blix.getBDBCodeFromLexiconCode('pdc'), blix.getTWOTCodeFromLexiconCode('pdc') )
        print( "Codes for pdd are", blix.getStrongsNumberFromLexiconCode('pdd'), blix.getBDBCodeFromLexiconCode('pdd'), blix.getTWOTCodeFromLexiconCode('pdd') )


    if 1: # demonstrate the Bible Lexicon class
        if Globals.verbosityLevel > 1: print( "\nDemonstrating the Bible Lexicon class..." )
        bl = BibleLexicon( HebrewLexiconFolder, GreekLexiconFolder ) # Load and process the XML
        print( bl ) # Just print a summary
        print()
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',
                           'G1','G123','G165','G1732','G1979','G2011','G5624','G5625',): # Last ones of each are invalid
            print( '\n' + strongsKey )
            print( " Data:", bl.getStrongsEntryData( strongsKey ) )
            print( " Usage:", bl.getStrongsEntryField( strongsKey, 'usage' ) )
            print( " HTML:", bl.getStrongsEntryHTML( strongsKey ) )
        for BDBKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            print( '\n' + BDBKey )
            print( " Data:", bl.getBDBEntryData( BDBKey ) )
            print( " Status:", bl.getBDBEntryField( BDBKey, 'status' ) )
            print( " HTML:", bl.getBDBEntryHTML( BDBKey ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=False )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of BibleLexicon.py