//! Python bindings for Bible export pipelines.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PySet};
use std::collections::HashMap;
use std::path::Path;
use crate::cv_index_bindings::PyInternalBibleEntryList;
use bos_internals::export::{export_to_text, export_to_html5};

/// Python-accessible wrapper for `export_to_text`.
///
/// Iterates over Python book objects in self.books, extracts their underlying
/// Rust `InternalBibleEntryList` from `_processedLines`, and runs the parallel export engine.
#[pyfunction]
#[pyo3(name = "exportToText")]
pub fn py_export_to_text<'py>(
    py: Python<'py>,
    books_dict: &Bound<'py, PyDict>,
    output_path_str: &str,
    column_width: usize,
) -> PyResult<Bound<'py, PySet>> {
    let mut books = HashMap::new();
    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let processed_lines_py = value.getattr("_processedLines")?;
        let entry_list_ref: PyRef<PyInternalBibleEntryList> = processed_lines_py.extract()?;
        books.insert(bbb, entry_list_ref.inner.clone());
    }

    let output_path = Path::new(output_path_str);
    let ignored_markers = export_to_text(&books, output_path, column_width)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

    let py_set = PySet::new(py, &ignored_markers)?;
    Ok(py_set)
}

/// Python-accessible wrapper for `export_to_html5`.
#[pyfunction]
#[pyo3(name = "exportToHtml5")]
pub fn py_export_to_html5<'py>(
    py: Python<'py>,
    books_dict: &Bound<'py, PyDict>,
    output_path_str: &str,
    column_width: usize,
) -> PyResult<Bound<'py, PySet>> {
    let mut books = HashMap::new();
    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let processed_lines_py = value.getattr("_processedLines")?;
        let entry_list_ref: PyRef<PyInternalBibleEntryList> = processed_lines_py.extract()?;
        books.insert(bbb, entry_list_ref.inner.clone());
    }

    let output_path = Path::new(output_path_str);
    let ignored_markers = export_to_html5(&books, output_path, column_width)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

    let py_set = PySet::new(py, &ignored_markers)?;
    Ok(py_set)
}
