//! USFM nesting and end marker logic.
//
// CHANGELOG:
//   2026-50-27 Make 'nb' cause a close 'nb' to be added BEFORE the new 'c' marker, but the 'nb' itself is closed with the original paragraph marker
use compact_str::CompactString;

use crate::entry::InternalBibleEntry;
use crate::entry_lists::InternalBibleEntryList;
use crate::bos_markers::{
    heading_markers, intro_list_markers, intro_outline_markers, introduction_markers,
    main_text_list_markers, major_section_markers, paragraph_markers,
};

/// Add logical verse start markers (`v=`) before sections, paragraphs, etc.
pub fn add_verse_start_markers(entries: InternalBibleEntryList) -> InternalBibleEntryList {
    let entries_vec = entries.into_vec();
    let num_entries = entries_vec.len();
    let mut result = InternalBibleEntryList::with_capacity(num_entries + 40);
    
    let fields_preceded = ["s1", "s2", "s3", "s4", "sp"];
    let mut fields_also_preceded: Vec<&str> = Vec::new();
    fields_also_preceded.extend_from_slice(paragraph_markers::ALL);
    fields_also_preceded.extend_from_slice(&["c#", "r", "d", "ms1", "mr", "sr", "sp", "ib", "b", "cl¤", "tr"]);

    for j in 0..num_entries {
        let entry = &entries_vec[j];
        let marker = entry.marker();
        assert!(!marker.is_empty() && !marker.contains('\\'), "Entry marker should not be empty and should not contain a backslash: found '{}'", marker);
        
        if fields_preceded.contains(&marker) {
            // Look ahead for next 'v'
            for k in 1..5 {
                if j + k < num_entries {
                    let next_entry = &entries_vec[j + k];
                    let next_marker = next_entry.marker();
                    if next_marker == "v" {
                        // Add v= marker
                        result.push(
                            InternalBibleEntry::new(
                                "v=",
                                "v",
                                next_entry.adjusted_text().unwrap_or(""),
                                next_entry.clean_text(),
                                None,
                                next_entry.original_text().unwrap_or(""),
                            )
                            .expect("Invalid internal entry"),
                        );
                        break; // Only add one v= for this preceded field
                    } else if !fields_also_preceded.contains(&next_marker)
                        && !next_marker.starts_with('¬')
                        && next_marker != "rem"
                    {
                        break;
                    }
                }
            }
        }
        result.push(entry.clone());
    }
    result
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
///   and both of those will be inside the 'p'/'¬p' or similar block.
pub fn add_nesting_markers(
    entries: InternalBibleEntryList,
    work_name: &str,
    bos_book_code: &str,
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

    // Helper functions for look-ahead
    let chapter_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == "c" {
                return true;
            }
            if matches!(m, "v" | "v~" | "p~") {
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
            if matches!(m, "v~" | "p~") {
                return false;
            }
        }
        true
    };

    let section_has_ended = |current_marker: &str, start_idx: usize, entries: &[InternalBibleEntry]| {
        let mut other_possibilities = Vec::new();
        if let Some(level_char) = current_marker.chars().last()
            && level_char.is_ascii_digit()
            && level_char > '1'
        {
            let level = level_char.to_digit(10).unwrap();
            let base = &current_marker[..current_marker.len() - 1];
            for z in 1..level {
                other_possibilities.push(format!("{}{}", base, z));
            }
        }
        if matches!(current_marker, "s1" | "s2" | "s3" | "s4") {
            other_possibilities.push("ms1".to_string());
        }

        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == current_marker || other_possibilities.iter().any(|p| p == m) {
                return true;
            }
            if matches!(m, "v" | "v~" | "p~") {
                return false;
            }
        }
        true
    };

    let paragraph_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            // "v=" comes before section headings and some other list markers
            if paragraph_markers::is_paragraph(m) || m=="v=" || main_text_list_markers::is_main_text_list(m) {
                return true;
            }
            if matches!(m, "v" | "v~" | "p~") {
                return false;
            }
        }
        true
    };

    let find_next_relevant_list_marker = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if !matches!(m, "c" | "v=" | "v" | "v~" | "p~") {
                return Some(CompactString::from(m));
            }
        }
        None
    };

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

    for j in 0..num_entries {
        let entry = &entries_vec[j];
        let marker = entry.marker();
        let marker_owned = CompactString::from(marker);
        let text = entry.clean_text();
        // println!("Processing entry {}: Marker: {}, Clean Text: '{}', open_markers {}", j, marker, text, open_markers.join(", "));
        // assert!(work_name!="OET-RV" ||bos_book_code != "HAG" || new_lines.len() != 92, "Gone too far without finding the expected verse end marker for 1:15 in OET-RV Haggai: Got {:#?}", new_lines.slice(85,95).iter());

        if current_chapter == "-1" {
            current_verse = CompactString::from(new_lines.len().to_string());
        }

        // Header and Intro logic
        if marker == "h" && !open_markers.iter().any(|m| m == "headers") {
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
        if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            && last_open == "list"
            && !main_text_list_markers::is_main_text_list(marker)
            && marker != "v~"
            && marker != "p~"
        {
            let close = if let Some(next_list_m) = find_next_relevant_list_marker(j, &entries_vec) {
                !main_text_list_markers::is_main_text_list(next_list_m.as_str())
            } else {
                true
            };
            if close {
                open_markers.pop();
                new_lines.push(InternalBibleEntry::simple("¬list", ""));
            }
        }

        // Chapter logic
        if marker == "nb" {
            // nb is a NOP for nesting - it's just a paragraph marker that extends across chapters
        } else if marker == "c" {
            if let Some(last_open) = open_markers.last().map(|s| s.to_string())
                && (last_open == "headers" || last_open == "intro")
            {
                open_markers.pop();
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open), ""));
            }

            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
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
                    new_lines.push(InternalBibleEntry::simple("¬nb", ""));
                    // Do NOT remove from open_markers - paragraph continues
                    // Do NOT clear last_p_marker - it will be closed at the next paragraph
                } else {
                    // Paragraph is ending - close it BEFORE closing the previous chapter
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
                    last_p_marker = None;
                }
            }

            // Close the previous chapter
            if let Some(pos) = open_markers.iter().rposition(|m| m == "c") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_chapter.as_str()));
            }

            if !open_markers.iter().any(|m| m == "chapters") {
                new_lines.push(InternalBibleEntry::nesting_marker("chapters"));
                open_markers.push(CompactString::from("chapters"));
            }

            current_chapter = CompactString::from(text);
            current_verse = CompactString::from("0");
            open_markers.push(marker_owned.clone());
        } else if marker == "vp#" {
            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
        } else if marker == "v" || marker == "v=" {
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker
                        && last_open_m == last_p.as_str()
                        && paragraph_has_ended(j, &entries_vec)
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
            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
            current_verse = CompactString::from(text);
            if marker == "v" {
                open_markers.push(marker_owned.clone());
            }
        } else if marker == "iot" {
            open_markers.push(CompactString::from("iot"));
        } else if intro_outline_markers::is_intro_outline(marker) {
            let should_open = if let Some(lm) = &last_marker {
                lm != "iot" && !intro_outline_markers::is_intro_outline(lm)
            } else {
                true
            };
            if should_open {
                new_lines.push(InternalBibleEntry::nesting_marker("iot"));
                open_markers.push(CompactString::from("iot"));
            }
        } else if intro_list_markers::is_intro_list(marker) {
            let should_open = last_marker
                .as_ref()
                .is_none_or(|lm| !intro_list_markers::is_intro_list(lm));
            if should_open {
                new_lines.push(InternalBibleEntry::nesting_marker("ilist"));
                open_markers.push(CompactString::from("ilist"));
            }
        } else if heading_markers::is_heading(marker) {
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if let Some(last_s) = &last_s_marker
                        && last_open_m == last_s.as_str()
                        && section_has_ended(last_s, j, &entries_vec)
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
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            if let Some(ls) = &last_s_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == ls)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            last_p_marker = None;
        } else if major_section_markers::is_major_section(marker) {
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "headers" || last_open_m == "intro" {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                        made_change = true;
                    } else if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if let Some(last_s) = &last_s_marker {
                        if last_open_m == last_s.as_str() && section_has_ended(last_s, j, &entries_vec) {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if last_open_m == "c" && chapter_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬c", current_chapter.as_str()));
                        made_change = true;
                    } else if last_open_m == marker {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", marker), ""));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }

            if !open_markers.iter().any(|m| m == "chapters") {
                new_lines.push(InternalBibleEntry::nesting_marker("chapters"));
                open_markers.push(CompactString::from("chapters"));
            } else if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }

            if let Some(ls) = &last_s_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == ls)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }

            if let Some(pos) = open_markers.iter().rposition(|m| m == marker) {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            open_markers.push(marker_owned.clone());
            last_p_marker = None;
            last_s_marker = Some(marker_owned.clone());
        } else if main_text_list_markers::is_main_text_list(marker) {
            for _ in 0..9 {
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
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            if !open_markers.iter().any(|m| m == "list") {
                new_lines.push(InternalBibleEntry::nesting_marker("list"));
                open_markers.push(CompactString::from("list"));
            }
            open_markers.push(marker_owned.clone());
            last_p_marker = Some(marker_owned.clone());
        } else if paragraph_markers::is_paragraph(marker) {
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
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            open_markers.push(marker_owned.clone());
            last_p_marker = Some(marker_owned.clone());
        } else if usfm_markers::get_marker_content_type(marker) == Some('N') {
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

        new_lines.push(entry.clone());
        last_marker = Some(marker_owned);
    }

    // Close any left-over open markers
    // println!("add_nesting_markers() finished processing entries, now closing any remaining open markers: {}", open_markers.join(", "));
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
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            current_chapter.as_str()
        } else { "" };
        new_lines.push(InternalBibleEntry::end_marker(end_marker_str, with_text).unwrap());
    }


    log::info!("    add_nesting_markers for {} finishing with {} entries", bos_book_code, new_lines.len());
    
    new_lines
}

#[cfg(test)]
mod tests {
    use crate::entry::InternalBibleEntry;
    use crate::entry_lists::InternalBibleEntryList;
use crate::nesting::{add_verse_start_markers, add_nesting_markers};

    #[test]
    fn test_add_verse_start_markers_no_change() {
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Verse one text."));

        let list = add_verse_start_markers(list); // This is always done first

        assert_eq!(list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            ["c", "p", "v", "v~"]);
    }

    #[test]
    fn test_add_verse_start_markers_simple() {
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

        let list = add_verse_start_markers(list); // This is always done first

        assert_eq!(list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            ["c", "p", "v", "v~", "v=", "s1", "p", "v", "v~", "c", "v=", "s1", "q1", "v", "v~"]);
        assert_eq!(list[4].adjusted_text(), Some("2")); // 'v=' should have the verse number of the following 'v'
        assert_eq!(list[10].adjusted_text(), Some("1")); // 'v=' should have the verse number of the following 'v'
    }

    #[test]
    fn test_add_verse_start_markers_complex() {
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse one text."));
        list.push(InternalBibleEntry::simple("v", "2"));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse two initial text."));
        list.push(InternalBibleEntry::simple("s1", "Heading one"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v~", "Chapter one Verse two more text."));
        list.push(InternalBibleEntry::simple("v", "3"));
        list.push(InternalBibleEntry::simple("v~", "Verse three text."));
        list.push(InternalBibleEntry::simple("c", "2"));
        list.push(InternalBibleEntry::simple("s1", "Heading two"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter two Verse one text."));
        list.push(InternalBibleEntry::simple("c", "3"));
        list.push(InternalBibleEntry::simple("nb", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Chapter three Verse one text in same paragraph."));

        let list = add_verse_start_markers(list); // This is always done first

        assert_eq!(list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            ["c", "p", "v", "v~", "v", "v~", "v=", "s1", "p", "v~", "v", "v~",
             "c", "v=", "s1", "p", "v", "v~",
             "c", "nb", "v", "v~"]);
        assert_eq!(list[6].adjusted_text(), Some("2")); // This is still in v2
        assert_eq!(list[13].adjusted_text(), Some("1")); // 'v=' should have the verse number of the following 'v'
    }

    #[test]
    fn test_add_nesting_markers_simple() {
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "Verse one text."));

        let list = add_verse_start_markers(list); // This is always done first
        let list = add_nesting_markers(list, "Simple test entries", "XXA");

        assert_eq!(list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            ["chapters",
                "c", "p", "v", "v~", "¬v", "¬p", "¬c",
                "¬chapters"]);
    }

    #[test]
    fn test_add_nesting_markers_normal() {
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

        let list = add_verse_start_markers(list); // This is always done first
        let list = add_nesting_markers(list, "Normal test entries", "XXB");

        assert_eq!(list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            ["id", "mt1", "intro", "ip", "ie", "¬intro",
                "chapters",
                "c", "p", "v", "v~", "¬v", "¬p", "q1", "v", "v~", "¬v", "¬q1", "¬c",
                "c", "v=", "s1", "m", "v", "v~", "¬v", "v", "v~", "¬v", "¬m", "¬c",
                "¬chapters"]);
    }

    #[test]
    fn test_add_nesting_markers_complex_nb() {
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
        list.push(InternalBibleEntry::simple("s1", "Chapter 3 heading"));
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
        let list = add_verse_start_markers(list); // This is always done first
        let list = add_nesting_markers(list, "Complex test entries with nb", "XXC");
        // println!("After add_nesting_markers: ({} entries) {}", list.len(), list);

        assert_eq!(list.iter().filter_map(|e| Some(e.marker())).collect::<Vec<_>>(),
            ["id", "mt1", "intro", "ip", "ie", "¬intro",
                "chapters",
                "c", "p", "v", "v~", "¬v", "v", "v~", "¬v", "¬nb", "¬c",
                "c", "nb", "v", "v~", "¬v", "v", "v~", "¬v", "¬p", "¬c",
                "c", "v=", "s1", "q1", "v", "v~", "¬v", "¬q1", "q2", "v", "v~", "¬v", "¬q2", "¬c",
                "c", "p", "v", "v~", "¬v", "¬p", "m", "v", "v~", "¬v", "¬nb", "¬c",
                "c", "nb", "v", "v~", "¬v", "v", "v~", "¬v", "¬m", "¬c",
                "¬chapters"]);
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