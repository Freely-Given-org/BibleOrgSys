use pyo3::prelude::*;

#[pymodule]
fn mylib(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add_numbers_py, m)?)?;
    Ok(())
}

#[pyfunction]
fn add_numbers_py(a: i32, b: i32) -> i32 {
    a + b
}
