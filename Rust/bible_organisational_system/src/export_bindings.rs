//! Python bindings for Bible export pipelines.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PySet};
use std::collections::HashMap;
use std::path::Path;
use crate::cv_index_bindings::PyInternalBibleEntryList;
use bos_internals::export::{export_to_text, export_to_html5};

/// Python-accessible wrapper for `export_to_text`.
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
    bible_name: &str,
    book_order: Vec<String>,
    book_names_dict: &Bound<'py, PyDict>,
    filename_dict_py: &Bound<'py, PyDict>,
    control_dict_py: &Bound<'py, PyDict>,
    program_name: &str,
    program_version: &str,
    today_str: &str,
    xref_callback: Option<Py<PyAny>>,
) -> PyResult<(Bound<'py, PySet>, Bound<'py, PySet>)> {
    let mut books = HashMap::new();
    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let processed_lines_py = value.getattr("_processedLines")?;
        let entry_list_ref: PyRef<PyInternalBibleEntryList> = processed_lines_py.extract()?;
        books.insert(bbb, entry_list_ref.inner.clone());
    }

    let mut book_names = HashMap::new();
    for (key, value) in book_names_dict.iter() {
        let bbb: String = key.extract()?;
        let name: String = value.extract()?;
        book_names.insert(bbb, name);
    }

    let mut filename_dict = HashMap::new();
    for (key, value) in filename_dict_py.iter() {
        let bbb: String = key.extract()?;
        let filename: String = value.extract()?;
        filename_dict.insert(bbb, filename);
    }

    let mut control_dict = HashMap::new();
    for (key, value) in control_dict_py.iter() {
        let opt_name: String = key.extract()?;
        let opt_val: String = value.extract()?;
        control_dict.insert(opt_name, opt_val);
    }

    let output_path = Path::new(output_path_str);
    
    let xref_cb: Option<Box<dyn Fn(&str) -> String + Sync>> = xref_callback.map(|cb| {
        let box_fn: Box<dyn Fn(&str) -> String + Sync> = Box::new(move |text: &str| -> String {
            Python::attach(|py| {
                if let Ok(res) = cb.call1(py, (text,)) {
                    if let Ok(res_str) = res.extract::<String>(py) {
                        return res_str;
                    }
                }
                text.to_string()
            })
        });
        box_fn
    });
    let xref_cb_ref = xref_cb.as_ref().map(|cb| &**cb as &(dyn Fn(&str) -> String + Sync));

    let (ignored, unhandled) = export_to_html5(
        &books,
        output_path,
        bible_name,
        &book_order,
        &book_names,
        &filename_dict,
        &control_dict,
        program_name,
        program_version,
        today_str,
        xref_cb_ref,
    )
    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

    let py_ignored = PySet::new(py, &ignored)?;
    let py_unhandled = PySet::new(py, &unhandled)?;
    
    Ok((py_ignored, py_unhandled))
}
