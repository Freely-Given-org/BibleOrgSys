//WARNINGS_GO_HERE

//! Module handling USFM3Markers.
//! See http://ubsicap.github.io/usfm/

#![allow(non_snake_case)]

use phf::phf_map;
use compact_str::{CompactString, format_compact};
use std::error::Error;
use std::fmt;

//STATIC_STRUCTS_GO_HERE

#[derive(Debug, PartialEq)]
pub enum LookupError<'a> {
    MarkerNotFound(&'a str),
}

impl<'a> fmt::Display for LookupError<'a> {
    #[inline]
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LookupError::MarkerNotFound(m) => write!(f, "USFM marker '{}' not found", m),
        }
    }
}

impl Error for LookupError<'_> {}

#[inline]
fn get_array_index(marker: &str) -> Result<usize, LookupError<'_>> {
    USFM_MARKER_MAP.get(marker)
        .copied()
        .ok_or_else(|| LookupError::MarkerNotFound(marker))
}

/// Returns True if the given marker is valid.
#[inline]
pub fn is_valid_marker(marker: &str) -> bool {
    USFM_MARKER_MAP.contains_key(marker)
}

/// Returns True if the given marker is a newline marker.
pub fn is_newline_marker(marker: &str) -> bool {
    get_array_index(marker).map(|idx| USFM_MARKER_ARRAY[idx].level == USFMMarkerLevel::Newline).unwrap_or(false)
}

/// Returns True if the given marker is an internal (character) marker.
/// This includes character markers, but not footnote and xref markers.
pub fn is_internal_marker(marker: &str) -> bool {
    get_array_index(marker).map(|idx| USFM_MARKER_ARRAY[idx].level == USFMMarkerLevel::Internal).unwrap_or(false)
}

/// Returns True if the given marker is a note marker.
/// This includes figure, footnote and xref markers.
pub fn is_note_marker(marker: &str) -> bool {
    get_array_index(marker).map(|idx| USFM_MARKER_ARRAY[idx].level == USFMMarkerLevel::Note).unwrap_or(false)
}

/// Returns True if the given marker is deprecated.
pub fn is_deprecated_marker(marker: &str) -> bool {
    get_array_index(marker).map(|idx| USFM_MARKER_ARRAY[idx].deprecated).unwrap_or(false)
}

/// Returns True if the given marker is compulsory.
pub fn is_compulsory_marker(marker: &str) -> bool {
    get_array_index(marker).map(|idx| USFM_MARKER_ARRAY[idx].compulsory).unwrap_or(false)
}

/// Returns True if the given marker can have a numerical suffix.
pub fn is_numberable_marker(marker: &str) -> bool {
    get_array_index(marker).map(|idx| USFM_MARKER_ARRAY[idx].highest_number_suffix.is_some()).unwrap_or(false)
}

/// Returns True if the given marker supports nesting.
pub fn is_nesting_marker(marker: &str) -> bool {
    get_array_index(marker).map(|idx| USFM_MARKER_ARRAY[idx].nests).unwrap_or(false)
}

/// Returns True if the marker's content is intended to be printed.
pub fn is_printed(marker: &str) -> bool {
    get_array_index(marker).map(|idx| USFM_MARKER_ARRAY[idx].printed).unwrap_or(false)
}

/// Return 'N', 'O', 'A', 'S' for marker closure type:
/// "Never", "Optional", "Always", "Self".
pub fn get_marker_closure_type(marker: &str) -> Option<char> {
    get_array_index(marker).ok().map(|idx| {
        match USFM_MARKER_ARRAY[idx].closed {
            USFMMarkerClosed::No => 'N',
            USFMMarkerClosed::Always => 'A',
            USFMMarkerClosed::Optional => 'O',
            USFMMarkerClosed::SelfMarker => 'S',
        }
    })
}

/// Return "N", "S", "A" for marker content type:
/// "Never", "Sometimes", "Always".
pub fn get_marker_content_type(marker: &str) -> Option<char> {
    get_array_index(marker).ok().map(|idx| {
        match USFM_MARKER_ARRAY[idx].has_content {
            USFMMarkerContent::Never => 'N',
            USFMMarkerContent::Always => 'A',
            USFMMarkerContent::Sometimes => 'S',
        }
    })
}

/// Returns a marker without numerical suffixes, i.e., s1 -> s, q1 -> q, etc.
pub fn to_raw_marker(marker: &str) -> Option<&'static str> {
    get_array_index(marker).ok().map(|idx| USFM_MARKER_ARRAY[idx].marker)
}

/// Return a short string indicating where the marker occurs, e.g. "Introduction", "Text".
pub fn marker_occurs_in(marker: &str) -> Option<&'static str> {
    get_array_index(marker).ok().map(|idx| USFM_MARKER_ARRAY[idx].occurs_in)
}

/// Returns the English name for a marker.
pub fn get_marker_english_name(marker: &str) -> Option<&'static str> {
    get_array_index(marker).ok().map(|idx| USFM_MARKER_ARRAY[idx].name_english)
}

/// Returns the description for a marker (or None).
pub fn get_marker_description(marker: &str) -> Option<&'static str> {
    get_array_index(marker).ok().and_then(|idx| USFM_MARKER_ARRAY[idx].description)
}

/// Returns a list of all possible internal markers.
/// This includes character markers, but not footnote and xref markers.
pub fn get_internal_markers_list() -> Vec<&'static str> {
    USFM_MARKER_ARRAY.iter()
        .filter(|m| m.level == USFMMarkerLevel::Internal)
        .map(|m| m.marker)
        .collect()
}

/// Returns a list of all possible character markers.
/// These are fields that need to be displayed inline with the text, albeit with special formatting.
/// This excludes footnote and xref markers.
pub fn get_character_markers_list(
    include_backslash: bool,
    include_end_markers: bool,
    include_nested_markers: bool,
    expand_numberable_markers: bool
) -> Vec<String> {
    let mut result = Vec::new();
    for entry in USFM_MARKER_ARRAY.iter() {
        if entry.level != USFMMarkerLevel::Internal { continue; }
        
        let valid_occurs = match entry.occurs_in {
            "Text" | "Canonical Text" | "Poetry" | "Table row" | "Introduction" | "Numbering" | "Acrostic verse" => true,
            _ => false,
        };
        
        if valid_occurs {
            let marker = entry.marker;
            let adj_marker = if include_backslash { format_compact!("\\{}", marker) } else { CompactString::new(marker) };
            
            result.push(adj_marker.to_string());
            
            if include_nested_markers {
                result.push(if include_backslash { format_compact!("\\+{}", marker) } else { format_compact!("+{}", marker) }.to_string());
            }
            
            if include_end_markers {
                // In Python: assert self.getMarkerClosureType( marker ) in ('A','S') or self.markerOccursIn(marker)=="Table row"
                result.push(format_compact!("{}*", adj_marker).to_string());
                if include_nested_markers {
                    result.push(if include_backslash { format_compact!("\\+{}*", marker) } else { format_compact!("+{}*", marker) }.to_string());
                }
            }
            
            if expand_numberable_markers {
                if let Some(highest) = entry.highest_number_suffix {
                    for digit in 1..=highest {
                        let m_with_digit = format_compact!("{}{}", adj_marker, digit);
                        result.push(m_with_digit.to_string());
                        
                        if include_nested_markers {
                            result.push(if include_backslash { format_compact!("\\+{}{}", marker, digit) } else { format_compact!("+{}{}", marker, digit) }.to_string());
                        }
                        
                        if include_end_markers {
                            result.push(format_compact!("{}*", m_with_digit).to_string());
                            if include_nested_markers {
                                result.push(if include_backslash { format_compact!("\\+{}*{}", marker, digit) } else { format_compact!("+{}*{}", marker, digit) }.to_string()); // Wait, USFM digit comes before asterisk? No, \it1*
                                // Let's check USFM spec. Usually \it1 ... \it1*
                                // My Python code said: result.append( adjMarker + str_digit + '*' )
                                // So \it1*
                            }
                        }
                    }
                }
            }
        }
    }
    result
}

/// Returns a list of all possible note markers.
/// This includes figure, footnote and xref markers.
pub fn get_note_markers_list() -> Vec<&'static str> {
    USFM_MARKER_ARRAY.iter()
        .filter(|m| m.level == USFMMarkerLevel::Note)
        .map(|m| m.marker)
        .collect()
}

/// Returns a list of all possible new line markers.
pub fn get_newline_markers_list(option: &str) -> Vec<String> {
    match option {
        "Raw" => {
            USFM_MARKER_ARRAY.iter()
                .filter(|m| m.level == USFMMarkerLevel::Newline)
                .map(|m| m.marker.to_string())
                .collect()
        }
        "Numbered" => {
            let mut res = Vec::new();
            for entry in USFM_MARKER_ARRAY.iter() {
                if entry.level != USFMMarkerLevel::Newline { continue; }
                if let Some(highest) = entry.highest_number_suffix {
                    for i in 1..=highest {
                        res.push(format_compact!("{}{}", entry.marker, i).to_string());
                    }
                } else {
                    res.push(entry.marker.to_string());
                }
            }
            res
        }
        "Combined" => {
            let mut res = Vec::new();
            for entry in USFM_MARKER_ARRAY.iter() {
                if entry.level != USFMMarkerLevel::Newline { continue; }
                res.push(entry.marker.to_string());
                if let Some(highest) = entry.highest_number_suffix {
                    for i in 1..=highest {
                        res.push(format_compact!("{}{}", entry.marker, i).to_string());
                    }
                }
            }
            res
        }
        "CanonicalText" => {
            let mut res = Vec::new();
            for entry in USFM_MARKER_ARRAY.iter() {
                if entry.level != USFMMarkerLevel::Newline { continue; }
                if entry.occurs_in != "Canonical Text" { continue; }
                if let Some(highest) = entry.highest_number_suffix {
                    for i in 1..=highest {
                        res.push(format_compact!("{}{}", entry.marker, i).to_string());
                    }
                } else {
                    res.push(entry.marker.to_string());
                }
            }
            res
        }
        _ => Vec::new(),
    }
}

/// Removes all instances of the marker (if it exists) and its contents from the original_text.
///
/// marker parameter should not contain the backslash or the following space.
///
/// If closed_flag=Some(true), expects a close marker (otherwise does nothing).
/// If closed_flag=Some(false), goes to the next marker or end of line.
/// If closed_flag=None (unknown), stops at the first of closing marker, next marker, or end of line.
pub fn remove_usfm_character_field(marker: &str, original_text: &str, closed_flag: Option<bool>) -> CompactString {
    let mut text = CompactString::new(original_text);
    let open_pattern = format_compact!("\\{} ", marker);
    let close_pattern = format_compact!("\\{}*", marker);
    
    while let Some(ix) = text.find(open_pattern.as_str()) {
        let t_len = text.len();
        match closed_flag {
            None => {
                let ix_end = text[ix + open_pattern.len()..].find('\\')
                    .map(|rel| rel + ix + open_pattern.len());
                match ix_end {
                    None => {
                        text.truncate(ix);
                    }
                    Some(end) => {
                        if text[end..].starts_with(close_pattern.as_str()) {
                            text.replace_range(ix..end + close_pattern.len(), "");
                        } else {
                            text.replace_range(ix..end, "");
                        }
                    }
                }
            }
            Some(true) => {
                if let Some(ix_end) = text[ix + open_pattern.len()..].find(close_pattern.as_str())
                    .map(|rel| rel + ix + open_pattern.len()) {
                    text.replace_range(ix..ix_end + close_pattern.len(), "");
                } else {
                    break;
                }
            }
            Some(false) => {
                let ix_end = text[ix + open_pattern.len()..].find('\\')
                    .map(|rel| rel + ix + open_pattern.len());
                match ix_end {
                    None => {
                        text.truncate(ix);
                    }
                    Some(end) => {
                        if end < t_len - 1 && text.as_bytes()[end + 1] == b'+' {
                            // Doesn't handle embedded markers yet
                            break;
                        } else {
                            text.replace_range(ix..end, "");
                        }
                    }
                }
            }
        }
    }
    text
}

/// Makes a series of replacements to a line of USFM text.
/// This is designed for USFM character formatting fields that are explicitly closed
/// so it doesn't work with footnote or cross-reference fields where
/// the next open marker implicitly closes the previous marker.
///
/// Produces warning messages if the opening and close markers don't match.
///
/// Returns the adjusted text.
pub fn replace_usfm_character_fields(replacements: &[(&[&str], &str, &str)], original_text: &str) -> CompactString {
    let mut text = CompactString::new(original_text);
    for (markers, open_rep, close_rep) in replacements {
        for &marker in *markers {
            let open_m = format_compact!("\\{} ", marker);
            let close_m = format_compact!("\\{}*", marker);
            text = text.replace(open_m.as_str(), open_rep).replace(close_m.as_str(), close_rep).into();
            
            let nested_open_m = format_compact!("\\+{} ", marker);
            let nested_close_m = format_compact!("\\+{}*", marker);
            text = text.replace(nested_open_m.as_str(), open_rep).replace(nested_close_m.as_str(), close_rep).into();
        }
    }
    text
}

/// Information about a USFM marker found in text.
#[derive(Debug, Clone)]
pub struct MarkerInfo<'a> {
    /// The marker (without backslash or space/asterisk), or None for initial text.
    pub marker: Option<&'a str>,
    /// Index of the backslash character in the text.
    pub index_of_backslash: usize,
    /// Next significant character after the marker name:
    /// ' ' for normal opening marker,
    /// '+' for nested opening marker,
    /// '-' for nested closing marker,
    /// '*' for normal closing marker,
    /// None for end of line or initial text.
    pub next_significant_char: Option<char>,
    /// Full marker text including the backslash (can be used to search for).
    pub full_marker_text: Option<&'a str>,
    /// Character context for the following text (list of markers, including this one).
    pub context: Vec<&'a str>,
    /// Index (to the result list) of the marker which closes this opening marker.
    pub closing_marker_index: Option<usize>,
    /// Text field from the marker until the next USFM.
    pub text: &'a str,
}

/// Given a text, return a list of the actual markers
/// (along with their positions and other useful derived information).
pub fn get_marker_list_from_text(text: &str, include_initial_text: bool, _verify_markers: bool) -> Vec<MarkerInfo<'_>> {
    if text.is_empty() { return Vec::new(); }
    
    let mut first_result = Vec::new();
    let bytes = text.as_bytes();
    let text_len = bytes.len();
    
    let mut ix_bs = 0;
    while ix_bs < text_len {
        if bytes[ix_bs] == b'\\' {
            let marker;
            let mut iy = ix_bs + 1;
            if iy < text_len {
                let c1 = bytes[iy];
                if c1 == b'+' {
                    iy += 1;
                    if iy < text_len {
                        let start = iy;
                        while iy < text_len && bytes[iy] != b' ' && bytes[iy] != b'*' && bytes[iy] != b'\\' {
                            iy += 1;
                        }
                        marker = &text[start..iy];
                        if iy < text_len {
                            if bytes[iy] == b' ' {
                                first_result.push((marker, ix_bs, Some('+'), &text[ix_bs..iy+1]));
                            } else if bytes[iy] == b'*' {
                                first_result.push((marker, ix_bs, Some('-'), &text[ix_bs..iy+1]));
                            } else {
                                first_result.push((marker, ix_bs, Some('+'), &text[ix_bs..iy]));
                            }
                        } else {
                            first_result.push((marker, ix_bs, Some('+'), &text[ix_bs..iy]));
                        }
                    }
                } else if c1 != b' ' && c1 != b'*' && c1 != b'\\' {
                    let start = iy;
                    while iy < text_len && bytes[iy] != b' ' && bytes[iy] != b'*' && bytes[iy] != b'\\' {
                        iy += 1;
                    }
                    marker = &text[start..iy];
                    if iy < text_len {
                        if bytes[iy] == b' ' {
                            first_result.push((marker, ix_bs, Some(' '), &text[ix_bs..iy+1]));
                        } else if bytes[iy] == b'*' {
                            first_result.push((marker, ix_bs, Some('*'), &text[ix_bs..iy+1]));
                        } else {
                            first_result.push((marker, ix_bs, None, &text[ix_bs..iy]));
                        }
                    } else {
                        first_result.push((marker, ix_bs, None, &text[ix_bs..iy]));
                    }
                }
            }
            ix_bs = iy;
        } else {
            ix_bs += 1;
        }
    }

    let mut second_result = Vec::new();
    let mut cx: Vec<&str> = Vec::new();
    for (j, &(m, ix, x, mx)) in first_result.iter().enumerate() {
        if is_newline_marker(m) {
            cx.clear();
        } else {
            match x {
                Some(' ') | None => {
                    cx = vec![m];
                }
                Some('+') => {
                    cx.push(m);
                }
                Some('-') => {
                    if !cx.is_empty() { cx.pop(); }
                }
                Some('*') => {
                    cx.clear();
                }
                _ => {}
            }
        }
        
        let tx = if j >= first_result.len() - 1 {
            &text[ix + mx.len()..]
        } else {
            &text[ix + mx.len()..first_result[j+1].1]
        };
        second_result.push((m, ix, x, mx, cx.clone(), tx));
    }

    let mut final_result = Vec::new();
    let r_len = second_result.len();
    for (j, &(m, ix, x, mx, ref context, tx)) in second_result.iter().enumerate() {
        let mut end_idx = None;
        if (x == Some(' ') || x == Some('+')) && !context.is_empty() {
            let cxi = context.len() - 1;
            for k in j + 1..r_len {
                let (_, _, _, _, ref context2, _) = second_result[k];
                if context2.len() <= cxi || context2[cxi] != m {
                    end_idx = Some(k);
                    break;
                }
            }
        }
        final_result.push(MarkerInfo {
            marker: Some(m),
            index_of_backslash: ix,
            next_significant_char: x,
            full_marker_text: Some(mx),
            context: context.clone(),
            closing_marker_index: end_idx,
            text: tx,
        });
    }

    if include_initial_text && !final_result.is_empty() {
        let ix1 = final_result[0].index_of_backslash;
        if ix1 != 0 {
            let initial = MarkerInfo {
                marker: None,
                index_of_backslash: 0,
                next_significant_char: None,
                full_marker_text: None,
                context: Vec::new(),
                closing_marker_index: Some(1),
                text: &text[..ix1],
            };
            let mut new_result = vec![initial];
            for mut info in final_result {
                if let Some(ref mut idx) = info.closing_marker_index {
                    *idx += 1;
                }
                new_result.push(info);
            }
            return new_result;
        }
    }

    final_result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_markers() {
        assert!(is_valid_marker("id"));
        assert!(is_valid_marker("p"));
        assert!(is_valid_marker("v"));
        assert!(is_valid_marker("q1"));
        assert!(!is_valid_marker("xyz"));
    }

    #[test]
    fn test_newline_markers() {
        assert!(is_newline_marker("p"));
        assert!(is_newline_marker("q1"));
        assert!(!is_newline_marker("it"));
    }

    #[test]
    fn test_to_raw_marker() {
        assert_eq!(to_raw_marker("q1"), Some("q"));
        assert_eq!(to_raw_marker("s2"), Some("s"));
        assert_eq!(to_raw_marker("p"), Some("p"));
        assert_eq!(to_raw_marker("xyz"), None);
    }

    #[test]
    fn test_marker_metadata() {
        assert_eq!(get_marker_closure_type("it"), Some('A'));
        assert_eq!(get_marker_closure_type("p"), Some('N'));
        assert_eq!(get_marker_content_type("p"), Some('S'));
        assert_eq!(marker_occurs_in("p"), Some("Canonical Text"));
        assert_eq!(get_marker_english_name("v"), Some("Verse number"));
    }

    #[test]
    fn test_remove_usfm_character_field() {
        let text = "\\v 1 This is some \\it italicised\\it* text.";
        assert_eq!(remove_usfm_character_field("it", text, Some(true)).as_str(), "\\v 1 This is some  text.");
        
        let text2 = "\\v 2 This \\it is\\it* \\bd more\\bd* complicated.";
        assert_eq!(remove_usfm_character_field("bd", text2, Some(true)).as_str(), "\\v 2 This \\it is\\it*  complicated.");
        
        // Test None closure (stops at next backslash)
        let text3 = "\\v 3 Text \\it italic \\bd bold";
        assert_eq!(remove_usfm_character_field("it", text3, None).as_str(), "\\v 3 Text \\bd bold");
    }

    #[test]
    fn test_replace_usfm_character_fields() {
        let text = "\\v 1 This is \\it italic\\it*.";
        let result = replace_usfm_character_fields(&[(&["it"], "<i>", "</i>")], text);
        assert_eq!(result.as_str(), "\\v 1 This is <i>italic</i>.");
        
        let text2 = "\\v 2 Nested \\+it italic\\+it* inside.";
        let result2 = replace_usfm_character_fields(&[(&["it"], "<i>", "</i>")], text2);
        assert_eq!(result2.as_str(), "\\v 2 Nested <i>italic</i> inside.");
    }

    #[test]
    fn test_marker_list_from_text() {
        let text = "\\v 1 This is \\it italic\\it*.";
        let markers = get_marker_list_from_text(text, false, false);
        assert_eq!(markers.len(), 3);
        assert_eq!(markers[0].marker, Some("v"));
        assert_eq!(markers[1].marker, Some("it"));
        assert_eq!(markers[1].next_significant_char, Some(' '));
        assert_eq!(markers[1].closing_marker_index, Some(2));
        assert_eq!(markers[2].marker, Some("it"));
        assert_eq!(markers[2].next_significant_char, Some('*'));
    }

    #[test]
    fn test_marker_list_with_initial_text() {
        let text = "Initial text \\v 1 \\it italic\\it*";
        let markers = get_marker_list_from_text(text, true, false);
        assert_eq!(markers.len(), 4);
        assert_eq!(markers[0].marker, None);
        assert_eq!(markers[0].text, "Initial text ");
        assert_eq!(markers[1].marker, Some("v"));
    }

    #[test]
    fn test_nested_markers() {
        let text = "\\v 1 \\add outer \\+it inner\\+it* and outer again\\add*";
        let markers = get_marker_list_from_text(text, false, false);
        assert_eq!(markers.len(), 5); // v, add, +it, +it*, add*
        
        assert_eq!(markers[1].marker, Some("add"));
        assert_eq!(markers[1].next_significant_char, Some(' '));
        assert_eq!(markers[1].context, vec!["add"]);
        
        assert_eq!(markers[2].marker, Some("it"));
        assert_eq!(markers[2].next_significant_char, Some('+'));
        assert_eq!(markers[2].context, vec!["add", "it"]);
        
        assert_eq!(markers[3].marker, Some("it"));
        assert_eq!(markers[3].next_significant_char, Some('-'));
        assert_eq!(markers[3].context, vec!["add"]);
    }

    #[test]
    fn test_list_functions() {
        let cm = get_character_markers_list(false, false, false, false);
        assert!(cm.contains(&"it".to_string()));
        assert!(cm.contains(&"bd".to_string()));
        assert!(!cm.contains(&"p".to_string()));
        
        let nl = get_newline_markers_list("Raw");
        assert!(nl.contains(&"p".to_string()));
        assert!(nl.contains(&"q".to_string()));
        assert!(!nl.contains(&"q1".to_string())); // Raw doesn't include numbered
        
        let nl_num = get_newline_markers_list("Numbered");
        assert!(nl_num.contains(&"q1".to_string()));
        assert!(!nl_num.contains(&"q".to_string())); // Numbered only
    }
}

//WARNINGS_GO_HERE
