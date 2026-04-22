//! USFM processing logic for Bible books.
//!
//! This module handles the initial processing of raw lines into structured entries,
//! including note extraction, character fix-ups, and structural marker insertion.

use regex::Regex;
use std::sync::LazyLock;

use crate::entry::{InternalBibleEntry, InternalBibleExtra};
use crate::entry_extras::{InternalBibleEntryList, InternalBibleExtraList};
use crate::markers::ExtraType;

/// Options for processing lines.
#[derive(Debug, Clone, Copy)]
pub struct ProcessLinesOptions {
    pub replace_angle_brackets: bool,
    pub replace_straight_double_quotes: bool,
    pub strict_checking: bool,
    pub object_type: ObjectType,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ObjectType {
    Usfm2,
    Usfm3,
    Usx,
    Osis,
    Sword,
    Other,
}

impl Default for ProcessLinesOptions {
    fn default() -> Self {
        Self {
            replace_angle_brackets: true,
            replace_straight_double_quotes: false,
            strict_checking: false,
            object_type: ObjectType::Usfm3,
        }
    }
}

/// Port of Python `_processLineFix`.
///
/// Does character fixes on a specific line and moves the following out of the main text:
/// footnotes, cross-references, and figures, Strongs numbers.
pub fn process_line_fix(
    text: &str,
    chapter: &str,
    verse: &str,
    book_code: &str,
    marker: &str,
    options: &ProcessLinesOptions,
    errors: &mut Vec<String>,
) -> (String, String, InternalBibleExtraList) {
    let mut adj_text = text.to_string();
    let line_location = format!("{}_{}:{}", book_code, chapter, verse);

    // 1. Remove trailing spaces
    if adj_text.ends_with(|c: char| c.is_whitespace()) {
        let trimmed = adj_text.trim_end();
        if trimmed.len() < adj_text.len() {
            errors.push(format!(
                "{} Removed trailing space in {}: {:?}",
                line_location, marker, text
            ));
            adj_text = trimmed.to_string();
        }
    }

    // 2. Character fixes (angle brackets, quotes)
    if matches!(
        options.object_type,
        ObjectType::Usfm2 | ObjectType::Usfm3 | ObjectType::Usx
    ) && !matches!(marker, "id" | "ide" | "h" | "rem")
    {
        if options.replace_angle_brackets && (adj_text.contains('<') || adj_text.contains('>')) {
            adj_text = adj_text
                .replace("<<", "“")
                .replace(">>", "”")
                .replace('<', "‘")
                .replace('>', "’");
        }

        if options.replace_straight_double_quotes && adj_text.contains('"') {
            // Simplified replacement logic
            if adj_text.starts_with('"') {
                adj_text.replace_range(0..1, "“");
            }
            adj_text = adj_text
                .replace(" \"", " “")
                .replace(";\"", ";“")
                .replace("(\"", "(“")
                .replace("[\"", "[“")
                .replace(".\"", ".”")
                .replace(",\"", ",”")
                .replace("?\"", "?”")
                .replace("!\"", "!”")
                .replace(")\"", ")”")
                .replace("]\"", "]”")
                .replace("*\"", "*”")
                .replace("\";", "”;")
                .replace("\"(", "”(")
                .replace("\"[", "”[")
                .replace("\" ", "” ")
                .replace("\",", "”,")
                .replace("\".", "”.")
                .replace("\"?", "”?")
                .replace("\"!", "”!");
        }
    }

    // 3. Handle \w fields with attributes
    if adj_text.contains('|') {
        let mut new_adj = String::with_capacity(adj_text.len());
        let mut last_pos = 0;

        static W_RE: LazyLock<Regex> =
            LazyLock::new(|| Regex::new(r"\\(\+?w)\s+([^|]+)\|([^\\\*]+)\\(\+?w)\*").unwrap());

        for cap in W_RE.captures_iter(&adj_text) {
            let full_match = cap.get(0).unwrap();
            new_adj.push_str(&adj_text[last_pos..full_match.start()]);

            let word = &cap[2];
            let attrs = &cap[3];

            new_adj.push_str(word);
            new_adj.push_str(&format!("\\ww {}|{}\\ww*", word, attrs));

            last_pos = full_match.end();
        }
        new_adj.push_str(&adj_text[last_pos..]);
        adj_text = new_adj;
    }

    // 4. Move notes and extras to extras list
    let mut extras = InternalBibleExtraList::new();

    static EXTRA_RE: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"\\(f|fe|x|fig|str|sem|ww|vp)\s+(.*?)\\(f|fe|x|fig|str|sem|ww|vp)\*").unwrap());

    let mut final_adj = String::with_capacity(adj_text.len());
    let mut last_pos = 0;

    for cap in EXTRA_RE.captures_iter(&adj_text) {
        let full_match = cap.get(0).unwrap();
        final_adj.push_str(&adj_text[last_pos..full_match.start()]);

        let m = &cap[1];
        let content = &cap[2];

        let extra_type = match m {
            "f" => ExtraType::Footnote,
            "fe" => ExtraType::Endnote,
            "x" => ExtraType::CrossRef,
            "fig" => ExtraType::Figure,
            "str" => ExtraType::Strongs,
            "sem" => ExtraType::Semantic,
            "ww" => ExtraType::WordWithAttributes,
            "vp" => ExtraType::VersePublished,
            _ => continue,
        };

        let clean_note = content.replace(r"\ft ", "").replace(r"\xt ", "").replace(r"\fqa ", "");

        let extra = InternalBibleExtra::new_unchecked(extra_type, final_adj.len(), content, clean_note);
        extras.push(extra);

        last_pos = full_match.end();
    }
    final_adj.push_str(&adj_text[last_pos..]);

    // 5. Generate clean text by removing all markers
    let mut final_clean = final_adj.clone();
    static MARKER_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\\[a-z0-9]+\*? ?").unwrap());
    final_clean = MARKER_RE.replace_all(&final_clean, "").to_string();

    (final_adj, final_clean, extras)
}

/// Main entry point for porting Python `processLines`.
pub fn process_lines(
    raw_lines: Vec<(String, String)>,
    book_code: &str,
    work_name: &str,
    options: &ProcessLinesOptions,
) -> InternalBibleEntryList {
    let mut processed = InternalBibleEntryList::with_capacity(raw_lines.len() * 2);
    let mut chapter = "-1".to_string();
    let mut verse = "0".to_string();
    let mut have_waiting_c: Option<String> = None;
    let mut errors = Vec::new();

    for (marker, text) in raw_lines {
        let marker = marker.as_str();

        if marker == "c" {
            let c_num = text.split_whitespace().next().unwrap_or(&text).to_string();
            chapter = c_num.clone();
            verse = "0".to_string();
            have_waiting_c = Some(chapter.clone());

            if let Some(pos) = text.find(|c: char| !c.is_ascii_digit() && c != ' ') {
                let extra = &text[pos..];
                let (adj, clean, extras) =
                    process_line_fix(extra, &chapter, &verse, book_code, "c", options, &mut errors);
                processed.push(InternalBibleEntry::new_unchecked(
                    "c",
                    "c",
                    chapter.clone(),
                    chapter.clone(),
                    None,
                    chapter.clone(),
                ));
                processed.push(InternalBibleEntry::new_unchecked(
                    "c~",
                    "c",
                    adj,
                    clean,
                    Some(extras),
                    extra,
                ));
            } else {
                processed.push(InternalBibleEntry::new_unchecked(
                    "c",
                    "c",
                    chapter.clone(),
                    chapter.clone(),
                    None,
                    text,
                ));
            }
            continue;
        } else if marker == "cp" {
            have_waiting_c = Some(text.clone());
            continue;
        } else if marker == "v" {
            let mut parts = text.splitn(2, ' ');
            let v_num_str = parts.next().unwrap_or(&text).to_string();
            verse = v_num_str.clone();

            if let Some(c_num) = have_waiting_c.take() {
                processed.push(InternalBibleEntry::new_unchecked(
                    "c#",
                    "c",
                    c_num.clone(),
                    c_num.clone(),
                    None,
                    c_num,
                ));
            }

            processed.push(InternalBibleEntry::new_unchecked(
                "v",
                "v",
                verse.clone(),
                verse.clone(),
                None,
                verse.clone(),
            ));

            if let Some(v_text) = parts.next() {
                let (adj, clean, extras) =
                    process_line_fix(v_text, &chapter, &verse, book_code, "v", options, &mut errors);
                processed.push(InternalBibleEntry::new_unchecked(
                    "v~",
                    "v",
                    adj,
                    clean,
                    Some(extras),
                    v_text,
                ));
            }
            continue;
        } else if matches!(marker, "d" | "iex") && have_waiting_c.is_some() {
            let c_num = have_waiting_c.take().unwrap();
            processed.push(InternalBibleEntry::new_unchecked(
                "c#",
                "c",
                c_num.clone(),
                c_num.clone(),
                None,
                c_num,
            ));
        } else if marker == "cl" && chapter == "-1" {
            let (adj, clean, extras) =
                process_line_fix(&text, &chapter, &verse, book_code, marker, options, &mut errors);
            processed.push(InternalBibleEntry::new_unchecked(
                "cl¤",
                marker,
                adj,
                clean,
                Some(extras),
                text,
            ));
            continue;
        }

        let (adj, clean, extras) = process_line_fix(&text, &chapter, &verse, book_code, marker, options, &mut errors);

        if (marker == "b" || crate::markers::paragraph_markers::is_paragraph(marker)) && !clean.is_empty() {
            processed.push(InternalBibleEntry::new_unchecked(marker, marker, "", "", None, ""));
            processed.push(InternalBibleEntry::new_unchecked(
                "p~",
                marker,
                adj,
                clean,
                Some(extras),
                text,
            ));
        } else {
            processed.push(InternalBibleEntry::new_unchecked(
                marker,
                marker,
                adj,
                clean,
                Some(extras),
                text,
            ));
        }
    }

    let nested = crate::nesting::add_nesting_markers(processed, work_name, book_code);
    crate::nesting::add_verse_start_markers(nested)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::File;
    use std::io::{BufRead, BufReader};

    #[test]
    fn test_process_lines_haggai() {
        let file_path = "src/indexes/OET-RV_HAG.ESFM";
        let file = File::open(file_path).expect("Could not open Haggai ESFM file");
        let reader = BufReader::new(file);

        let mut raw_lines = Vec::new();
        for line in reader.lines() {
            let line = line.expect("Could not read line");
            if line.trim().is_empty() {
                continue;
            }
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line.as_str(), ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);
            raw_lines.push((marker.to_string(), text.to_string()));
        }

        let options = ProcessLinesOptions::default();
        let processed = process_lines(raw_lines, "HAG", "OET-RV", &options);

        println!("Processed {} entries", processed.len());
        assert!(processed.len() >= 183);

        // Check some specific entries
        // Entry 0 should be \id
        assert_eq!(processed[0].marker(), "id");

        // Find chapter 1 start
        let c1_idx = processed.contains_marker("c", None).expect("Should find chapter 1");
        assert_eq!(processed[c1_idx].clean_text(), "1");
    }
}
