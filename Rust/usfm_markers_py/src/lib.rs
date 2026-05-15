use pyo3::prelude::*;
use pyo3::types::PyList;
use ::usfm_markers::{
    is_valid_marker, is_newline_marker, is_internal_marker, is_note_marker,
    is_deprecated_marker, is_compulsory_marker, is_numberable_marker,
    is_nesting_marker, is_printed, get_marker_closure_type, get_marker_content_type,
    to_raw_marker, to_standard_marker, marker_occurs_in, get_marker_english_name, 
    get_marker_description, get_occurs_in_list, get_typical_note_sets,
    remove_usfm_character_field, replace_usfm_character_fields, get_marker_list_from_text,
    get_internal_markers_list, get_character_markers_list, get_note_markers_list,
    get_newline_markers_list,
    OFTEN_IGNORED_USFM_HEADER_MARKERS, USFM_ALL_TITLE_MARKERS,
    USFM_INTRODUCTION_PARAGRAPH_MARKERS, USFM_ALL_INTRODUCTION_MARKERS,
    USFM_ALL_SECTION_HEADING_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS,
    USFM_ALL_BIBLE_PARAGRAPH_MARKERS, USFM_PRECHAPTER_MARKERS,
    USFM_PRINTABLE_MARKERS,
};

/// Returns a list of all possible internal markers.
#[pyfunction]
#[pyo3(name = "get_internal_markers_list")]
fn get_internal_markers_list_py() -> PyResult<Vec<&'static str>> {
    Ok(get_internal_markers_list())
}

/// Returns a list of all possible character markers.
#[pyfunction]
#[pyo3(name = "get_character_markers_list", signature = (include_backslash=false, include_end_markers=false, include_nested_markers=false, expand_numberable_markers=false))]
fn get_character_markers_list_py(
    include_backslash: bool,
    include_end_markers: bool,
    include_nested_markers: bool,
    expand_numberable_markers: bool
) -> PyResult<Vec<String>> {
    Ok(get_character_markers_list(include_backslash, include_end_markers, include_nested_markers, expand_numberable_markers))
}

/// Backward compatibility alias for get_character_markers_list.
#[pyfunction]
#[pyo3(name = "getCharacterMarkersList", signature = (include_backslash=false, include_end_markers=false, include_nested_markers=false, expand_numberable_markers=false))]
fn get_character_markers_list_compat(
    include_backslash: bool,
    include_end_markers: bool,
    include_nested_markers: bool,
    expand_numberable_markers: bool
) -> PyResult<Vec<String>> {
    Ok(get_character_markers_list(include_backslash, include_end_markers, include_nested_markers, expand_numberable_markers))
}

/// Returns a list of all possible note markers.
#[pyfunction]
#[pyo3(name = "get_note_markers_list")]
fn get_note_markers_list_py() -> PyResult<Vec<&'static str>> {
    Ok(get_note_markers_list())
}

/// Returns a container of typical footnote and xref sets.
#[pyfunction]
#[pyo3(name = "get_typical_note_sets")]
fn get_typical_note_sets_py(select: &str) -> PyResult<Vec<Vec<&'static str>>> {
    Ok(get_typical_note_sets(select).into_iter().map(|s| s.to_vec()).collect())
}

/// Returns a list of all possible new line markers.
#[pyfunction]
#[pyo3(name = "get_newline_markers_list")]
fn get_newline_markers_list_py(option: &str) -> PyResult<Vec<String>> {
    Ok(get_newline_markers_list(option))
}

/// Returns True if the given marker is valid.
#[pyfunction]
#[pyo3(name = "is_valid_marker")]
fn is_valid_marker_py(marker: &str) -> PyResult<bool> {
    Ok(is_valid_marker(marker))
}

/// Returns True if the given marker is a newline marker.
#[pyfunction]
#[pyo3(name = "is_newline_marker")]
fn is_newline_marker_py(marker: &str) -> PyResult<bool> {
    Ok(is_newline_marker(marker))
}

/// Returns True if the given marker is an internal (character) marker.
#[pyfunction]
#[pyo3(name = "is_internal_marker")]
fn is_internal_marker_py(marker: &str) -> PyResult<bool> {
    Ok(is_internal_marker(marker))
}

/// Returns True if the given marker is a note marker.
#[pyfunction]
#[pyo3(name = "is_note_marker")]
fn is_note_marker_py(marker: &str) -> PyResult<bool> {
    Ok(is_note_marker(marker))
}

/// Returns True if the given marker is deprecated.
#[pyfunction]
#[pyo3(name = "is_deprecated_marker")]
fn is_deprecated_marker_py(marker: &str) -> PyResult<bool> {
    Ok(is_deprecated_marker(marker))
}

/// Returns True if the given marker is compulsory.
#[pyfunction]
#[pyo3(name = "is_compulsory_marker")]
fn is_compulsory_marker_py(marker: &str) -> PyResult<bool> {
    Ok(is_compulsory_marker(marker))
}

/// Returns True if the given marker can have a numerical suffix.
#[pyfunction]
#[pyo3(name = "is_numberable_marker")]
fn is_numberable_marker_py(marker: &str) -> PyResult<bool> {
    Ok(is_numberable_marker(marker))
}

/// Returns True if the given marker supports nesting.
#[pyfunction]
#[pyo3(name = "is_nesting_marker")]
fn is_nesting_marker_py(marker: &str) -> PyResult<bool> {
    Ok(is_nesting_marker(marker))
}

/// Returns True if the marker's content is intended to be printed.
#[pyfunction]
#[pyo3(name = "is_printed")]
fn is_printed_py(marker: &str) -> PyResult<bool> {
    Ok(is_printed(marker))
}

/// Return 'N', 'O', 'A', 'S' for "never", "optional", "always", "self".
#[pyfunction]
#[pyo3(name = "get_marker_closure_type")]
fn get_marker_closure_type_py(marker: &str) -> PyResult<Option<char>> {
    Ok(get_marker_closure_type(marker))
}

/// Return "N", "S", "A" for "never", "sometimes", "always".
#[pyfunction]
#[pyo3(name = "get_marker_content_type")]
fn get_marker_content_type_py(marker: &str) -> PyResult<Option<char>> {
    Ok(get_marker_content_type(marker))
}

/// Returns a marker without numerical suffixes, i.e., s1->s, q1->q, etc.
#[pyfunction]
#[pyo3(name = "to_raw_marker")]
fn to_raw_marker_py(marker: &str) -> PyResult<Option<&'static str>> {
    Ok(to_raw_marker(marker))
}

/// Returns a standard marker, i.e., s->s1, q->q1, etc.
#[pyfunction]
#[pyo3(name = "to_standard_marker")]
fn to_standard_marker_py(marker: &str) -> PyResult<Option<&'static str>> {
    Ok(to_standard_marker(marker))
}

/// Return a short string, e.g. "Introduction", "Text".
#[pyfunction]
#[pyo3(name = "marker_occurs_in")]
fn marker_occurs_in_py(marker: &str) -> PyResult<Option<&'static str>> {
    Ok(marker_occurs_in(marker))
}

/// Returns the English name for a marker.
#[pyfunction]
#[pyo3(name = "get_marker_english_name")]
fn get_marker_english_name_py(marker: &str) -> PyResult<Option<&'static str>> {
    Ok(get_marker_english_name(marker))
}

/// Returns the description for a marker (or None).
#[pyfunction]
#[pyo3(name = "get_marker_description")]
fn get_marker_description_py(marker: &str) -> PyResult<Option<&'static str>> {
    Ok(get_marker_description(marker))
}

/// Returns a list of strings which marker_occurs_in can return.
#[pyfunction]
#[pyo3(name = "get_occurs_in_list")]
fn get_occurs_in_list_py() -> PyResult<Vec<&'static str>> {
    Ok(get_occurs_in_list())
}

/// Removes all instances of the marker (if it exists) and its contents from the original_text.
///
/// marker parameter should not contain the backslash or the following space.
///
/// If closed_flag=True, expects a close marker (otherwise does nothing).
/// If closed_flag=False, goes to the next marker or end of line.
/// If closed_flag=None (unknown), stops at the first of closing marker, next marker, or end of line.
#[pyfunction]
#[pyo3(name = "remove_usfm_character_field", signature = (marker, original_text, closed_flag=None))]
fn remove_usfm_character_field_py(marker: &str, original_text: &str, closed_flag: Option<bool>) -> PyResult<String> {
    Ok(remove_usfm_character_field(marker, original_text, closed_flag).to_string())
}

/// Backward compatibility alias for remove_usfm_character_field.
#[pyfunction]
#[pyo3(name = "removeUSFMCharacterField", signature = (marker, original_text, closed_flag=None))]
fn remove_usfm_character_field_compat(marker: &str, original_text: &str, closed_flag: Option<bool>) -> PyResult<String> {
    Ok(remove_usfm_character_field(marker, original_text, closed_flag).to_string())
}

/// Makes a series of replacements to a line of USFM text.
/// Designed for explicitly closed character formatting fields.
#[pyfunction]
#[pyo3(name = "replace_usfm_character_fields")]
fn replace_usfm_character_fields_py(replacements: Vec<(Vec<String>, String, String)>, original_text: &str) -> PyResult<String> {
    let mut rust_reps = Vec::with_capacity(replacements.len());
    for (markers, open, close) in &replacements {
        let m_refs: Vec<&str> = markers.iter().map(|s| s.as_str()).collect();
        rust_reps.push((m_refs, open.as_str(), close.as_str()));
    }
    
    let mut final_reps: Vec<(&[&str], &str, &str)> = Vec::with_capacity(rust_reps.len());
    for (m, o, c) in &rust_reps {
        final_reps.push((m.as_slice(), *o, *c));
    }
        
    Ok(replace_usfm_character_fields(&final_reps, original_text).to_string())
}

/// Backward compatibility alias for replace_usfm_character_fields.
#[pyfunction]
#[pyo3(name = "replaceUSFMCharacterFields")]
fn replace_usfm_character_fields_compat(replacements: Vec<(Vec<String>, String, String)>, original_text: &str) -> PyResult<String> {
    let mut rust_reps = Vec::with_capacity(replacements.len());
    for (markers, open, close) in &replacements {
        let m_refs: Vec<&str> = markers.iter().map(|s| s.as_str()).collect();
        rust_reps.push((m_refs, open.as_str(), close.as_str()));
    }
    
    let mut final_reps: Vec<(&[&str], &str, &str)> = Vec::with_capacity(rust_reps.len());
    for (m, o, c) in &rust_reps {
        final_reps.push((m.as_slice(), *o, *c));
    }
        
    Ok(replace_usfm_character_fields(&final_reps, original_text).to_string())
}

/// Given a text, return a list of the actual markers
/// (along with their positions and other useful derived information).
///
/// Returns a list of seven-tuples containing:
/// 1: marker name or None for initial text
/// 2: index of backslash character in text string
/// 3: next significant char (' ', '+', '-', '*', or '')
/// 4: full marker text including backslash
/// 5: character context for the following text (list of markers)
/// 6: index of closing marker in the result list (or None)
/// 7: text field from the marker until the next USFM
#[pyfunction]
#[pyo3(name = "get_marker_list_from_text", signature = (text, include_initial_text=false, _verify_markers=false))]
fn get_marker_list_from_text_py<'py>(py: Python<'py>, text: &str, include_initial_text: bool, _verify_markers: bool) -> PyResult<Bound<'py, PyList>> {
    let result = get_marker_list_from_text(text, include_initial_text, _verify_markers);
    let list = PyList::empty(py);
    for info in result {
        let context = PyList::empty(py);
        for c in info.context {
            context.append(c)?;
        }
        
        let sig_char = match info.next_significant_char {
            Some(' ') => " ",
            Some('+') => "+",
            Some('-') => "-",
            Some('*') => "*",
            _ => "",
        };

        let tuple = (
            info.marker,
            info.index_of_backslash,
            sig_char,
            info.full_marker_text,
            context,
            info.closing_marker_index,
            info.text,
        ).into_pyobject(py)?;
        list.append(tuple)?;
    }
    Ok(list)
}

/// Backward compatibility alias for get_marker_list_from_text.
#[pyfunction]
#[pyo3(name = "getMarkerListFromText", signature = (text, include_initial_text=false, verify_markers=false))]
fn get_marker_list_from_text_compat<'py>(py: Python<'py>, text: &str, include_initial_text: bool, verify_markers: bool) -> PyResult<Bound<'py, PyList>> {
    let result = get_marker_list_from_text(text, include_initial_text, verify_markers);
    let list = PyList::empty(py);
    for info in result {
        let context = PyList::empty(py);
        for c in info.context {
            context.append(c)?;
        }
        
        let sig_char = match info.next_significant_char {
            Some(' ') => " ",
            Some('+') => "+",
            Some('-') => "-",
            Some('*') => "*",
            _ => "",
        };

        let tuple = (
            info.marker,
            info.index_of_backslash,
            sig_char,
            info.full_marker_text,
            context,
            info.closing_marker_index,
            info.text,
        ).into_pyobject(py)?;
        list.append(tuple)?;
    }
    Ok(list)
}

#[pymodule]
fn usfm_markers_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(is_valid_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_newline_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_internal_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_note_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_deprecated_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_compulsory_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_numberable_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_nesting_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_printed_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_marker_closure_type_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_marker_content_type_py, m)?)?;
    m.add_function(wrap_pyfunction!(to_raw_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(to_standard_marker_py, m)?)?;
    m.add_function(wrap_pyfunction!(marker_occurs_in_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_marker_english_name_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_marker_description_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_occurs_in_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(remove_usfm_character_field_py, m)?)?;
    m.add_function(wrap_pyfunction!(remove_usfm_character_field_compat, m)?)?;
    m.add_function(wrap_pyfunction!(replace_usfm_character_fields_py, m)?)?;
    m.add_function(wrap_pyfunction!(replace_usfm_character_fields_compat, m)?)?;
    m.add_function(wrap_pyfunction!(get_marker_list_from_text_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_marker_list_from_text_compat, m)?)?;
    m.add_function(wrap_pyfunction!(get_internal_markers_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_character_markers_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_character_markers_list_compat, m)?)?;
    m.add_function(wrap_pyfunction!(get_note_markers_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_newline_markers_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_typical_note_sets_py, m)?)?;
    
    // Add constants as lists
    m.add("OFTEN_IGNORED_USFM_HEADER_MARKERS", PyList::new(m.py(), OFTEN_IGNORED_USFM_HEADER_MARKERS)?)?;
    m.add("USFM_ALL_TITLE_MARKERS", PyList::new(m.py(), USFM_ALL_TITLE_MARKERS)?)?;
    m.add("USFM_INTRODUCTION_PARAGRAPH_MARKERS", PyList::new(m.py(), USFM_INTRODUCTION_PARAGRAPH_MARKERS)?)?;
    m.add("USFM_ALL_INTRODUCTION_MARKERS", PyList::new(m.py(), USFM_ALL_INTRODUCTION_MARKERS)?)?;
    m.add("USFM_ALL_SECTION_HEADING_MARKERS", PyList::new(m.py(), USFM_ALL_SECTION_HEADING_MARKERS)?)?;
    m.add("USFM_BIBLE_PARAGRAPH_MARKERS", PyList::new(m.py(), USFM_BIBLE_PARAGRAPH_MARKERS)?)?;
    m.add("USFM_ALL_BIBLE_PARAGRAPH_MARKERS", PyList::new(m.py(), USFM_ALL_BIBLE_PARAGRAPH_MARKERS)?)?;
    m.add("USFM_PRECHAPTER_MARKERS", PyList::new(m.py(), USFM_PRECHAPTER_MARKERS)?)?;
    m.add("USFM_PRINTABLE_MARKERS", PyList::new(m.py(), USFM_PRINTABLE_MARKERS)?)?;

    Ok(())
}
