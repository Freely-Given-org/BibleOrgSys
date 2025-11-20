use pyo3::prelude::*;
use crate::internals::internal_bible_index::add_numbers;

#[pymodule]
fn mylib(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add_numbers_py, m)?)?;
    Ok(())
}

#[pyfunction]
fn add_numbers_py(a: i32, b: i32) -> i32 {
    add_numbers(a, b)
}
