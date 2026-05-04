//! Bible Org Sys Internals - Validation and checking logic.

use crate::entry_extras::InternalBibleEntryList;
use crate::markers::{self};

/// A single validation issue (error or warning).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ValidationIssue {
    pub priority: u16,
    pub message: String,
    pub book: String,
    pub chapter: String,
    pub verse: String,
    pub marker: String,
}

/// Aggregated results of a Bible check.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct CheckResults {
    pub issues: Vec<ValidationIssue>,
    pub newline_marker_errors: Vec<String>,
    pub internal_marker_errors: Vec<String>,
    pub note_marker_errors: Vec<String>,
    pub validation_errors: Vec<String>,
    pub priority_errors: Vec<(u16, String, (String, String, String))>,
    pub speech_mark_errors: Vec<String>,
    pub word_errors: Vec<String>,
    pub heading_errors: Vec<String>,
    pub introduction_errors: Vec<String>,
    pub newline_marker_counts: std::collections::HashMap<String, u32>,
    pub internal_marker_counts: std::collections::HashMap<String, u32>,
    pub note_marker_counts: std::collections::HashMap<String, u32>,
    pub functional_counts: std::collections::HashMap<String, u32>,
}

impl CheckResults {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_priority_error(&mut self, priority: u16, book: &str, chapter: &str, verse: &str, message: String) {
        self.priority_errors.push((priority, message, (book.to_string(), chapter.to_string(), verse.to_string())));
    }
}

/// Versification information for a Bible book.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct VersificationInfo {
    pub versification: Vec<(String, String)>,
    pub omitted_verses: Vec<(String, String)>,
    pub combined_verses: Vec<(String, String)>,
    pub reordered_verses: Vec<(String, String, String)>,
    pub versification_errors: Vec<String>,
}

/// Added units information for a Bible book.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct AddedUnitsInfo {
    pub paragraph_references: Vec<(String, String, Option<String>)>,
    pub q_references: Vec<((String, String, Option<String>), i32)>,
    pub section_headings: Vec<((String, String), String, String)>,
    pub section_references: Vec<((String, String), String)>,
    pub words_of_jesus: Vec<((String, String), (String, i32, bool, bool))>,
    pub added_unit_errors: Vec<String>,
}

/// Discovery flags used for checking.
#[derive(Debug, Clone, Default)]
pub struct DiscoveryFlags {
    pub partly_done: bool,
    pub percentage_progress: f32,
    pub seems_finished: bool,
    pub have_main_headings: bool,
    pub have_introductory_text: bool,
}

/// Options for checking a Bible book.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CheckOptions {
    pub check_sfms: bool,
    pub check_words: bool,
    pub check_headings: bool,
    pub check_introduction: bool,
    pub check_notes: bool,
    pub check_speech_marks: bool,
    pub check_added_units: bool,
    pub opening_chars: String,
    pub closing_chars: String,
    pub leading_punct: String,
    pub trailing_punct: String,
}

impl Default for CheckOptions {
    fn default() -> Self {
        Self {
            check_sfms: true,
            check_words: true,
            check_headings: true,
            check_introduction: true,
            check_notes: true,
            check_speech_marks: true,
            check_added_units: false,
            opening_chars: "“‘«„‹".to_string(),
            closing_chars: "”’»”›".to_string(),
            leading_punct: " *“‘(⌊—/".to_string(),
            trailing_punct: " .,?!;:”’ )⌋/\\".to_string(),
        }
    }
}

/// Port of `InternalBibleBook.validateMarkers`.
pub fn validate_processed_markers(
    entries: &InternalBibleEntryList,
    book_code: &str,
    _work_name: &str,
    _strict_checking: bool,
) -> CheckResults {
    let mut results = CheckResults::new();
    let mut chapter = "-1".to_string();
    let mut verse = "-1".to_string();

    for (j, entry) in entries.iter().enumerate() {
        let marker = entry.marker();
        let text = entry.text().unwrap_or("");

        // Keep track of location
        if marker == "c" {
            if !text.is_empty() {
                chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            } else {
                results.validation_errors.push(format!("{} {}:{} Missing chapter number", book_code, chapter, verse));
                results.add_priority_error(99, book_code, &chapter, &verse, "Missing chapter number".to_string());
                if chapter == "-1" {
                    chapter = "1".to_string();
                }
            }
            verse = "0".to_string();
        } else if marker == "v" {
            if !text.is_empty() {
                verse = text.split_whitespace().next().unwrap_or(text).to_string();
            } else {
                results.validation_errors.push(format!("{} {}:{} Missing verse number", book_code, chapter, verse));
                results.add_priority_error(86, book_code, &chapter, &verse, "Missing verse number".to_string());
            }
        } else if chapter == "-1" && !matches!(marker, "headers" | "intro") {
            if let Ok(v) = verse.parse::<i32>() {
                verse = (v + 1).to_string();
            }
        }

        let line_location = format!("{} {}:{}", book_code, chapter, verse);

        if marker == "id" {
            if j != 0 {
                results.validation_errors.push(format!("{} Marker 'id' should only appear as the first marker in a book but found on line {} in {}: {}", line_location, j + 1, marker, text));
                results.add_priority_error(99, book_code, &chapter, &verse, "'id' marker should only be in first line of file".to_string());
            }
            *results.functional_counts.entry("Book ID".to_string()).or_insert(0) += 1;
        }
 else if marker == "h" {
            *results.functional_counts.entry("Book Header".to_string()).or_insert(0) += 1;
        } else if marker == "p" {
            *results.functional_counts.entry("Paragraphs".to_string()).or_insert(0) += 1;
        } else if marker == "r" {
            *results.functional_counts.entry("Section Cross-References".to_string()).or_insert(0) += 1;
        }

        if !marker.starts_with('¬') && !markers::custom_nesting::is_custom_nesting(marker) && marker != "v=" {
            *results.newline_marker_counts.entry(marker.to_string()).or_insert(0) += 1;
        }

        if marker.starts_with('¬') {
        } else if !matches!(marker, "c#" | "cl¤" | "vp#" | "v=") 
            && !markers::custom_nesting::is_custom_nesting(marker)
            && !markers::is_newline_marker(marker) 
        {
            results.validation_errors.push(format!("{} Unexpected {:?} newline marker in Bible book (Text is {:?})", line_location, marker, text));
            results.add_priority_error(80, book_code, &chapter, &verse, format!("Marker {:?} not expected at beginning of line", marker));
        }

        if markers::is_deprecated_marker(marker) {
            results.validation_errors.push(format!("{} Deprecated {:?} newline marker in Bible book (Text is {:?})", line_location, marker, text));
            results.add_priority_error(90, book_code, &chapter, &verse, format!("Newline marker {:?} is deprecated in USFM standard", marker));
        }

        if !text.is_empty() && text.contains('\\') {
            static MARKER_RE: std::sync::LazyLock<regex::Regex> = std::sync::LazyLock::new(|| {
                regex::Regex::new(r"\\(\+?[a-z1-4]{1,6})").unwrap()
            });

            for cap in MARKER_RE.captures_iter(text) {
                let inside_marker = cap.get(1).unwrap().as_str();
                if markers::is_newline_marker(inside_marker) {
                    results.validation_errors.push(format!("{} Marker {:?} must not appear within line in {}: {}", line_location, inside_marker, marker, text));
                    results.add_priority_error(90, book_code, &chapter, &verse, format!("Newline marker {:?} should be at start of line", inside_marker));
                }
                if markers::is_deprecated_marker(inside_marker) {
                    results.validation_errors.push(format!("{} Deprecated {:?} internal marker in Bible book (Text is {:?})", line_location, inside_marker, text));
                    results.add_priority_error(89, book_code, &chapter, &verse, format!("Internal marker {:?} is deprecated in USFM standard", inside_marker));
                }
            }
        }
    }

    results
}

/// Port of `InternalBibleBook.getVersification`.
pub fn get_versification(
    entries: &InternalBibleEntryList,
    book_code: &str,
    work_name: &str,
) -> VersificationInfo {
    let mut info = VersificationInfo::default();
    let mut chapter_text = "-1".to_string();
    let mut chapter_number: i32 = -1;
    let mut last_chapter_number: i32 = -1;
    let mut last_verse_number_string = "0".to_string();

    for (j, entry) in entries.iter().enumerate() {
        let marker = entry.marker();
        let text = entry.text().unwrap_or("");

        if marker == "c" {
            if chapter_number == -1 {
                info.versification.push((chapter_text.clone(), (j as i32 - 1).to_string()));
            } else {
                info.versification.push((chapter_text.clone(), last_verse_number_string.clone()));
            }

            chapter_text = text.trim().to_string();
            if chapter_text.contains(' ') {
                info.versification_errors.push(format!("{} Unexpected space in USFM chapter number field {:?}", book_code, text));
                chapter_text = chapter_text.split_whitespace().next().unwrap_or(&chapter_text).to_string();
            }

            match chapter_text.parse::<i32>() {
                Ok(c) => chapter_number = c,
                Err(_) => {
                    chapter_number = if chapter_number == -1 { 1 } else { chapter_number + 1 };
                }
            }

            if chapter_number != last_chapter_number + 1 && (last_chapter_number != -1 || chapter_number != 1) {
                info.versification_errors.push(format!("{} ('{}' after '{}') USFM chapter numbers out of sequence in {} Bible book", book_code, chapter_number, last_chapter_number, work_name));
            }
            last_chapter_number = chapter_number;
            last_verse_number_string = "0".to_string();
        } else if marker == "v" {
            if chapter_text == "0" {
                info.versification_errors.push(format!("{} Missing chapter number field before verse {}", book_code, text));
            }
            if text.is_empty() {
                info.versification_errors.push(format!("{} Missing USFM verse number after v{}", book_code, last_verse_number_string));
                continue;
            }

            let verse_text = text.to_string();
            let mut clean_verse_text = verse_text.clone();
            for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ[]()\\".chars() {
                clean_verse_text = clean_verse_text.replace(c, "");
            }

            let (verse_number_str, end_verse_number_str) = if clean_verse_text.contains('-') || clean_verse_text.contains('–') {
                let range_text = clean_verse_text.replace('–', "-");
                let bits: Vec<&str> = range_text.split('-').collect();
                let start = bits[0].to_string();
                let end = if bits.len() > 1 { bits[1].to_string() } else { start.clone() };
                
                info.combined_verses.push((chapter_text.clone(), verse_text.clone()));
                (start, end)
            } else if clean_verse_text.contains(',') {
                let bits: Vec<&str> = clean_verse_text.split(',').collect();
                let start = bits[0].to_string();
                let end = if bits.len() > 1 { bits[1].to_string() } else { start.clone() };
                
                info.combined_verses.push((chapter_text.clone(), verse_text.clone()));
                (start, end)
            } else {
                (clean_verse_text.clone(), clean_verse_text.clone())
            };

            let verse_number = verse_number_str.parse::<i32>().unwrap_or(999);
            let last_verse_number = last_verse_number_string.parse::<i32>().unwrap_or(999);

            if verse_number != last_verse_number + 1 {
                if verse_number <= last_verse_number {
                    info.versification_errors.push(format!("{} {} ('{}' after '{}') USFM verse numbers out of sequence in Bible book", book_code, chapter_text, verse_text, last_verse_number_string));
                    info.reordered_verses.push((chapter_text.clone(), last_verse_number_string.clone(), verse_text.clone()));
                } else {
                    info.versification_errors.push(format!("{} {} Missing USFM verse number(s) between '{}' and '{}' in Bible book", book_code, chapter_text, last_verse_number_string, verse_number_str));
                    for n in (last_verse_number + 1)..verse_number {
                        info.omitted_verses.push((chapter_text.clone(), n.to_string()));
                    }
                }
            }
            last_verse_number_string = end_verse_number_str;
        }
    }

    info.versification.push((chapter_text, last_verse_number_string));
    info
}

/// Port of `InternalBibleBook.getAddedUnits`.
pub fn get_added_units(
    entries: &InternalBibleEntryList,
    book_code: &str,
) -> AddedUnitsInfo {
    let mut info = AddedUnitsInfo::default();
    let mut chapter = "0".to_string();
    let mut verse = "0".to_string();

    for entry in entries.iter() {
        let marker = entry.marker();
        let text = entry.text().unwrap_or("");

        if marker == "c" {
            chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            verse = "0".to_string();
        } else if marker == "cp" {
            let cp_chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            chapter = cp_chapter.trim_matches(|c| c == '(' || c == ')').to_string();
            verse = "0".to_string();
        } else if marker == "v" {
            if text.is_empty() {
                info.added_unit_errors.push(format!("{} Missing USFM verse number after v{}", book_code, verse));
                continue;
            }
            verse = text.to_string();
        } else if marker == "p" {
            let mut suffix: Option<String> = None;
            loop {
                let current_ref = (chapter.clone(), verse.clone(), suffix.clone());
                if !info.paragraph_references.contains(&current_ref) {
                    info.paragraph_references.push(current_ref);
                    break;
                }
                suffix = match suffix {
                    None => Some("a".to_string()),
                    Some(s) => {
                        let next_char = (s.chars().next().unwrap() as u8 + 1) as char;
                        Some(next_char.to_string())
                    }
                };
            }
        } else if marker.starts_with('q') && marker.chars().nth(1).map_or(false, |c| c.is_ascii_digit()) {
            let level = marker[1..].parse::<i32>().unwrap_or(1);
            let mut suffix: Option<String> = None;
            loop {
                let current_ref = (chapter.clone(), verse.clone(), suffix.clone());
                if info.q_references.iter().all(|(r, _)| r != &current_ref) {
                    info.q_references.push((current_ref, level));
                    break;
                }
                suffix = match suffix {
                    None => Some("a".to_string()),
                    Some(s) => {
                        let next_char = (s.chars().next().unwrap() as u8 + 1) as char;
                        Some(next_char.to_string())
                    }
                };
            }
        } else if matches!(marker, "s1" | "s2" | "s3" | "s4" | "d" | "r" | "qa") {
            let adj_text = text.trim().replace("\\nd ", "").replace("\\nd*", "");
            info.section_headings.push(((chapter.clone(), verse.clone()), marker.to_string(), adj_text));
        }

        if marker == "r" {
            let mut section_ref_text = text.to_string();
            if section_ref_text.starts_with('(') && section_ref_text.ends_with(')') {
                section_ref_text = section_ref_text[1..section_ref_text.len()-1].to_string();
            }
            info.section_references.push(((chapter.clone(), verse.clone()), section_ref_text));
        }

        if text.contains("wj") {
            let wj_count = text.matches("wj").count() as i32 / 2;
            let wj_first = text.starts_with("\\wj ");
            let wj_last = text.ends_with("\\wj*");
            info.words_of_jesus.push(((chapter.clone(), verse.clone()), (entry.original_marker().unwrap_or("").to_string(), wj_count, wj_first, wj_last)));
        }
    }

    info
}

/// Port of `InternalBibleBook.doCheckSFMs`.
pub fn do_check_sfms(
    entries: &InternalBibleEntryList,
    book_code: &str,
    _work_name: &str,
    discovery: &DiscoveryFlags,
    _check_usfm_sequences: bool,
) -> CheckResults {
    let mut results = CheckResults::new();

    let high_empty_field_priority = 97;
    let mut empty_field_priority = 17;
    if discovery.partly_done { empty_field_priority = 47; }
    if discovery.percentage_progress > 95.0 { empty_field_priority = 87; }
    if discovery.seems_finished { empty_field_priority = high_empty_field_priority; }

    let mut chapter = "-1".to_string();
    let mut verse = "-1".to_string();
    let mut section = markers::MarkerSection::Other;
    let mut last_marker = "".to_string();

    for entry in entries.iter() {
        let marker = entry.marker();
        assert!(!marker.is_empty(), "Entry marker should never be empty");
        let original_marker = entry.original_marker().unwrap_or("");
        let text = entry.text().unwrap_or("");
        let extras = entry.extras();
        let marker_text_empty = text.is_empty();

        if marker == "c" {
            if !text.is_empty() {
                chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            }
            verse = "0".to_string();
        } else if marker == "v" {
            if !text.is_empty() {
                verse = text.split_whitespace().next().unwrap_or(text).to_string();
            }
        } else if chapter == "-1" && !matches!(marker, "headers" | "intro") {
            if let Ok(v) = verse.parse::<i32>() {
                verse = (v + 1).to_string();
            }
        }

        let line_location = format!("{} {}:{}", book_code, chapter, verse);

        let content_type = markers::get_processed_marker_content_type(marker);
        if marker_text_empty && extras.is_none() && (content_type == markers::MarkerContentType::Always || matches!(marker, "v~" | "c~" | "c#")) {
            results.add_priority_error(empty_field_priority, book_code, &chapter, &verse, format!("Processed marker '{}' (from '{}') should always have text", marker, original_marker));
            if empty_field_priority >= high_empty_field_priority {
                results.newline_marker_errors.push(format!("{} Processed marker {:?} has no content", line_location, marker));
            } else {
                results.newline_marker_errors.push(format!("{} Processed marker {:?} should always have text", line_location, original_marker));
            }
        }

        if marker.starts_with('¬') || markers::custom_nesting::is_custom_nesting(marker) || marker == "v=" {
            continue;
        }

        let new_section = markers::marker_occurs_in(marker);
        if new_section != section {
            if section == markers::MarkerSection::Other && new_section != markers::MarkerSection::Header {
                if discovery.have_main_headings {
                    results.newline_marker_errors.push(format!("{} Missing Header section (went straight to {} section with {} marker)", line_location, new_section, marker));
                }
            } else if section != markers::MarkerSection::Other && new_section == markers::MarkerSection::Header {
                results.newline_marker_errors.push(format!("{} Didn't expect Header section after {} section (with {} marker)", line_location, section, marker));
            }
            section = new_section;
        }

        if marker == "nb" && matches!(last_marker.as_str(), "s" | "s1" | "s2" | "s3" | "s4" | "qa") {
            results.newline_marker_errors.push(format!("{} 'nb' not allowed immediately after {:?} section heading", line_location, last_marker));
        }

        if !text.is_empty() && text.contains('\\') {
            let mut hierarchy = Vec::new();
            static INT_MARKER_RE: std::sync::LazyLock<regex::Regex> = std::sync::LazyLock::new(|| {
                regex::Regex::new(r"\\(\+?[a-z1-4]{1,6}\*?)").unwrap()
            });

            for cap in INT_MARKER_RE.captures_iter(text) {
                let int_marker = cap.get(1).unwrap().as_str();
                *results.internal_marker_counts.entry(int_marker.to_string()).or_insert(0) += 1;
                if int_marker.ends_with('*') {
                    let closed_marker = &int_marker[..int_marker.len()-1];
                    let closure = markers::get_marker_closure_type(closed_marker);
                    if closure == markers::MarkerClosureType::Never {
                        results.internal_marker_errors.push(format!("{} Marker {} cannot be closed", line_location, closed_marker));
                    } else if hierarchy.last() == Some(&closed_marker) {
                        hierarchy.pop();
                    } else if hierarchy.contains(&closed_marker) {
                        results.internal_marker_errors.push(format!("{} Internal markers appear to overlap", line_location));
                    } else {
                        results.internal_marker_errors.push(format!("{} Unexpected internal closing marker: {}", line_location, int_marker));
                    }
                } else {
                    let closure = markers::get_marker_closure_type(int_marker);
                    if closure != markers::MarkerClosureType::Never {
                        hierarchy.push(int_marker);
                    }
                }
            }
            if !hierarchy.is_empty() {
                results.internal_marker_errors.push(format!("{} These markers {:?} appear not to be closed", line_location, hierarchy));
            }
        }

        last_marker = marker.to_string();
    }

    results
}

/// Port of `InternalBibleBook.doCheckSpeechMarks`.
pub fn do_check_speech_marks(
    entries: &InternalBibleEntryList,
    book_code: &str,
    opening_chars: &str,
    closing_chars: &str,
) -> CheckResults {
    let mut results = CheckResults::new();
    let mut speech_mark_errors = Vec::new();
    let mut open_speech_chars: Vec<char> = Vec::new();

    let mut chapter = "-1".to_string();
    let mut verse = "-1".to_string();

    for entry in entries.iter() {
        let marker = entry.marker();
        let text = entry.text().unwrap_or("");
        let clean_text = entry.clean_text();

        if marker == "c" {
            if !text.is_empty() {
                chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            }
            verse = "0".to_string();
        } else if marker == "v" {
            if !text.is_empty() {
                verse = text.split_whitespace().next().unwrap_or(text).to_string();
            }
        }

        let line_location = format!("{} {}:{}", book_code, chapter, verse);

        for c in clean_text.chars() {
            if opening_chars.contains(c) {
                if open_speech_chars.last() == Some(&c) {
                    speech_mark_errors.push(format!("{} Improperly nested speech marks {} after {:?}", line_location, c, open_speech_chars));
                    results.add_priority_error(55, book_code, &chapter, &verse, format!("Improperly nested speech marks {} after {:?}", c, open_speech_chars));
                }
                open_speech_chars.push(c);
            } else if closing_chars.contains(c) {
                let close_idx = closing_chars.find(c).unwrap();
                if open_speech_chars.is_empty() {
                    if c != '?' && c != '!' {
                        speech_mark_errors.push(format!("{} Unexpected {:?} speech closing character", line_location, c));
                        results.add_priority_error(52, book_code, &chapter, &verse, format!("Unexpected {:?} speech closing character", c));
                    }
                } else {
                    let last_open = open_speech_chars.last().unwrap();
                    let open_idx = opening_chars.find(*last_open).unwrap();
                    if close_idx == open_idx {
                        open_speech_chars.pop();
                    } else if c != '?' && c != '!' {
                        speech_mark_errors.push(format!("{} Mismatched {:?} speech closing character after {:?}", line_location, c, open_speech_chars));
                        results.add_priority_error(51, book_code, &chapter, &verse, format!("Mismatched {:?} speech closing character after {:?}", c, open_speech_chars));
                    }
                }
            }
        }

        if let Some(extras) = entry.extras() {
            for extra in extras.iter() {
                let mut note_open_chars = Vec::new();
                for c in extra.clean_note_text().chars() {
                    if opening_chars.contains(c) {
                        if note_open_chars.last() == Some(&c) {
                            speech_mark_errors.push(format!("{} Improperly nested speech marks {} after {:?} in note", line_location, c, note_open_chars));
                            results.add_priority_error(45, book_code, &chapter, &verse, format!("Improperly nested speech marks {} after {:?} in note", c, note_open_chars));
                        }
                        note_open_chars.push(c);
                    } else if closing_chars.contains(c) {
                        let close_idx = closing_chars.find(c).unwrap();
                        if note_open_chars.is_empty() {
                            if c != '?' && c != '!' {
                                speech_mark_errors.push(format!("{} Unexpected {:?} speech closing character in note", line_location, c));
                                results.add_priority_error(43, book_code, &chapter, &verse, format!("Unexpected {:?} speech closing character in note", c));
                            }
                        } else {
                            let last_open = note_open_chars.last().unwrap();
                            let open_idx = opening_chars.find(*last_open).unwrap();
                            if close_idx == open_idx {
                                note_open_chars.pop();
                            } else if c != '?' && c != '!' {
                                speech_mark_errors.push(format!("{} Mismatched {:?} speech closing character after {:?} in note", line_location, c, note_open_chars));
                                results.add_priority_error(42, book_code, &chapter, &verse, format!("Mismatched {:?} speech closing character after {:?} in note", c, note_open_chars));
                            }
                        }
                    }
                }
                if !note_open_chars.is_empty() {
                    speech_mark_errors.push(format!("{} Unclosed {:?} speech marks at end of note", line_location, note_open_chars));
                    results.add_priority_error(47, book_code, &chapter, &verse, format!("Unclosed {:?} speech marks at end of note", note_open_chars));
                }
            }
        }
    }

    if !open_speech_chars.is_empty() {
        results.validation_errors.push(format!("{} Unclosed {:?} speech marks at end of book", book_code, open_speech_chars));
        results.add_priority_error(54, book_code, &chapter, &verse, format!("Unclosed {:?} speech marks at end of book", open_speech_chars));
    }

    results.speech_mark_errors = speech_mark_errors;
    results
}

/// Port of `InternalBibleBook.doCheckWords`.
pub fn do_check_words(
    entries: &InternalBibleEntryList,
    book_code: &str,
    leading_punct: &str,
    trailing_punct: &str,
) -> CheckResults {
    let mut results = CheckResults::new();
    let mut word_errors = Vec::new();
    let mut last_word = String::new();
    let mut last_raw_word = String::new();

    let mut chapter = "-1".to_string();
    let mut verse = "-1".to_string();

    for entry in entries.iter() {
        let marker = entry.marker();
        let text = entry.text().unwrap_or("");
        let clean_text = entry.clean_text();

        if marker == "c" {
            if !text.is_empty() {
                chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            }
            verse = "0".to_string();
        } else if marker == "v" {
            if !text.is_empty() {
                verse = text.split_whitespace().next().unwrap_or(text).to_string();
            }
        }

        let line_location = format!("{} {}:{}", book_code, chapter, verse);

        if !clean_text.is_empty() && (marker == "v~" || marker == "p~" || markers::is_newline_marker(marker)) {
            let words = clean_text.replace('—', " ").replace('–', " ");
            for (j, raw_word) in words.split_whitespace().enumerate() {
                if (marker == "c" || marker == "v") && j == 0 && raw_word.chars().all(|c| c.is_ascii_digit()) {
                    continue;
                }

                let mut word = raw_word.to_string();
                while !word.is_empty() && leading_punct.contains(word.chars().next().unwrap()) {
                    word.remove(0);
                }
                while !word.is_empty() && trailing_punct.contains(word.chars().last().unwrap()) {
                    word.pop();
                }

                if !word.is_empty() {
                    if !word.chars().next().unwrap().is_alphanumeric() {
                        word_errors.push(format!("{} Have unexpected character starting word {:?}", line_location, word));
                    }

                    if word.to_lowercase() == last_word.to_lowercase() {
                        word_errors.push(format!("{} Have possible repeated word with {} {}", line_location, last_raw_word, raw_word));
                    }

                    last_word = word;
                    last_raw_word = raw_word.to_string();
                }
            }
        }

        if let Some(extras) = entry.extras() {
            for extra in extras.iter() {
                let note_words = extra.clean_note_text().replace('—', " ").replace('–', " ");
                for raw_word in note_words.split_whitespace() {
                    let mut word = raw_word.to_string();
                    while !word.is_empty() && leading_punct.contains(word.chars().next().unwrap()) {
                        word.remove(0);
                    }
                    while !word.is_empty() && trailing_punct.contains(word.chars().last().unwrap()) {
                        word.pop();
                    }
                }
            }
        }
    }

    results.word_errors = word_errors;
    results
}

fn has_closing_punctuation(text: &str) -> bool {
    if text.is_empty() { return false; }
    let last = text.chars().last().unwrap();
    if ".።?!".contains(last) { return true; }
    if text.len() >= 2 {
        let second_last = text.chars().nth(text.chars().count() - 2).unwrap();
        if ".።".contains(second_last) && ")]\"'\"'”’»›".contains(last) {
            return true;
        }
    }
    false
}

/// Port of `InternalBibleBook.doCheckHeadings`.
pub fn do_check_headings(
    entries: &InternalBibleEntryList,
    book_code: &str,
    _discovery: &DiscoveryFlags,
) -> CheckResults {
    let mut results = CheckResults::new();
    let mut heading_errors = Vec::new();

    let mut chapter = "-1".to_string();
    let mut verse = "-1".to_string();

    for entry in entries.iter() {
        let marker = entry.marker();
        let text = entry.text().unwrap_or("");

        if marker == "c" {
            if !text.is_empty() {
                chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            }
            verse = "0".to_string();
        } else if marker == "v" {
            if !text.is_empty() {
                verse = text.split_whitespace().next().unwrap_or(text).to_string();
            }
        }

        let line_location = format!("{} {}:{}", book_code, chapter, verse);

        if marker.starts_with("mt") {
            if text.is_empty() {
                heading_errors.push(format!("{} Missing title text for marker {}", line_location, marker));
                results.add_priority_error(59, book_code, &chapter, &verse, "Missing title text".to_string());
            } else if text.ends_with('.') || text.ends_with('።') {
                heading_errors.push(format!("{} {} title ends with a period: {}", line_location, marker, text));
                results.add_priority_error(69, book_code, &chapter, &verse, "Title ends with a period".to_string());
            }
        } else if matches!(marker, "s1" | "s2" | "s3" | "s4" | "qa") {
            if text.is_empty() {
                heading_errors.push(format!("{} Missing heading text for marker {}", line_location, marker));
                results.add_priority_error(58, book_code, &chapter, &verse, "Missing heading text".to_string());
            } else if text.ends_with('.') || text.ends_with('።') {
                heading_errors.push(format!("{} {} heading ends with a period: {}", line_location, marker, text));
                results.add_priority_error(68, book_code, &chapter, &verse, "Heading ends with a period".to_string());
            }
        } else if marker == "d" {
            if text.is_empty() {
                heading_errors.push(format!("{} Missing heading text for marker {}", line_location, marker));
                results.add_priority_error(57, book_code, &chapter, &verse, "Missing heading text".to_string());
            } else if !text.ends_with(':') && !has_closing_punctuation(text) {
                heading_errors.push(format!("{} {} heading should have closing punctuation (period): {}", line_location, marker, text));
                results.add_priority_error(67, book_code, &chapter, &verse, "Heading should have closing punctuation (period)".to_string());
            }
        }
    }

    results.heading_errors = heading_errors;
    results
}

/// Port of `InternalBibleBook.doCheckIntroduction`.
pub fn do_check_introduction(
    entries: &InternalBibleEntryList,
    book_code: &str,
) -> CheckResults {
    let mut results = CheckResults::new();
    let mut intro_errors = Vec::new();

    let mut chapter = "-1".to_string();
    let mut verse = "-1".to_string();

    for entry in entries.iter() {
        let marker = entry.marker();
        let text = entry.text().unwrap_or("");
        let clean_text = entry.clean_text();

        if marker == "c" {
            if !text.is_empty() {
                chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            }
            verse = "0".to_string();
        } else if marker == "v" {
            if !text.is_empty() {
                verse = text.split_whitespace().next().unwrap_or(text).to_string();
            }
        }

        let line_location = format!("{} {}:{}", book_code, chapter, verse);

        if matches!(marker, "imt1" | "imt2" | "imt3" | "imt4" | "is1" | "is2" | "is3" | "is4") {
            if clean_text.is_empty() {
                intro_errors.push(format!("{} Missing heading text for marker {}", line_location, marker));
                results.add_priority_error(39, book_code, &chapter, &verse, "Missing heading text".to_string());
            } else if clean_text.ends_with('.') || clean_text.ends_with('።') {
                intro_errors.push(format!("{} {} heading ends with a period: {}", line_location, marker, text));
                results.add_priority_error(49, book_code, &chapter, &verse, "Heading ends with a period".to_string());
            }
        } else if marker == "iot" {
            if clean_text.is_empty() {
                intro_errors.push(format!("{} Missing outline title text for marker {}", line_location, marker));
                results.add_priority_error(38, book_code, &chapter, &verse, "Missing outline title text".to_string());
            } else if clean_text.ends_with('.') || clean_text.ends_with('።') {
                intro_errors.push(format!("{} {} heading ends with a period: {}", line_location, marker, text));
                results.add_priority_error(48, book_code, &chapter, &verse, "Heading ends with a period".to_string());
            }
        } else if matches!(marker, "ip" | "ipi" | "im" | "imi") {
            if clean_text.is_empty() {
                intro_errors.push(format!("{} Missing introduction text for marker {}", line_location, marker));
                results.add_priority_error(36, book_code, &chapter, &verse, "Missing introduction text".to_string());
            } else if !clean_text.ends_with(':') && !has_closing_punctuation(clean_text) {
                intro_errors.push(format!("{} {} introduction text does not have closing punctuation (period): {}", line_location, marker, text));
                results.add_priority_error(46, book_code, &chapter, &verse, "Introduction text ends without closing punctuation (period)".to_string());
            }
        }
    }

    results.introduction_errors = intro_errors;
    results
}

/// Port of `InternalBibleBook.doCheckNotes`.
pub fn do_check_notes(
    entries: &InternalBibleEntryList,
    book_code: &str,
    _discovery: &DiscoveryFlags,
) -> CheckResults {
    let mut results = CheckResults::new();
    let mut footnote_errors = Vec::new();
    let mut xref_errors = Vec::new();

    let mut chapter = "-1".to_string();
    let mut verse = "-1".to_string();

    for entry in entries.iter() {
        let marker = entry.marker();
        let text = entry.text().unwrap_or("");

        if marker == "c" {
            if !text.is_empty() {
                chapter = text.split_whitespace().next().unwrap_or(text).to_string();
            }
            verse = "0".to_string();
        } else if marker == "v" {
            if !text.is_empty() {
                verse = text.split_whitespace().next().unwrap_or(text).to_string();
            }
        }

        let line_location = format!("{} {}:{}", book_code, chapter, verse);

        if let Some(extras) = entry.extras() {
            for extra in extras.iter() {
                let extra_text = extra.note_text();
                let clean_extra_text = extra.clean_note_text();
                
                // Extract markers from extra_text
                static EXTRA_INT_MARKER_RE: std::sync::LazyLock<regex::Regex> = std::sync::LazyLock::new(|| {
                    regex::Regex::new(r"\\(\+?[a-z1-4]{1,6}\*?)").unwrap()
                });
                for cap in EXTRA_INT_MARKER_RE.captures_iter(extra_text) {
                    let int_marker = cap.get(1).unwrap().as_str();
                    *results.note_marker_counts.entry(int_marker.to_string()).or_insert(0) += 1;
                }

                if matches!(extra.extra_type(), crate::markers::ExtraType::Footnote | crate::markers::ExtraType::Endnote) {
                    if clean_extra_text.ends_with(' ') {
                        footnote_errors.push(format!("{} Footnote seems to have an extra space at end: {:?}", line_location, extra_text));
                        results.add_priority_error(32, book_code, &chapter, &verse, "Extra space at end of footnote".to_string());
                    }
                } else if matches!(extra.extra_type(), crate::markers::ExtraType::CrossRef) {
                    if clean_extra_text.ends_with(' ') {
                        xref_errors.push(format!("{} Cross-reference seems to have an extra space at end: {:?}", line_location, extra_text));
                        results.add_priority_error(30, book_code, &chapter, &verse, "Extra space at end of cross-reference".to_string());
                    }
                }
            }
        }
    }

    results.note_marker_errors = footnote_errors;
    results.validation_errors = xref_errors;
    results
}

/// Port of `InternalBibleBook.doCheckCharacters`.
pub fn do_check_characters(
    _entries: &InternalBibleEntryList,
    _book_code: &str,
) -> CheckResults {
    CheckResults::default()
}

/// Main entry point for checking a Bible book in Rust.
pub fn check_book(
    entries: &InternalBibleEntryList,
    book_code: &str,
    work_name: &str,
    options: &CheckOptions,
    discovery: &DiscoveryFlags,
) -> CheckResults {
    let mut results = CheckResults::new();

    if options.check_sfms {
        let r = do_check_sfms(entries, book_code, work_name, discovery, true);
        results.newline_marker_errors.extend(r.newline_marker_errors);
        results.internal_marker_errors.extend(r.internal_marker_errors);
        results.priority_errors.extend(r.priority_errors);
    }

    if options.check_speech_marks {
        let r = do_check_speech_marks(entries, book_code, &options.opening_chars, &options.closing_chars);
        results.speech_mark_errors.extend(r.speech_mark_errors);
        results.priority_errors.extend(r.priority_errors);
        results.validation_errors.extend(r.validation_errors);
    }

    if options.check_words {
        let r = do_check_words(entries, book_code, &options.leading_punct, &options.trailing_punct);
        results.word_errors.extend(r.word_errors);
        results.priority_errors.extend(r.priority_errors);
    }

    if options.check_headings {
        let r = do_check_headings(entries, book_code, discovery);
        results.heading_errors.extend(r.heading_errors);
        results.priority_errors.extend(r.priority_errors);
    }

    if options.check_introduction {
        let r = do_check_introduction(entries, book_code);
        results.introduction_errors.extend(r.introduction_errors);
        results.priority_errors.extend(r.priority_errors);
    }

    if options.check_notes {
        let r = do_check_notes(entries, book_code, discovery);
        results.note_marker_errors.extend(r.note_marker_errors);
        results.priority_errors.extend(r.priority_errors);
        results.validation_errors.extend(r.validation_errors);
    }

    results
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use crate::processing::{process_lines, ProcessLinesOptions};
    use bos_books_codes::is_valid_reference_abbreviation;

    #[test]
    fn test_oet_lv_checking() {
        let test_folder_path = "../../Tests/DataFilesForTests/OET-LV";

        let paths = fs::read_dir(test_folder_path).expect("Could not read OET-LV folder");
        for path in paths {
            let path = path.unwrap().path();
            if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("ESFM") {
                let filename = path.file_name().unwrap().to_str().unwrap();
                // OET-LV_HAG.ESFM -> HAG
                let bos_book_code = filename.split('_').nth(1).unwrap().split('.').next().unwrap();
                if bos_book_code != "DAG" && bos_book_code != "ES1" && bos_book_code != "ES2" { // Need to sort out these OET-LV filenames
                    assert!(is_valid_reference_abbreviation(bos_book_code), "Invalid book code: {}", bos_book_code); // Not really required here, but a good test for bos_books_codes
                }
                
                let content = fs::read_to_string(&path).expect("Could not read file");
                let mut raw_lines = Vec::new();
                for line in content.lines() {
                    if line.trim().is_empty() { continue; }
                    let (marker, text) = match line.split_once(' ') {
                        Some((m, t)) => (m, t),
                        None => (line, ""),
                    };
                    let marker = marker.strip_prefix('\\').unwrap_or(marker);
                    raw_lines.push((marker.to_string(), text.to_string()));
                }

                let options = ProcessLinesOptions::default();
                let processed = process_lines(raw_lines, bos_book_code, "OET-LV", &options);

                let results = check_book(&processed, bos_book_code, "OET-LV", &CheckOptions {
                    check_sfms: true,
                    check_speech_marks: true,
                    check_words: true,
                    check_headings: true,
                    check_introduction: true,
                    check_notes: true,
                    check_added_units: true,
                    opening_chars: "“‘«‹".to_string(),
                    closing_chars: "”’»›".to_string(),
                    leading_punct: "([\"'“‘«‹".to_string(),
                    trailing_punct: ".,;:!?)]\"'”’»›".to_string(),
                }, &DiscoveryFlags {
                    have_introductory_text: true,
                    have_main_headings: true,
                    partly_done: false,
                    percentage_progress: 100.0,
                    seems_finished: true,
                });
                println!("Checked OET-LV {}: {} priority errors, {} newline marker errors, {} internal marker errors, {} speech mark errors, {} word errors, {} heading errors, {} introduction errors, {} note marker errors, {} validation errors", bos_book_code, results.priority_errors.len(), results.newline_marker_errors.len(), results.internal_marker_errors.len(), results.speech_mark_errors.len(), results.word_errors.len(), results.heading_errors.len(), results.introduction_errors.len(), results.note_marker_errors.len(), results.validation_errors.len());
                if bos_book_code == "HAG" && results.priority_errors.len() > 0 {
                    println!("Priority errors for OET-LV HAG:");
                    for error in results.priority_errors.iter() {
                        println!("  {:?}", error);
                    }
                }
            }
        }
    }

    #[test]
    fn test_oet_rv_checking() {
        let test_folder_path = "../../Tests/DataFilesForTests/OET-RV";

        let paths = fs::read_dir(test_folder_path).expect("Could not read OET-RV folder");
        for path in paths {
            let path = path.unwrap().path();
            if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("ESFM") {
                let filename = path.file_name().unwrap().to_str().unwrap();
                // OET-RV_HAG.ESFM -> HAG
                let bos_book_code = filename.split('_').nth(1).unwrap().split('.').next().unwrap();
                if bos_book_code != "DAG" && bos_book_code != "ES1" && bos_book_code != "ES2" { // Need to sort out these OET-RV filenames
                    assert!(is_valid_reference_abbreviation(bos_book_code), "Invalid book code: {}", bos_book_code); // Not really required here, but a good test for bos_books_codes
                }
                
                let content = fs::read_to_string(&path).expect("Could not read file");
                let mut raw_lines = Vec::new();
                for line in content.lines() {
                    if line.trim().is_empty() { continue; }
                    let (marker, text) = match line.split_once(' ') {
                        Some((m, t)) => (m, t),
                        None => (line, ""),
                    };
                    let marker = marker.strip_prefix('\\').unwrap_or(marker);
                    raw_lines.push((marker.to_string(), text.to_string()));
                }

                let options = ProcessLinesOptions::default();
                let processed = process_lines(raw_lines, bos_book_code, "OET-RV", &options);

                let results = check_book(&processed, bos_book_code, "OET-RV", &CheckOptions {
                    check_sfms: true,
                    check_speech_marks: true,
                    check_words: true,
                    check_headings: true,
                    check_introduction: true,
                    check_notes: true,
                    check_added_units: true,
                    opening_chars: "“‘«‹".to_string(),
                    closing_chars: "”’»›".to_string(),
                    leading_punct: "([\"'“‘«‹".to_string(),
                    trailing_punct: ".,;:!?)]\"'”’»›".to_string(),
                }, &DiscoveryFlags {
                    have_introductory_text: true,
                    have_main_headings: true,
                    partly_done: false,
                    percentage_progress: 100.0,
                    seems_finished: true,
                });
                println!("Checked OET-RV {}: {} priority errors, {} newline marker errors, {} internal marker errors, {} speech mark errors, {} word errors, {} heading errors, {} introduction errors, {} note marker errors, {} validation errors", bos_book_code, results.priority_errors.len(), results.newline_marker_errors.len(), results.internal_marker_errors.len(), results.speech_mark_errors.len(), results.word_errors.len(), results.heading_errors.len(), results.introduction_errors.len(), results.note_marker_errors.len(), results.validation_errors.len());
                if bos_book_code == "HAG" && results.priority_errors.len() > 0 {
                    println!("Priority errors for OET-RV HAG:");
                    for error in results.priority_errors.iter() {
                        println!("  {:?}", error);
                    }
                }
            }
        }
    }
}
