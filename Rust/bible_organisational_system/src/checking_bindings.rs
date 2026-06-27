//! Python bindings for Bible validation and checking.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use bos_internals::checking;
use crate::cv_index_bindings::PyInternalBibleEntryList;
use indexmap::IndexMap;

#[pyclass(name = "DiscoveryFlags", from_py_object)]
#[derive(Clone)]
pub struct PyDiscoveryFlags {
    pub inner: checking::DiscoveryFlags,
}

#[pymethods]
impl PyDiscoveryFlags {
    #[new]
    #[pyo3(signature = (partly_done=false, percentage_progress=0.0, seems_finished=false, have_main_headings=false, have_introductory_text=false))]
    fn new(
        partly_done: bool,
        percentage_progress: f32,
        seems_finished: bool,
        have_main_headings: bool,
        have_introductory_text: bool,
    ) -> Self {
        Self {
            inner: checking::DiscoveryFlags {
                partly_done,
                percentage_progress,
                seems_finished,
                have_main_headings,
                have_introductory_text,
            },
        }
    }

    #[getter]
    fn partly_done(&self) -> bool { self.inner.partly_done }
    #[setter]
    fn set_partly_done(&mut self, value: bool) { self.inner.partly_done = value; }
    #[getter(partlyDone)]
    fn get_partly_done_compat(&self) -> bool { self.inner.partly_done }
    #[setter(partlyDone)]
    fn set_partly_done_compat(&mut self, value: bool) { self.inner.partly_done = value; }

    #[getter]
    fn percentage_progress(&self) -> f32 { self.inner.percentage_progress }
    #[setter]
    fn set_percentage_progress(&mut self, value: f32) { self.inner.percentage_progress = value; }
    #[getter(percentageProgress)]
    fn get_percentage_progress_compat(&self) -> f32 { self.inner.percentage_progress }
    #[setter(percentageProgress)]
    fn set_percentage_progress_compat(&mut self, value: f32) { self.inner.percentage_progress = value; }

    #[getter]
    fn seems_finished(&self) -> bool { self.inner.seems_finished }
    #[setter]
    fn set_seems_finished(&mut self, value: bool) { self.inner.seems_finished = value; }
    #[getter(seemsFinished)]
    fn get_seems_finished_compat(&self) -> bool { self.inner.seems_finished }
    #[setter(seemsFinished)]
    fn set_seems_finished_compat(&mut self, value: bool) { self.inner.seems_finished = value; }

    #[getter]
    fn have_main_headings(&self) -> bool { self.inner.have_main_headings }
    #[setter]
    fn set_have_main_headings(&mut self, value: bool) { self.inner.have_main_headings = value; }
    #[getter(haveMainHeadings)]
    fn get_have_main_headings_compat(&self) -> bool { self.inner.have_main_headings }
    #[setter(haveMainHeadings)]
    fn set_have_main_headings_compat(&mut self, value: bool) { self.inner.have_main_headings = value; }

    #[getter]
    fn have_introductory_text(&self) -> bool { self.inner.have_introductory_text }
    #[setter]
    fn set_have_introductory_text(&mut self, value: bool) { self.inner.have_introductory_text = value; }
    #[getter(haveIntroductoryText)]
    fn get_have_introductory_text_compat(&self) -> bool { self.inner.have_introductory_text }
    #[setter(haveIntroductoryText)]
    fn set_have_introductory_text_compat(&mut self, value: bool) { self.inner.have_introductory_text = value; }
}

#[pyclass(name = "CheckOptions", from_py_object)]
#[derive(Clone)]
pub struct PyCheckOptions {
    pub inner: checking::CheckOptions,
}

#[pymethods]
impl PyCheckOptions {
    #[new]
    fn new() -> Self {
        Self {
            inner: checking::CheckOptions::default(),
        }
    }

    #[getter]
    fn check_sfms(&self) -> bool { self.inner.check_sfms }
    #[setter]
    fn set_check_sfms(&mut self, value: bool) { self.inner.check_sfms = value; }
    #[getter(checkSFMs)]
    fn get_check_sfms_compat(&self) -> bool { self.inner.check_sfms }
    #[setter(checkSFMs)]
    fn set_check_sfms_compat(&mut self, value: bool) { self.inner.check_sfms = value; }

    #[getter]
    fn check_words(&self) -> bool { self.inner.check_words }
    #[setter]
    fn set_check_words(&mut self, value: bool) { self.inner.check_words = value; }
    #[getter(checkWords)]
    fn get_check_words_compat(&self) -> bool { self.inner.check_words }
    #[setter(checkWords)]
    fn set_check_words_compat(&mut self, value: bool) { self.inner.check_words = value; }

    #[getter]
    fn check_headings(&self) -> bool { self.inner.check_headings }
    #[setter]
    fn set_check_headings(&mut self, value: bool) { self.inner.check_headings = value; }
    #[getter(checkHeadings)]
    fn get_check_headings_compat(&self) -> bool { self.inner.check_headings }
    #[setter(checkHeadings)]
    fn set_check_headings_compat(&mut self, value: bool) { self.inner.check_headings = value; }

    #[getter]
    fn check_introduction(&self) -> bool { self.inner.check_introduction }
    #[setter]
    fn set_check_introduction(&mut self, value: bool) { self.inner.check_introduction = value; }
    #[getter(checkIntroduction)]
    fn get_check_introduction_compat(&self) -> bool { self.inner.check_introduction }
    #[setter(checkIntroduction)]
    fn set_check_introduction_compat(&mut self, value: bool) { self.inner.check_introduction = value; }

    #[getter]
    fn check_notes(&self) -> bool { self.inner.check_notes }
    #[setter]
    fn set_check_notes(&mut self, value: bool) { self.inner.check_notes = value; }
    #[getter(checkNotes)]
    fn get_check_notes_compat(&self) -> bool { self.inner.check_notes }
    #[setter(checkNotes)]
    fn set_check_notes_compat(&mut self, value: bool) { self.inner.check_notes = value; }

    #[getter]
    fn check_speech_marks(&self) -> bool { self.inner.check_speech_marks }
    #[setter]
    fn set_check_speech_marks(&mut self, value: bool) { self.inner.check_speech_marks = value; }
    #[getter(checkSpeechMarks)]
    fn get_check_speech_marks_compat(&self) -> bool { self.inner.check_speech_marks }
    #[setter(checkSpeechMarks)]
    fn set_check_speech_marks_compat(&mut self, value: bool) { self.inner.check_speech_marks = value; }

    #[getter]
    fn check_added_units(&self) -> bool { self.inner.check_added_units }
    #[setter]
    fn set_check_added_units(&mut self, value: bool) { self.inner.check_added_units = value; }
    #[getter(checkAddedUnits)]
    fn get_check_added_units_compat(&self) -> bool { self.inner.check_added_units }
    #[setter(checkAddedUnits)]
    fn set_check_added_units_compat(&mut self, value: bool) { self.inner.check_added_units = value; }

    #[getter]
    fn opening_chars(&self) -> String { self.inner.opening_chars.clone() }
    #[setter]
    fn set_opening_chars(&mut self, value: String) { self.inner.opening_chars = value; }
    #[getter(openingChars)]
    fn get_opening_chars_compat(&self) -> String { self.inner.opening_chars.clone() }
    #[setter(openingChars)]
    fn set_opening_chars_compat(&mut self, value: String) { self.inner.opening_chars = value; }

    #[getter]
    fn closing_chars(&self) -> String { self.inner.closing_chars.clone() }
    #[setter]
    fn set_closing_chars(&mut self, value: String) { self.inner.closing_chars = value; }
    #[getter(closingChars)]
    fn get_closing_chars_compat(&self) -> String { self.inner.closing_chars.clone() }
    #[setter(closingChars)]
    fn set_closing_chars_compat(&mut self, value: String) { self.inner.closing_chars = value; }

    #[getter]
    fn leading_punct(&self) -> String { self.inner.leading_punct.clone() }
    #[setter]
    fn set_leading_punct(&mut self, value: String) { self.inner.leading_punct = value; }
    #[getter(leadingPunct)]
    fn get_leading_punct_compat(&self) -> String { self.inner.leading_punct.clone() }
    #[setter(leadingPunct)]
    fn set_leading_punct_compat(&mut self, value: String) { self.inner.leading_punct = value; }

    #[getter]
    fn trailing_punct(&self) -> String { self.inner.trailing_punct.clone() }
    #[setter]
    fn set_trailing_punct(&mut self, value: String) { self.inner.trailing_punct = value; }
    #[getter(trailingPunct)]
    fn get_trailing_punct_compat(&self) -> String { self.inner.trailing_punct.clone() }
    #[setter(trailingPunct)]
    fn set_trailing_punct_compat(&mut self, value: String) { self.inner.trailing_punct = value; }
}

#[pyfunction]
#[pyo3(name = "validateMarkers")]
pub fn py_validate_processed_markers<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    bos_book_code: &str,
    work_name: &str,
    strict_checking: bool,
) -> PyResult<Bound<'py, PyDict>> {
    let results = checking::validate_processed_markers(&entries.inner, bos_book_code, work_name, strict_checking);

    let dict = PyDict::new(py);
    dict.set_item("validation_errors", results.validation_errors)?;

    let priority_errors = PyList::empty(py);
    for (p, msg, (b, c, v)) in results.priority_errors {
        let error_tuple = (p, msg, (b, c, v));
        priority_errors.append(error_tuple)?;
    }
    dict.set_item("priority_errors", priority_errors)?;

    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "getVersification")]
pub fn py_get_versification<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    bos_book_code: &str,
    work_name: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let info = checking::get_versification(&entries.inner, bos_book_code, work_name);

    let result = PyList::empty(py);
    result.append(info.versification)?;
    result.append(info.omitted_verses)?;
    result.append(info.combined_verses)?;
    result.append(info.reordered_verses)?;

    let dict = PyDict::new(py);
    dict.set_item("versification", result)?;
    dict.set_item("errors", info.versification_errors)?;

    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "getAddedUnits")]
pub fn py_get_added_units<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    bos_book_code: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let info = checking::get_added_units(&entries.inner, bos_book_code);

    let result = PyList::empty(py);
    result.append(info.paragraph_references)?;
    result.append(info.q_references)?;
    result.append(info.section_headings)?;
    result.append(info.section_references)?;
    result.append(info.words_of_jesus)?;

    let dict = PyDict::new(py);
    dict.set_item("added_units", result)?;
    dict.set_item("errors", info.added_unit_errors)?;

    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "checkBook")]
pub fn py_check_book<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    bos_book_code: &str,
    work_name: &str,
    options: &PyCheckOptions,
    discovery: &PyDiscoveryFlags,
) -> PyResult<Bound<'py, PyDict>> {
    let results = checking::check_book(&entries.inner, bos_book_code, work_name, &options.inner, &discovery.inner);

    let dict = PyDict::new(py);
    dict.set_item("newline_marker_errors", results.newline_marker_errors)?;
    dict.set_item("internal_marker_errors", results.internal_marker_errors)?;
    dict.set_item("speech_mark_errors", results.speech_mark_errors)?;
    dict.set_item("word_errors", results.word_errors)?;
    dict.set_item("heading_errors", results.heading_errors)?;
    dict.set_item("introduction_errors", results.introduction_errors)?;
    dict.set_item("note_marker_errors", results.note_marker_errors)?;
    dict.set_item("validation_errors", results.validation_errors)?;

    dict.set_item("newline_marker_counts", results.newline_marker_counts)?;
    dict.set_item("internal_marker_counts", results.internal_marker_counts)?;
    dict.set_item("note_marker_counts", results.note_marker_counts)?;
    dict.set_item("functional_counts", results.functional_counts)?;

    let priority_errors = PyList::empty(py);
    for (p, msg, (b, c, v)) in results.priority_errors {
        let error_tuple = (p, msg, (b, c, v));
        priority_errors.append(error_tuple)?;
    }
    dict.set_item("priority_errors", priority_errors)?;

    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "checkBible")]
pub fn py_check_bible<'py>(
    py: Python<'py>,
    books_dict: &Bound<'py, PyDict>,
    work_name: &str,
    options: &PyCheckOptions,
    discovery_results: &crate::discovery_bindings::PyBibleDiscoveryResults,
) -> PyResult<Bound<'py, PyDict>> {
    let mut books = IndexMap::new();
    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let py_list: PyRef<PyInternalBibleEntryList> = value.extract()?;
        books.insert(bbb, py_list.inner.clone());
    }

    let results = checking::check_bible(&books, work_name, &options.inner, &discovery_results.inner);

    let dict = PyDict::new(py);
    for (bbb, book_results) in results {
        let book_dict = PyDict::new(py);
        book_dict.set_item("newline_marker_errors", book_results.newline_marker_errors)?;
        book_dict.set_item("internal_marker_errors", book_results.internal_marker_errors)?;
        book_dict.set_item("speech_mark_errors", book_results.speech_mark_errors)?;
        book_dict.set_item("word_errors", book_results.word_errors)?;
        book_dict.set_item("heading_errors", book_results.heading_errors)?;
        book_dict.set_item("introduction_errors", book_results.introduction_errors)?;
        book_dict.set_item("note_marker_errors", book_results.note_marker_errors)?;
        book_dict.set_item("validation_errors", book_results.validation_errors)?;
        book_dict.set_item("newline_marker_counts", book_results.newline_marker_counts)?;
        book_dict.set_item("internal_marker_counts", book_results.internal_marker_counts)?;
        book_dict.set_item("note_marker_counts", book_results.note_marker_counts)?;
        book_dict.set_item("functional_counts", book_results.functional_counts)?;

        let priority_errors = PyList::empty(py);
        for (p, msg, (b, c, v)) in book_results.priority_errors {
            let error_tuple = (p, msg, (b, c, v));
            priority_errors.append(error_tuple)?;
        }
        book_dict.set_item("priority_errors", priority_errors)?;

        dict.set_item(bbb, book_dict)?;
    }
    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "validateBibleMarkers")]
pub fn py_validate_bible_markers<'py>(
    py: Python<'py>,
    books_dict: &Bound<'py, PyDict>,
    work_name: &str,
    strict_checking: bool,
) -> PyResult<Bound<'py, PyDict>> {
    let mut books = IndexMap::new();
    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let py_list: PyRef<PyInternalBibleEntryList> = value.extract()?;
        books.insert(bbb, py_list.inner.clone());
    }

    let results = checking::validate_bible_markers(&books, work_name, strict_checking);

    let dict = PyDict::new(py);
    for (bbb, book_results) in results {
        let book_dict = PyDict::new(py);
        book_dict.set_item("validation_errors", book_results.validation_errors)?;
        let priority_errors = PyList::empty(py);
        for (p, msg, (b, c, v)) in book_results.priority_errors {
            let error_tuple = (p, msg, (b, c, v));
            priority_errors.append(error_tuple)?;
        }
        book_dict.set_item("priority_errors", priority_errors)?;
        dict.set_item(bbb, book_dict)?;
    }
    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "getBibleVersification")]
pub fn py_get_bible_versification<'py>(
    py: Python<'py>,
    books_dict: &Bound<'py, PyDict>,
    work_name: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let mut books = IndexMap::new();
    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let py_list: PyRef<PyInternalBibleEntryList> = value.extract()?;
        books.insert(bbb, py_list.inner.clone());
    }

    let results = checking::get_bible_versification(&books, work_name);

    let dict = PyDict::new(py);
    for (bbb, info) in results {
        let book_dict = PyDict::new(py);
        let res_list = PyList::empty(py);
        res_list.append(info.versification)?;
        res_list.append(info.omitted_verses)?;
        res_list.append(info.combined_verses)?;
        res_list.append(info.reordered_verses)?;
        book_dict.set_item("versification", res_list)?;
        book_dict.set_item("errors", info.versification_errors)?;
        dict.set_item(bbb, book_dict)?;
    }
    Ok(dict)
}

#[pyfunction]
#[pyo3(name = "getBibleAddedUnits")]
pub fn py_get_bible_added_units<'py>(
    py: Python<'py>,
    books_dict: &Bound<'py, PyDict>,
) -> PyResult<Bound<'py, PyDict>> {
    let mut books = IndexMap::new();
    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let py_list: PyRef<PyInternalBibleEntryList> = value.extract()?;
        books.insert(bbb, py_list.inner.clone());
    }

    let results = checking::get_bible_added_units(&books);

    let dict = PyDict::new(py);
    for (bbb, info) in results {
        let book_dict = PyDict::new(py);
        let res_list = PyList::empty(py);
        res_list.append(info.paragraph_references)?;
        res_list.append(info.q_references)?;
        res_list.append(info.section_headings)?;
        res_list.append(info.section_references)?;
        res_list.append(info.words_of_jesus)?;
        book_dict.set_item("added_units", res_list)?;
        book_dict.set_item("errors", info.added_unit_errors)?;
        dict.set_item(bbb, book_dict)?;
    }
    Ok(dict)
}
