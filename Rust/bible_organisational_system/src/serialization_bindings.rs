//! Python bindings for fast Bible serialization.

use pyo3::prelude::*;
use pyo3::types::PyDict;
use bos_internals::serialization::{save_bos_bible, load_bos_bible};
use crate::cv_index_bindings::{PyInternalBibleBookCVIndex, PyInternalBibleEntryList};
use crate::section_index_bindings::PyInternalBibleBookSectionIndex;
use std::path::Path;

#[pyfunction]
#[pyo3(name = "saveBookFast")]
pub fn py_save_book_fast(
    _py: Python,
    path: &str,
    work_name: &str,
    book_code: &str,
    entries: &PyInternalBibleEntryList,
    cv_index: Option<&PyInternalBibleBookCVIndex>,
    section_index: Option<&PyInternalBibleBookSectionIndex>,
) -> PyResult<()> {
    save_bos_bible(
        Path::new(path),
        work_name,
        book_code,
        entries.inner.clone(),
        cv_index.map(|idx| &idx.inner),
        section_index.map(|idx| &idx.inner),
    ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
#[pyo3(name = "loadBookFast")]
pub fn py_load_book_fast<'py>(
    py: Python<'py>,
    path: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let file_data = load_bos_bible(Path::new(path))
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

    let dict = PyDict::new(py);
    
    // entries
    let py_entries = PyInternalBibleEntryList { inner: file_data.entries.clone() };
    dict.set_item("entries", Bound::new(py, py_entries)?)?;

    // cv_index
    if let Some(idx_data) = file_data.cv_index_data {
        let cv_index = bos_internals::indexes::cv_index::InternalBibleBookCVIndex::from_serialized(
            file_data.work_name.clone(),
            file_data.bos_book_code.clone(),
            idx_data,
            file_data.entries.clone(),
        );
        dict.set_item("cv_index", Bound::new(py, PyInternalBibleBookCVIndex { inner: cv_index })?)?;
    }

    // section_index
    if let Some(idx_data) = file_data.section_index_data {
        let section_index = bos_internals::indexes::section_index::InternalBibleBookSectionIndex::from_serialized(
            file_data.work_name.clone(),
            file_data.bos_book_code.clone(),
            idx_data,
            file_data.entries.clone(),
        );
        dict.set_item("section_index", Bound::new(py, PyInternalBibleBookSectionIndex { inner: section_index })?)?;
    }

    Ok(dict)
}
