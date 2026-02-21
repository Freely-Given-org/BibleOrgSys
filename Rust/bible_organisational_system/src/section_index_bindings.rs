//! Python bindings for InternalBibleBookSectionIndexEntry.
//!
//! Provides a backward-compatible API matching the Python class,
//! including camelCase method names and index-based field access.

use pyo3::exceptions::PyIndexError;
use pyo3::prelude::*;

use bos_internals::SectionIndexEntry;

// ============================================================================
// PySectionIndexEntry
// ============================================================================

/// A section index entry for a Bible book.
///
/// Each entry represents a section boundary and contains:
/// - endC, endV: End chapter and verse (inclusive)
/// - startIx, endIx: Start and end entry indices
/// - reasonMarker: The marker that started this section (e.g., "s1", "c")
/// - sectionName: The section heading text
/// - contextList: Context markers active at this point
#[pyclass(name = "InternalBibleBookSectionIndexEntry")]
#[derive(Clone)]
pub struct PySectionIndexEntry {
    pub(crate) inner: SectionIndexEntry,
}

#[pymethods]
#[allow(non_snake_case)]
impl PySectionIndexEntry {
    /// Create a new section index entry.
    ///
    /// Args:
    ///     endC: End chapter number string
    ///     endV: End verse number string
    ///     startIx: Start entry index
    ///     endIx: End entry index (inclusive)
    ///     reasonMarker: Marker that started this section
    ///     sectionName: Section heading text
    ///     contextList: Optional list of context markers
    #[new]
    #[pyo3(signature = (end_c, end_v, start_ix, end_ix, reason_marker, section_name, context_list=None))]
    fn new(
        end_c: &str,
        end_v: &str,
        start_ix: u16,
        end_ix: u16,
        reason_marker: &str,
        section_name: &str,
        context_list: Option<Vec<String>>,
    ) -> Self {
        let ctx = context_list
            .unwrap_or_default()
            .into_iter()
            .map(|s| s.into())
            .collect();
        Self {
            inner: SectionIndexEntry::new(
                end_c,
                end_v,
                start_ix,
                end_ix,
                reason_marker,
                section_name,
                ctx,
            ),
        }
    }

    // --- Properties (matching Python attribute access) ---

    #[getter]
    fn endC(&self) -> &str {
        self.inner.end_chapter_num_str()
    }

    #[getter]
    fn endV(&self) -> &str {
        self.inner.end_verse_num_str()
    }

    #[getter]
    fn startIx(&self) -> usize {
        self.inner.start_index()
    }

    #[getter]
    fn endIx(&self) -> usize {
        self.inner.end_index()
    }

    #[getter]
    fn reasonMarker(&self) -> &str {
        self.inner.reason_marker()
    }

    #[getter]
    fn sectionName(&self) -> &str {
        self.inner.section_name()
    }

    #[getter]
    fn contextList(&self) -> Vec<String> {
        self.inner
            .context()
            .iter()
            .map(|s| s.to_string())
            .collect()
    }

    // --- camelCase getter methods (Python backward compat) ---

    /// Get end chapter and verse as (str, str) tuple.
    fn getEndCV(&self) -> (String, String) {
        (
            self.inner.end_chapter_num_str().to_string(),
            self.inner.end_verse_num_str().to_string(),
        )
    }

    /// Get start entry index.
    fn getStartIndex(&self) -> usize {
        self.inner.start_index()
    }

    /// Get end entry index (inclusive).
    fn getEndIndex(&self) -> usize {
        self.inner.end_index()
    }

    /// Get entry count (endIx + 1 - startIx).
    fn getEntryCount(&self) -> usize {
        self.inner.entry_count()
    }

    /// Get context markers list.
    fn getContextList(&self) -> Vec<String> {
        self.inner
            .context()
            .iter()
            .map(|s| s.to_string())
            .collect()
    }

    /// Get section name and reason marker as (str, str) tuple.
    fn getSectionNameReason(&self) -> (String, String) {
        let (name, reason) = self.inner.section_name_reason();
        (name.to_string(), reason.to_string())
    }

    // --- Standard Python methods ---

    fn __len__(&self) -> usize {
        7
    }

    fn __getitem__(&self, key_index: isize) -> PyResult<Py<PyAny>> {
        Python::attach(|py| match key_index {
            0 => Ok(self
                .inner
                .end_chapter_num_str()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            1 => Ok(self
                .inner
                .end_verse_num_str()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            2 => Ok(self
                .inner
                .start_index()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            3 => Ok(self
                .inner
                .end_index()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            4 => Ok(self
                .inner
                .reason_marker()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            5 => Ok(self
                .inner
                .section_name()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            6 => {
                let ctx: Vec<String> = self
                    .inner
                    .context()
                    .iter()
                    .map(|s| s.to_string())
                    .collect();
                Ok(ctx.into_pyobject(py)?.into_any().unbind())
            }
            _ => Err(PyIndexError::new_err("Index out of range")),
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "InternalBibleBookSectionIndexEntry object: (inclusive) endCV={}:{} ix={}\u{2013}{} (cnt={}) {}='{}'{}",
            self.inner.end_chapter_num_str(),
            self.inner.end_verse_num_str(),
            self.inner.start_index(),
            self.inner.end_index(),
            self.inner.entry_count(),
            self.inner.reason_marker(),
            self.inner.section_name(),
            if self.inner.context().is_empty() {
                String::new()
            } else {
                let ctx: Vec<String> = self
                    .inner
                    .context()
                    .iter()
                    .map(|s| s.to_string())
                    .collect();
                format!(" ctxt={:?}", ctx)
            }
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}

impl From<SectionIndexEntry> for PySectionIndexEntry {
    fn from(inner: SectionIndexEntry) -> Self {
        Self { inner }
    }
}

impl From<&SectionIndexEntry> for PySectionIndexEntry {
    fn from(inner: &SectionIndexEntry) -> Self {
        Self {
            inner: inner.clone(),
        }
    }
}

/// Register section index types with the Python module.
pub fn register_section_index_types(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySectionIndexEntry>()?;
    Ok(())
}
