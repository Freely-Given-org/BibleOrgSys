//! USFM nesting and end marker logic.
//
// This is HIGHLY COMPLEX logic because of the overlapping nesting hierarchies.
//  The simple one is headers, optional introdction, and then chapters and verses.
//      (Actually, not all 'books' have chapters and verses, e.g., front and back matter, etc.)
//  Then overlaid on that are main sections, normal (s1,s2,...) sections, and various different paragraph types
//      which can sometimes cross chapter boundaries, and can also start or finish in the middle of a verse.
//  Then inside sections, there are also lists and tables.
//      Lists can have multiple levels (li1, li2, etc.) so can be nested inside each other.
//  On top of that, there's rem lines which can occur anywhere, including being nested inside other structures.
//
// CHANGELOG:
//   2026-05-27 Make 'nb' cause a close 'nb' to be added BEFORE the new 'c' marker, but the 'nb' itself is closed with the original paragraph marker
//   2026-07-03 Improve list handling
//   2026-08-24 Improve embedded list nesting with indent levels by Gemini for RJH
//
use compact_str::CompactString;
use std::collections::HashMap;
use indexmap::IndexMap;
use usfm_markers::normalize_marker;

use crate::bos_markers::intro_list_markers::is_intro_list;
use crate::bos_markers::main_text_list_markers::is_main_text_list;
use crate::bos_markers::{
    heading_markers, intro_list_markers, intro_outline_markers, introduction_markers, is_end_marker,
    main_text_list_markers, paragraph_markers
};
use crate::entry::InternalBibleEntry;
use crate::entry_lists::InternalBibleEntryList;
use crate::have_strict_checking_flag;
use crate::abbreviate;

#[inline]
fn get_list_level(marker: &str) -> u32 {
    if let Some(c) = marker.chars().last() {
        if c.is_ascii_digit() {
            return c.to_digit(10).unwrap_or(1);
        }
    }
    1
}

#[inline]
fn is_list_item_marker(marker: &str) -> bool {
    (marker.starts_with("li") && !marker.starts_with("list")) || marker.starts_with("lim") || marker == "lh" || marker == "lf"
}

fn close_lists_down_to(
    target_level: u32,
    open_markers: &mut Vec<CompactString>,
    open_list_levels: &mut Vec<u32>,
    new_lines: &mut InternalBibleEntryList,
) {
    // Step A: Unwind all deeper list levels
    while let Some(&curr_list_lvl) = open_list_levels.last() {
        if target_level == 0 || curr_list_lvl > target_level {
            // Close list items at or above this list level
            while let Some(pos) = open_markers.iter().rposition(|m| {
                let s = m.as_str();
                is_list_item_marker(s) && get_list_level(s) >= curr_list_lvl
            }) {
                let s = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", s), "").unwrap());
            }

            // Close the list container itself
            if let Some(pos) = open_markers.iter().rposition(|m| m == "list") {
                open_markers.remove(pos);
            }
            open_list_levels.pop();
            new_lines.push(InternalBibleEntry::end_marker("¬list", curr_list_lvl.to_string()).unwrap());
        } else {
            break;
        }
    }

    // Step B: If target_level > 0, close any open list item at target_level
    if target_level > 0 {
        while let Some(pos) = open_markers.iter().rposition(|m| {
            let s = m.as_str();
            is_list_item_marker(s) && get_list_level(s) >= target_level
        }) {
            let s = open_markers.remove(pos);
            new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", s), "").unwrap());
        }
    }
}

// TODO: These need to go into BOS Markers
/// Markers that can define section boundaries.
const NESTABLE_SECTION_MARKERS: &[&str] = &[
    "is1", // Introductory sections
    "ms1", //"ms2", "ms3", // Major sections
    "s1",  // Section headings
    "iex", // Chapter introductions, e.g., in KJB-1611
    "c",   // Chapters can also define section boundaries, especially for intro-to-content transitions
];
const SECTION_HEADER_FIELDS_PRECEDED_BY_PREVERSE_NUMBER: [&str; 8] = ["s1", "s2", "s3", "s4", "ms1", "ms2", "ms3", "sp"];

/// Add logical verse start markers (`v=`) before section headings
///   but don't add multiple markers in the section headings are consecutive
pub fn add_preverse_markers_before_headings(entries: InternalBibleEntryList, work_name: &str, bos_book_code: &str,)
             -> InternalBibleEntryList {
    let entries_vec = entries.into_vec();
    let num_entries = entries_vec.len();
    let mut result = InternalBibleEntryList::with_capacity(num_entries * 1.1 as usize);

    // let mut fields_also_preceded: Vec<&str> = Vec::new();
    // fields_also_preceded.extend_from_slice(paragraph_markers::ALL);
    // fields_also_preceded.extend_from_slice(&["c#", "sr", "r", "mr", "d", "ib", "b", "cl¤", "tr"]);

    let mut current_verse_number: Option<CompactString> = None;
    // let mut current_verse_clean_text: Option<CompactString> = None;
    // let mut current_verse_original_text: Option<CompactString> = None;
    let mut current_verse_part_index: usize = 0;
    let mut just_added_vequals = false;

    let mut _chapter_number_str = "0";
    for j in 0..num_entries {
        let entry = &entries_vec[j];
        let marker = entry.marker();
        assert!( !marker.is_empty() && !marker.contains('\\'),
            "{} {} entry marker should not be empty and should not contain a backslash: found '{}'", work_name, bos_book_code, marker);
        assert!( normalize_marker(marker) == marker,
            "{} {} Entry marker should be normalized (no extra spaces, etc.): found '{}'", work_name, bos_book_code, marker);
        if marker == "c" {
            _chapter_number_str = entry.clean_text();
        }

        if SECTION_HEADER_FIELDS_PRECEDED_BY_PREVERSE_NUMBER.contains(&marker) {
            let mut saw_continuation_after_field = false;
            let mut inserted_verse_text = String::new();

            // Look ahead for the next verse text, skipping over any continuation markers or other fields,
            //  but stopping if we hit a non-field marker that isn't a continuation
            for k in (j + 1)..num_entries {
                let next_entry = &entries_vec[k];
                let next_marker = next_entry.marker();
                if next_marker == "v" {
                    if saw_continuation_after_field && current_verse_number.is_some() {
                        if let Some(current_verse) = current_verse_number.as_deref() {
                            let verse_text = if current_verse_part_index > 0 {
                                // println!("{} {} added c{} line_entry 'v=' = '{}b'", work_name, bos_book_code, chapter_number_str, current_verse);
                                format!("{current_verse}b")
                            } else {
                                current_verse.to_string()
                            };
                            inserted_verse_text = verse_text;
                        }
                    } else {
                        inserted_verse_text = next_entry.adjusted_text().to_string();
                    }
                    break;
                } else if next_marker == "v~" {
                    saw_continuation_after_field = true;
                    continue;
                    // } else if !fields_also_preceded.contains(&next_marker)
                    //     && !next_marker.starts_with('¬')
                    // {
                    //     break;
                }
            }

            if !inserted_verse_text.is_empty() && !just_added_vequals {
                result.push(
                    InternalBibleEntry::new(
                        "v=",
                        "v",
                        &inserted_verse_text,
                        &inserted_verse_text,
                        None,
                        &inserted_verse_text,
                    )
                    .expect("Invalid internal entry"),
                );
                just_added_vequals = true;
            }
        }

        result.push(entry.clone());

        match marker {
            "c" => {
                current_verse_number = None;
                // current_verse_clean_text = None;
                // current_verse_original_text = None;
                current_verse_part_index = 0;
                just_added_vequals = false;
            }
            "v" => {
                current_verse_number = Some(CompactString::from(entry.adjusted_text()));
                // current_verse_clean_text = Some(CompactString::from(entry.clean_text()));
                // current_verse_original_text = Some(CompactString::from(entry.original_text().unwrap_or("")));
                current_verse_part_index = 0;
                just_added_vequals = false;
            }
            "v~" => {
                if current_verse_number.is_some() {
                    current_verse_part_index += 1;
                }
                just_added_vequals = false;
            }
            _ => {}
        }
    }

    if have_strict_checking_flag() || cfg!(debug_assertions) {
        let validation_results = validate_preverse_marker_insertions(&result);
        if !validation_results.is_empty() {
            panic!("add_verse_numbers_before_headings validation for {} {} failed with {} issues: {:?}", work_name, bos_book_code, validation_results.len(), validation_results);
        }
    }

    result
}

/// (Debug) Validate the processed lines for common issues and return a list of error messages.
fn validate_preverse_marker_insertions(processed_lines: &InternalBibleEntryList) -> Vec<String> {
    let mut issues = Vec::new();

    if processed_lines.is_empty() {
        issues.push("No processed_lines entries to validate".to_string());
        return issues;
    }

    let have_another_close_preverse_marker = |start_idx: usize, entries: &InternalBibleEntryList| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == "v=" {
                return true;
            }
            if matches!(m, "v" | "v~") {
                return false;
            }
        }
        false
    };

    let mut _previous_marker = CompactString::new("");
    let mut _next_marker = CompactString::new("");
    let mut marker_counts: IndexMap<CompactString, usize> = IndexMap::new();
    for (n, entry) in processed_lines.iter().enumerate() {
        let current_marker: CompactString = entry.marker().into();
        *marker_counts.entry(current_marker.clone()).or_insert(0) += 1;
        if n < processed_lines.len() - 1 {
            _next_marker = processed_lines[n + 1].marker().into();
        } else {
            _next_marker = CompactString::new("");
        }

        if current_marker == "v=" {
            // if cfg!(debug_assertions) && !entry.clean_text().chars().all(|c| c.is_ascii_digit()) {
            //     println!("Validating verse start marker 'v=' '{}' at index {}: previous markers are '{}', '{}', following markers are '{}', '{}', '{}', '{}'",
            //         entry.clean_text(), n, processed_lines[n - 2].marker().to_string(),
            //         previous_marker, next_marker,
            //         processed_lines[n + 2].marker().to_string(),
            //         processed_lines[n + 3].marker().to_string(),
            //         processed_lines[n + 4].marker().to_string());
            // }
            if !SECTION_HEADER_FIELDS_PRECEDED_BY_PREVERSE_NUMBER.contains(&_next_marker.as_str()) {
                issues.push(format!(
                    "Preverse number marker 'v=' at index {} is not followed by a verse or section marker (found '{}')",
                    n, _next_marker));
            }

            if have_another_close_preverse_marker( n, &processed_lines) {
                issues.push(format!(
                    "Preverse number marker 'v=' at index {} is followed closely by another preverse marker: {}",
                    n, processed_lines.slice(n-1, n+10)));
                }
        }

        _previous_marker = current_marker;
    }
    assert!(
        marker_counts.get("v=").cloned().unwrap_or(0)
            <= marker_counts.get("s1").cloned().unwrap_or(0)
                + marker_counts.get("s2").cloned().unwrap_or(0)
                + marker_counts.get("s3").cloned().unwrap_or(0)
                + marker_counts.get("s4").cloned().unwrap_or(0)
                + marker_counts.get("ms1").cloned().unwrap_or(0)
                + marker_counts.get("ms2").cloned().unwrap_or(0)
                + marker_counts.get("sp").cloned().unwrap_or(0),
        "There should not be more preverse 'v=' markers than section markers, but found {} 'v=' markers and {} section markers",
        marker_counts.get("v=").cloned().unwrap_or(0),
        marker_counts.get("s1").cloned().unwrap_or(0)
            + marker_counts.get("s2").cloned().unwrap_or(0)
            + marker_counts.get("s3").cloned().unwrap_or(0)
            + marker_counts.get("s4").cloned().unwrap_or(0)
            + marker_counts.get("ms1").cloned().unwrap_or(0)
            + marker_counts.get("ms2").cloned().unwrap_or(0)
            + marker_counts.get("sp").cloned().unwrap_or(0)
    ); // This is a sanity check to make sure we don't have an unexpected number of v= markers

    issues
}

/// Add nesting and end markers to a list of processed Internal
/// Bible entries. (End markers start with the '¬' character.)
///
/// Note that although nb is considered as a USFM paragraph marker,
///   it's a special case, and when encountered, it will cause a
///   close 'nb' to be added before the '¬c' and the new 'c' marker
///   (rather than the normal close paragraph marker),
///   but the 'nb' itself is closed with that original paragraph marker,
///   i.e., the '¬nb' will occur in the list BEFORE the 'nb', not after,
///   and both of those will be inside the 'p'/'¬p' (or similar) block.
//
// This complex logic (with lots of look-ahead) is done at Bible load time,
//    to make it easier to work with the data in later processing and output stages.
pub fn add_nesting_markers(
    entries: InternalBibleEntryList, work_name: &str, bos_book_code: &str,
) -> InternalBibleEntryList {
    log::info!(
        "    add_nesting_markers for {} {} started with {} entries",
        work_name,
        bos_book_code,
        entries.len()
    );

    let entries_vec = entries.into_vec();
    let num_entries = entries_vec.len();
    let mut new_lines = InternalBibleEntryList::with_capacity(num_entries * 1.1 as usize);
    
    // Context tracking
    let mut open_markers: Vec<CompactString> = Vec::new();
    let mut open_list_levels: Vec<u32> = Vec::new();
    let mut current_chapter = CompactString::from("-1");
    let mut current_verse = CompactString::from("-1");
    let mut last_marker: Option<CompactString> = None;
    let mut last_p_marker: Option<CompactString> = None;
    // TODO: Remove last_s_marker because we can see if 's1' is in open_markers instead
    let mut last_s_marker: Option<CompactString> = None;
    let mut last_l_marker: Option<CompactString> = None;
    let mut section_crosses_chapters = HashMap::new();
    for section_marker in NESTABLE_SECTION_MARKERS { section_crosses_chapters.insert(CompactString::from(*section_marker), false); }

    // Helper functions for look-ahead
    let _chapter_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == "c" {
                return true;
            }
            if matches!(m, "v" | "v~") {
                return false;
            }
        }
        true
    };

    let verse_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if matches!(m, "v" | "c") {
                return true;
            }
            if m == "v~" {
                return false;
            }
            if m == "v="
                || heading_markers::is_heading(m)
                || paragraph_markers::is_paragraph(m)
                || main_text_list_markers::is_main_text_list(m)
                || intro_outline_markers::is_intro_outline(m)
                || intro_list_markers::is_intro_list(m)
                || m == "r"
                || m == "sp"
                || m == "rem"
                || m == "nb"
                // || m.starts_with('¬')
            {
                continue;
            }
            return true;
        }
        true
    };

    let section_has_ended = |current_marker: &str, start_idx: usize, entries: &[InternalBibleEntry]| {
        // let mut other_possibilities = Vec::new();
        // if let Some(level_char) = current_marker.chars().last()
        //     && level_char.is_ascii_digit()
        //     && level_char > '1'
        // {
        //     let level = level_char.to_digit(10).unwrap();
        //     let base = &current_marker[..current_marker.len() - 1];
        //     for z in 1..level {
        //         other_possibilities.push(format!("{}{}", base, z));
        //     }
        // }
        // if matches!(current_marker, "s1" | "s2" | "s3" | "s4") {
        //     other_possibilities.push("ms1".to_string());
        //     other_possibilities.push("ms2".to_string());
        // }

        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == current_marker || m == "v=" || NESTABLE_SECTION_MARKERS.iter().any(|p| *p == m) {
                return true;
            }
            if matches!(m, "v" | "v~") {
                return false;
            }
        }
        true
    };

    let ms1_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            // "v=" comes before section headings and some other list markers
            if m == "ms1" {
                return true;
            }
            if matches!(m, "v" | "v~") {
                return false;
            }
        }
        true
    };

    let paragraph_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            // "v=" comes before section headings and some other list markers
            if paragraph_markers::is_paragraph(m) || m == "v=" || main_text_list_markers::is_main_text_list(m) {
                return true;
            }
            if matches!(m, "v" | "v~") {
                return false;
            }
        }
        true
    };

    let list_item_has_ended = |current_marker: &str, start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            // "v=" comes before section headings and some other list markers
            if m == current_marker || paragraph_markers::is_paragraph(m) {
                return true;
            }
            if matches!(m, "v" | "v~") {
                return false;
            }
        }
        true
    };

    let previous_verse_start_marker = |start_idx: usize, entries: &[InternalBibleEntry]| -> Option<CompactString> {
        for entry in entries.iter().take(start_idx + 1).rev() {
            let m = entry.marker();
            if m == "v" || m == "v=" {
                return Some(CompactString::from(m));
            }
            if m == "v~" || m == "p" || m == "rem" || m == "nb" || m == "c" || m == "s1" || m == "s2" || m == "s3" || m == "s4" || m == "ms1" || m == "ms2" || m == "ms3" || m == "sp" || m == "q1" || m == "q2" || m == "q3" || m == "m" || m == "b" || m == "r" || heading_markers::is_heading(m) || main_text_list_markers::is_main_text_list(m) || paragraph_markers::is_paragraph(m) {
                continue;
            }
            if m.starts_with('¬') {
                continue;
            }
            // If we hit a marker that is not clearly a verse continuation context,
            // stop scanning since the preceding verse start is not tightly connected.
            break;
        }
        None
    };

    let list_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if main_text_list_markers::is_main_text_list(m) {
                return false;
            }
            if matches!(m, "v" | "v~" | "rem") {
                continue;
            }
            if paragraph_markers::is_paragraph(m) || m == "v=" || heading_markers::is_heading(m) || m == "c" {
                return true;
            }
            return true;
        }
        true
    };

    // let find_next_relevant_list_marker = |start_idx: usize, entries: &[InternalBibleEntry]| {
    //     for entry in entries.iter().skip(start_idx + 1) {
    //         let m = entry.marker();
    //         if !matches!(m, "c" | "v" | "v~") {
    //             return Some(CompactString::from(m));
    //         }
    //     }
    //     None
    // };

    let has_nb_after_c = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == "nb" {
                return true;
            }
            // Stop looking if we hit another section or paragraph marker
            if matches!(m, "c" | "s1" | "s2" | "s3" | "s4" | "p" | "q1" | "m") {
                return false;
            }
        }
        false
    };

    let (mut c, mut v) = ("0", "0");
    for j in 0..num_entries {
        let entry = &entries_vec[j];
        let marker = entry.marker();
        let marker_owned = CompactString::from(marker);
        let text = entry.clean_text();
        if have_strict_checking_flag() || cfg!(debug_assertions) {
            println!("{}/ Process {} {} {}:{} marker='{}' clean_text='{}' open_markers=[{}]", j, work_name, bos_book_code, current_chapter, current_verse, marker, abbreviate::<48, 24>(text), open_markers.join(", "));
        }

        if current_chapter == "-1" {
            current_verse = CompactString::from(new_lines.len().to_string());
        }

        // Header and Intro logic
        if ["h", "mt1", "mt2", "mt3"].contains(&marker) && !open_markers.iter().any(|m| m == "headers") {
            new_lines.push(InternalBibleEntry::nesting_marker("headers"));
            open_markers.push(CompactString::from("headers"));
        }

        if introduction_markers::is_introduction(marker)
            && !open_markers.iter().any(|m| m == "intro")
            && (marker != "iex" || !open_markers.iter().any(|m| m == "c"))
        {
            if let Some(pos) = open_markers.iter().position(|m| m == "headers") {
                let hm = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", hm), "").unwrap());
            }
            new_lines.push(InternalBibleEntry::nesting_marker("intro"));
            open_markers.push(CompactString::from("intro"));
        }

        if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            && last_open == "iot"
            && !intro_outline_markers::is_intro_outline(marker)
        {
            open_markers.pop();
            new_lines.push(InternalBibleEntry::end_marker("¬iot", "").unwrap());
        }
        if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            && last_open == "ilist"
            && !intro_list_markers::is_intro_list(marker)
        {
            open_markers.pop();
            new_lines.push(InternalBibleEntry::end_marker("¬ilist", "").unwrap());
        }

        // The following markers will NOT necessarily force a list to close
        if !["v","v~","rem","c","v="].contains(&marker)
            && !main_text_list_markers::is_main_text_list(marker)
            && !paragraph_markers::is_paragraph(marker)
            && !heading_markers::is_heading(marker)
        {
            if list_has_ended(j, &entries_vec) {
                close_lists_down_to(0, &mut open_markers, &mut open_list_levels, &mut new_lines);
                last_l_marker = None;
            }
        }

        // if let Some(last_open) = open_markers.last().map(|s| s.to_string())
        //     && last_open == "list"
        //     && !main_text_list_markers::is_main_text_list(marker)
        //     && marker != "v~"
        // {
        //     let close = if let Some(next_list_m) = find_next_relevant_list_marker(j, &entries_vec) {
        //         !main_text_list_markers::is_main_text_list(next_list_m.as_str())
        //     } else {
        //         true
        //     };
        //     if close {
        //         open_markers.pop();
        //         new_lines.push(InternalBibleEntry::simple("¬list", ""));
        //     }
        // }

        if marker == "c" {
            // println!("At c with open_markers=[{}]", open_markers.join(", "));
            (c, v) = (text, "0");

            for _ in 0..3 {
                if let Some(last_open) = open_markers.last().map(|s| s.to_string())
                    && (last_open == "headers" || last_open == "intro"  || last_open == "is1")
                {
                    open_markers.pop();
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open), "").unwrap());
                }
                else { break; }
            }

            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).unwrap());
            }

            // Check if there's an nb marker after this chapter
            let nb_follows = has_nb_after_c(j, &entries_vec);

            // Handle the paragraph with nb lookahead
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                if nb_follows {
                    // nb extends this paragraph across chapters
                    // Close with ¬nb instead of ¬p or whatever to indicate section break
                    // BUT keep the paragraph on the stack so it can be closed later
                    new_lines.push(InternalBibleEntry::end_marker("¬nb", "").unwrap());
                    // Do NOT remove from open_markers - paragraph continues
                    // Do NOT clear last_p_marker - it will be closed at the next paragraph
                } else {
                    // Paragraph is ending - close it BEFORE closing the previous chapter
                    let pm = open_markers.remove(pos);
                    assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} after v= with open_markers=[{}]", pm, open_markers.join(", "));
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", pm), "").unwrap());
                    last_p_marker = None;
                }
            }

            // Close a section BEFORE closing the chapter if it hasn't crossed chapter boundaries
            if let Some(last_s) = &last_s_marker
            && let Some(s_pos) = open_markers.iter().rposition(|m| NESTABLE_SECTION_MARKERS.contains(&&m.as_str())) {
                if section_has_ended(last_s, j, &entries_vec)
                && !section_crosses_chapters[last_s] {
                    // println!(
                    //     "  At {} {}:{} processing chapter marker and closing section that hasn't crossed chapter boundaries: last_s='{}' Current open markers: {}",
                    //     j, c, v, last_s, open_markers.join(", "));
                    if have_strict_checking_flag() || cfg!(debug_assertions) {
                        assert!(s_pos == open_markers.len()-1 || open_markers.contains(&CompactString::new("list")),
                            "Expected {} {} {}:{} '{}' to be last marker (not {}) in [{}] with last_s_marker='{:?}'",
                            work_name, bos_book_code, c, v,
                            last_s, s_pos, open_markers.join(", "), last_s_marker); // Must be the last marker then
                    }
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_s), "").unwrap());
                    open_markers.remove(s_pos); // Could do pop here
                    last_s_marker = None;
                }
                else {
                    // println!(
                    //     "At {} {}:{} processing chapter marker and seems like section has crossed chapter boundaries: last_s='{}' Current open markers: {}",
                    //     j, c, v, last_s, open_markers.join(", "));
                    section_crosses_chapters.insert(last_s.clone(), true);
                }
            }

            // Close the previous chapter
            // Close any open list-item markers (li1, li2, ...) before closing the previous chapter
            while let Some(top) = open_markers.last().cloned() {
                if is_list_item_marker(top.as_str()) {
                    open_markers.pop();
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", top), "").unwrap());
                } else {
                    break;
                }
            }

                // Close the previous chapter
                if let Some(c_pos) = open_markers.iter().rposition(|m| m == "c") {
                    let _m = open_markers.remove(c_pos);
                    new_lines.push(InternalBibleEntry::end_marker("¬c", current_chapter.as_str()).unwrap());
                }

            // Close a section AFTER closing the chapter if it has crossed chapter boundaries
            if let Some(last_s) = &last_s_marker
            && let Some(s_pos) = open_markers.iter().rposition(|m| NESTABLE_SECTION_MARKERS.contains(&&m.as_str())) {
                if section_has_ended(last_s, j, &entries_vec)
                && section_crosses_chapters[last_s] {
                    // println!(
                    //     "At {} {}:{} processing chapter marker and closing section that has crossed chapter boundaries: last_s='{}' Current open markers: {}",
                    //     j, c, v, last_s, open_markers.join(", "));
                    // The next line isn't always true because there may be a list open after the section marker, so we can't assert that the section marker is the last one in open_markers.
                    // assert_eq!(s_pos, open_markers.len()-1, "Expected {} to be last marker (not {}) in [{}] with last_s_marker='{:?}'", last_s, s_pos, open_markers.join(", "), last_s_marker); // Must be the last marker then
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_s), "").unwrap());
                    open_markers.remove(s_pos); // Could do pop here
                    last_s_marker = None;
                }
            }

            if !open_markers.iter().any(|m| m == "chapters") {
                new_lines.push(InternalBibleEntry::nesting_marker("chapters"));
                open_markers.push(CompactString::from("chapters"));
            }

            current_chapter = CompactString::from(text);
            current_verse = CompactString::from("0");
            open_markers.push(marker_owned.clone()); // Save the c marker
        }
        
        else if marker == "v" {
            v = text;
            // If the previous raw entry was a verse continuation (v~) but we don't
            // currently have an open 'v' in open_markers, then emit a missing
            // verse end marker so that sequences like v~ then v get a ¬v between them.
            if j > 0 && entries_vec[j - 1].marker() == "v~" && !open_markers.iter().any(|m| m == "v") {
                let prev_start_marker = previous_verse_start_marker(j - 1, &entries_vec);
                if prev_start_marker.as_deref() == Some("v") {
                    println!("[debug] Inserting missing ¬v at index {} after {}:{} open_markers=[{}] last_p_marker={:?} last_s_marker={:?} prev_start_marker={:?}", j, c, v, open_markers.join(", "), last_p_marker, last_s_marker, prev_start_marker);
                    let start_ctx = if j >= 5 { j-5 } else { 0 };
                    let end_ctx = std::cmp::min(num_entries, j + 5);
                    for k in start_ctx..end_ctx {
                        println!("   raw[{}] = {} '{}'", k, entries_vec[k].marker(), entries_vec[k].clean_text());
                    }
                    new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).unwrap());
                }
            }
            // For verse markers, we want to close any open verse if the verse is ending
            //  and close any open paragraph if the verse is ending and the next marker is not a continuation of the verse.
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).expect("msg"));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker
                        && last_open_m == last_p.as_str()
                        && paragraph_has_ended(j, &entries_vec)
                    {
                        // Paragraph is ending - close it BEFORE closing the verse
                        assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "At {}:{} adding ¬{} after v= with open_markers=[{}]", c, v, last_open_m, open_markers.join(", "));
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").unwrap());
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }
            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).unwrap());
            }
            current_verse = CompactString::from(text);
            if marker == "v" {
                open_markers.push(marker_owned.clone());
            }
        }

        else if marker == "v=" { // Then we're about to hit a section heading or similar
            // if current_chapter.as_str() == "50" && text.as_str() == "15" {
            //     eprintln!("DEBUG v= before section: j={} current_chapter='{}' current_verse='{}' last_s_marker={:?} last_p_marker={:?} open_markers=[{}]", j, current_chapter, current_verse, last_s_marker, last_p_marker, open_markers.join(", "));
            // }
            // For verse markers, we want to close any open verse if the verse is ending
            //  and close any open paragraph if the verse is ending and the next marker is not a continuation of the verse.
            if cfg!(debug_assertions) {
                println!("  At {} {}:{} processing preverse marker {} = '{}': last_p_marker='{}' last_s_marker='{}' Current open markers: {}",
                            j, c, v, marker, text, last_p_marker.clone().unwrap_or_default(), last_s_marker.clone().unwrap_or_default(), open_markers.join(", "));
            }
            for _ in 0..9 {
                // println!("    At {} {}:{} processing preverse marker {} = '{}': last_p_marker='{}' last_s_marker='{}' Current open markers: {}",
                //             jj, c, v, marker, text, last_p_marker.clone().unwrap_or_default(), last_s_marker.clone().unwrap_or_default(), open_markers.join(", "));
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    // Close any open verse (if it's actually ended)
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).unwrap());
                        made_change = true;
                    }
                    // Close any open paragraph
                    if let Some(last_p) = &last_p_marker
                        // && last_open_m == last_p.as_str()
                        && paragraph_has_ended(j, &entries_vec)
                        {
                        // Paragraph is ending - close it BEFORE closing the verse
                        // but the paragraph might be followed by an open verse marker in open_markers
                        assert_ne!(new_lines.last().expect("Must be there").marker(), "v=",
                            "At {}:{} adding ¬{} before v= with last_p_marker='{}' open_markers=[{}]",
                            c, v, last_open_m, last_p_marker.clone().unwrap_or_default(), open_markers.join(", "));
                        if let Some(pos) = open_markers.iter().rposition(|m| m == last_p) {
                            open_markers.remove(pos);
                            new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_p), "").unwrap());
                            made_change = true;
                        }
                    }
                    // Close any open lists
                    if open_markers.iter().any(|m| is_list_item_marker(m) || m == "list")
                        && list_has_ended(j, &entries_vec)
                    {
                        close_lists_down_to(0, &mut open_markers, &mut open_list_levels, &mut new_lines);
                        last_l_marker = None;
                        made_change = true;
                    }
                    // If the last open marker was a section, and the section has ended, then close it
                    // Note that sections can cross chapter boundaries,
                    //  so open_markers may have a chapter marker after the section marker
                    //  but we still want to close the section if it has ended.
                    if let Some(last_s) = &last_s_marker
                    && let Some(pos) = open_markers.iter().rposition(|m| m == last_s)
                    && section_has_ended(last_s, j, &entries_vec){
                            open_markers.remove(pos);
                            new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_s), "").unwrap());
                            made_change = true;
                        }
                    // if let Some(last_s) = &last_s_marker
                    //     && last_open_m == last_s.as_str()
                    //     && section_has_ended(last_s, j, &entries_vec)
                    // {
                    //     println!("    Removing {} from end of {:?}", last_s, open_markers);
                    //     assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} before v= with open_markers=[{}]", last_open_m, open_markers.join(", "));
                    //     open_markers.pop();
                    //     new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").unwrap());
                    //     made_change = true;
                    // }
                }
                    // If there's an open section (followed by an open chapter), then close the open section here
                if !made_change { break; }
            }

            // Close an open ms1 section if necessary
            if let Some(pos) = open_markers.iter().rposition(|m| m == "ms1")
            && ms1_has_ended(j, &entries_vec) {
                open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker("¬ms1", "").unwrap());
            }

            if open_markers.contains(&CompactString::from("s1")) || open_markers.contains(&CompactString::from("p")) || open_markers.contains(&CompactString::from("v")) {
                assert!(open_markers.contains(&CompactString::from("c")), "open_markers=[{}]", open_markers.join(", ")); }

            // If this current preverse marker is before a section heading, close any open section now so the end marker precedes the v=.
            if let Some(last_s) = &last_s_marker
                && section_has_ended(last_s, j, &entries_vec)
                && let Some(_s_pos) = open_markers.iter().rposition(|m| m == last_s)
            {
                // if current_chapter.as_str() == "50" && text.as_str() == "15" {
                //     eprintln!("DEBUG v= closing section last_s={} s_pos={} open_markers_before=[{}]", last_s, s_pos, open_markers.join(", "));
                // }
                while open_markers.last().map(|m| m.as_str()) == Some(last_s.as_str()) {
                    let m = open_markers.pop().unwrap();
                    // if current_chapter.as_str() == "50" && text.as_str() == "15" {
                    //     eprintln!("DEBUG v= popping before last_s: {}", m);
                    // }
                    assert!(!["c","v"].contains(&m.as_str()), "Unexpectedly trying to close {} before v= with open_markers=[{}]", m, open_markers.join(", "));
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").unwrap());
                }
                // open_markers.pop();
                // if current_chapter.as_str() == "50" && text.as_str() == "15" {
                //     eprintln!("DEBUG v= closed last_s {} open_markers_after=[{}]", last_s, open_markers.join(", "));
                // }
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_s), "").unwrap());
                last_s_marker = None;
            }
            current_verse = CompactString::from(text);
            if open_markers.contains(&CompactString::from("s1")) || open_markers.contains(&CompactString::from("p")) || open_markers.contains(&CompactString::from("v")) {
                assert!(open_markers.contains(&CompactString::from("c")), "open_markers=[{}]", open_markers.join(", ")); }
        // Not true if it precedes a s2 section heading
        // assert!(!open_markers.contains(&CompactString::from("s1")), "last_s_marker='{}' open_markers=[{}]", last_s_marker.as_deref().unwrap_or("None"), open_markers.join(", "));
        }
        
        else if heading_markers::is_heading(marker) { // e.g., s1, s2, but also including 'ms1','ms2', and 'is1', etc.
            if list_has_ended(j, &entries_vec) {
                close_lists_down_to(0, &mut open_markers, &mut open_list_levels, &mut new_lines);
                last_l_marker = None;
            }
            // For heading markers, we want to close any open verse, paragraph, or section if the heading is ending them.
            for _ in 0..9 {
                // println!("       {} loop with marker={}, last_p_marker={:?} last_s_marker={:?} and open_markers=[{}]", q_q, marker, last_p_marker, last_s_marker, open_markers.join(", "));
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).unwrap());
                        made_change = true;
                    } else if let Some(last_s) = &last_s_marker
                        && last_open_m == last_s.as_str()
                        && (marker==last_s || section_has_ended(last_s, j, &entries_vec))
                    {
                        assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "HERE Adding ¬{} after v= with open_markers=[{}]", last_open_m, open_markers.join(", "));
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").unwrap());
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if last_open_m == last_p.as_str() {
                            if have_strict_checking_flag() || cfg!(debug_assertions) {
                                assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} after v= with open_markers=[{}]", last_open_m, open_markers.join(", ")); }
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").unwrap());
                            made_change = true;
                        }
                    }
                }
                // See if we already have this current marker in open markers (albeit not at the end)
                if let Some(pos) = open_markers.iter().rposition(|m| m == marker) {
                    // println!("             {} Removing {} header marker from open_markers=[{}]", q_q, marker, open_markers.join(", "));
                    let m = open_markers.remove(pos);
                    assert_ne!(m.as_str(), "c");
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").unwrap());
                    made_change = true;
                }
                if !made_change {
                    break;
                }
            }
            if verse_has_ended(j, &entries_vec)
                && let Some(pos) = open_markers.iter().rposition(|m| m == "v")
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).unwrap());
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                assert_ne!(m.as_str(), "c");
                assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} after v= with open_markers=[{}]", m, open_markers.join(", "));
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").unwrap());
            }
            // // This code also closes 's2' markers which aren't open
            // if let Some(ls) = &last_s_marker
            //     && let Some(pos) = open_markers.iter().rposition(|m| m == ls)
            // {
            //     let m = open_markers.remove(pos);
            //     new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), ""));
            // }
            last_p_marker = None;
            if NESTABLE_SECTION_MARKERS.contains(&marker) {
                assert!(!open_markers.contains(&marker_owned),
                    "add_nesting_markers for {} {} {} {}:{} about to add another {} to {:?}",
                    work_name, bos_book_code, j, current_chapter, current_verse, marker, open_markers);
                section_crosses_chapters.insert(CompactString::from(marker), false);
                open_markers.push(marker_owned.clone());
                last_s_marker = Some(marker_owned.clone());
            }
        }
        
        else if main_text_list_markers::is_main_text_list(marker) {
            // NOTE: These MUST come before the paragraph marker check (because these markers are included)
            // For main text list markers, we want to close any open verse or paragraph before the list entry.
            for _ in 0..9 {
                let mut made_change = false;
                if verse_has_ended(j, &entries_vec) {
                    if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                        let m = open_markers.remove(pos);
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).unwrap());
                        made_change = true;
                    }
                }
                if let Some(last_p) = &last_p_marker {
                    if let Some(pos) = open_markers.iter().rposition(|m| m == last_p) {
                        let pm = open_markers.remove(pos);
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", pm), "").unwrap());
                        last_p_marker = None;
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }

            let new_level = get_list_level(marker);
            let current_list_level = open_list_levels.last().copied();

            match current_list_level {
                None => {
                    // No list currently open: open root list container
                    new_lines.push(InternalBibleEntry::simple("list", new_level.to_string()));
                    open_markers.push(CompactString::from("list"));
                    open_list_levels.push(new_level);
                    open_markers.push(marker_owned.clone());
                }
                Some(curr_lvl) if new_level == curr_lvl => {
                    // Same level: close previous list item of this level, then push new list item
                    close_lists_down_to(new_level, &mut open_markers, &mut open_list_levels, &mut new_lines);
                    open_markers.push(marker_owned.clone());
                }
                Some(curr_lvl) if new_level > curr_lvl => {
                    // Deeper level: open embedded sub-list container inside the parent item
                    new_lines.push(InternalBibleEntry::simple("list", new_level.to_string()));
                    open_markers.push(CompactString::from("list"));
                    open_list_levels.push(new_level);
                    open_markers.push(marker_owned.clone());
                }
                Some(_curr_lvl) => {
                    // Shallower level: close deeper items and sub-list containers down to new_level
                    close_lists_down_to(new_level, &mut open_markers, &mut open_list_levels, &mut new_lines);
                    open_markers.push(marker_owned.clone());
                }
            }
            last_l_marker = Some(marker_owned.clone());
        }
        
        else if marker == "nb" { // NOTE: This MUST come before the paragraph marker check (because this marker is included)
            // nb is a NOP for nesting - it's just a paragraph marker that extends across chapters
        }
        
        else if paragraph_markers::is_paragraph(marker) {
            // For paragraph markers, we want to close any open verse if the paragraph is ending.
            if verse_has_ended(j, &entries_vec)
                && let Some(pos) = open_markers.iter().rposition(|m| m == "v")
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).unwrap());
            }

            // Close all open list items and containers in LIFO order
            close_lists_down_to(0, &mut open_markers, &mut open_list_levels, &mut new_lines);
            last_l_marker = None;

            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let pm = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", pm), "").unwrap());
            }

            if have_strict_checking_flag() || cfg!(debug_assertions) {
                assert!(!open_markers.iter().any(|m| is_list_item_marker(m)),
                    "At {} {} {} {}:{} handling paragraph marker {} = '{}' open_markers=[{}] last_p_marker={:?} last_l_marker={:?} last_s_marker={:?}",
                        work_name, bos_book_code, j, c, v, marker, text, open_markers.join(", "), last_p_marker, last_l_marker, last_s_marker);
                assert!(!open_markers.iter().any(|m| m == "list"),
                    "At {} {}{} {}:{} handling paragraph marker {} = '{}' open_markers=[{}] last_p_marker={:?} last_l_marker={:?} last_s_marker={:?}",
                        work_name, bos_book_code, j, c, v, marker, text, open_markers.join(", "), last_p_marker, last_l_marker, last_s_marker);
            }

            open_markers.push(marker_owned.clone());
            last_p_marker = Some(marker_owned.clone());
        }
        
        else if marker == "rem" {
            if verse_has_ended(j, &entries_vec) {
                if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                    let _m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).unwrap());
                }
            }
            if let Some(last_l) = &last_l_marker
            && list_item_has_ended(last_l, j, &entries_vec) {
                if let Some(l_pos) = open_markers.iter().rposition(|m| m == last_l) {
                    open_markers.remove(l_pos);
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_l), "").unwrap());
                    last_l_marker = None;
                }
            }
        }
        
        else if marker == "iot" {
            open_markers.push(CompactString::from("iot"));
        }
        
        else if intro_outline_markers::is_intro_outline(marker) {
            let should_open = if let Some(lm) = &last_marker {
                lm != "iot" && !intro_outline_markers::is_intro_outline(lm)
            } else {
                true
            };
            if should_open {
                new_lines.push(InternalBibleEntry::nesting_marker("iot"));
                open_markers.push(CompactString::from("iot"));
            }
        }
        
        else if intro_list_markers::is_intro_list(marker) {
            let should_open = last_marker
                .as_ref()
                .is_none_or(|lm| !intro_list_markers::is_intro_list(lm));
            if should_open {
                new_lines.push(InternalBibleEntry::nesting_marker("ilist"));
                open_markers.push(CompactString::from("ilist"));
            }
        }
        
        // else if major_section_markers::is_major_section(marker) { // like ms1, ms2, ms3
        //     panic!("Can't get here because handled above in section markers");
        //     // For major section markers, we want to close any open verse, paragraph, or section if the major section is ending.
        //     for _ in 0..9 {
        //         let mut made_change = false;
        //         if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
        //             if last_open_m == "headers" || last_open_m == "intro" {
        //                 open_markers.pop();
        //                 new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").unwrap());
        //                 made_change = true;
        //             } else if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
        //                 open_markers.pop();
        //                 new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).unwrap());
        //                 made_change = true;
        //             } else if let Some(last_p) = &last_p_marker {
        //                 if last_open_m == last_p.as_str() {
        //                     open_markers.pop();
        //                     new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").unwrap());
        //                     made_change = true;
        //                 }
        //             } else if let Some(last_s) = &last_s_marker {
        //                 if last_open_m == last_s.as_str() && section_has_ended(last_s, j, &entries_vec) {
        //                     open_markers.pop();
        //                     new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").unwrap());
        //                     made_change = true;
        //                 }
        //             } else if last_open_m == "c" && chapter_has_ended(j, &entries_vec) {
        //                 open_markers.pop();
        //                 new_lines.push(InternalBibleEntry::end_marker("¬c", current_chapter.as_str()).unwrap());
        //                 made_change = true;
        //             } else if last_open_m == marker {
        //                 open_markers.pop();
        //                 new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", marker), "").unwrap());
        //                 made_change = true;
        //             }
        //         }
        //         if !made_change {
        //             break;
        //         }
        //     }

        //     if !open_markers.iter().any(|m| m == "chapters") {
        //         new_lines.push(InternalBibleEntry::nesting_marker("chapters"));
        //         open_markers.push(CompactString::from("chapters"));
        //     } else if let Some(lp) = &last_p_marker
        //         && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
        //     {
        //         let m = open_markers.remove(pos);
        //         new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").unwrap());
        //     }

        //     if let Some(ls) = &last_s_marker
        //         && let Some(pos) = open_markers.iter().rposition(|m| m == ls)
        //     {
        //         let m = open_markers.remove(pos);
        //         new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
        //     }

        //     if let Some(pos) = open_markers.iter().rposition(|m| m == marker) {
        //         let m = open_markers.remove(pos);
        //         new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
        //     }
        //     open_markers.push(marker_owned.clone());
        //     last_p_marker = None;
        //     last_s_marker = Some(marker_owned.clone());
        // }
        
        else if marker == "vp#" {
            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).unwrap());
            }
        }
        
        else if marker == "ie" { // optional so can't rely on this
            if let Some(pos) = open_markers.iter().rposition(|m| m == "is1") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).unwrap());
            }
        }
        
        else if usfm_markers::get_marker_content_type(marker) == Some('N') { // This is a marker that NEVER has content
            // For other USFM markers that we haven't specifically handled, we want to close any open verse if the marker is ending the verse.
            for _ in 0..999 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).unwrap());
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker
                        && last_open_m == last_p.as_str()
                    {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").unwrap());
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }
            if verse_has_ended(j, &entries_vec)
                && let Some(pos) = open_markers.iter().rposition(|m| m == "v")
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).unwrap());
            }
        }

        if have_strict_checking_flag() || cfg!(debug_assertions) { // End of loop checks
            if open_markers.contains(&CompactString::from("chapters")) {
                assert!(!open_markers.contains(&CompactString::from("headers")), "open_markers=[{}]", open_markers.join(", "));
                assert!(!open_markers.contains(&CompactString::from("intro")), "open_markers=[{}]", open_markers.join(", "));
            }
        }

        // End of loop code
        if have_strict_checking_flag() || cfg!(debug_assertions) {
            let last_pushed_marker = new_lines.iter().last().map(|e| e.marker().to_string());
            if let Some(last_pushed) = last_pushed_marker {
                if marker == "s1" && !["FRT","INT"].contains(&bos_book_code) {
                    assert_ne!(last_pushed, "¬s1"); } // Should be "v="
            }
        }
        // if marker == "ms1" { println!("            Before ms1 was {:?}", new_lines.iter().last())}
        // if marker == "mr"  { println!("            Before mr was {:?}", new_lines.iter().last())}
        new_lines.push(entry.clone()); // Push this current marker and entry
        
        last_marker = Some(marker_owned);
        if !["FRT","INT"].contains(&bos_book_code)
        && (open_markers.contains(&CompactString::from("s1")) || open_markers.contains(&CompactString::from("p")) || open_markers.contains(&CompactString::from("v"))) {
            assert!(open_markers.contains(&CompactString::from("c")), "open_markers=[{}]", open_markers.join(", "));
        }
    }

    // Close any left-over open markers
    if (have_strict_checking_flag() || cfg!(debug_assertions))
    && !["FRT","INT"].contains(&bos_book_code)
    && (open_markers.contains(&CompactString::from("s1")) || open_markers.contains(&CompactString::from("p")) || open_markers.contains(&CompactString::from("v"))) {
        assert!(open_markers.contains(&CompactString::from("c")) && open_markers.contains(&CompactString::from("chapters")),
            "add_nesting_markers() finished processing {} {} entries but open_markers is missing 'c' or 'chapters': {:?}",
            work_name, bos_book_code, open_markers); }
    if cfg!(debug_assertions) && !open_markers.is_empty() {
        println!("add_nesting_markers() finished processing {} {} entries, now closing remaining open markers: {}",
            work_name, bos_book_code, open_markers.join(", "));
    }
    while let Some(marker) = open_markers.pop() {
        let mut end_marker_str = CompactString::from("¬");
        end_marker_str.push_str(&marker);
        let with_text = if marker == "v" {
            current_verse.as_str()
        } else if marker == "c" {
            // However, if there's a paragraph marker still open, we should probably close that first
            // (Is that logic correct as this problem only occurs with nb which spans the chapter!!! ???)
            if paragraph_markers::ALL.contains(&open_markers.last().unwrap().as_str()) {
                let pm = open_markers.pop().unwrap();
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", pm), "").unwrap());
            }
            current_chapter.as_str()
        } else if marker == "list" {
            let lvl = open_list_levels.pop().unwrap_or(1);
            let s = CompactString::from(lvl.to_string());
            new_lines.push(InternalBibleEntry::end_marker(end_marker_str, s).unwrap());
            continue;
        } else { "" }; // For s1 and chapter markers, we don't need to include any text in the end marker
        new_lines.push(InternalBibleEntry::end_marker(end_marker_str, with_text).unwrap());
    }
    assert!(open_markers.is_empty(), "add_nesting_markers() finished processing entries but open_markers is not empty: {:?}", open_markers);

    log::info!(
        "    add_nesting_markers for {} finishing with {} entries",
        bos_book_code,
        new_lines.len()
    );

    // No automatic deduping here; keep generated markers as-is so logic must be correct.

    if have_strict_checking_flag() || cfg!(debug_assertions) {
        let validation_results = validate_nesting(&new_lines);
        if !validation_results.is_empty() {
            eprintln!("add_nesting_markers() validation for {} {} produced {} issues:", work_name, bos_book_code, validation_results.len());
            for issue in &validation_results {
                eprintln!("  - {}", issue);
            }
            // Continue instead of panicking to allow inspection of processed output during debugging
        }
    }

    new_lines
}

/// (Debug) Validate the processed lines for common issues and return a list of error messages.
fn validate_nesting(processed_lines: &InternalBibleEntryList) -> Vec<String> {
    let mut issues = Vec::new();

    if processed_lines.is_empty() {
        issues.push("No processed_lines entries to validate".to_string());
        return issues;
    }

    // let mut previous_marker = CompactString::new("");
    let mut next_marker;
    let mut marker_counts: IndexMap<CompactString, usize> = IndexMap::new();
    let (mut c, mut v)= ("0", "0");
    for (n, entry) in processed_lines.iter().enumerate() {
        let current_marker: CompactString = entry.marker().into();
        *marker_counts.entry(current_marker.clone()).or_insert(0) += 1;
        if n < processed_lines.len() - 1 {
            next_marker = processed_lines[n + 1].marker().into();
        } else {
            next_marker = CompactString::new("");
        }

        if current_marker == "c" {
            (c, v) = (entry.clean_text(), "0");
        }
        else if current_marker == "v" {
            v = entry.clean_text();
        }
        else if current_marker == "v=" {
            if is_end_marker(&next_marker) {
                issues.push(format!(
                    "Preverse number marker 'v=' at index {} after {}:{} is followed by an end marker '{}'",
                    n, c, v, next_marker));
            } else if !["s1", "s2", "s3", "s4", "ms1", "ms2", "ms3", "sp"].contains(&next_marker.as_str()) {
                issues.push(format!(
                    "Preverse number marker 'v=' at index {} after {}:{} is not followed by a verse or section marker (found '{}')",
                    n, c, v, next_marker));
            }
        }
        else if current_marker == "v~" && next_marker == "v" {
            issues.push(format!(
                "Missing verse end marker '¬v' at index {} after {}:{} (found 'v' = '{}')",
                n, c, v, processed_lines[n + 1].clean_text()));
        }
        else if (is_main_text_list(&current_marker) || is_intro_list(&current_marker))
        && is_end_marker(&next_marker) {
            issues.push(format!(
                "List marker '{}' at index {} after {}:{} is followed by an end marker '{}'",
                current_marker, n, c, v, next_marker));
        }
        else if current_marker == "¬li1" && next_marker == "¬li2" {
            issues.push(format!(
                "Closed list entries in the wrong order at index {} after {}:{} with '¬li1' followed by '¬li2'",
                n, c, v));
        }

        // previous_marker = current_marker;
    }

    // Check that all end markers have a corresponding start marker with the same count
    for (marker, count) in &marker_counts {
        if is_end_marker(&marker) {
            let start_marker: CompactString = marker.chars().skip(1).collect();
            if count != marker_counts.get(&start_marker).unwrap_or(&0) {
                issues.push(format!(
                    "Marker '{}' has {} entries but its corresponding start marker has {} from [{}]",
                    marker, count, marker_counts.get(&start_marker).unwrap_or(&0),
                    processed_lines.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>().join(", ")));
            }
        }
    }

    issues
}

/// Calls add_verse_markers_before_headings and add_nesting_markers in sequence
///   (which is the normal use)
pub fn add_additional_markers(
    entries: InternalBibleEntryList,
    work_name: &str,
    bos_book_code: &str,
) -> InternalBibleEntryList {
    let list = add_preverse_markers_before_headings(entries, work_name, bos_book_code); // This is always done first
    add_nesting_markers(list, work_name, bos_book_code)
}

#[cfg(test)]
mod tests {
    use crate::set_strict_checking_flag;
    use crate::entry::InternalBibleEntry;
    use crate::entry_lists::InternalBibleEntryList;
    use crate::nesting::{add_preverse_markers_before_headings, add_additional_markers};

    #[test]
    fn test_add_verse_markers_before_headings_no_change() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Verse one text."));

        let list = add_preverse_markers_before_headings(list, "test_add_verse_markers_before_headings_no_change", "aaa"); // This is always done first

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            ["c", "p", "v", "v~"]
        );
    }

    #[test]
    fn test_add_preverse_markers_before_headings_simple() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse one text."));
        list.push(InternalBibleEntry::simple("s1", "Heading one"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Verse two text."));
        list.push(InternalBibleEntry::simple("c", "2"));
        list.push(InternalBibleEntry::simple("s1", "Heading two"));
        list.push(InternalBibleEntry::simple("q1", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse one text."));

        let list = add_preverse_markers_before_headings(list, "test_add_verse_markers_before_headings_simple", "bbb"); // This is always done first

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "c", "p", "v", "v~", "v=", "s1", "p", "v", "v~", "c", "v=", "s1", "q1", "v", "v~"
            ]
        );
        assert!(list[4].marker()=="v=" && list[4].adjusted_text()=="2"); // 'v=' should have the verse number of the following 'v'
        assert!(list[10].marker()=="v=" && list[10].adjusted_text()=="1"); // 'v=' should have the verse number of the following 'v'
    }

    #[test]
    fn test_add_preverse_markers_before_headings_complex() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse two initial text."));
        list.push(InternalBibleEntry::simple("s1", "Heading one in middle of verse two"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse two more text."));
        list.push(InternalBibleEntry::simple("v", "3"));
        list.push(InternalBibleEntry::simple("v~", "Verse three text."));
        list.push(InternalBibleEntry::simple("c", "2"));
        list.push(InternalBibleEntry::simple("s1", "Heading two at start of chapter two"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse one text."));
        list.push(InternalBibleEntry::simple("c", "3"));
        list.push(InternalBibleEntry::simple("nb", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple(
            "v~",
            "Chapter three Verse one text in same paragraph.",
        ));

        let list = add_preverse_markers_before_headings(list, "test_add_verse_markers_before_headings_complex", "ccc"); // This is always done first

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "c", "p", "v", "v~", "v", "v~", "v=", "s1", "p", "v~", "v", "v~", "c", "v=", "s1", "p", "v", "v~", "c",
                "nb", "v", "v~"
            ]
        );
        assert!(list[6].marker()=="v=" && list[6].adjusted_text()=="2b"); // This s1 is still in v2 -- the 'b' says it's the second part of the verse
        assert!(list[13].marker()=="v=" && list[13].adjusted_text()=="1"); // 'v=' should have the verse number of the following 'v'
    }

    #[test]
    fn test_add_preverse_markers_before_headings_multiple_headers() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("mt1", "Main title"));
        list.push(InternalBibleEntry::simple("ie", ""));
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("ms1", "Book one Main Section heading"));
        list.push(InternalBibleEntry::simple("mr", "(Covers these chapters"));
        list.push(InternalBibleEntry::simple("s1", "First section heading"));
        list.push(InternalBibleEntry::simple("rem", "Remark about first section heading"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse two text."));
        list.push(InternalBibleEntry::simple("s1", "Heading one in middle of verse two"));
        list.push(InternalBibleEntry::simple("s2", "Subheading 2"));
        list.push(InternalBibleEntry::simple("v", "3"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse three text."));
        list.push(InternalBibleEntry::simple("c", "2"));
        list.push(InternalBibleEntry::simple("s1", "Heading two at start of chapter two"));
        list.push(InternalBibleEntry::simple("rem", "Could be in here"));
        list.push(InternalBibleEntry::simple("s3", "Subheading 3"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse twoA text."));
        list.push(InternalBibleEntry::simple("ms1", "Book two Main Section heading"));
        list.push(InternalBibleEntry::simple("s1", "Subheading 1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse twoB text."));
        list.push(InternalBibleEntry::simple("v", "3"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse three text."));

        let list = add_preverse_markers_before_headings(list, "test_add_verse_markers_before_headings_multiple_headers", "ddd"); // This is always done first

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "mt1", "ie",
                "c", "v=", "ms1", "mr", "s1", "rem", "p", "v", "v~", "v", "v~",
                    "v=", "s1", "s2", "v", "v~",
                "c", "v=", "s1", "rem", "s3", "p", "v", "v~", "v", "v~",
                    "v=", "ms1", "s1", "v~", "v", "v~",
            ]
        );
        assert!(list[3].marker()=="v=" && list[3].adjusted_text()=="1"); // This ms1 is for v1
        assert!(list[13].marker()=="v=" && list[13].adjusted_text()=="3"); // This s1/s2 is for v3
        assert!(list[19].marker()=="v=" && list[19].adjusted_text()=="1"); // This s1/rem/s3 is for v1
        assert!(list[28].marker()=="v=" && list[28].adjusted_text()=="2b"); // This ms1/s1 is still in v2 -- the 'b' says it's the second part of the verse
    }

    #[test]
    fn test_add_nesting_markers_simple_p() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Verse two text."));

        let list = add_additional_markers(list, "Simple test entries", "XXA");

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "chapters",
                "c", "p", "v","v~","¬v", "v","v~","¬v", "¬p", "¬c",
                "¬chapters"
            ]
        );
    }

    #[test]
    fn test_add_nesting_markers_simple_lists() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("id", "XXA"));
        list.push(InternalBibleEntry::simple("mt1", "XXA Book"));
        list.push(InternalBibleEntry::simple("ip", "Introduction paragraph."));
        list.push(InternalBibleEntry::simple("ili1", "Introduction list item 1."));
        list.push(InternalBibleEntry::simple("ili1", "Introduction list item 2."));
        list.push(InternalBibleEntry::simple("ili2", "Introduction list item 2a."));
        list.push(InternalBibleEntry::simple("ie", ""));
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Verse one text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Verse two text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "3"));
        list.push(InternalBibleEntry::simple("v~", "Verse three text."));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "4"));
        list.push(InternalBibleEntry::simple("v~", "Verse four text."));

        let list = add_additional_markers(list, "Simple test entries", "XXA");

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "id",
                "headers", "mt1", "¬headers",
                "intro", "ip", "ilist", "ili1", "ili1", "ili2", "¬ilist", "ie", "¬intro",
                "chapters",
                "c", "p", "v","v~","¬v", "¬p",
                    "list", "li1", "v","v~","¬v", "¬li1",
                    "li1", "v","v~","¬v", "¬li1", "¬list",
                "p", "v","v~","¬v", "¬p", "¬c",
                "¬chapters"
            ]
        );
    }


    #[test]
    fn test_add_nesting_markers_complex_lists() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("id", "XXB"));
        list.push(InternalBibleEntry::simple("mt1", "XXB Book"));
        list.push(InternalBibleEntry::simple("ip", "Introduction paragraph."));
        list.push(InternalBibleEntry::simple("ili1", "Introduction list item 1."));
        list.push(InternalBibleEntry::simple("ili1", "Introduction list item 2."));
        list.push(InternalBibleEntry::simple("ili2", "Introduction list item 2a."));
        list.push(InternalBibleEntry::simple("ie", ""));
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Verse 1one text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Verse 1two text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "3"));
        list.push(InternalBibleEntry::simple("v~", "Verse 1three text."));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "4"));
        list.push(InternalBibleEntry::simple("v~", "Verse 1four text."));
        list.push(InternalBibleEntry::simple("c", "2"));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Verse 2one text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Verse 2twoA text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v~", "Verse 2twoB text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "3"));
        list.push(InternalBibleEntry::simple("v~", "Verse 2three text."));
        list.push(InternalBibleEntry::simple("c", "3")); // List continues across chapter boundary
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Verse 3one text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Verse 3two text."));
        list.push(InternalBibleEntry::simple("rem", "/s1 Alternative section heading")); // List should continue through this remark
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "3"));
        list.push(InternalBibleEntry::simple("v~", "Verse 3three text."));

        let list = add_additional_markers(list, "Complex test entries", "XXB");

        println!("Generated markers: {:?}", list.iter().map(|e| e.marker()).collect::<Vec<_>>());
        println!("List length = {}", list.len());
        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "id",
                "headers", "mt1", "¬headers",
                "intro", "ip", "ilist", "ili1", "ili1", "ili2", "¬ilist", "ie", "¬intro",
                "chapters",
                "c", "p", "v","v~","¬v", "¬p", // c 1
                    "list", "li1", "v","v~","¬v", "¬li1",
                    "li1", "v","v~","¬v", "¬li1", "¬list",
                    "p", "v","v~","¬v", "¬p", "¬c",
                "c", "list", "li1", "v","v~","¬v", "¬li1", // c 2
                    "li1", "v","v~", "¬li1",   "li1", "v~","¬v", "¬li1",
                    "li1", "v","v~","¬v", "¬li1", "¬c",
                "c", "li1", "v","v~","¬v", "¬li1",// c 3
                    "li1", "v","v~","¬v", "¬li1",
                    "rem", "li1", "v","v~","¬v", "¬li1", "¬c", "¬list",
                "¬chapters"
            ]
        );
    }

    #[test]
    fn test_add_nesting_markers_normal() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("id", "XXC"));
        list.push(InternalBibleEntry::simple("mt1", "XXC Book"));
        list.push(InternalBibleEntry::simple("ip", "Introduction paragraph."));
        list.push(InternalBibleEntry::simple("ie", ""));
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse one text."));
        list.push(InternalBibleEntry::simple("q1", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse two text."));
        list.push(InternalBibleEntry::simple("c", "2"));
        list.push(InternalBibleEntry::simple("s1", "Chapter 2 heading"));
        list.push(InternalBibleEntry::simple("m", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse two text."));

        let list = add_additional_markers(list, "Normal test entries", "XXC");

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "id",
                "headers", "mt1", "¬headers",
                "intro", "ip", "ie","¬intro",
                "chapters",
                "c", "p", "v","v~","¬v", "¬p",
                    "q1", "v","v~","¬v", "¬q1", "¬c",
                "c", "v=", "s1", "m", "v","v~","¬v", "v","v~","¬v", "¬m", "¬s1",  "¬c",
                "¬chapters"
            ]
        );
    }

    #[test]
    fn test_add_nesting_markers_complex_headings_and_lists() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("id", "XXD"));
        list.push(InternalBibleEntry::simple("h", "XXD"));
        list.push(InternalBibleEntry::simple("mt1", "XXD Book"));
        list.push(InternalBibleEntry::simple("ip", "Introduction paragraph."));
        list.push(InternalBibleEntry::simple("ili1", "Introduction list line 1."));
        list.push(InternalBibleEntry::simple("ili1", "Introduction list line 2."));
        list.push(InternalBibleEntry::simple("ie", ""));
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse two text."));
        list.push(InternalBibleEntry::simple("c", "2"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse two text."));
        list.push(InternalBibleEntry::simple("c", "3"));
        list.push(InternalBibleEntry::simple("s1", "Chapter 3 heading crosses chapters"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter three Verse one text."));
        list.push(InternalBibleEntry::simple("q1", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter three Verse two text."));
        list.push(InternalBibleEntry::simple("c", "4"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter four Verse one text."));
        list.push(InternalBibleEntry::simple("m", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter four Verse two text."));
        list.push(InternalBibleEntry::simple("c", "5"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter five Verse one text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v~", "More chapter five Verse one text."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter five Verse two text."));

        // println!("Test InternalBibleEntryList = ({} entries) {}", list.len(), list);
        let list = add_additional_markers(list, "Complex test entries with nb", "XXD");
        // println!("After add_nesting_markers: ({} entries) {}", list.len(), list);

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "id",
                "headers", "h", "mt1", "¬headers",
                "intro", "ip", "ilist", "ili1", "ili1", "¬ilist", "ie", "¬intro",
                "chapters",
                "c", "p", "v","v~","¬v", "v","v~","¬v", "¬p", "¬c",
                "c", "p", "v","v~","¬v", "v","v~","¬v", "¬p", "¬c",
                "c", "v=", "s1", "p", "v","v~","¬v", "¬p",
                    "q1", "v","v~","¬v", "¬q1", "¬c",
                "c", "p", "v","v~","¬v", "¬p",
                    "m", "v","v~","¬v", "¬m", "¬c",
                "c", "p", "v","v~", "¬p",
                    "list", "li1", "v~","¬v", "¬li1",
                    "li1", "v","v~","¬v", "¬li1", "¬list",
                "¬c", "¬s1",
                "¬chapters"
            ]
        );
    }

    #[test]
    fn test_add_nesting_markers_complex_nb() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("id", "XXE"));
        list.push(InternalBibleEntry::simple("mt1", "XXE Book"));
        list.push(InternalBibleEntry::simple("ip", "Introduction paragraph."));
        list.push(InternalBibleEntry::simple("ie", ""));
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse two text."));
        list.push(InternalBibleEntry::simple("c", "2"));
        list.push(InternalBibleEntry::simple("nb", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse two text."));
        list.push(InternalBibleEntry::simple("c", "3"));
        list.push(InternalBibleEntry::simple("s1", "Chapter 3 heading crosses chapters"));
        list.push(InternalBibleEntry::simple("q1", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter three Verse one text."));
        list.push(InternalBibleEntry::simple("q2", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter three Verse two text."));
        list.push(InternalBibleEntry::simple("c", "4"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter four Verse one text."));
        list.push(InternalBibleEntry::simple("m", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter four Verse two text."));
        list.push(InternalBibleEntry::simple("c", "5"));
        list.push(InternalBibleEntry::simple("nb", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter five Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter five Verse two text."));

        // println!("Test InternalBibleEntryList = ({} entries) {}", list.len(), list);
        let list = add_additional_markers(list, "Complex test entries with nb", "XXE");
        // println!("After add_nesting_markers: ({} entries) {}", list.len(), list);

        assert_eq!(
            list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            [
                "id",
                "headers", "mt1", "¬headers",
                "intro", "ip", "ie", "¬intro",
                "chapters",
                "c", "p", "v","v~","¬v", "v","v~","¬v", "¬nb", "¬c",
                "c", "nb", "v","v~","¬v", "v","v~","¬v", "¬p", "¬c",
                "c", "v=", "s1", "q1", "v","v~","¬v", "¬q1",
                    "q2", "v","v~","¬v", "¬q2", "¬c",
                "c", "p", "v","v~","¬v", "¬p",
                    "m", "v","v~","¬v", "¬nb", "¬c",
                "c", "nb", "v","v~","¬v", "v","v~","¬v", "¬m", "¬c",  "¬s1",
                "¬chapters"
            ]
        );
    }

    #[test]
    fn test_add_nesting_markers_embedded_li1_li2_lists() {
        set_strict_checking_flag(true);
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("id", "FRT"));
        list.push(InternalBibleEntry::simple("is1", "Distinctives"));
        list.push(InternalBibleEntry::simple("m", "The OET has the following distinguishing points:"));
        list.push(InternalBibleEntry::simple("v~", "The OET has the following distinguishing points:"));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v~", "Item 1 (standalone level 1)"));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v~", "Item 2 with subitems:"));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v~", "Subitem 2a"));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v~", "Subitem 2b"));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v~", "Item 3 (standalone level 1)"));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v~", "Item 4 with subitems:"));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v~", "Subitem 4a"));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v~", "Subitem 4b"));
        list.push(InternalBibleEntry::simple("m", ""));
        list.push(InternalBibleEntry::simple("v~", "Note: always check the Readers' Version."));

        let processed = add_additional_markers(list, "Embedded list test entries", "FRT");

        let markers = processed.iter().map(|e| e.marker()).collect::<Vec<_>>();
        println!("Embedded list generated markers: {:?}", markers);

        assert_eq!(
            markers,
            [
                "id",
                "intro", "is1",
                "m", "v~", "¬m",
                "list",
                    "li1", "v~", "¬li1",
                    "li1", "v~",
                        "list",
                            "li2", "v~", "¬li2",
                            "li2", "v~", "¬li2",
                        "¬list",
                    "¬li1",
                    "li1", "v~", "¬li1",
                    "li1", "v~",
                        "list",
                            "li2", "v~", "¬li2",
                            "li2", "v~", "¬li2",
                        "¬list",
                    "¬li1",
                "¬list",
                "m", "v~", "¬m",
                "¬is1",
                "¬intro"
            ]
        );

        // Verify that 'list' and '¬list' entries have their indent level in clean_text
        let list_entries: Vec<(&str, &str)> = processed
            .iter()
            .filter(|e| matches!(e.marker(), "list" | "¬list"))
            .map(|e| (e.marker(), e.clean_text()))
            .collect();

        assert_eq!(
            list_entries,
            [
                ("list", "1"),
                ("list", "2"),
                ("¬list", "2"),
                ("list", "2"),
                ("¬list", "2"),
                ("¬list", "1"),
            ]
        );
    }

    #[test]
    #[ignore = "Test not finished yet"]
    fn test_add_nesting_markers_embedded_li1_li2_lists_and_c_s1() {
        set_strict_checking_flag(true);
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("id", "CH1"));
        list.push(InternalBibleEntry::simple("c", "6"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "71"));
        list.push(InternalBibleEntry::simple("v~", "The descendants of Gershon, who were part of the tribe of Manasseh, lived east \\add of the Jordan River\\add*. They were allotted the cities and towns and pastureland near them: Golan in \\add the\\add* Bashan and Ashtaroth \\add regions\\add*."));
        list.push(InternalBibleEntry::simple("li2", "")); // A list starting with li2 shouldn't be allowed in strict checking mode
        list.push(InternalBibleEntry::simple("v", "72"));
        list.push(InternalBibleEntry::simple("v~", "From the tribe of Issachar they were allotted cities and towns and pastureland near Kedesh, Daberath,"));
        list.push(InternalBibleEntry::simple("v", "73"));
        list.push(InternalBibleEntry::simple("v~", "Ramoth, and Anem."));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v", "74"));
        list.push(InternalBibleEntry::simple("v~", "From the tribe of Asher they were allotted cities and towns and pastureland near Mashal, Abdon,"));
        list.push(InternalBibleEntry::simple("v", "75"));
        list.push(InternalBibleEntry::simple("v~", "Hukok, and Rehob."));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v", "76"));
        list.push(InternalBibleEntry::simple("v~", "And from the tribe of Naphtali they were allotted cities and towns and pastureland near Kedesh in \\add the\\add* Galilee \\add region\\add*, and Hammon and Kiriathaim \\add towns\\add*."));
        list.push(InternalBibleEntry::simple("b", ""));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "77"));
        list.push(InternalBibleEntry::simple("v~", "The other descendants of Levi, those descended from Merari, were allotted towns and pasturelands from the tribe of Zebulun near Jokneam, Kartah, Rimmono, and Tabor."));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v", "78-79"));
        list.push(InternalBibleEntry::simple("v~", "From the tribe of Reuben they were allotted cities and towns and pastureland near Bezer in the desert, Jahzah, Kedemoth, and Mephaath. The tribe of Reuben lived east of the Jordan \\add River\\add*, across from Jericho."));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v", "80"));
        list.push(InternalBibleEntry::simple("v~", "From the tribe of Gad, they were allotted cities and towns and pastureland near Ramoth in \\add the\\add* Gilead \\add region\\add*, \\add the cities of\\add* Mahanaim,"));
        list.push(InternalBibleEntry::simple("v", "81"));
        list.push(InternalBibleEntry::simple("v~", "Heshbon, and Jazer.")); 
        list.push(InternalBibleEntry::simple("c", "6")); // Doesn't necessarily close the list
        list.push(InternalBibleEntry::simple("s1", "The descendants of Issachar")); // but this is a new section so the list must now be closed before the c entry
        list.push(InternalBibleEntry::simple("p", "")); // This would also have caused the list to be closed, but the s1 entry already did that
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "\\w Issachar|strong=\"H3485\"\\w*’s four \\w sons|strong=\"H1121\"\\w* \\w were|strong=\"H1121\"\\w* \\w Tola|strong=\"H8439\"\\w*, \\w Puah|strong=\"H6312\"\\w*, \\w Jashub|strong=\"H3437\"\\w*, \\w and|strong=\"H1121\"\\w* \\w Shimron|strong=\"H8110\"\\w*."));
        list.push(InternalBibleEntry::simple("li1", ""));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Tola’s sons were Uzzi, Rephaiah, Jeriel, Jahmai, Ibsam, and Samuel (OR, Shemuel). They were all leaders of the clans \\add descended from\\add* them."));
        list.push(InternalBibleEntry::simple("li2", ""));
        list.push(InternalBibleEntry::simple("v~", "In the record of Tola’s descendants were the names of 22,600 men who served in the army during the time that David was the king \\add of Israel\\add*."));

        set_strict_checking_flag(false); // Must succeed (do the best job that you can to handle human inconsistencies)
        let processed = add_additional_markers(list.clone(), "Embedded list test entries", "CH1");

        let markers = processed.iter().map(|e| e.marker()).collect::<Vec<_>>();
        println!("Embedded list generated markers: {:?}", markers);

        assert_eq!(
            markers,
            [
                "id",
                "chapters", "c",
                "p", "v", "v~",
                "list",
                    "li1", "v~", "¬li1",
                    "li1", "v~",
                        "list",
                            "li2", "v~", "¬li2",
                            "li2", "v~", "¬li2",
                        "¬list",
                    "¬li1",
                    "li1", "v~", "¬li1",
                    "li1", "v~",
                        "list",
                            "li2", "v~", "¬li2",
                            "li2", "v~", "¬li2",
                        "¬list",
                    "¬li1",
                "¬list",
                "m", "v~", "¬m",
                "¬is1",
                "¬intro"
            ]
        );

        // Verify that 'list' and '¬list' entries have their indent level in clean_text
        let list_entries: Vec<(&str, &str)> = processed
            .iter()
            .filter(|e| matches!(e.marker(), "list" | "¬list"))
            .map(|e| (e.marker(), e.clean_text()))
            .collect();

        assert_eq!(
            list_entries,
            [
                ("list", "1"),
                ("list", "2"),
                ("¬list", "2"),
                ("list", "2"),
                ("¬list", "2"),
                ("¬list", "1"),
            ]
        );

        set_strict_checking_flag(true); // Should fail now
        let processed = add_additional_markers(list, "Embedded list test entries", "CH1");

        let markers = processed.iter().map(|e| e.marker()).collect::<Vec<_>>();
        println!("Embedded list generated markers: {:?}", markers);

        assert_eq!(
            markers,
            [
                "id",
                "chapters", "c",
                "p", "v", "v~",
                "list",
                    "li1", "v~", "¬li1",
                    "li1", "v~",
                        "list",
                            "li2", "v~", "¬li2",
                            "li2", "v~", "¬li2",
                        "¬list",
                    "¬li1",
                    "li1", "v~", "¬li1",
                    "li1", "v~",
                        "list",
                            "li2", "v~", "¬li2",
                            "li2", "v~", "¬li2",
                        "¬list",
                    "¬li1",
                "¬list",
                "m", "v~", "¬m",
                "¬is1",
                "¬intro"
            ]
        );

        // Verify that 'list' and '¬list' entries have their indent level in clean_text
        let list_entries: Vec<(&str, &str)> = processed
            .iter()
            .filter(|e| matches!(e.marker(), "list" | "¬list"))
            .map(|e| (e.marker(), e.clean_text()))
            .collect();

        assert_eq!(
            list_entries,
            [
                ("list", "1"),
                ("list", "2"),
                ("¬list", "2"),
                ("list", "2"),
                ("¬list", "2"),
                ("¬list", "1"),
            ]
        );
    }
}

/* Need to fix '¬list' etc being added in the wrong place in some cases - need to look ahead to see the next list marker and only close if it's not a list marker (or if there isn't one at all) - otherwise we end up with '¬list' before the next list starts instead of after it ends. This is especially important for nb which can span across chapters and sections and should only be closed when we hit the next nb or the end of the chapter, not when we hit the next section or chapter.

Have nb: OET-RV book basicOnly=False ('DAN',) 11:0 inSection='section' inRightDiv=False inParagraph='p'
markerList=['id', 'usfm', 'ide', 'rem', 'rem', 'headers', 'h', 'toc1', 'toc2', 'toc3', 'mt1', 'mt3', '¬headers',
'intro', 'is1', 'ip', 'ip', 'ip', 'ip', 'iot', 'io1', 'io1', 'io2', 'io2', 'io2', 'io2', '¬iot', 'rem', 'ie', '¬intro',
'chapters',
'c', 'ms1', 'v=', '¬ms1', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', 'rem', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'rem', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬p', 'p', 'p~', '¬p', '¬v', 'p', 'v', 'v~', 'rem', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬p', 'p', 'p~', '¬v', 'v', 'v~', '¬v', '¬p', 'q1', 'v', 'v~', '¬q1', 'q1', 'p~', '¬q1', 'q1', 'p~', '¬q1', 'q1', 'p~', '¬q1', '¬v', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬p', 'p', 'p~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', 'rem', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', 'rem', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', 'rem', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬p', 'list', 'li1', 'p~', '¬li1', '¬v', 'li1', 'v', 'v~', '¬v', '¬li1', 'li1', 'v', 'v~', '¬v', '¬li1', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', 'rem', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬p', 'p', 'p~', '¬p', '¬v', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's2', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬p', 'p', 'p~', '¬v', 'v', 'v~', '¬v', '¬p', 'li1', 'v', 'v~', '¬v', '¬li1', 'li1', 'v', 'v~', '¬v', '¬li1', 'li1', 'v', 'v~', '¬v', '¬li1', 'li1', 'v', 'v~', '¬v', '¬li1', 'p', 'v', 'v~', 'rem', 'rem', '¬v', '¬p', 'q1', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬q1', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'mi', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬mi', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬p', 'mi', 'p~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬mi', 'p', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬p', 'p', 'p~', '¬p', '¬v', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬nb', '¬c',
'c', 'nb', 'c#', 'v', 'v~', '¬v', 'v=', '¬p', 's1', 'rem', 'p', 'v', 'v~', 'rem', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', 'rem', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', 'rem', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', '¬c',
'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', '¬c', '¬list',
'¬chapters']

*/
