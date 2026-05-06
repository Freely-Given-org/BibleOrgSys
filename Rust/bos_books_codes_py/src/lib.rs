use pyo3::prelude::*;
// use std::error::Error;
use ::bos_books_codes::{
    english_name_to_reference_abbrev, osis_abbrev_to_reference_abbrev,
    reference_abbrev_to_usfm_abbrev, usfm_abbrev_to_reference_abbrev,
    get_reference_number, is_ot_nr, is_nt_nr, is_dc_nr, is_valid_reference_abbreviation,
    get_bbb_from_reference_number, get_all_reference_abbreviations,
    get_all_osis_abbreviations,
    get_sequence_list,
    get_ccel_number, get_short_abbreviation, get_sbl_abbreviation, get_osis_abbreviation,
    get_sword_abbreviation, get_usfm_num_str, get_usx_num_str, get_unbound_bible_code,
    get_bibledit_num_str, get_logos_num_str, get_net_bible_abbreviation,
    get_drupal_bible_abbreviation, get_byzantine_abbreviation, get_expected_chapters_list,
    get_max_chapters, get_single_chapter_books_list, get_osis_single_chapter_books_list,
    get_possible_alternative_books,
    is_single_chapter_book, is_chapter_verse_book, get_typical_section, continues_through_chapters,
    get_book_name, get_english_name_nr, get_english_name_list_nr, tidy_bbb,
};

/// Returns True if the given reference abbreviation is valid.
#[pyfunction]
fn is_valid_reference_abbreviation_py(reference_abbreviation: &str) -> PyResult<bool> {
    Ok(is_valid_reference_abbreviation(reference_abbreviation))
}

/// Converts a BibleOrgSys (BOS) reference abbreviation book code to a USFM book code.
#[pyfunction]
fn reference_abbrev_to_usfm_abbrev_py(reference_abbreviation: &str) -> PyResult<Option<String>> {
    Ok(reference_abbrev_to_usfm_abbrev(reference_abbreviation)
        .unwrap().map(|s| s.to_string()))
}

/// Returns the reference number for a given reference abbreviation.
#[pyfunction]
fn get_reference_number_py(reference_abbreviation: &str) -> PyResult<u16> {
    Ok(get_reference_number(reference_abbreviation).unwrap())
}

/// Returns True if the given reference abbreviation is an Old Testament book.
/// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
#[pyfunction]
fn is_ot_nr_py(reference_abbreviation: &str) -> PyResult<bool> {
    Ok(is_ot_nr(reference_abbreviation))
}

/// Returns True if the given reference abbreviation is a New Testament book.
/// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
#[pyfunction]
fn is_nt_nr_py(reference_abbreviation: &str) -> PyResult<bool> {
    Ok(is_nt_nr(reference_abbreviation))
}

/// Returns True if the given reference abbreviation is a Deuterocanonical book.
/// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
#[pyfunction]
fn is_dc_nr_py(reference_abbreviation: &str) -> PyResult<bool> {
    Ok(is_dc_nr(reference_abbreviation))
}

/// Converts a USFM book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
fn usfm_abbrev_to_reference_abbrev_py(usfm_abbreviation: &str) -> PyResult<String> {
    Ok(usfm_abbrev_to_reference_abbrev(usfm_abbreviation)
        .unwrap()
        .to_string())
}

/// Converts an OSIS book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
fn osis_abbrev_to_reference_abbrev_py(osis_abbreviation: &str) -> PyResult<String> {
    Ok(osis_abbrev_to_reference_abbrev(osis_abbreviation)
        .unwrap()
        .to_string())
}

// Tries to see if an English book name can be narrowed down to a a reference abbreviation book code.
#[pyfunction]
fn english_name_to_reference_abbrev_py(english_name: &str) -> PyResult<Option<&'static str>> {
    Ok(english_name_to_reference_abbrev(english_name))
}

#[pyfunction]
fn get_bbb_from_reference_number_py(reference_number: u16) -> PyResult<Option<&'static str>> {
    Ok(get_bbb_from_reference_number(reference_number))
}

#[pyfunction]
fn get_all_reference_abbreviations_py() -> PyResult<Vec<&'static str>> {
    Ok(get_all_reference_abbreviations())
}

#[pyfunction]
fn get_all_osis_abbreviations_py() -> PyResult<Vec<&'static str>> {
    Ok(get_all_osis_abbreviations())
}

#[pyfunction]
fn get_sequence_list_py() -> PyResult<Vec<&'static str>> {
    Ok(get_sequence_list())
}

#[pyfunction]
fn get_ccel_number_py(reference_abbreviation: &str) -> PyResult<Option<u16>> {
    Ok(get_ccel_number(reference_abbreviation))
}

#[pyfunction]
fn get_short_abbreviation_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_short_abbreviation(reference_abbreviation))
}

#[pyfunction]
fn get_sbl_abbreviation_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_sbl_abbreviation(reference_abbreviation))
}

#[pyfunction]
fn get_osis_abbreviation_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_osis_abbreviation(reference_abbreviation))
}

#[pyfunction]
fn get_sword_abbreviation_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_sword_abbreviation(reference_abbreviation))
}

#[pyfunction]
fn get_usfm_num_str_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_usfm_num_str(reference_abbreviation))
}

#[pyfunction]
fn get_usx_num_str_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_usx_num_str(reference_abbreviation))
}

#[pyfunction]
fn get_unbound_bible_code_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_unbound_bible_code(reference_abbreviation))
}

#[pyfunction]
fn get_bibledit_num_str_py(reference_abbreviation: &str) -> PyResult<Option<u16>> {
    Ok(get_bibledit_num_str(reference_abbreviation))
}

#[pyfunction]
fn get_logos_num_str_py(reference_abbreviation: &str) -> PyResult<Option<u16>> {
    Ok(get_logos_num_str(reference_abbreviation))
}

#[pyfunction]
fn get_net_bible_abbreviation_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_net_bible_abbreviation(reference_abbreviation))
}

#[pyfunction]
fn get_drupal_bible_abbreviation_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_drupal_bible_abbreviation(reference_abbreviation))
}

#[pyfunction]
fn get_byzantine_abbreviation_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_byzantine_abbreviation(reference_abbreviation))
}

#[pyfunction]
fn get_possible_alternative_books_py(reference_abbreviation: &str) -> PyResult<Vec<&'static str>> {
    Ok(get_possible_alternative_books(reference_abbreviation))
}

#[pyfunction]
fn get_expected_chapters_list_py(reference_abbreviation: &str) -> PyResult<Vec<u16>> {
    Ok(get_expected_chapters_list(reference_abbreviation))
}

#[pyfunction]
fn get_max_chapters_py(reference_abbreviation: &str) -> PyResult<i16> {
    Ok(get_max_chapters(reference_abbreviation))
}

#[pyfunction]
fn get_single_chapter_books_list_py() -> PyResult<Vec<&'static str>> {
    Ok(get_single_chapter_books_list())
}

#[pyfunction]
fn get_osis_single_chapter_books_list_py() -> PyResult<Vec<&'static str>> {
    Ok(get_osis_single_chapter_books_list())
}

#[pyfunction]
fn is_single_chapter_book_py(reference_abbreviation: &str) -> PyResult<bool> {
    Ok(is_single_chapter_book(reference_abbreviation))
}

#[pyfunction]
fn is_chapter_verse_book_py(reference_abbreviation: &str) -> PyResult<bool> {
    Ok(is_chapter_verse_book(reference_abbreviation))
}

#[pyfunction]
fn get_typical_section_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_typical_section(reference_abbreviation))
}

#[pyfunction]
fn continues_through_chapters_py(reference_abbreviation: &str) -> PyResult<bool> {
    Ok(continues_through_chapters(reference_abbreviation))
}

#[pyfunction]
fn get_book_name_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_book_name(reference_abbreviation))
}

#[pyfunction]
fn get_english_name_nr_py(reference_abbreviation: &str) -> PyResult<Option<&'static str>> {
    Ok(get_english_name_nr(reference_abbreviation))
}

#[pyfunction]
fn get_english_name_list_nr_py(reference_abbreviation: &str) -> PyResult<Vec<&'static str>> {
    Ok(get_english_name_list_nr(reference_abbreviation))
}

#[pyfunction]
fn tidy_bbb_py(bbb: &str, title_case: bool, allow_four_chars: bool, insert_char: &str) -> PyResult<String> {
    Ok(tidy_bbb(bbb, title_case, allow_four_chars, insert_char))
}

/// A Python module implemented in Rust.
#[pymodule]
fn bos_books_codes_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(reference_abbrev_to_usfm_abbrev_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_reference_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(usfm_abbrev_to_reference_abbrev_py, m)?)?;
    m.add_function(wrap_pyfunction!(osis_abbrev_to_reference_abbrev_py, m)?)?;
    m.add_function(wrap_pyfunction!(english_name_to_reference_abbrev_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_reference_number_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_ot_nr_py, m)?)?; // nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
    m.add_function(wrap_pyfunction!(is_nt_nr_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_dc_nr_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_reference_number_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_reference_abbreviations_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_osis_abbreviations_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_sequence_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_ccel_number_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_short_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_sbl_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_osis_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_sword_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_usfm_num_str_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_usx_num_str_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_unbound_bible_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bibledit_num_str_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_logos_num_str_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_net_bible_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_drupal_bible_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_byzantine_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_possible_alternative_books_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_expected_chapters_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_max_chapters_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_single_chapter_books_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_osis_single_chapter_books_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_single_chapter_book_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_chapter_verse_book_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_typical_section_py, m)?)?;
    m.add_function(wrap_pyfunction!(continues_through_chapters_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_book_name_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_english_name_nr_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_english_name_list_nr_py, m)?)?;
    m.add_function(wrap_pyfunction!(tidy_bbb_py, m)?)?;
    Ok(())
}
