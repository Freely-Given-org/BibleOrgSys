//! Python bindings for BibleOrgSys Internals.
//!
//! This module provides PyO3 bindings to expose the Rust internals to Python.

use bos_internals::parsing;
use pyo3::prelude::*;

use crate::cv_index_bindings::{
    PyChapterVerse, PyCVIndexEntry, PyCVIndexIter, PyInternalBibleBookCVIndex,
    PyInternalBibleEntry, PyInternalBibleEntryList, PyInternalBibleEntryListIter,
};
use crate::discovery_bindings::{
    py_discover_bible, py_discover_book, PyAggregateDiscoveryResults, PyBibleDiscoveryResults,
    PyBookDiscoveryResults,
};
use crate::extras_bindings::{PyInternalBibleExtra, PyInternalBibleExtraList, PyInternalBibleExtraListIter};
use crate::processing_bindings::{PyObjectType, PyProcessLinesOptions, py_process_lines};
use crate::section_index_bindings::{PyInternalBibleBookSectionIndex, PySectionIndexEntry, PySectionIndexIter};

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
    m.add_function(wrap_pyfunction!(py_discover_book, m)?)?;
    m.add_function(wrap_pyfunction!(py_discover_bible, m)?)?;

    // Extra types
    m.add_class::<PyInternalBibleExtra>()?;
    m.add_class::<PyInternalBibleExtraList>()?;
    m.add_class::<PyInternalBibleExtraListIter>()?;

    // Discovery types
    m.add_class::<PyBookDiscoveryResults>()?;
    m.add_class::<PyAggregateDiscoveryResults>()?;
    m.add_class::<PyBibleDiscoveryResults>()?;

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
