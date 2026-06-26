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
                            if special_verse_num.ends_with("b") {
                                assert!(special_verse_num.to_string().starts_with(finishing_verse_num_str.as_str()));
                                finishing_verse_num_str += "a";
                            }
                            let (cv, entry) = this_pending_section.into_closed(
                                last_chapter_num_str.as_str(),
                                finishing_verse_num_str.as_str(),
                                end_idx,
                                context.clone());
                            println!("    About to close section at {}:{} with current_chapter_num_str={} current_verse_num_str={} last_verse_num_str={}",
                                        last_chapter_num_str, finishing_verse_num_str, current_chapter_num_str, current_verse_num_str, last_verse_num_str);
                            assert_ne!(finishing_verse_num_str, "0", "Don't want to finish the previous section at {}:{}", last_chapter_num_str, finishing_verse_num_str);
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

        // The problem here is that we don't know if the following 'v=' has a 'b', e.g., '3b', in which case, this should be '3a'
        //  so might be easiest to just ignore this
        // else if ["¬s1","¬ms1","¬is1"].contains(&marker) { // We've just finished a section
        //     assert!(pending.is_some());
        //     if let Some(previously_pending_section) = pending.take() {
        //         if have_strict_checking_flag() || cfg!(debug_assertions) { println!("  Adding close '{}' section", marker); }
        //         let (cv, entry) = previously_pending_section.into_closed(
        //             current_chapter_num_str.as_str(),
        //             current_verse_num_str.as_str(),
        //             i as u16,
        //             context.clone(),
        //         );
        //     self.index_data.insert(cv, entry);
        //     }
        // }
        
        else if current_chapter_num_str == "-1" { // We're still in the pre-chapter sections
                if marker == "¬headers" {
                    if let Some(previously_pending_section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u16).saturating_sub(1);
                        let (cv, entry) = previously_pending_section.into_closed(
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
                    if let Some(previous_pending_section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u16).saturating_sub(1);
                        if i as u16 > previous_pending_section.start_index {
                            let (cv, current_pending_section) = previous_pending_section.into_closed(
                                last_chapter_num_str.as_str(),
                                last_verse_num_str.as_str(),
                                (i - 1) as u16,
                                context.clone(),
                            );
                            if have_strict_checking_flag() || cfg!(debug_assertions) {
                                assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}");
                                assert_eq!(cv.verse().parse::<u16>(), Ok(current_pending_section.start_index));
                                assert_eq!(last_verse_num_str.parse::<u16>(), Ok(current_pending_section.end_index),
                                            "build {} {} section index loop {} with {} section index entries already, failed with {} {}\nfrom {}",
                                        self.work_name(), self.bos_book_code(), i, self.index_data.len(),
                                        last_verse_num_str, current_pending_section.end_index, self.line_entries);
                            }
                            self.index_data.insert(cv, current_pending_section);
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
                    if let Some(previously_pending_section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u16).saturating_sub(1);
                        let (cv, entry) = previously_pending_section.into_closed(
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
            
            // End of loop
            // Record current CV for the NEXT entry to use as its "previous" CV
            // But don't update it for markers that change the CV themselves,
            // so that if a section ends with such a marker, it uses the previous CV for endCV.
            if marker != "v" && marker != "v=" && marker != "c" && !is_end_marker(marker) {
                last_chapter_num_str = current_chapter_num_str.clone();
                last_verse_num_str = current_verse_num_str.clone();
            }
            last_marker = marker;
        }
        if have_strict_checking_flag() || cfg!(debug_assertions) { println!("Section heading loop finished with {} entries and pending={:?}", self.index_data.len(), pending); }

        // Close final section
        if let Some(previously_pending_section) = pending.as_mut().filter(|s| s.start_cv.is_none()) {
            previously_pending_section.start_cv = Some(ChapterVerse::new(
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
        if let Some(previously_pending_section) = pending {
            if have_strict_checking_flag() || cfg!(debug_assertions) { println!("  Adding final section"); }
            let (cv, entry) = previously_pending_section.into_closed(
                current_chapter_num_str.as_str(),
                current_verse_num_str.as_str(),
                end_idx,
                context,
            );
            if self.index_data.contains_key(&cv) { // This can happen for alternative endings to Mark
                if have_strict_checking_flag() || cfg!(debug_assertions) {
                    assert_eq!(self.bos_book_code(), "MRK", "{} {} section index is losing a key: {}", self.work_name(), self.bos_book_code(), cv);
                }
                self.index_data.insert(ChapterVerse::new(cv.chapter(), format!("{}n", cv.verse())), entry); // Append another b suffix
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
        for (cv, index_entry) in &self.index_data {
            if cv.chapter()=="-1" && cv.verse()=="0" { have_m1_0 = true; }
            if cv.chapter()=="1" && cv.verse()=="0" { have_1_0 = true; }
            if cv.chapter()=="1" && (cv.verse()=="1" || cv.verse_int().unwrap()==1) { have_1_1 = true; } // Could be a verse bridge, e.g., '1-2'
            assert!(!cv.chapter().is_empty() && (cv.chapter().chars().all(|c| c.is_ascii_digit()) || cv.chapter() == "-1"),
                "{} {} chapter should be a non-empty string of digits or '-1': found '{}' from {}",
                self.work_name, self.bos_book_code, cv.chapter(), cv);
            assert!(!cv.verse().is_empty() && cv.verse().chars().all(|c| c.is_ascii_digit() || c=='-' || c=='b'),
                "{} {} verse should be a non-empty string of digits (or a verse bridge): found '{}' from {}",
                self.work_name, self.bos_book_code, cv.verse(), cv);

            if index_entry.start_index() < last_end {
                issues.push(format!("{} {} {}: entry_index {} < previous end {}",
                    self.work_name(), self.bos_book_code(), cv, index_entry.start_index(), last_end));
            }

            if cv.chapter() == "-1"  {
                assert_eq!(cv.verse().parse::<usize>().unwrap(), index_entry.start_index(),
                    "Unexpected {} {} start index of {} for {} entry: {}",
                    self.work_name, self.bos_book_code, index_entry.start_index(), cv, index_entry);
                assert_eq!(index_entry.end_verse_num_str().parse::<usize>(), Ok(index_entry.end_index()),
                    "Unexpected {} {} end index of {} for {} entry: {}\nfrom {}",
                    self.work_name, self.bos_book_code, index_entry.end_index(), cv, index_entry, line_entries);

            } else { // We're now into the chapters

                // for processed_line_entry in self.entries.slice(entry.start_index(), entry.end_index()) {
                //     if processed_line_entry.marker() == "v" || processed_line_entry.marker() == "¬v" {
                //         assert!(processed_line_entry.clean_text().starts_with(cv.verse().to_string().as_str()), "Validating {} {} CV index entry for {} found unexpected verse marker with text {}='{}'\n\n{}:{} {}\n\n{} {}\n\n{}:{} {}",
                //             self.work_name(), self.bos_book_code(), cv, processed_line_entry.marker(),processed_line_entry.clean_text(),
                //             cv.chapter(), cv.verse_int().unwrap_or(1)-1, self.format_section_result(self.get_section_entries(&ChapterVerse::new(cv.chapter(), (cv.verse_int().unwrap_or(1) - 1).to_string().as_str()))),
                //             cv, self.format_section_result(self.get_section_entries(cv)),
                //             cv.chapter(), cv.verse_int().unwrap_or(1)+1, self.format_section_result(self.get_section_entries(&ChapterVerse::new(cv.chapter(), (cv.verse_int().unwrap_or(1) + 1).to_string().as_str()))));
                //         }
                //     }
                
                // Check that the segment finishes with an end marker
                let final_marker_in_entry = self.line_entries.get(index_entry.start_index() + index_entry.entry_count() as usize - 1).map(|e| e.marker()).unwrap_or("N/A");
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
                last_end = index_entry.end_index();
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
    fn test_normal_plus_midverse_section_headings() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "TST")); // 0
        entries.push(InternalBibleEntry::simple("headers", "")); // 1
        entries.push(InternalBibleEntry::simple("h", "Test2")); // 2
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 3

        entries.push(InternalBibleEntry::simple("chapters", "")); // 4
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("v", "1")); // 6
        entries.push(InternalBibleEntry::simple("v~", "Verse one text")); // 7
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 8
        entries.push(InternalBibleEntry::simple("v=", "2")); // 9
        entries.push(InternalBibleEntry::simple("s1", "First section heading")); // 10
        entries.push(InternalBibleEntry::simple("p", "")); // 11
        entries.push(InternalBibleEntry::simple("v", "2")); // 12
        entries.push(InternalBibleEntry::simple("v~", "Verse two text")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 14
        entries.push(InternalBibleEntry::simple("v", "3")); // 15
        entries.push(InternalBibleEntry::simple("v~", "Verse three text")); // 16
        entries.push(InternalBibleEntry::simple("¬p", "")); // 17
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 18
        entries.push(InternalBibleEntry::simple("v=", "3b")); // 19
        entries.push(InternalBibleEntry::simple("s1", "Second section heading")); // 20
        entries.push(InternalBibleEntry::simple("p", "")); // 21
        entries.push(InternalBibleEntry::simple("v~", "More verse three text")); // 22
        entries.push(InternalBibleEntry::simple("¬v", "3")); // 23
        entries.push(InternalBibleEntry::simple("¬p", "")); // 24
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 25
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 26
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 27

        let mut section_index = InternalBibleBookSectionIndex::new("YSV", "TST");
        section_index.build(entries).unwrap();

        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "c", "s1", "s1"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1");
        assert_eq!(second_section.1.end_cv().to_string(), "1:1");
        assert_eq!(second_section.1.start_index(), 5);
        assert_eq!(second_section.1.end_index(), 8);

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:2");
        assert_eq!(third_section.1.end_cv().to_string(), "1:3a");
        assert_eq!(third_section.1.start_index(), 9);
        assert_eq!(third_section.1.end_index(), 18);

        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:3b");
        assert_eq!(fourth_section.1.end_cv().to_string(), "1:3");
        assert_eq!(fourth_section.1.start_index(), 19);
        assert_eq!(fourth_section.1.end_index(), 26);
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

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:3"); // starts at 1:3
        assert_eq!(third_section.1.end_cv().to_string(), "1:4a"); // ends at 1:4a
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
        entries.push(InternalBibleEntry::simple("headers", "")); // 2
        entries.push(InternalBibleEntry::simple("mt1", "Psalms")); // 3
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 4

        // Section 2 (Intro)
        entries.push(InternalBibleEntry::simple("intro", "")); // 5
        entries.push(InternalBibleEntry::simple("is1", "Introduction to Psalms")); // 6
        entries.push(InternalBibleEntry::simple("ip", "An introductory paragraph.")); // 7
        entries.push(InternalBibleEntry::simple("ie", "")); // 8
        entries.push(InternalBibleEntry::simple("¬intro", "")); // 9

        // Section 3 Chapter begins WITHOUT a section heading (should be absorbed into the first section)
        entries.push(InternalBibleEntry::simple("chapters", "")); // 10
        entries.push(InternalBibleEntry::simple("c", "1")); // 11
        entries.push(InternalBibleEntry::simple("p", "")); // 12
        entries.push(InternalBibleEntry::simple("v", "1")); // 13
        entries.push(InternalBibleEntry::simple("v~", "First verse of Psalms...")); // 14
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 15
        entries.push(InternalBibleEntry::simple("v", "2")); // 16
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 1...")); // 17
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 18
        entries.push(InternalBibleEntry::simple("¬p", "")); // 19

        // Section 4
        entries.push(InternalBibleEntry::simple("v=", "3")); // 20
        entries.push(InternalBibleEntry::simple("s1", "First section heading mid-chapter")); // 21
        entries.push(InternalBibleEntry::simple("p", "")); // 22
        entries.push(InternalBibleEntry::simple("v", "3")); // 23
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of Psalm 1...")); // 24
        entries.push(InternalBibleEntry::simple("¬v", "3")); // 25
        entries.push(InternalBibleEntry::simple("v", "4")); // 26
        entries.push(InternalBibleEntry::simple("v~", "Verse 4 of Psalm 1...")); // 27
        entries.push(InternalBibleEntry::simple("¬v", "4")); // 28
        entries.push(InternalBibleEntry::simple("¬p", "")); // 29
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 30

        // Section 5 - chapter change without a new section heading should start a new section
        entries.push(InternalBibleEntry::simple("c", "2")); // 31
        entries.push(InternalBibleEntry::simple("p", "")); // 32
        entries.push(InternalBibleEntry::simple("v", "1")); // 33
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of Psalm 2...")); // 34
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 35
        entries.push(InternalBibleEntry::simple("v", "2")); // 36
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 2...")); // 37
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 38
        entries.push(InternalBibleEntry::simple("¬p", "")); // 39

        // Section 6 - chapter change with a new section heading should start a new section
        entries.push(InternalBibleEntry::simple("c", "3")); // 40
        entries.push(InternalBibleEntry::simple("v=", "1")); // 41
        entries.push(InternalBibleEntry::simple("s1", "Psa 3 section heading")); // 42
        entries.push(InternalBibleEntry::simple("q1", "")); // 43
        entries.push(InternalBibleEntry::simple("v", "1")); // 44
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of Psalm 3...")); // 45
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 46
        entries.push(InternalBibleEntry::simple("v", "2")); // 47
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 3...")); // 48
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 49
        entries.push(InternalBibleEntry::simple("¬q1", "")); // 50
        entries.push(InternalBibleEntry::simple("¬c", "3")); // 51
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 52

        entries
    }

    #[test]
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
        assert_eq!(first_section.1.end_cv().to_string(), "-1:4");
        assert_eq!(first_section.1.start_index(), 0); // starts at entry index 0
        assert_eq!(first_section.1.end_index(), 4); // ends at
        assert_eq!(first_section.1.reason_marker(), "Headers");
        assert_eq!(first_section.1.section_name(), "PSA");
        assert_eq!(first_section.1.context(), Vec::<CompactString>::new());

        // 1: Intro
        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "-1:6");
        assert_eq!(second_section.1.end_cv().to_string(), "-1:9");
        assert_eq!(second_section.1.start_index(), 6); // starts at 'is1'
        assert_eq!(second_section.1.end_index(), 9); // ends at '¬intro'
        assert_eq!(second_section.1.reason_marker(), "is1");
        assert_eq!(second_section.1.section_name(), "Introduction to Psalms");
        assert_eq!(second_section.1.context(), Vec::<CompactString>::new());

        // 2: Chapter 1
        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:1");
        assert_eq!(third_section.1.end_cv().to_string(), "1:2");
        assert_eq!(third_section.1.start_index(), 11); // starts at 'c'
        assert_eq!(third_section.1.end_index(), 19); // ends at '¬p'
        assert_eq!(third_section.1.reason_marker(), "c");
        assert_eq!(third_section.1.section_name(), "1");
        assert_eq!(third_section.1.context(), ["chapters","c"]);

        // 3: Mid-chapter heading
        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:3");
        assert_eq!(fourth_section.1.end_cv().to_string(), "1:4");
        assert_eq!(fourth_section.1.start_index(), 20); // starts at 'v='
        assert_eq!(fourth_section.1.end_index(), 30); // ends at '¬c'
        assert_eq!(fourth_section.1.reason_marker(), "s1");
        assert_eq!(fourth_section.1.section_name(), "First section heading mid-chapter");
        assert_eq!(fourth_section.1.context(), ["chapters","c"]);

        // 4: Chapter 2
        let fifth_section = section_index.index_data.get_index(4).unwrap();
        assert_eq!(fifth_section.0.to_string(), "2:1");
        assert_eq!(fifth_section.1.end_cv().to_string(), "2:2");
        assert_eq!(fifth_section.1.start_index(), 31); // starts at 'c'
        assert_eq!(fifth_section.1.end_index(), 39); // ends at '¬p'
        assert_eq!(fifth_section.1.reason_marker(), "c");
        assert_eq!(fifth_section.1.section_name(), "2");
        assert_eq!(fifth_section.1.context(), ["chapters","c"]);

        // 5: Chapter 3 (merged c/s1)
        let sixth_section = section_index.index_data.get_index(5).unwrap();
        assert_eq!(sixth_section.0.to_string(), "3:1");
        assert_eq!(sixth_section.1.end_cv().to_string(), "3:2");
        assert_eq!(sixth_section.1.start_index(), 40); // starts at 'c''
        assert_eq!(sixth_section.1.end_index(), 51); // ends at '¬c'
        assert_eq!(sixth_section.1.reason_marker(), "c/s1");
        assert_eq!(sixth_section.1.section_name(), "Psa 3 section heading");
        assert_eq!(sixth_section.1.context(), ["chapters","c"]);
    }

    #[test]
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
        assert_eq!(entry1.end_cv().to_string(), "-1:22");
        assert_eq!(entry1.start_index(), 13);
        assert_eq!(entry1.end_index(), 22);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:1 s1='God\'s command to rebuild the temple':
        let (cv2, entry2) = section_index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:1");
        assert_eq!(entry2.end_cv().to_string(), "1:11");
        assert_eq!(entry2.start_index(), 24);
        assert_eq!(entry2.end_index(), 72);
        assert_eq!(entry2.reason_marker(), "s1/c");
        assert_eq!(entry2.section_name(), "God's command to rebuild the temple");

        // 3 1:11 s1='The people start rebuilding'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:12");
        assert_eq!(entry3.end_cv().to_string(), "1:15");
        assert_eq!(entry3.start_index(), 73);
        assert_eq!(entry3.end_index(), 91);
        assert_eq!(entry3.reason_marker(), "s1");
        assert_eq!(entry3.section_name(), "The people start rebuilding");

        // 4 2:1 s1='The splendour of the new temple'
        let (cv4, entry4) = section_index.index_data.get_index(4).unwrap();
        assert_eq!(cv4.to_string(), "2:1");
        assert_eq!(entry4.end_cv().to_string(), "2:9");
        assert_eq!(entry4.start_index(), 92);
        assert_eq!(entry4.end_index(), 126);
        assert_eq!(entry4.reason_marker(), "s1/c");
        assert_eq!(entry4.section_name(), "The splendour of the new temple");

        // 5 2:9 s1='Haggai consults the priests'
        let (cv5, entry5) = section_index.index_data.get_index(5).unwrap();
        assert_eq!(cv5.to_string(), "2:10");
        assert_eq!(entry5.end_cv().to_string(), "2:19");
        assert_eq!(entry5.start_index(), 127);
        assert_eq!(entry5.end_index(), 173);
        assert_eq!(entry5.reason_marker(), "s1");
        assert_eq!(entry5.section_name(), "Haggai consults the priests");

        // 6 2:19 s1='God\'s promise to Zerubavel'
        let (cv6, entry6) = section_index.index_data.get_index(6).unwrap();
        assert_eq!(cv6.to_string(), "2:20");
        assert_eq!(entry6.end_cv().to_string(), "2:23");
        assert_eq!(entry6.start_index(), 174);
        assert_eq!(entry6.end_index(), 192); // Don't include the ¬chapters
        assert_eq!(entry6.reason_marker(), "s1");
        assert_eq!(entry6.section_name(), "God's promise to Zerubavel");
    }

    #[test]
    fn test_oet_rv_malachi_section_index_build() {
        // Note that OET-RV Malachi has 3 section headings inside verse boundaries XXXX WRONG!!! This test can eventually be deleted
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
        //     OET-RV MAL processed_line_entries = InternalBibleEntryList:
        //         0/ id = "MAL - Open English Translation…ders' Version (OET-RV) v0.1.05"
        //         1/ usfm = "3.0"
        //         2/ ide = "UTF-8"
        //         3/ rem = "ESFM v0.6 MAL"
        //         4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //         5/ headers = ""
        //         6/ h = "Malaki"
        //         7/ toc1 = "Malaki"
        //         8/ toc2 = "Malaki"
        //         9/ toc3 = "Mal."
        //         10/ mt1 = "Malaki"
        //         11/ mt2 = "(Malachi)"
        //         12/ ¬headers = ""
        //         13/ intro = ""
        //         14/ is1 = "Introduction"
        //         15/ ip = "This document records some of … and to restore his agreement."
        //         16/ iot = "Main components of this account"
        //         17/ io1 = "The sins of the Israelis 1:1–2:16"
        //         18/ io1 = "God's judgement and mercy 2:17–4:6"
        //         19/ ¬iot = ""
        //         20/ rem = "This is still a very early loo…dvance before using in public."
        //         21/ ¬is1 = "21"
        //         22/ ie = ""
        //         23/ ¬intro = ""
        //         24/ chapters = ""
        //         25/ c = "1"
        //         26/ p = ""
        //         27/ c# = "1"
        //         28/ v = "1"
        //         29/ v~ = "This is a message¦380162 that …ve to Malaki for the Israelis:"
        //         30/ ¬v = "1"
        //         31/ ¬p = ""
        //         32/ v= = "2"
        //         33/ s1 = "Yahweh's love for the Israelis"
        //         34/ rem = "/s1 The Lord's Love for Israel…om; The Lord's Love for Israel"
        //         35/ p = ""
        //         36/ v = "2"
        //         37/ v~ = "“I have loved you all,” says Y…e you shown your love for us?”"
        //         38/ ¬p = ""
        //         39/ p = ""
        //         40/ v~ = "“Wasn't Esaw¦380181 Yacob's¦38…. “Yet I've¦380171 loved Yacob" + extras
        //         41/ ¬v = "2"
        //         42/ v = "3"
        //         43/ v~ = "and ≈rejected Esaw. I've¦38019…2 to the wild jackals¦380203.”"
        //         44/ ¬v = "3"
        //         45/ ¬p = ""
        //         46/ p = ""
        //         47/ v = "4"
        //         48/ v~ = "If Esaw's descendants in Edom¦…is forever¦380233 angry with.’"
        //         49/ ¬v = "4"
        //         50/ ¬p = ""
        //         51/ p = ""
        //         52/ v = "5"
        //         53/ v~ = "Your own eyes¦380235 will see¦…el's¦380243 borders¦380242.’ ”"
        //         54/ ¬v = "5"
        //         55/ ¬p = ""
        //         56/ ¬s1 = ""
        //         57/ v= = "6"
        //         58/ s1 = "Second-class sacrifices"
        //         59/ rem = "/s1 The Lord Reprimands the Pr…; Corruption of the Priesthood"
        //         60/ p = ""
        //         61/ v = "6"
        //         62/ v~ = "“A son honours his father, and…ts¦380267 who despise my name."
        //         63/ ¬p = ""
        //         64/ p = ""
        //         65/ v~ = "“But¦380248 you say, ‘How have we despised your name?’"
        //         66/ ¬v = "6"
        //         67/ v = "7"
        //         68/ v~ = "By offering polluted food on¦3…0287 can just be disrespected."
        //         69/ ¬v = "7"
        //         70/ v = "8"
        //         71/ v~ = "Don't¦380297 you think it's wr…ommander¦380317 Yahweh¦380316." + extras
        //         72/ ¬v = "8"
        //         73/ ¬p = ""
        //         74/ p = ""
        //         75/ v = "9"
        //         76/ v~ = "≈So¦380319 now bring you reque…inging second-class offerings?"
        //         77/ ¬v = "9"
        //         78/ ¬p = ""
        //         79/ p = ""
        //         80/ v = "10"
        //         81/ v~ = "“Yeah, if only there¦380349 wa…380357 ≈that you all bring me."
        //         82/ ¬v = "10"
        //         83/ v = "11"
        //         84/ v~ = "People in other countries from…ommander¦380388 Yahweh¦380387."
        //         85/ ¬v = "11"
        //         86/ v = "12"
        //         87/ v~ = "“But¦380392 you all are dishon… treated with¦380393 contempt."
        //         88/ ¬v = "12"
        //         89/ v = "13"
        //         90/ v~ = "You all also say, ‘How tiresom… those from you?” says Yahweh."
        //         91/ ¬v = "13"
        //         92/ v = "14"
        //         93/ v~ = "“May the cheats be cursed¦3804…ted among the nations¦380447.”"
        //         94/ ¬v = "14"
        //         95/ ¬p = ""
        //         96/ ¬s1 = "1"
        //         97/ ¬c = "1"
        //         98/ c = "2"
        //         99/ v= = "1"
        //         100/ s1 = "A warning for the priests"
        //         101/ rem = "/s1 Admonition for the Priests; A Warning for the Priests"
        //         102/ p = ""
        //         103/ c# = "2"
        //         104/ v = "1"
        //         105/ v~ = "Now¦380453 you priests¦380453,…mand¦380451 is for all of you:"
        //         106/ ¬v = "1"
        //         107/ v = "2"
        //         108/ v~ = "Army-commander¦380471 Yahweh¦3…nternalising ‘my instructions."
        //         109/ ¬v = "2"
        //         110/ v = "3"
        //         111/ v~ = "Listen, I'm about¦380491 to re… be taken¦380503 away with it."
        //         112/ ¬v = "3"
        //         113/ v = "4"
        //         114/ v~ = "That's so you'll all know¦3805…ommander¦380521 Yahweh¦380520." + extras
        //         115/ ¬v = "4"
        //         116/ ¬p = ""
        //         117/ p = ""
        //         118/ v = "5"
        //         119/ v~ = "“My agreement with @your ances… and ≈honoured my name¦380535." + extras
        //         120/ ¬v = "5"
        //         121/ v = "6"
        //         122/ v~ = "≈They taught the people what w…any people to stop disobeying."
        //         123/ ¬v = "6"
        //         124/ v = "7"
        //         125/ v~ = "≈Yes, priests¦380559 should pa…eh's¦380568 messengers¦380567."
        //         126/ ¬v = "7"
        //         127/ ¬p = ""
        //         128/ p = ""
        //         129/ v = "8"
        //         130/ v~ = "But¦380573 you all have turned…ommander¦380586 Yahweh¦380585."
        //         131/ ¬v = "8"
        //         132/ v = "9"
        //         133/ v~ = "“So¦380588 that's why I've¦380…07 matters¦380598 of the law.”"
        //         134/ ¬v = "9"
        //         135/ ¬p = ""
        //         136/ ¬s1 = ""
        //         137/ v= = "10"
        //         138/ s1 = "The people have been unfaithful"
        //         139/ rem = "/s1 A Call to Faithfulness; Th…People's Unfaithfulness to God"
        //         140/ p = ""
        //         141/ v = "10"
        //         142/ v~ = "Don't¦380610 we all have one f…1 our¦380613 ancestors¦380624?"
        //         143/ ¬v = "10"
        //         144/ v = "11"
        //         145/ v~ = "Our nation of Yehudah¦380627 (… women who worship pagan gods."
        //         146/ ¬v = "11"
        //         147/ v = "12"
        //         148/ v~ = "May Yahweh, the one who is awa… army-commander¦380658 Yahweh."
        //         149/ ¬v = "12"
        //         150/ ¬p = ""
        //         151/ p = ""
        //         152/ v = "13"
        //         153/ v~ = "Secondly¦380666, you cover¦380…678 what you all bring to him."
        //         154/ ¬v = "13"
        //         155/ v = "14"
        //         156/ v~ = "≈So¦380682 you ≈ask, “Why not?… and¦380682 despite your vows."
        //         157/ ¬v = "14"
        //         158/ v = "15"
        //         159/ v~ = "Didn't @Yahweh make you and yo…u married when you were young."
        //         160/ ¬v = "15"
        //         161/ ¬p = ""
        //         162/ p = ""
        //         163/ v = "16"
        //         164/ v~ = "“Indeed, I hate divorce,” says…d don't¦380743 be unfaithful.”"
        //         165/ ¬v = "16"
        //         166/ ¬p = ""
        //         167/ ¬s1 = ""
        //         168/ v= = "17"
        //         169/ s1 = "Judgement day is coming"
        //         170/ rem = "/s1 The Day of Judgment; The Day of Judgment Is Near"
        //         171/ p = ""
        //         172/ v = "17"
        //         173/ v~ = "You've all wearied Yahweh with…god¦380767 of justice¦380768?”"
        //         174/ ¬v = "17"
        //         175/ ¬p = ""
        //         176/ ¬c = "2"
        //         177/ c = "3"
        //         178/ rem = "/s1 The Coming Day of Judgment; The Coming Messenger"
        //         179/ p = ""
        //         180/ c# = "3"
        //         181/ v = "1"
        //         182/ v~ = "“Listen, I'm about to send my …ommander¦380799 Yahweh¦380798." + extras
        //         183/ ¬v = "1"
        //         184/ v = "2"
        //         185/ v~ = "≈But¦380801 who could survive …e the cleaners' powerful soap?" + extras
        //         186/ ¬v = "2"
        //         187/ v = "3"
        //         188/ v~ = "@Yahweh will act as a refiner … to *him that are ≈acceptable."
        //         189/ ¬v = "3"
        //         190/ v = "4"
        //         191/ v~ = "After that, the offerings¦3808…d as in previous years¦380845."
        //         192/ ¬v = "4"
        //         193/ ¬p = ""
        //         194/ p = ""
        //         195/ v = "5"
        //         196/ v~ = "This is what army-commander¦38…hose who ≈refuse to honour me."
        //         197/ ¬v = "5"
        //         198/ ¬p = ""
        //         199/ ¬s1 = ""
        //         200/ v= = "6"
        //         201/ s1 = "Giving a tenth"
        //         202/ rem = "/s1 The Payment of Tithes; Robbing God; A Call to Repentance"
        //         203/ p = ""
        //         204/ v = "6"
        //         205/ v~ = "“I am Yahweh¦380876 and¦380879…380882 haven't been destroyed."
        //         206/ ¬v = "6"
        //         207/ v = "7"
        //         208/ v~ = "Ever since¦380886 the time¦380… can we¦380901 return to you?’"
        //         209/ rem = "/s1 Don't rob God"
        //         210/ ¬v = "7"
        //         211/ v = "8"
        //         212/ v~ = "Can a human rob God¦380905? Ye… plus¦380910 offerings¦380914."
        //         213/ ¬v = "8"
        //         214/ v = "9"
        //         215/ v~ = "You're¦380919 all cursed¦38091…e¦380923 nation¦380922 of you."
        //         216/ ¬v = "9"
        //         217/ v = "10"
        //         218/ v~ = "Bring¦380925 the full tenth in…owing blessing¦380954 for you." + extras
        //         219/ ¬v = "10"
        //         220/ v = "11"
        //         221/ v~ = "I'll¦380968 rebuke¦380961 the …ommander¦380980 Yahweh¦380979." + extras
        //         222/ ¬v = "11"
        //         223/ v = "12"
        //         224/ v~ = "“Then¦380983 all the other cou…ommander¦380995 Yahweh¦380994."
        //         225/ ¬v = "12"
        //         226/ ¬p = ""
        //         227/ ¬s1 = ""
        //         228/ v= = "13"
        //         229/ s1 = "God promises mercy for some"
        //         230/ rem = "/s1 The righteous triumphant; God's Promise of Mercy"
        //         231/ p = ""
        //         232/ v = "13"
        //         233/ v~ = "“Your words¦381000 against me … among ourselves against you?’"
        //         234/ ¬v = "13"
        //         235/ v = "14"
        //         236/ v~ = "You've all said¦381009, ‘It's …ommander¦381024 Yahweh¦381023?"
        //         237/ ¬v = "14"
        //         238/ v = "15"
        //         239/ v~ = "≈It seems that arrogant¦381029…et nothing happens to them.’ ”"
        //         240/ rem = "/s1 The Reward of the Faithful; The Lord's Promise of Mercy"
        //         241/ ¬v = "15"
        //         242/ ¬p = ""
        //         243/ p = ""
        //         244/ v = "16"
        //         245/ v~ = "Then those who ≈still respecte…noured his¦381054 name¦381058."
        //         246/ ¬v = "16"
        //         247/ v = "17"
        //         248/ v~ = "“They'll be mine,” says¦381062…punish his son who ≈obeys him."
        //         249/ ¬v = "17"
        //         250/ v = "18"
        //         251/ v~ = "Then¦381081 once again¦381081 …8 and #those who don't¦381090."
        //         252/ ¬v = "18"
        //         253/ ¬p = ""
        //         254/ ¬s1 = "3"
        //         255/ ¬c = "3"
        //         256/ c = "4"
        //         257/ v= = "1"
        //         258/ s1 = "Be ready for future judgement"
        //         259/ rem = "/s1 The Day of the Lord; The C…ing; The Great Day of the Lord"
        //         260/ p = ""
        //         261/ c# = "4"
        //         262/ v = "1"
        //         263/ v~ = "“≈Yes, listen, the day that bu…leaving any roots or branches."
        //         264/ ¬v = "1"
        //         265/ v = "2"
        //         266/ v~ = "But for you who respect my nam…calves let out of their stall,"
        //         267/ ¬v = "2"
        //         268/ v = "3"
        //         269/ v~ = "and you'll all trample down th…,” says army-commander Yahweh."
        //         270/ ¬v = "3"
        //         271/ ¬p = ""
        //         272/ p = ""
        //         273/ v = "4"
        //         274/ v~ = "“≈Be sure to obey the law that…—the statutes and the rulings."
        //         275/ ¬v = "4"
        //         276/ ¬p = ""
        //         277/ p = ""
        //         278/ v = "5"
        //         279/ v~ = "Listen, I'll send the prophet … fearful day of *my judgement." + extras
        //         280/ ¬v = "5"
        //         281/ v = "6"
        //         282/ v~ = "He'll ≈restore harmony between…th with complete destruction.”"
        //         283/ ¬v = "6"
        //         284/ ¬p = ""
        //         285/ ¬s1 = ""
        //         286/ ¬c = "4"
        //         287/ ¬chapters = ""

        let mut section_index = InternalBibleBookSectionIndex::new("OET-RV", "MAL");
        section_index.build(processed_line_entries.clone()).unwrap();
        
        // It should give the following eleven entries:
        //     0/ ('-1', '0') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:12 ix=0–12 (cnt=13) Headers='MAL'
        //     1/ ('-1', '14') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:22 ix=14–22 (cnt=9) is1='Introduction'
        //     2/ ('1', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:1 ix=24–30 (cnt=7) c='Malaki 1' ctxt=["chapters", "c"]
        //     3/ ('1', '2') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:5 ix=31–54 (cnt=24) s1='Yahweh's love for the Israelis' ctxt=["chapters", "c"]
        //     4/ ('1', '6') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:14 ix=55–94 (cnt=40) s1='Second-class sacrifices' ctxt=["chapters", "c"]
        //     5/ ('2', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:9 ix=95–132 (cnt=38) s1/c='A warning for the priests' ctxt=["chapters", "c"]
        //     6/ ('2', '10') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:16 ix=133–162 (cnt=30) s1='The people have been unfaithful' ctxt=["chapters", "c"]
        //     7/ ('2', '17') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:5 ix=163–193 (cnt=31) s1='Judgement day is coming' ctxt=["chapters", "c"]
        //     8/ ('3', '6') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:12 ix=194–220 (cnt=27) s1='Giving a tenth' ctxt=["chapters", "c"]
        //     9/ ('3', '13') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:18 ix=221–247 (cnt=27) s1='God promises mercy for some' ctxt=["chapters", "c"]
        //     10/ ('4', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=4:6 ix=248–277 (cnt=30) s1/c='Be ready for future judgement' ctxt=["chapters", "c"]

        assert_eq!(section_index.len(), 11);
        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "is1", "c", "s1", "s1", "s1/c", "s1", "s1", "s1", "s1", "s1/c"]);

        // 0 -1:0 Headers='MAL'
        let (cv0, entry0) = section_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:12");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 12); // ends at '¬headers'
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
        assert_eq!(entry2.start_index(), 25); // c
        assert_eq!(entry2.end_index(), 31); // ¬p
        assert_eq!(entry2.reason_marker(), "c");
        assert_eq!(entry2.section_name(), "Malaki 1");

        // 3 1:2 s1='Yahweh's love for the Israelis'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:2");
        assert_eq!(entry3.end_cv().to_string(), "1:5");
        assert_eq!(entry3.start_index(), 32); // v=
        assert_eq!(entry3.end_index(), 56);
        assert_eq!(entry3.reason_marker(), "s1");
        assert_eq!(entry3.section_name(), "Yahweh's love for the Israelis");

        // 4 1:6 s1='Second-class sacrifices'
        let (cv4, entry4) = section_index.index_data.get_index(4).unwrap();
        assert_eq!(cv4.to_string(), "1:6");
        assert_eq!(entry4.end_cv().to_string(), "1:14");
        assert_eq!(entry4.start_index(), 57);
        assert_eq!(entry4.end_index(), 97);
        assert_eq!(entry4.reason_marker(), "s1");
        assert_eq!(entry4.section_name(), "Second-class sacrifices");

        // 5 2:1 s1='A warning for the priests'
        let (cv5, entry5) = section_index.index_data.get_index(5).unwrap();
        assert_eq!(cv5.to_string(), "2:1");
        assert_eq!(entry5.end_cv().to_string(), "2:9");
        assert_eq!(entry5.start_index(), 98);
        assert_eq!(entry5.end_index(), 136);
        assert_eq!(entry5.reason_marker(), "s1/c");
        assert_eq!(entry5.section_name(), "A warning for the priests");

        // 6 2:10 s1='The people have been unfaithful'
        let (cv6, entry6) = section_index.index_data.get_index(6).unwrap();
        assert_eq!(cv6.to_string(), "2:10");
        assert_eq!(entry6.end_cv().to_string(), "2:16");
        assert_eq!(entry6.start_index(), 137);
        assert_eq!(entry6.end_index(), 167);
        assert_eq!(entry6.reason_marker(), "s1");
        assert_eq!(entry6.section_name(), "The people have been unfaithful");

        // 7 2:19 s1='Judgement day is coming'
        let (cv7, entry7) = section_index.index_data.get_index(7).unwrap();
        assert_eq!(cv7.to_string(), "2:17");
        assert_eq!(entry7.end_cv().to_string(), "3:5");
        assert_eq!(entry7.start_index(), 168);
        assert_eq!(entry7.end_index(), 199);
        assert_eq!(entry7.reason_marker(), "s1");
        assert_eq!(entry7.section_name(), "Judgement day is coming");

        // 8 3:6 s1='Giving a tenth'
        let (cv8, entry8) = section_index.index_data.get_index(8).unwrap();
        assert_eq!(cv8.to_string(), "3:6");
        assert_eq!(entry8.end_cv().to_string(), "3:12");
        assert_eq!(entry8.start_index(), 200);
        assert_eq!(entry8.end_index(), 227);
        assert_eq!(entry8.reason_marker(), "s1");
        assert_eq!(entry8.section_name(), "Giving a tenth");

        // 9 3:13 s1='God promises mercy for some'
        let (cv9, entry9) = section_index.index_data.get_index(9).unwrap();
        assert_eq!(cv9.to_string(), "3:13");
        assert_eq!(entry9.end_cv().to_string(), "3:18");
        assert_eq!(entry9.start_index(), 228);
        assert_eq!(entry9.end_index(), 255);
        assert_eq!(entry9.reason_marker(), "s1");
        assert_eq!(entry9.section_name(), "God promises mercy for some");

        // 10 4:1 s1='Be ready for future judgement'
        let (cv10, entry10) = section_index.index_data.get_index(10).unwrap();
        assert_eq!(cv10.to_string(), "4:1");
        assert_eq!(entry10.end_cv().to_string(), "4:6");
        assert_eq!(entry10.start_index(), 256);
        assert_eq!(entry10.end_index(), 286);
        assert_eq!(entry10.reason_marker(), "s1/c");
        assert_eq!(entry10.section_name(), "Be ready for future judgement");
    }

    #[test]
    fn test_oet_rv_2samuel_section_index_build() {
        // Note that OET-RV 2 Samuel has 3 section headings inside verse boundaries
        set_strict_checking_flag( true );
        let content = include_str!("../../../../Tests/DataFilesForTests/OET-RV/OET-RV_SA2.ESFM");
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
        let processed_line_entries = crate::processing::process_lines(raw_lines, "SA2", "OET-RV", &options);

        println!("OET-RV SA2 processed_line_entries = {}", processed_line_entries);
        //         OET-RV SA2 added c12 line_entry 'v=' = '15b'
        //         OET-RV SA2 added c12 line_entry 'v=' = '15b'
        //         OET-RV SA2 added c12 line_entry 'v=' = '24b'
        //         OET-RV SA2 added c12 line_entry 'v=' = '24b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '8b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '8b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '18b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '18b'
        //     0/ id = "2SA - Open English Translation…ders' Version (OET-RV) v0.1.16"
        //     1/ usfm = "3.0"
        //     2/ ide = "UTF-8"
        //     3/ rem = "ESFM v0.6 SA2"
        //     4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //     5/ headers = ""
        //     6/ h = "2 Shemuel"
        //     7/ toc1 = "2 Shemuel"
        //     8/ toc2 = "2 Shemuel"
        //     9/ toc3 = "2 She."
        //     10/ mt1 = "2 Shemuel"
        //     11/ ¬headers = ""
        //     12/ intro = ""
        //     13/ is1 = "Introduction"
        //     14/ ip = "Second Shemuel (commonly, but …ong to fit on a single scroll."
        //     15/ ip = "This the story of David's reig… punishment that God gave him."
        //     16/ ip = "The times of peace and prosper…d who would love God like him."
        //     17/ iot = "Main components of this account"
        //     18/ io1 = "The kingdom of David in Yehudah 1:1–4:12"
        //     19/ io1 = "The kingdom of David over all Yisrael 5:1–24:25"
        //     20/ io2 = "a. The early years 5:1–10:19"
        //     21/ io2 = "b. David takes Uriyah's wife 11:1–12:25"
        //     22/ io2 = "c. The battles and the difficulties 12:26–20:26"
        //     23/ io2 = "d. The later years 21:1–24:25"
        //     24/ ¬iot = ""
        //     25/ rem = "This is still a very early loo…dvance before using in public."
        //     26/ ie = ""
        //     27/ ¬intro = ""
        //     28/ chapters = ""
        //     29/ c = "1"
        //     30/ v= = "1"
        //     31/ s1 = "David learns about Sha'ul's death"
        //     32/ rem = "/s1 David Learns of Saul's Dea…g; David Hears of Saul's Death"
        //     33/ s4 = "Full kingdom"
        //     34/ p = ""
        //     35/ c# = "1"
        //     36/ v = "1"
        //     37/ v~ = "≈After David¦141765 returned¦1…was dead by this time¦141774.)"
        //     38/ ¬v = "1"
        //     39/ v = "2"
        //     40/ v~ = "Then¦141777 on the third¦14178…is knees and bowed¦141802 low."
        //     41/ ¬v = "2"
        //     42/ v = "3"
        //     43/ v~ = "“Where ≈have you¦141809 come from?” David¦141806 ≈asked him."
        //     44/ ¬p = ""
        //     45/ p = ""
        //     46/ v~ = "“I ≈was in Yisrael's¦141813 ca…o escape¦141814.” he ≈replied."
        //     47/ ¬v = "3"
        //     48/ v = "4"
        //     49/ v~ = "“≈Why? What happened?” David¦1…ded. “Tell me, please¦141825,”"
        //     50/ ¬p = ""
        //     51/ p = ""
        //     52/ v~ = "“&Our people¦141841 fled from …844 and his son Yonatan died.”"
        //     53/ ¬p = ""
        //     54/ ¬v = "4"
        //     55/ p = ""
        //     56/ v = "5"
        //     57/ v~ = "“How do¦141857 you¦141857 know…41853 who'd ≈brought the news."
        //     58/ ¬v = "5"
        //     59/ ¬p = ""
        //     60/ p = ""
        //     61/ v = "6"
        //     62/ v~ = "“I¦141871 happened¦141870 to b…83 overtook¦141884 him¦141884," + extras
        //     63/ ¬v = "6"
        //     64/ v = "7"
        //     65/ v~ = "and he turned¦141886 around an… and I ≈answered, ‘Here I am.’"
        //     66/ ¬v = "7"
        //     67/ v = "8"
        //     68/ v~ = "‘Who are you¦141898?’ he ≈aske…Amalekite¦141902,’ I told him."
        //     69/ ¬v = "8"
        //     70/ v = "9"
        //     71/ v~ = "Then¦141905 he said¦141905 to …live, the pain is unbearable.’"
        //     72/ ¬v = "9"
        //     73/ v = "10"
        //     74/ v~ = "≈So¦141923 I stood¦141923 over…ere to you, my master¦141948.”"
        //     75/ ¬v = "10"
        //     76/ ¬p = ""
        //     77/ p = ""
        //     78/ v = "11"
        //     79/ v~ = "Then¦141951 David¦141952 pulle…141959 with him ≈did the same,"
        //     80/ ¬v = "11"
        //     81/ v = "12"
        //     82/ v~ = "and they¦141985 mourned¦141963…raelis¦141983 had been killed."
        //     83/ ¬v = "12"
        //     84/ ¬p = ""
        //     85/ p = ""
        //     86/ v = "13"
        //     87/ v~ = "Then David¦141990 ≈asked the y…he news, “Where are you from?”"
        //     88/ ¬p = ""
        //     89/ p = ""
        //     90/ v~ = "“I'm a foreigner's son,” he ≈replied, “an Amalekite¦142004.”"
        //     91/ ¬v = "13"
        //     92/ v = "14"
        //     93/ v~ = "“How come you¦142012 weren't a…nds?” David¦142009 ≈asked him."
        //     94/ ¬v = "14"
        //     95/ v = "15"
        //     96/ v~ = "Then¦142021 David¦142022 calle…42030 him, and he died¦142031."
        //     97/ ¬v = "15"
        //     98/ v = "16"
        //     99/ v~ = "“Your blood's¦142036 on your o…s¦142051 anointed¦142050 one.”"
        //     100/ ¬v = "16"
        //     101/ ¬p = ""
        //     102/ v= = "17"
        //     103/ s1 = "David's song of mourning"
        //     104/ rem = "/s1 David's Lament for Saul an…d's Song for Saul and Jonathan"
        //     105/ s4 = "Full kingdom"
        //     106/ p = ""
        //     107/ v = "17"
        //     108/ v~ = "Then David¦142055 sang this fu…'ul¦142062 and his son Yonatan"
        //     109/ ¬v = "17"
        //     110/ v = "18"
        //     111/ v~ = "and said¦142068 that it should…75 down in the Book of Yashar:" + extras
        //     112/ ¬v = "18"
        //     113/ ¬p = ""
        //     114/ q1 = ""
        //     115/ v = "19"
        //     116/ v~ = "“Yisrael's¦142082 splendour was slain¦142086 ≈in the hills."
        //     117/ ¬q1 = ""
        //     118/ q1 = ""
        //     119/ v~ = "≈How the ≈powerful warriors have ≈died."
        //     120/ ¬q1 = ""
        //     121/ ¬v = "19"
        //     122/ q1 = ""
        //     123/ v = "20"
        //     124/ v~ = "Don't tell ‘them in Gat¦142094."
        //     125/ ¬q1 = ""
        //     126/ q1 = ""
        //     127/ v~ = "≈Don't let ‘them take the news…kelon's¦142099 streets¦142098,"
        //     128/ ¬q1 = ""
        //     129/ q1 = ""
        //     130/ v~ = "in case the Philistine ≈women¦142103 celebrate,"
        //     131/ ¬q1 = ""
        //     132/ q1 = ""
        //     133/ v~ = "and the daughters of the uncircumcised¦142109 are elated."
        //     134/ ¬q1 = ""
        //     135/ ¬v = "20"
        //     136/ b = ""
        //     137/ q1 = ""
        //     138/ v = "21"
        //     139/ v~ = "≈You mountains¦142111 in¦142112 Gilboa¦142112,"
        //     140/ ¬q1 = ""
        //     141/ q2 = ""
        //     142/ v~ = "may you have no dew or rain fall on¦142112 you,"
        //     143/ ¬q2 = ""
        //     144/ q2 = ""
        //     145/ v~ = "nor fields¦142120 producing grain for offerings."
        //     146/ ¬q2 = ""
        //     147/ q1 = ""
        //     148/ v~ = "Because it¦142124 was there¦14…as ≈splattered with his blood,"
        //     149/ ¬q1 = ""
        //     150/ q2 = ""
        //     151/ v~ = "and the leather won't¦142113 b…eserved with oil¦142131 again."
        //     152/ ¬q2 = ""
        //     153/ ¬v = "21"
        //     154/ q1 = ""
        //     155/ v = "22"
        //     156/ v~ = "From the blood¦142133 of those¦142134 slain¦142134—"
        //     157/ ¬q1 = ""
        //     158/ q2 = ""
        //     159/ v~ = "≈from the fat of the ≈warriors,"
        //     160/ ¬q2 = ""
        //     161/ q1 = ""
        //     162/ v~ = "Yonatan's bow didn't ≈retreat"
        //     163/ ¬q1 = ""
        //     164/ q2 = ""
        //     165/ v~ = "≈and¦142142 Sha'ul's sword¦142…2 didn't ≈fail on its strikes."
        //     166/ ¬q2 = ""
        //     167/ ¬v = "22"
        //     168/ b = ""
        //     169/ q1 = ""
        //     170/ v = "23"
        //     171/ v~ = "Sha'ul¦142148 and Yonatan were loved—"
        //     172/ ¬q1 = ""
        //     173/ q2 = ""
        //     174/ v~ = "≈they pleased¦142151 the people."
        //     175/ ¬q2 = ""
        //     176/ q2 = ""
        //     177/ v~ = "and even at¦142152 their death…they weren't separated¦142155."
        //     178/ ¬q2 = ""
        //     179/ q1 = ""
        //     180/ v~ = "They were swifter¦142157 than eagles¦142156."
        //     181/ ¬q1 = ""
        //     182/ q2 = ""
        //     183/ v~ = "≈they were stronger¦142159 than lions¦142158."
        //     184/ ¬q2 = ""
        //     185/ ¬v = "23"
        //     186/ b = ""
        //     187/ q1 = ""
        //     188/ v = "24"
        //     189/ v~ = "Weep for Sha'ul¦142165 you dau…ters¦142161 of Yisrael¦142162,"
        //     190/ ¬q1 = ""
        //     191/ q1 = ""
        //     192/ v~ = "the one who ≈dressed you in ni…clothes¦142167 with jewellery,"
        //     193/ ¬q1 = ""
        //     194/ q1 = ""
        //     195/ v~ = "≈and gave you all gold¦142174 ≈brooches to put on."
        //     196/ ¬q1 = ""
        //     197/ ¬v = "24"
        //     198/ b = ""
        //     199/ q1 = ""
        //     200/ v = "25"
        //     201/ v~ = "Those warriors have fallen¦142…e¦142181 of the battle¦142182."
        //     202/ ¬q1 = ""
        //     203/ q1 = ""
        //     204/ v~ = "≈Yonatan has been killed there on the hills."
        //     205/ ¬q1 = ""
        //     206/ ¬v = "25"
        //     207/ b = ""
        //     208/ q1 = ""
        //     209/ v = "26"
        //     210/ v~ = "I ≈grieve for you my dear friend Yonatan."
        //     211/ ¬q1 = ""
        //     212/ q1 = ""
        //     213/ v~ = "You were ≈so kind to me."
        //     214/ ¬q1 = ""
        //     215/ q1 = ""
        //     216/ v~ = "Your ≈friendship meant more to…¦142202 ≈who say they love me."
        //     217/ ¬q1 = ""
        //     218/ ¬v = "26"
        //     219/ b = ""
        //     220/ q1 = ""
        //     221/ v = "27"
        //     222/ v~ = "Yes, those ≈powerful warriors have fallen¦142205,"
        //     223/ ¬q1 = ""
        //     224/ q1 = ""
        //     225/ v~ = "≈and¦142207 those weapons¦1422… of war have ≈been destroyed.”"
        //     226/ ¬v = "27"
        //     227/ ¬q1 = ""
        //     228/ ¬c = "1"
        //     229/ c = "2"
        //     230/ v= = "1"
        //     231/ s1 = "The kingdom of David"
        //     232/ rem = "/s1 David Anointed King of Jud…David Anointed King Over Judah"
        //     233/ s4 = "Full kingdom"
        //     234/ p = ""
        //     235/ c# = "2"
        //     236/ v = "1"
        //     237/ v~ = "After ≈that was over, David¦14…hudah's¦142224 cities¦142223?”"
        //     238/ ¬p = ""
        //     239/ p = ""
        //     240/ v~ = "“Yes,, go,” Yahweh ≈answered."
        //     241/ ¬p = ""
        //     242/ p = ""
        //     243/ v~ = "“Where should I go?” David ≈asked again."
        //     244/ ¬p = ""
        //     245/ p = ""
        //     246/ v~ = "“To Hebron¦142234,” he said."
        //     247/ ¬p = ""
        //     248/ ¬v = "1"
        //     249/ p = ""
        //     250/ v = "2"
        //     251/ v~ = "≈So¦142236 David¦142238 took h…142247) and went there¦142237." + extras
        //     252/ ¬v = "2"
        //     253/ v = "3"
        //     254/ v~ = "He¦142254 took his men¦142249 … the surrounding towns¦142258."
        //     255/ ¬v = "3"
        //     256/ v = "4"
        //     257/ v~ = "Then¦142261 the Yehudah ≈leade…9 as king¦142270 over Yehudah."
        //     258/ ¬p = ""
        //     259/ p = ""
        //     260/ v~ = "They told him, “It was the men… buried¦142282 Sha'ul¦142285.”" + extras
        //     261/ ¬v = "4"
        //     262/ v = "5"
        //     263/ v~ = "≈So David¦142289 sent¦142288 m…2310 to bury him respectfully."
        //     264/ ¬v = "5"
        //     265/ v = "6"
        //     266/ v~ = "Now may Yahweh¦142317 ≈treat y…5 to you because you did that."
        //     267/ ¬v = "6"
        //     268/ v = "7"
        //     269/ v~ = "≈Meanwhile now that Sha'ul¦142…king¦142352 over ≈their tribe."
        //     270/ ¬v = "7"
        //     271/ ¬p = ""
        //     272/ v= = "8"
        //     273/ s1 = "Disputes between Sha'ul and David's families"
        //     274/ rem = "/s1 Ishbaal King of Israel; Is…n the Houses of David and Saul"
        //     275/ s4 = "Full kingdom"
        //     276/ p = ""
        //     277/ v = "8"
        //     278/ v~ = "However, Abner¦142356 (Ner's¦1…ysh-Boshet across to Mahanayim" + extras
        //     279/ ¬v = "8"
        //     280/ v = "9"
        //     281/ v~ = "and ≈declared him¦142376 to be…nd over all of Yisrael¦142394."
        //     282/ ¬v = "9"
        //     283/ v = "10"
        //     284/ v~ = "Iysh-Boshet ≈was forty¦142400 … he ≈ruled them for two years."
        //     285/ ¬p = ""
        //     286/ p = ""
        //     287/ v~ = "But¦142412 the tribe of Yehuda…2417 was loyal to David¦142420"
        //     288/ ¬v = "10"
        //     289/ v = "11"
        //     290/ v~ = "and *he ≈ruled them for seven¦…42434 and a half years¦142435."
        //     291/ rem = "/s1 The Battle of Gibeon; War between Israel and Judah"
        //     292/ ¬v = "11"
        //     293/ ¬p = ""
        //     294/ p = ""
        //     295/ v = "12"
        //     296/ v~ = "One day Abner¦142441 left Maha… went¦142440 to Gibeon¦142453,"
        //     297/ ¬v = "12"
        //     298/ v = "13"
        //     299/ v~ = "≈but¦142455 Yoav¦142455 (Tseru…roup on each side of the pool."
        //     … (3609 total entries)

        let mut section_index = InternalBibleBookSectionIndex::new("OET-RV", "SA2");
        section_index.build(processed_line_entries.clone()).unwrap();
        
        // It should give the following 52 entries:
        //         OET-RV SA2 added c12 line_entry 'v=' = '15b'
        //         OET-RV SA2 added c12 line_entry 'v=' = '24b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '8b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '18b'
        //     0/ ('-1', '0') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:11 ix=0–11 (cnt=12) Headers='SA2'
        //     1/ ('-1', '13') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:27 ix=13–27 (cnt=15) is1='Introduction'
        //     2/ ('1', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:16 ix=29–101 (cnt=73) s1/c='David learns about Sha'ul's death' ctxt=["chapters", "c"]
        //     3/ ('1', '17') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:27 ix=102–228 (cnt=127) s1='David's song of mourning' ctxt=["chapters", "c"]
        //     4/ ('2', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:7 ix=229–271 (cnt=43) s1/c='The kingdom of David' ctxt=["chapters", "c"]
        //     5/ ('2', '8') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:1 ix=272–388 (cnt=117) s1='Disputes between Sha'ul and David's families' ctxt=["chapters", "c"]
        //     6/ ('3', '2') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:5 ix=389–406 (cnt=18) s1='David's sons' ctxt=["chapters", "c"]
        //     7/ ('3', '6') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:21 ix=407–468 (cnt=62) s1='Abner switches over to David' ctxt=["chapters", "c"]
        //     8/ ('3', '22') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:30 ix=469–503 (cnt=35) s1='Yoav murders Abner' ctxt=["chapters", "c"]
        //     9/ ('3', '31') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:39 ix=504–550 (cnt=47) s1='Abnir's burial' ctxt=["chapters", "c"]
        //     10/ ('4', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=4:12 ix=551–598 (cnt=48) s1/c='The murder of Iysh-Boshet' ctxt=["chapters", "c"]
        //     11/ ('5', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=5:5 ix=599–622 (cnt=24) s1/c='David becomes king of all Yisrael' ctxt=["chapters", "c"]
        //     12/ ('5', '6') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=5:16 ix=623–672 (cnt=50) s1='David captures Yerushalem' ctxt=["chapters", "c"]
        //     13/ ('5', '17') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=5:25 ix=673–714 (cnt=42) s1='Defeated by David the Philistines' ctxt=["chapters", "c"]
        //     14/ ('6', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=6:23 ix=715–806 (cnt=92) s1/c='The Box with the agreement is brought to Yerushalem' ctxt=["chapters", "c"]
        //     15/ ('7', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=7:16 ix=807–867 (cnt=61) s1/c='Yahweh's promise to David' ctxt=["chapters", "c"]
        //     16/ ('7', '17') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=7:29 ix=868–918 (cnt=51) s1='David's prayer' ctxt=["chapters", "c"]
        //     17/ ('8', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=8:18 ix=919–995 (cnt=77) s1/c='David's victories' ctxt=["chapters", "c"]
        //     18/ ('9', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=9:13 ix=996–1074 (cnt=79) s1/c='David assists Mefiboshet' ctxt=["chapters", "c"]
        //     19/ ('10', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=10:19 ix=1075–1154 (cnt=80) s1/c='Yisrael defeats the Ammonites and the Arameans' ctxt=["chapters", "c"]
        //     20/ ('11', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=11:27 ix=1155–1264 (cnt=110) s1/c='David takes Uriyah's wife' ctxt=["chapters", "c"]
        //     21/ ('12', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=12:15 ix=1265–1326 (cnt=62) s1/c='Natan brings rebuke to David' ctxt=["chapters", "c"]
        //     22/ ('12', '15b') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=12:24 ix=1327–1371 (cnt=45) s1='David's son dies' ctxt=["chapters", "c"]
        //     23/ ('12', '24b') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=12:25 ix=1372–1382 (cnt=11) s1='The birth of Shelomoh' ctxt=["chapters", "c"]
        //     24/ ('12', '26') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=12:31 ix=1383–1408 (cnt=26) s1='David captures Rabbah' ctxt=["chapters", "c"]
        //     25/ ('13', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=13:22 ix=1409–1503 (cnt=95) s1/c='Amnon rapes Tamar' ctxt=["chapters", "c"]
        //     26/ ('13', '23') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=13:39 ix=1504–1577 (cnt=74) s1='Abshalom kills Amnon' ctxt=["chapters", "c"]
        //     27/ ('14', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=14:24 ix=1578–1696 (cnt=119) s1/c='Abshalom returns to Yerushalem' ctxt=["chapters", "c"]
        //     28/ ('14', '25') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=14:33 ix=1697–1738 (cnt=42) s1='Abshalom and David reconcile' ctxt=["chapters", "c"]
        //     29/ ('15', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=15:12 ix=1739–1786 (cnt=48) s1/c='Abshalom plans his rebellion' ctxt=["chapters", "c"]
        //     30/ ('15', '13') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=15:37 ix=1787–1887 (cnt=101) s1='The fleeing of David' ctxt=["chapters", "c"]
        //     31/ ('16', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=16:4 ix=1888–1920 (cnt=33) s1/c='Dishonest Tsiva helps David' ctxt=["chapters", "c"]
        //     32/ ('16', '5') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=16:14 ix=1921–1960 (cnt=40) s1='Shimei curses David' ctxt=["chapters", "c"]
        //     33/ ('16', '15') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=16:23 ix=1961–2004 (cnt=44) s1='The conflicting advice of Hushay and Ahitofel' ctxt=["chapters", "c"]
        //     34/ ('17', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=17:14 ix=2005–2061 (cnt=57) s1/c='Hushay argues against Ahitofel's advice' ctxt=["chapters", "c"]
        //     35/ ('17', '15') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=17:29 ix=2062–2129 (cnt=68) s1='The warning to David to flee' ctxt=["chapters", "c"]
        //     36/ ('18', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=18:18 ix=2130–2209 (cnt=80) s1/c='Abshalom's defeat and death' ctxt=["chapters", "c"]
        //     37/ ('18', '19') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=18:33 ix=2210–2305 (cnt=96) s1='David learns about Abshalom's death' ctxt=["chapters", "c"]
        //     38/ ('19', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:8 ix=2306–2338 (cnt=33) s1/c='Yoav scolds David' ctxt=["chapters", "c"]
        //     39/ ('19', '8b') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:18 ix=2339–2382 (cnt=44) s1='David returns to Yerushalem' ctxt=["chapters", "c"]
        //     40/ ('19', '18b') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:23 ix=2383–2409 (cnt=27) s1='David's mercy to Shimei' ctxt=["chapters", "c"]
        //     41/ ('19', '24') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:30 ix=2410–2442 (cnt=33) s1='David's mercy to Mefiboshet' ctxt=["chapters", "c"]
        //     42/ ('19', '31') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:39 ix=2443–2479 (cnt=37) s1='David's kindness to Barzillai' ctxt=["chapters", "c"]
        //     43/ ('19', '40') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:43 ix=2480–2506 (cnt=27) s1='Yehudah and Yisrael disagree' ctxt=["chapters", "c"]
        //     44/ ('20', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=20:22 ix=2507–2616 (cnt=110) s1/c='Sheva rebels against David' ctxt=["chapters", "c"]
        //     45/ ('20', '23') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=20:26 ix=2617–2635 (cnt=19) s1='David's officials' ctxt=["chapters", "c"]
        //     46/ ('21', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=21:14 ix=2636–2701 (cnt=66) s1/c='The Gibeonites' claim on Sha'ul's descendants' ctxt=["chapters", "c"]
        //     47/ ('21', '15') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=21:22 ix=2702–2739 (cnt=38) s1='Battles against Philistine giants' ctxt=["chapters", "c"]
        //     48/ ('22', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=22:51 ix=2740–3199 (cnt=460) s1/c='David's song of praise' ctxt=["chapters", "c"]
        //     49/ ('23', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=23:7 ix=3200–3292 (cnt=93) s1/c='David's ending speech' ctxt=["chapters", "c"]
        //     50/ ('23', '8') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=23:39 ix=3293–3494 (cnt=202) s1='David's top warriors' ctxt=["chapters", "c"]
        //     51/ ('24', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=24:25 ix=3495–3607 (cnt=113) s1/c='David takes a census' ctxt=["chapters", "c"]

        assert_eq!(section_index.len(), 52);
        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "is1", "s1/c", "s1", "s1/c", "s1", "s1", "s1", "s1", "s1", "s1/c", "s1/c",
                                    "s1", "s1", "s1/c", "s1/c", "s1", "s1/c", "s1/c", "s1/c", "s1/c", "s1/c", "s1", "s1",
                                    "s1", "s1/c", "s1", "s1/c", "s1", "s1/c", "s1", "s1/c", "s1", "s1", "s1/c", "s1",
                                    "s1/c", "s1", "s1/c", "s1", "s1", "s1", "s1", "s1", "s1/c", "s1", "s1/c", "s1",
                                    "s1/c", "s1/c", "s1", "s1/c"]);

        // 0 -1:0 Headers='SA2'
        let (cv0, entry0) = section_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:11");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 11); // ends at '¬headers'
        assert_eq!(entry0.reason_marker(), "Headers");
        assert_eq!(entry0.section_name(), "SA2");

        // 1 -1:13 is1='Introduction'
        let (cv1, entry1) = section_index.index_data.get_index(1).unwrap();
        assert_eq!(cv1.to_string(), "-1:13");
        assert_eq!(entry1.end_cv().to_string(), "-1:28");
        assert_eq!(entry1.start_index(), 13);
        assert_eq!(entry1.end_index(), 28);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:1 s1='David learns about Sha'ul's death'
        let (cv2, entry2) = section_index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:1");
        assert_eq!(entry2.end_cv().to_string(), "1:16");
        assert_eq!(entry2.start_index(), 30); // c
        assert_eq!(entry2.end_index(), 103); // ¬p
        assert_eq!(entry2.reason_marker(), "s1/c");
        assert_eq!(entry2.section_name(), "David learns about Sha'ul's death");

        // 3 1:2 s1='David's song of mourning'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:17");
        assert_eq!(entry3.end_cv().to_string(), "1:27");
        assert_eq!(entry3.start_index(), 104); // v=
        assert_eq!(entry3.end_index(), 231);
        assert_eq!(entry3.reason_marker(), "s1");
        assert_eq!(entry3.section_name(), "David's song of mourning");

        // 4 21:1 s1='Natan brings rebuke to David'
        let (cv21, entry21) = section_index.index_data.get_index(21).unwrap();
        assert_eq!(cv21.to_string(), "12:1");
        assert_eq!(entry21.end_cv().to_string(), "12:15a");
        assert_eq!(entry21.start_index(), 1285);
        assert_eq!(entry21.end_index(), 1347);
        assert_eq!(entry21.reason_marker(), "s1/c");
        assert_eq!(entry21.section_name(), "Natan brings rebuke to David");

        // 5 12:15b s1='David's son dies'
        let (cv22, entry22) = section_index.index_data.get_index(22).unwrap();
        assert_eq!(cv22.to_string(), "12:15b");
        assert_eq!(entry22.end_cv().to_string(), "12:24a");
        assert_eq!(entry22.start_index(), 1348);
        assert_eq!(entry22.end_index(), 1393);
        assert_eq!(entry22.reason_marker(), "s1");
        assert_eq!(entry22.section_name(), "David's son dies");

        // // 6 2:10 s1='The people have been unfaithful'
        // let (cv6, entry6) = section_index.index_data.get_index(6).unwrap();
        // assert_eq!(cv6.to_string(), "2:10");
        // assert_eq!(entry6.end_cv().to_string(), "2:16");
        // assert_eq!(entry6.start_index(), 133);
        // assert_eq!(entry6.end_index(), 162);
        // assert_eq!(entry6.reason_marker(), "s1");
        // assert_eq!(entry6.section_name(), "The people have been unfaithful");

        // // 7 2:19 s1='Judgement day is coming'
        // let (cv7, entry7) = section_index.index_data.get_index(7).unwrap();
        // assert_eq!(cv7.to_string(), "2:17");
        // assert_eq!(entry7.end_cv().to_string(), "3:5");
        // assert_eq!(entry7.start_index(), 163);
        // assert_eq!(entry7.end_index(), 193);
        // assert_eq!(entry7.reason_marker(), "s1");
        // assert_eq!(entry7.section_name(), "Judgement day is coming");

        // // 8 3:6 s1='Giving a tenth'
        // let (cv8, entry8) = section_index.index_data.get_index(8).unwrap();
        // assert_eq!(cv8.to_string(), "3:6");
        // assert_eq!(entry8.end_cv().to_string(), "3:12");
        // assert_eq!(entry8.start_index(), 194);
        // assert_eq!(entry8.end_index(), 220);
        // assert_eq!(entry8.reason_marker(), "s1");
        // assert_eq!(entry8.section_name(), "Giving a tenth");

        // // 9 3:13 s1='God promises mercy for some'
        // let (cv9, entry9) = section_index.index_data.get_index(9).unwrap();
        // assert_eq!(cv9.to_string(), "3:13");
        // assert_eq!(entry9.end_cv().to_string(), "3:18");
        // assert_eq!(entry9.start_index(), 221);
        // assert_eq!(entry9.end_index(), 247);
        // assert_eq!(entry9.reason_marker(), "s1");
        // assert_eq!(entry9.section_name(), "God promises mercy for some");
    }
}
