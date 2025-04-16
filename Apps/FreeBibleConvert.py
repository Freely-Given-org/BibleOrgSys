#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# FreeBibleConvert.py
#
# Given a text export of the Free Bible New Testament, convert it to USFM2 files.
#
# Copyright (C) 2018 Robert Hunt
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
Given the MediaWiki text export of the Free Bible New Testament from LibreOffice,
    convert it to USFM2 files.
"""

from gettext import gettext as _
import os.path
import logging
from pathlib import Path
from datetime import datetime

if __name__ == '__main__':
    import sys
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports
# BibleOrgSys imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Misc.NoisyReplaceFunctions import noisyFind, noisyRegExFind, \
                                    noisyReplaceAll, noisyDeleteAll, noisyRegExReplaceAll


LAST_MODIFIED_DATE = '2018-12-02' # by RJH
SHORT_PROGRAM_NAME = "FreeBibleConverter"
PROGRAM_NAME = "FreeBible Converter"
PROGRAM_VERSION = '0.09'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


ID_LINE = "Free Bible Version New Testament Version 2.1.1"

BIBLES_FOLDERPATH = Path( '/mnt/SSDs/Bibles/' )

#INPUT_FILEPATH = '/home/robert/FBVNT2.1.1.LOExport.txt'
#INPUT_FILEPATH = '/Users/Robert/Desktop/FBVNT2.1.1.LOExport.txt'
INPUT_FILEPATH = BIBLES_FOLDERPATH.joinpath( 'English translations/Free Bible/FBVNT2.1.1.txt' )

# Subfolder USFM/ gets added to OUTPUT_FOLDERPATH for writing the individual USFM files
OUTPUT_FOLDERPATH = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'FreeBibleConversion/' )
#OUTPUT_FOLDERPATH = os.path.join( BIBLES_FOLDERPATH.joinpath( 'English translations/Free Bible/' )


def splitAndWriteBooks( entireBibleText, folderpath ):
    """
    Given a text string containing the entire Bible document,
        split it by \id lines and write out the individual files
        into the given folder.

    Also can be customized to do specific formatting corrections
        for specific books if necessary.
    """
    writtenCount = 0
    splitOnString = '\\id '
    for splitText in entireBibleText.split( splitOnString ):
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "here", writtenCount, repr(splitText[:40]) )
        if not splitText: continue # coz it gets a blank one right at the beginning
        assert splitText[3] == ' '
        bookID = splitText[:3]
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Got book id", repr(bookID) )
        assert bookID in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodes( toUpper=True )
        splitText = splitOnString + splitText

        # Last chance to fix things up (e.g., by bookID)
        if splitText[-1] != '\n': splitText += '\n' # Ensure that we have a final newline character in each file
        # if bookID == 'FRT':

        filepath = os.path.join( folderpath, 'FBV_{}.usfm'.format( bookID ) )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "Writing {}…".format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as bookFile:
            bookFile.write( splitText )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "  {} characters ({} lines) written".format( len(splitText), splitText.count('\n') ) )
        writtenCount += 1
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} books written to {}".format( writtenCount, folderpath ) )
# end of FreeBibleConvert.splitAndWriteBooks


def briefDemo() -> None:
    """
    Demo program to handle command line parameters and run a few functions.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    sampleText = "This is a lot of nonsense"
    sampleText = noisyReplaceAll( sampleText, ' lot ', ' great, pig pile ' )
    sampleText = noisyRegExReplaceAll( sampleText, ' p(\S)', ' b\\1' ) # pig to big hopefully
    noisyFind( sampleText, 'bile', logging.critical )

    if BibleOrgSysGlobals.verbosityLevel>0: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, sampleText )
# end of FreeBibleConvert.main


def main() -> None:
    """
    Main program to handle command line parameters
        and then convert the FBV text file.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Loading {}…").format( INPUT_FILEPATH ) )
    with open( INPUT_FILEPATH, 'rt', encoding='utf-8' ) as textFile:
        originalText = textFile.read()
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("  Loaded {:,} characters ({:,} lines)").format( len(originalText), originalText.count('\n') ) )

    # Preparation by inserting some lines at the beginning
    entireText = '\\id FRT -- {}\n'.format( ID_LINE )
    entireText += '\\rem Converted by {!r}\n'.format( f'{PROGRAM_NAME_VERSION} {_("last modified")} {LAST_MODIFIED_DATE}' )
    entireText += '\\rem Converted from \'{}\'\n'.format( INPUT_FILEPATH )
    entireText += '\\rem Converted {}\n'.format( datetime.now() )
    entireText += originalText

    # More preparation
    entireText = noisyReplaceAll( entireText, '\n\r', '\n' ) # Makes it easier later
    entireText = noisyReplaceAll( entireText, '\r\n', '\n' ) # Makes it easier later
    entireText = noisyReplaceAll( entireText, '﻿', '' ) # Remove zero-width space or whatever it is
    entireText = noisyReplaceAll( entireText, '  ', ' ', loop=True ) # Consolidate spaces
    entireText = noisyReplaceAll( entireText, '<div style="text-align:center;"></div>', '' ) # Remove blank lines at beginning
    entireText = entireText.replace( "<div style=\"text-align:center;\">'''Free Bible Version '''</div>", '\\mt1 Free Bible Version', 1 )
    entireText = entireText.replace( "<div style=\"text-align:center;\">'''New Testament'''</div>", '\\mt2 New Testament', 1 )
    entireText = noisyReplaceAll( entireText, '<div style="margin-left:0cm;margin-right:0cm;"><sup>', '<sup>' )

    # Fix specific mistakes and inconsistencies/irregularities
    entireText = noisyReplaceAll( entireText, '<ref name="ftn720"> Referring to Sarah', '<ref name="ftn720"> 4:23. Referring to Sarah' ) # GAL
    entireText = noisyReplaceAll( entireText, '“</sup>', '</sup>“' )
    entireText = noisyReplaceAll( entireText, '<sup> <ref ', '<ref ' )
    entireText = noisyReplaceAll( entireText, '"><sup> ', '"> ' )
    entireText = noisyReplaceAll( entireText, '</sup></ref>', '</ref>' )
    entireText = noisyReplaceAll( entireText, '<sup> </sup>', ' ' )
    entireText = noisyDeleteAll( entireText, '<sup></sup>' )
    entireText = noisyRegExReplaceAll( entireText, "<ref name=\"ftn(\\d{1,3})\">'' ", "’<ref name=\"ftn\\1\"> " )
    entireText = noisyReplaceAll( entireText, "''</ref>", "</ref>" )
    entireText = noisyRegExReplaceAll( entireText, '<span style="color:#0000ff;"><u>(\\S)</u></span>', '\\1' ) # Often surrounding a comma
    entireText = noisyRegExReplaceAll( entireText, '<span style="color:#0000ff;">(\\S)</span>', '\\1' ) # Often surrounding a comma
    entireText = noisyRegExReplaceAll( entireText, '<span style="color:#800080;">( )</span>', '\\1' ) # Don't need a regex for this one
    entireText = noisyRegExReplaceAll( entireText, '<nowiki>(.+?)</nowiki>', '\\1' )

    # Book divisions
    entireText = noisyRegExReplaceAll( entireText,
        "<div style=\"text-align:center;\">'''Free Bible Version(.+?)'''</div>",
        '\n\\\\id \\1' )
    entireText = noisyRegExReplaceAll( entireText,
        "\n<div style=\"text-align:center;\">'''Free Bible Version'''</div>\n\n?<div style=\"text-align:center;\">'''(.+?)'''</div>",
        '\n\\\\id \\1' )

    entireText = noisyRegExReplaceAll( entireText, '<div style="text-align:center;">(.+?)</div>', '\\\\pc \\1' ) # Centred paragraphs

    # Chapters, verses, and footnotes
    entireText = noisyRegExReplaceAll( entireText, "\\n\\n'''(\\d{1,3}) ?'''", '\\n\\\\c \\1\\n\\\\p' ) # Could be wrong if some chapters don't start a new paragraph
    entireText = noisyRegExReplaceAll( entireText, '<sup> ?(\\d{1,3}) ?</sup>', '\\n\\\\v \\1 ' )
    entireText = noisyRegExReplaceAll( entireText, '<ref name="ftn(\\d{1,4})"> ?', '\\\\f + \\\\fXXX ' )
    entireText = noisyRegExReplaceAll( entireText, '\\\\fXXX (\\d{1,3}:\\d{1,3}\\.) ?', '\\\\fr \\1 \\\\ft ' )
    entireText = noisyRegExReplaceAll( entireText, '\\\\fXXX (\\d{1,3}\\.) ?', '\\\\fr \\1 \\\\ft ' ) # For single chapter books
    entireText = noisyRegExReplaceAll( entireText, '\\\\fXXX (\\d{1,3}:\\d{1,3}) ?', '\\\\fr \\1. \\\\ft ' ) # without the final period
    entireText = noisyRegExReplaceAll( entireText, '\\\\fXXX (\\d{1,3}) ?', '\\\\fr \\1. \\\\ft ' ) # For single chapter books
    entireText = noisyRegExReplaceAll( entireText, '\\\\fXXX (.+?\\.) ?', '\\\\fr \\1 \\\\ft ' ) # Other forms, e.g., 2:3a-5.
    entireText = noisyRegExReplaceAll( entireText, '\\\\fXXX ([^\\.]+?) ?', '\\\\fr \\1. \\\\ft ' ) # Other forms, e.g., 2:3a-5.
    entireText = noisyReplaceAll( entireText, '</ref>', '\\f*' )
    entireText = noisyReplaceAll( entireText, '\n\\f*', '\\f*', loop=True )
    entireText = noisyReplaceAll( entireText, ' \\f*', '\\f*', loop=True )

    # Some extra paragraphs
    entireText = noisyReplaceAll( entireText, '\n\n\\v ', '\n\\p\n\\v ' )
    entireText = noisyRegExReplaceAll( entireText, '\n([^\n\\\\<])', '\n\\\\p \\1' )

    # Some character stuff
    entireText = noisyRegExReplaceAll( entireText, '\n<u>(.+?)</u>\n', '\n\\\\s \\1\n' ) # in BAK part
    entireText = noisyReplaceAll( entireText, '<u>', '\\em ')
    entireText = noisyReplaceAll( entireText, '</u>', '\\em*')
    entireText = noisyRegExReplaceAll( entireText, "([ “])''", "\\1‘" ) # Single opening quote
    entireText = noisyRegExReplaceAll( entireText, "''([ \\.,”—])", "’\\1" ) # Single closing quote
    entireText = noisyReplaceAll( entireText, '“into Moses"', '“into Moses”' )
    # Stuff at end of file
    entireText = noisyReplaceAll( entireText,
        '\n\\v 21 May the grace of the Lord Jesus be with the believers. Amen.\n',
        '\n\\v 21 May the grace of the Lord Jesus be with the believers. Amen.'
        '\n\\id BAK -- {}\n\\h Back matter\n\\toc1 Back matter\n'.format( ID_LINE ) )
    entireText = noisyRegExReplaceAll( entireText, '<div style="margin-left:0cm;margin-right:0cm;">(.+?)</div>', '\\\\m \\1' )
    entireText = noisyRegExReplaceAll( entireText, '\n<u>(.+?)</u>\n', '\n\\\\s1 \\1' )
    entireText = noisyReplaceAll( entireText, '<references/>', '' )

    # Check
    noisyFind( entireText, '<', logging.error ); noisyFind( entireText, '>', logging.error )

    # Clean-up left-overs
    entireText = noisyDeleteAll( entireText, '</div>' )
    entireText = noisyDeleteAll( entireText, '<sup>' )
    entireText = noisyDeleteAll( entireText, '</sup>' )

    # Clean-up duplicates
    entireText = noisyReplaceAll( entireText, '  ', ' ', loop=True )
    entireText = noisyReplaceAll( entireText, '\n\n', '\n', loop=True )
    entireText = noisyReplaceAll( entireText, ' \n', '\n', loop=True )

    # Adjust book IDs, and insert h,toc1,toc2,toc3,mt1
    vPrint( 'Info', DEBUGGING_THIS_MODULE, "Adjusting book names and IDs…" )
    for name,abbrev,bookID in ( ('Matthew','Mat','MAT'), ('Mark','Mrk','MRK'), ('Luke','Luk','LUK'), ('John','Jhn','JHN'), ('Acts','Act','ACT'),
                        ('Romans','Rom','ROM'), ('First Corinthians','1 Cor','1CO'), ('Second Corinthians','2 Cor','2CO'),
                        ('Galatians','Gal','GAL'), ('Ephesians','Eph','EPH'), ('Philippians','Php','PHP'), ('Colossians','Col','COL'),
                        ('First Thessalonians','1 Thess','1TH'), ('Second Thessalonians','2 Thess','2TH'), ('First Timothy','1 Tim','1TI'), ('Second Timothy','2 Tim','2TI'),
                        ('Titus','Tit','TIT'), ('Philemon','Phm','PHM'), ('Hebrews','Heb','HEB'), ('James','Jas','JAS'),
                        ('First Peter','1 Pet','1PE'), ('Second Peter','2 Pet','2PE'),
                        ('First John','1 Jhn','1JN'), ('Second John','2 Jhn','2JN'), ('Third John','3 Jhn','3JN'),
                        ('Jude','Jud','JUD'), ('Revelation','Rev','REV'), ):
        shortenedName = name.replace('First','1').replace('Second','2').replace('Third','3')
        entireText = entireText.replace( '\\id '+name,
                                '\\id {} -- {}'.format( bookID, ID_LINE ) + \
                                '\n\\h {}'.format( shortenedName ) + \
                                '\n\\toc1 {}'.format( name ) + \
                                '\n\\toc2 {}'.format( shortenedName ) + \
                                '\n\\toc3 {}'.format( abbrev ) + \
                                '\n\\mt1 {}'.format( name )
                                )

    # Check again
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Final checks before writing files…" )
    noisyFind( entireText, '<', logging.critical ); noisyFind( entireText, '>', logging.critical )
    noisyFind( entireText, "'''", logging.critical )
    noisyFind( entireText, "''", logging.critical )
    noisyFind( entireText, 'fXXX', logging.critical )
    noisyFind( entireText, '\\ft[ ]?\\f*', logging.critical )
    noisyFind( entireText, ' \\f*', logging.error )
    noisyRegExFind( entireText, '\n[^\\\\]', logging.critical ) # Line that doesn't begin with backslash

    # Write the temp output (for debugging)
    if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
        # Write out entire file for checking
        if not os.path.exists( OUTPUT_FOLDERPATH):
            os.makedirs( OUTPUT_FOLDERPATH )
        filepath = OUTPUT_FOLDERPATH.joinpath( 'FBV.NT.usfm' )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Writing temp file {}…".format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as BibleTextFile:
            BibleTextFile.write( entireText )

    # Write out the USFM files
    USFMFolderpath = OUTPUT_FOLDERPATH.joinpath( 'USFM/' )
    if not os.path.exists( USFMFolderpath):
        os.makedirs( USFMFolderpath )
    splitAndWriteBooks( entireText, USFMFolderpath )
# end of FreeBibleConvert.main


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

    main()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of FreeBibleConvert.py
