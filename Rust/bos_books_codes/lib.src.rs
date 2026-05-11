//WARNINGS_GO_HERE

//! BibleOrgSys uses a three-character book code to identify books.
//! These reference abbreviations are nearly always represented as BBB in the program code,
//! and in a sense, this is the center of the BibleOrgSys.
//! The reference abbreviation (BBB) always starts with a letter, and letters are always UPPERCASE
//! (e.g., 2 Corinthians is 'CO2', not '2Co').
//! This was because early versions of HTML ID fields needed to start with a letter (not a digit),
//! and most identifiers in computer languages still require that.

#![allow(non_snake_case)]
// #![allow(unused)]

use std::error::Error;
use std::fmt;

use phf::phf_map;
use compact_str::{CompactString, format_compact};
// use std::collections::HashSet;

//STATIC_STRUCTS_GO_HERE


#[derive(Debug, PartialEq)]
pub enum LookupError<'a> {
    AbbrevNotFound(&'a str, &'a str),
    // ValueIsNone(String),
}

impl<'a> fmt::Display for LookupError<'a> {
    #[inline]
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LookupError::AbbrevNotFound(t,k) => write!(f, "{} abbreviation '{}' not found", t,k),
            // LookupError::ValueIsNone(k) => write!(f, "Key '{}' found but value is None", k),
        }
    }
}

impl Error for LookupError<'_> {}


#[inline]
pub fn is_valid_bos_book_code(bos_book_code: &str) -> bool {
    REFERENCE_ABBREVIATION_MAP.contains_key(bos_book_code)
}

#[inline]
fn get_array_index(bos_book_code: &str) -> Result<usize, LookupError<'_>> {
    REFERENCE_ABBREVIATION_MAP.get(bos_book_code)
        .copied()
        .ok_or_else(|| LookupError::AbbrevNotFound("Reference", bos_book_code))
}

/// Returns the referenceNumber 1..999 for the given book code (referenceAbbreviation).
pub fn get_reference_number(bos_book_code: &str) -> Result<u16, LookupError<'_>> {
    let array_index = get_array_index(bos_book_code)?;
    Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_reference_number)
}

/// Returns the sequence number for a given reference abbreviation.
pub fn get_sequence_number(bos_book_code: &str) -> Result<u16, LookupError<'_>> {
    let array_index = get_array_index(bos_book_code)?;
    Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_sequence_number)
}

/// Return the reference abbreviation for the given book number (reference number).
/// This is probably only useful in the range 1..66 (GEN..REV).
/// (After that, it specifies our arbitrary order.)
pub fn get_bos_book_code_from_reference_number(reference_number: u16) -> Option<&'static str> {
    BIBLE_BOOKS_CODES_ARRAY.iter()
        .find(|e| e.BOS_reference_number == reference_number)
        .map(|e| e.BOS_book_code)
}

#[inline]
pub fn get_all_bos_book_codes() -> &'static [&'static str] {
    ALL_REFERENCE_ABBREVIATIONS
}

#[inline]
pub fn get_all_osis_book_codes() -> &'static [&'static str] {
    ALL_OSIS_ABBREVIATIONS
}

pub fn get_all_usfm_abbreviations(to_upper: bool) -> Vec<CompactString> {
    if to_upper {
        ALL_USFM_ABBREVIATIONS.iter()
            .map(|&s| CompactString::from(s).to_uppercase())
            .collect()
    } else {
        ALL_USFM_ABBREVIATIONS.iter()
            .map(|&s| CompactString::from(s))
            .collect()
    }
}

#[inline]
pub fn get_all_usfm_books_code_number_triples() -> &'static [(&'static str, &'static str, &'static str)] {
    USFM_CODE_NUMBER_TRIPLES
}

#[inline]
pub fn get_all_usx_books_code_number_triples() -> &'static [(&'static str, &'static str, &'static str)] {
    USX_CODE_NUMBER_TRIPLES
}

#[inline]
pub fn get_all_bibledit_books_code_number_triples() -> &'static [(&'static str, &'static str, &'static str)] {
    BIBLEDIT_CODE_NUMBER_TRIPLES
}

/// Return a list of BBB codes in a sequence that could be used for the print order
/// if no further information is available.
/// If you supply a list of books, it puts your actual book codes into the default order.
pub fn get_sequence_list(my_list: Option<Vec<&str>>) -> Vec<&'static str> {
    match my_list {
        None => BOS_SEQUENCE_LIST.to_vec(),
        Some(list) => {
            let mut result = Vec::with_capacity(list.len());
            for &bbb1 in BOS_SEQUENCE_LIST {
                for bbb2 in &list {
                    if *bbb2 == bbb1 {
                        result.push(bbb1);
                        break;
                    }
                }
            }
            result
        }
    }
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn is_old_testament_nr(bos_book_code: &str) -> bool {
    if let Ok(num) = get_reference_number(bos_book_code) {
        return 1 <= num && num <= 39;
    }
    false
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn is_new_testament_nr(bos_book_code: &str) -> bool {
    if let Ok(num) = get_reference_number(bos_book_code) {
        return 40 <= num && num <= 66;
    }
    false
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn is_deuterocanon_nr(bos_book_code: &str) -> bool {
    matches!(bos_book_code, "TOB"|"JDT"|"ESG"|"WIS"|"SIR"|"BAR"|"LJE"|"PAZ"|"SUS"|"BEL"|"MA1"|"MA2"|"GES"|"LES"|"MAN")
}

pub fn get_ccel_number_str(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].CCEL_number_str)
}

pub fn get_short_abbreviation(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].short_abbreviation)
}

pub fn get_sbl_abbreviation(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].SBL_abbreviation)
}

pub fn bos_to_osis_book_code(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].OSIS_abbreviation)
}

pub fn bos_to_sword_book_code(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Sword_abbreviation)
}

pub fn bos_book_code_to_usfm_num_str(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].USFM_number_str)
}

pub fn get_usx_num_str(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].USX_number_str)
}

pub fn get_unbound_bible_code(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Unbound_Code)
}

pub fn get_bibledit_num_str(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Bibledit_number_str)
}

pub fn get_possible_alternative_books(bos_book_code: &str) -> Vec<&'static str> {
    get_array_index(bos_book_code).ok()
        .map(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].possible_alternative_books_codes.to_vec())
        .unwrap_or_default()
}

pub fn get_logos_num_str(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Logos_number_str)
}

pub fn bos_to_net_bible_book_code(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].NET_Bible_abbreviation)
}

pub fn bos_to_drupal_book_code(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Drupal_Bible_abbreviation)
}

pub fn get_byzantine_abbreviation(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Byzantine_abbreviation)
}

/// Gets a list with the number of expected chapters for the given book code (reference abbreviation).
/// Why is it a list? Because some books have alternate possible numbers of chapters
/// depending on the Biblical tradition.
pub fn get_expected_chapters_list(bos_book_code: &str) -> Vec<u16> {
    if let Ok(idx) = get_array_index(bos_book_code) {
        match BIBLE_BOOKS_CODES_ARRAY[idx].expected_num_chapters {
            OptionalNumberOrTwoNumbers::Number(n) => vec![n],
            OptionalNumberOrTwoNumbers::TwoNumbers(nums) => vec![nums[0], nums[1]],
            OptionalNumberOrTwoNumbers::None => vec![],
        }
    } else {
        vec![]
    }
}

pub fn get_max_chapters(bos_book_code: &str) -> i16 {
    let list = get_expected_chapters_list(bos_book_code);
    if list.is_empty() {
        -1
    } else {
        *list.iter().max().unwrap() as i16
    }
}

pub fn get_single_chapter_books_list() -> Vec<&'static str> {
    BIBLE_BOOKS_CODES_ARRAY.iter()
        .filter(|e| matches!(e.expected_num_chapters, OptionalNumberOrTwoNumbers::Number(1)))
        .map(|e| e.BOS_book_code)
        .collect()
}

pub fn get_osis_single_chapter_books_list() -> Vec<&'static str> {
    BIBLE_BOOKS_CODES_ARRAY.iter()
        .filter(|e| matches!(e.expected_num_chapters, OptionalNumberOrTwoNumbers::Number(1)))
        .filter_map(|e| e.OSIS_abbreviation)
        .collect()
}

pub fn is_single_chapter_book(bos_book_code: &str) -> bool {
    if let Ok(idx) = get_array_index(bos_book_code) {
        return matches!(BIBLE_BOOKS_CODES_ARRAY[idx].expected_num_chapters, OptionalNumberOrTwoNumbers::Number(1));
    }
    false
}

pub fn is_chapter_verse_book(bos_book_code: &str) -> bool {
    if let Ok(idx) = get_array_index(bos_book_code) {
        return !matches!(BIBLE_BOOKS_CODES_ARRAY[idx].expected_num_chapters, OptionalNumberOrTwoNumbers::None);
    }
    false
}

pub fn get_typical_section(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].typical_section)
}

/// Returns true for 116 Psalms that traditionally have a header field in the Hebrew (USFM /d field).
/// Otherwise returns false (for the other 34, plus for other books).
pub fn has_psalm_title(bbb: &str, c: &str) -> bool {
    if bbb != "PSA" || c.is_empty() || !c.as_bytes().iter().all(|&ch| ch.is_ascii_digit()) { return false; }
    !matches!(c, "0"| "1"|"2"| "10"| "33"| "43"| "71"| "91"| "93"|"94"|"95"|"96"|"97"|"99"|
                 "104"|"105"|"106"|"107"| "111"|"112"|"113"|"114"|"115"|"116"|"117"|"118"|"119"| "135"|"136"|"137"| "146"|"147"|"148"|"149"|"150")
}

/// Convert a BCV or BCVS reference to an integer especially so that references can be sorted.
/// If a verse is a verse span with a hyphen (e.g., '3-4'), it uses the value before the hyphen.
pub fn bcv_reference_to_int(bbb: &str, c: &str, v: &str, s: Option<&str>) -> i32 {
    let ref_num = get_reference_number(bbb).unwrap_or(999) as i32;
    let int_c = c.parse::<i32>().unwrap_or(0);
    let int_v = v.split('-').next().unwrap_or("0").parse::<i32>().unwrap_or(0);
    let int_s = match s {
        Some(val) if val.eq_ignore_ascii_case("a") => 0,
        Some(val) if val.eq_ignore_ascii_case("b") => 1,
        _ => 0,
    };

    ((ref_num * 100 + int_c) * 150 + int_v) * 10 + int_s
}

pub fn sort_bcv_references<T>(references: &mut [T], get_parts: impl Fn(&T) -> (&str, &str, &str, Option<&str>)) {
    references.sort_by_key(|r| {
        let (bbb, c, v, s) = get_parts(r);
        bcv_reference_to_int(bbb, c, v, s)
    });
}


/// Returns true if the storyline of the book continues through chapters,
/// i.e., the chapter divisions are artificial.
/// Returns false for books like Psalms where chapters are actual units.
pub fn continues_through_chapters(bos_book_code: &str) -> bool {
    !matches!(bos_book_code, "PSA" | "PS2" | "LAM")
}

pub fn get_book_name(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .map(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].original_language_book_name)
}

pub fn get_full_entry(bos_book_code: &str) -> Result<&'static BibleBooksCodesArrayEntry<'static>, LookupError<'_>> {
    let array_index = get_array_index(bos_book_code)?;
    Ok(&BIBLE_BOOKS_CODES_ARRAY[array_index])
}

/// Returns the first English name for a book.
/// Remember: These names are only intended as comments or for some basic module processing.
/// They are not intended to be used for a proper international human interface.
/// The first one in the list is supposed to be the more common.
// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn get_english_name_nr(bos_book_code: &str) -> Option<&'static str> {
    get_array_index(bos_book_code).ok()
        .map(|idx| {
            let guide = BIBLE_BOOKS_CODES_ARRAY[idx].book_name_English_guide;
            guide.split('/').next().unwrap_or(guide).trim()
        })
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn get_english_name_list_nr(bos_book_code: &str) -> Vec<&'static str> {
    if let Ok(idx) = get_array_index(bos_book_code) {
        BIBLE_BOOKS_CODES_ARRAY[idx].book_name_English_guide
            .split('/')
            .map(|s| s.trim())
            .collect()
    } else {
        vec![]
    }
}

/// Change book codes like SA1 to the conventional 1SA
/// (or 1Sa using the titleCase flag or 1 SAM using the allowFourChars and with a space for insertChar).
/// BBB is always three characters starting with an UPPERCASE LETTER.
/// insertChar prevents 1SA (becomes 1-SA or whatever) from being mistaken for ISA.
pub fn tidy_bbb(bbb: &str, title_case: bool, allow_four_chars: bool, insert_char: &str) -> CompactString {
    if title_case {
        if allow_four_chars {
            match bbb {
                "RUT" => return CompactString::new("Ruth"),
                "SA1" => return format_compact!("1{}Sam", insert_char),
                "SA2" => return format_compact!("2{}Sam", insert_char),
                "CH1" => return format_compact!("1{}Chr", insert_char),
                "CH2" => return format_compact!("2{}Chr", insert_char),
                "EZR" => return CompactString::new("Ezra"),
                "PRO" => return CompactString::new("Prov"),
                "JOL" => return CompactString::new("Joel"),
                "AMO" => return CompactString::new("Amos"),
                "MA1" => return format_compact!("1{}Mac", insert_char),
                "MA2" => return format_compact!("2{}Mac", insert_char),
                "MA3" => return format_compact!("3{}Mac", insert_char),
                "MA4" => return format_compact!("4{}Mac", insert_char),
                "MRK" => return CompactString::new("Mark"),
                "LUK" => return CompactString::new("Luke"),
                "JHN" => return CompactString::new("John"),
                "ACT" => return CompactString::new("Acts"),
                "CO1" => return format_compact!("1{}Cor", insert_char),
                "CO2" => return format_compact!("2{}Cor", insert_char),
                "TI1" => return format_compact!("1{}Tim", insert_char),
                "TI2" => return format_compact!("2{}Tim", insert_char),
                "PE1" => return format_compact!("1{}Pet", insert_char),
                "PE2" => return format_compact!("2{}Pet", insert_char),
                "JN1" => return format_compact!("1{}Jhn", insert_char),
                "JN2" => return format_compact!("2{}Jhn", insert_char),
                "JN3" => return format_compact!("3{}Jhn", insert_char),
                "JDE" => return CompactString::new("Jude"),
                _ => {}
            }
        }
        let bbb_chars: Vec<char> = bbb.chars().collect();
        if bbb_chars.len() >= 3 && bbb_chars[2].is_ascii_digit() {
            return format_compact!("{}{}{}{}", bbb_chars[2], insert_char, bbb_chars[0], bbb_chars[1].to_lowercase());
        } else {
            return format_compact!("{}{}", bbb_chars[0], bbb[1..].to_lowercase());
        }
    }

    if allow_four_chars {
        match bbb {
            "RUT" => return CompactString::new("RUTH"),
            "SA1" => return format_compact!("1{}SAM", insert_char),
            "SA2" => return format_compact!("2{}SAM", insert_char),
            "CH1" => return format_compact!("1{}CHR", insert_char),
            "CH2" => return format_compact!("2{}CHR", insert_char),
            "EZR" => return CompactString::new("EZRA"),
            "PRO" => return CompactString::new("PROV"),
            "JOL" => return CompactString::new("JOEL"),
            "AMO" => return CompactString::new("AMOS"),
            "MA1" => return format_compact!("1{}MAC", insert_char),
            "MA2" => return format_compact!("2{}MAC", insert_char),
            "MA3" => return format_compact!("3{}MAC", insert_char),
            "MA4" => return format_compact!("4{}MAC", insert_char),
            "MRK" => return CompactString::new("MARK"),
            "LUK" => return CompactString::new("LUKE"),
            "JHN" => return CompactString::new("JOHN"),
            "ACT" => return CompactString::new("ACTS"),
            "CO1" => return format_compact!("1{}COR", insert_char),
            "CO2" => return format_compact!("2{}COR", insert_char),
            "TI1" => return format_compact!("1{}TIM", insert_char),
            "TI2" => return format_compact!("2{}TIM", insert_char),
            "PE1" => return format_compact!("1{}PET", insert_char),
            "PE2" => return format_compact!("2{}PET", insert_char),
            "JN1" => return format_compact!("1{}JHN", insert_char),
            "JN2" => return format_compact!("2{}JHN", insert_char),
            "JN3" => return format_compact!("3{}JHN", insert_char),
            "JDE" => return CompactString::new("JUDE"),
            _ => {}
        }
    }

    let bbb_chars: Vec<char> = bbb.chars().collect();
    if bbb_chars.len() >= 3 && bbb_chars[2].is_ascii_digit() {
        return format_compact!("{}{}{}", bbb_chars[2], insert_char, &bbb[0..2]);
    }

    CompactString::new(bbb)
}

#[inline]
pub fn bos_book_code_to_usfm_abbrev<'a>(
    bos_book_code: &str,
) -> Result<Option<&'static str>, LookupError<'_>> {
    let array_index = *REFERENCE_ABBREVIATION_MAP.get(bos_book_code)
        .ok_or_else(|| LookupError::AbbrevNotFound("Reference", bos_book_code))?;

    Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].USFM_abbreviation)
        // .as_ref()
        // .ok_or_else(|| Box::new(LookupError::ValueIsNone(bos_book_code.to_string())) as Box<dyn Error>)?)
}

#[inline]
pub fn usfm_abbrev_to_bos_book_code<'a>(
    usfm_abbreviation: &'a str,
) -> Result<&'static str, LookupError<'a>> {
    if let Some(&array_index) = USFM_ABBREVIATION_MAP.get(usfm_abbreviation) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    } else if let Some(&array_index) = UPPERCASE_USFM_ABBREVIATION_MAP.get(usfm_abbreviation.to_uppercase().as_str()) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    } else {
        Err(LookupError::AbbrevNotFound("USFM", usfm_abbreviation))
    }
}

#[inline]
pub fn osis_book_code_to_bos_book_code<'a>(
    osis_book_code: &'a str,
    strict: bool,
) -> Result<&'static str, LookupError<'a>> {
    if let Some(&array_index) = OSIS_ABBREVIATION_MAP.get(osis_book_code) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    } else if !strict {
        let uc = CompactString::from(osis_book_code).to_uppercase();
        if let Some(&array_index) = SWORD_ABBREVIATION_MAP.get(uc.as_str()) {
             Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
        } else {
            Err(LookupError::AbbrevNotFound("OSIS/Sword", osis_book_code))
        }
    } else {
        Err(LookupError::AbbrevNotFound("OSIS", osis_book_code))
    }
}

#[inline]
pub fn drupal_book_code_to_bos_book_code<'a>(
    drupal_book_code: &'a str,
) -> Result<&'static str, LookupError<'a>> {
    if let Some(&array_index) = DRUPAL_BIBLE_ABBREVIATION_MAP.get(drupal_book_code) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    } else {
        Err(LookupError::AbbrevNotFound("Drupal", drupal_book_code))
    }
}

#[inline]
pub fn unbound_code_to_bos_book_code<'a>(
    unbound_code: &'a str,
) -> Result<&'static str, LookupError<'a>> {
    if let Some(&array_index) = UNBOUND_CODE_MAP.get(unbound_code) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    } else {
        Err(LookupError::AbbrevNotFound("Unbound", unbound_code))
    }
}

/// Return the reference abbreviation string for the given short book code string.
/// NOTE: This tends to be more forgiving than more specific Bible code systems.
#[inline]
pub fn short_abbrev_to_bos_book_code<'a>(
    short_abbreviation: &'a str,
    strict: bool,
) -> Result<&'static str, LookupError<'a>> {
    let uc = CompactString::from(short_abbreviation).to_uppercase();
    if let Some(&array_index) = SHORT_ABBREVIATION_MAP.get(uc.as_str()) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    } else if !strict {
        // Maybe it has a space in it?
        let no_space = uc.replace(' ', "");
        if let Some(&array_index) = SHORT_ABBREVIATION_MAP.get(no_space.as_str()) {
            Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
        } else if let Some(&array_index) = SBL_ABBREVIATION_MAP.get(uc.as_str()) {
            Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
        } else if let Some(&array_index) = NET_BIBLE_ABBREVIATION_MAP.get(uc.as_str()) {
            Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
        } else {
             Err(LookupError::AbbrevNotFound("Short/SBL/NET", short_abbreviation))
        }
    } else {
        Err(LookupError::AbbrevNotFound("Short", short_abbreviation))
    }
}

#[inline]
pub fn sbl_abbrev_to_bos_book_code<'a>(
    sbl_abbreviation: &'a str,
) -> Result<&'static str, LookupError<'a>> {
    let uc = CompactString::from(sbl_abbreviation).to_uppercase();
    if let Some(&array_index) = SBL_ABBREVIATION_MAP.get(uc.as_str()) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    } else {
        Err(LookupError::AbbrevNotFound("SBL", sbl_abbreviation))
    }
}

#[inline]
pub fn net_bible_abbrev_to_bos_book_code<'a>(
    net_bible_abbreviation: &'a str,
) -> Result<&'static str, LookupError<'a>> {
    let uc = CompactString::from(net_bible_abbreviation).to_uppercase();
    if let Some(&array_index) = NET_BIBLE_ABBREVIATION_MAP.get(uc.as_str()) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    } else {
        Err(LookupError::AbbrevNotFound("NET", net_bible_abbreviation))
    }
}

pub fn english_name_to_bos_book_code(english_name: &str,) -> Option<&'static str> {
    let adj_english_name = CompactString::from(english_name).to_uppercase();
    if let Some(&array_index) = ENGLISH_NAME_MAP.get(adj_english_name.as_str()) {
        return Some(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
    }

    let pairs = [
        ("1.", "1"), ("I ", "1"), ("I.", "1"),
        ("2.", "2"), ("II ", "2"), ("II.", "2"),
        ("3.", "3"), ("III ", "3"), ("III.", "3"),
        ("4.", "4"), ("IV ", "4"), ("IV.", "4"),
        ("5.", "5"), ("V ", "5"), ("V.", "5"),
        ("6.", "6"), ("VI ", "6"), ("VI.", "6"),
    ];

    for (s1, s2) in pairs {
        if adj_english_name.starts_with(s1) {
            if let Some(&array_index) = ENGLISH_NAME_MAP.get(format_compact!("{}{}", s2, &adj_english_name[s1.len()..]).as_str()) {
                return Some(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_book_code)
            }
        }
    }

    None
}

// pub fn usfm_num_to_usfm_abbreviation(usfm_num_str: &str) -> Result<String, Box<dyn Error>> {
//     println!("usfm_num_to_usfm_bbb for {:?}", usfm_num_str);
//     if !&self.USFMNumberDict.contains_key(usfm_num_str) {
//         return Err("Invalid USFM number: '".to_owned() + &usfm_num_str + "'")?; // I never actually figured out why I need the question mark?
//     }
//     let bbbStringOrListOfStrings =
//         &self.USFMNumberDict[usfm_num_str].USFMAbbreviationOrAbbreviations;
//     match bbbStringOrListOfStrings {
//         StringOrListOfStrings::Abbreviation(bbb) => Ok(bbb.to_string()),
//         StringOrListOfStrings::ListOfAbbreviations(bbb_list) => Ok(bbb_list[0].to_string()),
//     }
// }

// pub fn usfm_num_to_bos_book_code(usfm_num_str: &str) -> Result<String, Box<dyn Error>> {
//     println!("usfm_num_to_usfm_bbb for {:?}", usfm_num_str);
//     if !&self.USFMNumberDict.contains_key(usfm_num_str) {
//         return Err("Invalid USFM number: '".to_owned() + &usfm_num_str + "'")?; // I never actually figured out why I need the question mark?
//     }
//     let bbbStringOrListOfStrings =
//         &self.USFMNumberDict[usfm_num_str].referenceAbbreviationOrAbbreviations;
//     match bbbStringOrListOfStrings {
//         StringOrListOfStrings::Abbreviation(bbb) => Ok(bbb.to_string()),
//         StringOrListOfStrings::ListOfAbbreviations(bbb_list) => Ok(bbb_list[0].to_string()),
//     }
// }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loaded_books_codes() {
        println!(
            "    Loaded Bible books codes data for {:?} books.",
            BIBLE_BOOKS_CODES_ARRAY.len()
        );
        assert_eq!(
            BIBLE_BOOKS_CODES_ARRAY.len(),
            REFERENCE_ABBREVIATION_MAP.len()
        );
        assert!(BIBLE_BOOKS_CODES_ARRAY.len() > USFM_ABBREVIATION_MAP.len());
    }

    #[test]
    fn test_is_valid_bos_book_code() {
        assert_eq!(is_valid_bos_book_code("SAM"), true);
        assert_eq!(is_valid_bos_book_code("SIM"), false);
    }

    #[test]
    fn test_bos_book_code_to_usfm_abbrev() {
        assert_eq!(bos_book_code_to_usfm_abbrev("EXO"), Ok(Some("Exo")));
        assert_eq!(bos_book_code_to_usfm_abbrev("CH1"), Ok(Some("1Ch")));
        println!(
            "    bos_book_code_to_usfm_abbrev for 'SAM' got {:?}",
            bos_book_code_to_usfm_abbrev("SAM")
        );
        println!(
            "    bos_book_code_to_usfm_abbrev for 'XyZ' got {:?}",
            bos_book_code_to_usfm_abbrev("XyZ")
        );
        assert_eq!(bos_book_code_to_usfm_abbrev("SAM"), Ok(None));
        assert!(matches!(bos_book_code_to_usfm_abbrev("XyZ"), Err(LookupError::AbbrevNotFound("Reference",ref key)) if *key == "XyZ"));
        assert!(matches!(bos_book_code_to_usfm_abbrev("XyZ"), Err(LookupError::AbbrevNotFound("Reference","XyZ"))));
    }

    #[test]
    fn test_usfm_to_bos_book_code() {
        assert_eq!(usfm_abbrev_to_bos_book_code("Exo"), Ok("EXO"));
        assert_eq!(usfm_abbrev_to_bos_book_code("exo"), Ok("EXO"));
        assert_eq!(usfm_abbrev_to_bos_book_code("1Ki"), Ok("KI1"));
        assert_eq!(usfm_abbrev_to_bos_book_code("MAT"), Ok("MAT"));
        assert_eq!(usfm_abbrev_to_bos_book_code("1PE"), Ok("PE1"));
        assert!(usfm_abbrev_to_bos_book_code("XyZ").is_err());
        assert!(matches!(usfm_abbrev_to_bos_book_code("XyZ"), Err(LookupError::AbbrevNotFound("USFM","XyZ"))));
    }

    #[test]
    fn test_osis_to_bos_book_code() {
        assert_eq!(osis_book_code_to_bos_book_code("Exod", true), Ok("EXO"));
        assert!(osis_book_code_to_bos_book_code("XyZ", true).is_err());
        assert!(matches!(osis_book_code_to_bos_book_code("XyZ", true), Err(LookupError::AbbrevNotFound("OSIS","XyZ"))));
        // Test fallback
        assert_eq!(osis_book_code_to_bos_book_code("Exod", false), Ok("EXO"));
    }

    #[test]
    fn test_short_abbrev_to_bos_book_code() {
        assert_eq!(short_abbrev_to_bos_book_code("Ge", true), Ok("GEN"));
        assert_eq!(short_abbrev_to_bos_book_code("ge", true), Ok("GEN"));
        assert!(short_abbrev_to_bos_book_code("1 Sa", true).is_err());
        
        // Test fallbacks
        assert_eq!(short_abbrev_to_bos_book_code("1 Sa", false), Ok("SA1")); // space removal
        assert_eq!(short_abbrev_to_bos_book_code("Gen", false), Ok("GEN")); // SBL fallback
        assert_eq!(short_abbrev_to_bos_book_code("Sos", false), Ok("SNG")); // NET fallback
    }

    #[test]
    fn test_get_all_usfm_abbreviations() {
        let all = get_all_usfm_abbreviations(false);
        assert!(all.iter().any(|s| s == "Gen"));
        assert!(!all.iter().any(|s| s == "GEN"));

        let all_up = get_all_usfm_abbreviations(true);
        assert!(all_up.iter().any(|s| s == "GEN"));
        assert!(!all_up.iter().any(|s| s == "Gen"));
    }

    #[test]
    fn test_bcv_reference_to_int() {
        let gen1_1 = bcv_reference_to_int("GEN", "1", "1", None);
        let gen1_2 = bcv_reference_to_int("GEN", "1", "2", None);
        let exo1_1 = bcv_reference_to_int("EXO", "1", "1", None);
        
        assert!(gen1_1 < gen1_2);
        assert!(gen1_2 < exo1_1);
     
        let psa119_1 = bcv_reference_to_int("PSA", "119", "1", None);
        let psa119_1a = bcv_reference_to_int("PSA", "119", "1", Some("a"));
        let psa119_1b = bcv_reference_to_int("PSA", "119", "1", Some("b"));
     
        assert_eq!(psa119_1, psa119_1a);
        assert!(psa119_1a < psa119_1b);
    }
    
    #[test]
    fn test_tidy_bbb() {
        // Defaults: title_case=false, allow_four_chars=true, insert_char=""
        assert_eq!(tidy_bbb("SA1", false, true, ""), "1SAM");
        assert_eq!(tidy_bbb("SA1", true, true, ""), "1Sam");
        assert_eq!(tidy_bbb("SA1", true, false, ""), "1Sa");
        assert_eq!(tidy_bbb("SA1", true, true, "-"), "1-Sam");
        assert_eq!(tidy_bbb("SA1", true, true, " "), "1 Sam");
        assert_eq!(tidy_bbb("SA1", false, false, "-"), "1-SA");

        // Check standard 3-char codes
        assert_eq!(tidy_bbb("GEN", false, true, ""), "GEN");
        assert_eq!(tidy_bbb("GEN", true, true, ""), "Gen");

        // Check 4-char specific mappings
        assert_eq!(tidy_bbb("RUT", false, true, ""), "RUTH");
        assert_eq!(tidy_bbb("RUT", true, true, ""), "Ruth");
        assert_eq!(tidy_bbb("RUT", true, false, ""), "Rut");
    }

    #[test]
    fn test_english_name_to_bos_book_code() {
        assert_eq!(english_name_to_bos_book_code("Exodus"), Some("EXO"));
        assert_eq!(english_name_to_bos_book_code("Esther"), Some("EST"));
        assert_eq!(english_name_to_bos_book_code("Ester"), Some("EST"));
        assert_eq!(english_name_to_bos_book_code("Eccle"), Some("ECC"));
        assert_eq!(english_name_to_bos_book_code("1 Cor"), Some("CO1"));
        assert_eq!(english_name_to_bos_book_code("1 Co"), Some("CO1"));
        assert_eq!(english_name_to_bos_book_code("1Cor"), Some("CO1"));
        assert_eq!(english_name_to_bos_book_code("1Co"), Some("CO1"));
        assert_eq!(english_name_to_bos_book_code("1.Cor"), Some("CO1"));
        assert_eq!(english_name_to_bos_book_code("1.Co"), Some("CO1"));
        assert_eq!(english_name_to_bos_book_code("XyZ"), None);
    }

    #[test]
    fn test_book_metadata_lookups() {
        assert_eq!(get_bos_book_code_from_reference_number(1), Some("GEN"));
        assert_eq!(get_bos_book_code_from_reference_number(66), Some("REV"));
        assert_eq!(get_bos_book_code_from_reference_number(999), Some("UNK"));
        assert_eq!(get_bos_book_code_from_reference_number(1000), None);

        assert_eq!(get_ccel_number_str("GEN"), Some("1"));
        assert_eq!(get_short_abbreviation("GEN"), Some("Ge"));
        assert_eq!(get_sbl_abbreviation("GEN"), Some("Gen"));
        assert_eq!(bos_to_osis_book_code("GEN"), Some("Gen"));
        assert_eq!(bos_to_sword_book_code("GEN"), Some("Gen"));
        assert_eq!(bos_book_code_to_usfm_num_str("MAT"), Some("41"));
        assert_eq!(get_usx_num_str("MAT"), Some("040"));
        assert_eq!(get_unbound_bible_code("GEN"), Some("01O"));
        assert_eq!(get_bibledit_num_str("MAT"), Some("40"));
        assert_eq!(get_logos_num_str("MAT"), Some("61"));
        assert_eq!(bos_to_net_bible_book_code("SNG"), Some("Sos"));
        assert_eq!(bos_to_drupal_book_code("SNG"), Some("Son"));
        assert_eq!(get_byzantine_abbreviation("MAT"), Some("MT"));
    }

    #[test]
    fn test_chapter_lookups() {
        assert_eq!(get_expected_chapters_list("EST"), vec![10]);
        assert_eq!(get_expected_chapters_list("PSA"), vec![150, 151]);
        assert_eq!(get_expected_chapters_list("XyZ"), Vec::<u16>::new());

        assert_eq!(get_max_chapters("PSA"), 151);
        assert_eq!(get_max_chapters("EST"), 10);
        assert_eq!(get_max_chapters("XyZ"), -1);

        assert!(is_single_chapter_book("PHM"));
        assert!(!is_single_chapter_book("GEN"));
        assert!(is_chapter_verse_book("GEN"));

        let osis_single = get_osis_single_chapter_books_list();
        assert!(osis_single.contains(&"Phlm"));
        assert!(!osis_single.contains(&"Gen"));
    }

    #[test]
    fn test_categorization() {
        // nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
        assert!(is_old_testament_nr("GEN"));
        assert!(!is_old_testament_nr("TOB"));
        assert!(!is_old_testament_nr("MAT"));
        assert!(is_new_testament_nr("MAT"));
        assert!(!is_new_testament_nr("TOB"));
        assert!(!is_new_testament_nr("GEN"));
        assert!(is_deuterocanon_nr("TOB"));
        assert!(!is_deuterocanon_nr("GEN"));
        assert!(!is_deuterocanon_nr("MRK"));

        assert!(!is_old_testament_nr("FRT"));
        assert!(!is_new_testament_nr("FRT"));
        assert!(!is_deuterocanon_nr("FRT"));

        assert_eq!(get_typical_section("GEN"), Some("OT"));
        assert_eq!(get_typical_section("MAT"), Some("NT"));
        assert!(continues_through_chapters("GEN"));
        assert!(!continues_through_chapters("PSA"));
    }

    #[test]
    fn test_name_lookups() {
        assert_eq!(get_book_name("GEN"), Some("בְּרֵאשִׁית"));
        // nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
        assert_eq!(get_english_name_nr("GEN"), Some("Genesis"));
        assert_eq!(get_english_name_list_nr("GEN"), vec!["Genesis", "1 Moses"]);
    }

    #[test]
    fn test_has_psalm_title() {
        assert!(!has_psalm_title("PSA", "1"));
        assert!(!has_psalm_title("PSA", "2"));
        assert!(has_psalm_title("PSA", "3"));
        assert!(has_psalm_title("PSA", "53"));
        assert!(!has_psalm_title("GEN", "2"));
        assert!(!has_psalm_title("PSA", "0"));
        assert!(!has_psalm_title("PSA", "-1"));
        assert!(!has_psalm_title("Psalm", "2"));
    }
}

//WARNINGS_GO_HERE
