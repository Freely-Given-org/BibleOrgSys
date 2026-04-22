//! Python bindings for section index types.
//!
//! Provides backward-compatible APIs matching the Python classes:
//! - `InternalBibleBookSectionIndexEntry` — a single section entry
//! - `InternalBibleBookSectionIndex` — the section index collection

use pyo3::exceptions::{PyIndexError, PyKeyError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use bos_internals::{ChapterVerse, InternalBibleBookSectionIndex, SectionIndexEntry};

use crate::cv_index_bindings::PyInternalBibleEntryList;
use crate::verbosity_print;

/// A section index entry for a Bible book.
///
/// Each entry represents a section boundary and contains:
/// - endC, endV: End chapter and verse (inclusive)
/// - startIx, endIx: Start and end entry indices
/// - reasonMarker: The marker that started this section (e.g., "s1", "c")
/// - sectionName: The section heading text
/// - contextList: Context markers active at this point
#[pyclass(
    name = "InternalBibleBookSectionIndexEntry",
    module = "bible_organisational_system",
    from_py_object
)]
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
        let ctx = context_list.unwrap_or_default().into_iter().map(|s| s.into()).collect();
        Self {
            inner: SectionIndexEntry::new(end_c, end_v, start_ix, end_ix, reason_marker, section_name, ctx),
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
        self.inner.context().iter().map(|s| s.to_string()).collect()
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
        self.inner.context().iter().map(|s| s.to_string()).collect()
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
            0 => Ok(self.inner.end_chapter_num_str().into_pyobject(py)?.into_any().unbind()),
            1 => Ok(self.inner.end_verse_num_str().into_pyobject(py)?.into_any().unbind()),
            2 => Ok(self.inner.start_index().into_pyobject(py)?.into_any().unbind()),
            3 => Ok(self.inner.end_index().into_pyobject(py)?.into_any().unbind()),
            4 => Ok(self.inner.reason_marker().into_pyobject(py)?.into_any().unbind()),
            5 => Ok(self.inner.section_name().into_pyobject(py)?.into_any().unbind()),
            6 => {
                let ctx: Vec<String> = self.inner.context().iter().map(|s| s.to_string()).collect();
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
                let ctx: Vec<String> = self.inner.context().iter().map(|s| s.to_string()).collect();
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
        Self { inner: inner.clone() }
    }
}

/// Section index for a Bible book.
///
/// Maps section starting points (C:V) to section entries.
/// Accepts (str, str) tuples for keys.
#[pyclass(name = "InternalBibleBookSectionIndex", module = "bible_organisational_system")]
#[derive(rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct PyInternalBibleBookSectionIndex {
    inner: InternalBibleBookSectionIndex,
}

#[pymethods]
#[allow(non_snake_case)]
impl PyInternalBibleBookSectionIndex {
    /// Create a new empty section index.
    #[new]
    fn new(work_name: &str, bos_book_code: &str) -> Self {
        Self {
            inner: InternalBibleBookSectionIndex::new(work_name, bos_book_code),
        }
    }

    // === Properties ===

    #[getter(workName)]
    fn work_name(&self) -> &str {
        self.inner.work_name()
    }

    #[getter(BBB)]
    fn bbb(&self) -> &str {
        self.inner.bos_book_code()
    }

    #[getter(_indexedFlag)]
    fn indexed_flag(&self) -> bool {
        self.inner.is_indexed()
    }

    #[getter(givenBibleEntries)]
    fn given_bible_entries(&self) -> PyInternalBibleEntryList {
        PyInternalBibleEntryList::from(self.inner.entries().clone())
    }

    // === Python protocol methods ===

    fn __len__(&self) -> usize {
        self.inner.len()
    }

    fn __contains__(&self, key: (String, String)) -> bool {
        let cv = ChapterVerse::new(&key.0, &key.1);
        self.inner.contains(&cv)
    }

    fn __getitem__(&self, key: (String, String)) -> PyResult<PySectionIndexEntry> {
        let cv = ChapterVerse::new(&key.0, &key.1);
        self.inner
            .get_index_entry(&cv)
            .map(PySectionIndexEntry::from)
            .ok_or_else(|| PyKeyError::new_err(format!("({:?}, {:?})", key.0, key.1)))
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PySectionIndexIter {
        let keys: Vec<(String, String)> = slf
            .inner
            .iter()
            .map(|(cv, _)| (cv.chapter().to_string(), cv.verse().to_string()))
            .collect();
        PySectionIndexIter { keys, index: 0 }
    }

    fn items(&self) -> Vec<((String, String), PySectionIndexEntry)> {
        self.inner
            .iter()
            .map(|(cv, entry)| {
                (
                    (cv.chapter().to_string(), cv.verse().to_string()),
                    PySectionIndexEntry::from(entry),
                )
            })
            .collect()
    }

    // === camelCase methods (Python backward compat) ===

    /// Build the section index from processed entries.
    fn makeBookSectionIndex(&mut self, entries: &PyInternalBibleEntryList) -> PyResult<()> {
        verbosity_print!(
            2,
            "Building section index for {} {}…",
            self.inner.work_name(),
            self.inner.bos_book_code()
        );
        self.inner
            .build(entries.inner.clone())
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Get entries for a section by (C,V) key.
    fn getSectionEntries(&self, key: (String, String)) -> PyResult<PyInternalBibleEntryList> {
        let cv = ChapterVerse::new(&key.0, &key.1);
        self.inner
            .get_section_entries(&cv)
            .map(PyInternalBibleEntryList::from)
            .map_err(|_| PyKeyError::new_err(format!("({:?}, {:?})", key.0, key.1)))
    }

    /// Get section entries with context markers.
    fn getSectionEntriesWithContext(&self, key: (String, String)) -> PyResult<(PyInternalBibleEntryList, Vec<String>)> {
        let cv = ChapterVerse::new(&key.0, &key.1);
        self.inner
            .get_section_entries_with_context(&cv)
            .map(|(entries, context)| {
                (
                    PyInternalBibleEntryList::from(entries),
                    context.into_iter().map(|s| s.to_string()).collect(),
                )
            })
            .map_err(|_| PyKeyError::new_err(format!("({:?}, {:?})", key.0, key.1)))
    }

    fn __repr__(&self) -> String {
        if self.inner.is_indexed() {
            format!(
                "InternalBibleBookSectionIndex object for {}:\n  {} index entries created from {} data entries",
                self.inner.bos_book_code(),
                self.inner.len(),
                self.inner.entries().len(),
            )
        } else {
            format!(
                "InternalBibleBookSectionIndex object for {}:\n  Index is empty",
                self.inner.bos_book_code(),
            )
        }
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }

    // Pickling support using rkyv zero-copy serialization.
    fn __getstate__(&self, py: Python) -> PyResult<Py<PyAny>> {
        let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(self).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(PyBytes::new(py, &bytes).into())
    }

    fn __setstate__(&mut self, state: &Bound<'_, PyAny>) -> PyResult<()> {
        let bytes = state.extract::<&[u8]>()?;
        *self =
            rkyv::from_bytes::<Self, rkyv::rancor::Error>(bytes).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(())
    }
}

/// Iterator for PyInternalBibleBookSectionIndex, yields (C, V) string tuples.
#[pyclass]
pub struct PySectionIndexIter {
    keys: Vec<(String, String)>,
    index: usize,
}

#[pymethods]
impl PySectionIndexIter {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(&mut self) -> Option<(String, String)> {
        let key = self.keys.get(self.index)?.clone();
        self.index += 1;
        Some(key)
    }
}
