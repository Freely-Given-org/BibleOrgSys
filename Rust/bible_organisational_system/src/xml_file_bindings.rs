//! Python bindings for XML handling.

use pyo3::prelude::*;
use pyo3::types::PyTuple;
use pyo3::IntoPyObjectExt;
use bos_internals::xml_file;

/// Check if XML is well-formed.
#[pyfunction]
#[pyo3(name = "validateWellFormedness")]
pub fn py_validate_well_formedness(path: &str) -> PyResult<bool> {
    match xml_file::validate_well_formedness(path) {
        Ok(_) => Ok(true),
        Err(e) => Err(pyo3::exceptions::PyValueError::new_err(e)),
    }
}

/// Validate XML with xmllint.
#[pyfunction]
#[pyo3(name = "validateWithLint")]
pub fn py_validate_with_lint<'py>(
    py: Python<'py>,
    xml_path: &str,
    schema_path: Option<&str>,
) -> PyResult<Bound<'py, PyTuple>> {
    let (success, stdout, stderr, code) = xml_file::validate_with_xmllint(xml_path, schema_path);
    
    let success_py = match success {
        Some(s) => s.into_py_any(py)?,
        None => py.None(),
    };
    let stdout_py = match stdout {
        Some(s) => s.into_py_any(py)?,
        None => py.None(),
    };
    let stderr_py = match stderr {
        Some(s) => s.into_py_any(py)?,
        None => py.None(),
    };
    let code_py = match code {
        Some(c) => c.into_py_any(py)?,
        None => py.None(),
    };

    Ok(PyTuple::new(py, vec![success_py, stdout_py, stderr_py, code_py])?)
}
