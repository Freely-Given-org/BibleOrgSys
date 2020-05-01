#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# TextFile.py
#
# Text file read/edit module
#
# Copyright (C) 2016 Robert Hunt
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
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module for reading and parsing simple text control files.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2016-12-28' # by RJH
SHORT_PROGRAM_NAME = "TextFile"
PROGRAM_NAME = "Text File"
PROGRAM_VERSION = '0.03'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


import os.path
import logging

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint



class TextFile:
    """
    """
    def __init__( self, filepath=None, folderpath=None, filename=None, encoding=None, autoLoad=True ):
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel>2:
            vPrint( 'Quiet', debuggingThisModule, "TextFile.__init__( {!r}, {!r}, {!r}, {!r}, {} )".format( filepath, Folderpath, filename, encoding, autoLoad ) )

        self.encoding = encoding if encoding else 'utf-8'
        if folderpath and filename:
            assert filepath is None
            self.folderpath, self.filename = folderpath, filename
            self.filepath = os.path.join( self.folderpath, self.filename )
        elif filepath:
            assert folderpath is None and filename is None
            self.filepath = filepath
            self.folderpath, self.filename = os.path.split( self.filepath )
        else:
            logging.critical( "TextFile.__init__ seems to have too little or too much information: {} {} {}".format( filepath, folderpath, filename ) )

        if autoLoad:
            with open( self.filepath, mode='rt', encoding=encoding ) as myFile: # Automatically closes the file when done
                self.fileText = myFile.read()
        else: self.fileText = None
        self.changed = False
    # end of TextFile.__init__


    #def __enter__( self ):
        #return self
    # end of TextFile.__enter__


    def replace( self, findString, replaceString, replaceCount=None ):
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel>2:
            vPrint( 'Quiet', debuggingThisModule, "TextFile.replace( {!r}, {!r}, {} )".format( findString, replaceString, replaceCount ) )
        assert self.fileText is not None

        self.originalText = self.fileText
        if replaceCount is None: self.fileText = self.fileText.replace( findString, replaceString )
        else: self.fileText = self.fileText.replace( findString, replaceString, replaceCount )
        if self.fileText!= self.originalText: self.changed = True
    # end of TextFile.replace


    def save( self ):
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel>2:
            vPrint( 'Quiet', debuggingThisModule, "TextFile.save()" )
        assert self.fileText is not None

        if self.changed:
            with open( self.filepath, mode='wt', encoding=self.encoding ) as myFile: # Automatically closes the file when done
                myFile.write( self.fileText )
            self.changed = False
    # end of TextFile.save


    def saveAs( self, filepath=None, folderpath=None, filename=None, encoding=None ):
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel>1:
            vPrint( 'Quiet', debuggingThisModule, "TextFile.saveAs( {!r}, {!r}, {!r}, {} )".format( filepath, folderpath, filename, encoding ) )
        assert self.fileText is not None

        encoding = encoding if encoding else 'utf-8'
        if folderpath and filename:
            assert filepath is None
            filepath = os.path.join( folderpath, filename )
        elif filepath:
            assert folderpath is None and filename is None
            folderpath, filename = os.path.split( filepath )
        else:
            logging.critical( "TextFile.saveAs seems to have too little or too much information: {} {} {}".format( filepath, folderpath, filename ) )

        with open( filepath, mode='wt', encoding=encoding ) as myFile: # Automatically closes the file when done
            myFile.write( self.fileText )
    # end of TextFile.saveAs


    def __exit__( self, exc_type, exc_value, traceback ):
        if self.changed: self.save()
    # end of TextFile.__exit__


    def __del__( self ):
        if self.changed:
            logging.critical( "TextFile: {!r} wasn't saved!!!".format( self.filename ) )
    # end of TextFile.__del__
# end of class TextFile



def briefDemo() -> None:
    """
    Demo program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    #tf = TextFile( 'TextFile.py' ) # Read myself!
    #tf.replace( "TextFile", "ABRACADABRA" )
    #vPrint( 'Quiet', debuggingThisModule, tf.fileText )
    ##tf.saveAs( "/tmp/fred.py" )

    tf = TextFile( folderpath=os.path.dirname(__file__), filename='TextFile.py' ) # Read myself!
    tf.replace( "TextFile", "ABRACADABRA" )
    vPrint( 'Quiet', debuggingThisModule, tf.fileText )
    #tf.saveAs( "/tmp/fred.py" )

    #with TextFile( 'TextFile.py' ) as tf:
        #tf.replace( "TextFile", "ABRACADABRA-DOOOOOOOOOOO" )
# end of fullDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of TextFile.py
