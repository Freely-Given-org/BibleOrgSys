//! Python bindings for Bible validation and checking.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use bos_internals::checking;
use crate::cv_index_bindings::PyInternalBibleEntryList;

#[pyclass(name = "DiscoveryFlags")]
#[derive(Clone)]
pub struct PyDiscoveryFlags {
    pub inner: checking::DiscoveryFlags,
}

#[pymethods]
impl PyDiscoveryFlags {
    #[new]
    #[pyo3(signature = (partly_done=false, percentage_progress=0.0, seems_finished=false, have_main_headings=false, have_introductory_text=false))]
    fn new(
        partly_done: bool,
        percentage_progress: f32,
        seems_finished: bool,
        have_main_headings: bool,
        have_introductory_text: bool,
    ) -> Self {
        Self {
            inner: checking::DiscoveryFlags {
                partly_done,
                percentage_progress,
                seems_finished,
                have_main_headings,
                have_introductory_text,
            },
        }
    }
}

#[pyclass(name = "CheckOptions")]
#[derive(Clone)]
pub struct PyCheckOptions {
    pub inner: checking::CheckOptions,
}

#[pymethods]
impl PyCheckOptions {
    #[new]
    fn new() -> Self {
        Self {
            inner: checking::CheckOptions::default(),
        }
    }
}

#[pyfunction]
#[pyo3(name = "validateMarkers")]
pub fn py_validate_processed_markers<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    book_code: &str,
    work_name: &str,
    strict_checking: bool,
) -> PyResult<Bound<'py, PyDict>> {
    let results = checking::validate_processed_markers(&entries.inner, book_code, work_name, strict_checking);
    
    let dict = PyDict::new(py);
    dict.set_item("validation_errors", results.validation_errors)?;
    
    let priority_errors = PyList::empty(py);
    for (p, msg, (b, c, v)) in results.priority_errors {
        let error_tuple = (p, msg, (b, c, v));
        priority_errors.append(error_tuple)?;
    }
    dict.set_item("priority_errors", priority_errors)?;
    
    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "getVersification")]
pub fn py_get_versification<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    book_code: &str,
    work_name: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let info = checking::get_versification(&entries.inner, book_code, work_name);
    
    let result = PyList::empty(py);
    result.append(info.versification)?;
    result.append(info.omitted_verses)?;
    result.append(info.combined_verses)?;
    result.append(info.reordered_verses)?;
    
    let dict = PyDict::new(py);
    dict.set_item("versification", result)?;
    dict.set_item("errors", info.versification_errors)?;
    
    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "getAddedUnits")]
pub fn py_get_added_units<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    book_code: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let info = checking::get_added_units(&entries.inner, book_code);
    
    let result = PyList::empty(py);
    result.append(info.paragraph_references)?;
    result.append(info.q_references)?;
    result.append(info.section_headings)?;
    result.append(info.section_references)?;
    result.append(info.words_of_jesus)?;
    
    let dict = PyDict::new(py);
    dict.set_item("added_units", result)?;
    dict.set_item("errors", info.added_unit_errors)?;
    
    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "checkBook")]
pub fn py_check_book<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    book_code: &str,
    work_name: &str,
    options: &PyCheckOptions,
    discovery: &PyDiscoveryFlags,
) -> PyResult<Bound<'py, PyDict>> {
    let results = checking::check_book(&entries.inner, book_code, work_name, &options.inner, &discovery.inner);
    
    let dict = PyDict::new(py);
    dict.set_item("newline_marker_errors", results.newline_marker_errors)?;
    dict.set_item("internal_marker_errors", results.internal_marker_errors)?;
    dict.set_item("speech_mark_errors", results.speech_mark_errors)?;
    dict.set_item("word_errors", results.word_errors)?;
    dict.set_item("heading_errors", results.heading_errors)?;
    dict.set_item("introduction_errors", results.introduction_errors)?;
    dict.set_item("note_marker_errors", results.note_marker_errors)?;
    dict.set_item("validation_errors", results.validation_errors)?;
    
    dict.set_item("newline_marker_counts", results.newline_marker_counts)?;
    dict.set_item("internal_marker_counts", results.internal_marker_counts)?;
    dict.set_item("note_marker_counts", results.note_marker_counts)?;
    dict.set_item("functional_counts", results.functional_counts)?;
    
    let priority_errors = PyList::empty(py);
    for (p, msg, (b, c, v)) in results.priority_errors {
        let error_tuple = (p, msg, (b, c, v));
        priority_errors.append(error_tuple)?;
    }
    dict.set_item("priority_errors", priority_errors)?;
    
    Ok(dict)
}
