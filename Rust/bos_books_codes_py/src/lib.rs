// Python bindings for BibleOrgSys/BOS 3-character Bible Books Codes.
// Originally converted from Python to Rust by RJH, updated May 2026 by Gemini for RJH.
// LAST_MODIFIED_DATE: 2026-05-20

use pyo3::prelude::*;
// use std::error::Error;
use ::bos_books_codes::{
    english_name_to_bos_book_code, osis_book_code_to_bos_book_code,
    drupal_book_code_to_bos_book_code, unbound_code_to_bos_book_code,
    short_abbrev_to_bos_book_code, sbl_abbrev_to_bos_book_code,
    net_bible_abbrev_to_bos_book_code,
    bos_book_code_to_usfm_abbrev, usfm_abbrev_to_bos_book_code,
    get_reference_number, get_sequence_number,
    is_old_testament_nr, is_new_testament_nr, is_deuterocanon_nr, is_valid_bos_book_code,
    get_bos_book_code_from_reference_number, get_all_bos_book_codes,
    get_all_osis_book_codes,
    get_sequence_list,
    get_ccel_number_str, get_short_abbreviation, get_sbl_abbreviation, bos_to_osis_book_code,
    bos_to_sword_book_code, bos_book_code_to_usfm_num_str, get_usx_num_str, get_unbound_bible_code,
    get_bibledit_num_str, get_logos_num_str, bos_to_net_bible_book_code,
    bos_to_drupal_book_code, get_byzantine_abbreviation, get_expected_chapters_list,
    get_max_chapters, get_single_chapter_books_list, get_osis_single_chapter_books_list,
    get_possible_alternative_books,
    is_single_chapter_book, is_chapter_verse_book, get_typical_section, continues_through_chapters,
    get_book_name, get_english_name_nr, get_english_name_list_nr, tidy_bbb,
    get_full_entry, OptionalNumberOrTwoNumbers, has_psalm_title,
    bcv_reference_to_int,
};
use pyo3::types::{PyDict, PyList, PyTuple};
use compact_str::format_compact;

/// Returns True if the given reference abbreviation is valid.
#[pyfunction]
#[pyo3(name = "is_valid_bos_book_code")]
fn is_valid_bos_book_code_py(bos_book_code: &str) -> PyResult<bool> {
    Ok(is_valid_bos_book_code(bos_book_code))
}

/// Converts a BibleOrgSys (BOS) reference abbreviation book code to a USFM book code.
#[pyfunction]
#[pyo3(name = "bos_book_code_to_usfm_abbrev")]
fn bos_book_code_to_usfm_abbrev_py(bos_book_code: &str) -> PyResult<Option<String>> {
    Ok(bos_book_code_to_usfm_abbrev(bos_book_code)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .map(|s| s.to_string()))
}

/// Returns the referenceNumber 1..999 for the given book code (referenceAbbreviation).
#[pyfunction]
#[pyo3(name = "get_reference_number")]
fn get_reference_number_py(bos_book_code: &str) -> PyResult<u16> {
    Ok(get_reference_number(bos_book_code)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?)
}

/// Returns the sequence number for a given reference abbreviation.
#[pyfunction]
#[pyo3(name = "get_sequence_number")]
fn get_sequence_number_py(bos_book_code: &str) -> PyResult<u16> {
    Ok(get_sequence_number(bos_book_code).unwrap_or(9999))
}

/// Returns True if the given reference abbreviation is an Old Testament book.
/// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
#[pyfunction]
#[pyo3(name = "is_old_testament_nr")]
fn is_old_testament_nr_py(bos_book_code: &str) -> PyResult<bool> {
    Ok(is_old_testament_nr(bos_book_code))
}

/// Returns True if the given reference abbreviation is a New Testament book.
/// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
#[pyfunction]
#[pyo3(name = "is_new_testament_nr")]
fn is_new_testament_nr_py(bos_book_code: &str) -> PyResult<bool> {
    Ok(is_new_testament_nr(bos_book_code))
}

/// Returns True if the given reference abbreviation is a Deuterocanonical book.
/// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
#[pyfunction]
#[pyo3(name = "is_deuterocanon_nr")]
fn is_deuterocanon_nr_py(bos_book_code: &str) -> PyResult<bool> {
    Ok(is_deuterocanon_nr(bos_book_code))
}

/// Converts a USFM book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
#[pyo3(name = "usfm_abbrev_to_bos_book_code", signature = (usfm_abbreviation, strict=false))]
// NOTE: This code doesn't exactly match the original Python code which always did to_uppercase() and better handled when the result was multiple abbreviations.
fn usfm_abbrev_to_bos_book_code_py(usfm_abbreviation: &str, strict: bool) -> PyResult<String> {
    Ok(usfm_abbrev_to_bos_book_code(usfm_abbreviation, strict)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}

/// Backward compatibility alias for usfm_abbrev_to_bos_book_code.
#[pyfunction]
#[pyo3(name = "usfm_abbrev_to_bos_book_code", signature = (usfm_abbreviation, strict=false))]
fn get_bbb_from_usfm_abbreviation_py(usfm_abbreviation: &str, strict: bool) -> PyResult<String> {
    Ok(usfm_abbrev_to_bos_book_code(usfm_abbreviation, strict)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}


/// Converts a short book abbreviation to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
#[pyo3(name = "short_abbrev_to_bos_book_code", signature = (short_abbreviation, strict=false))]
fn short_abbrev_to_bos_book_code_py(short_abbreviation: &str, strict: bool) -> PyResult<String> {
    Ok(short_abbrev_to_bos_book_code(short_abbreviation, strict)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}

/// Backward compatibility alias for short_abbrev_to_bos_book_code.
#[pyfunction]
#[pyo3(name = "short_abbrev_to_bos_book_code", signature = (short_abbreviation, strict=false))]
fn get_bbb_from_short_abbreviation_py(short_abbreviation: &str, strict: bool) -> PyResult<String> {
    Ok(short_abbrev_to_bos_book_code(short_abbreviation, strict)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}


/// Converts an OSIS book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
#[pyo3(name = "osis_book_code_to_bos_book_code", signature = (osis_book_code, strict=false))]
fn osis_book_code_to_bos_book_code_py(osis_book_code: &str, strict: bool) -> PyResult<String> {
    Ok(osis_book_code_to_bos_book_code(osis_book_code, strict)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}

/// Backward compatibility alias for osis_book_code_to_bos_book_code.
#[pyfunction]
#[pyo3(name = "osis_book_code_to_bos_book_code", signature = (osis_book_code, strict=false))]
fn get_bbb_from_osis_abbreviation_py(osis_book_code: &str, strict: bool) -> PyResult<String> {
    Ok(osis_book_code_to_bos_book_code(osis_book_code, strict)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}

/// Converts a Drupal book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
#[pyo3(name = "drupal_book_code_to_bos_book_code")]
fn drupal_book_code_to_bos_book_code_py(drupal_book_code: &str) -> PyResult<String> {
    Ok(drupal_book_code_to_bos_book_code(drupal_book_code)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}

/// Converts an Unbound book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
#[pyo3(name = "unbound_code_to_bos_book_code")]
fn unbound_code_to_bos_book_code_py(unbound_code: &str) -> PyResult<String> {
    Ok(unbound_code_to_bos_book_code(unbound_code)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}

/// Converts an SBL book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
#[pyo3(name = "sbl_abbrev_to_bos_book_code")]
fn sbl_abbrev_to_bos_book_code_py(sbl_abbreviation: &str) -> PyResult<String> {
    Ok(sbl_abbrev_to_bos_book_code(sbl_abbreviation)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}

/// Converts a NET Bible book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
#[pyo3(name = "net_bible_abbrev_to_bos_book_code")]
fn net_bible_abbrev_to_bos_book_code_py(net_bible_abbreviation: &str) -> PyResult<String> {
    Ok(net_bible_abbrev_to_bos_book_code(net_bible_abbreviation)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?
        .to_string())
}

// Tries to see if an English book name can be narrowed down to a a reference abbreviation book code.
#[pyfunction]
#[pyo3(name = "english_name_to_bos_book_code")]
fn english_name_to_bos_book_code_py(english_name: &str) -> PyResult<Option<&'static str>> {
    Ok(english_name_to_bos_book_code(english_name))
}

/// Return the reference abbreviation for the given book number (reference number).
/// This is probably only useful in the range 1..66 (GEN..REV).
/// (After that, it specifies our arbitrary order.)
#[pyfunction]
#[pyo3(name = "get_bos_book_code_from_reference_number")]
fn get_bos_book_code_from_reference_number_py(reference_number: u16) -> PyResult<Option<&'static str>> {
    Ok(get_bos_book_code_from_reference_number(reference_number))
}

#[pyfunction]
#[pyo3(name = "get_all_bos_book_codes")]
fn get_all_bos_book_codes_py<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    for bbb in get_all_bos_book_codes() {
        list.append(bbb)?;
    }
    Ok(list)
}

#[pyfunction]
#[pyo3(name = "get_all_osis_book_codes")]
fn get_all_osis_book_codes_py<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    for abbrev in get_all_osis_book_codes() {
        list.append(abbrev)?;
    }
    Ok(list)
}

#[pyfunction]
#[pyo3(name = "get_all_usfm_abbreviations", signature = (to_upper=false))]
fn get_all_usfm_abbreviations_py<'py>(py: Python<'py>, to_upper: bool) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    for abbrev in ::bos_books_codes::get_all_usfm_abbreviations(to_upper) {
        list.append(abbrev.as_str())?;
    }
    Ok(list)
}

/// Backward compatibility alias for get_all_usfm_abbreviations.
#[pyfunction]
#[pyo3(name = "get_all_usfm_books_codes", signature = (to_upper=false))]
fn get_all_usfm_books_codes_py<'py>(py: Python<'py>, to_upper: bool) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    for abbrev in ::bos_books_codes::get_all_usfm_abbreviations(to_upper) {
        list.append(abbrev.as_str())?;
    }
    Ok(list)
}

#[pyfunction]
#[pyo3(name = "get_all_usfm_books_code_number_triples")]
fn get_all_usfm_books_code_number_triples_py<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    for triple in ::bos_books_codes::get_all_usfm_books_code_number_triples() {
        list.append(PyTuple::new(py, &[triple.0, triple.1, triple.2])?)?;
    }
    Ok(list)
}

#[pyfunction]
#[pyo3(name = "get_all_usx_books_code_number_triples")]
fn get_all_usx_books_code_number_triples_py<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    for triple in ::bos_books_codes::get_all_usx_books_code_number_triples() {
        list.append(PyTuple::new(py, &[triple.0, triple.1, triple.2])?)?;
    }
    Ok(list)
}

#[pyfunction]
#[pyo3(name = "get_all_bibledit_books_code_number_triples")]
fn get_all_bibledit_books_code_number_triples_py<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    for triple in ::bos_books_codes::get_all_bibledit_books_code_number_triples() {
        list.append(PyTuple::new(py, &[triple.0, triple.1, triple.2])?)?;
    }
    Ok(list)
}

/// Return a list of BBB codes in a sequence that could be used for the print order
/// if no further information is available.
/// If you supply a list of books, it puts your actual book codes into the default order.
#[pyfunction]
#[pyo3(name = "get_sequence_list", signature = (my_list=None))]
fn get_sequence_list_py<'py>(py: Python<'py>, my_list: Option<Vec<String>>) -> PyResult<Bound<'py, PyList>> {
    let list_refs: Option<Vec<&str>> = my_list.as_ref().map(|v| v.iter().map(|s| s.as_str()).collect());
    let list = PyList::empty(py);
    for bbb in get_sequence_list(list_refs) {
        list.append(bbb)?;
    }
    Ok(list)
}

#[pyfunction]
#[pyo3(name = "get_ccel_number")]
fn get_ccel_number_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_ccel_number_str(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_short_abbreviation")]
fn get_short_abbreviation_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_short_abbreviation(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_sbl_abbreviation")]
fn get_sbl_abbreviation_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_sbl_abbreviation(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "bos_to_osis_book_code")]
fn bos_to_osis_book_code_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(bos_to_osis_book_code(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "bos_to_sword_book_code")]
fn bos_to_sword_book_code_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(bos_to_sword_book_code(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "bos_book_code_to_usfm_num_str")]
fn bos_book_code_to_usfm_num_str_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(bos_book_code_to_usfm_num_str(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_usx_num_str")]
fn get_usx_num_str_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_usx_num_str(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_unbound_bible_code")]
fn get_unbound_bible_code_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_unbound_bible_code(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_bibledit_num_str")]
fn get_bibledit_num_str_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_bibledit_num_str(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_logos_num_str")]
fn get_logos_num_str_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_logos_num_str(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "bos_to_net_bible_book_code")]
fn bos_to_net_bible_book_code_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(bos_to_net_bible_book_code(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "bos_to_drupal_book_code")]
fn bos_to_drupal_book_code_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(bos_to_drupal_book_code(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_byzantine_abbreviation")]
fn get_byzantine_abbreviation_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_byzantine_abbreviation(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_possible_alternative_books")]
fn get_possible_alternative_books_py(bos_book_code: &str) -> PyResult<Vec<&'static str>> {
    Ok(get_possible_alternative_books(bos_book_code))
}

/// Gets a list with the number of expected chapters for the given book code (reference abbreviation).
/// Why is it a list? Because some books have alternate possible numbers of chapters
/// depending on the Biblical tradition.
#[pyfunction]
#[pyo3(name = "get_expected_chapters_list")]
fn get_expected_chapters_list_py(bos_book_code: &str) -> PyResult<Vec<u16>> {
    Ok(get_expected_chapters_list(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_max_chapters")]
fn get_max_chapters_py(bos_book_code: &str) -> PyResult<i16> {
    Ok(get_max_chapters(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_single_chapter_books_list")]
fn get_single_chapter_books_list_py() -> PyResult<Vec<&'static str>> {
    Ok(get_single_chapter_books_list())
}

#[pyfunction]
#[pyo3(name = "get_osis_single_chapter_books_list")]
fn get_osis_single_chapter_books_list_py() -> PyResult<Vec<&'static str>> {
    Ok(get_osis_single_chapter_books_list())
}

#[pyfunction]
#[pyo3(name = "is_single_chapter_book")]
fn is_single_chapter_book_py(bos_book_code: &str) -> PyResult<bool> {
    Ok(is_single_chapter_book(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "is_chapter_verse_book")]
fn is_chapter_verse_book_py(bos_book_code: &str) -> PyResult<bool> {
    Ok(is_chapter_verse_book(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_typical_section")]
fn get_typical_section_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_typical_section(bos_book_code))
}

/// Returns true if the storyline of the book continues through chapters,
/// i.e., the chapter divisions are artificial.
/// Returns false for books like Psalms where chapters are actual units.
#[pyfunction]
#[pyo3(name = "continues_through_chapters")]
fn continues_through_chapters_py(bos_book_code: &str) -> PyResult<bool> {
    Ok(continues_through_chapters(bos_book_code))
}

/// Returns true for 116 Psalms that traditionally have a header field in the Hebrew (USFM /d field).
/// Otherwise returns false (for the other 34, plus for other books).
#[pyfunction]
#[pyo3(name = "has_psalm_title")]
fn has_psalm_title_py(bbb: &str, c: &str) -> PyResult<bool> {
    Ok(has_psalm_title(bbb, c))
}

#[pyfunction]
#[pyo3(name = "get_book_name")]
fn get_book_name_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_book_name(bos_book_code))
}

/// Returns the first English name for a book.
/// Remember: These names are only intended as comments or for some basic module processing.
/// They are not intended to be used for a proper international human interface.
/// The first one in the list is supposed to be the more common.
// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
#[pyfunction]
#[pyo3(name = "get_english_name_nr")]
fn get_english_name_nr_py(bos_book_code: &str) -> PyResult<Option<&'static str>> {
    Ok(get_english_name_nr(bos_book_code))
}

#[pyfunction]
#[pyo3(name = "get_english_name_list_nr")]
fn get_english_name_list_nr_py(bos_book_code: &str) -> PyResult<Vec<&'static str>> {
    Ok(get_english_name_list_nr(bos_book_code))
}

/// Change book codes like SA1 to the conventional 1SA
/// (or 1Sa using the titleCase flag or 1 SAM using the allowFourChars and with a space for insertChar).
/// BBB is always three characters starting with an UPPERCASE LETTER.
/// insertChar prevents 1SA (becomes 1-SA or whatever) from being mistaken for ISA.
#[pyfunction]
#[pyo3(name = "tidy_bbb", signature = (bbb, title_case=false, allow_four_chars=true, insert_char=None))]
fn tidy_bbb_py(bbb: &str, title_case: bool, allow_four_chars: bool, insert_char: Option<&str>) -> PyResult<String> {
    Ok(tidy_bbb(bbb, title_case, allow_four_chars, insert_char.unwrap_or("")).to_string())
}

#[pyfunction]
#[pyo3(name = "tidy_bbbs", signature = (bbbs, title_case=false, allow_four_chars=true))]
fn tidy_bbbs_py<'py>(py: Python<'py>, bbbs: Vec<String>, title_case: bool, allow_four_chars: bool) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    for bbb in bbbs {
        list.append(tidy_bbb(&bbb, title_case, allow_four_chars, "").as_str())?;
    }
    Ok(list)
}

/// Convert a BCV or BCVS reference to an integer especially so that references can be sorted.
/// If a verse is a verse span with a hyphen (e.g., '3-4'), it uses the value before the hyphen.
#[pyfunction]
#[pyo3(name = "bcv_reference_to_int", signature = (bbb, c, v, s=None))]
fn bcv_reference_to_int_py(bbb: &str, c: &str, v: &str, s: Option<&str>) -> PyResult<i32> {
    Ok(bcv_reference_to_int(bbb, c, v, s))
}

#[pyfunction]
#[pyo3(name = "sort_bcv_references")]
fn sort_bcv_references_py<'py>(py: Python<'py>, references: Bound<'py, PyList>) -> PyResult<Bound<'py, PyList>> {
    let mut refs: Vec<(String, String, String, Option<String>)> = Vec::new();
    for item in references.iter() {
        if let Ok(tuple) = item.cast::<PyTuple>() {
            let bbb: String = tuple.get_item(0)?.extract()?;
            let c: String = tuple.get_item(1)?.extract()?;
            let v: String = tuple.get_item(2)?.extract()?;
            let s: Option<String> = if tuple.len() > 3 {
                Some(tuple.get_item(3)?.extract()?)
            } else {
                None
            };
            refs.push((bbb, c, v, s));
        }
    }

    refs.sort_by_key(|r| bcv_reference_to_int(&r.0, &r.1, &r.2, r.3.as_deref()));

    let sorted_list = PyList::empty(py);
    for r in refs {
        let tuple = if let Some(s) = r.3 {
            PyTuple::new(py, &[r.0, r.1, r.2, s])?
        } else {
            PyTuple::new(py, &[r.0, r.1, r.2])?
        };
        sorted_list.append(tuple)?;
    }

    Ok(sorted_list)
}

#[pyfunction]
#[pyo3(name = "get_full_bookcodes_entry")]
fn get_full_bookcodes_entry_py<'py>(py: Python<'py>, bos_book_code: &str) -> PyResult<Bound<'py, PyDict>> {
    let entry = get_full_entry(bos_book_code).map_err(|e| PyErr::new::<pyo3::exceptions::PyKeyError, _>(e.to_string()))?;
    let dict = PyDict::new(py);

    dict.set_item("originalLanguageCode", entry.original_language_code)?;
    dict.set_item("bookName", entry.original_language_book_name)?;
    dict.set_item("bookNameEnglishGuide", entry.book_name_English_guide)?;
    dict.set_item("referenceNumber", entry.BOS_reference_number)?;

    let expected_chapters = match entry.expected_num_chapters {
        OptionalNumberOrTwoNumbers::Number(n) => Some(format_compact!("{}", n).to_string()),
        OptionalNumberOrTwoNumbers::TwoNumbers(nums) => Some(format_compact!("{},{}", nums[0], nums[1]).to_string()),
        OptionalNumberOrTwoNumbers::None => None,
    };
    dict.set_item("numExpectedChapters", expected_chapters)?;

    dict.set_item("shortAbbreviation", entry.short_abbreviation)?;
    dict.set_item("SBLAbbreviation", entry.SBL_abbreviation)?;
    dict.set_item("OSISAbbreviation", entry.OSIS_abbreviation)?;
    dict.set_item("SwordAbbreviation", entry.Sword_abbreviation)?;
    dict.set_item("CCELNumberString", entry.CCEL_number_str)?;
    dict.set_item("USFMAbbreviation", entry.USFM_abbreviation)?;
    dict.set_item("USFMNumberString", entry.USFM_number_str)?;
    dict.set_item("USXNumberString", entry.USX_number_str)?;
    dict.set_item("UnboundCodeString", entry.Unbound_Code)?;
    dict.set_item("BibleditNumberString", entry.Bibledit_number_str)?;
    dict.set_item("LogosNumberString", entry.Logos_number_str)?;
    dict.set_item("LogosAbbreviation", entry.Logos_abbreviation)?;
    dict.set_item("NETBibleAbbreviation", entry.NET_Bible_abbreviation)?;
    dict.set_item("DrupalBibleAbbreviation", entry.Drupal_Bible_abbreviation)?;
    dict.set_item("ByzantineAbbreviation", entry.Byzantine_abbreviation)?;

    dict.set_item("possibleAlternativeBooks", if entry.possible_alternative_books_codes.is_empty() { None } else { Some(entry.possible_alternative_books_codes.to_vec()) })?;
    dict.set_item("typicalSection", entry.typical_section)?;

    Ok(dict)
}

/// A Python module implemented in Rust.
#[pymodule]
fn bos_books_codes_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(bos_book_code_to_usfm_abbrev_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(usfm_abbrev_to_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_usfm_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(osis_book_code_to_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_osis_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(drupal_book_code_to_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(unbound_code_to_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(short_abbrev_to_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_short_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(sbl_abbrev_to_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(net_bible_abbrev_to_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(english_name_to_bos_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_reference_number_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_sequence_number_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_old_testament_nr_py, m)?)?; // nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
    m.add_function(wrap_pyfunction!(is_new_testament_nr_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_deuterocanon_nr_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bos_book_code_from_reference_number_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_bos_book_codes_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_osis_book_codes_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_usfm_abbreviations_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_usfm_books_codes_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_usfm_books_code_number_triples_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_usx_books_code_number_triples_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_all_bibledit_books_code_number_triples_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_sequence_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_ccel_number_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_short_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_sbl_abbreviation_py, m)?)?;
    m.add_function(wrap_pyfunction!(bos_to_osis_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(bos_to_sword_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(bos_book_code_to_usfm_num_str_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_usx_num_str_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_unbound_bible_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bibledit_num_str_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_logos_num_str_py, m)?)?;
    m.add_function(wrap_pyfunction!(bos_to_net_bible_book_code_py, m)?)?;
    m.add_function(wrap_pyfunction!(bos_to_drupal_book_code_py, m)?)?;
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
    m.add_function(wrap_pyfunction!(has_psalm_title_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_book_name_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_english_name_nr_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_english_name_list_nr_py, m)?)?;
    m.add_function(wrap_pyfunction!(tidy_bbb_py, m)?)?;
    m.add_function(wrap_pyfunction!(tidy_bbbs_py, m)?)?;
    m.add_function(wrap_pyfunction!(bcv_reference_to_int_py, m)?)?;
    m.add_function(wrap_pyfunction!(sort_bcv_references_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_full_bookcodes_entry_py, m)?)?;
    Ok(())
}
