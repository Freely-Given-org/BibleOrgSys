#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# build_static_tables.py
#
# Script taking BibleBooksCodes TSV data table
#       and formatting it into static declarations in a Rust include file.
#
# Copyright (C) 2025-2026 Robert Hunt
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
Script taking BibleBooksCodes TSV data table
       and formatting it into static declarations in a Rust include file.

CHANGELOG:
    2025-10-21 Allow insertChar in tidyBBB function
    2026-05-03 Sort the field names with optional values output (so don't cause extra diffs)
"""
from pathlib import Path
from csv import DictReader
import logging


VERSION_STR = 'v0.1.10'
TSV_SOURCE = Path( 'BibleBooksCodes_Tables.tsv' )
EXPECTED_TSV_HEADER = "originalLanguageCode\tbookName\tbookNameEnglishGuide\tBOSReferenceAbbreviation\tBOSReferenceNumber\tBOSSequenceNumber\texpectedChapters\tshortAbbreviation\tSBLAbbreviation\tOSISAbbreviation\tSwordAbbreviation\tCCELNumber\tUSFMAbbreviation\tUSFMNumber\tUSXNumber\tUnboundCode\tBibleditNumber\tLogosNumber\tLogosAbbreviation\tNETBibleAbbreviation\tDrupalBibleAbbreviation\tBibleWorksAbbreviation\tByzantineAbbreviation\tpossibleAlternativeAbbreviations\tpossibleAlternativeBooksCodes\tconsistsOfBooks\ttypicalSection\ttypicalSubsection\tallEnglishDerivedAbbreviations"
NUM_EXPECTED_TSV_COLUMNS = 29
RUST_SOURCE = Path( 'lib.src.rs' )
RUST_OUTPUT = Path( 'src/lib.rs' )
SUMMARY_TEXT_OUTPUT = Path( 'results_summary.txt' )


if __name__ == '__main__':
    summary_text = f"bos_books_codes build_static_tables.py {VERSION_STR}"
    print( summary_text )

    with open( TSV_SOURCE, 'rt', encoding='utf-8' ) as tsv_file:
        tsv_lines = tsv_file.readlines()
    text = f"Loaded {len(tsv_lines):,} tsv lines."
    print( text ); summary_text = f'{summary_text}\n{text}'

    # Remove any BOM
    if tsv_lines[0].startswith("\ufeff"):
        print("  Handling Byte Order Marker (BOM) at start of tsv file…")
        tsv_lines[0] = tsv_lines[0][1:]

    # Get the headers before we start
    tsv_header_line = tsv_lines[0].strip()
    assert tsv_header_line == EXPECTED_TSV_HEADER, f"{tsv_header_line=}"
    tsv_column_headers = [header for header in tsv_header_line.split('\t')]
    print( f"Column headers: ({len(tsv_column_headers)}): {tsv_column_headers}")
    assert len(tsv_column_headers) == NUM_EXPECTED_TSV_COLUMNS, len(tsv_column_headers)


    # Read, check the number of columns, and summarise row contents all in one go
    field_names_with_optional_values = set()
    fullArrayEntries, refAbbrevEntries, englishNameEntries = [], [], [] # Only for values that are compulsory on every line and unique
    usfmDictEntries, osisDictEntries = {}, {} # These ones are more complex because if there may be duplicate entries
    for n, row in enumerate( DictReader(tsv_lines, delimiter='\t') ):
        if len(row) != NUM_EXPECTED_TSV_COLUMNS:
            logging.critical(f"Line {n} has {len(row)} columns instead of {NUM_EXPECTED_TSV_COLUMNS}!!!")
        for field_name in row:
            if not row[field_name]:
                field_names_with_optional_values.add( field_name )

        if row['expectedChapters']:
            assert row['expectedChapters'].count( ',' ) <= 1 # i.e., maximum of two numbers
            expected_num_chapters = f"{'OptionalNumberOrTwoNumbers::TwoNumbers(['+row['expectedChapters']+'])' if ',' in row['expectedChapters'] else 'OptionalNumberOrTwoNumbers::Number('+row['expectedChapters']+')'}"
        else:
            expected_num_chapters = 'OptionalNumberOrTwoNumbers::None'

        # if row['possibleAlternativeAbbreviations']:
        #     alts = row['possibleAlternativeAbbreviations'].split( ',' )
        #     if len(alts) == 1:
        #         possible_alternative_abbreviations = f'''OptionalAbbreviationOrListOfAbbreviations::Abbreviation("{row['possibleAlternativeAbbreviations']}")'''
        #     elif len(alts) == 2:
        #         possible_alternative_abbreviations = f'''OptionalAbbreviationOrListOfAbbreviations::TwoAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 3:
        #         possible_alternative_abbreviations = f'''OptionalAbbreviationOrListOfAbbreviations::ThreeAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 4:
        #         possible_alternative_abbreviations = f'''OptionalAbbreviationOrListOfAbbreviations::FourAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 5:
        #         possible_alternative_abbreviations = f'''OptionalAbbreviationOrListOfAbbreviations::FiveAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 6:
        #         possible_alternative_abbreviations = f'''OptionalAbbreviationOrListOfAbbreviations::SixAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 7:
        #         possible_alternative_abbreviations = f'''OptionalAbbreviationOrListOfAbbreviations::SevenAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     else: raise ValueError(f"Too many possible_alternative_abbreviations: {n} {row['BOSReferenceAbbreviation']} ({len(alts)}) {row['possibleAlternativeAbbreviations']=}")
        # else:
        #     possible_alternative_abbreviations = 'OptionalAbbreviationOrListOfAbbreviations::None'

        # if row['possibleAlternativeBooksCodes']:
        #     alts = row['possibleAlternativeBooksCodes'].split( ',' )
        #     if len(alts) == 1:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::Abbreviation("{row['possibleAlternativeBooksCodes']}")'''
        #     elif len(alts) == 2:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::TwoAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 3:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::ThreeAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 4:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::FourAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 5:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::FiveAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 6:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::SixAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 12:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::TwelveAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 13:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::ThirteenAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 14:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::FourteenAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     elif len(alts) == 16:
        #         possible_alternative_books_codes = f'''OptionalAbbreviationOrListOfAbbreviations::SixteenAbbreviations([{','.join([f'"{abbrev}"' for abbrev in alts])}])'''
        #     else: raise ValueError(f"Too many possibleAlternativeBooksCodes: {n} {row['BOSReferenceAbbreviation']} ({len(alts)}) {row['possibleAlternativeBooksCodes']=}")
        # else:
        #     possible_alternative_books_codes = 'OptionalAbbreviationOrListOfAbbreviations::None'

        fullArrayEntries.append( f'''    BibleBooksCodesArrayEntry {{
        original_language_code: "{row['originalLanguageCode']}",
        original_language_book_name: "{row['bookName']}",
        book_name_English_guide: "{row['bookNameEnglishGuide']}",
        BOS_reference_abbreviation: "{row['BOSReferenceAbbreviation']}",
        BOS_reference_number: {row['BOSReferenceNumber']},
        BOS_sequence_number: {row['BOSSequenceNumber']},
        expected_num_chapters: {expected_num_chapters},
        short_abbreviation: {'Some("'+row['shortAbbreviation']+'")' if row['shortAbbreviation'] else 'None'},
        SBL_abbreviation: {'Some("'+row['SBLAbbreviation']+'")' if row['SBLAbbreviation'] else 'None'},
        OSIS_abbreviation: {'Some("'+row['OSISAbbreviation']+'")' if row['OSISAbbreviation'] else 'None'},
        Sword_abbreviation: {'Some("'+row['SwordAbbreviation']+'")' if row['SwordAbbreviation'] else 'None'},
        CCEL_number: {'Some('+row['CCELNumber']+')' if row['CCELNumber'] else 'None'},
        USFM_abbreviation: {'Some("'+row['USFMAbbreviation']+'")' if row['USFMAbbreviation'] else 'None'},
        USFM_number_str: {'Some("'+row['USFMNumber']+'")' if row['USFMNumber'] else 'None'},
        USX_number_str: {'Some("'+row['USXNumber']+'")' if row['USXNumber'] else 'None'},
        Unbound_Code: {'Some("'+row['UnboundCode']+'")' if row['UnboundCode'] else 'None'},
        Bibledit_number: {'Some('+row['BibleditNumber']+')' if row['BibleditNumber'] else 'None'},
        Logos_number: {'Some('+row['LogosNumber']+')' if row['LogosNumber'] else 'None'},
        Logos_abbreviation: {'Some("'+row['LogosAbbreviation']+'")' if row['LogosAbbreviation'] else 'None'},
        NET_Bible_abbreviation: {'Some("'+row['NETBibleAbbreviation']+'")' if row['NETBibleAbbreviation'] else 'None'},
        Drupal_Bible_abbreviation: {'Some("'+row['DrupalBibleAbbreviation']+'")' if row['DrupalBibleAbbreviation'] else 'None'},
        Bible_Works_abbreviation: {'Some("'+row['BibleWorksAbbreviation']+'")' if row['BibleWorksAbbreviation'] else 'None'},
        Byzantine_abbreviation: {'Some("'+row['ByzantineAbbreviation']+'")' if row['ByzantineAbbreviation'] else 'None'},
        possible_alternative_abbreviations: &[{','.join([f'"{abbrev}"' for abbrev in row['possibleAlternativeAbbreviations'].split(',')])}],
        possible_alternative_books_codes: &{f'''[{','.join([f'"{abbrev}"' for abbrev in row['possibleAlternativeBooksCodes'].split(',')])}]''' if row['possibleAlternativeBooksCodes'] else '[]'},
        consists_of_books_codes: {'Some("'+row['consistsOfBooks']+'")' if row['consistsOfBooks'] else 'None'},
        typical_section: {'Some("'+row['typicalSection']+'")' if row['typicalSection'] else 'None'},
        typical_subsection: {'Some("'+row['typicalSubsection']+'")' if row['typicalSubsection'] else 'None'},
        all_English_derived_abbreviations: "{row['allEnglishDerivedAbbreviations']}",
    }},''' )
        # //possible_alternative_abbreviations: {possible_alternative_abbreviations},
        # //possible_alternative_books_codes: {possible_alternative_books_codes},
        # possible_alternative_books_codes: {f'''Some(&[{','.join([f'"{abbrev}"' for abbrev in row['possibleAlternativeBooksCodes'].split(',')])}])''' if row['possibleAlternativeBooksCodes'] else 'None'},
        assert row['BOSReferenceAbbreviation'] not in refAbbrevEntries
        refAbbrevEntries.append( f'"{row['BOSReferenceAbbreviation']}"' )
        for englishName in row['allEnglishDerivedAbbreviations'].split( ',' ):
            englishNameEntries.append( f'"{englishName}"=>{n}' )
        if row['USFMAbbreviation']:
            # assert row['USFMNumber'], f"{row['USFMAbbreviation']=} {row['USFMNumber']=}" // Not true for 'PSo'
            if f'"{row['USFMAbbreviation']}"' not in usfmDictEntries: # already
                usfmDictEntries[f'"{row['USFMAbbreviation']}"'] = f'=>{n},' # We always take the first one for any given abbreviation
        if row['OSISAbbreviation']:
            if f'"{row['OSISAbbreviation']}"' not in osisDictEntries: # already
                osisDictEntries[f'"{row['OSISAbbreviation']}"'] = f'=>{n},' # We always take the first one for any given abbreviation

    # The following field names should have 'Option' below (because they don't exist for every code)
    sorted_field_names_with_optional_values = sorted( field_names_with_optional_values )
    text = f"{sorted_field_names_with_optional_values=}" # {'DrupalBibleAbbreviation', 'LogosNumber', 'USFMAbbreviation', 'typicalSubsection', 'OSISAbbreviation', 'allEnglishDerivedAbbreviations',
        # 'BibleditNumber', 'expectedChapters', 'possibleAlternativeBooksCodes', 'NETBibleAbbreviation', 'SwordAbbreviation', 'SBLAbbreviation', 'shortAbbreviation',
        # 'UnboundCode', 'possibleAlternativeAbbreviations', 'USXNumber', 'CCELNumber', 'ByzantineAbbreviation', 'USFMNumber', 'LogosAbbreviation', 'BibleWorksAbbreviation'}
    summary_text = f'{summary_text}\n{text}'

    static_rust_structs_str = f'''
#[derive(Debug)]
pub enum OptionalNumberOrTwoNumbers {{
    Number(u16),
    TwoNumbers([u16; 2]),
    None,
}}

//#[derive(Debug)]
//pub enum OptionalAbbreviationOrListOfAbbreviations<'a> {{
//    Abbreviation(&'a str),
//    TwoAbbreviations([&'a str; 2]),
//    ThreeAbbreviations([&'a str; 3]),
//    FourAbbreviations([&'a str; 4]),
//    FiveAbbreviations([&'a str; 5]),
//    SixAbbreviations([&'a str; 6]),
//    SevenAbbreviations([&'a str; 7]),
//    TwelveAbbreviations([&'a str; 12]),
//    ThirteenAbbreviations([&'a str; 13]),
//    FourteenAbbreviations([&'a str; 14]),
//    SixteenAbbreviations([&'a str; 16]),
//    None,
//}}

#[derive(Debug)]
pub struct BibleBooksCodesArrayEntry<'a> {{
    original_language_code: &'a str,
    original_language_book_name: &'a str,
    book_name_English_guide: &'a str,
    BOS_reference_abbreviation: &'a str,
    BOS_reference_number: u16,
    BOS_sequence_number: u16,
    expected_num_chapters: OptionalNumberOrTwoNumbers,
    short_abbreviation: Option<&'a str>,
    SBL_abbreviation: Option<&'a str>,
    OSIS_abbreviation: Option<&'a str>,
    Sword_abbreviation: Option<&'a str>,
    CCEL_number: Option<u16>,
    USFM_abbreviation: Option<&'a str>,
    USFM_number_str: Option<&'a str>,
    USX_number_str: Option<&'a str>,
    Unbound_Code: Option<&'a str>,
    Bibledit_number: Option<u16>,
    Logos_number: Option<u16>,
    Logos_abbreviation: Option<&'a str>,
    NET_Bible_abbreviation: Option<&'a str>,
    Drupal_Bible_abbreviation: Option<&'a str>,
    Bible_Works_abbreviation: Option<&'a str>,
    Byzantine_abbreviation: Option<&'a str>,
    //possible_alternative_abbreviations: OptionalAbbreviationOrListOfAbbreviations<'a>,
    possible_alternative_abbreviations: &'static [&'static str],
    //possible_alternative_books_codes: OptionalAbbreviationOrListOfAbbreviations<'a>,
    //possible_alternative_books_codes: Option<&'static [&'static str]>,
    possible_alternative_books_codes: &'static [&'static str],
    consists_of_books_codes: Option<&'a str>,
    typical_section: Option<&'a str>,
    typical_subsection: Option<&'a str>,
    all_English_derived_abbreviations: &'a str,
}}

pub static BIBLE_BOOKS_CODES_ARRAY: [BibleBooksCodesArrayEntry; {len(tsv_lines)-1}] = [
    {'\n'.join(fullArrayEntries)}
];

// NOTE: The following perfect_hash_function maps contain the array index of the entry in the above BIBLE_BOOKS_CODES_ARRAY
//static REFERENCE_ABBREVIATION_ARRAY: [&'static str; {len(refAbbrevEntries)}] = [{','.join(refAbbrevEntries)}]; // The array index matches the BIBLE_BOOKS_CODES_ARRAY index
static REFERENCE_ABBREVIATION_MAP: phf::Map<&'static str, usize> = phf_map! {{ {','.join([f'{v}=>{i}' for i,v in enumerate(refAbbrevEntries)])} }};
static USFM_ABBREVIATION_MAP: phf::Map<&'static str, usize> = phf_map! {{ {' '.join([f'{k}{v}' for k,v in usfmDictEntries.items()])} }};
static UPPERCASE_USFM_ABBREVIATION_MAP: phf::Map<&'static str, usize> = phf_map! {{ {' '.join([f'{k.upper()}{v}' for k,v in usfmDictEntries.items()])} }};
static OSIS_ABBREVIATION_MAP: phf::Map<&'static str, usize> = phf_map! {{ {' '.join([f'{k}{v}' for k,v in osisDictEntries.items()])} }};
static ENGLISH_NAME_MAP: phf::Map<&'static str, usize> = phf_map! {{ {', '.join(englishNameEntries)} }};
'''

    summary_text = f'{summary_text}\nWrote {len(fullArrayEntries):,} full array entries to BIBLE_BOOKS_CODES_ARRAY'
    summary_text = f'{summary_text}\nWrote {len(refAbbrevEntries):,} entries to REFERENCE_ABBREVIATION_ARRAY and/or REFERENCE_ABBREVIATION_MAP'
    summary_text = f'{summary_text}\nWrote {len(usfmDictEntries):,} entries to USFM_ABBREVIATION_MAP and UPPERCASE_USFM_ABBREVIATION_MAP'
    summary_text = f'{summary_text}\nWrote {len(osisDictEntries):,} entries to OSIS_ABBREVIATION_MAP'
    summary_text = f'{summary_text}\nWrote {len(englishNameEntries):,} entries to ENGLISH_NAME_MAP'

    with open( RUST_SOURCE, 'rt', encoding='utf-8' ) as source_file:
        rust_text = source_file.read()

    rust_text = ( rust_text
                 .replace( '//WARNINGS_GO_HERE', f'''// WARNING: DO NOT EDIT THIS FILE!!!
//   This file was created by build_static_tables.py {VERSION_STR} invoked by build.rs (both in the folder above this one)
//      which added in the static data structures.
//   To change the functions in this library,
//      edit lib.src.rs (also in the folder above this one)''' )
                 .replace( '//STATIC_STRUCTS_GO_HERE', f'''
// THESE VARIOUS STATIC ARRAYS AND HASHMAPS WERE CREATED AUTOMATICALLY BY build_static_tables.py
//   from the data in BibleBooksCodes_Tables.tsv (both files in the folder above this one)
{static_rust_structs_str}
''' )
                 )

    with open( RUST_OUTPUT, 'wt', encoding='utf-8' ) as rust_output_file:
        rust_output_file.write( rust_text )

    text = f"build_static_tables.py {VERSION_STR} SUCCESSFUL! $" # The $ currently indicates success to the Rust script (in build.rs)
    print( text ); summary_text = f'{summary_text}\n{text}'

    # Write a summary output results file in our own folder, so we have a build record that we can refer back to
    with open( SUMMARY_TEXT_OUTPUT, 'wt', encoding='utf-8' ) as text_output_file:
        text_output_file.write( f'{summary_text}\n' )
# end of build_static_tables.py
