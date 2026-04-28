use pyo3::prelude::*;
// use std::error::Error;
use ::bos_books_codes::{
    english_name_to_reference_abbrev, osis_abbrev_to_reference_abbrev,
    reference_abbrev_to_usfm_abbrev, usfm_abbrev_to_reference_abbrev,
};

/// Converts a USFM book code to a BibleOrgSys (BOS) reference abbreviation book code to a USFM book code.
#[pyfunction]
// RUST pub fn usfm_abbrev_to_reference_abbrev(reference_abbreviation: &str) -> Result<&str, Box<dyn Error>> {
fn reference_abbrev_to_usfm_abbrev_py(reference_abbreviation: &str) -> PyResult<String> {
    Ok(reference_abbrev_to_usfm_abbrev(reference_abbreviation)
        .unwrap().unwrap()
        .to_string())
}

/// Converts a USFM book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
// RUST pub fn usfm_abbrev_to_reference_abbrev(usfm_abbreviation: &str) -> Result<&str, Box<dyn Error>> {
fn usfm_abbrev_to_reference_abbrev_py(usfm_abbreviation: &str) -> PyResult<String> {
    Ok(usfm_abbrev_to_reference_abbrev(usfm_abbreviation)
        .unwrap()
        .to_string())
}

/// Converts an OSIS book code to a BibleOrgSys (BOS) reference abbreviation book code.
#[pyfunction]
// RUST pub fn osis_abbrev_to_reference_abbrev(osis_abbreviation: &str) -> Result<&str, Box<dyn Error>> {
fn osis_abbrev_to_reference_abbrev_py(osis_abbreviation: &str) -> PyResult<String> {
    // match osis_abbrev_to_reference_abbrev(osis_abbreviation) { // From ChatGPT fails
    //     Ok(abbrev) => Ok(abbrev),
    //     Err(err_msg) => Err(pyo3::exceptions::PyValueError::new_err(err_msg)),
    // }
    Ok(osis_abbrev_to_reference_abbrev(osis_abbreviation)
        .unwrap()
        .to_string())
}

// Tries to see if an English book name can be narrowed down to a a reference abbreviation book code.
#[pyfunction]
// RUST pub fn english_name_to_reference_abbrev(english_name: &str,) -> Option<&'static str> {
fn english_name_to_reference_abbrev_py(english_name: &str) -> PyResult<Option<&'static str>> {
    Ok(english_name_to_reference_abbrev(english_name))
}

/// A Python module implemented in Rust.
#[pymodule]
// fn bos_books_codes_py(_py: Python, m: &PyModule) -> PyResult<()> { // From ChatGPT gives MANY errors
fn bos_books_codes_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // From PyO3 tutorial
    m.add_function(wrap_pyfunction!(reference_abbrev_to_usfm_abbrev_py, m)?)?;
    m.add_function(wrap_pyfunction!(usfm_abbrev_to_reference_abbrev_py, m)?)?;
    m.add_function(wrap_pyfunction!(osis_abbrev_to_reference_abbrev_py, m)?)?;
    m.add_function(wrap_pyfunction!(english_name_to_reference_abbrev_py, m)?)?;
    Ok(())
}
