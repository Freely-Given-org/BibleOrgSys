//! Python bindings for processing lines.

use pyo3::prelude::*;
use bos_internals::processing::{ObjectType, ProcessLinesOptions, process_lines};
use crate::cv_index_bindings::PyInternalBibleEntryList;
use indexmap::IndexMap;

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
    // rylai emits pyo3 signature defaults verbatim as Python. An enum-path
    // default like `PyObjectType::Usfm3` would produce invalid Python
    // (`PyObjectType :: Usfm3`), so the default is expressed as `None` here
    // and the real default is applied in the body.
    #[new]
    #[pyo3(signature = (replace_angle_brackets=true, replace_straight_double_quotes=false, strict_checking=false, object_type=None))]
    fn new(
        replace_angle_brackets: bool,
        replace_straight_double_quotes: bool,
        strict_checking: bool,
        object_type: Option<PyObjectType>,
    ) -> Self {
        Self {
            replace_angle_brackets,
            replace_straight_double_quotes,
            strict_checking,
            object_type: object_type.unwrap_or(PyObjectType::Usfm3),
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
pub fn py_process_lines<'py>(
    py: Python<'py>,
    raw_lines: Vec<(String, String)>,
    book_code: &str,
    work_name: &str,
    options: PyProcessLinesOptions,
) -> PyResult<Bound<'py, PyInternalBibleEntryList>> {
    let result = process_lines(raw_lines, book_code, work_name, &options.into());
    Bound::new(py, PyInternalBibleEntryList { inner: result })
}

#[pyfunction]
#[pyo3(name = "processBible")]
pub fn py_process_bible<'py>(
    py: Python<'py>,
    books_dict: &Bound<'py, pyo3::types::PyDict>,
    work_name: &str,
    options: PyProcessLinesOptions,
) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
    let mut raw_books = IndexMap::new();
    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let lines: Vec<(String, String)> = value.extract()?;
        raw_books.insert(bbb, lines);
    }

    let results = bos_internals::processing::process_bible(raw_books, work_name, &options.into());

    let dict = pyo3::types::PyDict::new(py);
    for (bbb, entries) in results {
        let py_entries = PyInternalBibleEntryList { inner: entries };
        dict.set_item(bbb, Bound::new(py, py_entries)?)?;
    }
    Ok(dict)
}
