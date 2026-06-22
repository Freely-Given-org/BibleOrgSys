//! Section-based index for table of contents navigation.
//!
//! This module provides:
//! - `SectionIndexEntry` - Index entry for a single section
//! - `InternalBibleBookSectionIndex` - Section index for a book

use compact_str::{CompactString, ToCompactString};
use indexmap::IndexMap;
use num_format::{Locale, ToFormattedString};
use rkyv::validation;

use bos_books_codes::is_chapter_verse_book;
use crate::bos_markers::{is_end_marker, title_markers};
use crate::chapter_verse::ChapterVerse;
use crate::indexes::section_index;
use crate::parsing::get_small_leading_int;
use crate::entry_lists::InternalBibleEntryList;
use crate::error::LookupError;
use crate::have_strict_checking_flag;

/// Markers that can define section boundaries.
const SECTION_MARKERS: &[&str] = &[
    "is1", // Introductory sections
    "ms1", //"ms2", "ms3", // Major sections
    "s1",  // Section headings
    "iex", // Chapter introductions, e.g., in KJB-1611
    "c",   // Chapters can also define section boundaries, especially for intro-to-content transitions
];

/// An entry in the section index.
///
/// Each entry represents a section (usually defined by a heading)
/// and contains the range of entries it covers.
#[derive(Debug, Clone, PartialEq, Eq, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct SectionIndexEntry {
    /// Chapter where this section ends.
    end_chapter_num_str: CompactString,
    /// Verse where this section ends.
    end_verse_num_str: CompactString,
    /// Index of the first entry for this section.
    start_index: u16,
    /// Index of the last entry for this section (inclusive).
    end_index: u16,
    /// The marker that started this section (e.g., "Headers", "is1", "s1", "c", "c/s1").
    /// Note that "c/s1" should only occur for Psalms (where each chapter is automatically a new section)
    reason_marker: CompactString,
    /// The section name/heading text.
    section_name: String,
    /// Context markers active at this section.
    context: Vec<CompactString>,
}

impl SectionIndexEntry {
    /// Create a new section index entry.
    pub fn new(
        end_chapter: impl Into<CompactString>,
        end_verse: impl Into<CompactString>,
        start_index: u16,
        end_index: u16,
        reason_marker: impl Into<CompactString>,
        section_name: impl Into<String>,
        context: Vec<CompactString>,
    ) -> Self {
        Self {
            end_chapter_num_str: end_chapter.into(),
            end_verse_num_str: end_verse.into(),
            start_index,
            end_index,
            reason_marker: reason_marker.into(),
            section_name: section_name.into(),
            context,
        }
    }

    /// Get the ending chapter:verse as a ChapterVerse.
    pub fn end_cv(&self) -> ChapterVerse {
        ChapterVerse::new(self.end_chapter_num_str.as_str(), self.end_verse_num_str.as_str())
    }

    /// Get the ending chapter number.
    #[inline]
    pub fn end_chapter_num_str(&self) -> &str {
        &self.end_chapter_num_str
    }

    /// Get the ending verse number.
    #[inline]
    pub fn end_verse_num_str(&self) -> &str {
        &self.end_verse_num_str
    }

    /// Get the starting entry index.
    #[inline]
    pub fn start_index(&self) -> usize {
        self.start_index as usize
    }

    /// Get the ending entry index (inclusive).
    #[inline]
    pub fn end_index(&self) -> usize {
        self.end_index as usize
    }

    /// Get the count of entries in this section.
    #[inline]
    pub fn entry_count(&self) -> usize {
        (self.end_index + 1 - self.start_index) as usize
    }

    /// Get the marker that started this section.
    #[inline]
    pub fn reason_marker(&self) -> &str {
        &self.reason_marker
    }

    /// Get the section name/heading text.
    #[inline]
    pub fn section_name(&self) -> &str {
        &self.section_name
    }

    /// Get the section name and reason marker as a tuple.
    pub fn section_name_reason(&self) -> (&str, &str) {
        (&self.section_name, &self.reason_marker)
    }

    /// Get the context markers.
    #[inline]
    pub fn context(&self) -> &[CompactString] {
        &self.context
    }
}

impl std::fmt::Display for SectionIndexEntry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "SectionEntry({} [{} lines {}-{}] {:?})",
            self.reason_marker,
            self.end_cv(),
            self.start_index,
            self.end_index,
            self.section_name
        )
    }
}

/// Index for section-based lookup in a Bible book.
///
/// This index maps section starting points (C:V) to section entries,
/// useful for table of contents navigation and section-based access.
/// 
/// Note that unlike the CV index,
///     the section index doesn't necessarily include all the line entries.
#[derive(Debug, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleBookSectionIndex {
    /// Name of the work/Bible.
    work_name: CompactString,
    /// Three-letter book code.
    bos_book_code: CompactString,
    /// The section -> entry mapping (keyed by starting C:V).
    index_data: IndexMap<ChapterVerse, SectionIndexEntry>,
    /// The processed entries this index references.
    line_entries: InternalBibleEntryList,
    /// Whether the index has been built.
    indexed: bool,
}

impl InternalBibleBookSectionIndex {
    /// Create a new empty section index.
    pub fn new(work_name: impl Into<CompactString>, bos_book_code: impl Into<CompactString>) -> Self {
        Self {
            work_name: work_name.into(),
            bos_book_code: bos_book_code.into(),
            index_data: IndexMap::new(),
            line_entries: InternalBibleEntryList::new(),
            indexed: false,
        }
    }

    /// Get the work name.
    #[inline]
    pub fn work_name(&self) -> &str {
        &self.work_name
    }

    /// Get the book code.
    #[inline]
    pub fn bos_book_code(&self) -> &str {
        &self.bos_book_code
    }

    /// Check if the index has been built.
    #[inline]
    pub fn is_indexed(&self) -> bool {
        self.indexed
    }

    /// Get the number of sections in the index.
    #[inline]
    pub fn len(&self) -> usize {
        self.index_data.len()
    }

    /// Check if the index is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.index_data.is_empty()
    }

    /// Check if a specific section starting point exists.
    #[inline]
    pub fn contains(&self, cv: &ChapterVerse) -> bool {
        self.index_data.contains_key(cv)
    }

    /// Get an iterator over all sections.
    pub fn iter(&self) -> impl Iterator<Item = (&ChapterVerse, &SectionIndexEntry)> {
        self.index_data.iter()
    }

    /// Get entries for a section.
    ///
    /// # Arguments
    ///
    /// * `cv` - The starting chapter:verse of the section
    pub fn get_section_entries(&self, cv: &ChapterVerse) -> Result<InternalBibleEntryList, LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }

        let entry = self
            .index_data
            .get(cv)
            .ok_or_else(|| LookupError::SectionNotFound(cv.clone()))?;

        Ok(self
            .line_entries
            .slice(entry.start_index as usize, (entry.end_index + 1) as usize))
    }

    /// Get section entries with context markers.
    pub fn get_section_entries_with_context(
        &self,
        cv: &ChapterVerse,
    ) -> Result<(InternalBibleEntryList, Vec<CompactString>), LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }

        let entry = self
            .index_data
            .get(cv)
            .ok_or_else(|| LookupError::SectionNotFound(cv.clone()))?;

        let entries = self
            .line_entries
            .slice(entry.start_index as usize, (entry.end_index + 1) as usize);
        Ok((entries, entry.context.clone()))
    }

    /// Get the section index entry for a specific starting CV.
    pub fn get_index_entry(&self, cv: &ChapterVerse) -> Option<&SectionIndexEntry> {
        self.index_data.get(cv)
    }

    /// Get all section names as a table of contents.
    pub fn table_of_contents(&self) -> Vec<(&ChapterVerse, &str, &str)> {
        self.index_data
            .iter()
            .map(|(cv, entry)| (cv, entry.section_name(), entry.reason_marker()))
            .collect()
    }

    /// Get direct access to the underlying entries.
    #[inline]
    pub fn entries(&self) -> &InternalBibleEntryList {
        &self.line_entries
    }

    /// Get direct access to the underlying index data.
    #[inline]
    pub fn index_data(&self) -> &IndexMap<ChapterVerse, SectionIndexEntry> {
        &self.index_data
    }

    /// Reconstruct from serialized data.
    pub fn from_serialized(
        work_name: impl Into<CompactString>,
        bos_book_code: impl Into<CompactString>,
        index_data: IndexMap<ChapterVerse, SectionIndexEntry>,
        line_entries: InternalBibleEntryList,
    ) -> Self {
        Self {
            work_name: work_name.into(),
            bos_book_code: bos_book_code.into(),
            index_data,
            line_entries,
            indexed: true,
        }
    }

    /// Build the section index from processed entries.
    ///
    /// This analyzes the entry list and creates section boundaries
    /// based on section heading markers.
    pub fn build(&mut self, line_entries: InternalBibleEntryList) -> Result<(), crate::error::IndexError> {
        if line_entries.is_empty() {
            return Err(crate::error::IndexError::EmptyEntries);
        }
        log::info!(
            "Building section index for {} {} from {} entries…",
            self.work_name(),
            self.bos_book_code(),
            line_entries.len().to_formatted_string(&Locale::en)
        );

        self.line_entries = line_entries;
        self.index_data.clear();

        // Just see if we have section headings in this verse line_entry data
        let mut have_section_headings = false;
        for line_entry in self.line_entries.iter() {
            if line_entry.marker() == "s1" {
                have_section_headings = true;
                break;
            }
        }
        let process_chapters_as_section_breaks = self.bos_book_code()=="PSA" || !have_section_headings;

        let mut current_chapter_num_str = CompactString::from("-1");
        let mut current_verse_num_str = CompactString::from("0");
        let mut last_chapter_num_str = CompactString::from("-1");
        let mut last_verse_num_str = CompactString::from("0");
        let mut last_marker = "";
        let mut pending = None;
        let mut context: Vec<CompactString> = Vec::new();
        let mut book_name = String::new();
        let mut had_section_heading_since_chapters = false;
        // let mut last_bridge_entry_index: Option<u16> = None;
        // let mut last_bridge_verse_num_str: Option<CompactString> = None;

        for (i, line_entry) in self.line_entries.iter().enumerate() {
            let marker = line_entry.marker();
            if have_strict_checking_flag() || cfg!(debug_assertions) {
                println!("  sectionIndex {} {} build loop (with {} existing index entries) {}: {}",
                    self.work_name(), self.bos_book_code(), self.index_data.len(), i, marker);
            }

            // Get the very first marker
            if last_marker.is_empty() && ["id","usfm","ide","headers","h","intro","mt1"].contains(&marker) {
                assert!(pending.is_none());
                pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(), current_verse_num_str.as_str())),
                        start_index: 0,
                        reason: CompactString::from("Headers"),
                        name: self.bos_book_code().to_string(),
                        // has_content: false,
                    });
                last_marker = marker;
                continue
            }

            if marker == "h" {
                book_name = line_entry.clean_text().to_string();
                continue;
            } else if marker == "c" {
                current_chapter_num_str = CompactString::from(line_entry.clean_text());
                if !context.contains(&CompactString::from("c")) { context.push("c".into()); }
                current_verse_num_str = CompactString::from("0");
            } else if marker == "v" {
                current_verse_num_str = CompactString::from(line_entry.clean_text());
            } else if current_chapter_num_str == "-1" && marker != "chapters" {
                current_verse_num_str = i.to_compact_string();
            } else if marker == "chapters" {
                context.push(CompactString::from("chapters"));
                current_chapter_num_str = CompactString::from("0");
                had_section_heading_since_chapters = false;
            } else if marker == "s1" || marker == "ms1" {
                had_section_heading_since_chapters = true;
            }

            if have_strict_checking_flag() || cfg!(debug_assertions) {
                println!("    build {} {} section index loop {} with {} section index entries already from the given {} entry lines\n  with current {}:{} last {}:{} context=[{}] pending={:?}",
                    self.work_name(), self.bos_book_code(), i, self.index_data.len(), self.line_entries.len(),
                    current_chapter_num_str, current_verse_num_str, last_chapter_num_str, last_verse_num_str,
                    context.join(", "), pending);
            }

            // Once we reach the chapters, i.e., after the headers and introduction,
            //  we should only need to start sections at v= and sometimes at c markers
            if marker == "v=" {
            // && (!process_chapters_as_section_breaks || last_marker != "c") {
                let special_verse_num = line_entry.clean_text();
                // if current_verse_num_str=="0" && special_verse_num=="1" { current_verse_num_str = CompactString::from("1"); }
                let next_line_entry = self.line_entries.get(i+1).unwrap();
                let next_marker = next_line_entry.marker();
                if ["s1","ms1"].contains(&next_marker) {
                    if have_strict_checking_flag() || cfg!(debug_assertions) {
                        println!("    build {} section index at {} {} {}:{} has v= = '{}' followed by '{}' so need to start new index entry here",
                                self.work_name(), i, self.bos_book_code(), current_chapter_num_str, current_verse_num_str, special_verse_num, next_marker);
                    }
                    let this_start_index = i as u16 - {if last_marker=="c" {1} else {0}};
                    // current_verse_num_str = CompactString::from(special_verse_num);
                    let mut finishing_verse_num_str = CompactString::from(last_verse_num_str.clone());
                    if current_verse_num_str.contains("b") { finishing_verse_num_str = CompactString::from(current_verse_num_str.replace("b", "a")); }
                    // last_bridge_entry_index = Some(i as u16);
                    // last_bridge_verse_num_str = Some(CompactString::from(verse_num));
                    // if let Some(section) = pending.as_mut() {
                    //     if section.start_cv.is_none() {
                    //         section.start_cv = Some(ChapterVerse::new(
                    //             current_chapter_num_str.as_str(),
                    //             current_verse_num_str.as_str(),
                    //         ));
                    //         }
                    //     }
                    //     log::trace!("  Build {} {} section index: at entry #{} {}:{}",
                    //         self.work_name(), self.bos_book_code(), i, current_chapter_num_str, current_verse_num_str );

                    // Close previous section and start new one.
                    if let Some(mut this_pending_section) = pending.take() {
                        if this_start_index > this_pending_section.start_index {
                            if this_pending_section.start_cv.is_none() {
                                this_pending_section.start_cv = Some(ChapterVerse::new(
                                    current_chapter_num_str.as_str(),
                                    current_verse_num_str.as_str(),
                                ));
                            }
                            let mut end_idx = (i as u16).saturating_sub(1);
                            for _ in 0..4 {
                                if have_strict_checking_flag() || cfg!(debug_assertions) {
                                    println!("      Finding end of previous section that started at {}: {} marker = {}", this_pending_section.start_index, end_idx, self.line_entries.get(end_idx as usize).clone().unwrap().marker());
                                }
                                let some_previous_marker = self.line_entries.get(end_idx as usize).clone().unwrap().marker();
                                if is_end_marker(some_previous_marker)
                                || (self.index_data.len()<2 && (["id","usfm","ide"].contains(&some_previous_marker) || title_markers::ALL.contains(&some_previous_marker)))
                                    { break; }
                                end_idx = end_idx.saturating_sub(1);
                            }
                            let (cv, entry) = this_pending_section.into_closed(
                                last_chapter_num_str.as_str(),
                                finishing_verse_num_str.as_str(),
                                end_idx,
                                context.clone());
                            if have_strict_checking_flag() || cfg!(debug_assertions) { assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}"); }
                            self.index_data.insert(cv, entry);
                            // context.pop();
                        }
                    }
                    // New section starts at this section marker
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(),  special_verse_num)),
                        start_index: this_start_index,
                        reason: CompactString::from( if current_verse_num_str=="0" {if process_chapters_as_section_breaks {format!("c/{}", next_marker)} else {format!("{}/c", next_marker)}}
                                                     else {next_marker.to_string()}),
                        name: next_line_entry.clean_text().to_string(),
                        // has_content: false
                        });
                    if have_strict_checking_flag() || cfg!(debug_assertions) { println!("    v= pending = {:?}", pending); }
                    }
            }

            else if marker == "c" {
                let mut next_relevant_marker = "";
                if !process_chapters_as_section_breaks {
                    for adder in 1..9 { // Look at what's ahead
                        if ["v","v="].contains(&self.line_entries.get(i+adder).unwrap().marker()) {
                            next_relevant_marker = self.line_entries.get(i+adder).unwrap().marker();
                            break;
                        }
                    }
                }
                if next_relevant_marker != "v=" // If it's v=, we'll handle that on the next loop instead
                && (!had_section_heading_since_chapters || process_chapters_as_section_breaks) {
                    if have_strict_checking_flag() || cfg!(debug_assertions) {
                        println!("    build {} {} section index at {} {}:{} has c followed by '{}' so need to start new index entry here",
                            self.work_name(), self.bos_book_code(), i, current_chapter_num_str, current_verse_num_str, next_relevant_marker);
                    }
                    // Close previous section and start new one.
                    if let Some(mut this_pending_section) = pending.take() {
                        if i as u16 > this_pending_section.start_index {
                            if this_pending_section.start_cv.is_none() {
                                this_pending_section.start_cv = Some(ChapterVerse::new(
                                    current_chapter_num_str.as_str(),
                                    current_verse_num_str.as_str(),
                                ));
                            }
                            let mut end_idx = (i as u16).saturating_sub(1);
                            let mut found_end_marker = false;
                            for _ in 0..4 {
                                if is_end_marker(self.line_entries.get(end_idx as usize).clone().unwrap().marker()) {
                                    found_end_marker = true;
                                    break;
                                }
                                end_idx = end_idx.saturating_sub(1);
                            }
                            if !found_end_marker { end_idx = (i as u16).saturating_sub(1); } // Go back to where we where
                            let (cv, entry) = this_pending_section.into_closed(
                                last_chapter_num_str.as_str(),
                                last_verse_num_str.as_str(),
                                end_idx,
                                context.clone());
                            if have_strict_checking_flag() || cfg!(debug_assertions) { assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}"); }
                            self.index_data.insert(cv, entry);
                            // context.pop();
                        }
                    }
                    // New section starts at or just before this chapter marker
                    let mut start_idx = i;
                    for subber in 1..i { // Look at what's behind
                        if ["cl"].contains(&self.line_entries.get(i-subber).unwrap().marker()) {
                            start_idx = i - subber;
                            break;
                        }
                    }
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(),
                                                            if current_verse_num_str=="0" {"1"} else {current_verse_num_str.as_str()})),
                        start_index: start_idx.try_into().unwrap(),
                        reason: CompactString::from("c"),
                        name: if book_name.is_empty() {current_chapter_num_str.to_string()} else {format!("{} {}", book_name, current_chapter_num_str)},
                        // has_content: false
                        });
                    }
            }

            else if current_chapter_num_str == "-1" { // We're still in the pre-chapter sections
                if marker == "¬headers" {
                    if let Some(mut section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u16).saturating_sub(1);
                        let (cv, entry) = section.into_closed(
                            current_chapter_num_str.as_str(),
                            current_verse_num_str.as_str(),
                            i as u16,
                            context.clone());
                        if have_strict_checking_flag() || cfg!(debug_assertions) { assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}"); }
                        self.index_data.insert(cv, entry);
                        context.clear();
                    }
                    // pending = Some(PendingSection {
                    //     start_cv: None, //Some(ChapterVerse::new(current_chapter_num_str.as_str(), current_verse_num_str.as_str())),
                    //     start_index: i+1.try_into().unwrap(),
                    //     reason: CNone,
                    //     name: entry.clean_text().to_string(),
                    //     has_content: false,
                    // });
                } else if marker == "intro" && self.line_entries.get(i+1).unwrap().marker() == "is1" {
                    assert!( pending.is_none());
                    // current_chapter_num_str = CompactString::from("0");
                    // if let Some(mut section) = pending.take() {
                    //     assert!(section.reason)
                    //     if section.start_cv.is_none() {
                    //         section.start_cv = Some(ChapterVerse::new(
                    //             current_chapter_num_str.as_str(),
                    //             current_verse_num_str.as_str(),
                    //         ));
                    //     }
                    //     let end_idx = (i as u16).saturating_sub(1);
                    //     let (cv, entry) = section.into_closed(
                    //         last_chapter_num_str.as_str(),
                    //         last_verse_num_str.as_str(),
                    //         end_idx,
                    //         context.clone(),
                    //     );
                    //     self.index_data.insert(cv, entry);
                    //     context.clear();
                    // }
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(), current_verse_num_str.as_str())),
                        start_index: (i+1).try_into().unwrap(),
                        reason: CompactString::const_new("is1"),
                        name: self.line_entries.get(i+1).unwrap().clean_text().to_string(),
                        // has_content: false,
                    });
                } else if marker == "is1" {
                    // current_chapter_num_str = CompactString::from("0");
                    if let Some(mut section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u16).saturating_sub(1);
                        if i as u16 > section.start_index {
                            let (cv, entry) = section.into_closed(
                                last_chapter_num_str.as_str(),
                                last_verse_num_str.as_str(),
                                i as u16,
                                context.clone(),
                            );
                            if have_strict_checking_flag() || cfg!(debug_assertions) { assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}"); }
                            self.index_data.insert(cv, entry);
                            context.clear();
                        }
                    }
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(), current_verse_num_str.as_str())),
                        start_index: i.try_into().unwrap(),
                        reason: CompactString::from(marker),
                        name: line_entry.clean_text().to_string(),
                        // has_content: false,
                    });
                } else if marker == "¬intro" {
                    if let Some(mut section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u16).saturating_sub(1);
                        let (cv, entry) = section.into_closed(
                            current_chapter_num_str.as_str(),
                            current_verse_num_str.as_str(),
                            i as u16,
                            context.clone(),
                        );
                        assert!(["is1","Headers"].contains(&entry.reason_marker()));
                        if have_strict_checking_flag() || cfg!(debug_assertions) { assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}"); }
                        self.index_data.insert(cv, entry);
                        context.clear();
                    }
                }
            }
            

            // } else if is_section_marker(marker) {
            //     log::trace!(
            //         "  Build {} {} section index: found section marker at entry #{} {}={} with {}:{}",
            //         self.work_name(),
            //         self.bos_book_code(),
            //         i,
            //         marker,
            //         entry.clean_text(),
            //         last_chapter_num_str,
            //         last_verse_num_str
            //     );
            //     if marker == "c" {
            //         let was_intro = current_chapter_num_str == "-1";
            //         if was_intro || self.bos_book_code() == "PSA" {
            //             // Transitioning from intro to content (or new Psalm): close the previous section
            //             if let Some(mut section) = pending.take() {
            //                 if section.start_cv.is_none() {
            //                     section.start_cv = Some(ChapterVerse::new(
            //                         current_chapter_num_str.as_str(),
            //                         current_verse_num_str.as_str(),
            //                     ));
            //                 }
            //                 let end_idx = (i as u16).saturating_sub(1);
            //                 let end_v_intro;
            //                 let (end_ch, end_v) = if was_intro {
            //                     end_v_intro = end_idx.to_string();
            //                     ("-1", end_v_intro.as_str())
            //                 } else {
            //                     (last_chapter_num_str.as_str(), last_verse_num_str.as_str())
            //                 };
            //                 let (cv, entry) = section.into_closed(end_ch, end_v, end_idx, context.clone());
            //                 self.index_data.insert(cv, entry);
            //                 context.clear();
            //             }
            //             // Construct section name from book_name + " " + chapter
            //             let chapter_text = entry.clean_text();
            //             let s_name = if !book_name.is_empty() {
            //                 format!("{} {}", book_name, chapter_text)
            //             } else {
            //                 "".to_string()
            //             };

            //             // Start a transition section at this c marker (will be merged with next section heading if no content)
            //             pending = Some(PendingSection {
            //                 start_cv: None,
            //                 start_index: i.try_into().unwrap(),
            //                 reason: CompactString::from("c"),
            //                 name: s_name,
            //                 has_content: false,
            //             });
            //         }

            //         current_chapter_num_str = CompactString::from(entry.clean_text());
            //         current_verse_num_str = CompactString::from("0");
            //    }
            //     if current_chapter_num_str == "-1" {
            //         // In intro mode: close previous section with -1:(i-1) addressing
            //         if let Some(mut section) = pending.take() {
            //             if section.start_cv.is_none() {
            //                 section.start_cv = Some(ChapterVerse::new(
            //                     current_chapter_num_str.as_str(),
            //                     current_verse_num_str.as_str(),
            //                 ));
            //             }
            //             let end_idx = (i as u16).saturating_sub(1);
            //             let (cv, entry) = section.into_closed("-1", &end_idx.to_string(), end_idx, context.clone());
            //             self.index_data.insert(cv, entry);
            //             context.clear();
            //         }
            //         // Start new intro section with -1:i addressing
            //         pending = Some(PendingSection {
            //             start_cv: Some(ChapterVerse::new("-1", i.to_string())),
            //             start_index: i.try_into().unwrap(),
            //             reason: CompactString::from(marker),
            //             name: entry.clean_text().to_string(),
            //             has_content: false,
            //         });
            //     } else if pending.as_ref().is_some_and(|s| !s.has_content) {
            //         // Merge heading into the section if no content seen yet
            //         let section = pending.as_mut().unwrap();
            //         let marker_prefix = if self.bos_book_code() == "PSA" && section.reason == "c" { "c/" } else { "" };
            //         section.reason = CompactString::from(format!("{}{}", marker_prefix, marker));
            //         section.name = entry.clean_text().to_string();
            //         section.start_index = i.try_into().unwrap(); // Update start_index to heading
            //     } else if marker != "c"
            //         && is_section_marker(marker)
            //         && last_bridge_entry_index.is_some_and(|idx| idx + 1 == i as u16)
            //         {
            //         // A bridge verse immediately before this section heading should define the section start.
            //         if let Some(mut section) = pending.take() {
            //             if section.start_cv.is_none() {
            //                 section.start_cv = Some(ChapterVerse::new(
            //                     current_chapter_num_str.as_str(),
            //                     current_verse_num_str.as_str(),
            //                 ));
            //             }
            //             let end_idx = (i as u16).saturating_sub(1);
            //             let (cv, entry) = section.into_closed(
            //                 last_chapter_num_str.as_str(),
            //                 last_verse_num_str.as_str(),
            //                 end_idx,
            //                 context.clone(),
            //             );
            //             self.index_data.insert(cv, entry);
            //             context.clear();
            //         }
            //         let start_index = last_bridge_entry_index.take().unwrap_or(i as u16);
            //         let bridge_verse = last_bridge_verse_num_str.as_deref().unwrap_or(current_verse_num_str.as_str());
            //         pending = Some(PendingSection {
            //             start_cv: Some(ChapterVerse::new(
            //                 current_chapter_num_str.as_str(),
            //                 bridge_verse,
            //             )),
            //             start_index,
            //             reason: CompactString::from(marker),
            //             name: entry.clean_text().to_string(),
            //             has_content: false,
            //         });
            //     } else {
            //         // Normal content: close previous section and start new one.
            //         if let Some(mut section) = pending.take() {
            //             if section.start_cv.is_none() {
            //                 section.start_cv = Some(ChapterVerse::new(
            //                     current_chapter_num_str.as_str(),
            //                     current_verse_num_str.as_str(),
            //                 ));
            //             }
            //             let end_idx = (i as u16).saturating_sub(1);
            //             let (cv, entry) = section.into_closed(
            //                 last_chapter_num_str.as_str(),
            //                 last_verse_num_str.as_str(),
            //                 end_idx,
            //                 context.clone(),
            //             );
            //             self.index_data.insert(cv, entry);
            //             context.clear();
            //         }
            //         // New section starts at this section marker
            //         pending = Some(PendingSection {
            //             start_cv: None,
            //             start_index: i.try_into().unwrap(),
            //             reason: CompactString::from(marker),
            //             name: entry.clean_text().to_string(),
            //             has_content: false,
            //         });
            //     }
            // } else if marker == "v" {
            //     let verse_num = entry.clean_text();
            //     current_verse_num_str = CompactString::from(verse_num);
            //     last_bridge_entry_index = None;
            //     last_bridge_verse_num_str = None;
            //     if let Some(section) = pending.as_mut() {
            //         if section.start_cv.is_none() {
            //             section.start_cv = Some(ChapterVerse::new(
            //                 current_chapter_num_str.as_str(),
            //                 current_verse_num_str.as_str(),
            //             ));
            //         }
            //     }
            //     log::trace!(
            //         "  Build {} {} section index: at entry #{} {}:{}",
            //         self.work_name(),
            //         self.bos_book_code(),
            //         i,
            //         current_chapter_num_str,
            //         current_verse_num_str
            //     );
            // } else if marker == "id" {
            //     pending = Some(PendingSection {
            //         start_cv: Some(ChapterVerse::new(
            //             current_chapter_num_str.as_str(),
            //             current_verse_num_str.as_str(),
            //         )),
            //         start_index: i.try_into().unwrap(),
            //         reason: CompactString::from("Headers"),
            //         name: entry.clean_text().chars().take(3).collect::<String>(),
            //         has_content: false,
            //     });
            // }

            // if marker == "v~" {
            //     if let Some(section) = pending.as_mut() {
            //         section.has_content = true;
            //     }
            // }
            
            // Record current CV for the NEXT entry to use as its "previous" CV
            // But don't update it for markers that change the CV themselves,
            // so that if a section ends with such a marker, it uses the previous CV for endCV.
            if marker != "v" && marker != "v=" && marker != "c" {
                last_chapter_num_str = current_chapter_num_str.clone();
                last_verse_num_str = current_verse_num_str.clone();
            }
            last_marker = marker;
        }
        if have_strict_checking_flag() || cfg!(debug_assertions) { println!("Section heading loop finished with {} entries and pending={:?}", self.index_data.len(), pending); }

        // Close final section
        if let Some(section) = pending.as_mut().filter(|s| s.start_cv.is_none()) {
            section.start_cv = Some(ChapterVerse::new(
                current_chapter_num_str.as_str(),
                current_verse_num_str.as_str(),
            ));
        }
        // Don't include the ¬chapters line in the final section
        let mut end_idx = (self.line_entries.len() as u16).saturating_sub(1);
        if self.line_entries.get(end_idx as usize).clone().unwrap().marker() == "¬chapters" {
             end_idx = end_idx.saturating_sub(1); // Go back to the one before
             assert!(is_end_marker(self.line_entries.get(end_idx as usize).clone().unwrap().marker()));
        }
        if let Some(section) = pending {
            if have_strict_checking_flag() || cfg!(debug_assertions) { println!("  Adding final section"); }
            let (cv, entry) = section.into_closed(
                current_chapter_num_str.as_str(),
                current_verse_num_str.as_str(),
                end_idx,
                context,
            );
            if self.index_data.contains_key(&cv) { // This can happen for alternative endings to Mark
                if have_strict_checking_flag() || cfg!(debug_assertions) {
                    assert_eq!(self.bos_book_code(), "MRK", "{} {} section index is losing a key: {}", self.work_name(), self.bos_book_code(), cv);
                }
                self.index_data.insert(ChapterVerse::new(cv.chapter(), format!("{}b", cv.verse())), entry); // Append another b suffix
            } else {
                if have_strict_checking_flag() || cfg!(debug_assertions) { assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}"); }
                self.index_data.insert(cv, entry);
            }
        }
        if have_strict_checking_flag() || cfg!(debug_assertions) { println!("Section heading build finished with {} entries", self.index_data.len()); }
        self.indexed = true;

        if have_strict_checking_flag() || cfg!(debug_assertions) {
             let validation_results = self.validate(&self.line_entries);
             if !validation_results.is_empty() {
                panic!("{} {} section index validation failed with issues: {:?}", self.work_name, self.bos_book_code, validation_results);
            }
        }
        Ok(())
    }

    fn format_section_result(&self, res: Result<InternalBibleEntryList, LookupError>) -> String {
        match res {
            Ok(entries) => format!("{}", entries),
            Err(e) => format!("{}", e),
        }
    }

    /// Validate the section index structure.
    ///
    /// Returns a list of any issues found.
    fn validate(&self, line_entries: &InternalBibleEntryList) -> Vec<String> {
        let mut issues = Vec::new();

        if !self.indexed {
            issues.push(format!("{} {} section index has not been built", self.work_name, self.bos_book_code));
            return issues;
        }

        // Check for overlapping entries,
        //  for entries containing incorrect verse numbers,
        //  and that the last line in an index segment is an end marker
        //  and that there's entries for -1:0 and 1:1.
        let mut have_m1_0 = false;
        let mut have_1_0 = false; // Surely we only need one of these???
        let mut have_1_1 = false; // Surely we only need one of these???
        let mut last_end: usize = 0;
        for (cv, entry) in &self.index_data {
            if cv.chapter()=="-1" && cv.verse()=="0" { have_m1_0 = true; }
            if cv.chapter()=="1" && cv.verse()=="0" { have_1_0 = true; }
            if cv.chapter()=="1" && (cv.verse()=="1" || cv.verse_int().unwrap()==1) { have_1_1 = true; } // Could be a verse bridge, e.g., '1-2'
            assert!(!cv.chapter().is_empty() && (cv.chapter().chars().all(|c| c.is_ascii_digit()) || cv.chapter() == "-1"),
                "{} {} chapter should be a non-empty string of digits or '-1': found '{}' from {}",
                self.work_name, self.bos_book_code, cv.chapter(), cv);
            assert!(!cv.verse().is_empty() && cv.verse().chars().all(|c| c.is_ascii_digit() || c=='-' || c=='b'),
                "{} {} verse should be a non-empty string of digits (or a verse bridge): found '{}' from {}",
                self.work_name, self.bos_book_code, cv.verse(), cv);

            if entry.start_index() < last_end {
                issues.push(format!("{} {} {}: entry_index {} < previous end {}",
                    self.work_name(), self.bos_book_code(), cv, entry.start_index(), last_end));
            }

            if cv.chapter() != "-1"  {
                // for processed_line_entry in self.entries.slice(entry.start_index(), entry.end_index()) {
                //     if processed_line_entry.marker() == "v" || processed_line_entry.marker() == "¬v" {
                //         assert!(processed_line_entry.clean_text().starts_with(cv.verse().to_string().as_str()), "Validating {} {} CV index entry for {} found unexpected verse marker with text {}='{}'\n\n{}:{} {}\n\n{} {}\n\n{}:{} {}",
                //             self.work_name(), self.bos_book_code(), cv, processed_line_entry.marker(),processed_line_entry.clean_text(),
                //             cv.chapter(), cv.verse_int().unwrap_or(1)-1, self.format_section_result(self.get_section_entries(&ChapterVerse::new(cv.chapter(), (cv.verse_int().unwrap_or(1) - 1).to_string().as_str()))),
                //             cv, self.format_section_result(self.get_section_entries(cv)),
                //             cv.chapter(), cv.verse_int().unwrap_or(1)+1, self.format_section_result(self.get_section_entries(&ChapterVerse::new(cv.chapter(), (cv.verse_int().unwrap_or(1) + 1).to_string().as_str()))));
                //         }
                //     }
                
                let final_marker_in_entry = self.line_entries.get(entry.start_index() + entry.entry_count() as usize - 1).map(|e| e.marker()).unwrap_or("N/A");
                if !is_end_marker(final_marker_in_entry) && cv.verse() != "0" {
                    // println!("Entry for {} {} {} is at index {} with end marker '{}'", self.work_name(), self.bos_book_code(), cv, entry.entry_index(), final_marker_in_entry);
                    // assert!(cv.verse()=="0" || is_end_marker(final_marker_in_entry),
                    //     "Validating {} {} CV index entry for {} expected last entry to be an end marker but found marker '{}'",
                    //     self.work_name(), self.bos_book_code(), cv, final_marker_in_entry);
                    issues.push(format!(
                        "{} {} section index entry for {} expected last entry to be an end marker but found marker '{}'",
                        self.work_name(), self.bos_book_code(), cv, final_marker_in_entry
                    ));
                    }
                }
                last_end = entry.end_index();
            }

        assert!(have_m1_0 || line_entries.get(0).unwrap().marker()=="chapters", // i.e., no preliminary markers at all!!!
                    "Expected {} {} section index '-1:0' entry:\nKeys {:?}\nHave {:?}\nFrom {:?}",
                    self.work_name(), self.bos_book_code(), self.index_data.keys(), self.index_data.iter().take(4).collect::<std::collections::HashMap<_, _>>(), line_entries.iter().take(10).collect::<std::vec::Vec<_>>());
        assert!(have_1_0 || have_1_1 || !is_chapter_verse_book(&self.bos_book_code),
                    "{} {} section index is missing 1:1 entry\nKeys {:?}\nHave {:?}\nFrom {:?}",
                    self.work_name(), self.bos_book_code(), self.index_data.keys(), self.index_data.iter().take(6).collect::<std::collections::HashMap<_, _>>(), line_entries.iter().take(10).collect::<std::vec::Vec<_>>());
        // Temporarily disabled but should it be reenabled again???
        // // Check that all entries are covered
        // if last_end != self.entries.len() {
        //     issues.push(format!(
        //         "{} {} section index covers {} entries but list has {}",
        //         self.work_name(), self.bos_book_code(), last_end, self.entries.len()));
        // }

        issues
    }
}


/// Tracks a section being built before it's finalized and inserted into the index.
#[derive(Debug)]
struct PendingSection {
    /// `None` when the start CV isn't known yet (heading appeared before first verse).
    start_cv: Option<ChapterVerse>,
    start_index: u16,
    reason: CompactString,
    name: String,
    // Whether this section has had actual content (text) yet.
    // has_content: bool,
}

impl PendingSection {
    fn into_closed(
        self,
        end_chapter: &str,
        end_verse: &str,
        end_index: u16,
        context: Vec<CompactString>,
    ) -> (ChapterVerse, SectionIndexEntry) {
        let start_cv = self.start_cv.expect("section closed before start CV was resolved");
        if have_strict_checking_flag() || cfg!(debug_assertions) {
            println!("      Wanting to close pending {} {} section with {}:{} at {} with {}:[{}]",
                start_cv, self.start_index, end_chapter, end_verse, end_index, self.reason, context.join(", "));
            assert!(end_index > self.start_index,
                "Attempting to close {} start_index={} section at end_index={}", start_cv, self.start_index, end_index);
            assert!(get_small_leading_int(end_verse).unwrap() >= start_cv.verse_int().unwrap() || get_small_leading_int(end_chapter).unwrap() > start_cv.chapter_int().unwrap(),
                "Attempting to close {} section at {}:{}", start_cv, end_chapter, end_verse);
            }
        let entry = SectionIndexEntry::new(
            end_chapter,
            end_verse,
            self.start_index,
            end_index,
            self.reason,
            self.name,
            context,
        );
        (start_cv, entry)
    }
}

/// Check if a marker is a section-defining marker.
fn is_section_marker(marker: &str) -> bool {
    SECTION_MARKERS.contains(&marker)
}

impl std::fmt::Display for InternalBibleBookSectionIndex {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(
            f,
            "InternalBibleBookSectionIndex({} {}):",
            self.work_name, self.bos_book_code
        )?;
        if !self.indexed {
            writeln!(f, "  Not indexed")?;
        } else if self.index_data.is_empty() {
            writeln!(f, "  Empty")?;
        } else {
            writeln!(f, "  {} sections", self.index_data.len())?;
            for (i, (cv, entry)) in self.index_data.iter().enumerate() {
                if i >= 20 {
                    writeln!(f, "  ...")?;
                    break;
                }
                writeln!(f, "  {}: {}", cv, entry)?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]

mod tests {
    use super::*;
    use crate::entry::InternalBibleEntry;
    use crate::set_strict_checking_flag;
    
    fn create_sample_gen_test_entries() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "GEN Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("ide", "UTF-8")); // 2
        entries.push(InternalBibleEntry::simple("headers", "")); // 3
        entries.push(InternalBibleEntry::simple("h", "Genesis")); // 4
        entries.push(InternalBibleEntry::simple("mt1", "Book of Genesis")); // 5
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 6

        // Section 2 (Intro)
        entries.push(InternalBibleEntry::simple("intro", "")); // 7
        entries.push(InternalBibleEntry::simple("is1", "Introduction to Genesis")); // 8
        entries.push(InternalBibleEntry::simple("ip", "An introductory paragraph.")); // 9
        entries.push(InternalBibleEntry::simple("¬intro", "")); // 10

        // Section 3
        entries.push(InternalBibleEntry::simple("chapters", "")); // 11
        entries.push(InternalBibleEntry::simple("c", "1")); // 12
        entries.push(InternalBibleEntry::simple("v=", "1")); // 13
        entries.push(InternalBibleEntry::simple("s1", "The Creation")); // 14
        entries.push(InternalBibleEntry::simple("p", "")); // 15
        entries.push(InternalBibleEntry::simple("v", "1")); // 16
        entries.push(InternalBibleEntry::simple("v~", "In the beginning...")); // 17
        entries.push(InternalBibleEntry::simple("v", "2")); // 18
        entries.push(InternalBibleEntry::simple("v~", "And the earth was without form...")); // 19
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 20
        entries.push(InternalBibleEntry::simple("c", "2")); // 21
        entries.push(InternalBibleEntry::simple("nb", "")); // 22
        entries.push(InternalBibleEntry::simple("v", "1")); // 23
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of chapter 2...")); // 24
        entries.push(InternalBibleEntry::simple("¬p", "")); // 25
        
        // Section 4
        entries.push(InternalBibleEntry::simple("v=", "2")); // 26
        entries.push(InternalBibleEntry::simple("s1", "The Fall")); // 27
        entries.push(InternalBibleEntry::simple("p", "")); // 28
        entries.push(InternalBibleEntry::simple("v", "2")); // 29
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of chapter 2...")); // 30
        entries.push(InternalBibleEntry::simple("v", "3")); // 31
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of chapter 2...")); // 32
        entries.push(InternalBibleEntry::simple("¬p", "")); // 33
        entries.push(InternalBibleEntry::simple("¬c", "2")); // 34

        // Section 5
        entries.push(InternalBibleEntry::simple("c", "3")); // 35
        entries.push(InternalBibleEntry::simple("v=", "1")); // 36
        entries.push(InternalBibleEntry::simple("s1", "Chapter Three")); // 37
        entries.push(InternalBibleEntry::simple("rem", "/s1 Alternative heading")); // 38
        entries.push(InternalBibleEntry::simple("p", "")); // 39
        entries.push(InternalBibleEntry::simple("v", "1")); // 40
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of chapter 3...")); // 41
        entries.push(InternalBibleEntry::simple("v", "2")); // 42
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of chapter 3...")); // 43
        entries.push(InternalBibleEntry::simple("¬p", "")); // 44
        entries.push(InternalBibleEntry::simple("¬c", "3")); // 45
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 46

        entries
    }

    #[test]
    fn test_build_sample_gen_section_index() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        section_index.build(create_sample_gen_test_entries()).unwrap();
        log::trace!("Index1:{}", section_index);
        assert!(section_index.is_indexed());

        assert_eq!(section_index.len(), 5, "{section_index}"); // Headers, is1, s1 (Creation), s1 (Fall), s1 (Chapter Three)
        let section_reasons: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(section_reasons, vec!["Headers", "is1", "s1/c", "s1", "s1/c"]);

        let first_section = section_index.index_data.get_index(0).unwrap();
        assert_eq!(first_section.0.to_string(), "-1:0"); // ID Header starts at -1:0
        assert_eq!(first_section.1.end_cv().to_string(), "-1:6"); // ID Header ends at -1:6
        assert_eq!(first_section.1.start_index(), 0); // starts at id
        assert_eq!(first_section.1.end_index(), 6); // ends at ¬headers
        assert_eq!(first_section.1.reason_marker(), "Headers");
        assert_eq!(first_section.1.section_name(), "GEN");
        assert_eq!(first_section.1.context(), Vec::<CompactString>::new());

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "-1:8"); // starts at -1:8 // was -1:8
        assert_eq!(second_section.1.end_cv().to_string(), "-1:10"); // ends at -1:10
        assert_eq!(second_section.1.start_index(), 8); // starts at is1
        assert_eq!(second_section.1.end_index(), 10); // ends at ¬intro
        assert_eq!(second_section.1.reason_marker(), "is1");
        assert_eq!(second_section.1.section_name(), "Introduction to Genesis");
        assert_eq!(second_section.1.context(), Vec::<CompactString>::new());

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:1"); // starts at 1:1
        assert_eq!(third_section.1.end_cv().to_string(), "2:1"); // ends at 2:1
        assert_eq!(third_section.1.start_index(), 12); // starts at the c before s1 marker
        assert_eq!(third_section.1.end_index(), 25); // ends at ¬p
        assert_eq!(third_section.1.reason_marker(), "s1/c");
        assert_eq!(third_section.1.section_name(), "The Creation");
        assert_eq!(third_section.1.context(), ["chapters", "c"]);

        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "2:2"); // starts at 2:2
        assert_eq!(fourth_section.1.end_cv().to_string(), "2:3"); // ends at 2:3
        assert_eq!(fourth_section.1.start_index(), 26); // starts at the v= before s1 marker
        assert_eq!(fourth_section.1.end_index(), 34); // ends at ¬c
        assert_eq!(fourth_section.1.reason_marker(), "s1");
        assert_eq!(fourth_section.1.section_name(), "The Fall");
        assert_eq!(fourth_section.1.context(), ["chapters", "c"]);

        let fifth_section = section_index.index_data.get_index(4).unwrap();
        assert_eq!(fifth_section.0.to_string(), "3:1"); // starts at 3:1
        assert_eq!(fifth_section.1.end_cv().to_string(), "3:2"); // ends at 3:2
        assert_eq!(fifth_section.1.start_index(), 35); // starts at the c before s1 marker
        assert_eq!(fifth_section.1.end_index(), 45); // Don't include the ¬chapters
        assert_eq!(fifth_section.1.reason_marker(), "s1/c");
        assert_eq!(fifth_section.1.section_name(), "Chapter Three");
        assert_eq!(fifth_section.1.context(), ["chapters", "c"]);
    }

    #[test]
    fn test_test_kjb_mark() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "MRK")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("ide", "UTF-8")); // 2
        entries.push(InternalBibleEntry::simple("headers", "")); // 3
        entries.push(InternalBibleEntry::simple("h", "Mark")); // 4
        entries.push(InternalBibleEntry::simple("toc1", "Mark")); // 5
        entries.push(InternalBibleEntry::simple("toc2", "Mark")); // 6
        entries.push(InternalBibleEntry::simple("toc3", "Mrk")); // 7
        entries.push(InternalBibleEntry::simple("ie", "")); // 8
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 9
        entries.push(InternalBibleEntry::simple("chapters", "")); // 10
        entries.push(InternalBibleEntry::simple("cl", "CHAP")); // 11
        entries.push(InternalBibleEntry::simple("c", "1")); // 12
        entries.push(InternalBibleEntry::simple("iex", "1 The office of Iohn the Baptist. 9 Iesus is baptized, 12 tempted, 14 he preacheth: 16 calleth Peter, Andrew, Iames and Iohn: 23 healeth one that had a deuill, 29 Peters mother in law, 32 many diseased persons, 41 and cleanseth the Leper.")); // 13
        entries.push(InternalBibleEntry::simple("v", "1")); // 14
        entries.push(InternalBibleEntry::simple("v~", "¶ The beginning of the Gospel of Iesus Christ, the Sonne of God,")); // 15
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 16
        entries.push(InternalBibleEntry::simple("v", "2")); // 17
        entries.push(InternalBibleEntry::simple("v~", "As it is written in the Prophets, Behold, I send my messenger before thy face, which shall prepare thy way before thee.")); // 18
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 19
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 20
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 21

        let mut section_index = InternalBibleBookSectionIndex::new("KJB", "TST");
        section_index.build(entries).unwrap();

        assert_eq!(section_index.len(), 2);
        let section_reasons: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(section_reasons, vec!["Headers", "c"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1");
        assert_eq!(second_section.1.start_index(), 11); // The 'cl' marker
        assert_eq!(second_section.1.end_index(), 20); // The '¬c' marker
    }

    #[test]
    fn test_section_index_with_single_section_heading_at_verse_2() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "TST")); // 0
        entries.push(InternalBibleEntry::simple("headers", "")); // 1
        entries.push(InternalBibleEntry::simple("h", "Test1")); // 2
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 3
        entries.push(InternalBibleEntry::simple("chapters", "")); // 4
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("v", "1")); // 6
        entries.push(InternalBibleEntry::simple("v~", "First section text")); // 7
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 8
        entries.push(InternalBibleEntry::simple("v=", "2")); // 9
        entries.push(InternalBibleEntry::simple("s1", "Second section")); // 10
        entries.push(InternalBibleEntry::simple("p", "")); // 11
        entries.push(InternalBibleEntry::simple("v", "2")); // 12
        entries.push(InternalBibleEntry::simple("v~", "Second section text")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 14
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 15
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 16

        let mut section_index = InternalBibleBookSectionIndex::new("XSV", "TST");
        section_index.build(entries).unwrap();

        assert_eq!(section_index.len(), 3);
        let section_reasons: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(section_reasons, vec!["Headers", "c", "s1"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1");
        assert_eq!(second_section.1.start_index(), 5);
        assert_eq!(second_section.1.end_index(), 8);

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:2");
        assert_eq!(third_section.1.start_index(), 9);
        assert_eq!(third_section.1.end_index(), 15); // The '¬c' marker
    }

    #[test]
    fn test_section_index_with_ms1() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "JOB")); // 0
        entries.push(InternalBibleEntry::simple("headers", "")); // 1
        entries.push(InternalBibleEntry::simple("h", "Test1")); // 2
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 3
        entries.push(InternalBibleEntry::simple("chapters", "")); // 4
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("v=", "1")); // 6
        entries.push(InternalBibleEntry::simple("ms1", "SECTION ONE: The introduction")); // 7
        entries.push(InternalBibleEntry::simple("mr", "(1:1–2:13)")); // 8
        entries.push(InternalBibleEntry::simple("s1", "Iyyov's prosperous life")); // 9
        entries.push(InternalBibleEntry::simple("rem", "/s1 Prologue; Job and His Family; Satan Tests Job")); // 10
        entries.push(InternalBibleEntry::simple("p", "")); // 11
        entries.push(InternalBibleEntry::simple("v", "1")); // 12
        entries.push(InternalBibleEntry::simple("v~", "First section text")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 14
        entries.push(InternalBibleEntry::simple("v=", "2")); // 15
        entries.push(InternalBibleEntry::simple("s1", "Second section")); // 16
        entries.push(InternalBibleEntry::simple("p", "")); // 17
        entries.push(InternalBibleEntry::simple("v", "2")); // 18
        entries.push(InternalBibleEntry::simple("v~", "Second section text")); // 19
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 20
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 21
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 22

        let mut section_index = InternalBibleBookSectionIndex::new("PQR", "JOB");
        section_index.build(entries).unwrap();

        assert_eq!(section_index.len(), 3);
        let section_reasons: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(section_reasons, vec!["Headers", "ms1/c", "s1"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1");
        assert_eq!(second_section.1.start_index(), 5);
        assert_eq!(second_section.1.end_index(), 14);

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:2");
        assert_eq!(third_section.1.start_index(), 15);
        assert_eq!(third_section.1.end_index(), 21);
    }

    #[test]
    fn test_bridge_verse_before_section_heading_starts_section_complex() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "TST")); // 0
        entries.push(InternalBibleEntry::simple("h", "Test2")); // 1
        entries.push(InternalBibleEntry::simple("chapters", "")); // 2
        entries.push(InternalBibleEntry::simple("c", "1")); // 3
        entries.push(InternalBibleEntry::simple("v", "1")); // 4
        entries.push(InternalBibleEntry::simple("v~", "Verse one text")); // 5
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 6
        entries.push(InternalBibleEntry::simple("v=", "2")); // 7
        entries.push(InternalBibleEntry::simple("s1", "First section heading")); // 8
        entries.push(InternalBibleEntry::simple("p", "")); // 9
        entries.push(InternalBibleEntry::simple("v", "2")); // 10
        entries.push(InternalBibleEntry::simple("v~", "Verse two text")); // 11
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 12
        entries.push(InternalBibleEntry::simple("v", "3")); // 13
        entries.push(InternalBibleEntry::simple("v~", "Verse three text")); // 14
        entries.push(InternalBibleEntry::simple("¬p", "")); // 15
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 16
        entries.push(InternalBibleEntry::simple("v=", "3b")); // 17
        entries.push(InternalBibleEntry::simple("s1", "Second section heading")); // 18
        entries.push(InternalBibleEntry::simple("p", "")); // 19
        entries.push(InternalBibleEntry::simple("v~", "More verse three text")); // 20
        entries.push(InternalBibleEntry::simple("¬v", "3")); // 21
        entries.push(InternalBibleEntry::simple("¬p", "")); // 22
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 23
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 24
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 25

        let mut section_index = InternalBibleBookSectionIndex::new("YSV", "TST");
        section_index.build(entries).unwrap();

        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "c", "s1", "s1"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1");
        assert_eq!(second_section.1.start_index(), 3);
        assert_eq!(second_section.1.end_index(), 6);

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:2");
        assert_eq!(third_section.1.start_index(), 7);
        assert_eq!(third_section.1.end_index(), 16);

        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:3b");
        assert_eq!(fourth_section.1.start_index(), 17);
        assert_eq!(fourth_section.1.end_index(), 24);
    }

    fn create_sample_mrk_test_entries() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "MRK Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("headers", "")); // 2
        entries.push(InternalBibleEntry::simple("h", "Mark")); // 3
        entries.push(InternalBibleEntry::simple("mt1", "Mark")); // 4
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 5

        entries.push(InternalBibleEntry::simple("chapters", "")); // 6

        // Section 2 Chapter begins WITHOUT a section heading (should be absorbed into the first section)
        entries.push(InternalBibleEntry::simple("c", "1")); // 7
        entries.push(InternalBibleEntry::simple("p", "")); // 8
        entries.push(InternalBibleEntry::simple("v", "1")); // 9
        entries.push(InternalBibleEntry::simple("v~", "First verse of Mark...")); // 10
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 11
        entries.push(InternalBibleEntry::simple("v", "2")); // 12
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Mark 1...")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 14

        // Section 3
        entries.push(InternalBibleEntry::simple("v=", "3")); // 15
        entries.push(InternalBibleEntry::simple("s1", "First section heading")); // 16
        entries.push(InternalBibleEntry::simple("p", "")); // 17
        entries.push(InternalBibleEntry::simple("v", "3")); // 18
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of chapter 1...")); // 19
        entries.push(InternalBibleEntry::simple("v", "4")); // 20
        entries.push(InternalBibleEntry::simple("v~", "Verse 4 of chapter 1...")); // 21
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 22

        // Section 4
        entries.push(InternalBibleEntry::simple("v=", "4b")); // 23
        entries.push(InternalBibleEntry::simple("s1", "First alternative ending to Mark")); // 24
        entries.push(InternalBibleEntry::simple("p", "")); // 25
        entries.push(InternalBibleEntry::simple("v~", "No verses here--just text...")); // 26
        entries.push(InternalBibleEntry::simple("¬v", "4")); // 27
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 28

        // Section 5
        entries.push(InternalBibleEntry::simple("v=", "9")); // 29
        entries.push(InternalBibleEntry::simple("s1", "Second alternative ending to Mark")); // 30
        entries.push(InternalBibleEntry::simple("p", "")); // 31
        entries.push(InternalBibleEntry::simple("v", "9")); // 32
        entries.push(InternalBibleEntry::simple("v~", "Has verses here...")); // 33
        entries.push(InternalBibleEntry::simple("¬v", "9")); // 34
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 35
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 36
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 37

        entries
    }

    #[test]
    fn test_build_sample_mrk_section_index() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("YSV", "MRK");
        section_index.build(create_sample_mrk_test_entries()).unwrap();
        log::trace!("Index2:{}", section_index);
        assert!(section_index.is_indexed());

        assert_eq!(section_index.len(), 5); // Headers, c, s1, s1 x2 (at end)

        let first_section = section_index.index_data.get_index(0).unwrap();
        assert_eq!(first_section.0.to_string(), "-1:0"); // ID Header starts at -1:0
        assert_eq!(first_section.1.end_cv().to_string(), "-1:5"); // ID Header ends at -1:5
        assert_eq!(first_section.1.start_index(), 0); // starts at beginning
        assert_eq!(first_section.1.end_index(), 5); // ends at '¬headers'
        assert_eq!(first_section.1.reason_marker(), "Headers");
        assert_eq!(first_section.1.section_name(), "MRK");

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1"); // starts at 1:1
        assert_eq!(second_section.1.end_cv().to_string(), "1:2"); // ends at 1:2
        assert_eq!(second_section.1.start_index(), 7); // starts at c marker
        assert_eq!(second_section.1.end_index(), 14); // ends at ¬v marker
        assert_eq!(second_section.1.reason_marker(), "c");
        assert_eq!(second_section.1.section_name(), "Mark 1");
    // #[ignore = "Need to get section index working properly"]

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:3"); // starts at 1:3
        assert_eq!(third_section.1.end_cv().to_string(), "1:4"); // ends at 1:4
        assert_eq!(third_section.1.start_index(), 15); // starts' at v= marker
        assert_eq!(third_section.1.end_index(), 22); // ends at '¬s1'
        assert_eq!(third_section.1.reason_marker(), "s1");
        assert_eq!(third_section.1.section_name(), "First section heading");

        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:4b"); // starts at 1:4b
        assert_eq!(fourth_section.1.end_cv().to_string(), "1:4"); // ends at 1:4
        assert_eq!(fourth_section.1.start_index(), 23); // starts at 'v='
        assert_eq!(fourth_section.1.end_index(), 28); // ends at '¬s1'
        assert_eq!(fourth_section.1.reason_marker(), "s1");
        assert_eq!(fourth_section.1.section_name(), "First alternative ending to Mark");

        let fifth_section = section_index.index_data.get_index(4).unwrap();
        assert_eq!(fifth_section.0.to_string(), "1:9"); // starts at 1:4
        assert_eq!(fifth_section.1.end_cv().to_string(), "1:9"); // ends at 1:4
        assert_eq!(fifth_section.1.start_index(), 29); // starts at 'v='
        assert_eq!(fifth_section.1.end_index(), 36); // ends at '¬s1'
        assert_eq!(fifth_section.1.reason_marker(), "s1");
        assert_eq!(fifth_section.1.section_name(), "Second alternative ending to Mark");
    }

    fn create_sample_psa_test_entries() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "PSA Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("mt1", "Psalms")); // 2

        // Section 2 (Intro)
        entries.push(InternalBibleEntry::simple("is1", "Introduction to Psalms")); // 3
        entries.push(InternalBibleEntry::simple("ip", "An introductory paragraph.")); // 4

        // Section 3 Chapter begins WITHOUT a section heading (should be absorbed into the first section)
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("p", "")); // 6
        entries.push(InternalBibleEntry::simple("v", "1")); // 7
        entries.push(InternalBibleEntry::simple("v~", "First verse of Psalms...")); // 8
        entries.push(InternalBibleEntry::simple("v", "2")); // 9
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 1...")); // 10

        // Section 4
        entries.push(InternalBibleEntry::simple("s1", "First section heading mid-chapter")); // 11
        entries.push(InternalBibleEntry::simple("p", "")); // 12
        entries.push(InternalBibleEntry::simple("v", "3")); // 13
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of Psalm 1...")); // 14
        entries.push(InternalBibleEntry::simple("v", "4")); // 15
        entries.push(InternalBibleEntry::simple("v~", "Verse 4 of Psalm 1...")); // 16

        // Section 5 - chapter change without a new section heading should start a new section
        entries.push(InternalBibleEntry::simple("c", "2")); // 17
        entries.push(InternalBibleEntry::simple("p", "")); // 18
        entries.push(InternalBibleEntry::simple("v", "1")); // 19
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of Psalm 2...")); // 20
        entries.push(InternalBibleEntry::simple("v", "2")); // 21
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 2...")); // 22

        // Section 6 - chapter change with a new section heading should start a new section
        entries.push(InternalBibleEntry::simple("c", "3")); // 23
        entries.push(InternalBibleEntry::simple("s1", "Psa 3 section heading")); // 24
        entries.push(InternalBibleEntry::simple("q1", "")); // 25
        entries.push(InternalBibleEntry::simple("v", "1")); // 26
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of Psalm 3...")); // 27
        entries.push(InternalBibleEntry::simple("v", "2")); // 28
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 3...")); // 29

        entries
    }

    #[test]
    #[ignore = "Need to get section index or test working properly"]
    fn test_build_sample_section_index_psa() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("ZSV", "PSA");
        section_index.build(create_sample_psa_test_entries()).unwrap();
        log::trace!("PSA index:{}", section_index);
        assert!(section_index.is_indexed());

        assert_eq!(section_index.len(), 6); // Headers, is1, c, s1, c, c/s1 (merged)

        // 0: Headers
        let first_section = section_index.index_data.get_index(0).unwrap();
        assert_eq!(first_section.0.to_string(), "-1:0");
        assert_eq!(first_section.1.end_cv().to_string(), "-1:2");
        assert_eq!(first_section.1.start_index(), 0); // starts at entry index 0
        assert_eq!(first_section.1.end_index(), 2); // ends at entry index 2
        assert_eq!(first_section.1.reason_marker(), "Headers");
        assert_eq!(first_section.1.section_name(), "PSA");

        // 1: Intro
        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "-1:3");
        assert_eq!(second_section.1.end_cv().to_string(), "-1:4");
        assert_eq!(second_section.1.start_index(), 3); // starts at entry index 3
        assert_eq!(second_section.1.end_index(), 4); // ends at entry index 4
        assert_eq!(second_section.1.reason_marker(), "is1");
        assert_eq!(second_section.1.section_name(), "Introduction to Psalms");

        // 2: Chapter 1
        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:1");
        assert_eq!(third_section.1.end_cv().to_string(), "1:2");
        assert_eq!(third_section.1.start_index(), 5); // starts at entry index 5
        assert_eq!(third_section.1.end_index(), 10); // ends at entry index 10
        assert_eq!(third_section.1.reason_marker(), "c");
        assert_eq!(third_section.1.section_name(), "");

        // 3: Mid-chapter heading
        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:3");
        assert_eq!(fourth_section.1.end_cv().to_string(), "1:4");
        assert_eq!(fourth_section.1.start_index(), 11); // starts at entry index 11
        assert_eq!(fourth_section.1.end_index(), 16); // ends at entry index 16
        assert_eq!(fourth_section.1.reason_marker(), "s1");
        assert_eq!(fourth_section.1.section_name(), "First section heading mid-chapter");

        // 4: Chapter 2
        let fifth_section = section_index.index_data.get_index(4).unwrap();
        assert_eq!(fifth_section.0.to_string(), "2:1");
        assert_eq!(fifth_section.1.end_cv().to_string(), "2:2");
        assert_eq!(fifth_section.1.start_index(), 17); // starts at entry index 17
        assert_eq!(fifth_section.1.end_index(), 22); // ends at entry index 22
        assert_eq!(fifth_section.1.reason_marker(), "c");
        assert_eq!(fifth_section.1.section_name(), "");

        // 5: Chapter 3 (merged c/s1)
        let sixth_section = section_index.index_data.get_index(5).unwrap();
        assert_eq!(sixth_section.0.to_string(), "3:1");
        assert_eq!(sixth_section.1.end_cv().to_string(), "3:2");
        assert_eq!(sixth_section.1.start_index(), 24); // starts at entry index 24 (s1 marker)
        assert_eq!(sixth_section.1.end_index(), 29); // ends at entry index 29
        assert_eq!(sixth_section.1.reason_marker(), "c/s1");
        assert_eq!(sixth_section.1.section_name(), "Psa 3 section heading");
    }

    #[test]
    #[ignore = "Need to get section index or test working properly"]
    fn test_table_of_contents() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        section_index.build(create_sample_gen_test_entries()).unwrap();

        let toc = section_index.table_of_contents();
        assert!(!toc.is_empty());

        // Check that section names are captured
        let names: Vec<&str> = toc.iter().map(|(_, name, _)| *name).collect();
        assert!(
            names
                .iter()
                .any(|n| n.contains("Creation") || n.contains("Fall") || n == &"1" || n == &"3")
        );
    }

    #[test]
    #[ignore = "Need to get section index or test working properly"]
    fn test_get_section_entries() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        section_index.build(create_sample_gen_test_entries()).unwrap();

        // Get first section
        if let Some((cv, _)) = section_index.iter().next() {
            let entries = section_index.get_section_entries(cv).unwrap();
            assert!(!entries.is_empty());
        }
    }

    #[test]
    // #[ignore = "Need to get section index or test working properly"]
    fn test_oet_rv_haggai_section_index_build() {
        // Note that OET-RV Haggai has NO section headings inside verse boundaries
        set_strict_checking_flag( true );
        let content = include_str!("../../../../Tests/DataFilesForTests/OET-RV/OET-RV_HAG.ESFM");
        let mut raw_lines = Vec::new();
        for line in content.lines() {
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line, ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);
            raw_lines.push((marker.to_string(), text.to_string()));
        }

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_line_entries = crate::processing::process_lines(raw_lines, "HAG", "OET-RV", &options);

        // println!("OET-RV HAG processed_line_entries = {}", processed_line_entries);
        // OET-RV HAG processed_line_entries = InternalBibleEntryList:
        //     0/ id = "HAG - Open English Translation…ders' Version (OET-RV) v0.1.03"
        //     1/ usfm = "3.0"
        //     2/ ide = "UTF-8"
        //     3/ rem = "ESFM v0.6 HAG"
        //     4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //     5/ headers = ""
        //     6/ h = "Haggai"
        //     7/ toc1 = "Haggai"
        //     8/ toc2 = "Haggai"
        //     9/ toc3 = "Hag."
        //     10/ mt1 = "Haggai"
        //     11/ ¬headers = ""
        //     12/ intro = ""
        //     13/ is1 = "Introduction"
        //     14/ ip = "This document contains a numbe… bless their living situation."
        //     15/ iot = "Main components of this account"
        //     16/ io1 = "God's command to rebuild the temple 1:1-15"
        //     17/ io1 = "Stories of comfort and hope 2:1-23"
        //     18/ ¬iot = ""
        //     19/ rem = "This is still a very early loo…dvance before using in public."
        //     20/ ie = ""
        //     21/ ¬intro = ""
        //     22/ chapters = ""
        //     23/ c = "1"
        //     24/ v= = "1"
        //     25/ s1 = "God's command to rebuild the temple"
        //     26/ rem = "/s1 The Lord's Command to Rebu… Command to Rebuild the Temple"
        //     27/ p = ""
        //     28/ c# = "1"
        //     29/ v = "1"
        //     30/ v~ = "In Dareyavesh's (Darius's¦3755…375591 son), telling them that" + extras
        //     31/ ¬v = "1"
        //     32/ v = "2"
        //     33/ v~ = "Commander-in-chief Yahweh says…2 Yahweh's¦375598 ≈residence.”"
        //     34/ ¬v = "2"
        //     35/ ¬p = ""
        //     36/ p = ""
        //     37/ v = "3"
        //     38/ v~ = "Then Yahweh¦375618 ≈gave this …gai¦375621 to tell the people:"
        //     39/ ¬v = "3"
        //     40/ ¬p = ""
        //     41/ m = ""
        //     42/ v = "4"
        //     43/ v~ = "Is it a time¦375625 for all of…Yahweh's temple lies in ruins?"
        //     44/ ¬v = "4"
        //     45/ v = "5"
        //     46/ v~ = "≈So¦375635 now Commander-in-ch…e what you're all going to do."
        //     47/ ¬v = "5"
        //     48/ v = "6"
        //     49/ v~ = "You've all planted a lot, ≈but…ets seem to be full of holes.”"
        //     50/ ¬v = "6"
        //     51/ ¬m = ""
        //     52/ p = ""
        //     53/ v = "7"
        //     54/ v~ = "≈So Commander-in-chief Yahweh¦…e what you're all going to do."
        //     55/ ¬v = "7"
        //     56/ v = "8"
        //     57/ v~ = "Go up into the hills¦375682 an…e,” says¦375692 Yahweh¦375693."
        //     58/ ¬v = "8"
        //     59/ ¬p = ""
        //     60/ p = ""
        //     61/ v = "9"
        //     62/ v~ = "“You ≈expected much, but¦37569…y ≈working on your own houses."
        //     63/ ¬v = "9"
        //     64/ v = "10"
        //     65/ v~ = "That's why the sky withholds t…il withholds its¦375733 crops."
        //     66/ ¬v = "10"
        //     67/ v = "11"
        //     68/ v~ = "I've¦375735 ≈summoned¦375735 a… onto ≈everything you all do.”"
        //     69/ ¬v = "11"
        //     70/ ¬p = ""
        //     71/ v= = "12"
        //     72/ s1 = "The people start rebuilding"
        //     73/ rem = "/s1 The People Obey the Lord's…mmand; Obedience to God's Call"
        //     74/ p = ""
        //     75/ v = "12"
        //     76/ v~ = "Then Shealtiyel's son Zerubave… the people ≈respected Yahweh."
        //     77/ ¬v = "12"
        //     78/ v = "13"
        //     79/ v~ = "Then¦375802 Yahweh's¦375805 me…m with¦375806 you¦375811 all.”"
        //     80/ ¬v = "13"
        //     81/ v = "14"
        //     82/ v~ = "Then¦375816 Yahweh ≈inspired S…49, Commander-in-chief Yahweh,"
        //     83/ ¬v = "14"
        //     84/ v = "15"
        //     85/ v~ = "on¦375856 the twenty-fourth da…esh the king¦375860 of Persia."
        //     86/ ¬v = "15"
        //     87/ ¬p = ""
        //     88/ ¬c = "1"
        //     89/ c = "2"
        //     90/ v= = "1"
        //     91/ s1 = "The splendour of the new temple"
        //     92/ rem = "/s1 The Future Glory of the Te…romised Glory of the New House"
        //     93/ p = ""
        //     94/ c# = "2"
        //     95/ v = "1"
        //     96/ v~ = "On the 21st of the seventh¦375… prophet¦375873 Haggai¦375872:"
        //     97/ ¬v = "1"
        //     98/ v = "2"
        //     99/ v~ = "Please ≈ask Shealtiyel's son Z…the rest of the people¦375898,"
        //     100/ ¬v = "2"
        //     101/ v = "3"
        //     102/ v~ = "“≈Are there any of you still a…g¦375919 in¦375902 comparison." + extras
        //     103/ ¬v = "3"
        //     104/ v = "4"
        //     105/ v~ = "Yahweh is telling you now, Zer… with you ≈as you work¦375944."
        //     106/ ¬v = "4"
        //     107/ v = "5"
        //     108/ v~ = "≈That's what I promised¦375955…Don't¦375965 be afraid¦375967," + extras
        //     109/ ¬v = "5"
        //     110/ v = "6"
        //     111/ v~ = "because¦375970 Commander-in-ch…9 and the dry land, once more." + extras
        //     112/ ¬v = "6"
        //     113/ v = "7"
        //     114/ v~ = "I'll shake¦375994 all the nati…mander-in-chief Yahweh¦376012."
        //     115/ ¬v = "7"
        //     116/ v = "8"
        //     117/ v~ = "Commander-in-chief Yahweh¦3760…er¦376016 belong¦376017 to me."
        //     118/ ¬v = "8"
        //     119/ v = "9"
        //     120/ v~ = "*I declare that this ≈temple w…sperity to this place¦376035.”"
        //     121/ ¬v = "9"
        //     122/ ¬p = ""
        //     123/ v= = "10"
        //     124/ s1 = "Haggai consults the priests"
        //     125/ rem = "/s1 Blessings Promised for Obe…e Prophet Consults the Priests"
        //     126/ p = ""
        //     127/ v = "10"
        //     128/ v~ = "On the 24th of the ninth¦37604… prophet¦376057 Haggai¦376056:"
        //     129/ ¬v = "10"
        //     130/ v = "11"
        //     131/ v~ = "Commander-in-chief Yahweh¦3760…Mosheh's ≈instructions¦376070."
        //     132/ ¬v = "11"
        //     133/ v = "12"
        //     134/ v~ = "‘≈If a priest took some meat¦3…r food  become¦376102 holy?’ ”"
        //     135/ ¬p = ""
        //     136/ p = ""
        //     137/ v~ = "“No, it wouldn't,” the priests¦376104 ≈replied."
        //     138/ ¬p = ""
        //     139/ ¬v = "12"
        //     140/ p = ""
        //     141/ v = "13"
        //     142/ v~ = "Then¦376108 Haggai¦376109 aske…ood, would it become unclean?”" + extras
        //     143/ ¬p = ""
        //     144/ p = ""
        //     145/ v~ = "“Yes, it would become unclean,…riests¦376121 answered¦376120."
        //     146/ ¬p = ""
        //     147/ ¬v = "13"
        //     148/ p = ""
        //     149/ v = "14"
        //     150/ v~ = "“≈That's what Yahweh¦376139 de…t transfers to your offerings."
        //     151/ rem = "/s1 The Lord Promises His Blessing"
        //     152/ ¬v = "14"
        //     153/ v = "15"
        //     154/ v~ = "So¦376151 now think back to be…id for Yahweh's¦376169 temple."
        //     155/ ¬v = "15"
        //     156/ v = "16"
        //     157/ v~ = "≈During that time, when someon…re was only enough for twenty."
        //     158/ ¬v = "16"
        //     159/ v = "17"
        //     160/ v~ = "Yahweh¦376205 declares that he…ill didn't¦376199 turn to him."
        //     161/ ¬v = "17"
        //     162/ v = "18"
        //     163/ v~ = "Think back to the time from wh… month¦376219). Consider that."
        //     164/ ¬v = "18"
        //     165/ v = "19"
        //     166/ v~ = "Is any grain left in¦376234 th…bless you from today onwards.”"
        //     167/ ¬v = "19"
        //     168/ ¬p = ""
        //     169/ v= = "20"
        //     170/ s1 = "God's promise to Zerubavel"
        //     171/ rem = "/s1 The Lord's Promise to Zeru…ubbabel the Lord's Signet Ring"
        //     172/ p = ""
        //     173/ v = "20"
        //     174/ v~ = "Then Yahweh¦376254 gave a seco…gai¦376259 on¦376260 the 24th:"
        //     175/ ¬v = "20"
        //     176/ v = "21"
        //     177/ v~ = "Tell Zerubavel, the governor¦3…s¦376277 and the earth¦376280."
        //     178/ ¬v = "21"
        //     179/ v = "22"
        //     180/ v~ = "I'll overthrow the thrones¦376… ≈will kill¦376285 each other."
        //     181/ ¬v = "22"
        //     182/ v = "23"
        //     183/ v~ = "Commander-in-chief Yahweh decl…6316 he's been chosen¦376319.”"
        //     184/ ¬v = "23"
        //     185/ ¬p = ""
        //     186/ ¬c = "2"
        //     187/ ¬chapters = ""

        let mut section_index = InternalBibleBookSectionIndex::new("OET-RV", "HAG");
        section_index.build(processed_line_entries).unwrap();

        // It should give the following seven entries:
        //    0 -1:0 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:12 ix=0–12 (cnt=13) Headers='HAG'
        //    1 -1:13 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:22 ix=13–22 (cnt=10) is1='Introduction'
        //    2 1:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:11 ix=24–69 (cnt=46) s1='God's command to rebuild the temple'
        //    3 1:12 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:15 ix=70–87 (cnt=18) s1='The people start rebuilding'
        //    4 2:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:9 ix=88–119 (cnt=32) s1='The splendour of the new temple'
        //    5 2:10 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:19 ix=120–164 (cnt=45) s1='Haggai consults the priests'
        //    6 2:20 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:23 ix=165–182 (cnt=18) s1='God's promise to Zerubavel'

        assert_eq!(section_index.len(), 7);
        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "is1", "s1/c", "s1", "s1/c", "s1", "s1"]);

        // 0 -1:0 Headers='HAG'
        let (cv0, entry0) = section_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:11");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 11);
        assert_eq!(entry0.reason_marker(), "Headers");
        assert_eq!(entry0.section_name(), "HAG");

        // 1 -1:13 is1='Introduction'
        let (cv1, entry1) = section_index.index_data.get_index(1).unwrap();
        assert_eq!(cv1.to_string(), "-1:13");
        assert_eq!(entry1.end_cv().to_string(), "-1:21");
        assert_eq!(entry1.start_index(), 13);
        assert_eq!(entry1.end_index(), 21);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:1 s1='God\'s command to rebuild the temple'
        let (cv2, entry2) = section_index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:1");
        assert_eq!(entry2.end_cv().to_string(), "1:11");
        assert_eq!(entry2.start_index(), 23);
        assert_eq!(entry2.end_index(), 70);
        assert_eq!(entry2.reason_marker(), "s1/c");
        assert_eq!(entry2.section_name(), "God's command to rebuild the temple");

        // 3 1:11 s1='The people start rebuilding'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:12");
        assert_eq!(entry3.end_cv().to_string(), "1:15");
        assert_eq!(entry3.start_index(), 71);
        assert_eq!(entry3.end_index(), 88);
        assert_eq!(entry3.reason_marker(), "s1");
        assert_eq!(entry3.section_name(), "The people start rebuilding");

        // 4 2:1 s1='The splendour of the new temple'
        let (cv4, entry4) = section_index.index_data.get_index(4).unwrap();
        assert_eq!(cv4.to_string(), "2:1");
        assert_eq!(entry4.end_cv().to_string(), "2:9");
        assert_eq!(entry4.start_index(), 89);
        assert_eq!(entry4.end_index(), 122);
        assert_eq!(entry4.reason_marker(), "s1/c");
        assert_eq!(entry4.section_name(), "The splendour of the new temple");

        // 5 2:9 s1='Haggai consults the priests'
        let (cv5, entry5) = section_index.index_data.get_index(5).unwrap();
        assert_eq!(cv5.to_string(), "2:10");
        assert_eq!(entry5.end_cv().to_string(), "2:19");
        assert_eq!(entry5.start_index(), 123);
        assert_eq!(entry5.end_index(), 168);
        assert_eq!(entry5.reason_marker(), "s1");
        assert_eq!(entry5.section_name(), "Haggai consults the priests");

        // 6 2:19 s1='God\'s promise to Zerubavel'
        let (cv6, entry6) = section_index.index_data.get_index(6).unwrap();
        assert_eq!(cv6.to_string(), "2:20");
        assert_eq!(entry6.end_cv().to_string(), "2:23");
        assert_eq!(entry6.start_index(), 169);
        assert_eq!(entry6.end_index(), 186); // Don't include the ¬chapters
        assert_eq!(entry6.reason_marker(), "s1");
        assert_eq!(entry6.section_name(), "God's promise to Zerubavel");
    }

    #[test]
    #[ignore = "Need to get section index or test working properly"]
    fn test_oet_rv_malachi_section_index_build() {
        // Note that OET-RV Malachi has 3 section headings inside verse boundaries
        set_strict_checking_flag( true );
        let content = include_str!("../../../../Tests/DataFilesForTests/OET-RV/OET-RV_MAL.ESFM");
        let mut raw_lines = Vec::new();
        for line in content.lines() {
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line, ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);
            raw_lines.push((marker.to_string(), text.to_string()));
        }

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_line_entries = crate::processing::process_lines(raw_lines, "MAL", "OET-RV", &options);

        // println!("OET-RV MAL processed_line_entries = {}", processed_line_entries);
        // OET-RV MAL processed_line_entries = InternalBibleEntryList:
        //     0/ id = "MAL - Open English Translation…ders' Version (OET-RV) v0.1.05"
        //     1/ usfm = "3.0"
        //     2/ ide = "UTF-8"
        //     3/ rem = "ESFM v0.6 MAL"
        //     4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //     5/ headers = ""
        //     6/ h = "Malaki"
        //     7/ toc1 = "Malaki"
        //     8/ toc2 = "Malaki"
        //     9/ toc3 = "Mal."
        //     10/ mt1 = "Malaki"
        //     11/ mt2 = "(Malachi)"
        //     12/ ¬headers = ""
        //     13/ intro = ""
        //     14/ is1 = "Introduction"
        //     15/ ip = "This document records some of … and to restore his agreement."
        //     16/ iot = "Main components of this account"
        //     17/ io1 = "The sins of the Israelis 1:1–2:16"
        //     18/ io1 = "God's judgement and mercy 2:17–4:6"
        //     19/ ¬iot = ""
        //     20/ rem = "This is still a very early loo…dvance before using in public."
        //     21/ ie = ""
        //     22/ ¬intro = ""
        //     23/ chapters = ""
        //     24/ c = "1"
        //     25/ p = ""
        //     26/ c# = "1"
        //     27/ v = "1"
        //     28/ v~ = "This is a message¦380162 that …ve to Malaki for the Israelis:"
        //     29/ ¬v = "1"
        //     30/ ¬p = ""
        //     31/ v= = "2"
        //     32/ s1 = "Yahweh's love for the Israelis"
        //     33/ rem = "/s1 The Lord's Love for Israel…om; The Lord's Love for Israel"
        //     34/ p = ""
        //     35/ v = "2"
        //     36/ v~ = "“I have loved you all,” says Y…e you shown your love for us?”"
        //     37/ ¬p = ""
        //     38/ p = ""
        //     39/ v~ = "“Wasn't Esaw¦380181 Yacob's¦38…. “Yet I've¦380171 loved Yacob" + extras
        //     40/ ¬v = "2"
        //     41/ v = "3"
        //     42/ v~ = "and ≈rejected Esaw. I've¦38019…2 to the wild jackals¦380203.”"
        //     43/ ¬v = "3"
        //     44/ ¬p = ""
        //     45/ p = ""
        //     46/ v = "4"
        //     47/ v~ = "If Esaw's descendants in Edom¦…is forever¦380233 angry with.’"
        //     48/ ¬v = "4"
        //     49/ ¬p = ""
        //     50/ p = ""
        //     51/ v = "5"
        //     52/ v~ = "Your own eyes¦380235 will see¦…el's¦380243 borders¦380242.’ ”"
        //     53/ ¬v = "5"
        //     54/ ¬p = ""
        //     55/ v= = "6"
        //     56/ s1 = "Second-class sacrifices"
        //     57/ rem = "/s1 The Lord Reprimands the Pr…; Corruption of the Priesthood"
        //     58/ p = ""
        //     59/ v = "6"
        //     60/ v~ = "“A son honours his father, and…ts¦380267 who despise my name."
        //     61/ ¬p = ""
        //     62/ p = ""
        //     63/ v~ = "“But¦380248 you say, ‘How have we despised your name?’"
        //     64/ ¬v = "6"
        //     65/ v = "7"
        //     66/ v~ = "By offering polluted food on¦3…0287 can just be disrespected."
        //     67/ ¬v = "7"
        //     68/ v = "8"
        //     69/ v~ = "Don't¦380297 you think it's wr…ommander¦380317 Yahweh¦380316." + extras
        //     70/ ¬v = "8"
        //     71/ ¬p = ""
        //     72/ p = ""
        //     73/ v = "9"
        //     74/ v~ = "≈So¦380319 now bring you reque…inging second-class offerings?"
        //     75/ ¬v = "9"
        //     76/ ¬p = ""
        //     77/ p = ""
        //     78/ v = "10"
        //     79/ v~ = "“Yeah, if only there¦380349 wa…380357 ≈that you all bring me."
        //     80/ ¬v = "10"
        //     81/ v = "11"
        //     82/ v~ = "People in other countries from…ommander¦380388 Yahweh¦380387."
        //     83/ ¬v = "11"
        //     84/ v = "12"
        //     85/ v~ = "“But¦380392 you all are dishon… treated with¦380393 contempt."
        //     86/ ¬v = "12"
        //     87/ v = "13"
        //     88/ v~ = "You all also say, ‘How tiresom… those from you?” says Yahweh."
        //     89/ ¬v = "13"
        //     90/ v = "14"
        //     91/ v~ = "“May the cheats be cursed¦3804…ted among the nations¦380447.”"
        //     92/ ¬v = "14"
        //     93/ ¬p = ""
        //     94/ ¬c = "1"
        //     95/ c = "2"
        //     96/ v= = "1"
        //     97/ s1 = "A warning for the priests"
        //     98/ rem = "/s1 Admonition for the Priests; A Warning for the Priests"
        //     99/ p = ""
        //     100/ c# = "2"
        //     101/ v = "1"
        //     102/ v~ = "Now¦380453 you priests¦380453,…mand¦380451 is for all of you:"
        //     103/ ¬v = "1"
        //     104/ v = "2"
        //     105/ v~ = "Army-commander¦380471 Yahweh¦3…nternalising ‘my instructions."
        //     106/ ¬v = "2"
        //     107/ v = "3"
        //     108/ v~ = "Listen, I'm about¦380491 to re… be taken¦380503 away with it."
        //     109/ ¬v = "3"
        //     110/ v = "4"
        //     111/ v~ = "That's so you'll all know¦3805…ommander¦380521 Yahweh¦380520." + extras
        //     112/ ¬v = "4"
        //     113/ ¬p = ""
        //     114/ p = ""
        //     115/ v = "5"
        //     116/ v~ = "“My agreement with @your ances… and ≈honoured my name¦380535." + extras
        //     117/ ¬v = "5"
        //     118/ v = "6"
        //     119/ v~ = "≈They taught the people what w…any people to stop disobeying."
        //     120/ ¬v = "6"
        //     121/ v = "7"
        //     122/ v~ = "≈Yes, priests¦380559 should pa…eh's¦380568 messengers¦380567."
        //     123/ ¬v = "7"
        //     124/ ¬p = ""
        //     125/ p = ""
        //     126/ v = "8"
        //     127/ v~ = "But¦380573 you all have turned…ommander¦380586 Yahweh¦380585."
        //     128/ ¬v = "8"
        //     129/ v = "9"
        //     130/ v~ = "“So¦380588 that's why I've¦380…07 matters¦380598 of the law.”"
        //     131/ ¬v = "9"
        //     132/ ¬p = ""
        //     133/ v= = "10"
        //     134/ s1 = "The people have been unfaithful"
        //     135/ rem = "/s1 A Call to Faithfulness; Th…People's Unfaithfulness to God"
        //     136/ p = ""
        //     137/ v = "10"
        //     138/ v~ = "Don't¦380610 we all have one f…1 our¦380613 ancestors¦380624?"
        //     139/ ¬v = "10"
        //     140/ v = "11"
        //     141/ v~ = "Our nation of Yehudah¦380627 (… women who worship pagan gods."
        //     142/ ¬v = "11"
        //     143/ v = "12"
        //     144/ v~ = "May Yahweh, the one who is awa… army-commander¦380658 Yahweh."
        //     145/ ¬v = "12"
        //     146/ ¬p = ""
        //     147/ p = ""
        //     148/ v = "13"
        //     149/ v~ = "Secondly¦380666, you cover¦380…678 what you all bring to him."
        //     150/ ¬v = "13"
        //     151/ v = "14"
        //     152/ v~ = "≈So¦380682 you ≈ask, “Why not?… and¦380682 despite your vows."
        //     153/ ¬v = "14"
        //     154/ v = "15"
        //     155/ v~ = "Didn't @Yahweh make you and yo…u married when you were young."
        //     156/ ¬v = "15"
        //     157/ ¬p = ""
        //     158/ p = ""
        //     159/ v = "16"
        //     160/ v~ = "“Indeed, I hate divorce,” says…d don't¦380743 be unfaithful.”"
        //     161/ ¬v = "16"
        //     162/ ¬p = ""
        //     163/ v= = "17"
        //     164/ s1 = "Judgement day is coming"
        //     165/ rem = "/s1 The Day of Judgment; The Day of Judgment Is Near"
        //     166/ p = ""
        //     167/ v = "17"
        //     168/ v~ = "You've all wearied Yahweh with…god¦380767 of justice¦380768?”"
        //     169/ ¬v = "17"
        //     170/ ¬p = ""
        //     171/ ¬c = "2"
        //     172/ c = "3"
        //     173/ rem = "/s1 The Coming Day of Judgment; The Coming Messenger"
        //     174/ p = ""
        //     175/ c# = "3"
        //     176/ v = "1"
        //     177/ v~ = "“Listen, I'm about to send my …ommander¦380799 Yahweh¦380798." + extras
        //     178/ ¬v = "1"
        //     179/ v = "2"
        //     180/ v~ = "≈But¦380801 who could survive …e the cleaners' powerful soap?" + extras
        //     181/ ¬v = "2"
        //     182/ v = "3"
        //     183/ v~ = "@Yahweh will act as a refiner … to *him that are ≈acceptable."
        //     184/ ¬v = "3"
        //     185/ v = "4"
        //     186/ v~ = "After that, the offerings¦3808…d as in previous years¦380845."
        //     187/ ¬v = "4"
        //     188/ ¬p = ""
        //     189/ p = ""
        //     190/ v = "5"
        //     191/ v~ = "This is what army-commander¦38…hose who ≈refuse to honour me."
        //     192/ ¬v = "5"
        //     193/ ¬p = ""
        //     194/ v= = "6"
        //     195/ s1 = "Giving a tenth"
        //     196/ rem = "/s1 The Payment of Tithes; Robbing God; A Call to Repentance"
        //     197/ p = ""
        //     198/ v = "6"
        //     199/ v~ = "“I am Yahweh¦380876 and¦380879…380882 haven't been destroyed."
        //     200/ ¬v = "6"
        //     201/ v = "7"
        //     202/ v~ = "Ever since¦380886 the time¦380… can we¦380901 return to you?’"
        //     203/ rem = "/s1 Don't rob God"
        //     204/ ¬v = "7"
        //     205/ v = "8"
        //     206/ v~ = "Can a human rob God¦380905? Ye… plus¦380910 offerings¦380914."
        //     207/ ¬v = "8"
        //     208/ v = "9"
        //     209/ v~ = "You're¦380919 all cursed¦38091…e¦380923 nation¦380922 of you."
        //     210/ ¬v = "9"
        //     211/ v = "10"
        //     212/ v~ = "Bring¦380925 the full tenth in…owing blessing¦380954 for you." + extras
        //     213/ ¬v = "10"
        //     214/ v = "11"
        //     215/ v~ = "I'll¦380968 rebuke¦380961 the …ommander¦380980 Yahweh¦380979." + extras
        //     216/ ¬v = "11"
        //     217/ v = "12"
        //     218/ v~ = "“Then¦380983 all the other cou…ommander¦380995 Yahweh¦380994."
        //     219/ ¬v = "12"
        //     220/ ¬p = ""
        //     221/ v= = "13"
        //     222/ s1 = "God promises mercy for some"
        //     223/ rem = "/s1 The righteous triumphant; God's Promise of Mercy"
        //     224/ p = ""
        //     225/ v = "13"
        //     226/ v~ = "“Your words¦381000 against me … among ourselves against you?’"
        //     227/ ¬v = "13"
        //     228/ v = "14"
        //     229/ v~ = "You've all said¦381009, ‘It's …ommander¦381024 Yahweh¦381023?"
        //     230/ ¬v = "14"
        //     231/ v = "15"
        //     232/ v~ = "≈It seems that arrogant¦381029…et nothing happens to them.’ ”"
        //     233/ rem = "/s1 The Reward of the Faithful; The Lord's Promise of Mercy"
        //     234/ ¬v = "15"
        //     235/ ¬p = ""
        //     236/ p = ""
        //     237/ v = "16"
        //     238/ v~ = "Then those who ≈still respecte…noured his¦381054 name¦381058."
        //     239/ ¬v = "16"
        //     240/ v = "17"
        //     241/ v~ = "“They'll be mine,” says¦381062…punish his son who ≈obeys him."
        //     242/ ¬v = "17"
        //     243/ v = "18"
        //     244/ v~ = "Then¦381081 once again¦381081 …8 and #those who don't¦381090."
        //     245/ ¬v = "18"
        //     246/ ¬p = ""
        //     247/ ¬c = "3"
        //     248/ c = "4"
        //     249/ v= = "1"
        //     250/ s1 = "Be ready for future judgement"
        //     251/ rem = "/s1 The Day of the Lord; The C…ing; The Great Day of the Lord"
        //     252/ p = ""
        //     253/ c# = "4"
        //     254/ v = "1"
        //     255/ v~ = "“≈Yes, listen, the day that bu…leaving any roots or branches."
        //     256/ ¬v = "1"
        //     257/ v = "2"
        //     258/ v~ = "But for you who respect my nam…calves let out of their stall,"
        //     259/ ¬v = "2"
        //     260/ v = "3"
        //     261/ v~ = "and you'll all trample down th…,” says army-commander Yahweh."
        //     262/ ¬v = "3"
        //     263/ ¬p = ""
        //     264/ p = ""
        //     265/ v = "4"
        //     266/ v~ = "“≈Be sure to obey the law that…—the statutes and the rulings."
        //     267/ ¬v = "4"
        //     268/ ¬p = ""
        //     269/ p = ""
        //     270/ v = "5"
        //     271/ v~ = "Listen, I'll send the prophet … fearful day of *my judgement." + extras
        //     272/ ¬v = "5"
        //     273/ v = "6"
        //     274/ v~ = "He'll ≈restore harmony between…th with complete destruction.”"
        //     275/ ¬v = "6"
        //     276/ ¬p = ""
        //     277/ ¬c = "4"
        //     278/ ¬chapters = ""

        let mut section_index = InternalBibleBookSectionIndex::new("OET-RV", "MAL");
        section_index.build(processed_line_entries.clone()).unwrap();
        
        // It should give the following eleven entries:
        //    0 -1:0 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:12 ix=0–13 (cnt=14) Headers='MAL'
        //    1 -1:13 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:22 ix=14–23 (cnt=9) is1='Introduction'
        //    2 1:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:1 ix=24–30 (cnt=7) c='Malaki 1'
        //    3 1:2 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:5 ix=32–87 (cnt=18) s1='Yahweh's love for the Israelis'
        //  The rest are wrong
        //    4 2:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:9 ix=88–119 (cnt=32) s1='The splendour of the new temple'
        //    5 2:10 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:19 ix=120–164 (cnt=45) s1='Haggai consults the priests'
        //    6 2:20 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:23 ix=165–182 (cnt=18) s1='God's promise to Zerubavel'

        assert_eq!(section_index.len(), 11);
        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "is1", "s1", "s1", "s1/c", "s1", "s1", "s1", "s1", "s1/c"]);

        // 0 -1:0 Headers='MAL'
        let (cv0, entry0) = section_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:13");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 13);
        assert_eq!(entry0.reason_marker(), "Headers");
        assert_eq!(entry0.section_name(), "MAL");

        // 1 -1:13 is1='Introduction'
        let (cv1, entry1) = section_index.index_data.get_index(1).unwrap();
        assert_eq!(cv1.to_string(), "-1:14");
        assert_eq!(entry1.end_cv().to_string(), "-1:23");
        assert_eq!(entry1.start_index(), 14);
        assert_eq!(entry1.end_index(), 23);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:1 chapter one start
        let (cv2, entry2) = section_index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:1");
        assert_eq!(entry2.end_cv().to_string(), "1:1");
        assert_eq!(entry2.start_index(), 24); // c
        assert_eq!(entry2.end_index(), 30); // ¬p
        assert_eq!(entry2.reason_marker(), "c");
        assert_eq!(entry2.section_name(), "Malaki 1");

        // 3 1:2 s1='Yahweh's love for the Israelis'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:2");
        assert_eq!(entry3.end_cv().to_string(), "1:5");
        assert_eq!(entry3.start_index(), 31); // v=
        assert_eq!(entry3.end_index(), 60);
        assert_eq!(entry3.reason_marker(), "s1");
        assert_eq!(entry3.section_name(), "Yahweh's love for the Israelis");

        // // 4 2:1 s1='The splendour of the new temple'
        // let (cv4, entry4) = index.index_data.get_index(4).unwrap();
        // assert_eq!(cv4.to_string(), "2:1");
        // assert_eq!(entry4.end_cv().to_string(), "2:9");
        // assert_eq!(entry4.start_index(), 90);
        // assert_eq!(entry4.end_index(), 123);
        // assert_eq!(entry4.reason_marker(), "s1");
        // assert_eq!(entry4.section_name(), "The splendour of the new temple");

        // // 5 2:9 s1='Haggai consults the priests'
        // let (cv5, entry5) = index.index_data.get_index(5).unwrap();
        // assert_eq!(cv5.to_string(), "2:10");
        // assert_eq!(entry5.end_cv().to_string(), "2:19");
        // assert_eq!(entry5.start_index(), 123);
        // assert_eq!(entry5.end_index(), 169);
        // assert_eq!(entry5.reason_marker(), "s1");
        // assert_eq!(entry5.section_name(), "Haggai consults the priests");

        // // 6 2:19 s1='God\'s promise to Zerubavel'
        // let (cv6, entry6) = index.index_data.get_index(6).unwrap();
        // assert_eq!(cv6.to_string(), "2:20");
        // assert_eq!(entry6.end_cv().to_string(), "2:23");
        // assert_eq!(entry6.start_index(), 169);
        // assert_eq!(entry6.end_index(), 187);
        // assert_eq!(entry6.reason_marker(), "s1");
        // assert_eq!(entry6.section_name(), "God's promise to Zerubavel");
    }
}
