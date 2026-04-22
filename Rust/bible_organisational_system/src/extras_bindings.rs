//! Python bindings for InternalBibleExtra and InternalBibleExtraList.
//!
//! These provide backward-compatible APIs matching the Python classes,
//! including camelCase method names and index-based field access.

use pyo3::exceptions::{PyIndexError, PyValueError};
use pyo3::prelude::*;

use bos_internals::{ExtraType, InternalBibleExtra, InternalBibleExtraList};

/// An "extra" element extracted from Bible text (footnote, cross-ref, etc.).
///
/// Each extra contains:
/// - myType: The type string ('fn', 'en', 'xr', 'fig', 'str', 'sem', 'ww', 'vp')
/// - index: Position in the adjusted text where this was extracted
/// - noteText: Full text with USFM markers
/// - cleanNoteText: Plain text without markers
#[pyclass(name = "InternalBibleExtra", module = "bible_organisational_system", from_py_object)]
#[derive(Clone)]
pub struct PyInternalBibleExtra {
    pub(crate) inner: InternalBibleExtra,
}

#[pymethods]
#[allow(non_snake_case)]
impl PyInternalBibleExtra {
    /// Create a new InternalBibleExtra.
    ///
    /// Args:
    ///     myType: Type string ('fn', 'en', 'xr', 'fig', 'str', 'sem', 'ww', 'vp')
    ///     indexToAdjText: Position in adjusted text
    ///     noteText: Full note text with USFM markers
    ///     cleanNoteText: Clean note text without markers
    ///     location: Location string for error messages (not stored)
    #[new]
    #[pyo3(signature = (my_type, index_to_adj_text, note_text, clean_note_text, location=None))]
    fn new(
        my_type: &str,
        index_to_adj_text: usize,
        note_text: &str,
        clean_note_text: &str,
        location: Option<&str>,
    ) -> PyResult<Self> {
        let _ = location; // Not stored, matches Python API
        let extra_type = ExtraType::from_type_str(my_type)
            .ok_or_else(|| PyValueError::new_err(format!("Unknown extra type: {}", my_type)))?;
        let inner = InternalBibleExtra::new(extra_type, index_to_adj_text, note_text, clean_note_text)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(Self { inner })
    }

    // --- Python-compatible camelCase properties (matching Python attribute access) ---

    /// Get the type string.
    #[getter(myType)]
    fn my_type(&self) -> &str {
        self.inner.extra_type().type_str()
    }

    /// Get the index into adjusted text.
    #[getter]
    fn index(&self) -> usize {
        self.inner.index()
    }

    /// Get the full note text.
    #[getter(noteText)]
    fn note_text(&self) -> &str {
        self.inner.note_text()
    }

    /// Get the clean note text.
    #[getter(cleanNoteText)]
    fn clean_note_text(&self) -> &str {
        self.inner.clean_note_text()
    }

    // --- Python-compatible camelCase getter methods ---

    /// Get the type string (Python compat).
    fn getType(&self) -> &str {
        self.inner.extra_type().type_str()
    }

    /// Get the index (Python compat).
    fn getIndex(&self) -> usize {
        self.inner.index()
    }

    /// Get the note text (Python compat).
    fn getText(&self) -> &str {
        self.inner.note_text()
    }

    /// Get the clean note text (Python compat).
    fn getCleanText(&self) -> &str {
        self.inner.clean_note_text()
    }

    // --- Standard Python methods ---

    fn __len__(&self) -> usize {
        4
    }

    fn __getitem__(&self, key_index: isize) -> PyResult<Py<PyAny>> {
        Python::attach(|py| match key_index {
            0 => Ok(self
                .inner
                .extra_type()
                .type_str()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            1 => Ok(self.inner.index().into_pyobject(py)?.into_any().unbind()),
            2 => Ok(self.inner.note_text().into_pyobject(py)?.into_any().unbind()),
            3 => Ok(self.inner.clean_note_text().into_pyobject(py)?.into_any().unbind()),
            _ => Err(PyIndexError::new_err("Index out of range")),
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "InternalBibleExtra object: {} @ {} = {:?}",
            self.inner.extra_type().type_str(),
            self.inner.index(),
            self.inner.note_text()
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }

    fn __eq__(&self, other: &PyInternalBibleExtra) -> bool {
        self.inner == other.inner
    }

    fn __ne__(&self, other: &PyInternalBibleExtra) -> bool {
        self.inner != other.inner
    }
}

impl From<InternalBibleExtra> for PyInternalBibleExtra {
    fn from(inner: InternalBibleExtra) -> Self {
        Self { inner }
    }
}

impl From<&InternalBibleExtra> for PyInternalBibleExtra {
    fn from(inner: &InternalBibleExtra) -> Self {
        Self { inner: inner.clone() }
    }
}

/// A list of InternalBibleExtra objects.
#[pyclass(
    name = "InternalBibleExtraList",
    module = "bible_organisational_system",
    from_py_object
)]
#[derive(Debug, Clone)]
pub struct PyInternalBibleExtraList {
    pub(crate) inner: InternalBibleExtraList,
}

#[pymethods]
#[allow(non_snake_case)]
impl PyInternalBibleExtraList {
    /// Create a new InternalBibleExtraList, optionally from existing data.
    #[new]
    #[pyo3(signature = (initial_data=None))]
    fn new(initial_data: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let mut inner = InternalBibleExtraList::new();
        if let Some(data) = initial_data {
            let iter = data.try_iter()?;
            for item in iter {
                let item = item?;
                let extra: PyRef<PyInternalBibleExtra> = item.extract()?;
                inner.push(extra.inner.clone());
            }
        }
        Ok(Self { inner })
    }

    fn __len__(&self) -> usize {
        self.inner.len()
    }

    fn __getitem__(&self, key_index: isize) -> PyResult<PyInternalBibleExtra> {
        let len = self.inner.len() as isize;
        let idx = if key_index < 0 { len + key_index } else { key_index };
        if idx < 0 || idx >= len {
            return Err(PyIndexError::new_err(format!("Index {} out of range", key_index)));
        }
        Ok(PyInternalBibleExtra::from(&self.inner[idx as usize]))
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyInternalBibleExtraListIter {
        PyInternalBibleExtraListIter {
            data: slf.inner.clone(),
            index: 0,
        }
    }

    fn __bool__(&self) -> bool {
        !self.inner.is_empty()
    }

    /// Add an extra to the list.
    fn append(&mut self, new_extra: &PyInternalBibleExtra) {
        self.inner.push(new_extra.inner.clone());
    }

    /// Remove and return the last extra.
    fn pop(&mut self) -> Option<PyInternalBibleExtra> {
        self.inner.pop().map(PyInternalBibleExtra::from)
    }

    /// Extend with another list.
    fn extend(&mut self, other: &PyInternalBibleExtraList) {
        self.inner.extend(&other.inner);
    }

    /// Check for extras at a specific string index.
    ///
    /// Returns None if no extras found, a single extra if one found,
    /// or a list if multiple found.
    fn checkForIndex(&self, string_index: usize) -> PyResult<Py<PyAny>> {
        let matches: Vec<&InternalBibleExtra> = self.inner.iter().filter(|e| e.index() == string_index).collect();

        Python::attach(|py| match matches.len() {
            0 => Ok(py.None()),
            1 => {
                let extra = PyInternalBibleExtra::from(matches[0]);
                Ok(extra.into_pyobject(py)?.into_any().unbind())
            }
            _ => {
                let list: Vec<PyInternalBibleExtra> = matches.iter().map(|e| PyInternalBibleExtra::from(*e)).collect();
                Ok(list.into_pyobject(py)?.into_any().unbind())
            }
        })
    }

    /// Get a short summary string.
    fn summary(&self) -> String {
        self.inner.summary()
    }

    /// Get a full summary string with note text.
    fn fullSummary(&self) -> String {
        self.inner.full_summary()
    }

    fn __repr__(&self) -> String {
        format!("InternalBibleExtraList({} entries)", self.inner.len())
    }

    fn __str__(&self) -> String {
        format!("{}", self.inner)
    }

    fn __eq__(&self, other: &PyInternalBibleExtraList) -> bool {
        self.inner == other.inner
    }
}

impl From<InternalBibleExtraList> for PyInternalBibleExtraList {
    fn from(inner: InternalBibleExtraList) -> Self {
        Self { inner }
    }
}

/// Iterator for PyInternalBibleExtraList.
#[pyclass]
pub struct PyInternalBibleExtraListIter {
    data: InternalBibleExtraList,
    index: usize,
}

#[pymethods]
impl PyInternalBibleExtraListIter {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(&mut self) -> Option<PyInternalBibleExtra> {
        if self.index < self.data.len() {
            let extra = PyInternalBibleExtra::from(&self.data[self.index]);
            self.index += 1;
            Some(extra)
        } else {
            None
        }
    }
}
