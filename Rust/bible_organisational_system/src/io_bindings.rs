//! Python bindings for SFM/USFM/ESFM I/O.

use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple};
use pyo3::IntoPyObjectExt;
use bos_internals::io;

/// Python binding for split_usfm_marker_from_text.
#[pyfunction]
#[pyo3(name = "splitUSFMMarkerFromText")]
pub fn py_split_usfm_marker_from_text(py: Python<'_>, line: &str) -> PyResult<Py<PyAny>> {
    let (marker, text) = io::split_usfm_marker_from_text(line);
    let marker_py = match marker {
        Some(m) => m.as_str().into_bound_py_any(py)?,
        None => py.None().into_bound_py_any(py)?,
    };
    let text_py = text.as_str().into_bound_py_any(py)?;
    Ok(PyTuple::new(py, vec![marker_py, text_py])?.into_any().unbind())
}

/// Python binding for USFMFile.read
#[pyfunction]
#[pyo3(name = "readUSFMFile")]
pub fn py_read_usfm_file(py: Python<'_>, path: &str, ignore_sfms: Vec<String>) -> PyResult<Py<PyAny>> {
    let ignore_refs: Vec<&str> = ignore_sfms.iter().map(|s| s.as_str()).collect();
    let lines = io::read_usfm_file(path, &ignore_refs)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    let result = PyList::empty(py);
    for line in lines {
        let tuple = PyTuple::new(py, vec![line.marker.as_str(), line.text.as_str()])?;
        result.append(tuple)?;
    }
    Ok(result.into_any().unbind())
}

/// Python binding for ESFMFile.read
#[pyfunction]
#[pyo3(name = "readESFMFile")]
pub fn py_read_esfm_file(py: Python<'_>, path: &str, ignore_sfms: Vec<String>) -> PyResult<Py<PyAny>> {
    let ignore_refs: Vec<&str> = ignore_sfms.iter().map(|s| s.as_str()).collect();
    let lines = io::read_esfm_file(path, &ignore_refs)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    let result = PyList::empty(py);
    for line in lines {
        let tuple = PyTuple::new(py, vec![line.marker.as_str(), line.text.as_str()])?;
        result.append(tuple)?;
    }
    Ok(result.into_any().unbind())
}

/// Python binding for SFMLines.read
#[pyfunction]
#[pyo3(name = "readSFMLines")]
pub fn py_read_sfm_lines(py: Python<'_>, path: &str, ignore_sfms: Vec<String>) -> PyResult<Py<PyAny>> {
    let ignore_refs: Vec<&str> = ignore_sfms.iter().map(|s| s.as_str()).collect();
    let lines = io::read_sfm_lines(path, &ignore_refs)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    let result = PyList::empty(py);
    for line in lines {
        let tuple = PyTuple::new(py, vec![line.marker.as_str(), line.text.as_str()])?;
        result.append(tuple)?;
    }
    Ok(result.into_any().unbind())
}

/// Python binding for SFMRecords.read
#[pyfunction]
#[pyo3(name = "readSFMRecords")]
pub fn py_read_sfm_records(
    py: Python<'_>,
    path: &str,
    key: Option<String>,
    ignore_sfms: Vec<String>,
    ignore_entries: Vec<String>,
    change_pairs: Vec<(String, String)>,
) -> PyResult<Py<PyAny>> {
    let ignore_sfms_refs: Vec<&str> = ignore_sfms.iter().map(|s| s.as_str()).collect();
    let ignore_entries_refs: Vec<&str> = ignore_entries.iter().map(|s| s.as_str()).collect();
    
    let records = io::read_sfm_records(
        path,
        key.as_deref(),
        &ignore_sfms_refs,
        &ignore_entries_refs,
        &change_pairs,
    )
    .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    let result = PyList::empty(py);
    for record in records {
        let py_record = PyList::empty(py);
        for line in record {
            let tuple = PyTuple::new(py, vec![line.marker.as_str(), line.text.as_str()])?;
            py_record.append(tuple)?;
        }
        result.append(py_record)?;
    }
    Ok(result.into_any().unbind())
}
