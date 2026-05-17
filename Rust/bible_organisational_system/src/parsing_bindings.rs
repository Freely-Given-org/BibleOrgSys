//! Python bindings for BibleOrgSys Internals.
//!
//! This module provides PyO3 bindings to expose the Rust internals to Python.

use bos_internals::parsing;
use pyo3::prelude::*;

use crate::cv_index_bindings::{
    PyChapterVerse, PyCVIndexEntry, PyCVIndexIter, PyInternalBibleBookCVIndex,
    PyInternalBibleEntry, PyInternalBibleEntryList, PyInternalBibleEntryListIter,
    py_build_bible_cv_indexes,
};
use crate::discovery_bindings::{
    py_discover_bible, py_discover_book, py_discover_filenames, PyAggregateDiscoveryResults,
    PyBibleDiscoveryResults, PyBookDiscoveryResults, PyDiscoveryOptions, PyDiscoveryResults,
};
use crate::extras_bindings::{PyInternalBibleExtra, PyInternalBibleExtraList, PyInternalBibleExtraListIter};
use crate::processing_bindings::{PyObjectType, PyProcessLinesOptions, py_process_lines, py_process_bible};
use crate::section_index_bindings::{
    PyInternalBibleBookSectionIndex, PySectionIndexEntry, PySectionIndexIter,
    py_build_bible_section_indexes,
};
use crate::checking_bindings::{
    py_validate_processed_markers, py_validate_bible_markers, py_get_versification,
    py_get_bible_versification, py_get_added_units, py_get_bible_added_units,
    py_check_book, py_check_bible,
    PyDiscoveryFlags, PyCheckOptions,
};
use crate::io_bindings::{
    py_read_esfm_file, py_read_sfm_lines, py_read_sfm_records, py_read_usfm_file,
    py_split_usfm_marker_from_text,
};
use crate::ml_writer_bindings::{
    py_escape_characters, PyHumanReadable, PyMlOutputType, PyMlWriter, PySectionName,
};
use crate::xml_file_bindings::{py_validate_well_formedness, py_validate_with_lint};

/// Python module for BibleOrgSys internals.
#[pymodule]
fn bible_organisational_system(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Forward Rust logs to Python logging
    let _ = pyo3_log::try_init();

    m.add_function(wrap_pyfunction!(get_small_leading_int, m)?)?;
    m.add_function(wrap_pyfunction!(get_positive_leading_int, m)?)?;
    m.add_function(wrap_pyfunction!(set_rust_verbosity, m)?)?;
    m.add_function(wrap_pyfunction!(set_rust_debug, m)?)?;
    m.add_function(wrap_pyfunction!(set_rust_strict_checking, m)?)?;
    m.add_function(wrap_pyfunction!(py_process_lines, m)?)?;
    m.add_function(wrap_pyfunction!(py_process_bible, m)?)?;
    m.add_function(wrap_pyfunction!(py_discover_book, m)?)?;
    m.add_function(wrap_pyfunction!(py_discover_bible, m)?)?;
    m.add_function(wrap_pyfunction!(py_discover_filenames, m)?)?;
    m.add_function(wrap_pyfunction!(py_parse_word_attributes, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_processed_markers, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_bible_markers, m)?)?;
    m.add_function(wrap_pyfunction!(py_get_versification, m)?)?;
    m.add_function(wrap_pyfunction!(py_get_bible_versification, m)?)?;
    m.add_function(wrap_pyfunction!(py_get_added_units, m)?)?;
    m.add_function(wrap_pyfunction!(py_get_bible_added_units, m)?)?;
    m.add_function(wrap_pyfunction!(py_check_book, m)?)?;
    m.add_function(wrap_pyfunction!(py_check_bible, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_bible_cv_indexes, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_bible_section_indexes, m)?)?;

    m.add_function(wrap_pyfunction!(py_split_usfm_marker_from_text, m)?)?;
    m.add_function(wrap_pyfunction!(py_read_usfm_file, m)?)?;
    m.add_function(wrap_pyfunction!(py_read_esfm_file, m)?)?;
    m.add_function(wrap_pyfunction!(py_read_sfm_lines, m)?)?;
    m.add_function(wrap_pyfunction!(py_read_sfm_records, m)?)?;
    m.add_function(wrap_pyfunction!(py_escape_characters, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_well_formedness, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_with_lint, m)?)?;

    m.add_class::<PyDiscoveryFlags>()?;
    m.add_class::<PyCheckOptions>()?;

    // Extra types
    m.add_class::<PyInternalBibleExtra>()?;
    m.add_class::<PyInternalBibleExtraList>()?;
    m.add_class::<PyInternalBibleExtraListIter>()?;

    // Discovery types
    m.add_class::<PyBookDiscoveryResults>()?;
    m.add_class::<PyAggregateDiscoveryResults>()?;
    m.add_class::<PyBibleDiscoveryResults>()?;
    m.add_class::<PyDiscoveryOptions>()?;
    m.add_class::<PyDiscoveryResults>()?;

    // CV index types
    m.add_class::<PyChapterVerse>()?;
    m.add_class::<PyInternalBibleEntry>()?;
    m.add_class::<PyInternalBibleEntryList>()?;
    m.add_class::<PyInternalBibleEntryListIter>()?;
    m.add_class::<PyCVIndexEntry>()?;
    m.add_class::<PyInternalBibleBookCVIndex>()?;
    m.add_class::<PyCVIndexIter>()?;

    // Section index types
    m.add_class::<PySectionIndexEntry>()?;
    m.add_class::<PyInternalBibleBookSectionIndex>()?;
    m.add_class::<PySectionIndexIter>()?;

    // Processing types
    m.add_class::<PyObjectType>()?;
    m.add_class::<PyProcessLinesOptions>()?;

    m.add_class::<PyMlWriter>()?;
    m.add_class::<PyMlOutputType>()?;
    m.add_class::<PyHumanReadable>()?;
    m.add_class::<PySectionName>()?;

    Ok(())
}

/// Extract leading integer from a string (e.g., "17a" -> 17).
#[pyfunction]
#[pyo3(name = "getSmallLeadingInt")]
fn get_small_leading_int(s: &str) -> PyResult<i16> {
    parsing::get_small_leading_int(s).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Extract leading integer from a string (e.g., "17a" -> 17).
#[pyfunction]
#[pyo3(name = "getPositiveLeadingInt")]
fn get_positive_leading_int(s: &str) -> PyResult<u32> {
    parsing::get_positive_leading_int(s).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

use bos_internals::{DEBUG, STRICT_CHECKING, VERBOSITY};
use std::sync::atomic::Ordering;

#[pyfunction]
pub fn set_rust_verbosity(level: u8) {
    VERBOSITY.store(level, Ordering::Relaxed); // Store the level (0-4) using Relaxed ordering (fastest)
    let filter = match level {
        0 => log::LevelFilter::Off,
        1 => log::LevelFilter::Warn,
        2 => log::LevelFilter::Info,
        3 => log::LevelFilter::Debug,
        4 => log::LevelFilter::Trace,
        _ => log::LevelFilter::Trace,
    };
    log::set_max_level(filter);
    // Forward Rust logs to Python logging
    let _ = pyo3_log::try_init();
}

#[pyfunction]
pub fn set_rust_debug(value: bool) {
    DEBUG.store(value, Ordering::Relaxed);
}

#[pyfunction]
pub fn set_rust_strict_checking(value: bool) {
    STRICT_CHECKING.store(value, Ordering::Relaxed);
}

/// Parse word attributes from a USFM3 `\w` field.
/// Returns a dict for backward compatibility with the old Python implementation.
#[pyfunction]
#[pyo3(name = "parseWordAttributes")]
#[pyo3(signature = (*args, **_kwargs))]
fn py_parse_word_attributes<'py>(
    py: Python<'py>,
    args: &Bound<'py, pyo3::types::PyTuple>,
    _kwargs: Option<&Bound<'py, pyo3::types::PyDict>>,
) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
    // The old Python version took: (workName, BBB, C, V, wwField, errorList=None)
    // We only care about wwField (the 5th argument or the only argument if called with just the string)
    let ww_field = if args.len() == 1 {
        args.get_item(0)?.extract::<String>()?
    } else if args.len() >= 5 {
        args.get_item(4)?.extract::<String>()?
    } else {
        return Err(pyo3::exceptions::PyTypeError::new_err(
            "parseWordAttributes expects at least 1 argument (wwField) or 5 (workName, BBB, C, V, wwField)",
        ));
    };

    let result = parsing::parse_word_attributes(&ww_field)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("word", result.word)?;
    if let Some(lemma) = result.lemma {
        dict.set_item("lemma", lemma)?;
    }
    if let Some(strong) = result.strong {
        dict.set_item("strong", strong)?;
    }
    for (k, v) in result.extra {
        dict.set_item(k, v)?;
    }
    Ok(dict)
}
