//! Python bindings for OSIS XML parsing.

use pyo3::prelude::*;
use pyo3::types::PyDict;
use bos_internals::osis::parse_osis;
use std::path::Path;

#[pyfunction]
#[pyo3(name = "parseOsis")]
pub fn py_parse_osis<'py>(
    py: Python<'py>,
    path: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let results = parse_osis(Path::new(path))
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

    let dict = PyDict::new(py);
    
    // Metadata
    let metadata_dict = PyDict::new(py);
    for (k, v) in results.metadata {
        metadata_dict.set_item(k, v)?;
    }
    dict.set_item("metadata", metadata_dict)?;

    // Books
    let books_dict = PyDict::new(py);
    for (bbb, lines) in results.books {
        books_dict.set_item(bbb, lines)?;
    }
    dict.set_item("books", books_dict)?;

    Ok(dict)
}
