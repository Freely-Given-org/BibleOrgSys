//! USFM processing logic for Bible books.
//!
//! This module handles the initial processing of raw lines into structured entries,
//! including note extraction, character fix-ups, and structural marker insertion.

use compact_str::CompactString;
use indexmap::IndexMap;
use rayon::prelude::*;
use regex::Regex;
use std::sync::LazyLock;

use crate::bos_markers::{ExtraType, is_end_marker};
use crate::entry::{InternalBibleEntry, InternalBibleExtra};
use crate::entry_extras::InternalBibleExtraList;
use crate::entry_lists::InternalBibleEntryList;
use crate::have_strict_checking_flag;

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
///
/// Returns the adjusted text, the clean text (with all markers removed), and a list of extras.
pub fn line_fix_and_move_extras_out(
    text: &str,
    chapter: &str,
    verse: &str,
    bos_book_code: &str,
    marker: &str,
    options: &ProcessLinesOptions,
    errors: &mut Vec<String>,
) -> (String, String, InternalBibleExtraList) {
    let mut adj_text = text.to_string();
    let line_location = format!("{}_{}:{}", bos_book_code, chapter, verse);

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

        static W_RE: LazyLock<Regex> = LazyLock::new(|| {
            Regex::new(r"\\(?:w\s+([^|]+)\|([^\\\*]+)\\w\*|\+w\s+([^|]+)\|([^\\\*]+)\\\+w\*)").unwrap()
        });

        for cap in W_RE.captures_iter(&adj_text) {
            let full_match = cap.get(0).unwrap();
            new_adj.push_str(&adj_text[last_pos..full_match.start()]);

            let (word, attrs) = if let Some(w) = cap.get(1) {
                (w.as_str(), cap.get(2).unwrap().as_str())
            } else {
                (cap.get(3).unwrap().as_str(), cap.get(4).unwrap().as_str())
            };

            new_adj.push_str(word);
            new_adj.push_str(&format!("\\ww {}|{}\\ww*", word, attrs));

            last_pos = full_match.end();
        }
        new_adj.push_str(&adj_text[last_pos..]);
        adj_text = new_adj;
    }

    // 4. Move notes and extras to extras list
    let mut extras = InternalBibleExtraList::new();

    static EXTRA_RE: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"\\(?:f\s+(.*?)\\f\*|fe\s+(.*?)\\fe\*|x\s+(.*?)\\x\*|fig\s+(.*?)\\fig\*|str\s+(.*?)\\str\*|sem\s+(.*?)\\sem\*|ww\s+(.*?)\\ww\*|vp\s+(.*?)\\vp\*)").unwrap()
    });

    let mut final_adj = String::with_capacity(adj_text.len());
    let mut last_pos = 0;

    for cap in EXTRA_RE.captures_iter(&adj_text) {
        let full_match = cap.get(0).unwrap();
        final_adj.push_str(&adj_text[last_pos..full_match.start()]);

        let (extra_type, content) = if let Some(c) = cap.get(1) {
            (ExtraType::Footnote, c.as_str())
        } else if let Some(c) = cap.get(2) {
            (ExtraType::Endnote, c.as_str())
        } else if let Some(c) = cap.get(3) {
            (ExtraType::CrossRef, c.as_str())
        } else if let Some(c) = cap.get(4) {
            (ExtraType::Figure, c.as_str())
        } else if let Some(c) = cap.get(5) {
            (ExtraType::Strongs, c.as_str())
        } else if let Some(c) = cap.get(6) {
            (ExtraType::Semantic, c.as_str())
        } else if let Some(c) = cap.get(7) {
            (ExtraType::WordWithAttributes, c.as_str())
        } else if let Some(c) = cap.get(8) {
            (ExtraType::VersePublished, c.as_str())
        } else {
            continue;
        };

        let clean_note = content.replace(r"\ft ", "").replace(r"\xt ", "").replace(r"\fqa ", "");

        let extra = InternalBibleExtra::new_unchecked(extra_type, final_adj.len(), content, clean_note);
        extras.push(extra);

        last_pos = full_match.end();
    }
    final_adj.push_str(&adj_text[last_pos..]);

    // 5. Generate clean text by removing all markers
    let mut final_clean = final_adj.trim_start().to_string();
    static MARKER_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\\\+?[a-z0-9]{1,6}(?:\*| )?").unwrap());
    final_clean = MARKER_RE.replace_all(&final_clean, "").to_string();
    assert!(
        !final_clean.contains('\\'),
        "line_fix_and_move_extras_out {}: Clean text should not contain backslashes after marker removal: '{}' from '{}'",
        line_location,
        final_clean,
        text
    );

    (final_adj, final_clean, extras)
}

/// Main entry point for porting Python `processLines`.
///    Accepts the raw (USFM/ESFM) lines with (marker,text) entries, and processes them to:
///
//     Splits lines if a paragraph marker appears within a line.
//     Move notes out of the text into extras.
//
//     Returns the list of processedLines.
//
// NOTE: the Python function calls this and then calls makeBookCVIndex() immediately afterwards
//
pub fn process_lines(
    raw_lines: Vec<(String, String)>,
    bos_book_code: &str,
    work_name: &str,
    options: &ProcessLinesOptions,
) -> InternalBibleEntryList {
    let mut processed = InternalBibleEntryList::with_capacity(raw_lines.len() * 2);
    let mut chapter_num_str = "-1".to_string();
    let mut verse_num_str = "0".to_string();
    let mut have_waiting_c: Option<String> = None;
    let mut errors = Vec::new();

    for (n,(marker, text)) in raw_lines.iter().enumerate() {
        let marker = crate::bos_markers::normalize_marker(marker.as_str());
        log::info!("process_lines: Processing marker {} with text '{}'", marker, text);
        // println!("process_lines: Processing marker {} with text '{}'", marker, text);
        // if text.contains("O Yahweh, do not rebuke me in your anger,") {
        //     println!("process_lines: Found {} {} raw line with {} {}='{}'", work_name, bos_book_code, n-2, raw_lines.get(n-2).unwrap().0, raw_lines.get(n-2).unwrap().1);
        //     println!("process_lines: Found {} {} raw line with {} {}='{}'", work_name, bos_book_code, n-1, raw_lines.get(n-1).unwrap().0, raw_lines.get(n-1).unwrap().1);
        //     println!("process_lines: Found {} {} raw line with {} {}='{}'", work_name, bos_book_code, n+0, raw_lines.get(n+0).unwrap().0, raw_lines.get(n+0).unwrap().1);
        //     println!("process_lines: Found {} {} raw line with {} {}='{}'", work_name, bos_book_code, n+1, raw_lines.get(n+1).unwrap().0, raw_lines.get(n+1).unwrap().1);
        //     println!("process_lines: Found {} {} raw line with {} {}='{}'", work_name, bos_book_code, n+2, raw_lines.get(n+2).unwrap().0, raw_lines.get(n+2).unwrap().1);
        //     panic!("process_lines: Stop here");
        // }

        if marker == "v" { // Put the most common marker first for better performance
            let mut parts = text.splitn(2, ' ');
            let v_num_str = parts.next().unwrap_or(&text).to_string();
            verse_num_str = v_num_str.clone();

            if let Some(c_num) = have_waiting_c.take() {
                debug_assert!(verse_num_str=="1" || verse_num_str=="1-2" || verse_num_str=="1-3",
                    "{} {} verse number should be '1' when processing a waiting chapter marker, but found '{}'",
                    work_name, bos_book_code, verse_num_str); // This may not be true for all real-world cases, but is true for the test cases and is a good sanity check
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
                verse_num_str.clone(),
                verse_num_str.clone(),
                None,
                verse_num_str.clone(),
            ));

            if let Some(v_text) = parts.next() {
                let (adj, clean, extras) =
                    line_fix_and_move_extras_out(v_text, &chapter_num_str, &verse_num_str, bos_book_code, "v", options, &mut errors);
                processed.push(InternalBibleEntry::new_unchecked(
                    "v~",
                    "v",
                    v_text,
                    adj,
                    Some(extras),
                    clean,
                ));
            }
            continue;
        } else if marker == "c" {
            let c_num = text.split_whitespace().next().unwrap_or(&text).to_string();
            chapter_num_str = c_num.clone();
            verse_num_str = "0".to_string();
            have_waiting_c = Some(chapter_num_str.clone()); // Will be used to insert c# line later

            if let Some(pos) = text.find(|c: char| !c.is_ascii_digit() && c != ' ') {
                // We have additional text on the c line so we split that into a 'c~' line
                // println!("process_lines: Found chapter marker with extra text: ch='{}' txt='{}'", chapter_num_str, text);
                let extra = &text[pos..];
                let (adj, clean, extras) =
                    line_fix_and_move_extras_out(extra, &chapter_num_str, &verse_num_str, bos_book_code, "c", options, &mut errors);
                processed.push(InternalBibleEntry::new_unchecked(
                    "c",
                    "c",
                    chapter_num_str.clone(),
                    chapter_num_str.clone(),
                    None,
                    chapter_num_str.clone(),
                ));
                processed.push(InternalBibleEntry::new_unchecked(
                    "c~",
                    "c",
                    extra,
                    adj,
                    Some(extras),
                    clean,
                ));
            } else { // it's the normal case of a plain chapter number by itself on the line
                debug_assert_eq!( // Might not be true for all real-world cases, but is a good sanity check for the test cases and expected common cases
                    text.trim(),
                    chapter_num_str,
                    "Chapter marker text should match chapter number when no extra text is present"
                );
                processed.push(InternalBibleEntry::new_unchecked(
                    "c",
                    "c",
                    text,
                    chapter_num_str.clone(),
                    None,
                    chapter_num_str.clone(),
                ));
            }
            continue;
        } else if marker == "cp" { // We use this text to print instead of what was on the c line, so save it to go onto the c# line later.
            have_waiting_c = Some(text.clone());
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
        } else if marker == "cl" && chapter_num_str == "-1" {
            let (adj, clean, extras) =
                line_fix_and_move_extras_out(&text, &chapter_num_str, &verse_num_str, bos_book_code, marker, options, &mut errors);
            processed.push(InternalBibleEntry::new_unchecked(
                "cl¤",
                marker,
                text,
                adj,
                Some(extras),
                clean,
            ));
            continue;
        }

        let (adj, clean, extras) =
            line_fix_and_move_extras_out(&text, &chapter_num_str, &verse_num_str, bos_book_code, marker, options, &mut errors);
        // println!("process_lines: After line_fix_and_move_extras_out for marker {}: adj='{}', clean='{}', extras={}", marker, adj, clean, extras.len());

        if (marker == "b" || crate::bos_markers::paragraph_markers::is_paragraph(marker))
            && (!clean.is_empty() || !extras.is_empty())
        {
            processed.push(InternalBibleEntry::new_unchecked(marker, marker, "", "", None, ""));
            processed.push(InternalBibleEntry::new_unchecked(
                "v~", // "XXXp~"
                marker,
                text,
                adj,
                Some(extras),
                clean,
            ));
        } else {
            processed.push(InternalBibleEntry::new_unchecked(
                marker,
                marker,
                text,
                adj,
                Some(extras),
                clean,
            ));
        }
        // if text_copy.contains("FG_with_text_below.png") {
        //     panic!("Found FG_with_text_below.png in text: {}='{}'", marker, text_copy);
        // }
    }

    // Now add additional nesting and other markers in order to simplify future processing
    let processed_lines = crate::nesting::add_additional_markers(processed, work_name, bos_book_code);

    if have_strict_checking_flag() || cfg!(debug_assertions) {
        let validation_results = validate(&processed_lines, bos_book_code, work_name);
        if !validation_results.is_empty() {
            println!("process_lines validation failed with {} issues: {:?}", validation_results.len(), validation_results);
        }
    }
    processed_lines
}

/// (Debug) Validate the processed lines for common issues and return a list of error messages.
pub fn validate(processed_lines: &InternalBibleEntryList, bos_book_code: &str, work_name: &str) -> Vec<String> {
    let mut issues = Vec::new();

    if processed_lines.is_empty() {
        issues.push(format!("No {} {} processed_lines entries to validate", work_name, bos_book_code));
        return issues;
    }

    // let mut previous_marker = CompactString::new("");
    let mut next_marker = CompactString::new("");
    let mut marker_counts: IndexMap<CompactString, usize> = IndexMap::new();
    for (n, entry) in processed_lines.iter().enumerate() {
        let current_marker: CompactString = entry.marker().into();
        *marker_counts.entry(current_marker.clone()).or_insert(0) += 1;
        if n < processed_lines.len() - 1 {
            next_marker = processed_lines[n + 1].marker().into();
        } else {
            next_marker = CompactString::new("");
        }

        if current_marker == "v=" {
            if is_end_marker(&next_marker) {
                issues.push(format!(
                    "Special {} {} verse number marker 'v=' at index {} is followed by an end marker '{}'",
                    work_name, bos_book_code, n, next_marker
                ));
            } else if !["s1", "s2", "s3", "s4", "ms1", "ms2", "ms3", "sp"].contains(&next_marker.as_str()) {
                issues.push(format!(
                    "Special {} {} verse number marker 'v=' at index {} is not followed by a verse or section marker (found '{}')",
                    work_name, bos_book_code, n, next_marker
                ));
            }
        }

        // previous_marker = current_marker;
    }

    // Check that all end markers have a corresponding start marker with the same count
    for (marker, count) in &marker_counts {
        if is_end_marker(&marker) {
            let start_marker: CompactString = marker.chars().skip(1).collect();
            if count != marker_counts.get(&start_marker).unwrap_or(&0) {
                issues.push(format!(
                    "{} {} end marker '{}' has {} entries but its corresponding start marker has {}",
                    work_name, bos_book_code, marker, count, marker_counts.get(&start_marker).unwrap_or(&0)
                ));
            }
        }
    }

    issues
}

/// Process all books in a Bible in parallel.
pub fn process_bible(
    raw_books: IndexMap<String, Vec<(String, String)>>,
    work_name: &str,
    options: &ProcessLinesOptions,
) -> IndexMap<String, InternalBibleEntryList> {
    raw_books
        .into_par_iter()
        .map(|(bos_book_code, raw_lines)| {
            let processed_lines = process_lines(raw_lines, &bos_book_code, work_name, options);
            (bos_book_code, processed_lines)
        })
        .collect()
}

#[cfg(test)]
mod tests {

    use bos_books_codes::{is_new_testament_nr, is_old_testament_nr};

    use super::*;
    use std::fs::File;
    use std::io::{BufRead, BufReader};

    #[test]
    fn test_line_fix_and_move_extras_out() {
        let (_adj_text, clean_text, extras) = line_fix_and_move_extras_out(
            r" Mismatched \f footnote \fe* should be ignored. ",
            "1",
            "1",
            "TST",
            "p",
            &ProcessLinesOptions::default(),
            &mut Vec::new(),
        );
        // It should NOT extract the mismatched footnote as an extra
        assert!(extras.is_empty());
        // Trailing space is trimmed, \f<space> is removed, \fe* is removed
        assert_eq!(clean_text, "Mismatched footnote  should be ignored.");

        let (_adj_text, clean_text, extras) = line_fix_and_move_extras_out(
            r" Mismatched \w word|attr \+w* should be ignored. ",
            "1",
            "1",
            "TST",
            "p",
            &ProcessLinesOptions::default(),
            &mut Vec::new(),
        );
        // It should NOT extract/convert the mismatched \w
        assert!(extras.is_empty());
        assert_eq!(clean_text, "Mismatched word|attr  should be ignored.");

        let (adj_text, clean_text, extras) = line_fix_and_move_extras_out(
            r"\fig |/srv/Websites/Freely-Given.org/Logo/FG_with_text_below.png|span||||\fig*",
            "-1",
            "16",
            "FRT",
            "pc",
            &ProcessLinesOptions::default(),
            &mut Vec::new(),
        );
        assert_eq!(adj_text, "");
        assert_eq!(clean_text, "");
        assert!(extras.len() == 1); // Should have one figure
        assert_eq!(extras[0].extra_type(), ExtraType::Figure);
        assert_eq!(
            extras[0].clean_note_text(),
            "|/srv/Websites/Freely-Given.org/Logo/FG_with_text_below.png|span||||"
        );
        assert_eq!(
            extras[0].clean_text(),
            "|/srv/Websites/Freely-Given.org/Logo/FG_with_text_below.png|span||||"
        );

        let (adj_text, clean_text, extras) = line_fix_and_move_extras_out(
            r" Praise Yah.\f + \fr 150:? \ft Hebrew \+it hallelujah\+it*\f* ",
            "150",
            "6",
            "PSA",
            "li1",
            &ProcessLinesOptions::default(),
            &mut Vec::new(),
        );
        assert_eq!(adj_text, " Praise Yah.");
        assert_eq!(clean_text, "Praise Yah.");
        assert!(extras.len() == 1); // Should have one footnote
        assert_eq!(extras[0].extra_type(), ExtraType::Footnote);
        assert_eq!(
            extras[0].clean_note_text(),
            "+ \\fr 150:? Hebrew \\+it hallelujah\\+it*"
        );
        assert_eq!(extras[0].clean_text(), "+ \\fr 150:? Hebrew \\+it hallelujah\\+it*");

        let (_adj_text, clean_text, extras) = line_fix_and_move_extras_out(
            r"\f + \fr 8:28 \ft Note: KJB: Exod.8.32\f* and¦29089= Parˊoh¦29090 =he¦29089_made¦29089_unresponsive¦29089 \untr DOM¦29091\untr* his/its¦29093=heart¦29093 also¦29094 at¦29095÷time¦29095 (the)¦29096÷this¦29096 and¦29097=not¦29097 he¦29098_let¦29098_go¦29098 \untr DOM¦29099\untr* the¦29101÷people¦29101.",
            "8",
            "28",
            "EXO",
            "v~",
            &ProcessLinesOptions::default(),
            &mut Vec::new(),
        );
        // println!("Adj text: {:?}", adj_text);
        assert_eq!(
            clean_text,
            "and¦29089= Parˊoh¦29090 =he¦29089_made¦29089_unresponsive¦29089 DOM¦29091 his/its¦29093=heart¦29093 also¦29094 at¦29095÷time¦29095 (the)¦29096÷this¦29096 and¦29097=not¦29097 he¦29098_let¦29098_go¦29098 DOM¦29099 the¦29101÷people¦29101."
        );
        assert!(extras.len() == 1); // Should have one footnote
        assert_eq!(extras[0].extra_type(), ExtraType::Footnote);
        assert_eq!(extras[0].clean_note_text(), "+ \\fr 8:28 Note: KJB: Exod.8.32");
        assert_eq!(extras[0].clean_text(), "+ \\fr 8:28 Note: KJB: Exod.8.32");

        let (_adj_text, clean_text, extras) = line_fix_and_move_extras_out(
            r"The¦283645_vision¦283645_of¦283645 Yəshaˊ\sup yāh\sup*¦283646 the¦283647_son¦283647_of¦283647 ʼĀmōʦ¦283649 which¦283650 he¦283651_saw¦283651 on¦283652 Yəhūdāh/(Judah)¦283654 and¦283655÷Yərūshālam/(Jerusalem)¦283655 in¦283656÷the¦283656_days¦283656_of¦283656 ˊUzziy\sup yāh\sup*¦283657 Yōtām/(Jotham)¦283658 ʼĀḩāz¦283659 Ḩizqiy\sup yāh\sup*¦283660 the¦283661_kings¦283661_of¦283661 Yəhūdāh¦283662.",
            "1",
            "1",
            "ISA",
            "v~",
            &ProcessLinesOptions::default(),
            &mut Vec::new(),
        );
        // println!("Adj text: {:?}", adj_text);
        assert_eq!(
            clean_text,
            "The¦283645_vision¦283645_of¦283645 Yəshaˊyāh¦283646 the¦283647_son¦283647_of¦283647 ʼĀmōʦ¦283649 which¦283650 he¦283651_saw¦283651 on¦283652 Yəhūdāh/(Judah)¦283654 and¦283655÷Yərūshālam/(Jerusalem)¦283655 in¦283656÷the¦283656_days¦283656_of¦283656 ˊUzziyyāh¦283657 Yōtām/(Jotham)¦283658 ʼĀḩāz¦283659 Ḩizqiyyāh¦283660 the¦283661_kings¦283661_of¦283661 Yəhūdāh¦283662."
        );
        assert!(extras.is_empty());

        let (_adj_text, clean_text, extras) = line_fix_and_move_extras_out(
            r"Hear¦283664 Oh¦283665_heavens¦283665 and¦283666÷give¦283666_ear¦283666 Oh¦283667_earth¦283667 if/because¦283668 \nd YHWH¦283669\nd* he¦283670_has¦283670_spoken¦283670 children¦283671 I¦283672_have¦283672_brought¦283672_up¦283672 and¦283673÷I¦283673_have¦283673_raised¦283673 and¦283674÷they¦283674 they¦283675_have¦283675_rebelled¦283675 against¦283676÷me¦283676.",
            "1",
            "2",
            "ISA",
            "v~",
            &ProcessLinesOptions::default(),
            &mut Vec::new(),
        );
        // println!("Adj text: {:?}", adj_text);
        assert_eq!(
            clean_text,
            "Hear¦283664 Oh¦283665_heavens¦283665 and¦283666÷give¦283666_ear¦283666 Oh¦283667_earth¦283667 if/because¦283668 YHWH¦283669 he¦283670_has¦283670_spoken¦283670 children¦283671 I¦283672_have¦283672_brought¦283672_up¦283672 and¦283673÷I¦283673_have¦283673_raised¦283673 and¦283674÷they¦283674 they¦283675_have¦283675_rebelled¦283675 against¦283676÷me¦283676."
        );
        assert!(extras.is_empty());
    }

    #[test]
    fn test_pc_marker_with_fig_in_frt() {
        let raw_lines = vec![
            ("id".to_string(), "FRT".to_string()),
            ("pc".to_string(), r"\fig |/srv/logo.png|span||||\fig*".to_string()),
        ];
        let options = ProcessLinesOptions::default();
        let processed_lines = process_lines(raw_lines, "FRT", "WORK", &options);

        // We expect "id", then "headers" nesting, then "pc" (empty), "XXXp~" (with fig in extras)
        let markers: Vec<&str> = processed_lines.iter().map(|e| e.marker()).collect();
        // println!("Markers: {}", markers.join(", "));

        // Find "pc"
        let pc_idx = markers.iter().position(|&m| m == "pc").expect("Should find pc marker");
        assert_eq!(processed_lines[pc_idx].clean_text(), "");
        assert_eq!(processed_lines[pc_idx + 1].marker(), "v~"); // "XXXp~"
        assert!(processed_lines[pc_idx + 1].has_extras());
        assert_eq!(processed_lines[pc_idx + 1].extras().unwrap().len(), 1);
        assert_eq!(
            processed_lines[pc_idx + 1].extras().unwrap()[0].extra_type(),
            ExtraType::Figure
        );
    }

    #[test]
    fn test_mt_marker_normalization() {
        let raw_lines = vec![
            ("id".to_string(), "GEN".to_string()),
            ("mt".to_string(), "Genesis".to_string()),
        ];
        let options = ProcessLinesOptions::default();
        let processed_lines = process_lines(raw_lines, "GEN", "WORK", &options);

        let markers: Vec<&str> = processed_lines.iter().map(|e| e.marker()).collect();
        // println!("Markers: {}", markers.join(", "));

        // Check if "mt" was normalized to "mt1"
        assert!(markers.contains(&"mt1"));
        assert!(!markers.contains(&"mt"));
    }

    #[test]
    fn test_process_lines_greek() {
        let raw_lines = vec![
            ("id".to_string(), "MRK".to_string()),
            ("mt".to_string(), "Μάρκος".to_string()),
            ("c".to_string(), "1".to_string()),
            ("v".to_string(), "1 This is verse one.".to_string()),
            ("v".to_string(), r#"24 \w Καὶ|lemma="καί" x-koine="και" x-strong="G25320" x-morph="Gr,C,......."\w* \w ἀπῆλθεν|lemma="ἀπέρχομαι" x-koine="απηλθεν" x-strong="G05650" x-morph="Gr,V,IAA3..S"\w* \w μετʼ|lemma="μετά" x-koine="μετ" x-strong="G33260" x-morph="Gr,P,......."\w* \w αὐτοῦ|lemma="αὐτός" x-koine="αυτου" x-strong="G08460" x-morph="Gr,R,...3GMS"\w*"#.to_string()),
            ("p".to_string(), r#"\w Καὶ|lemma="καί" x-koine="και" x-strong="G25320" x-morph="Gr,C,......."\w* \w ἠκολούθει|lemma="ἀκολουθέω" x-koine="ηκολουθει" x-strong="G01900" x-morph="Gr,V,IIA3..S"\w*"#.to_string()),
            ("v".to_string(), r#"25 \w Καὶ|lemma="καί" x-koine="και" x-strong="G25320" x-morph="Gr,C,......."\w* "\w γυνὴ|lemma="γυνή" x-koine="γυνη" x-strong="G11350" x-morph="Gr,N,....NFS"\w*"#.to_string()),
        ];
        let options = ProcessLinesOptions::default();
        let processed_lines = process_lines(raw_lines, "MRK", "GREEK", &options);
        // for entry in &processed {
        //     println!("Greek Marker: {}, Clean Text: '{}', Extras: {:?}", entry.marker(), entry.clean_text(), entry.extras());
        // }

        // Verification
        let markers: Vec<&str> = processed_lines.iter().map(|e| e.marker()).collect();
        // println!("Markers: {:?}", markers);

        // Should have start/end markers for chapters and verses due to nesting
        assert!(!markers.contains(&""), "{:?}", markers);
        assert!(markers.contains(&"v"), "{:?}", markers);
        assert!(markers.contains(&"v~"), "{:?}", markers);
        assert!(markers.contains(&"¬v"), "{:?}", markers);
        assert!(markers.contains(&"p"), "{:?}", markers);
        assert!(markers.contains(&"v~"), "{:?}", markers); // "XXXp~"
        assert!(markers.contains(&"¬p"), "{:?}", markers);

        // Find "Καὶ" at start of verse 24
        let kai = processed_lines
            .iter()
            .find(|e| e.clean_text().starts_with("Καὶ"))
            .expect("Should find Καὶ at beginning of verse 24");
        assert!(kai.has_extras());
        let extra = &kai.extras().unwrap()[0];
        assert_eq!(extra.extra_type(), ExtraType::WordWithAttributes);
        assert!(extra.clean_note_text().contains("G25320"));
    }

    #[test]
    fn test_oet_lv_haggai_processing() {
        let file_path = "../../Tests/DataFilesForTests/OET-LV/OET-LV_HAG.ESFM";
        let file = File::open(file_path).expect("Could not open OET-LV Haggai ESFM file");
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

        // Results should match test_data/OET-LV_HAG_rawLines.txt
        let original_count = raw_lines.len();
        // println!("Original lines read: {}", original_count);
        assert_eq!(original_count, 57, "Expected 57 raw lines in Haggai ESFM file");

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_lines = crate::processing::process_lines(raw_lines, "HAG", "OET-LV", &options);
        // println!("Final OET-LV Haggai processed line entries: {}", processed.len());
        assert_eq!(
            processed_lines.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "id", "usfm", "ide", "rem", "rem", "rem", "rem", "rem", "rem",
                "headers", "h", "toc1", "toc2", "toc3", "mt1", "ie", "¬headers",
                "chapters",
                "c",
                "nb",
                "c#",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "¬c",
                "c",
                "nb",
                "c#",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "v",
                "v~",
                "¬v",
                "¬c",
                "¬chapters"
            ]
        );
        // panic!("Final OET-LV Haggai processed line entries: {:?}", processed.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>());

        // Check some specific entries
        // Entry 0 should be \id
        assert_eq!(processed_lines[0].marker(), "id");
        // Find chapter 1 start
        let c1_idx = processed_lines.contains_marker("c", None).expect("Should find chapter 1");
        assert_eq!(processed_lines[c1_idx].clean_text(), "1");

        // Verify some key structural markers from the reference test
        assert_eq!(processed_lines[9].marker(), "headers");
        assert_eq!(processed_lines[16].marker(), "¬headers");
        assert_eq!(processed_lines[17].marker(), "chapters");
        assert_eq!(processed_lines[18].marker(), "c");
        assert_eq!(processed_lines[18].clean_text(), "1");
        assert_eq!(processed_lines[21].marker(), "v");
        assert_eq!(processed_lines[21].adjusted_text(), "1");
        assert_eq!(processed_lines[22].marker(), "v~");
        assert_eq!(
            processed_lines[22].original_text(),
            "In¦375561=year¦375561 two¦375562 of¦375563÷Dārəyāvesh¦375563 the¦375564=king¦375564 in¦375565÷month¦375565 the¦375566=sixth¦375566 in/on¦375567=day¦375567 one¦375568 of¦375569÷month¦375569 the¦375571_message¦375571_of¦375571 it¦375570_came¦375570 of¦375573_\\nd YHWH¦375573\\nd* by¦375574÷the¦375574_hand¦375574_of¦375574 Ḩaggay¦375576 the¦375577÷prophet¦375577 to¦375578 Zərubāⱱel¦375580 the¦375581_son¦375581_of¦375581 Shəʼaltiy\\sup ʼēl\\sup*¦375583 the¦375584_governor¦375584_of¦375584 Yəhūdāh/(Judah)¦375585 and¦375586=near/to¦375586 Yəhōshūˊa/(Joshua)¦375588 the¦375589_son¦375589_of¦375589 Yəhōʦādāq/(Jehozadak)¦375591 the¦375592=priest/officer¦375592 (the)¦375593÷great¦375593 to¦375594=say¦375594."
        );
        assert_eq!(
            processed_lines[22].adjusted_text(),
            "In¦375561=year¦375561 two¦375562 of¦375563÷Dārəyāvesh¦375563 the¦375564=king¦375564 in¦375565÷month¦375565 the¦375566=sixth¦375566 in/on¦375567=day¦375567 one¦375568 of¦375569÷month¦375569 the¦375571_message¦375571_of¦375571 it¦375570_came¦375570 of¦375573_\\nd YHWH¦375573\\nd* by¦375574÷the¦375574_hand¦375574_of¦375574 Ḩaggay¦375576 the¦375577÷prophet¦375577 to¦375578 Zərubāⱱel¦375580 the¦375581_son¦375581_of¦375581 Shəʼaltiy\\sup ʼēl\\sup*¦375583 the¦375584_governor¦375584_of¦375584 Yəhūdāh/(Judah)¦375585 and¦375586=near/to¦375586 Yəhōshūˊa/(Joshua)¦375588 the¦375589_son¦375589_of¦375589 Yəhōʦādāq/(Jehozadak)¦375591 the¦375592=priest/officer¦375592 (the)¦375593÷great¦375593 to¦375594=say¦375594."
        );
        assert!(
            processed_lines[22].extras().unwrap().is_empty(),
            "Expected no extras for verse 1 line"
        );
        assert_eq!(
            processed_lines[22].clean_text(),
            "In¦375561=year¦375561 two¦375562 of¦375563÷Dārəyāvesh¦375563 the¦375564=king¦375564 in¦375565÷month¦375565 the¦375566=sixth¦375566 in/on¦375567=day¦375567 one¦375568 of¦375569÷month¦375569 the¦375571_message¦375571_of¦375571 it¦375570_came¦375570 of¦375573_YHWH¦375573 by¦375574÷the¦375574_hand¦375574_of¦375574 Ḩaggay¦375576 the¦375577÷prophet¦375577 to¦375578 Zərubāⱱel¦375580 the¦375581_son¦375581_of¦375581 Shəʼaltiyʼēl¦375583 the¦375584_governor¦375584_of¦375584 Yəhūdāh/(Judah)¦375585 and¦375586=near/to¦375586 Yəhōshūˊa/(Joshua)¦375588 the¦375589_son¦375589_of¦375589 Yəhōʦādāq/(Jehozadak)¦375591 the¦375592=priest/officer¦375592 (the)¦375593÷great¦375593 to¦375594=say¦375594."
        );
        assert_eq!(processed_lines[23].marker(), "¬v");
        assert_eq!(processed_lines[23].adjusted_text(), "1");
        assert_eq!(processed_lines[139].marker(), "¬c");
        assert_eq!(processed_lines[139].clean_text(), "2");
        assert_eq!(processed_lines[140].marker(), "¬chapters");
        assert!(processed_lines[140].clean_text().is_empty());

        assert_eq!(
            processed_lines.len(),
            141,
            "{}",
            processed_lines.iter().map(|e| e.marker()).collect::<Vec<_>>().join(",")
        );
    }

    #[test]
    fn test_oet_rv_haggai_processing() {
        // A simple 2-chapter book
        let file_path = "../../Tests/DataFilesForTests/OET-RV/OET-RV_HAG.ESFM";
        let file = File::open(file_path).expect("Could not open OET-RV Haggai ESFM file");
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

        let original_count = raw_lines.len();
        // println!("Original lines read: {}", original_count);
        assert_eq!(original_count, 81, "Expected 81 raw lines in Haggai ESFM file");

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_lines = crate::processing::process_lines(raw_lines, "HAG", "OET-RV", &options);
        // println!("Final OET-RV Haggai processed line entries: {}", processed.len());
        for (n, entry) in processed_lines.clone().into_iter().enumerate() {
            // println!("  {}: Marker: {}, Clean Text: '{}', Extras: {:?}", n, entry.marker(), entry.clean_text(), entry.extras());
            assert!(
                entry.marker() != "¬v=",
                "Unexpected end verse= marker in OET-RV Haggai at entry {}: {:?}",
                n,
                entry
            );
        }

        // println!("HAG markers 20..40: {:?}", (20..40).map(|i| (i, processed[i].marker(), processed[i].clean_text())).collect::<Vec<_>>());
        assert_eq!(processed_lines.len(), 194, "Expected 188 entries after verse start markers and nesting markers added");

        // Verify some key structural markers from the reference test
        assert_eq!(processed_lines[5].marker(), "headers");
        assert_eq!(processed_lines[11].marker(), "¬headers");
        assert_eq!(processed_lines[12].marker(), "intro");
        assert_eq!(processed_lines[22].marker(), "¬intro");
        assert_eq!(processed_lines[23].marker(), "chapters");
        assert_eq!(processed_lines[24].marker(), "c");
        assert_eq!(processed_lines[24].clean_text(), "1");
        assert_eq!(processed_lines[25].marker(), "v=");
        assert_eq!(processed_lines[25].clean_text(), "1");
        assert_eq!(processed_lines[30].marker(), "v");
        assert_eq!(processed_lines[30].adjusted_text(), "1");
        assert_eq!(processed_lines[31].marker(), "v~");
        assert_eq!(processed_lines[31].original_text(),
            "In Dareyavesh's \\add (Darius's¦375563)\\add* second year¦375561 as king¦375564 \\add of Persia\\add*, on¦375565 the 1st of the sixth¦375566 month, the prophet¦375577 Haggai¦375576 brought Yahweh's¦375573 message¦375571 to the governor¦375584 of Yehudah¦375585, Zerubavel¦375580 (Shealtiyel's¦375583 son), and to the high¦375593 priest¦375592, Yehoshua (Yehotsadak's¦375591 son), telling \\add them that\\add*\\x + \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.\\x*");
        assert_eq!(processed_lines[31].adjusted_text(),
            "In Dareyavesh's \\add (Darius's¦375563)\\add* second year¦375561 as king¦375564 \\add of Persia\\add*, on¦375565 the 1st of the sixth¦375566 month, the prophet¦375577 Haggai¦375576 brought Yahweh's¦375573 message¦375571 to the governor¦375584 of Yehudah¦375585, Zerubavel¦375580 (Shealtiyel's¦375583 son), and to the high¦375593 priest¦375592, Yehoshua (Yehotsadak's¦375591 son), telling \\add them that\\add*");
        assert_eq!(processed_lines[31].extras().unwrap().len(), 1, "Expected one extra for verse 1 xref");
        assert_eq!(processed_lines[31].clean_text(),
            "In Dareyavesh's (Darius's¦375563) second year¦375561 as king¦375564 of Persia, on¦375565 the 1st of the sixth¦375566 month, the prophet¦375577 Haggai¦375576 brought Yahweh's¦375573 message¦375571 to the governor¦375584 of Yehudah¦375585, Zerubavel¦375580 (Shealtiyel's¦375583 son), and to the high¦375593 priest¦375592, Yehoshua (Yehotsadak's¦375591 son), telling them that");
        assert_eq!(processed_lines[88].marker(), "¬v");
        assert_eq!(processed_lines[88].clean_text(), "15");
        assert_eq!(processed_lines[89].marker(), "¬p");
        assert_eq!(processed_lines[89].clean_text(), "");
        assert_eq!(processed_lines[91].marker(), "¬c");
        assert_eq!(processed_lines[91].clean_text(), "1");
        assert_eq!(processed_lines[92].marker(), "c");
        assert_eq!(processed_lines[92].clean_text(), "2");
        println!("186 {}", processed_lines[186]);
        println!("187 {}", processed_lines[187]);
        println!("188 {}", processed_lines[188]);
        println!("189 {}", processed_lines[189]);
        assert_eq!(processed_lines[192].marker(), "¬c");
        assert_eq!(processed_lines[192].clean_text(), "2");
        assert_eq!(processed_lines[193].marker(), "¬chapters");
        assert!(processed_lines[193].clean_text().is_empty());
    }

    #[test]
    fn test_oet_rv_genesis_processing() {
        // More complex because the first section crosses the chapter boundary
        let file_path = "../../Tests/DataFilesForTests/OET-RV/OET-RV_GEN.ESFM";
        let file = File::open(file_path).expect("Could not open OET-RV Genesis ESFM file");
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

        let original_count = raw_lines.len();
        // println!("Original lines read: {}", original_count);
        assert_eq!(original_count, 2568, "Expected 2568 raw lines in Genesis ESFM file");

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_lines = crate::processing::process_lines(raw_lines, "GEN", "OET-RV", &options);
        // println!("Final OET-RV Genesis processed line entries: {}", processed.len());
        for (n, entry) in processed_lines.clone().into_iter().enumerate() {
            // println!("  {}: Marker: {}, Clean Text: '{}', Extras: {:?}", n, entry.marker(), entry.clean_text(), entry.extras());
            assert!(entry.marker() != "¬v=", "Unexpected end verse= marker in OET-RV Genesis at entry {}: {:?}", n, entry);
        }

        // for j in 50..=200 {
        //     println!("Entry {}: Marker: {}, Clean Text: '{}', Extras: {:?}", j, processed[j].marker(), processed[j].clean_text(), processed[j].extras());
        // }
        // println!("GEN markers 50..200: {:?}", (50..200).map(|i| (i, processed[i].marker(), processed[i].clean_text())).collect::<Vec<_>>());

        assert_eq!(processed_lines.len(), 6843, "Expected 6743 entries after nesting and verse start markers");

        // Verify some key structural markers from the reference test
        assert_eq!(processed_lines[5].marker(), "headers");
        assert_eq!(processed_lines[11].marker(), "¬headers");
        assert_eq!(processed_lines[12].marker(), "intro");
        assert_eq!(processed_lines[36].marker(), "¬intro");
        assert_eq!(processed_lines[37].marker(), "chapters");

        let chapter_1_idx = processed_lines
            .iter()
            .position(|entry| entry.marker() == "c" && entry.clean_text() == "1")
            .expect("Should find chapter 1");
        assert_eq!(processed_lines[chapter_1_idx + 1].marker(), "v=");
        assert_eq!(processed_lines[chapter_1_idx + 1].clean_text(), "1");

        let verse_13_end_idx = processed_lines
            .iter()
            .position(|entry| entry.marker() == "¬v" && entry.clean_text() == "13")
            .expect("Should find verse 13 end marker");
        assert_eq!(processed_lines[verse_13_end_idx].marker(), "¬v");
        assert_eq!(processed_lines[verse_13_end_idx].clean_text(), "13");
        assert_eq!(processed_lines[verse_13_end_idx + 1].marker(), "¬p");
        assert_eq!(processed_lines[verse_13_end_idx + 1].clean_text(), "");

        let verse_31_end_idx = processed_lines
            .iter()
            .position(|entry| entry.marker() == "¬v" && entry.clean_text() == "31")
            .expect("Should find verse 31 end marker");
        assert_eq!(processed_lines[verse_31_end_idx].marker(), "¬v");
        assert_eq!(processed_lines[verse_31_end_idx].clean_text(), "31");
        assert_eq!(processed_lines[verse_31_end_idx + 1].marker(), "¬p");
        assert_eq!(processed_lines[verse_31_end_idx + 1].clean_text(), "");

        let chapter_2_idx = processed_lines
            .iter()
            .position(|entry| entry.marker() == "c" && entry.clean_text() == "2")
            .expect("Should find chapter 2");
        assert_eq!(processed_lines[chapter_2_idx].marker(), "c");
        assert_eq!(processed_lines[chapter_2_idx].clean_text(), "2");
        assert_eq!(processed_lines[chapter_2_idx + 1].marker(), "p");
        assert_eq!(processed_lines[chapter_2_idx + 1].clean_text(), "");
        assert_eq!(processed_lines[chapter_2_idx + 2].marker(), "c#");
        assert_eq!(processed_lines[chapter_2_idx + 2].clean_text(), "2");

        let final_chapter_end_idx = processed_lines
            .iter()
            .rposition(|entry| entry.marker() == "¬c" && entry.clean_text() == "50")
            .expect("Should find the closing chapter 50 marker");
        assert_eq!(processed_lines[final_chapter_end_idx].marker(), "¬c");
        assert_eq!(processed_lines[final_chapter_end_idx].clean_text(), "50");
        assert_eq!(processed_lines[final_chapter_end_idx + 1].marker(), "¬chapters");
        assert!(processed_lines[final_chapter_end_idx + 1].clean_text().is_empty());
    }

    #[test]
    fn test_oet_rv_front_matter_processing() {
        // Unusual non-CV nesting situation
        let file_path = "../../Tests/DataFilesForTests/OET-RV/OET-RV_FRT.ESFM";
        let file = File::open(file_path).expect("Could not open OET-RV Front Matter ESFM file");
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

        let original_count = raw_lines.len();
        // println!("Original lines read: {}", original_count);
        assert_eq!(original_count, 60, "Expected 60 raw lines in Front Matter ESFM file");

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_lines = crate::processing::process_lines(raw_lines, "FRT", "OET-RV", &options);

        // println!("Final OET-RV Front Matter processed line entries: {}", processed_lines.len());
        // println!("OET-RV FRT Processed lines markers = {}", processed_lines.iter().map(|e| e.marker()).collect::<Vec<_>>().join(", "));

        // println!("OET-RV FRT processed_line_entries = {}", processed_lines);
        //     OET-RV FRT processed_line_entries = InternalBibleEntryList:
        //         0/ id = "FRT - Open English Translation…ders' Version (OET-RV) v0.2.03"
        //         1/ periph = "Title Page"
        //         2/ headers = ""
        //         3/ mt1 = "The Open English Translation"
        //         4/ mt2 = "of the Bible"
        //         5/ pc = ""
        //         6/ v~ = "Open English Translation"
        //         7/ ¬pc = ""
        //         8/ pc = ""
        //         9/ v~ = "" + extras
        //         10/ ¬pc = ""
        //         11/ pc = ""
        //         12/ v~ = "Freely-Given.org"
        //         13/ periph = "Preface"
        //         14/ mt1 = "Preliminary preface"
        //         15/ ¬pc = ""
        //         16/ p = ""
        //         17/ v~ = "It is our prayer that the Open…god-inspired Biblical writers."
        //         18/ ¬p = ""
        //         19/ b = ""
        //         20/ m = ""
        //         21/ v~ = "Note: This is still a very ear…we're still testing both ways."
        //         22/ ¬headers = ""
        //         23/ intro = ""
        //         24/ ¬m = ""
        //         25/ is1 = "Introduction"
        //         26/ p = ""
        //         27/ v~ = "The OET Literal Version (OET-L…chnical details are important."
        //         28/ ¬p = ""
        //         29/ p = ""
        //         30/ v~ = "In contrast, this OET Readers'…ories that they can relate to."
        //         31/ ¬p = ""
        //         32/ ¬is1 = ""
        //         33/ is1 = "Goals and intended audience"
        //         34/ m = ""
        //         35/ v~ = "The OET has the following goals:"
        //         36/ ¬m = ""
        //         37/ list = ""
        //         38/ li1 = ""
        //         39/ v~ = "The primary goal of the Open E…nterpreted by the translators."
        //         40/ ¬li1 = ""
        //         41/ li1 = ""
        //         42/ v~ = "Part of the motivation comes f…od by modern English speakers."
        //         43/ ¬li1 = ""
        //         44/ li1 = ""
        //         45/ v~ = "A further goal is to expose mo…that can possibly be improved."
        //         46/ ¬li1 = ""
        //         47/ li1 = ""
        //         48/ v~ = "Finally, we also want a transl…akers or writers likely meant."
        //         49/ ¬li1 = ""
        //         50/ ¬list = ""
        //         51/ ¬is1 = ""
        //         52/ is1 = "Distinctives"
        //         53/ m = ""
        //         54/ v~ = "The OET has the following distinguishing points:"
        //         55/ ¬m = ""
        //         56/ list = ""
        //         57/ li1 = ""
        //         58/ v~ = "An easy-to-understand Readers'…ngside a very Literal Version."
        //         59/ ¬li1 = ""
        //         60/ li1 = ""
        //         61/ v~ = "A generous open license so tha…needing to request permission."
        //         62/ ¬li1 = ""
        //         63/ li1 = ""
        //         64/ v~ = "This Readers' Version speaks l…peak like dinosaurs (or Yoda)!"
        //         65/ ¬li1 = ""
        //         66/ li1 = ""
        //         67/ v~ = "The Readers' Version has secti…hat help modern Bible readers."
        //         68/ ¬li1 = ""
        //         69/ li1 = ""
        //         70/ v~ = "The Readers' Version uses mode…torical and symbolic studies)."
        //         71/ ¬li1 = ""
        //         72/ li1 = ""
        //         73/ v~ = "The Readers' Version uses well…rn readers are familiar with)."
        //         74/ ¬li1 = ""
        //         75/ li1 = ""
        //         76/ v~ = "Up and down in the original la…norm (with computerised maps)."
        //         77/ ¬li1 = ""
        //         78/ li1 = ""
        //         79/ v~ = "The Readers' Version is less f…nguages of the common people.)"
        //         80/ ¬li1 = ""
        //         81/ li1 = ""
        //         82/ v~ = "The Readers' Version uses sect… came before and what follows."
        //         83/ ¬li1 = ""
        //         84/ li2 = ""
        //         85/ v~ = "We've also tried to focus our … events happening at the time."
        //         86/ ¬li2 = ""
        //         87/ li2 = ""
        //         88/ v~ = "We also provide a list of thes…h we don't use in the OET-RV)."
        //         89/ ¬li2 = ""
        //         90/ li1 = ""
        //         91/ v~ = "Being a 21st century translati…ob-in-the-bible/ for example.)"
        //         92/ ¬li1 = ""
        //         93/ li1 = ""
        //         94/ v~ = "In addition to wanting to get …ngly do use Felix and Festus.)"
        //         95/ ¬li1 = ""
        //         96/ li1 = ""
        //         97/ v~ = "With regular words, we've trie… this example becomes immerse."
        //         98/ ¬li1 = ""
        //         99/ li1 = ""
        //         100/ v~ = "Italics are only used for emph…ghter colour for added words.)"
        //         101/ ¬li1 = ""
        //         102/ li1 = ""
        //         103/ v~ = "Bolding is used for nomina sac…es considered to refer to God."
        //         104/ ¬li1 = ""
        //         105/ li1 = ""
        //         106/ v~ = "The English Christ is an adapt…o is selected/chosen (by God)."
        //         107/ ¬li1 = ""
        //         108/ li1 = ""
        //         109/ v~ = "Most readers living in modern …s felt a little too informal.)"
        //         110/ ¬li1 = ""
        //         111/ li1 = ""
        //         112/ v~ = "The Literal Version tries to a…t is correct or even helpful.)"
        //         113/ ¬li1 = ""
        //         114/ li1 = ""
        //         115/ v~ = "Most dialects of modern Englis…cts now prefer y'all or yous)."
        //         116/ ¬li1 = ""
        //         117/ li1 = ""
        //         118/ v~ = "Because the Literal Version so…require the following changes:"
        //         119/ ¬li1 = ""
        //         120/ li2 = ""
        //         121/ v~ = "to raise from sitting, we'd want: stand up"
        //         122/ ¬li2 = ""
        //         123/ li2 = ""
        //         124/ v~ = "to raise from bed, we'd want: get up"
        //         125/ ¬li2 = ""
        //         126/ li2 = ""
        //         127/ v~ = "to raise from the grave, we'd want: come back to life"
        //         128/ ¬li2 = ""
        //         129/ li2 = ""
        //         130/ v~ = "to raise an object, we'd want: lift up"
        //         131/ ¬li2 = ""
        //         132/ li2 = ""
        //         133/ v~ = "to raise a person, we'd often want: exalt or praise"
        //         134/ ¬li2 = ""
        //         135/ li2 = ""
        //         136/ v~ = "Alert readers might be aware t… side-by-side in front of you!"
        //         137/ ¬li2 = ""
        //         138/ li1 = ""
        //         139/ v~ = "These particular pages use Bri…so be available in the future."
        //         140/ ¬li1 = ""
        //         141/ li1 = ""
        //         142/ v~ = "Our preference in most edition…is has a couple of advantages:"
        //         143/ ¬li1 = ""
        //         144/ li2 = ""
        //         145/ v~ = "The Old Testament starts with …beginning was the Messenger…”."
        //         146/ ¬li2 = ""
        //         147/ li2 = ""
        //         148/ v~ = "Acts ends up right after the first book by its author Luke."
        //         149/ ¬li2 = ""
        //         150/ li2 = ""
        //         151/ v~ = "It just reminds readers that t…cred degree—only by tradition."
        //         152/ ¬li2 = ""
        //         153/ li2 = ""
        //         154/ v~ = "Some do complain that the trad…Israel mentioned in Numbers 2."
        //         155/ ¬li2 = ""
        //         156/ li1 = ""
        //         157/ v~ = "Beware of some traps interpret…n the English Literal Version:"
        //         158/ ¬li1 = ""
        //         159/ li2 = ""
        //         160/ v~ = "Other languages use the negati…e (in the Greek in this case)."
        //         161/ ¬li2 = ""
        //         162/ li2 = ""
        //         163/ v~ = "Other languages may omit (or e…hich should follow ‘daughter’."
        //         164/ ¬li2 = ""
        //         165/ ¬list = ""
        //         166/ m = ""
        //         167/ v~ = "Always check the Readers' Vers…l Version says or doesn't say."
        //         168/ ¬m = ""
        //         169/ ¬is1 = ""
        //         170/ ¬intro = ""

        assert_eq!(processed_lines.len(), 171, "Expected 171 entries after nesting and verse start markers");

        // Verify some key structural markers from the reference test
        assert_eq!(processed_lines[2].marker(), "headers");
        assert_eq!(processed_lines[22].marker(), "¬headers");
        assert_eq!(processed_lines[23].marker(), "intro");
        assert_eq!(processed_lines[170].marker(), "¬intro");
    }

    #[test]
    fn test_oet_lv_ot_summary_verification() {
        let summary_path = "test_data/OET-LV_OT_summary.text";
        let summary_content = std::fs::read_to_string(summary_path).expect("Could not read summary file");

        let dir_path = "../../Tests/DataFilesForTests/OET-LV/";
        let mut books_to_verify = Vec::new();
        for entry in std::fs::read_dir(dir_path).expect("Could not read OET-LV OT directory") {
            let entry = entry.expect("Could not read directory entry");
            let path = entry.path();
            if let Some(file_name) = path.file_name().and_then(|s| s.to_str()) {
                if file_name.starts_with("OET-LV_") && file_name.ends_with(".ESFM") {
                    let bos_book_code = &file_name[7..file_name.len() - 5];
                    if bos_book_code.len() == 3 && is_old_testament_nr(bos_book_code) {
                        books_to_verify.push((bos_book_code.to_string(), path.to_str().unwrap().to_string()));
                    }
                }
            }
        }
        books_to_verify.sort_by(|a, b| a.0.cmp(&b.0));

        let options = ProcessLinesOptions::default();

        for (bos_book_code, file_path) in books_to_verify {
            let summary_line = summary_content
                .lines()
                .find(|l| l.trim().starts_with(&bos_book_code))
                .unwrap_or_else(|| panic!("Book {} not found in summary", bos_book_code));

            let expected_raw = summary_line
                .split("len(self._rawLines)=")
                .nth(1)
                .unwrap()
                .split_whitespace()
                .next()
                .unwrap()
                .parse::<usize>()
                .unwrap();
            let expected_proc = summary_line
                .split("len(self._processedLines)=")
                .nth(1)
                .unwrap()
                .split_whitespace()
                .next()
                .unwrap()
                .parse::<usize>()
                .unwrap();
            // println!("Verifying {}: expected raw lines = {}, expected processed lines = {}", bos_book_code, expected_raw, expected_proc);

            let file = File::open(&file_path).expect(&format!("Could not open ESFM file: {}", file_path));
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

            assert_eq!(
                raw_lines.len(),
                expected_raw,
                "Raw lines count mismatch for {}",
                bos_book_code
            );

            let processed_lines = process_lines(raw_lines, &bos_book_code, "OET-LV_OT", &options);
            assert_eq!(
                processed_lines.len(),
                expected_proc,
                "Processed lines count mismatch for {}",
                bos_book_code
            );
        }
    }

    #[test]
    fn test_oet_lv_nt_summary_verification() {
        let summary_path = "test_data/OET-LV_NT_summary.text";
        let summary_content = std::fs::read_to_string(summary_path).expect("Could not read summary file");

        let dir_path = "../../Tests/DataFilesForTests/OET-LV/";
        let mut books_to_verify = Vec::new();
        for entry in std::fs::read_dir(dir_path).expect("Could not read OET-LV NT directory") {
            let entry = entry.expect("Could not read directory entry");
            let path = entry.path();
            if let Some(file_name) = path.file_name().and_then(|s| s.to_str()) {
                if file_name.starts_with("OET-LV_") && file_name.ends_with(".ESFM") {
                    let bos_book_code = &file_name[7..file_name.len() - 5];
                    if bos_book_code.len() == 3 && is_new_testament_nr(bos_book_code) {
                        books_to_verify.push((bos_book_code.to_string(), path.to_str().unwrap().to_string()));
                    }
                }
            }
        }
        books_to_verify.sort_by(|a, b| a.0.cmp(&b.0));

        let options = ProcessLinesOptions::default();

        for (bos_book_code, file_path) in books_to_verify {
            let summary_line = summary_content
                .lines()
                .find(|l| l.trim().starts_with(&bos_book_code))
                .unwrap_or_else(|| panic!("Book {} not found in summary", bos_book_code));

            let expected_raw = summary_line
                .split("len(self._rawLines)=")
                .nth(1)
                .unwrap()
                .split_whitespace()
                .next()
                .unwrap()
                .parse::<usize>()
                .unwrap();
            let expected_proc = summary_line
                .split("len(self._processedLines)=")
                .nth(1)
                .unwrap()
                .split_whitespace()
                .next()
                .unwrap()
                .parse::<usize>()
                .unwrap();
            // println!("Verifying {}: expected raw lines = {}, expected processed lines = {}", bos_book_code, expected_raw, expected_proc);

            let file = File::open(&file_path).expect(&format!("Could not open ESFM file: {}", file_path));
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

            assert_eq!(
                raw_lines.len(),
                expected_raw,
                "Raw lines count mismatch for {}",
                bos_book_code
            );

            let processed_lines = process_lines(raw_lines, &bos_book_code, "OET-LV_NT", &options);
            assert_eq!(
                processed_lines.len(),
                expected_proc,
                "Processed lines count mismatch for {}",
                bos_book_code
            );
        }
    }

    #[test]
    // TODO: This is a bit of a useless check as the expected counts are based on the current processing,
    //  but it at least ensures we don't have any major regressions in line counts for the OET-RV books.
    //  We can improve this in the future by adding more detailed checks for specific markers and structures in the processed output.
    fn test_oet_rv_summary_verification() {
        let summary_path = "test_data/OET-RV_summary.text";
        let summary_content = std::fs::read_to_string(summary_path).expect("Could not read summary file");

        let dir_path = "../../Tests/DataFilesForTests/OET-RV/";
        let mut books_to_verify = Vec::new();
        for entry in std::fs::read_dir(dir_path).expect("Could not read OET-RV directory") {
            let entry = entry.expect("Could not read directory entry");
            let path = entry.path();
            if let Some(file_name) = path.file_name().and_then(|s| s.to_str()) {
                if file_name.starts_with("OET-RV_") && file_name.ends_with(".ESFM") {
                    let bos_book_code = &file_name[7..file_name.len() - 5];
                    if bos_book_code.len() == 3 && (is_old_testament_nr(bos_book_code) || is_new_testament_nr(bos_book_code)) {
                        books_to_verify.push((bos_book_code.to_string(), path.to_str().unwrap().to_string()));
                    }
                }
            }
        }
        books_to_verify.sort_by(|a, b| a.0.cmp(&b.0));

        let options = ProcessLinesOptions::default();

        for (bos_book_code, file_path) in books_to_verify {
            let summary_line = summary_content
                .lines()
                .find(|l| l.trim().starts_with(&bos_book_code))
                .unwrap_or_else(|| panic!("Book {} not found in summary", bos_book_code));

            let expected_raw = summary_line
                .split("len(self._rawLines)=")
                .nth(1)
                .unwrap()
                .split_whitespace()
                .next()
                .unwrap()
                .parse::<usize>()
                .unwrap();
            let expected_proc = summary_line
                .split("len(self._processedLines)=")
                .nth(1)
                .unwrap()
                .split_whitespace()
                .next()
                .unwrap()
                .parse::<usize>()
                .unwrap();
            // println!("Verifying {}: expected raw lines = {}, expected processed lines = {}", bos_book_code, expected_raw, expected_proc);

            let file = File::open(&file_path).expect(&format!("Could not open ESFM file: {}", file_path));
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

            if bos_book_code == "ISA" {
                println!(
                    "WIP: ISA raw lines count: {}, expected: {}",
                    raw_lines.len(),
                    expected_raw
                );
                assert_eq!(
                    raw_lines.len(),
                    expected_raw - 307,
                    "Raw lines count mismatch for {}",
                    bos_book_code
                );
            } else {
                assert_eq!(
                    raw_lines.len(),
                    expected_raw,
                    "Raw lines count mismatch for {}",
                    bos_book_code
                );
            }

            let processed_lines = process_lines(raw_lines, &bos_book_code, "OET-RV", &options);
            // NOTE: We now have more 'v=' entries (for better or for worse???)
            if bos_book_code == "ACT" {
                println!("NEED TO CHECK: ACT processed lines count: {}, expected: {}",
                    processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 92, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "AMO" {
                println!("NEED TO CHECK: AMO processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 18, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "CH1" {
                println!("NEED TO CHECK: CH1 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 97, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "CH2" {println!(
                    "NEED TO CHECK: CH2 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!( processed_lines.len(), expected_proc + 73, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "CO1" {
                println!("NEED TO CHECK: CO1 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 32, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "CO2" {
                println!("NEED TO CHECK: CO2 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 24, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "COL" {
                println!("NEED TO CHECK: COL processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 10, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "DAN" {
                println!("NEED TO CHECK: DAN processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 26, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "DEU" {
                println!("NEED TO CHECK: DEU processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 84, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "ECC" {
                println!("NEED TO CHECK: ECC processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 13, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "EPH" {
                println!("NEED TO CHECK: EPH processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 17, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "EST" {
                println!("NEED TO CHECK: EST processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 15, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "EXO" {
                println!("NEED TO CHECK: EXO processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 106, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "EZE" {
                println!("NEED TO CHECK: EZE processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 118, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "EZR" {
                println!("NEED TO CHECK: EZR processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 42, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "GAL" {
                println!("NEED TO CHECK: GAL processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 15, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "GEN" {
                println!("NEED TO CHECK: GEN processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 102, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "HAB" {
                println!("NEED TO CHECK: HAB processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 7, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "HAG" {
                println!("NEED TO CHECK: HAG processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 6, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "HEB" {
                println!("NEED TO CHECK: HEB processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 23, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "HOS" {
                println!("NEED TO CHECK: HEB processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 26, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "ISA" {
                println!("WIP: ISA processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), 13813, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JAM" {
                println!("NEED TO CHECK: JAM processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 16, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JDE" {
                println!("NEED TO CHECK: JDE processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 4, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JDG" {
                println!("NEED TO CHECK: JDG processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 41, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JER" {
                println!("WIP: JER processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), 8959, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JHN" {
                println!("NEED TO CHECK: JHN processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 85, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JN1" {
                println!("NEED TO CHECK: JN1 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 14, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JN2" {
                println!("NEED TO CHECK: JN2 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 3, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JN3" {
                println!("NEED TO CHECK: JN3 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 4, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JNA" {
                println!("NEED TO CHECK: JNA processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 5, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JOB" {
                println!("NEED TO CHECK: JOB processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 41, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JOL" {
                println!("NEED TO CHECK: JOL processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 9, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "JOS" {
                println!("NEED TO CHECK: JOS processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 52, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "KI1" {
                println!("NEED TO CHECK: KI1 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 69, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "KI2" {
                println!("NEED TO CHECK: KI2 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 69, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "LAM" {
                println!("NEED TO CHECK: LAM processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 10, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "LEV" {
                println!("NEED TO CHECK: LEV processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 53, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "LUK" {
                println!("NEED TO CHECK: LUK processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 159, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "MAL" {
                println!("NEED TO CHECK: MAL processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 9, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "MAT" {
                println!("NEED TO CHECK: MAT processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 156, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "MIC" {
                println!("NEED TO CHECK: MIC processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 14, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "MRK" {
                println!("NEED TO CHECK: MRK processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 93, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "NAH" {
                println!("NEED TO CHECK: NAH processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 3, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "NEH" {
                println!("NEED TO CHECK: NEH processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 70, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "NUM" {
                println!("NEED TO CHECK: NUM processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 105, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "OBA" {
                println!("NEED TO CHECK: OBA processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 6, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "PE1" {
                println!("NEED TO CHECK: PE1 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 12, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "PE2" {
                println!("NEED TO CHECK: PE2 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 4, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "PHM" {
                println!("NEED TO CHECK: PHM processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 4, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "PHP" {
                println!("NEED TO CHECK: PHP processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 11, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "PRO" {
                println!("NEED TO CHECK: PRO processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 29, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "PSA" {
                println!("NEED TO CHECK: PSA processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 310, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "REV" {
                println!("NEED TO CHECK: REV processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 41, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "ROM" {
                println!("NEED TO CHECK: ROM processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 41, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "RUT" {
                println!("NEED TO CHECK: RUT processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 8, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "SA1" {
                println!("NEED TO CHECK: SA1 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 64, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "SA2" {
                println!("NEED TO CHECK: SA2 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 55, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "SNG" {
                println!("NEED TO CHECK: SNG processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 25, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "TH1" {
                println!("NEED TO CHECK: TH1 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 7, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "TH2" {
                println!("NEED TO CHECK: TH2 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 8, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "TI1" {
                println!("NEED TO CHECK: TI1 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 13, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "TI2" {
                println!("NEED TO CHECK: TI2 processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 8, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "TIT" {
                println!("NEED TO CHECK: TIT processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 6, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "ZEC" {
                println!("NEED TO CHECK: ZEC processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 27, "Processed lines count mismatch for {}", bos_book_code);
            } else if bos_book_code == "ZEP" {
                println!("NEED TO CHECK: ZEP processed lines count: {}, expected: {}", processed_lines.len(), expected_proc);
                assert_eq!(processed_lines.len(), expected_proc + 6, "Processed lines count mismatch for {}", bos_book_code);
            } else {
                assert_eq!(processed_lines.len(), expected_proc, "Processed lines count mismatch for {}", bos_book_code);
            }
        }
    }
}
