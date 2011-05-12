#!/usr/bin/python3
#
# USFMBibleBook.py
#
# Module handling the USFM markers for Bible books
#   Last modified: 2011-05-12 by RJH (also update versionString below)
#
# Copyright (C) 2010-2011 Robert Hunt
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
Module for defining and manipulating USFM Bible books.
"""

progName = "USFM Bible book handler"
versionString = "0.20"


import os, logging
from gettext import gettext as _
from collections import OrderedDict

import Globals
from USFMMarkers import USFMMarkers


# Define commonly used sets of footnote and xref markers
footnoteSets = (
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
for thisSet in footnoteSets: assert( footnoteSets.count(thisSet) == 1 )
for thisSet in xrefSets: assert( xrefSets.count(thisSet) == 1 )


class USFMBibleBook:
    """
    Class to load and manipulate a single USFM file / book.
    """

    def __init__( self ):
        """
        Create the object.
        """
        self.lines = []
        self.USFMMarkers = USFMMarkers().loadData()
        self.errorDictionary = OrderedDict()
        self.givenAngleBracketWarning, self.givenDoubleQuoteWarning = False, False
    # end of __init_

    def __str__( self ):
        """
        This method returns the string representation of a Bible book.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = _("USFM Bible Book object")
        if self.bookReferenceCode: result += ('\n' if result else '') + "  " + self.bookReferenceCode
        if self.sourceFilepath: result += ('\n' if result else '') + "  " + _("From: ") + self.sourceFilepath
        result += ('\n' if result else '') + "  " + _("Number of lines = ") + str(len(self.lines))
        if Globals.verbosityLevel > 1: result += ('\n' if result else '') + "  " + _("Deduced short book name is '{}'").format( self.getBookName() )
        return result
    # end of __str__


    def load( self, bookReferenceCode, folder, filename, encoding='utf-8', logErrors=False ):
        """
        Load the book from a file.
        """
        def fix( marker, text ):
            """ Does character fixes on a specific line. """
            adjText = text

            # Fix up quote marks
            if '<' in adjText or '>' in adjText:
                if not self.givenAngleBracketWarning: # Just give the warning once
                    fixErrors.append( _("{} {}:{} Found angle brackets in {}: {}").format( bookReferenceCode, c, v, marker, text ) )
                    if logErrors: logging.warning( _("Found angle bracket(s) after {} {}:{} in {}: {}").format( bookReferenceCode, c, v, marker, text ) )
                    self.givenAngleBracketWarning = True
                adjText = adjText.replace('<<','“').replace('>>','”').replace('<','‘').replace('>','’') # Replace angle brackets with the proper opening and close quote marks
            if '"' in adjText:
                if not self.givenDoubleQuoteWarning: # Just give the warning once
                    fixErrors.append( _("{} {}:{} Found \" in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )
                    if logErrors: logging.warning( _("Found \" after {} {}:{} in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )
                    self.givenDoubleQuoteWarning = True
                adjText = adjText.replace(' "',' “').replace('"','”') # Try to replace double-quote marks with the proper opening and closing quote marks

            # Move footnotes and crossreferences out to extras
            extras = []
            ixFN = adjText.find( '\\f ' )
            ixXR = adjText.find( '\\x ' )
            while ixFN!=-1 or ixXR!=-1: # We have one or the other
                if ixFN!=-1 and ixXR!=-1: # We have both
                    assert( ixFN != ixXR )
                    ix1 = min( ixFN, ixXR ) # Process the first one
                else: ix1 = ixFN if ixXR==-1 else ixXR
                if ix1 == ixFN:
                    ix2 = adjText.find( '\\f*' )
                    thisOne, this1 = "footnote", "fn"
                else:
                    assert( ix1 == ixXR )
                    ix2 = adjText.find( '\\x*' )
                    thisOne, this1 = "cross-reference", "xr"
                if ix2 == -1: # no closing marker
                    fixErrors.append( _("{} {}:{} Found unmatched {} open in {}: {}").format( bookReferenceCode, c, v, thisOne, marker, adjText ) )
                    if logErrors: logging.error( _("Found unmatched {} open after {} {}:{} in {}: {}").format( bookReferenceCode, c, v, thisOne, marker, adjText ) )
                    ix2 = 99999 # Go to the end
                elif ix2 < ix1: # closing marker is before opening marker
                    fixErrors.append( _("{} {}:{} Found unmatched {} in {}: {}").format( bookReferenceCode, c, v, thisOne, marker, adjText ) )
                    if logErrors: logging.error( _("Found unmatched {} after {} {}:{} in {}: {}").format( bookReferenceCode, c, v, thisOne, marker, adjText ) )
                    ix1, ix2 = ix2, ix1 # swap them then
                # Remove the footnote or xref
                #print( "Found {} at {} {} in '{}'".format( thisOne, ix1, ix2, adjText ) )
                note = adjText[ix1+3:ix2] # Get the note text (without the beginning and end markers)
                adjText = adjText[:ix1] + adjText[ix2+3:] # Remove the note completely from the text
                extras.append( (this1,ix1,note,) )
                ixFN = adjText.find( '\\f ' )
                ixXR = adjText.find( '\\x ' )
            #if extras: print( "Fix gave '{}' and '{}'".format( adjText, extras ) )
            #if len(extras)>1: print( "Mutiple fix gave '{}' and '{}'".format( adjText, extras ) )

            if '\\f' in adjText or '\\x' in adjText:
                fixErrors.append( _("{} {}:{} Unable to properly process footnotes and cross-references in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )
                if logErrors: logging.error( _("Unable to properly process footnotes and cross-references {} {}:{} in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )
                halt

            if '<' in adjText or '>' in adjText or '"' in adjText: print( marker, adjText ); halt
            return marker, adjText, extras
        # end of fix

        def processLine( marker, text ):
            """ Process one USFM line. """
            #print( marker, text )
            # Convert markers like s to standard markers like s1
            adjMarker = self.USFMMarkers.toStandardMarker( marker )
            #if adjMarker!=marker: print( marker, "->", adjMarker )

            if text:
                # Check markers inside the lines
                markerList = self.USFMMarkers.getMarkerListFromText( text )
                #if markerList: print( "\nText {} {}:{} = {}:'{}'".format(self.bookReferenceCode, c, v, marker, text)); print( markerList )
                closed = True
                for insideMarker, nextSignificantChar, iMIndex in markerList: # check character markers
                    if self.USFMMarkers.isInternalMarker(insideMarker) and closed==True and nextSignificantChar in ('',' '): closed = insideMarker
                    if closed!=True and nextSignificantChar=='*' and insideMarker==closed: closed = True
                if closed!=True:
                    loadErrors.append( _("{} {}:{} Marker '{}' doesn't appear to be closed in {}: {}").format( self.bookReferenceCode, c, v, closed, marker, text ) )
                    if logErrors: logging.warning( _("Marker '{}' doesn't appear to be closed after {} {}:{} in {}: {}").format( closed, self.bookReferenceCode, c, v, marker, text ) )
                ix = 0
                for insideMarker, nextSignificantChar, iMIndex in markerList: # check paragraph markers
                    if self.USFMMarkers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
                        if ix==0:
                            loadErrors.append( _("{} {}:{} Marker '{}' shouldn't appear within line in {}: '{}'").format( self.bookReferenceCode, c, v, insideMarker, marker, text ) )
                            if logErrors: logging.error( _("Marker '{}' shouldn't appear within line after {} {}:{} in {}: '{}'").format( insideMarker, self.bookReferenceCode, c, v, marker, text ) ) # Only log the first error in the line
                        thisText = text[ix:iMIndex].rstrip()
                        #print( "got {}:'{}'".format( adjMarker, thisText ) )
                        self.lines.append( fix( adjMarker, thisText ) )
                        ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                        adjMarker = self.USFMMarkers.toStandardMarker( insideMarker ) # setup for the next line
                if ix != 0: # We must have separated multiple lines
                    #print( "Here '{}' {} {}".format( text, ix, ix+len(insideMarker)+1 ) )
                    text = text[ix:]
                    #print( "leaving {}:'{}'".format( adjMarker, text ) )

            # Save the corrected data
            self.lines.append( fix( adjMarker, text ) )
        # end of processLine


        import SFMFile

        if Globals.verbosityLevel > 2: print( "  " + _("Loading {}...").format( filename ) )
        self.bookReferenceCode = bookReferenceCode
        self.sourceFolder = folder
        self.sourceFilename = filename
        self.sourceFilepath = os.path.join( folder, filename )
        originalBook = SFMFile.SFMLines()
        originalBook.read( self.sourceFilepath, encoding=encoding )

        # Do some important cleaning up before we save the data
        c, v = '0', '0'
        lastMarker, lastText = '', ''
        loadErrors, fixErrors = [], []
        for marker,text in originalBook.lines: # Always process a line behind in case we have to combine lines
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = 0
            if marker=='v' and text: v = text.split()[0]

            if self.USFMMarkers.isNewlineMarker( marker ):
                if lastMarker: processLine( lastMarker, lastText )
                lastMarker, lastText = marker, text
            else: # the line begins with an internal marker -- append it to the previous line
                loadErrors.append( _("{} {}:{} Found '{}' internal marker at beginning of line with text: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                if logErrors: logging.error( _("Found '{}' internal marker after {} {}:{} at beginning of line with text: {}").format( marker, self.bookReferenceCode, c, v, text ) )
                #lastText += '' if lastText.endswith(' ') else ' ' # Not always good to add a space, but it's their fault!
                lastText +=  '\\' + marker + ' ' + text
                #print( "{} {} {} Now have {}:'{}'".format( self.bookReferenceCode, c, v, lastMarker, lastText ) )
        if lastMarker: processLine( lastMarker, lastText ) # Process the final line

        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
        if fixErrors: self.errorDictionary['Fix Text Errors'] = fixErrors
    # end of load


    def validateUSFM( self, logErrors=False ):
        """
        Validate the loaded book.
        """
        assert( self.lines )
        validationErrors = []

        for j, (marker,text,extras) in enumerate(self.lines):
            #print( marker, text[:40] )

            # Keep track of where we are for more helpful error messages
            if marker == 'c':
                if text: c = text.split()[0]
                else:
                    validationErrors.append( _("{} {}:{} Missing chapter number").format( self.bookReferenceCode, c, v ) )
                    if logErrors: logging.error( _("Missing chapter number after {} {}:{}").format( self.bookReferenceCode, c, v ) )
                v = 0
            if marker == 'v':
                if text: v = text.split()[0]
                else:
                    validationErrors.append( _("{} {}:{} Missing verse number").format( self.bookReferenceCode, c, v ) )
                    if logErrors: logging.error( _("Missing verse number after {} {}:{}").format( self.bookReferenceCode, c, v ) )

            # Do a rough check of the SFMs
            if marker=='id' and j!=0:
                validationErrors.append( _("{} {}:{} Marker 'id' should only appear as the first marker in a book but found on line {} in {}: {}").format( self.bookReferenceCode, c, v, j, marker, text ) )
                if logErrors: logging.error( _("Marker 'id' should only appear as the first marker in a book but found on line {} after {} {}:{} in {}: {}").format( j, self.bookReferenceCode, c, v, marker, text ) )
            if not self.USFMMarkers.isNewlineMarker( marker ):
                validationErrors.append( _("{} {}:{} Unexpected '{}' new line marker in Bible book (Text is '{}')").format( self.bookReferenceCode, c, v, marker, text ) )
                if logErrors: logging.warning( _("Unexpected '{}' paragraph marker in Bible book after {} {}:{} (Text is '{}')").format( marker, self.bookReferenceCode, c, v, text ) )
            markerList = self.USFMMarkers.getMarkerListFromText( text )
            #if markerList: print( "\nText = {}:'{}'".format(marker,text)); print( markerList )
            closed = True
            for insideMarker, nextSignificantChar, iMIndex in markerList: # check character markers
                if self.USFMMarkers.isInternalMarker(insideMarker) and closed==True and nextSignificantChar in ('',' '): closed = insideMarker
                if closed!=True and nextSignificantChar=='*' and insideMarker==closed: closed = True
            if closed!=True:
                validationErrors.append( _("{} {}:{} Marker '{}' doesn't appear to be closed in {}: {}").format( self.bookReferenceCode, c, v, closed, marker, text ) )
                if logErrors: logging.warning( _("Marker '{}' doesn't appear to be closed after {} {}:{} in {}: {}").format( closed, self.bookReferenceCode, c, v, marker, text ) )
            ix = 0
            for insideMarker, nextSignificantChar, iMIndex in markerList: # check newline markers
                if self.USFMMarkers.isNewlineMarker(insideMarker):
                    validationErrors.append( _("{} {}:{} Marker '{}' shouldn't appear within line in {}: {}").format( self.bookReferenceCode, c, v, insideMarker, marker, text ) )
                    if logErrors: logging.error( _("Marker '{}' shouldn't appear within line after {} {}:{} in {}: {}").format( insideMarker, self.bookReferenceCode, c, v, marker, text ) )

        if validationErrors: self.errorDictionary['Validation Errors'] = validationErrors
    # end of validateUSFM


    def getField( self, fieldName ):
        """
        Extract a SFM field from the loaded book.
        """
        assert( fieldName and isinstance( fieldName, str ) )
        assert( self.lines )
        adjFieldName = self.USFMMarkers.toStandardMarker( fieldName )

        for marker,text,extras in self.lines:
            if marker == adjFieldName:
                assert( not extras )
                return text
    # end of getField


    def getBookName( self ):
        """
        Attempts to deduce a bookname from the loaded book.
        Use the English name as a last resort
        """
        from BibleBooksCodes import BibleBooksCodes
        assert( self.lines )

        header = self.getField( 'h' )
        if header is not None and header.isupper(): header = header.title()
        mt1 = self.getField( 'mt1' )
        if mt1 is not None and mt1.isupper(): mt1 = mt1.title()

        if header is not None: bookName = header
        elif mt1 is not None: bookName = mt1
        else: # no helpful fields in file
            bbc = BibleBooksCodes().loadData()
            bookName = bbc.getEnglishName_NR( self.bookReferenceCode )

        if Globals.verbosityLevel > 2: # Print our level of confidence
            if header is not None and header==mt1: assert( bookName == header ); print( "getBookName: header and main title are both '{}'".format( bookName ) )
            elif header is not None and mt1 is not None: print( "getBookName: header '{}' and main title '{}' are both different so selected '{}'".format( header, mt1, bookName ) )
            elif header is not None or mt1 is not None: print( "getBookName: only have one of header '{}' or main title '{}'".format( header, mt1 ) )
            else: print( "getBookName: no header or main title so used English book name '{}'".format( bookName ) )

        return bookName
    # end of getBookName


    def getVersification( self, logErrors=False ):
        """
        Get the versification of the book into a two lists of (c, v) tuples.
            The first list contains an entry for each chapter in the book showing the number of verses.
            The second list contains an entry for each missing verse in the book (not including verses that are missing at the END of a chapter).
        Note that all chapter and verse values are returned as strings not integers.
        """
        assert( self.lines )
        versificationErrors = []

        versification, omittedVerses, combinedVerses, reorderedVerses = [], [], [], []
        chapterText, chapterNumber, lastChapterNumber = '0', 0, 0
        verseText, verseNumberString, lastVerseNumberString = '0', '0', '0'
        for marker,text,extras in self.lines:
            #print( marker, text )
            if marker == 'c':
                if chapterNumber > 0:
                    versification.append( (chapterText, lastVerseNumberString,) )
                chapterText = text.strip()
                if ' ' in chapterText: # Seems that we can have footnotes here :)
                    versificationErrors.append( _("{} {}:{} Unexpected space in USFM chapter number field '{}'").format( self.bookReferenceCode, lastChapterNumber, lastVerseNumberString, chapterText, lastChapterNumber ) )
                    if logErrors: logging.info( _("Unexpected space in USFM chapter number field '{}' after chapter {} of {}").format( chapterText, lastChapterNumber, self.bookReferenceCode ) )
                    chapterText = chapterText.split( None, 1)[0]
                #print( "{} chapter {}".format( self.bookReferenceCode, chapterText ) )
                chapterNumber = int( chapterText)
                if chapterNumber != lastChapterNumber+1:
                    versificationErrors.append( _("{} ({} after {}) USFM chapter numbers out of sequence in Bible book").format( self.bookReferenceCode, chapterNumber, lastChapterNumber ) )
                    if logErrors: logging.error( _("USFM chapter numbers out of sequence in Bible book {} ({} after {})").format( self.bookReferenceCode, chapterNumber, lastChapterNumber ) )
                lastChapterNumber = chapterNumber
                verseText, verseNumberString, lastVerseNumberString = '0', '0', '0'
            elif marker == 'cp':
                versificationErrors.append( _("{} {}:{} Encountered cp field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, text ) )
                if logErrors: logging.warning( _("Encountered cp field {} after {}:{} of {}").format( text, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
            elif marker == 'v':
                if not text:
                    versificationErrors.append( _("{} {} Missing USFM verse number after {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString ) )
                    if logErrors: logging.warning( _("Missing USFM verse number after {} in chapter {} of {}").format( lastVerseNumberString, chapterNumber, self.bookReferenceCode ) )
                    continue
                try:
                    verseText = text.split( None, 1 )[0]
                except:
                    print( "verseText is '{}'".format(verseText) )
                    halt
                doneWarning = False
                for char in 'abcdefghijklmnopqrstuvwxyz[]()\\':
                    if char in verseText:
                        if not doneWarning:
                            versificationErrors.append( _("{} {} Removing letter(s) from USFM verse number {} in Bible book").format( self.bookReferenceCode, chapterText, verseText ) )
                            if logErrors: logging.info( _("Removing letter(s) from USFM verse number {} in Bible book {} {}").format( verseText, self.bookReferenceCode, chapterText ) )
                            doneWarning = True
                        verseText = verseText.replace( char, '' )
                if '-' in verseText or '–' in verseText: # we have a range like 7-9 with hyphen or en-dash
                    versificationErrors.append( _("{} {}:{} Encountered combined verses field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, verseText ) )
                    if logErrors: logging.info( _("Encountered combined verses field {} after {}:{} of {}").format( verseText, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
                    bits = verseText.replace('–','-').split( '-', 1 ) # Make sure that it's a hyphen then split once
                    verseNumberString = bits[0]
                    endVerseNumberString = bits[1]
                    if int(verseNumberString) >= int(endVerseNumberString):
                        versificationErrors.append( _("{} {} ({}-{}) USFM verse range out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                        if logErrors: logging.error( _("USFM verse range out of sequence in Bible book {} {} ({}-{})").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                    #else:
                    combinedVerses.append( (chapterText, verseText,) )
                elif ',' in verseText: # we have a range like 7,8
                    versificationErrors.append( _("{} {}:{} Encountered comma combined verses field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, verseText ) )
                    if logErrors: logging.info( _("Encountered comma combined verses field {} after {}:{} of {}").format( verseText, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
                    bits = verseText.split( ',', 1 )
                    verseNumberString = bits[0]
                    endVerseNumberString = bits[1]
                    if int(verseNumberString) >= int(endVerseNumberString):
                        versificationErrors.append( _("{} {} ({}-{}) USFM verse range out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                        if logErrors: logging.error( _("USFM verse range out of sequence in Bible book {} {} ({}-{})").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                    #else:
                    combinedVerses.append( (chapterText, verseText,) )
                else: # Should be just a single verse number
                    verseNumberString = verseText
                    endVerseNumberString = verseNumberString
                try:
                    verseNumber = int( verseNumberString )
                except:
                    versificationErrors.append( _("{} {} {} Invalid verse number digits in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString ) )
                    if logErrors: logging.error( _("Invalid verse number digits in Bible book {} {} {}").format( self.bookReferenceCode, chapterText, verseNumberString ) )
                    newString = ''
                    for char in verseNumberString:
                        if char.isdigit(): newString += char
                        else: break
                    verseNumber = int(newString) if newString else 999
                try:
                    lastVerseNumber = int( lastVerseNumberString )
                except:
                    newString = ''
                    for char in lastVerseNumberString:
                        if char.isdigit(): newString += char
                        else: break
                    lastVerseNumber = int(newString) if newString else 999
                if verseNumber != lastVerseNumber+1:
                    if verseNumber <= lastVerseNumber:
                        versificationErrors.append( _("{} {} ({} after {}) USFM verse numbers out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseText, lastVerseNumberString ) )
                        if logErrors: logging.warning( _("USFM verse numbers out of sequence in Bible book {} {} ({} after {})").format( self.bookReferenceCode, chapterText, verseText, lastVerseNumberString ) )
                        reorderedVerses.append( (chapterText, lastVerseNumberString, verseText,) )
                    else: # Must be missing some verse numbers
                        versificationErrors.append( _("{} {} Missing USFM verse number(s) between {} and {} in Bible book").format( self.bookReferenceCode, chapterText, lastVerseNumberString, verseNumberString ) )
                        if logErrors: logging.info( _("Missing USFM verse number(s) between {} and {} in Bible book {} {}").format( lastVerseNumberString, verseNumberString, self.bookReferenceCode, chapterText ) )
                        for number in range( lastVerseNumber+1, verseNumber ):
                            omittedVerses.append( (chapterText, str(number),) )
                lastVerseNumberString = endVerseNumberString
        versification.append( (chapterText, lastVerseNumberString,) ) # Append the verse count for the final chapter
        if reorderedVerses: print( "Reordered verses in", self.bookReferenceCode, "are:", reorderedVerses )
        if versificationErrors: self.errorDictionary['Versification Errors'] = versificationErrors
        return versification, omittedVerses, combinedVerses, reorderedVerses
    # end of getVersification


    def checkSFMs( self ):
        """Runs a number of checks on the USFM codes in this Bible book."""
        if 'SFMs' not in self.errorDictionary: self.errorDictionary['SFMs'] = OrderedDict()
        allAvailableNewlineMarkers = self.USFMMarkers.getNewlineMarkersList()

        newlineMarkerCounts, internalMarkerCounts, noteMarkerCounts = OrderedDict(), OrderedDict(), OrderedDict()
        #newlineMarkerCounts['Total'], internalMarkerCounts['Total'], noteMarkerCounts['Total'] = 0, 0, 0 # Put these first in the ordered dict
        newlineMarkerErrors, internalMarkerErrors, noteMarkerErrors = [], [], []
        functionalCounts = {}
        modifiedMarkerList = []
        c, v, section = '0', '0', ''
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                c = text.split()[0]; v = 0
                functionalCounts['Chapters'] = 1 if 'Chapters' not in functionalCounts else (functionalCounts['Chapters'] + 1)
            if marker=='v' and text:
                v = text.split()[0]
                functionalCounts['Verses'] = 1 if 'Verses' not in functionalCounts else (functionalCounts['Verses'] + 1)

            assert( marker in allAvailableNewlineMarkers ) # Should have been checked at load time
            newlineMarkerCounts[marker] = 1 if marker not in newlineMarkerCounts else (newlineMarkerCounts[marker] + 1)

            # Check the progression through the various sections
            newSection = self.USFMMarkers.markerOccursIn( marker )
            if newSection != section: # Check changes into new sections
                #print( section, marker, newSection )
                if section=='' and newSection!='Header': newlineMarkerErrors.append( _("{} {}:{} Missing Header section (went straight to {} section with {} marker)").format( self.bookReferenceCode, c, v, newSection, marker ) )
                elif section!='' and newSection=='Header': newlineMarkerErrors.append( _("{} {}:{} Didn't expect Header section after {} section (with {} marker)").format( self.bookReferenceCode, c, v, section, marker ) )
                if section=='Header' and newSection!='Introduction': newlineMarkerErrors.append( _("{} {}:{} Missing Introduction section (went straight to {} section with {} marker)").format( self.bookReferenceCode, c, v, newSection, marker ) )
                elif section!='Header' and newSection=='Introduction': newlineMarkerErrors.append( _("{} {}:{} Didn't expect Introduction section after {} section (with {} marker)").format( self.bookReferenceCode, c, v, section, marker ) )
                section = newSection

            # Note the newline SFM order -- create a list of markers in order (with duplicates combined, e.g., \v \v -> \v)
            if not modifiedMarkerList or modifiedMarkerList[-1] != marker: modifiedMarkerList.append( marker )

            # Check the internal SFMs
            if '\\' in text:
                #print( text )
                assert( '\\f ' not in text and '\\f*' not in text and '\\x ' not in text and '\\x*' not in text ) # The contents of these fields should now be in extras
                assert( '\\fr ' not in text and '\\ft' not in text and '\\xo ' not in text and '\\xt' not in text ) # The contents of these fields should now be in extras
                internalTextMarkers = []
                ixStart = text.find( '\\' )
                while( ixStart != -1 ):
                    ixSpace = text.find( ' ', ixStart+1 )
                    ixAsterisk = text.find( '*', ixStart+1 )
                    if ixSpace==-1 and ixAsterisk==-1: ixEnd = len(text) - 1
                    elif ixSpace!=-1 and ixAsterisk==-1: ixEnd = ixSpace
                    elif ixSpace==-1 and ixAsterisk!=-1: ixEnd = ixAsterisk+1 # The asterisk is considered part of the marker
                    else: ixEnd = min( ixSpace, ixAsterisk+1 ) # Both were found
                    internalMarker = text[ixStart+1:ixEnd]
                    internalTextMarkers.append( internalMarker )
                    ixStart = text.find( '\\', ixStart+1 )
                #print( "Found", internalTextMarkers )
                hierarchy = []
                for internalMarker in internalTextMarkers: # count the SFMs and check the hierarchy
                    internalMarkerCounts[internalMarker] = 1 if internalMarker not in internalMarkerCounts else (internalMarkerCounts[internalMarker] + 1)
                    if internalMarker and internalMarker[-1] == '*':
                        closedMarkerText = internalMarker[:-1]
                        shouldBeClosed = self.USFMMarkers.markerShouldBeClosed( closedMarkerText )
                        if shouldBeClosed == 'N': internalMarkerErrors.append( _("{} {}:{} Marker {} cannot be closed").format( self.bookReferenceCode, c, v, closedMarkerText ) )
                        elif hierarchy and hierarchy[-1] == closedMarkerText: hierarchy.pop(); continue # all ok
                        elif closedMarkerText in hierarchy: internalMarkerErrors.append( _("{} {}:{} Internal markers appear to overlap: {}").format( self.bookReferenceCode, c, v, internalTextMarkers ) )
                        else: internalMarkerErrors.append( _("{} {}:{} Unexpected internal closing marker: {} in {}").format( self.bookReferenceCode, c, v, internalMarker, internalTextMarkers ) )
                    else: # it's not a closing marker
                        shouldBeClosed = self.USFMMarkers.markerShouldBeClosed( internalMarker )
                        if shouldBeClosed == 'N': continue # N for never
                        else: hierarchy.append( internalMarker ) # but what if it's optional ????????????????????????????????
                if hierarchy: # it should be empty
                    internalMarkerErrors.append( _("{} {}:{} These markers {} appear not to be closed in {}").format( self.bookReferenceCode, c, v, hierarchy, internalTextMarkers ) )

            if extras:
                #print( extras )
                extraMarkers = []
                for extraType, extraIndex, extraText in extras:
                    assert( extraText ) # Shouldn't be blank
                    assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    #print( self.bookReferenceCode, c, v, extraIndex, len(text), text )
                    ( 0 <= extraIndex <= len(text) )
                    assert( extraType in ('fn','xr',) )
                    assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras
                    thisExtraMarkers = []
                    if '\\\\' in extraText:
                        noteMarkerErrors.append( _("{} {}:{} doubled backslash characters in  {}: {}").format( self.bookReferenceCode, c, v, extraType, extraText ) )
                        while '\\\\' in extraText: extraText = extraText.replace( '\\\\', '\\' )
                    if '  ' in extraText:
                        noteMarkerErrors.append( _("{} {}:{} doubled space characters in  {}: {}").format( self.bookReferenceCode, c, v, extraType, extraText ) )
                        while '  ' in extraText: extraText = extraText.replace( '  ', ' ' )
                    if '\\' in extraText:
                        #print( extraText )
                        assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # These beginning and end markers should already be removed
                        thisExtraMarkers = []
                        ixStart = extraText.find( '\\' )
                        while( ixStart != -1 ):
                            ixSpace = extraText.find( ' ', ixStart+1 )
                            ixAsterisk = extraText.find( '*', ixStart+1 )
                            if ixSpace==-1 and ixAsterisk==-1: ixEnd = len(extraText) - 1
                            elif ixSpace!=-1 and ixAsterisk==-1: ixEnd = ixSpace
                            elif ixSpace==-1 and ixAsterisk!=-1: ixEnd = ixAsterisk+1 # The asterisk is considered part of the marker
                            else: ixEnd = min( ixSpace, ixAsterisk+1 ) # Both were found
                            extraMarker = extraText[ixStart+1:ixEnd]
                            thisExtraMarkers.append( extraMarker )
                            ixStart = extraText.find( '\\', ixStart+1 )
                        #print( "Found", thisExtraMarkers )
                        hierarchy = []
                        for extraMarker in thisExtraMarkers: # count the SFMs and check the hierarchy
                            noteMarkerCounts[extraMarker] = 1 if extraMarker not in noteMarkerCounts else (noteMarkerCounts[extraMarker] + 1)
                            if extraMarker and extraMarker[-1] == '*':
                                closedMarkerText = extraMarker[:-1]
                                shouldBeClosed = self.USFMMarkers.markerShouldBeClosed( closedMarkerText )
                                #print( "here with", extraType, extraText, thisExtraMarkers, hierarchy, closedMarkerText, shouldBeClosed )
                                if shouldBeClosed == 'N': noteMarkerErrors.append( _("{} {}:{} Marker {} cannot be closed").format( self.bookReferenceCode, c, v, closedMarkerText ) )
                                elif hierarchy and hierarchy[-1] == closedMarkerText: hierarchy.pop(); continue # all ok
                                elif closedMarkerText in hierarchy: noteMarkerErrors.append( _("{} {}:{} Internal markers appear to overlap: {}").format( self.bookReferenceCode, c, v, thisExtraMarkers ) )
                                else: noteMarkerErrors.append( _("{} {}:{} Unexpected note closing marker: {} in {}").format( self.bookReferenceCode, c, v, extraMarker, thisExtraMarkers ) )
                            else: # it's not a closing marker -- for extras, it probably automatically closes the previous marker
                                shouldBeClosed = self.USFMMarkers.markerShouldBeClosed( extraMarker )
                                if shouldBeClosed == 'N': continue # N for never
                                elif hierarchy: # Maybe the previous one is automatically closed by this one
                                    previousMarker = hierarchy[-1]
                                    previousShouldBeClosed = self.USFMMarkers.markerShouldBeClosed( previousMarker )
                                    if previousShouldBeClosed == 'S': # S for sometimes
                                        hierarchy.pop() # That they are not overlapped, but rather that the previous one is automatically closed by this one
                                hierarchy.append( extraMarker )
                        if len(hierarchy)==1 and self.USFMMarkers.markerShouldBeClosed(hierarchy[0])=='S': # Maybe the last marker can be automatically closed
                            hierarchy.pop()
                        if hierarchy: # it should be empty
                            #print( "here with remaining", extraType, extraText, thisExtraMarkers, hierarchy )
                            noteMarkerErrors.append( _("{} {}:{} These note markers {} appear not to be closed in {}").format( self.bookReferenceCode, c, v, hierarchy, extraText ) )
                    adjExtraMarkers = thisExtraMarkers
                    for uninterestingMarker in ('it*','it','nd*','nd','sc*','sc','bk*','bk'): # Remove character formatting markers so we can check the footnote/xref hierarchy
                        while uninterestingMarker in adjExtraMarkers: adjExtraMarkers.remove( uninterestingMarker )
                    if (extraType=='fn' and adjExtraMarkers not in footnoteSets) \
                    or (extraType=='xr' and adjExtraMarkers not in xrefSets):
                        #print( "Got", extraType, extraText, thisExtraMarkers )
                        if thisExtraMarkers: noteMarkerErrors.append( _("{} {}:{} Unusual {} marker set: {} in {}").format( self.bookReferenceCode, c, v, extraType, thisExtraMarkers, extraText ) )
                        else: noteMarkerErrors.append( _("{} {}:{} Missing {} formatting in {}").format( self.bookReferenceCode, c, v, extraType, extraText ) )

                    if len(extraText) > 2 and extraText[1] == ' ':
                        leaderChar = extraText[0] # Leader character should be followed by a space
                        if extraType == 'fn':
                            functionalCounts['Footnotes'] = 1 if 'Footnotes' not in functionalCounts else (functionalCounts['Footnotes'] + 1)
                            leaderName = "Footnote leader '{}'".format( leaderChar )
                            functionalCounts[leaderName] = 1 if leaderName not in functionalCounts else (functionalCounts[leaderName] + 1)
                        elif extraType == 'xr':
                            functionalCounts['Cross-References'] = 1 if 'Cross-References' not in functionalCounts else (functionalCounts['Cross-References'] + 1)
                            leaderName = "Cross-reference leader '{}'".format( leaderChar )
                            functionalCounts[leaderName] = 1 if leaderName not in functionalCounts else (functionalCounts[leaderName] + 1)
                    else: noteMarkerErrors.append( _("{} {}:{} {} seems to be missing a leader character in {}").format( self.bookReferenceCode, c, v, extraType, extraText ) )


        # Check the relative ordering of newline markers
        #print( "modifiedMarkerList", modifiedMarkerList )
        if modifiedMarkerList[0] != 'id':
            newlineMarkerErrors.append( _("{} First USFM field in file should have been 'id' not '{}'").format( self.bookReferenceCode, modifiedMarkerList[0] ) )
        for otherHeaderMarker in ( 'ide','sts', ):
            if otherHeaderMarker in modifiedMarkerList and modifiedMarkerList.index(otherHeaderMarker) > 8:
                newlineMarkerErrors.append( _("{} {}:{} USFM '{}' field in file should have been earlier in {}...").format( self.bookReferenceCode, c, v, otherHeaderMarker, modifiedMarkerList[:10] ) )
        if 'mt2' in modifiedMarkerList: # Must be before or after a mt1
            ix = modifiedMarkerList.index( 'mt2' )
            if (ix==0 or modifiedMarkerList[ix-1]!='mt1') and (ix==len(modifiedMarkerList)-1 or modifiedMarkerList[ix+1]!='mt1'):
                newlineMarkerErrors.append( _("{} Expected mt2 marker to be next to an mt1 marker in {}...").format( self.bookReferenceCode, modifiedMarkerList[:10] ) )

        if newlineMarkerErrors: self.errorDictionary['SFMs']['Newline Marker Errors'] = newlineMarkerErrors
        if internalMarkerErrors: self.errorDictionary['SFMs']['Internal Marker Errors'] = internalMarkerErrors
        if noteMarkerErrors: self.errorDictionary['SFMs']['Footnote and Cross-Reference Marker Errors'] = noteMarkerErrors
        if modifiedMarkerList: self.errorDictionary['SFMs']['Modified Marker List'] = modifiedMarkerList
        if 1: # new code
            if newlineMarkerCounts:
                total = 0
                for marker in newlineMarkerCounts: total += newlineMarkerCounts[marker]
                self.errorDictionary['SFMs']['All Newline Marker Counts'] = newlineMarkerCounts
                self.errorDictionary['SFMs']['All Newline Marker Counts']['Total'] = total
            if internalMarkerCounts:
                total = 0
                for marker in internalMarkerCounts: total += internalMarkerCounts[marker]
                self.errorDictionary['SFMs']['All Text Internal Marker Counts'] = internalMarkerCounts
                self.errorDictionary['SFMs']['All Text Internal Marker Counts']['Total'] = total
            if noteMarkerCounts:
                total = 0
                for marker in noteMarkerCounts: total += noteMarkerCounts[marker]
                self.errorDictionary['SFMs']['All Footnote and Cross-Reference Internal Marker Counts'] = noteMarkerCounts
                self.errorDictionary['SFMs']['All Footnote and Cross-Reference Internal Marker Counts']['Total'] = total
        else: # old code
            if len(newlineMarkerCounts) > 1: # We started with a 'Total' entry of zero
                for marker in newlineMarkerCounts: newlineMarkerCounts['Total'] += newlineMarkerCounts[marker] # Add up the totals
                self.errorDictionary['SFMs']['All Newline Marker Counts'] = newlineMarkerCounts
            if len(internalMarkerCounts) > 1: # We started with a 'Total' entry of zero
                for marker in internalMarkerCounts: internalMarkerCounts['Total'] += internalMarkerCounts[marker] # Add up the totals
                self.errorDictionary['SFMs']['All Text Internal Marker Counts'] = internalMarkerCounts
            if len(noteMarkerCounts) > 1: # We started with a 'Total' entry of zero
                for marker in noteMarkerCounts: noteMarkerCounts['Total'] += noteMarkerCounts[marker] # Add up the totals
                self.errorDictionary['SFMs']['All Footnote and Cross-Reference Internal Marker Counts'] = noteMarkerCounts
        if functionalCounts: self.errorDictionary['SFMs']['Functional Marker Counts'] = functionalCounts
    # end of checkSFMs


    def checkCharacters( self ):
        """Runs a number of checks on the characters used."""
        if 'Characters' not in self.errorDictionary: self.errorDictionary['Characters'] = OrderedDict()

        characterCounts, letterCounts, punctuationCounts = {}, {}, {} # We don't care about the order in which they appeared
        c, v = '0', '0'
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = 0
            if marker=='v' and text: v = text.split()[0]

            if self.USFMMarkers.isPrinted( marker ):
                for char in text:
                    lcChar = char.lower()
                    characterCounts[char] = 1 if char not in characterCounts else characterCounts[char] + 1
                    if char.isalpha():
                        letterCounts[lcChar] = 1 if lcChar not in letterCounts else letterCounts[lcChar] + 1
                    elif not char.isalnum(): # Assume it's punctuation
                        punctuationCounts[char] = 1 if char not in punctuationCounts else punctuationCounts[char] + 1

        # Add up the totals
        if characterCounts:
            total = 0
            for character in characterCounts: total += characterCounts[character]
            self.errorDictionary['Characters']['All Character Counts'] = characterCounts
            self.errorDictionary['Characters']['All Character Counts']['Total'] = total
        if letterCounts:
            total = 0
            for character in letterCounts: total += letterCounts[character]
            self.errorDictionary['Characters']['Letter Counts'] = letterCounts
            self.errorDictionary['Characters']['Letter Counts']['Total'] = total
        if punctuationCounts:
            total = 0
            for character in punctuationCounts: total += punctuationCounts[character]
            self.errorDictionary['Characters']['Punctuation Counts'] = punctuationCounts
            self.errorDictionary['Characters']['Punctuation Counts']['Total'] = total
    # end of checkCharacters


    def checkWords( self ):
        """Runs a number of checks on the words used."""
        leadingPunctChars = '\'"‘“([{<'
        trailingPunctChars = ',.\'"’”?)!;:]}>'

        def stripWordPunctuation( word ):
            """Removes leading and trailing punctuation from a word.
                Returns the "clean" word."""
            while word and word[0] in leadingPunctChars:
                word = word[1:] # Remove leading punctuation
            while word and word[-1] in trailingPunctChars:
                word = word[:-1] # Remove trailing punctuation
            return word
        # end of stripWordPunctuation

        if 'Words' not in self.errorDictionary: self.errorDictionary['Words'] = {} # Don't think it needs to be OrderedDict()
        allowedWordPunctuation = '-'
        internalSFMsToRemove = ('\\bk*','\\bk','\\it*','\\it','\\wd*','\\wd') # List longest first

        # Count all the words
        wordCounts, caseInsensitiveWordCounts = {}, {}
        wordErrors = []
        c, v = '0', '0'
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = 0
            if marker=='v' and text: v = text.split()[0]

            if self.USFMMarkers.isPrinted( marker ):
                assert( '—' != '–' )
                words = text.replace('—',' ').replace('–',' ').split() # Treat em-dash and en-dash as word break characters
                for rawWord in words:
                    word = rawWord
                    for internalMarker in internalSFMsToRemove: word = word.replace( internalMarker, '' )
                    word = stripWordPunctuation( word )
                    if word and not word[0].isalnum():
                        wordErrors.append( _("{} {}:{} Have unexpected character starting word '{}'").format( self.bookReferenceCode, c, v, word ) )
                        word = word[1:]
                    if word: # There's still some characters remaining after all that stripping
                        if Globals.verbosityLevel > 3:
                            for j,char in enumerate(word):
                                if not char.isalnum() and (j==0 or j==len(word)-1 or char not in allowedWordPunctuation):
                                    wordErrors.append( _("{} {}:{} Have unexpected '{}' in word '{}'").format( self.bookReferenceCode, c, v, char, word ) )
                        wordCounts[word] = 1 if word not in wordCounts else wordCounts[word] + 1
                        lcWord = word.lower()
                        caseInsensitiveWordCounts[lcWord] = 1 if lcWord not in caseInsensitiveWordCounts else caseInsensitiveWordCounts[lcWord] + 1

        # Add up the totals
        if wordCounts:
            total = 0
            for word in wordCounts: total += wordCounts[word]
            self.errorDictionary['Words']['All Word Counts'] = wordCounts
            self.errorDictionary['Words']['All Word Counts']['--Total--'] = total
        if caseInsensitiveWordCounts:
            total = 0
            for word in caseInsensitiveWordCounts: total += caseInsensitiveWordCounts[word]
            self.errorDictionary['Words']['Case Insensitive Word Counts'] = caseInsensitiveWordCounts
            self.errorDictionary['Words']['Case Insensitive Word Counts']['--Total--'] = total
        if wordErrors: self.errorDictionary['Words']['Possible Word Errors'] = wordErrors
    # end of checkWords


    def check( self ):
        """Runs a number of checks on the book and returns the error dictionary."""
        self.getVersification() # This checks CV ordering, etc.
        self.checkSFMs()
        self.checkCharacters()
        self.checkWords()
        return self.errorDictionary
    # end of check


    def getErrors( self ):
        """Returns the error dictionary."""
        return self.errorDictionary
# end of class USFMBibleBook


def main():
    """
    Demonstrate reading and processing some Bible databases.
    """
    import USFMFilenames

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    logErrors = False

    name, encoding, testFolder = "Matigsalug", "utf-8", "/mnt/Data/Matigsalug/Scripture/MBTV/" # You can put your test folder here
    if os.access( testFolder, os.R_OK ):
        if Globals.verbosityLevel > 1: print( _("Loading {} from {}...").format( name, testFolder ) )
        fileList = USFMFilenames.USFMFilenames( testFolder ).getActualFilenames()
        for bookReferenceCode,filename in fileList:
            UBB = USFMBibleBook()
            UBB.load( bookReferenceCode, testFolder, filename, encoding, logErrors )
            print( "  ID is '{}'".format( UBB.getField( 'id' ) ) )
            print( "  Header is '{}'".format( UBB.getField( 'h' ) ) )
            print( "  Main titles are '{}' and '{}'".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
            print( UBB )
            UBB.validateUSFM()
            result = UBB.getVersification ()
            #print( result )
            #print( UBB.getErrors() )
            UBErrors = UBB.check()
            #print( UBErrors )
    else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

if __name__ == '__main__':
    main()
## End of USFMBibleBook.py
