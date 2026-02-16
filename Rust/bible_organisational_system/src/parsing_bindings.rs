//! Python bindings for BibleOrgSys Internals.
//!
//! This module provides PyO3 bindings to expose the Rust internals to Python.

use pyo3::prelude::*;
use bos_internals::parsing;

use crate::cv_index_bindings::register_cv_index_types;
use crate::extra_bindings::register_extra_types;

/// Python module for BibleOrgSys internals.
#[pymodule]
fn bible_organisational_system(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_leading_int, m)?)?;
    m.add_function(wrap_pyfunction!(parse_word_attributes, m)?)?;

    // Register types
    register_extra_types(m)?;
    register_cv_index_types(m)?;

    Ok(())
}

/// Extract leading integer from a string (e.g., "17a" -> 17).
#[pyfunction]
#[pyo3(name = "getLeadingInt")]
fn get_leading_int(s: &str) -> PyResult<i16> {
    parsing::get_leading_int(s).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Parse word attributes from a USFM3 \w field.
#[pyfunction]
fn parse_word_attributes(word_attribute_string: &str) -> PyResult<std::collections::HashMap<String, String>> {
    let attrs = bos_internals::parsing::parse_word_attributes(word_attribute_string)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

    let mut result = std::collections::HashMap::new();
    result.insert("word".to_string(), attrs.word);
    if let Some(lemma) = attrs.lemma {
        result.insert("lemma".to_string(), lemma);
    }
    if let Some(strong) = attrs.strong {
        result.insert("strong".to_string(), strong);
    }
    for (k, v) in attrs.extra {
        result.insert(k, v);
    }
    Ok(result)
}
