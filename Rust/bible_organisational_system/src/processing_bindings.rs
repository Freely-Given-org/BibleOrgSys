//! Python bindings for processing lines.

use crate::cv_index_bindings::PyInternalBibleEntryList;
use bos_internals::processing::{ObjectType, ProcessLinesOptions, process_lines};
use pyo3::prelude::*;

#[pyclass(name = "ObjectType", module = "bible_organisational_system", from_py_object)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum PyObjectType {
    Usfm2,
    Usfm3,
    Usx,
    Osis,
    Sword,
    Other,
}

impl From<PyObjectType> for ObjectType {
    fn from(obj: PyObjectType) -> Self {
        match obj {
            PyObjectType::Usfm2 => ObjectType::Usfm2,
            PyObjectType::Usfm3 => ObjectType::Usfm3,
            PyObjectType::Usx => ObjectType::Usx,
            PyObjectType::Osis => ObjectType::Osis,
            PyObjectType::Sword => ObjectType::Sword,
            PyObjectType::Other => ObjectType::Other,
        }
    }
}

#[pyclass(name = "ProcessLinesOptions", module = "bible_organisational_system", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyProcessLinesOptions {
    #[pyo3(get, set)]
    pub replace_angle_brackets: bool,
    #[pyo3(get, set)]
    pub replace_straight_double_quotes: bool,
    #[pyo3(get, set)]
    pub strict_checking: bool,
    #[pyo3(get, set)]
    pub object_type: PyObjectType,
}

#[pymethods]
impl PyProcessLinesOptions {
    #[new]
    #[pyo3(signature = (replace_angle_brackets=true, replace_straight_double_quotes=false, strict_checking=false, object_type=PyObjectType::Usfm3))]
    fn new(
        replace_angle_brackets: bool,
        replace_straight_double_quotes: bool,
        strict_checking: bool,
        object_type: PyObjectType,
    ) -> Self {
        Self {
            replace_angle_brackets,
            replace_straight_double_quotes,
            strict_checking,
            object_type,
        }
    }
}

impl From<PyProcessLinesOptions> for ProcessLinesOptions {
    fn from(py_opts: PyProcessLinesOptions) -> Self {
        Self {
            replace_angle_brackets: py_opts.replace_angle_brackets,
            replace_straight_double_quotes: py_opts.replace_straight_double_quotes,
            strict_checking: py_opts.strict_checking,
            object_type: py_opts.object_type.into(),
        }
    }
}

#[pyfunction]
#[pyo3(name = "processLines")]
pub fn py_process_lines(
    raw_lines: Vec<(String, String)>,
    book_code: &str,
    work_name: &str,
    options: PyProcessLinesOptions,
) -> PyInternalBibleEntryList {
    let result = process_lines(raw_lines, book_code, work_name, &options.into());
    PyInternalBibleEntryList { inner: result }
}
