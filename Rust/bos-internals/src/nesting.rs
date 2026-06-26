//! USFM nesting and end marker logic.
// use std::thread::current;

//
// CHANGELOG:
//   2026-05-27 Make 'nb' cause a close 'nb' to be added BEFORE the new 'c' marker, but the 'nb' itself is closed with the original paragraph marker
use compact_str::CompactString;
use std::collections::HashMap;
use indexmap::IndexMap;
use usfm_markers::normalize_marker;

use crate::bos_markers::{
    heading_markers, intro_list_markers, intro_outline_markers, introduction_markers, is_end_marker,
    main_text_list_markers, major_section_markers, paragraph_markers,
};
use crate::entry::InternalBibleEntry;
use crate::entry_lists::InternalBibleEntryList;
use crate::have_strict_checking_flag;

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
    let mut result = InternalBibleEntryList::with_capacity(num_entries + 40);

    // let mut fields_also_preceded: Vec<&str> = Vec::new();
    // fields_also_preceded.extend_from_slice(paragraph_markers::ALL);
    // fields_also_preceded.extend_from_slice(&["c#", "sr", "r", "mr", "d", "ib", "b", "cl¤", "tr"]);

    let mut current_verse_number: Option<CompactString> = None;
    // let mut current_verse_clean_text: Option<CompactString> = None;
    // let mut current_verse_original_text: Option<CompactString> = None;
    let mut current_verse_part_index: usize = 0;
    let mut just_added_vequals = false;

    let mut chapter_number_str = "0";
    for j in 0..num_entries {
        let entry = &entries_vec[j];
        let marker = entry.marker();
        assert!( !marker.is_empty() && !marker.contains('\\'),
            "{} {} entry marker should not be empty and should not contain a backslash: found '{}'", work_name, bos_book_code, marker);
        assert!( normalize_marker(marker) == marker,
            "{} {} Entry marker should be normalized (no extra spaces, etc.): found '{}'", work_name, bos_book_code, marker);
        if marker == "c" {
            chapter_number_str = entry.clean_text();
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
            panic!("add_verse_numbers_before_headings for {} {} failed with issues: {:?}", work_name, bos_book_code, validation_results);
        }
    }

    result
}

/// (Debug) Validate the processed lines for common issues and return a list of error messages.
pub fn validate_preverse_marker_insertions(processed_lines: &InternalBibleEntryList) -> Vec<String> {
    let mut issues = Vec::new();

    if processed_lines.is_empty() {
        issues.push("No processed_lines entries to validate".to_string());
        return issues;
    }

    let mut previous_marker = CompactString::new("");
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
            // if cfg!(debug_assertions) && !entry.clean_text().chars().all(|c| c.is_ascii_digit()) {
            //     println!("Validating verse start marker 'v=' '{}' at index {}: previous markers are '{}', '{}', following markers are '{}', '{}', '{}', '{}'",
            //         entry.clean_text(), n, processed_lines[n - 2].marker().to_string(),
            //         previous_marker, next_marker,
            //         processed_lines[n + 2].marker().to_string(),
            //         processed_lines[n + 3].marker().to_string(),
            //         processed_lines[n + 4].marker().to_string());
            // }
            if !SECTION_HEADER_FIELDS_PRECEDED_BY_PREVERSE_NUMBER.contains(&next_marker.as_str()) {
                issues.push(format!(
                    "Preverse number marker 'v=' at index {} is not followed by a verse or section marker (found '{}')",
                    n, next_marker
                ));
            }
        }

        previous_marker = current_marker;
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
    let mut open_markers: Vec<CompactString> = Vec::new();

    // Context tracking
    let mut current_chapter = CompactString::from("-1");
    let mut current_verse = CompactString::from("-1");
    let mut last_marker: Option<CompactString> = None;
    let mut last_p_marker: Option<CompactString> = None;
    let mut last_s_marker: Option<CompactString> = None;
    let mut section_crosses_chapters = HashMap::new();
    for section_marker in NESTABLE_SECTION_MARKERS { section_crosses_chapters.insert(CompactString::from(*section_marker), false); }

    // Helper functions for look-ahead
    let chapter_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == "c" {
                return true;
            }
            if matches!(m, "v" | "v~" | "XXXp~") {
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
            if matches!(m, "v~") {
                return false;
            }
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

    let list_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            // "v=" comes before section headings and some other list markers
            if paragraph_markers::is_paragraph(m) || m == "v=" {
                return true;
            }
            if matches!(m, "v" | "v~" | "li1" | "li2" | "li3" | "li4" ) {
                return false;
            }
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
        // println!("Processing {} {} entry {}: Marker: {}, Clean Text: '{}', open_markers {}", work_name, bos_book_code, j, marker, text, open_markers.join(", "));

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
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            new_lines.push(InternalBibleEntry::nesting_marker("intro"));
            open_markers.push(CompactString::from("intro"));
        }

        if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            && last_open == "iot"
            && !intro_outline_markers::is_intro_outline(marker)
        {
            open_markers.pop();
            new_lines.push(InternalBibleEntry::simple("¬iot", ""));
        }
        if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            && last_open == "ilist"
            && !intro_list_markers::is_intro_list(marker)
        {
            open_markers.pop();
            new_lines.push(InternalBibleEntry::simple("¬ilist", ""));
        }
        if !["v","v~","li1"].contains(&marker) && list_has_ended(j, &entries_vec) {
            // if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            //     && last_open == "li1"
            //     && list_has_ended(j, &entries_vec)
            // {
            //     open_markers.pop();
            //     new_lines.push(InternalBibleEntry::simple("¬li1", ""));
            // }
            // else
            if let Some(l_pos) = open_markers.iter().rposition(|m| m == "li1")
                && list_has_ended(j, &entries_vec) { // the list can also end mid-verse
                open_markers.remove(l_pos);
                new_lines.push(InternalBibleEntry::simple("¬li1", ""));
            }
            if let Some(l_pos) = open_markers.iter().rposition(|m| m == "list")
                && list_has_ended(j, &entries_vec) { // the list can also end mid-verse
                open_markers.remove(l_pos);
                new_lines.push(InternalBibleEntry::simple("¬list", ""));
            }
        //     if let Some(last_open) = open_markers.last().map(|s| s.to_string())
        //         && last_open == "list"
        //         && list_has_ended(j, &entries_vec)
        //     {
        //         open_markers.pop();
        //         new_lines.push(InternalBibleEntry::simple("¬list", ""));
        //     }
        // }
        }

        // if let Some(last_open) = open_markers.last().map(|s| s.to_string())
        //     && last_open == "list"
        //     && !main_text_list_markers::is_main_text_list(marker)
        //     && marker != "v~"
        //     && marker != "XXXp~"
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
            println!("At c with open_markers=[{}]", open_markers.join(", "));
            (c, v) = (text, "0");

            for _ in 0..3 {
                if let Some(last_open) = open_markers.last().map(|s| s.to_string())
                    && (last_open == "headers" || last_open == "intro"  || last_open == "is1")
                {
                    open_markers.pop();
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open), "").expect("Oops"));
                }
                else { break; }
            }

            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).expect("Oops"));
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
                    new_lines.push(InternalBibleEntry::end_marker("¬nb", "").expect("Oops"));
                    // Do NOT remove from open_markers - paragraph continues
                    // Do NOT clear last_p_marker - it will be closed at the next paragraph
                } else {
                    // Paragraph is ending - close it BEFORE closing the previous chapter
                    let m = open_markers.remove(pos);
                    assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} after v= with open_markers=[{}]", m, open_markers.join(", "));
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").expect("Oops"));
                    last_p_marker = None;
                }
            }

            // Close a section BEFORE closing the chapter if it hasn't crossed chapter boundaries
            if let Some(last_s) = &last_s_marker
            && let Some(s_pos) = open_markers.iter().rposition(|m| NESTABLE_SECTION_MARKERS.contains(&&m.as_str())) {
                if section_has_ended(last_s, j, &entries_vec)
                && !section_crosses_chapters[last_s] {
                    println!(
                        "At {} {}:{} processing chapter marker and closing section that hasn't crossed chapter boundaries: last_s='{}' Current open markers: {}",
                        j, c, v, last_s, open_markers.join(", "));
                    assert_eq!(s_pos, open_markers.len()-1, "Expected {} to be last marker (not {}) in [{}] with last_s_marker='{:?}'", last_s, s_pos, open_markers.join(", "), last_s_marker); // Must be the last marker then
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_s), "").expect("Oops"));
                    open_markers.remove(s_pos); // Could do pop here
                    last_s_marker = None;
                }
                else {
                    println!(
                        "At {} {}:{} processing chapter marker and seems like section has crossed chapter boundaries: last_s='{}' Current open markers: {}",
                        j, c, v, last_s, open_markers.join(", "));
                    section_crosses_chapters.insert(last_s.clone(), true);
                }
            }

            // Close the previous chapter
            if let Some(c_pos) = open_markers.iter().rposition(|m| m == "c") {
                let m = open_markers.remove(c_pos);
                new_lines.push(InternalBibleEntry::end_marker("¬c", current_chapter.as_str()).expect("Oops"));
            }

            // Close a section AFTER closing the chapter if it has crossed chapter boundaries
            if let Some(last_s) = &last_s_marker
            && let Some(s_pos) = open_markers.iter().rposition(|m| NESTABLE_SECTION_MARKERS.contains(&&m.as_str())) {
                if section_has_ended(last_s, j, &entries_vec)
                && section_crosses_chapters[last_s] {
                    println!(
                        "At {} {}:{} processing chapter marker and closing section that has crossed chapter boundaries: last_s='{}' Current open markers: {}",
                        j, c, v, last_s, open_markers.join(", "));
                    assert_eq!(s_pos, open_markers.len()-1, "Expected {} to be last marker (not {}) in [{}] with last_s_marker='{:?}'", last_s, s_pos, open_markers.join(", "), last_s_marker); // Must be the last marker then
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_s), ""));
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
            open_markers.push(marker_owned.clone());
        }
        
        else if marker == "v" { // || marker == "v="
            v = text;
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
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").expect("Oops"));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }
            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).expect("Oops"));
            }
            current_verse = CompactString::from(text);
            if marker == "v" {
                open_markers.push(marker_owned.clone());
            }
        }

        else if marker == "v=" { // Then we're about to hit a section heading or similar
            // For verse markers, we want to close any open verse if the verse is ending
            //  and close any open paragraph if the verse is ending and the next marker is not a continuation of the verse.
            if cfg!(debug_assertions) {
                println!(
                    "At {} {}:{} processing preverse marker {} = '{}': last_p_marker='{}' Current open markers: {}",
                    j, c, v, marker, text, last_p_marker.clone().unwrap_or_default(), open_markers.join(", "));
            }
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    // Close any open verse (if it's actually ended)
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).expect("Oops"));
                        made_change = true;
                    }
                    // Close any open paragraph
                    if let Some(last_p) = &last_p_marker
                        // && last_open_m == last_p.as_str()
                        // && paragraph_has_ended(j, &entries_vec)
                        {
                        // Paragraph is ending - close it BEFORE closing the verse
                        // but the paragraph might be followed by an open verse marker in open_markers
                        assert_ne!(new_lines.last().expect("Must be there").marker(), "v=",
                            "At {}:{} adding ¬{} before v= with last_p_marker='{}' open_markers=[{}]",
                            c, v, last_open_m, last_p_marker.clone().unwrap_or_default(), open_markers.join(", "));
                        if let Some(pos) = open_markers.iter().rposition(|m| m == last_p) {
                            open_markers.remove(pos);
                            new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_p), "").expect("Oops"));
                            made_change = true;
                        }
                    }
                    // If the last open marker was a section, and the section has ended, then close it
                    if let Some(last_s) = &last_s_marker
                        && last_open_m == last_s.as_str()
                        && section_has_ended(last_s, j, &entries_vec)
                    {
                        println!("    Removing {} from end of {:?}", last_s, open_markers);
                        assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} before v= with open_markers=[{}]", last_open_m, open_markers.join(", "));
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").expect("Oops"));
                        made_change = true;
                    }
                    // If there's an open section (followed by an open chapter), then close the open section here
                    else if let Some(last_s) = &last_s_marker
                        // && last_open_m == last_s.as_str()
                        && section_has_ended(last_s, j, &entries_vec)
                        && open_markers.contains(&last_s)
                    { // There must be a c marker at the end of open_markers after the s
                        println!("    Removing {} from middle of {:?}", last_s, open_markers);
                        assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} before v= with open_markers=[{}]", last_s, open_markers.join(", "));
                        open_markers.retain(|ss| ss != last_s); // Remove that section marker
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_s), "").expect("Oops"));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }
            // if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
            //     let m = open_markers.remove(pos);
            //     new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            // }
            current_verse = CompactString::from(text);
        }
        
        else if heading_markers::is_heading(marker) { // e.g., s1, s2, but also including 'ms1','ms2', etc.
            // For heading markers, we want to close any open verse, paragraph, or section if the heading is ending them.
            for q_q in 0..9 {
                println!("       {} loop with marker={}, last_p_marker={:?} last_s_marker={:?} and open_markers=[{}]", q_q, marker, last_p_marker, last_s_marker, open_markers.join(", "));
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).expect("Oops"));
                        made_change = true;
                    } else if let Some(last_s) = &last_s_marker
                        && last_open_m == last_s.as_str()
                        && (marker==last_s || section_has_ended(last_s, j, &entries_vec))
                    {
                        assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "HERE Adding ¬{} after v= with open_markers=[{}]", last_open_m, open_markers.join(", "));
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").expect("Oops"));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if last_open_m == last_p.as_str() {
                            assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} after v= with open_markers=[{}]", last_open_m, open_markers.join(", "));
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").expect("Oops"));
                            made_change = true;
                        }
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
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).expect("Oops"));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                assert_ne!(new_lines.last().expect("Must be there").marker(), "v=", "Adding ¬{} after v= with open_markers=[{}]", m, open_markers.join(", "));
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").expect("Oops"));
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
                    "add_nesting_markers for {} {} about to add another {} to {:?}",
                    work_name, bos_book_code, marker, open_markers);
                section_crosses_chapters.insert(CompactString::from(marker), false);
                open_markers.push(marker_owned.clone());
                last_s_marker = Some(marker_owned.clone());
            }
        }
        
        else if main_text_list_markers::is_main_text_list(marker) {
            // NOTE: These MUST come before the paragraph marker check (because these markers are included)
            // For main text list markers, we want to close any open verse or paragraph if the list is ending.
            // if cfg!(debug_assertions) {
            //     println!("At {} processing list marker {} = '{}' last_p_marker={:?} Current open markers: {}",
            //         j, marker, text, last_p_marker, open_markers.join(", "));
            // }
            // This loop is to close any open verse or paragraph that should be closed before the new list entry starts.
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    // println!("Last open m 1 = {}", last_open_m);
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).expect("Oops"));
                        made_change = true;
                    }
                } else if let Some(last_p) = &last_p_marker
                    && main_text_list_markers::is_main_text_list(last_p)
                {
                    open_markers.pop();
                    new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_p), "").expect("Oops"));
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
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).expect("Oops"));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").expect("Oops"));
            }
            if !open_markers.iter().any(|m| m == "list") {
                new_lines.push(InternalBibleEntry::nesting_marker("list"));
                open_markers.push(CompactString::from("list"));
            }
            open_markers.push(marker_owned.clone());
            last_p_marker = Some(marker_owned.clone());
        }
        
        else if marker == "nb" { // NOTE: This MUST come before the paragraph marker check (because this marker is included)
            // nb is a NOP for nesting - it's just a paragraph marker that extends across chapters
        }
        
        else if paragraph_markers::is_paragraph(marker) {
            // For paragraph markers, we want to close any open verse if the paragraph is ending.
            // if cfg!(debug_assertions) && open_markers.contains(&CompactString::new("list")) {
            //         println!("At {} processing paragraph marker {} = '{}' last_p_marker={:?} Current open markers: {}",
            //             j, marker, text, last_p_marker, open_markers.join(", "));
            // }
            for _ in 0..999 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).expect("Oops"));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker
                        && (last_open_m == last_p.as_str() || last_open_m == "list")
                    {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").expect("Oops"));
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
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), current_verse.as_str()).expect("Oops"));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").expect("Oops"));
            }
            open_markers.push(marker_owned.clone());
            last_p_marker = Some(marker_owned.clone());
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
        //                 new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").expect("Oops"));
        //                 made_change = true;
        //             } else if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
        //                 open_markers.pop();
        //                 new_lines.push(InternalBibleEntry::end_marker("¬v", current_verse.as_str()).expect("Oops"));
        //                 made_change = true;
        //             } else if let Some(last_p) = &last_p_marker {
        //                 if last_open_m == last_p.as_str() {
        //                     open_markers.pop();
        //                     new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").expect("Oops"));
        //                     made_change = true;
        //                 }
        //             } else if let Some(last_s) = &last_s_marker {
        //                 if last_open_m == last_s.as_str() && section_has_ended(last_s, j, &entries_vec) {
        //                     open_markers.pop();
        //                     new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", last_open_m), "").expect("Oops"));
        //                     made_change = true;
        //                 }
        //             } else if last_open_m == "c" && chapter_has_ended(j, &entries_vec) {
        //                 open_markers.pop();
        //                 new_lines.push(InternalBibleEntry::end_marker("¬c", current_chapter.as_str()).expect("Oops"));
        //                 made_change = true;
        //             } else if last_open_m == marker {
        //                 open_markers.pop();
        //                 new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", marker), "").expect("Oops"));
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
        //         new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").expect("Oops"));
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
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
        }
        
        else if marker == "ie" { // optional so can't rely on this
            if let Some(pos) = open_markers.iter().rposition(|m| m == "is1") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
        }
        
        else if usfm_markers::get_marker_content_type(marker) == Some('N') {
            // For other USFM markers that we haven't specifically handled, we want to close any open verse if the marker is ending the verse.
            for _ in 0..999 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker
                        && last_open_m == last_p.as_str()
                    {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
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
        new_lines.push(entry.clone());
        last_marker = Some(marker_owned);
    }

    // Close any left-over open markers
    if cfg!(debug_assertions) && !open_markers.is_empty() {
        println!("add_nesting_markers() finished processing entries, now closing remaining open markers: {}",
            open_markers.join(", "));
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
                let m = open_markers.pop().unwrap();
                new_lines.push(InternalBibleEntry::end_marker(format!("¬{}", m), "").expect("Oops"));
            }
            current_chapter.as_str()
        } else {
            ""
        };
        new_lines.push(InternalBibleEntry::end_marker(end_marker_str, with_text).unwrap());
    }

    log::info!(
        "    add_nesting_markers for {} finishing with {} entries",
        bos_book_code,
        new_lines.len()
    );

    if have_strict_checking_flag() || cfg!(debug_assertions) {
        let validation_results = validate_nesting(&new_lines, bos_book_code, work_name);
        if !validation_results.is_empty() {
            panic!("add_nesting_markers for {} {} failed with issues: {:?}", work_name, bos_book_code, validation_results);
        }
    }

    new_lines
}

/// (Debug) Validate the processed lines for common issues and return a list of error messages.
pub fn validate_nesting(processed_lines: &InternalBibleEntryList, bos_book_code: &str, work_name: &str) -> Vec<String> {
    let mut issues = Vec::new();

    if processed_lines.is_empty() {
        issues.push(format!("No {} {} processed_lines entries to validate", work_name, bos_book_code));
        return issues;
    }

    // let mut previous_marker = CompactString::new("");
    let mut next_marker = CompactString::new("");
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
                    "Special {} {} verse number marker 'v=' at index {} after {}:{} is followed by an end marker '{}'",
                    work_name, bos_book_code, n, c, v, next_marker));
            } else if !["s1", "s2", "s3", "s4", "ms1", "ms2", "ms3", "sp"].contains(&next_marker.as_str()) {
                issues.push(format!(
                    "Special {} {} verse number marker 'v=' at index {} after {}:{} is not followed by a verse or section marker (found '{}')",
                    work_name, bos_book_code, n, c, v, next_marker));
            }
        } else if current_marker == "v~" && next_marker == "v" {
            issues.push(format!(
                "Missing {} {} verse end marker '¬v' at index {} after {}:{} (found 'v' = '{}')",
                work_name, bos_book_code, n, c, v, processed_lines[n + 1].clean_text()));
        }

        // previous_marker = current_marker;
    }

    // Check that all end markers have a corresponding start marker with the same count
    for (marker, count) in &marker_counts {
        if is_end_marker(&marker) {
            let start_marker: CompactString = marker.chars().skip(1).collect();
            if count != marker_counts.get(&start_marker).unwrap_or(&0) {
                issues.push(format!(
                    "{} {} end marker '{}' has {} entries but its corresponding start marker has {} from [{}]",
                    work_name, bos_book_code, marker, count, marker_counts.get(&start_marker).unwrap_or(&0),
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
    fn test_add_nesting_markers_normal() {
        set_strict_checking_flag( true );
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("id", "XXB"));
        list.push(InternalBibleEntry::simple("mt1", "XXB Book"));
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

        let list = add_additional_markers(list, "Normal test entries", "XXB");

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
        list.push(InternalBibleEntry::simple("id", "XXC"));
        list.push(InternalBibleEntry::simple("h", "XXC"));
        list.push(InternalBibleEntry::simple("mt1", "XXC Book"));
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
        let list = add_additional_markers(list, "Complex test entries with nb", "XXC");
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
        list.push(InternalBibleEntry::simple("id", "XXC"));
        list.push(InternalBibleEntry::simple("mt1", "XXC Book"));
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
        let list = add_additional_markers(list, "Complex test entries with nb", "XXC");
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
