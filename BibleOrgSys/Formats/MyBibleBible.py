#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# MyBibleBible.py
#
# Module handling "MyBible" Bible module files
#
# Copyright (C) 2016-2020 Robert Hunt
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
Module reading and loading MyBible Bible databases.
These can be downloaded from: http://mybible.zone/b-eng.php?q=mybible&k=bibles&qq=2&q=bbl
The format can be found from: http://mybible.zone/creat-eng.php
    and was here: https://docs.google.com/document/d/12rf4Pqy13qhnAW31uKkaWNTBDTtRbNW0s7cM0vcimlA/edit?pref=2&pli=1

The filename.SQLite3 is the module abbreviation.

A MyBible Bible module file has three tables
    TABLE info (name TEXT, value TEXT);
    TABLE "books" ("book_color" TEXT, "book_number" NUMERIC, "short_name" TEXT, "long_name" TEXT);
    TABLE "verses" ("book_number" NUMERIC, "chapter" NUMERIC, "verse" NUMERIC, "text" TEXT);
    UNIQUE INDEX verses_index on "verses" (book_number, chapter, verse);

Here is a typical info table:
    PRAGMA foreign_keys=OFF;
    BEGIN TRANSACTION;
    CREATE TABLE info (name TEXT, value TEXT);
    INSERT INTO "info" VALUES('description','International Standard Version');
    INSERT INTO "info" VALUES('chapter_string','Chapter');
    INSERT INTO "info" VALUES('language','en');
    INSERT INTO "info" VALUES('language_iso639-2b','eng');
    INSERT INTO "info" VALUES('russian_numbering','false');
    INSERT INTO "info" VALUES('strong_numbers','false');
    INSERT INTO "info" VALUES('right_to_left','false');
    COMMIT;

Should look for books_all table first.
Here is a typical books table:
    PRAGMA foreign_keys=OFF;
    BEGIN TRANSACTION;
    CREATE TABLE "books" ("book_color" TEXT, "book_number" NUMERIC, "short_name" TEXT, "long_name" TEXT);
    INSERT INTO "books" VALUES('#ccccff',10,'Gen','Genesis');
    INSERT INTO "books" VALUES('#ccccff',20,'Exo','Exodus');
    INSERT INTO "books" VALUES('#ccccff',30,'Lev','Leviticus');
    INSERT INTO "books" VALUES('#ccccff',40,'Num','Numbers');
    INSERT INTO "books" VALUES('#ccccff',50,'Deu','Deuteronomy');
    INSERT INTO "books" VALUES('#ffcc99',60,'Josh','Joshua');
    …
    INSERT INTO "books" VALUES('#00ff00',710,'3Jn','3 John');
    INSERT INTO "books" VALUES('#00ff00',720,'Jud','Jude');
    INSERT INTO "books" VALUES('#ff7c80',730,'Rev','Revelation');
    COMMIT;

Here is a typical verses table segment (one verse per SQLite3 table row):
    …
    INSERT INTO "verses" VALUES(730,22,17,'<n>{Concluding Invitation}</n> d The Spirit and the bride say, "Come!" Let everyone who hears this say, "Come!" Let everyone who is thirsty come! Let anyone who wants the water of life take it as a gift! ');
    INSERT INTO "verses" VALUES(730,22,18,'<n>{Concluding Warning}</n> d I warn everyone who hears the words of the prophecy in this book: If anyone adds anything to them, God will strike him with the plagues that are written in this book. ');
    INSERT INTO "verses" VALUES(730,22,19,'If anyone takes away any words from the book of this prophecy, God will take away his portion of the tree of life and the holy city that are described in this book. ');
    INSERT INTO "verses" VALUES(730,22,20,'<n>{Epilogue}</n> d The one who is testifying to these things says, "Yes, I am coming soon!" Amen! Come, Lord Jesus! ');
    INSERT INTO "verses" VALUES(730,22,21,'May the grace of the Lord Jesus be with all the saints. Amen. <n>{Other mss. lack Amen}</n> ');
    CREATE UNIQUE INDEX verses_index on "verses" (book_number, chapter, verse);
    COMMIT;

NOTE that MyBible can put different parts of the translation into different databases/files,
    e.g., a main (plain) text module, plus having footnotes, subheadings, and cross-references in separate modules.
    This code does not (yet?) handle combining multiple MyBible databases into one InternalBible,
        i.e., you can only have the text module OR the footnote module, but not both together.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-01-06' # by RJH
SHORT_PROGRAM_NAME = "MyBibleBible"
PROGRAM_NAME = "MyBible Bible format handler"
PROGRAM_VERSION = '0.21'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging
import os
import sqlite3
import re
import multiprocessing
from random import randrange
from pathlib import Path

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem



FILENAME_ENDINGS_TO_ACCEPT = ( '.SQLITE3', ) # Must be UPPERCASE
BIBLE_FILENAME_ENDINGS_TO_ACCEPT = ( '.SQLITE3', '.COMMENTARIES.SQLITE3', ) # Must be UPPERCASE
FILENAME_PARTS_TO_REJECT = ( '.DICTIONARY.', '.CROSSREFERENCES.', ) # Must be UPPERCASE


KNOWN_INFO_FIELD_NAMES = ( 'description',
                          'chapter_string', 'chapter_string_ot', 'chapter_string_nt', 'chapter_string_ps',
                            'language', 'language_iso639-2b', 'region', 'russian_numbering',
                            'strong_numbers', 'strong_numbers_prefix',
                            'right_to_left', 'right_to_left_ot', 'right_to_left_nt',
                            'localized_book_abbreviations', 'contains_accents',
                            'detailed_info', 'introduction_string', 'Introduction',
                            'is_footnotes', )


# NOTE that color values can vary between modules
BOOK_TABLE = {
    'GEN': ( '#ccccff', 10, 'Быт', 'Бытие', 'Gen', 'Genesis'),
    'EXO': ( '#ccccff', 20, 'Исх', 'Исход', 'Exo', 'Exodus'),
    'LEV': ( '#ccccff', 30, 'Лев', 'Левит', 'Lev', 'Leviticus'),
    'NUM': ( '#ccccff', 40, 'Чис', 'Числа', 'Num', 'Numbers'),
    'DEU': ( '#ccccff', 50, 'Втор', 'Второзаконие', 'Deu', 'Deuteronomy'),
    'JOS': ( '#ffcc99', 60, 'Нав', 'Иисус Навин', 'Josh', 'Joshua'),
    'JDG': ( '#ffcc99', 70, 'Суд', 'Судьи', 'Judg', 'Judges'),
    'RUT': ( '#ffcc99', 80, 'Руфь', 'Руфь', 'Ruth', 'Ruth'),
    'SA1': ( '#ffcc99', 90, '1Цар', '1-я Царств', '1Sam', '1 Samuel'),
    'SA2': ( '#ffcc99', 100, '2Цар', '2-я Царств', '2Sam', '2 Samuel'),
    'KI1': ( '#ffcc99', 110, '3Цар', '3-я Царств', '1Kin', '1 Kings'),
    'KI2': ( '#ffcc99', 120, '4Цар', '4-я Царств', '2Kin', '2 Kings'),
    'JDT': ( '#ffcc99', 180, 'Иудф', 'Иудифь', 'Jdth', 'Judith'),
    'CH1': ( '#ffcc99', 130, '1Пар', '1-я Паралипоменон', '1Chr', '1 Chronicles'),
    'CH2': ( '#ffcc99', 140, '2Пар', '2-я Паралипоменон', '2Chr', '2 Chronicles'),
    'EZR': ( '#ffcc99', 150, 'Ездр', 'Ездра', 'Ezr', 'Ezra'),
    'NEH': ( '#ffcc99', 160, 'Неем', 'Неемия', 'Neh', 'Nehemiah'),
    'LES': ( '#ffcc99', 165, '2Езд', '2-я Ездры', '2Esd', '2 Esdras'), # Was 740 -- NOT SURE ABOUT THIS ONE -- 2nd Ezra
    'TOB': ( '#ffcc99', 170, 'Тов', 'Товит', 'Tob', 'Tobit'),
    'EST': ( '#ffcc99', 190, 'Есф', 'Есфирь', 'Esth', 'Esther'),
    'JOB': ( '#66ff99', 220, 'Иов', 'Иов', 'Job', 'Job'),
    'PSA': ( '#66ff99', 230, 'Пс', 'Псалтирь', 'Ps', 'Psalms'),
    'PRO': ( '#66ff99', 240, 'Прит', 'Притчи', 'Prov', 'Proverbs'),
    'ECC': ( '#66ff99', 250, 'Еккл', 'Екклесиаст', 'Eccl', 'Ecclesiastes'),
    'SNG': ( '#66ff99', 260, 'Песн', 'Песня Песней', 'Song', 'Song of Solomon'),
    'WIS': ( '#66ff99', 270, 'Прем', 'Премудрость Соломона', 'Wis', 'Wisdom of Solomon'),
    'SIR': ( '#66ff99', 280, 'Сир', 'Сирах', 'Sir', 'Sirach'),
    'ISA': ( '#ff9fb4', 290, 'Ис', 'Исаия', 'Isa', 'Isaiah'),
    'JER': ( '#ff9fb4', 300, 'Иер', 'Иеремия', 'Jer', 'Jeremiah'),
    'PAZ': ( '#ff9fb4', 305, '???', '???', 'Azar', 'Azariah'),
    'LAM': ( '#ff9fb4', 310, 'Плач', 'Плач Иеремии', 'Lam', 'Lamentations'),
    'LJE': ( '#ff9fb4', 315, 'Посл', 'Послание Иеремии', 'Let', 'Letter of Jeremiah'),
    'BAR': ( '#ff9fb4', 320, 'Вар', 'Варух', 'Bar', 'Baruch'),
    'SUS': ( '#ff9fb4', 325, '???', '???', 'Sus', 'Susanna'),
    'EZE': ( '#ff9fb4', 330, 'Иез', 'Иезекииль', 'Ezek', 'Ezekiel'),
    'DAN': ( '#ff9fb4', 340, 'Дан', 'Даниил', 'Dan', 'Daniel'),
    'BEL': ( '#ff9fb4', 345, '???', '???', 'Bel', 'Bel and Dragon'),
    'HOS': ( '#ffff99', 350, 'Ос', 'Осия', 'Hos', 'Hosea'),
    'JOL': ( '#ffff99', 360, 'Иоил', 'Иоиль', 'Joel', 'Joel'),
    'AMO': ( '#ffff99', 370, 'Ам', 'Амос', 'Am', 'Amos'),
    'OBA': ( '#ffff99', 380, 'Авд', 'Авдий', 'Oba', 'Obadiah'),
    'JNA': ( '#ffff99', 390, 'Ион', 'Иона', 'Jona', 'Jonah'),
    'MIC': ( '#ffff99', 400, 'Мих', 'Михей', 'Mic', 'Micah'),
    'NAH': ( '#ffff99', 410, 'Наум', 'Наум', 'Nah', 'Nahum'),
    'HAB': ( '#ffff99', 420, 'Авв', 'Аввакум', 'Hab', 'Habakkuk'),
    'ZEP': ( '#ffff99', 430, 'Соф', 'Софония', 'Zeph', 'Zephaniah'),
    'HAG': ( '#ffff99', 440, 'Агг', 'Аггей', 'Hag', 'Haggai'),
    'ZEC': ( '#ffff99', 450, 'Зах', 'Захария', 'Zech', 'Zechariah'),
    'MAL': ( '#ffff99', 460, 'Мал', 'Малахия', 'Mal', 'Malachi'),
    'MA1': ( '#d3d3d3', 462, '1Мак', '1-я Маккавейская', '1Mac', '1 Maccabees'), # Was 200
    'MA2': ( '#d3d3d3', 464, '2Мак', '2-я Маккавейская', '2Mac', '2 Maccabees'), # Was 210
    'MA3': ( '#d3d3d3', 466, '3Мак', '3-я Маккавейская', '3Mac', '3 Maccabees'), # MAN appears at 466 in KJ-1769
    'EZ5': ( '#d3d3d3', 468, '3Езд', '3-я Ездры', '3Esd', '3 Esdras'), # Was 750 -- NOT SURE ABOUT THIS ONE -- 3rd Ezra
    'MAT': ( '#ff6600', 470, 'Мат', 'От Матфея', 'Mat', 'Matthew'),
    'MRK': ( '#ff6600', 480, 'Мар', 'От Марка', 'Mar', 'Mark'),
    'LUK': ( '#ff6600', 490, 'Лук', 'От Луки', 'Luk', 'Luke'),
    'JHN': ( '#ff6600', 500, 'Ин', 'От Иоанна', 'John', 'John'),
    'ACT': ( '#00ffff', 510, 'Деян', 'Деяния', 'Acts', 'Acts'),
    'JAM': ( '#00ff00', 660, 'Иак', 'Иакова', 'Jam', 'James'),
    'PE1': ( '#00ff00', 670, '1Пет', '1-е Петра', '1Pet', '1 Peter'),
    'PE2': ( '#00ff00', 680, '2Пет', '2-е Петра', '2Pet', '2 Peter'),
    'JN1': ( '#00ff00', 690, '1Ин', '1-е Иоанна', '1Jn', '1 John'),
    'JN2': ( '#00ff00', 700, '2Ин', '2-е Иоанна', '2Jn', '2 John'),
    'JN3': ( '#00ff00', 710, '3Ин', '3-е Иоанна', '3Jn', '3 John'),
    'JDE': ( '#00ff00', 720, 'Иуд', 'Иуды', 'Jud', 'Jude'),
    'ROM': ( '#ffff00', 520, 'Рим', 'К Римлянам', 'Rom', 'Romans'),
    'CO1': ( '#ffff00', 530, '1Кор', '1-е Коринфянам', '1Cor', '1 Corinthians'),
    'CO2': ( '#ffff00', 540, '2Кор', '2-е Коринфянам', '2Cor', '2 Corinthians'),
    'GAL': ( '#ffff00', 550, 'Гал', 'К Галатам', 'Gal', 'Galatians'),
    'EPH': ( '#ffff00', 560, 'Еф', 'К Ефесянам', 'Eph', 'Ephesians'),
    'PHP': ( '#ffff00', 570, 'Флп', 'К Филиппийцам', 'Phil', 'Philippians'),
    'COL': ( '#ffff00', 580, 'Кол', 'К Колоссянам', 'Col', 'Colossians'),
    'TH1': ( '#ffff00', 590, '1Фес', '1-е Фессалоникийцам', '1Ths', '1 Thessalonians'),
    'TH2': ( '#ffff00', 600, '2Фес', '2-е Фессалоникийцам', '2Ths', '2 Thessalonians'),
    'TI1': ( '#ffff00', 610, '1Тим', '1-е Тимофею', '1Tim', '1 Timothy'),
    'TI2': ( '#ffff00', 620, '2Тим', '2-е Тимофею', '2Tim', '2 Timothy'),
    'TIT': ( '#ffff00', 630, 'Тит', 'К Титу', 'Tit', 'Titus'),
    'PHM': ( '#ffff00', 640, 'Флм', 'К Филимону', 'Phlm', 'Philemon'),
    'HEB': ( '#ffff00', 650, 'Евр', 'К Евреям', 'Heb', 'Hebrews'),
    'REV': ( '#ff7c80', 730, 'Откр', 'Откровение', 'Rev', 'Revelation'),
    'LAO': ( '#00ff00', 780, 'Лаод', 'К Лаодикийцам', 'Lao', 'Letter to the Laodiceans'),
    'MAN': ( '#66ff99', 790, 'Мол', 'Молитва Манассии', 'Man', 'Prayer of Manasseh'), # Can also appear at 466
    }
# Create a pivot table by book number
BOOKNUMBER_TABLE = {}
# Check the table
for bBBB,bStuff in BOOK_TABLE.items():
    #print( bBBB, bStuff )
    assert len(bStuff) == 6
    for someField in bStuff: assert someField # shouldn't be blank
    if debuggingThisModule: assert BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber(bBBB)
    bkColor, bkNumber, rusAbbrev, rusName, engAbbrev, engName = bStuff
    assert bkNumber not in BOOKNUMBER_TABLE
    BOOKNUMBER_TABLE[bkNumber] = (bBBB,bkColor,rusAbbrev,rusName,engAbbrev,engName)
assert len(BOOKNUMBER_TABLE) == len(BOOK_TABLE)
# We only use the BOOKNUMBER_TABLE for CREATING modules -- not for reading



def MyBibleBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for MyBible Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one MyBible Bible is found,
        returns the loaded MyBibleBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "MyBibleBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag:
        assert givenFolderName and isinstance( givenFolderName, str )
        assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("MyBibleBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("MyBibleBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " MyBibleBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for stuff in FILENAME_PARTS_TO_REJECT:
                if stuff in somethingUpper: ignore=True; break
            if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
            if somethingUpperExt in FILENAME_ENDINGS_TO_ACCEPT:
                foundFiles.append( something )

    # See if there's an MyBibleBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "MyBibleBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            MyBB = MyBibleBible( givenFolderName, lastFilenameFound )
            if autoLoad or autoLoadBooks: MyBB.preload()
            if autoLoadBooks: MyBB.loadBooks() # Load and process the database
            return MyBB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("MyBibleBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    MyBibleBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for stuff in FILENAME_PARTS_TO_REJECT:
                    if stuff in somethingUpper: ignore=True; break
                if ignore: continue
                #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                if somethingUpperExt in FILENAME_ENDINGS_TO_ACCEPT:
                    foundSubfiles.append( something )

        # See if there's an MyBible project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "MyBibleBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            MyBB = MyBibleBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoad or autoLoadBooks: MyBB.preload()
            if autoLoadBooks: MyBB.loadBooks() # Load and process the database
            return MyBB
        return numFound
# end of MyBibleBibleFileCheck



class MyBibleBible( Bible ):
    """
    Class for reading, validating, and converting MyBibleBible files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'MyBible Bible object'
        self.objectTypeString = 'MyBible'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("MyBibleBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        filenameBits = os.path.splitext( self.sourceFilename )
        self.name = self.abbreviation = filenameBits[0]
        self.fileExtension = filenameBits[1]

        #if self.fileExtension.upper().endswith('X'):
            #logging.warning( _("MyBibleBible: File {!r} is encrypted").format( self.sourceFilepath ) )
    # end of MyBibleBible.__init__


    def preload( self ):
        """
        Load the metadata from the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("preload()") )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Preloading {}…").format( self.sourceFilepath ) )

        fileExtensionUpper = self.fileExtension.upper()
        if fileExtensionUpper not in FILENAME_ENDINGS_TO_ACCEPT:
            logging.critical( "{} doesn't appear to be a MyBible file".format( self.sourceFilename ) )
        elif not self.sourceFilename.upper().endswith( BIBLE_FILENAME_ENDINGS_TO_ACCEPT[0] ):
            logging.critical( "{} doesn't appear to be a MyBible Bible file".format( self.sourceFilename ) )

        connection = sqlite3.connect( self.sourceFilepath )
        connection.row_factory = sqlite3.Row # Enable row names
        self.cursor = connection.cursor()

        # First get the settings
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['MyBible'] = {}
        self.cursor.execute( 'select * from info' )
        rows = self.cursor.fetchall()
        for row in rows:
            assert len(row) == 2 # name, value
            name, value = row
            if debuggingThisModule: print( '  INFO', name, repr(value) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                assert name in KNOWN_INFO_FIELD_NAMES
            # NOTE: detailed_info may contain HTML formatting
            if value == 'false': value = False
            elif value == 'true': value = True
            self.suppliedMetadata['MyBible'][name] = value
        #print( self.suppliedMetadata['MyBible'] ); halt

        if self.getSetting('language') in ('ru','rus',) \
        or self.getSetting('Language') in ('ru','rus',) \
        or self.getSetting('LanguageName') in ('Russian',) \
        or self.getSetting('ISOLanguageCode') in ('rus',) \
        or self.getSetting('language_iso639-2b') in ('rus',):
            self.BibleOrganisationalSystem = BibleOrganisationalSystem( 'GENERIC-80-RUS' )
        else: self.BibleOrganisationalSystem = BibleOrganisationalSystem( 'GENERIC-ENG' ) # All possible books

        # Now get the book info -- try the books_all table first to see if it exists
        self.suppliedMetadata['MyBible']['BookInfo'] = {}

        loadedBookInfo = False
        try:
            self.cursor.execute( 'select * from books_all' )
            rows = self.cursor.fetchall()
            #print( "  BOOKS_ALL rows", len(rows) )
            isPresent = True
            for j, row in enumerate( rows ):
                assert len(row) == 5
                bookColor, bookNumber, shortName, longName, isPresent = row
                #print( bookColor, bookNumber, shortName, longName, isPresent )
                if BibleOrgSysGlobals.debugFlag: assert bookNumber in BOOKNUMBER_TABLE
                if len(rows) == 66: BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( j+1 )
                else:
                    BBB = self.BibleOrganisationalSystem.getBBBFromText( longName ) # Might not work for other languages
                    if BBB is None: BBB = self.BibleOrganisationalSystem.getBBBFromText( shortName ) # Might not work for other languages
                #print( "  Got1 BBB", BBB, repr(longName) )
                assert BBB
                self.suppliedMetadata['MyBible']['BookInfo'][BBB] = { 'bookNumber':bookNumber, 'longName':longName,
                                                'shortName':shortName, 'isPresent':isPresent, 'bookColor':bookColor }
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  Loaded book info ({}) from BOOKS_ALL table".format( len(rows) ) )
            loadedBookInfo = True
        except sqlite3.OperationalError: pass # Table is not in older module versions

        if not loadedBookInfo: # from newer books_all table
            try:
                self.cursor.execute( 'select * from books' )
                rows = self.cursor.fetchall()
                #print( "  BOOKS rows", len(rows) )
                isPresent = True
                for j, row in enumerate( rows ):
                    try: bookColor, bookNumber, shortName, longName = row
                    except ValueError: bookColor, bookNumber, shortName, longName, isPresent = row
                    #print( bookColor, bookNumber, shortName, longName, isPresent )
                    if BibleOrgSysGlobals.debugFlag: assert bookNumber in BOOKNUMBER_TABLE
                    longName = longName.strip() # Why do some have a \n at the end???
                    if len(rows) == 66: BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( j+1 )
                    else:
                        BBB = self.BibleOrganisationalSystem.getBBBFromText( longName ) # Might not work for other languages
                        if BBB is None: BBB = self.BibleOrganisationalSystem.getBBBFromText( shortName ) # Might not work for other languages
                        if BBB is None and shortName=='3Ма': BBB = 'MA3' # Cant't track down why this fails ???
                    #print( "  Got2 BBB", BBB, repr(longName), repr(shortName) )
                    assert BBB
                    self.suppliedMetadata['MyBible']['BookInfo'][BBB] = { 'bookNumber':bookNumber, 'longName':longName,
                                                    'shortName':shortName, 'isPresent':isPresent, 'bookColor':bookColor }
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "  Loaded book info ({}) from (old) BOOKS table".format( len(rows) ) )
                loadedBookInfo = True
            except sqlite3.OperationalError: pass # Table is not in older module versions

        if loadedBookInfo:
            self.availableBBBs.update( self.suppliedMetadata['MyBible']['BookInfo'].keys() )
        else: # no book info loaded
            if '.commentaries.' not in self.sourceFilename:
                logging.critical( "MyBibleBible.preload for {} had no books table".format( self.sourceFilename ) )
        #print( self.suppliedMetadata['MyBible'] ); halt
        self.preloadDone = True
    # end of MyBibleBible.preload


    def loadBooks( self ):
        """
        Load all the books out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("loadBooks()") )
        assert self.preloadDone

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )

        for BBB in self.suppliedMetadata['MyBible']['BookInfo']:
            #print( 'isPresent', self.suppliedMetadata['MyBible']['BookInfo'][BBB]['isPresent'] )
            if self.suppliedMetadata['MyBible']['BookInfo'][BBB]['isPresent']:
                self.loadBook( BBB )
            elif BibleOrgSysGlobals.verbosityLevel > 1:
                print( "   {} is not present in this Bible".format( BBB ) )

        self.cursor.close()
        del self.cursor
        self.applySuppliedMetadata( 'MyBible' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of MyBibleBible.loadBooks


    def loadBook( self, BBB ):
        """
        Load the requested book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("loadBook( {} )").format( BBB ) )
        assert self.preloadDone

        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading MyBibleBible {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("MyBibleBible: Loading {} from {}…").format( BBB, self.sourceFilepath ) )

        if '.commentaries.' in self.sourceFilename: self.__loadBibleCommentaryBook( BBB )
        else: self.__loadBibleBook( BBB )
    # end of MyBibleBible.loadBook


    def __loadBibleBook( self, BBB ):
        """
        Load the requested Bible book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "__loadBibleBook( {} )".format( BBB ) )

        lastC = None
        def importVerseLine( name, BBB, C, V, originalLine, bookObject ):
            """
            Change MyBible format codes to our codes
                and then add the line to the given bookObject
            """
            nonlocal lastC

            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( "importVerseLine( {!r}, {} {}:{}, {!r}, … )".format( name, BBB, C, V, originalLine ) )

            if originalLine is None: # We don't have an entry for this C:V
                return

            while originalLine and originalLine[-1] in '\r\n': # RHB
                originalLine = originalLine[:-1]
            assert '\n' not in originalLine and '\r' not in originalLine
            line = originalLine

            if line.endswith( '<BR>' ): line = line[:-4] # CSLU

            # Change MyBible format codes
            line = line.replace( '<n>{', '\\f ' ).replace( '}</n>', '\\f*' ) # ISV
            line = line.replace( '<n>', '\\f ' ).replace( '</n>', '\\f*' )
            line = line.replace( '<f>', '\\fn ' ).replace( '</f>', '\\fn*' ) # BTI
            line = line.replace( '<i>', '\\add ' ).replace( '</i>', '\\add*' )
            line = line.replace( '<b>', '\\bd ' ).replace( '</b>', '\\bd*' ) # RHB
            line = line.replace( '<e>', '\\em ' ).replace( '</e>', '\\em*' )
            line = line.replace( '<J>', '\\wj ' ).replace( '</J>', '\\wj*' ).replace( '<J/>', '\\wj*' ) # ¥­£¥
            line = line.replace( '<S>', '\\str ' ).replace( '</S>', '\\str*' )
            line = line.replace( '<t>', '\\qm ' ).replace( '</t>', '\\m ' )
            line = line.replace( '<br/>', '\\m ' )
            line = line.replace( '<pb/>', '\\p ' )
            line = line.replace( '<p>', '\\p ' ) # KJ-1769
            line = line.replace( '<br>', '\\m ' ) # RHB

            # Check for left-overs
            if '<' in line or '>' in line: # or '{' in line or '}' in line: RSTI has braces
                print( _("importVerseLine( {!r} failed at {} {}:{} {!r} from {!r} )").format( name, BBB, C, V, line, originalLine ) )
                if debuggingThisModule: halt

            # Ok, use the adjusted info
            if C!=lastC:
                bookObject.addLine( 'c', str(C) )
                lastC = C
            #print( BBB, C, V, repr(line) )
            bookObject.addLine( 'v', '{} {}'.format( V, line ) )
        # end of importVerseLine


        # Main code for loadBook()
        if BBB not in self.suppliedMetadata['MyBible']['BookInfo'] \
        or not self.suppliedMetadata['MyBible']['BookInfo'][BBB]['isPresent']:
            return

        # Create the empty book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'MyBible Bible Book object'
        thisBook.objectTypeString = 'MyBible'

        C = V = 1

        #ourGlobals = {}
        #continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        mbBookNumber = self.suppliedMetadata['MyBible']['BookInfo'][BBB]['bookNumber']
        #print( repr(mbBookNumber) )
        self.cursor.execute('select chapter,verse,text from verses where book_number=?', (mbBookNumber,) )
        for row in self.cursor.fetchall():
            C, V, line = row
            #try:
                #row = self.cursor.fetchone()
                #C, V, line = row
            #except TypeError: # This reference is missing (row is None)
                ##print( "something wrong at", BBB, C, V )
                ##if BibleOrgSysGlobals.debugFlag: halt
                ##print( row )
                #line = None
            #print ( mbBookNumber, BBB, C, V, "MyBib file line is", repr(line) )
            if line is None: logging.warning( "MyBibleBible.loadBibleBook: Have missing verse line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not line: logging.warning( "MyBibleBible.loadBibleBook: Found blank verse line at {} {}:{}".format( BBB, C, V ) )
                else:
                    haveLines = True

                    ## Some modules end lines with \r\n or have it in the middle!
                    ##   (We just ignore these for now)
                    #while line and line[-1] in '\r\n': line = line[:-1]
                    #if '\r' in line or '\n' in line: # (in the middle)
                        #logging.warning( "MyBibleBible.load: Found CR or LF characters in verse line at {} {}:{}".format( BBB, C, V ) )
                    #line = line.replace( '\r\n', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' )

            importVerseLine( self.name, BBB, C, V, line, thisBook ) # handle any formatting and save the line

        if haveLines:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  MyBible loadBibleBook saving", BBB )
            self.stashBook( thisBook )
        #else: print( "Not saving", BBB )

        #if ourGlobals['haveParagraph']:
            #thisBook.addLine( 'p', '' )
            #ourGlobals['haveParagraph'] = False
    # end of MyBibleBible.__loadBibleBook


    def __loadBibleCommentaryBook( self, BBB ):
        """
        Load the requested Bible book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("__loadBibleCommentaryBook( {} )").format( BBB ) )

        lastC = None
        def importCommentaryLine( name, BBB, C, V, footnoteNumber, originalLine, bookObject ):
            """
            Change MyBible format codes to our codes
                and then add the line to the given bookObject
            """
            nonlocal lastC

            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( _("importCommentaryLine( {!r}, {} {}:{}, {!r},{!r}, … )").format( name, BBB, C, V, footnoteNumber, originalLine ) )

            if originalLine is None: # We don't have an entry for this C:V
                return
            assert '\n' not in originalLine and '\r' not in originalLine
            line = originalLine

            # Change MyBible format codes
            line = line.replace( '<n>{', '\\f ' ).replace( '}</n>', '\\f*' ) # ISV
            line = line.replace( '<n>', '\\f ' ).replace( '</n>', '\\f*' )
            line = line.replace( '<i>', '\\add ' ).replace( '</i>', '\\add*' )
            line = line.replace( '<e>', '\\em ' ).replace( '</e>', '\\em*' )
            line = line.replace( '<J>', '\\wj ' ).replace( '</J>', '\\wj*' )
            line = line.replace( '<S>', '\\str ' ).replace( '</S>', '\\str*' )
            line = line.replace( '<t>', '\\qm ' ).replace( '</t>', '\\m ' )
            line = line.replace( '<br/>', '\\m ' ).replace( '<pb/>', '\\p ' )

            # Check for left-overs
            if '<' in line or '>' in line or '=' in line or '{' in line or '}' in line:
                if '<a ' not in line:
                    print( _("importCommentaryLine( {!r} failed at {} {}:{} {!r} from {!r} )").format( name, BBB, C, V, line, originalLine ) )
                    if debuggingThisModule:
                        halt

            # Ok, use the adjusted info
            if C!=lastC:
                bookObject.addLine( 'c', str(C) )
                lastC = C
            #print( BBB, C, V, repr(line) )
            bookObject.addLine( 'v', '{} {}'.format( V, line ) )
        # end of importCommentaryLine


        # Main code for loadBook()
        #if BBB not in self.suppliedMetadata['MyBible']['BookInfo'] \
        #or not self.suppliedMetadata['MyBible']['BookInfo'][BBB]['isPresent']:
            #return

        # Create the empty book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'MyBible Bible Book object'
        thisBook.objectTypeString = 'MyBible'

        C = V = 1

        #ourGlobals = {}
        #continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        footnoteMarker = None
        mbBookNumber = BOOK_TABLE[BBB][1]
        #print( repr(mbBookNumber) )
        if self.suppliedMetadata['MyBible']['is_footnotes']:
            self.cursor.execute('select chapter_number_from,verse_number_from,chapter_number_to,verse_number_to,marker,text from commentaries where book_number=?', (mbBookNumber,) )
        else:
            self.cursor.execute('select chapter_number_from,verse_number_from,chapter_number_to,verse_number_to,text from commentaries where book_number=?', (mbBookNumber,) )
        for row in self.cursor.fetchall():
            if self.suppliedMetadata['MyBible']['is_footnotes']:
                C, V, C2, V2, footnoteMarker, line = row
                #print( '{!r}:{!r}-{!r}:{!r} {!r}:{!r}'.format( C, V, C2, V2, footnoteMarker, line ) )
            else: # not footnotes
                C, V, C2, V2, line = row
                #print( '{!r}:{!r}-{!r}:{!r} {!r}'.format( C, V, C2, V2, line ) )
            if C2 is not None or V2 is not None:
                if C2 is None or C2==C:
                    assert V2 > V
                    V = '{}-{}'.format( V, V2 ) # Make a verse bridge
                else: halt # it's across a chapter boundary -- not finished
            #try:
                #row = self.cursor.fetchone()
                #C, V, line = row
            #except TypeError: # This reference is missing (row is None)
                ##print( "something wrong at", BBB, C, V )
                ##if BibleOrgSysGlobals.debugFlag: halt
                ##print( row )
                #line = None
            #print ( mbBookNumber, BBB, C, V, "MyBib file line is", repr(line) )
            if line is None: logging.warning( "MyBibleBible.loadBibleCommentaryBook: Have missing commentary line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not line: logging.warning( "MyBibleBible.loadBibleCommentaryBook: Found blank commentary line at {} {}:{}".format( BBB, C, V ) )
                else:
                    haveLines = True

                    ## Some modules end lines with \r\n or have it in the middle!
                    ##   (We just ignore these for now)
                    #while line and line[-1] in '\r\n': line = line[:-1]
                    #if '\r' in line or '\n' in line: # (in the middle)
                        #logging.warning( "MyBibleBible.load: Found CR or LF characters in verse line at {} {}:{}".format( BBB, C, V ) )
                    #line = line.replace( '\r\n', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' )

            importCommentaryLine( self.name, BBB, C, V, footnoteMarker, line, thisBook ) # handle any formatting and save the line

        if haveLines:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  MyBible loadBibleCommentaryBook saving", BBB )
            self.stashBook( thisBook )
        #else: print( "Not saving", BBB )

        #if ourGlobals['haveParagraph']:
            #thisBook.addLine( 'p', '' )
            #ourGlobals['haveParagraph'] = False
    # end of MyBibleBible.__loadBibleCommentaryBook
# end of MyBibleBible class



def createMyBibleModule( self, outputFolder, controlDict ) -> bool:
    """
    Create a SQLite3 database module for the Android program MyBible.

    self here is a Bible object with _processedLines
    """
    import zipfile
    from BibleOrgSys.Reference.USFM3Markers import OFTEN_IGNORED_USFM_HEADER_MARKERS, USFM_ALL_INTRODUCTION_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS, removeUSFMCharacterField, replaceUSFMCharacterFields
    from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS, BOS_NESTING_MARKERS
    from BibleOrgSys.Formats.theWordBible import theWordOTBookLines, theWordNTBookLines, theWordBookLines, theWordIgnoredIntroMarkers

    def adjustLine( BBB, C, V, originalLine ):
        """
        Handle pseudo-USFM markers within the line (cross-references, footnotes, and character formatting).

        Parameters are the Scripture reference (for error messsages)
            and the line (string) containing the backslash codes.

        Returns a string with the backslash codes replaced by MyBible RTF formatting codes.
        """
        line = originalLine # Keep a copy of the original line for error messages

        if '\\x' in line: # Remove cross-references completely (why???)
            #line = line.replace('\\x ','<RX>').replace('\\x*','<Rx>')
            line = removeUSFMCharacterField( 'x', line, closedFlag=True ).lstrip() # Remove superfluous spaces

        if '\\f' in line: # Handle footnotes
            #print( "originalLine", repr(originalLine) )
            while True: # fix internal footnote formatting
                match = re.search( r"\\f (.+?)\\f\*", line )
                if not match: break
                #print( "line1", repr(line) )
                #print( "1", match.group(1) )
                adjNote = match.group(1).replace('\\fqa*','\\ft ').replace('\\nd*','\\ft ').replace('\\add*','\\ft ')
                if '\\' in adjNote:
                    noteBits = adjNote.split( '\\' )
                    #print( "noteBits", noteBits )
                    newNote = ''
                    for noteBit in noteBits:
                        if noteBit in ( '+ ', '- ', '* ', '*  ', ): pass # Just ignore these -- '*  ' is for WEB
                        elif noteBit.startswith( '+ ' ): newNote += (' ' if newNote else '') + noteBit[2:]
                        elif noteBit.rstrip().isdigit(): pass # Just ignore footnote digits
                        elif noteBit.startswith( 'fr ' ): pass # Just ignore the origin markers (since we'll see the footnotes inline anyway)
                        elif noteBit.startswith( 'ft ' ): newNote += (' ' if newNote else '') + noteBit[3:]
                        elif noteBit.startswith( 'fq ' ): newNote += '<i>' + noteBit[3:] + '</i>'
                        elif noteBit.startswith( 'fqa ' ): newNote += '<i>' + noteBit[4:] + '</i>'
                        elif noteBit.startswith( 'nd ' ): newNote += noteBit[3:]
                        elif noteBit.startswith( 'add ' ): newNote += noteBit[4:]
                        elif noteBit.startswith( '+wj ' ): newNote += '<J>' + noteBit[4:]
                        elif noteBit.startswith( '+wj*' ): newNote += '</J>' + noteBit[4:]
                        else:
                            logging.error( "MyBible adjustLine: {} {!r} footnote field not handled properly yet.".format( self.abbreviation if self.abbreviation else self.name, noteBit[:3] ) )
                            newNote += '[[' + noteBit[3:] + ']]'
                            if BibleOrgSysGlobals.debuggingThisModule and debuggingThisModule: halt
                else: newNote = adjNote # No backslash fields inside note
                line = line[:match.start()] + '<n>' + newNote + '</n>' + line[match.end():]
                #print( "line2", repr(line) )

            #line = removeUSFMCharacterField( 'f', line, closedFlag=True ).lstrip() # Remove superfluous spaces
            ##for marker in ( 'fr', 'fm', ): # simply remove these whole field
                ##line = removeUSFMCharacterField( marker, line, closedFlag=None )
            ##for marker in ( 'fq', 'fqa', 'fl', 'fk', ): # italicise these ones
                ##while '\\'+marker+' ' in line:
                    ###print( BBB, C, V, marker, line.count('\\'+marker+' '), line )
                    ###print( "was", "'"+line+"'" )
                    ##ix = line.find( '\\'+marker+' ' )
                    ##assert ix != -1
                    ##ixEnd = line.find( '\\', ix+len(marker)+2 )
                    ##if ixEnd == -1: # no following marker so assume field stops at the end of the line
                        ##line = line.replace( '\\'+marker+' ', '<i>' ) + '</i>'
                    ##elif line[ixEnd:].startswith( '\\'+marker+'*' ): # replace the end marker also
                        ##line = line.replace( '\\'+marker+' ', '<i>' ).replace( '\\'+marker+'*', '</i>' )
                    ##else: # leave the next marker in place
                        ##line = line[:ixEnd].replace( '\\'+marker+' ', '<i>' ) + '</i>' + line[ixEnd:]
            ##for marker in ( 'ft', ): # simply remove these markers (but leave behind the text field)
                ##line = line.replace( '\\'+marker+' ', '' ).replace( '\\'+marker+'*', '' )
            ###for caller in '+*abcdefghijklmnopqrstuvwxyz': line.replace('\\f '+caller+' ','<RF>') # Handle single-character callers
            ##line = re.sub( r'(\\f [a-z+*]{1,4} )', '<RF>', line ) # Handle one to three character callers
            ##line = line.replace('\\f ','<RF>').replace('\\f*','<Rf>') # Must be after the italicisation
            ###if '\\f' in originalLine:
                ###print( "o", originalLine )
                ###print( "n", line )
                ###halt

        if '\\' in line: # Handle character formatting fields
            line = removeUSFMCharacterField( 'fig', line, closedFlag=True ) # Remove figures
            #line = removeUSFMCharacterField( 'str', line, closedFlag=True ) # Remove Strong's numbers
            line = removeUSFMCharacterField( 'sem', line, closedFlag=True ) # Remove semantic tagging
            replacements = (
                ( ('add',), '<i>','</i>' ),
                ( ('qt',), '','' ),
                ( ('wj',), '<J>','</J>' ),
                ( ('ca','va',), '(',')' ),
                ( ('bdit',), '<b><i>','</i></b>' ),
                ( ('bd','em','k',), '<b>','</b>' ),
                ( ('it','rq','bk','dc','qs','sig','sls','tl',), '<i>','</i>' ),
                ( ('nd','sc',), '','' ),
                #( ('f',), '<n>','</n>' ),
                ( ('str',), '<S>','</S>' ),
                )
            line = replaceUSFMCharacterFields( replacements, line ) # This function also handles USFM 2.4 nested character markers
            if '\\nd' not in originalLine and '\\+nd' not in originalLine:
                line = line.replace('LORD', '<font size=-1>LORD</font>')
                #line = line.replace('\\nd ','<font size=-1>',).replace('\\nd*','</font>').replace('\\+nd ','<font size=-1>',).replace('\\+nd*','</font>')
            #else:
                #line = line.replace('LORD', '<font size=-1>LORD</font>')
            #line = line.replace('\\add ','<FI>').replace('\\add*','<Fi>').replace('\\+add ','<FI>').replace('\\+add*','<Fi>')
            #line = line.replace('\\qt ','<FO>').replace('\\qt*','<Fo>').replace('\\+qt ','<FO>').replace('\\+qt*','<Fo>')
            #line = line.replace('\\wj ','<FR>').replace('\\wj*','<Fr>').replace('\\+wj ','<FR>').replace('\\+wj*','<Fr>')

        #if '\\' in line: # Output simple HTML tags (with no semantic info)
            #line = line.replace('\\bdit ','<b><i>').replace('\\bdit*','</i></b>').replace('\\+bdit ','<b><i>').replace('\\+bdit*','</i></b>')
            #for marker in ( 'it', 'rq', 'bk', 'dc', 'qs', 'sig', 'sls', 'tl', ): # All these markers are just italicised
                #line = line.replace('\\'+marker+' ','<i>').replace('\\'+marker+'*','</i>').replace('\\+'+marker+' ','<i>').replace('\\+'+marker+'*','</i>')
            #for marker in ( 'bd', 'em', 'k', ): # All these markers are just bolded
                #line = line.replace('\\'+marker+' ','<b>').replace('\\'+marker+'*','</b>').replace('\\+'+marker+' ','<b>').replace('\\+'+marker+'*','</b>')
            #line = line.replace('\\sc ','<font size=-1>',).replace('\\sc*','</font>').replace('\\+sc ','<font size=-1>',).replace('\\+sc*','</font>')

        # Check what's left at the end
        if '\\' in line:
            logging.warning( "toMyBible.adjustLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, line ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "toMyBible.adjustLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, line ) )
                halt
        return line
    # end of toMyBible.adjustLine


    #def handleIntroduction( BBB, bookData, ourGlobals ):
        #"""
        #Go through the book introduction (if any) and extract main titles for MyBible export.

        #Parameters are BBB (for error messages),
            #the actual book data, and
            #ourGlobals dictionary for persistent variables.

        #Returns the information in a composed line string.
        #"""
        #C = V = 0
        #composedLine = ''
        #while True:
            ##print( "toMyBible.handleIntroduction", BBB, C, V )
            #try: result = bookData.getContextVerseData( (BBB,'0',str(V),) ) # Currently this only gets one line
            #except KeyError: break # Reached the end of the introduction
            #verseData, context = result
            #assert len(verseData ) == 1 # in the introductory section
            #marker, text = verseData[0].getMarker(), verseData[0].getFullText()
            #if marker not in theWordIgnoredIntroMarkers and '¬' not in marker and marker not in BOS_ADDED_NESTING_MARKERS: # don't need added markers here either
                #if   marker in ('mt1','mte1',): composedLine += '<TS1>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
                #elif marker in ('mt2','mte2',): composedLine += '<TS2>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
                #elif marker in ('mt3','mte3',): composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
                #elif marker in ('mt4','mte4',): composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
                #elif marker=='ms1': composedLine += '<TS2>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
                #elif marker in ('ms2','ms3','ms4'): composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
                #elif marker=='mr': composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
                #else:
                    #logging.warning( "toMyBible.handleIntroduction: doesn't handle {} {!r} yet".format( BBB, marker ) )
                    #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        #print( "toMyBible.handleIntroduction: doesn't handle {} {!r} yet".format( BBB, marker ) )
                        #halt
                    #ourGlobals['unhandledMarkers'].add( marker + ' (in intro)' )
            #V += 1 # Step to the next introductory section "verse"

        ## Check what's left at the end
        #if '\\' in composedLine:
            #logging.warning( "toMyBible.handleIntroduction: Doesn't handle formatted line yet: {} {!r}".format( BBB, composedLine ) )
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( "toMyBible.handleIntroduction: Doesn't handle formatted line yet: {} {!r}".format( BBB, composedLine ) )
                #halt
        #return composedLine.replace( '~^~', '\\' )
    ## end of toMyBible.handleIntroduction


    def composeVerseLine( BBB, C, V, verseData, ourGlobals ):
        """
        Composes a single line representing a verse.

        Parameters are the Scripture reference (for error messages),
            the verseData (a list of InternalBibleEntries: pseudo-USFM markers and their contents),
            and a ourGlobals dictionary for holding persistent variables (between calls).

        This function handles the paragraph/new-line markers;
            adjustLine (above) is called to handle internal/character markers.

        Returns the composed line.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( "toMyBible.composeVerseLine( {} {}:{} {} {}".format( BBB, C, V, verseData, ourGlobals ) )

        composedLine = ourGlobals['line'] # We might already have some book headings to precede the text for this verse
        ourGlobals['line'] = '' # We've used them so we don't need them any more
        #marker = text = None

        vCount = 0
        lastMarker = gotVP = None
        #if BBB=='MAT' and C==4 and 14<V<18: print( BBB, C, V, ourGlobals, verseData )
        for verseDataEntry in verseData:
            marker, text = verseDataEntry.getMarker(), verseDataEntry.getFullText()
            if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS: continue # Just ignore added markers -- not needed here
            if marker in ('c','c#','cl','cp','rem',): lastMarker = marker; continue  # ignore all of these for this

            if marker == 'vp#': # This precedes a v field and has the verse number to be printed
                gotVP = text # Just remember it for now
            elif marker == 'v': # handle versification differences here
                vCount += 1
                if vCount == 1: # Handle verse bridges
                    if text != str(V):
                        composedLine += '<sup>('+adjustLine(BBB,C,V,text)+')</sup> ' # Put the additional verse number into the text in parenthesis
                elif vCount > 1: # We have an additional verse number
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert text != str(V)
                    composedLine += ' <sup>('+adjustLine(BBB,C,V,text)+')</sup>' # Put the additional verse number into the text in parenthesis
                lastMarker = marker
                continue

            #print( "toMyBible.composeVerseLine:", BBB, C, V, marker, text )
            if marker in theWordIgnoredIntroMarkers:
                logging.error( "toMyBible.composeVerseLine: Found unexpected {} introduction marker at {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                print( "toMyBible.composeVerseLine:", BBB, C, V, marker, text, verseData )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    assert marker not in theWordIgnoredIntroMarkers # these markers shouldn't occur in verses

            if marker == 'ms1':
                pass #composedLine += '<TS2>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
            elif marker in ('ms2','ms3','ms4'):
                pass #composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts><pb/>'
            elif marker == 's1':
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<pb/>' # append the new paragraph marker to the previous line
                composedLine += '<br/><t>'+adjustLine(BBB,C,V,text)+'</t><br/>'
            #elif marker == 's2': composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~cf0~^~b0~^~i0<pb/>'
            elif marker in ( 's2', 's3','s4', 'sr','mr', 'd', ): composedLine += '<t>'+adjustLine(BBB,C,V,text)+'</t>'
            elif marker in ( 'qa', 'r', ):
                if marker=='r' and text and text[0]!='(' and text[-1]!=')': # Put parenthesis around this if not already there
                    text = '(' + text + ')'
                composedLine += '<br/><t>'+adjustLine(BBB,C,V,text)+'</t><br/>'
            elif marker in ( 'm', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<pb/>' # append the new paragraph marker to the previous line
                #if text:
                    #print( 'm', repr(text), verseData )
                    #composedLine += '<pb/>'+adjustLine(BBB,C,V,text)
                    #if ourGlobals['pi1'] or ourGlobals['pi2'] or ourGlobals['pi3'] or ourGlobals['pi4'] or ourGlobals['pi5'] or ourGlobals['pi6'] or ourGlobals['pi7']:
                        #composedLine += '<pb/>'
                    #else: composedLine += '<pb/>'
                #else: # there is text
                    #composedLine += '~^~line'+adjustLine(BBB,C,V,text)
            elif marker in ( 'p', 'b', ):
                #print( marker, text )
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<pb/>' # append the new paragraph marker to the previous line
                #else: composedLine += '<pb/>'
                #composedLine += adjustLine(BBB,C,V,text)
            elif marker in ( 'pi1', ):
                assert not text
            elif marker in ( 'pi2', ):
                assert not text
            elif marker in ( 'pi3', 'pmc', ):
                assert not text
            elif marker in ( 'pi4', ):
                assert not text
            elif marker in ( 'pc', ):
                assert not text
            elif marker in ( 'pr', 'pmr', 'cls', ):
                assert not text
            elif marker in ( 'b','nb','ib', 'mi', 'pm', 'pmo', ):
                assert not text
            elif marker in ( 'q1', 'qm1', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '<pb/>' # append the new quotation paragraph marker to the previous line
                else: composedLine += '<pb/>'
                #composedLine += adjustLine(BBB,C,V,text)
            elif marker in ( 'q2', 'qm2', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '<pb/>' # append the new quotation paragraph marker to the previous line
                else: composedLine += '<pb/>'
                #composedLine += '~^~line<PI2>'+adjustLine(BBB,C,V,text)
            elif marker in ( 'q3', 'qm3', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '<pb/>' # append the new quotation paragraph marker to the previous line
                else: composedLine += '<pb/>'
                #composedLine += '~^~line<PI3>'+adjustLine(BBB,C,V,text)
            elif marker in ( 'q4', 'qm4', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '<pb/>' # append the new quotation paragraph marker to the previous line
                else: composedLine += '<pb/>'
                #composedLine += '~^~line<PI4>'+adjustLine(BBB,C,V,text)
            elif marker == 'li1': composedLine += '• '+adjustLine(BBB,C,V,text)
            elif marker == 'li2': composedLine += '• '+adjustLine(BBB,C,V,text)
            elif marker == 'li3': composedLine += '• '+adjustLine(BBB,C,V,text)
            elif marker == 'li4': composedLine += '• '+adjustLine(BBB,C,V,text)
            elif marker in ( 'cd', 'sp', ): composedLine += '<i>'+adjustLine(BBB,C,V,text)+'</i>'
            elif marker in ( 'v~', 'p~', ):
                #print( lastMarker )
                if lastMarker == 'p': composedLine += '<pb/>' # We had a continuation paragraph
                elif lastMarker == 'm': composedLine += '<br/>' # We had a continuation paragraph
                elif lastMarker in BibleOrgSysGlobals.USFMParagraphMarkers: pass # Did we need to do anything here???
                elif lastMarker != 'v':
                    #print( BBB, C, V, marker, lastMarker, verseData )
                    composedLine += adjustLine(BBB,C,V, text )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt # This should never happen -- probably a b marker with text
                composedLine += adjustLine(BBB,C,V, text )
            else:
                logging.warning( "toMyBible.composeVerseLine: doesn't handle {!r} yet".format( marker ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "toMyBible.composeVerseLine: doesn't handle {!r} yet".format( marker ) )
                    halt
                ourGlobals['unhandledMarkers'].add( marker )
            lastMarker = marker

        # Final clean-up
        #while '  ' in composedLine: # remove double spaces
            #composedLine = composedLine.replace( '  ', ' ' )

        # Check what's left at the end (but hide MyBible \line markers first)
        if '\\' in composedLine:
            logging.warning( "toMyBible.composeVerseLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, composedLine ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "toMyBible.composeVerseLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, composedLine ) )
                halt
        return composedLine.replace( '~^~', '\\' ).rstrip()
    # end of toMyBible.composeVerseLine


    def writeMyBibleBook( sqlObject, BBB:str, nBBB, bkData, ourGlobals ):
        """
        Writes a book to the MyBible sqlObject file.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "writeMyBibleBook( …, {}, {}, …, {} )".format( BBB, nBBB, ourGlobals ) )

        try: verseList = BOS.getNumVersesList( BBB )
        except KeyError: return False
        #nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
        numC, numV = len(verseList), verseList[0]

        ourGlobals['line'], ourGlobals['lastLine'] = '', None
        if bkData:
            ## Write book headings (stuff before chapter 1)
            #ourGlobals['line'] = handleIntroduction( BBB, bkData, ourGlobals )

            # Write the verses
            C = V = 1
            ourGlobals['lastLine'] = ourGlobals['lastBCV'] = None
            while True:
                verseData = None
                if bkData:
                    try:
                        result = bkData.getContextVerseData( (BBB,str(C),str(V),) )
                        verseData, context = result
                    except KeyError: # Just ignore missing verses
                        logging.warning( "BibleWriter.toMyBible: missing source verse at {} {}:{}".format( BBB, C, V ) )
                    # Handle some common versification anomalies
                    if (BBB,C,V) == ('JN3',1,14): # Add text for v15 if it exists
                        try:
                            result15 = bkData.getContextVerseData( ('JN3','1','15',) )
                            verseData15, context15 = result15
                            verseData.extend( verseData15 )
                        except KeyError: pass #  just ignore it
                    elif (BBB,C,V) == ('REV',12,17): # Add text for v15 if it exists
                        try:
                            result18 = bkData.getContextVerseData( ('REV','12','18',) )
                            verseData18, context18 = result18
                            verseData.extend( verseData18 )
                        except KeyError: pass #  just ignore it
                    composedLine = ''
                    if verseData:
                        composedLine = composeVerseLine( BBB, C, V, verseData, ourGlobals )
                        #if composedLine: # don't bother writing blank (unfinished?) verses
                            #print( "toMyBible: Writing", BBB, nBBB, C, V, marker, repr(line) )
                            #sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', (nBBB,C,V,composedLine) )
                        # Stay one line behind (because paragraph indicators get appended to the previous line)
                        if ourGlobals['lastBCV'] is not None \
                        and ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
                            try:
                                sqlObject.execute( 'INSERT INTO verses VALUES(?,?,?,?)', \
                                (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
                            except Exception as e:
                                logging.critical( f"MyBible: error using {ourGlobals}: {e}" )
                                raise e # again
                            #lineCount += 1
                    ourGlobals['lastLine'] = composedLine
                ourGlobals['lastBCV'] = (nBBB,C,V)
                V += 1
                if V > numV:
                    C += 1
                    if C > numC:
                        break
                    else: # next chapter only
                        numV = verseList[C-1]
                        V = 1
            #assert not ourGlobals['line'] and not ourGlobals['lastLine'] #  We should have written everything

        # Write the last line of the file
        if ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
            sqlObject.execute( 'INSERT INTO verses VALUES(?,?,?,?)', \
                (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
            #lineCount += 1
        return True
    # end of toMyBible.writeMyBibleBook


    # Set-up their Bible reference system
    BOS = BibleOrganisationalSystem( 'GENERIC-KJV-80-ENG' )
    extension = '.SQLite3'
    #BRL = BibleReferenceList( BOS, BibleObject=None )

    ## Try to figure out if it's an OT/NT or what (allow for up to 4 extra books like FRT,GLS, etc.)
    #if len(self) <= (39+4) and self.containsAnyOT39Books() and not self.containsAnyNT27Books():
        #testament, startBBB, endBBB = 'OT', 'GEN', 'MAL'
        #booksExpected, textLineCountExpected, checkTotals = 39, 23145, theWordOTBookLines
    #elif len(self) <= (27+4) and self.containsAnyNT27Books() and not self.containsAnyOT39Books():
        #testament, startBBB, endBBB = 'NT', 'MAT', 'REV'
        #booksExpected, textLineCountExpected, checkTotals = 27, 7957, theWordNTBookLines
    #else: # assume it's an entire Bible
        #testament, startBBB, endBBB = 'BOTH', 'GEN', 'REV'
        #booksExpected, textLineCountExpected, checkTotals = 66, 31102, theWordBookLines

    if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to MyBible format…") )
    if BibleOrgSysGlobals.alreadyMultiprocessing:
        logging.warning( "writeMyBibleBook() can fail with multiprocessing if output filenames happen to coincide" )
    mySettings = {}
    mySettings['unhandledMarkers'] = set()
    handledBooks = []

    # Try to find a somewhat-descriptive filename
    workAbbreviation = self.getSetting( 'workAbbreviation' )
    if 'MyBibleOutputFilename' in controlDict: filename = controlDict['MyBibleOutputFilename']
    elif workAbbreviation: filename = workAbbreviation
    elif self.abbreviation: filename = self.abbreviation
    elif self.shortName: filename = self.shortName
    elif self.sourceFilename: filename = self.sourceFilename
    elif self.name: filename = self.name
    elif self.sourceFilename: filename = self.sourceFilename
    else: filename = 'export'
    filename = filename.replace( ' ', '_' )
    if BibleOrgSysGlobals.alreadyMultiprocessing: # Need to ensure filenames are unique so we don't get a conflict
        filename += f'_{randrange(9_999)}'
        logging.warning( f"writeMyBibleBook() used random filename '{filename}' but could still fail with multiprocessing" )

    if not filename.endswith( extension ): filename += extension # Make sure that we have the right file extension
    filepath = os.path.join( outputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
    if os.path.exists( filepath ): os.remove( filepath )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( '  writeMyBibleBook: ' + _("Writing {!r}…").format( filepath ) )
    conn = sqlite3.connect( filepath )
    cursor = conn.cursor()


    # First write the settings info table
    cursor.execute( 'CREATE TABLE info (name TEXT, value TEXT)' )
    exeStr = 'INSERT INTO info VALUES(?,?)'

    description = self.getSetting( 'MyBibleDescription' )
    if not description: description = self.getSetting( 'Description' )
    if not description: description = self.getSetting( 'description' )
    if not description: description = self.name
    if not description: description = 'Unknown'
    cursor.execute( exeStr, ('description', description) )

    chapterString = self.getSetting( 'MyBibleChapterString' )
    if not chapterString: chapterString = 'Chapter'
    cursor.execute( exeStr, ('chapter_string', chapterString) )

    language = self.getSetting( 'MyBibleLanguage' )
    if not language: language = 'en'
    cursor.execute( exeStr, ('language', language) )

    ISOLanguageCode = self.getSetting( 'ISOLanguageCode' )
    if not ISOLanguageCode: ISOLanguageCode = 'eng'
    cursor.execute( exeStr, ('language_iso639-2b', ISOLanguageCode) )

    cursor.execute( exeStr, ('russian_numbering', 'false') )

    Strong = self.getSetting( 'Strong' )
    if not Strong: Strong = 'false'
    cursor.execute( exeStr, ('strong_numbers', Strong) )

    rightToLeft = self.getSetting( 'RightToLeft' )
    if not rightToLeft: rightToLeft = 'false'
    cursor.execute( exeStr, ('right_to_left', rightToLeft) )
    conn.commit() # save (commit) the changes


    BOOKS_TO_IGNORE = ( 'FRT', 'INT', 'BAK', 'GLS', 'OTH', 'XXA','XXB','XXC','XXD','XXE','XXF','XXG', 'NDX', 'UNK',
                       'PS2', 'ESG','GES', 'MA4', ) # This line are ones containing verse data but which we don't know how to encode

    # Now create and fill the Bible books table
    cursor.execute( 'CREATE TABLE books_all(book_color TEXT, book_number NUMERIC, short_name TEXT, long_name TEXT, is_present NUMERIC)' )
    exeStr = 'INSERT INTO books_all VALUES(?,?,?,?,?)'
    for bkData in self:
        BBB = bkData.BBB
        if BBB in BOOKS_TO_IGNORE: continue # No way to encode these books
        #print( "LOOP1", self.name, BBB )
        adjBBB = BBB
        #if BBB=='ESG': adjBBB = 'GES'
        bookColor, bookNumber, rusAbbrev, rusName, engAbbrev, engName = BOOK_TABLE[adjBBB]

        bookAbbrev = self.getSetting( BBB+'Abbreviation' )
        if not bookAbbrev: bookAbbrev = self.getSetting( BBB+'ShortName' )
        if not bookAbbrev: bookAbbrev = engAbbrev

        bookName = self.getSetting( BBB+'LongName' )
        if not bookName: bookName = self.getSetting( BBB+'ShortName' )
        if not bookName: bookName = engName

        cursor.execute( exeStr, (bookColor, bookNumber, bookAbbrev, bookName, 1) )
    conn.commit() # save (commit) the changes

    # Now create and fill the Bible verses table
    cursor.execute( 'CREATE TABLE verses (book_number NUMERIC, chapter NUMERIC, verse NUMERIC, text TEXT)' )
    #exeStr = 'INSERT INTO verses VALUES(?,?,?,?)'
    for bkData in self:
        BBB = bkData.BBB
        if BBB in BOOKS_TO_IGNORE: continue # No way to encode these books
        #print( "LOOP2", self.name, BBB )
        adjBBB = BBB
        #if BBB=='ESG': adjBBB = 'GES'
        bookColor, bookNumber, rusAbbrev, rusName, engAbbrev, engName = BOOK_TABLE[adjBBB]
        #cursor.execute( exeStr, (bookNumber, C, V, adjustedLine) )
        if writeMyBibleBook( cursor, BBB, bookNumber, bkData, mySettings ):
            try: conn.commit() # save (commit) the changes
            except Exception as e:
                logging.critical( f"MyBible: error writing {filepath}: {e}" )
                raise e # again
            handledBooks.append( BBB )

    # Now create the index to the verses
    cursor.execute( 'CREATE UNIQUE INDEX verses_index on "verses" (book_number, chapter, verse)' )
    conn.commit() # save (commit) the changes
    cursor.close() # All done

    if mySettings['unhandledMarkers']:
        logging.warning( "BibleWriter.toMyBible: Unhandled markers were {}".format( mySettings['unhandledMarkers'] ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled toMyBible markers were {}").format( mySettings['unhandledMarkers'] ) )
    unhandledBooks = []
    for BBB in self.getBookList():
        if BBB not in handledBooks: unhandledBooks.append( BBB )
    if unhandledBooks:
        logging.warning( "toMyBible: Unhandled books were {}".format( unhandledBooks ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled toMyBible books were {}").format( unhandledBooks ) )

    # Now create a zipped version
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} MyBible file…".format( filename ) )
    zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
    zf.write( filepath, filename )
    zf.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        print( "  BibleWriter.toMyBible finished successfully." )
    return True
# end of createMyBibleModule



def testMyBB( indexString:str, MyBBfolder, MyBBfilename:str ) -> None:
    """
    Crudely demonstrate the MyBible Bible class.

    Used by demo() for multiprocessing, etc. so must be at the outer level.
    """
    #print( "tMSB", MyBBfolder )
    from BibleOrgSys.Reference import VerseReferences
    #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/MyBible modules/' ) # Must be the same as below

    #TUBfolder = os.path.join( MyBBfolder, MyBBfilename )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the MyBible Bible class {}…").format( indexString) )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder/filename are {!r} {!r}".format( MyBBfolder, MyBBfilename ) )
    MyBB = MyBibleBible( MyBBfolder, MyBBfilename )
    MyBB.preload()
    #MyBB.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( MyBB ) # Just print a summary
    #print( MyBB.suppliedMetadata['MyBible'] )
    if MyBB is not None:
        if BibleOrgSysGlobals.strictCheckingFlag: MyBB.check()
        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                            ('OT','DAN','1','21'),
                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
            (t, b, c, v) = reference
            if t=='OT' and len(MyBB)==27: continue # Don't bother with OT references if it's only a NT
            if t=='NT' and len(MyBB)==39: continue # Don't bother with NT references if it's only a OT
            if t=='DC' and len(MyBB)<=66: continue # Don't bother with DC references if it's too small
            svk = VerseReferences.SimpleVerseKey( b, c, v )
            #print( svk, ob.getVerseDataList( reference ) )
            try:
                shortText = svk.getShortText()
                verseText = MyBB.getVerseText( svk )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( '    {}\t{!r}'.format( shortText, verseText ) )
            except KeyError:
                if BibleOrgSysGlobals.verbosityLevel > 1: print( '  testMyBB', reference, "not found!!!" )
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: raise

        #MyBB.loadBooks()
        if __name__ == '__main__':
            MyBB.doAllExports()

        if 0: # Now export the Bible and compare the round trip
            MyBB.toMyBible()
            #doaResults = MyBB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                outputFolder = "OutputFiles/BOS_MyBible_Reexport/"
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported MyBible files…" )
                result = BibleOrgSysGlobals.fileCompare( MyBBfilename, MyBBfilename, MyBBfolder, outputFolder )
                if BibleOrgSysGlobals.debugFlag:
                    if not result: halt
# end of testMyBB


def exportMyBB( eIndexString:str, eFolder ) -> None:
    """
    Used by demo() for multiprocessing, etc. so must be at the outer level.
    """
    from BibleOrgSys.UnknownBible import UnknownBible
    uB = UnknownBible( eFolder )
    result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "  {} result is: {}".format( eIndexString, result ) )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )
    if isinstance( result, Bible ) and result.books:
        result.toMyBible()
        #try: result.toMyBible()
        #except AttributeError:
            #errorClass, exceptionInstance, traceback = sys.exc_info()
            ##print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
            #if "object has no attribute 'toMyBible'" in str(exceptionInstance):
                #logging.info( "No 'toMyBible()' function to export Bible" ) # Ignore errors
            #else: # it's some other attribute error in the loadBook function
                #raise
# end of exportMyBB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )


    if 1: # A: demo the file checking code
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MyBibleTest/' )
        result1 = MyBibleBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = MyBibleBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA2", result2 )
        result3 = MyBibleBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA3", result3 )


    if 1: # B: individual modules in the test folder
        testFolder = BiblesFolderpath.joinpath( 'MyBible modules/' )
        names = ('CSLU',)
        for j, name in enumerate( names, start=1 ):
            fullname = name + '.SQLite3'
            pathname = os.path.join( testFolder, fullname )
            if os.path.exists( pathname ):
                indexString = f'B{j}'
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib {}/ Trying {}".format( indexString, fullname ) )
                testMyBB( indexString, testFolder, fullname )


    if 1: # C: individual modules in the output folder
        testFolder = "OutputFiles/BOS_MyBibleExport"
        names = ("Matigsalug",)
        for j, name in enumerate( names, start=1 ):
            fullname = name + '.SQLite3'
            pathname = os.path.join( testFolder, fullname )
            if os.path.exists( pathname ):
                indexString = f'C{j}'
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib {}/ Trying {}".format( indexString, fullname ) )
                testMyBB( indexString, testFolder, fullname )


    if 1: # D: all discovered modules in the test folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.SQLite3'):
                ignore = False
                somethingUpper = something.upper()
                for rejectStuff in FILENAME_PARTS_TO_REJECT:
                    if rejectStuff in somethingUpper: ignore=True; break
                if ignore: continue
                foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nD: Trying all {} discovered modules…".format( len(foundFiles) ) )
            parameters = [('D'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( testMyBB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ), start=1 ):
                indexString = f'D{j}'
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib {}/ Trying {}".format( indexString, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testMyBB( indexString, testFolder, someFile )
                #break # only do the first one…temp

    if 1: # E: all discovered modules in the test folder
        testFolder = BiblesFolderpath.joinpath( 'MyBible modules/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.SQLite3'):
                ignore = False
                somethingUpper = something.upper()
                for rejectStuff in FILENAME_PARTS_TO_REJECT:
                    if rejectStuff in somethingUpper: ignore=True; break
                if ignore: continue
                foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib E: Trying all {} discovered modules…".format( len(foundFiles) ) )
            parameters = [(f'E{j}',testFolder,filename) for j,filename in enumerate(sorted(foundFiles),start=1)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( testMyBB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ), start=1 ):
                indexString = f'E{j}'
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib {}/ Trying {}".format( indexString, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testMyBB( indexString, testFolder, someFile )
                #break # only do the first one…temp

    if 1: # F: test the export of various kinds of Bibles
        testFolders = ( os.path.join(
                    os.path.expanduser('~'), 'Logs/'), # Shouldn't have any Bibles here
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DBLTest/' ),
                    BiblesFolderpath.joinpath( 'theWord modules/' ),
                    BiblesFolderpath.joinpath( 'Biola Unbound modules/' ),
                    BiblesFolderpath.joinpath( 'EasyWorship Bibles/' ),
                    BiblesFolderpath.joinpath( 'OpenSong Bibles/' ),
                    BiblesFolderpath.joinpath( 'Zefania modules/' ),
                    BiblesFolderpath.joinpath( 'YET modules/' ),
                    BiblesFolderpath.joinpath( 'MyBible modules/' ),
                    BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/'),
                    Path( '/srv/AutoProcesses/Processed/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-OEB/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-WEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DBLTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFXTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFXTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFX-ASV/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFX-WEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ZefaniaTest/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'HaggaiTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ZefaniaTest/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VerseViewXML/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MyBibleTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordTest/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MySwordTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'YETTest/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PDBTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EasyWorshipBible/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DrupalTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest2/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest3/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH, # Up a level
                    )
        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
            # This fails with "daemonic processes are not allowed to have children"
            #   -- InternalBible (used by UnknownBible) already uses pools for discovery (and possibly for loading)
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\n\nMyBib F: Export all {} discovered Bibles…".format( len(foundFiles) ) )
            parameters = [(f'F{j}',testFolder) for j,testFolder in enumerate(testFolders,start=1)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( exportMyBB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, testFolder in enumerate( testFolders, start=1 ):
                indexString = f'F{j}'
                if BibleOrgSysGlobals.verbosityLevel > 0: print( "\ntoMyBible {}/ Export MyBible module for {}…".format( indexString, testFolder ) )
                exportMyBB( indexString, testFolder )
                #uB = UnknownBible( testFolder )
                #result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
                #if BibleOrgSysGlobals.verbosityLevel > 2: print( "  {} result is: {}".format( indexString, result ) )
                #if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )
                #try: result.toMyBible()
                #except AttributeError:
                    #errorClass, exceptionInstance, traceback = sys.exc_info()
                    ##print( '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
                    #if "object has no attribute 'toMyBible'" in str(exceptionInstance):
                        #logging.info( "No 'toMyBible()' function to export Bible" ) # Ignore errors
                    #else: # it's some other attribute error in the loadBook function
                        #raise
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of MyBibleBible.py
