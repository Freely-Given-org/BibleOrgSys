//! Section-based index for table of contents navigation.
//!
//! This module provides:
//! - `SectionIndexEntry` - Index entry for a single section
//! - `InternalBibleBookSectionIndex` - Section index for a book

use compact_str::CompactString;
use indexmap::IndexMap;
use num_format::{Locale, ToFormattedString};

use crate::chapter_verse::ChapterVerse;
use crate::entry_extras::InternalBibleEntryList;
use crate::error::LookupError;

/// Markers that can define section boundaries.
const SECTION_MARKERS: &[&str] = &[
    "is1", // Introductory sections
    "ms1", "ms2", "ms3", // Major sections
    "s1",  // Section headings
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
    /// Note that "c/s1" should only occur for Psalms (where each chapter is automatically a new section) and for chapter 1 of any book if there's no initial section heading
    reason_marker: CompactString,
    /// The section name/heading text.
    section_name: CompactString,
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
        section_name: impl Into<CompactString>,
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
#[derive(Debug, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleBookSectionIndex {
    /// Name of the work/Bible.
    work_name: CompactString,
    /// Three-letter book code.
    bos_book_code: CompactString,
    /// The section -> entry mapping (keyed by starting C:V).
    index_data: IndexMap<ChapterVerse, SectionIndexEntry>,
    /// The processed entries this index references.
    entries: InternalBibleEntryList,
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
            entries: InternalBibleEntryList::new(),
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
            .entries
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
            .entries
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
        &self.entries
    }

    /// Build the section index from processed entries.
    ///
    /// This analyzes the entry list and creates section boundaries
    /// based on section heading markers.
    pub fn build(&mut self, entries: InternalBibleEntryList) -> Result<(), crate::error::IndexError> {
        if entries.is_empty() {
            return Err(crate::error::IndexError::EmptyEntries);
        }
        log::info!(
            "Building section index for {} {} from {} entries…",
            self.work_name(),
            self.bos_book_code(),
            entries.len().to_formatted_string(&Locale::en)
        );

        self.entries = entries;
        self.index_data.clear();

        let mut current_chapter_num_str = CompactString::from("-1");
        let mut current_verse_num_str = CompactString::from("0");
        let mut pending: Option<PendingSection> = None;
        let mut context: Vec<CompactString> = Vec::new();
        // Saved state from the most recent `c` marker, cleared when a `v` absorbs it.
        // (end_chapter, end_verse, end_index) — used so a following section marker
        // closes the previous section before the chapter change, not after.
        let mut pre_chapter_change: Option<(CompactString, CompactString, u16)> = None;

        for (i, entry) in self.entries.iter().enumerate() {
            let marker = entry.marker();

            if marker == "v" {
                // Put the most common one first
                let verse_text = entry.clean_text();
                let verse_num = verse_text.split_whitespace().next().unwrap_or(verse_text);
                current_verse_num_str = CompactString::from(verse_num);
                // A verse after a chapter change means the section spans the boundary
                pre_chapter_change = None;
                if let Some(section) = pending.as_mut() {
                    if section.start_cv.is_none() {
                        section.start_cv = Some(ChapterVerse::new(
                            current_chapter_num_str.as_str(),
                            current_verse_num_str.as_str(),
                        ));
                    }
                    // A verse marker ends the "transition" state from a `c` marker;
                    // subsequent headings should start new sections.
                    section.is_transition = false;
                }
                log::trace!(
                    "  Build {} section index: at entry #{} {} {}:{}",
                    self.work_name(),
                    i,
                    self.bos_book_code(),
                    current_chapter_num_str,
                    current_verse_num_str
                );
            } else if marker == "id" {
                pending = Some(PendingSection {
                    start_cv: Some(ChapterVerse::new(
                        current_chapter_num_str.as_str(),
                        current_verse_num_str.as_str(),
                    )),
                    start_index: i.try_into().unwrap(),
                    reason: CompactString::from("Headers"),
                    name: CompactString::from(entry.clean_text().chars().take(3).collect::<String>()),
                    is_transition: false,
                });
            }
            // Check for section markers (but chapter markers are only section markers if they appear in intro or content-transition contexts or in Psalms, handled above)
            else if is_section_marker(marker) {
                log::trace!(
                    "  Build {} {} section index: found section marker at entry #{} {}={} with {}:{}",
                    self.work_name(),
                    self.bos_book_code(),
                    i,
                    marker,
                    entry.clean_text(),
                    current_chapter_num_str,
                    current_verse_num_str
                );
                if marker == "c" {
                    let was_intro = current_chapter_num_str == "-1";
                    if was_intro || self.bos_book_code() == "PSA" {
                        // Transitioning from intro to content (or new Psalm): close the previous section
                        if let Some(mut section) = pending.take() {
                            if section.start_cv.is_none() {
                                section.start_cv = Some(ChapterVerse::new(
                                    current_chapter_num_str.as_str(),
                                    current_verse_num_str.as_str(),
                                ));
                            }
                            let end_idx = (i as u16).saturating_sub(1);
                            let end_v_intro;
                            let (end_ch, end_v) = if was_intro {
                                end_v_intro = end_idx.to_string();
                                ("-1", end_v_intro.as_str())
                            } else {
                                (current_chapter_num_str.as_str(), current_verse_num_str.as_str())
                            };
                            let (cv, entry) = section.into_closed(end_ch, end_v, end_idx, context.clone());
                            self.index_data.insert(cv, entry);
                            context.clear();
                        }
                        // Start a transition section at this c marker (will be merged with next section heading)
                        pending = Some(PendingSection {
                            start_cv: None,
                            start_index: i.try_into().unwrap(),
                            reason: CompactString::from("c"),
                            name: CompactString::from(""),
                            is_transition: true,
                        });
                    } else {
                        // Content chapter boundary: save state so a following section marker
                        // can close the previous section at the right point
                        pre_chapter_change = Some((
                            current_chapter_num_str.clone(),
                            current_verse_num_str.clone(),
                            (i as u16).saturating_sub(1),
                        ));
                    }

                    current_chapter_num_str = CompactString::from(entry.clean_text());
                    current_verse_num_str = CompactString::from("0");
                } else if current_chapter_num_str == "-1" {
                    // In intro mode: close previous section with -1:(i-1) addressing
                    if let Some(mut section) = pending.take() {
                        if section.start_cv.is_none() {
                            section.start_cv = Some(ChapterVerse::new(
                                current_chapter_num_str.as_str(),
                                current_verse_num_str.as_str(),
                            ));
                        }
                        let end_idx = (i as u16).saturating_sub(1);
                        let (cv, entry) = section.into_closed("-1", &end_idx.to_string(), end_idx, context.clone());
                        self.index_data.insert(cv, entry);
                        context.clear();
                    }
                    // Start new intro section with -1:i addressing
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new("-1", i.to_string())),
                        start_index: i.try_into().unwrap(),
                        reason: CompactString::from(marker),
                        name: CompactString::from(entry.clean_text()),
                        is_transition: false,
                    });
                } else if pending.as_ref().is_some_and(|s| s.is_transition) {
                    // Merge heading into the transition section started by the c marker
                    let section = pending.as_mut().unwrap();
                    let marker_prefix = if self.bos_book_code() == "PSA" { "c/" } else { "" };
                    section.reason = CompactString::from(format!("{}{}", marker_prefix, marker));
                    section.name = CompactString::from(entry.clean_text());
                    section.is_transition = false;
                } else {
                    // Normal content: close previous section and start new one.
                    // If a `c` marker preceded this section marker without an
                    // intervening verse, close at the pre-chapter-change point
                    // so the `c` entry belongs to the new section.
                    let chapter_boundary = pre_chapter_change.take();
                    if let Some(mut section) = pending.take() {
                        if section.start_cv.is_none() {
                            section.start_cv = Some(ChapterVerse::new(
                                current_chapter_num_str.as_str(),
                                current_verse_num_str.as_str(),
                            ));
                        }
                        let (end_ch, end_v, end_idx) = match &chapter_boundary {
                            Some((ch, v, idx)) => (ch.as_str(), v.as_str(), *idx),
                            None => (
                                current_chapter_num_str.as_str(),
                                current_verse_num_str.as_str(),
                                (i as u16).saturating_sub(1),
                            ),
                        };
                        let (cv, entry) = section.into_closed(end_ch, end_v, end_idx, context.clone());
                        self.index_data.insert(cv, entry);
                        context.clear();
                    }
                    // New section starts at the `c` entry if there was a chapter
                    // change, otherwise at this section marker
                    let (start_index, reason): (u16, CompactString) = match &chapter_boundary {
                        Some((_, _, idx)) => {
                            let marker_prefix = if self.bos_book_code() == "PSA" { "c/" } else { "" };
                            (idx + 1, CompactString::from(format!("{}{}", marker_prefix, marker)))
                        }
                        None => (i.try_into().unwrap(), CompactString::from(marker)),
                    };
                    pending = Some(PendingSection {
                        start_cv: None,
                        start_index,
                        reason,
                        name: CompactString::from(entry.clean_text()),
                        is_transition: false,
                    });
                }
            }

            // Track context (simplified)
            /*
            if !crate::markers::is_end_marker(marker) {
                if crate::markers::paragraph_markers::is_paragraph(marker) {
                    // Reset paragraph context
                    context.retain(|m| !crate::markers::paragraph_markers::is_paragraph(m));
                    context.push(CompactString::from(marker));
                }
            }*/
        }

        // Close final section
        // If there's a pending section that hasn't had its start CV resolved yet, it means we never encountered a verse marker to set the start CV. In this case, we can use the current chapter and verse (which would be the last ones seen in the entries) as the start CV for this section.
        // This can happen if the last section in the book is defined by a heading marker and there are no verses after it. In that case, we want the section to start at the last known chapter and verse rather than being left without a start CV.
        // This only happens in OEB MRK for an alternative special ending (but it does make this logic more robust in general).
        if let Some(section) = pending.as_mut().filter(|s| s.start_cv.is_none()) {
            section.start_cv = Some(ChapterVerse::new(
                current_chapter_num_str.as_str(),
                current_verse_num_str.as_str(),
            ));
        }
        if let Some(section) = pending {
            let (cv, entry) = section.into_closed(
                current_chapter_num_str.as_str(),
                current_verse_num_str.as_str(),
                (self.entries.len() as u16).saturating_sub(1),
                context,
            );
            self.index_data.insert(cv, entry);
        }

        self.indexed = true;
        Ok(())
    }
}

/// Tracks a section being built before it's finalized and inserted into the index.
struct PendingSection {
    /// `None` when the start CV isn't known yet (heading appeared before first verse).
    start_cv: Option<ChapterVerse>,
    start_index: u16,
    reason: CompactString,
    name: CompactString,
    /// This section was started by a `c` marker (intro-to-content transition)
    /// and should merge with the next section heading rather than being closed.
    is_transition: bool,
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

    fn create_test_entries_1() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "GEN Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("ide", "UTF-8")); // 2

        // Section 2 (Intro)
        entries.push(InternalBibleEntry::simple("is1", "Introduction to Genesis")); // 3
        entries.push(InternalBibleEntry::simple("ip", "An introductory paragraph.")); // 4

        // Section 3
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("s1", "The Creation")); // 6
        entries.push(InternalBibleEntry::simple("p", "")); // 7
        entries.push(InternalBibleEntry::simple("v", "1")); // 8
        entries.push(InternalBibleEntry::simple("v~", "In the beginning...")); // 9
        entries.push(InternalBibleEntry::simple("v", "2")); // 10
        entries.push(InternalBibleEntry::simple("v~", "And the earth was without form...")); // 11
        entries.push(InternalBibleEntry::simple("¬c", "")); // 12

        // Section 4
        entries.push(InternalBibleEntry::simple("c", "2")); // 13
        entries.push(InternalBibleEntry::simple("nb", "")); // 14
        entries.push(InternalBibleEntry::simple("v", "1")); // 15
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of chapter 2...")); // 16
        entries.push(InternalBibleEntry::simple("s1", "The Fall")); // 17
        entries.push(InternalBibleEntry::simple("p", "")); // 18
        entries.push(InternalBibleEntry::simple("v", "2")); // 19
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of chapter 2...")); // 20
        entries.push(InternalBibleEntry::simple("v", "3")); // 21
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of chapter 2...")); // 22

        // Section 5
        entries.push(InternalBibleEntry::simple("c", "3")); // 23
        entries.push(InternalBibleEntry::simple("s1", "Chapter Three")); // 24
        entries.push(InternalBibleEntry::simple("rem", "/s1 Alternative heading")); // 25
        entries.push(InternalBibleEntry::simple("p", "")); // 26
        entries.push(InternalBibleEntry::simple("v", "1")); // 27
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of chapter 3...")); // 28
        entries.push(InternalBibleEntry::simple("v", "2")); // 29
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of chapter 3...")); // 30

        entries
    }

    #[test]
    fn test_build_section_index_1() {
        let mut index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        index.build(create_test_entries_1()).unwrap();
        log::trace!("Index1:{}", index);
        assert!(index.is_indexed());

        assert!(index.index_data.get_index(0).unwrap().0.to_string() == "-1:0"); // ID Header starts at -1:0
        assert!(index.index_data.get_index(0).unwrap().1.end_cv().to_string() == "-1:2"); // ID Header ends at -1:2
        assert!(index.index_data.get_index(0).unwrap().1.start_index() == 0); // starts at entry index 0
        assert!(index.index_data.get_index(0).unwrap().1.end_index() == 2); // ends at entry index 2
        assert!(index.index_data.get_index(0).unwrap().1.reason_marker() == "Headers");
        assert!(index.index_data.get_index(0).unwrap().1.section_name() == "GEN");

        assert!(index.index_data.get_index(1).unwrap().0.to_string() == "-1:3"); // starts at -1:3
        assert!(index.index_data.get_index(1).unwrap().1.end_cv().to_string() == "-1:4"); // ends at -1:4
        assert!(index.index_data.get_index(1).unwrap().1.start_index() == 3); // starts at entry index 3
        assert!(index.index_data.get_index(1).unwrap().1.end_index() == 4); // ends at entry index 4
        assert!(index.index_data.get_index(1).unwrap().1.reason_marker() == "is1");
        assert!(index.index_data.get_index(1).unwrap().1.section_name() == "Introduction to Genesis");

        assert!(index.index_data.get_index(2).unwrap().0.to_string() == "1:1"); // starts at 1:1
        assert!(index.index_data.get_index(2).unwrap().1.end_cv().to_string() == "2:1"); // ends at 2:1
        assert!(index.index_data.get_index(2).unwrap().1.start_index() == 5); // starts at entry index 5
        assert!(index.index_data.get_index(2).unwrap().1.end_index() == 16); // crosses chapters and ends at entry index 16
        assert!(index.index_data.get_index(2).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(2).unwrap().1.section_name() == "The Creation");

        assert!(index.index_data.get_index(3).unwrap().0.to_string() == "2:2"); // starts at 2:2
        assert!(index.index_data.get_index(3).unwrap().1.end_cv().to_string() == "2:3"); // ends at 2:3
        assert!(index.index_data.get_index(3).unwrap().1.start_index() == 17); // starts at entry index 17
        assert!(index.index_data.get_index(3).unwrap().1.end_index() == 22); // ends at entry index 22
        assert!(index.index_data.get_index(3).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(3).unwrap().1.section_name() == "The Fall");

        assert!(index.index_data.get_index(4).unwrap().0.to_string() == "3:1"); // starts at 3:1
        assert!(index.index_data.get_index(4).unwrap().1.end_cv().to_string() == "3:2"); // ends at 3:2
        assert!(index.index_data.get_index(4).unwrap().1.start_index() == 23); // starts at entry index 23 (the c marker)
        assert!(index.index_data.get_index(4).unwrap().1.end_index() == 30); // ends at entry index 30
        assert!(index.index_data.get_index(4).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(4).unwrap().1.section_name() == "Chapter Three");

        assert!(index.len() == 5); // Headers, is1, s1 (1/The Creation), s1 (Fall), s1 (3/Chapter Three)
    }

    fn create_test_entries_2() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "MRK Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("mt1", "Mark")); // 2

        // Section 2 Chapter begins WITHOUT a section heading (should be absorbed into the first section)
        entries.push(InternalBibleEntry::simple("c", "1")); // 3
        entries.push(InternalBibleEntry::simple("p", "")); // 4
        entries.push(InternalBibleEntry::simple("v", "1")); // 5
        entries.push(InternalBibleEntry::simple("v~", "First verse of Mark...")); // 6
        entries.push(InternalBibleEntry::simple("v", "2")); // 7
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Mark 1...")); // 8

        // Section 3
        entries.push(InternalBibleEntry::simple("s1", "First section heading")); // 9
        entries.push(InternalBibleEntry::simple("p", "")); // 10
        entries.push(InternalBibleEntry::simple("v", "3")); // 11
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of chapter 1...")); // 12
        entries.push(InternalBibleEntry::simple("v", "4")); // 13
        entries.push(InternalBibleEntry::simple("v~", "Verse 4 of chapter 1...")); // 14

        // Section 4
        entries.push(InternalBibleEntry::simple("s1", "First alternative ending to Mark")); // 15
        entries.push(InternalBibleEntry::simple("p", "")); // 16
        entries.push(InternalBibleEntry::simple("p~", "No verses here--just text...")); // 17

        // Section 5
        entries.push(InternalBibleEntry::simple("s1", "Second alternative ending to Mark")); // 18
        entries.push(InternalBibleEntry::simple("p", "")); // 19
        entries.push(InternalBibleEntry::simple("v", "9")); // 20
        entries.push(InternalBibleEntry::simple("v~", "Has verses here...")); // 21

        entries
    }

    #[test]
    fn test_build_section_index_2() {
        let mut index = InternalBibleBookSectionIndex::new("YSV", "MRK");
        index.build(create_test_entries_2()).unwrap();
        log::trace!("Index2:{}", index);
        assert!(index.is_indexed());

        assert!(index.index_data.get_index(0).unwrap().0.to_string() == "-1:0"); // ID Header starts at -1:0
        assert!(index.index_data.get_index(0).unwrap().1.end_cv().to_string() == "-1:2"); // ID Header ends at -1:2
        assert!(index.index_data.get_index(0).unwrap().1.start_index() == 0); // starts at entry index 0
        assert!(index.index_data.get_index(0).unwrap().1.end_index() == 2); // ends at entry index 2
        assert!(index.index_data.get_index(0).unwrap().1.reason_marker() == "Headers");
        assert!(index.index_data.get_index(0).unwrap().1.section_name() == "MRK");

        assert!(index.index_data.get_index(1).unwrap().0.to_string() == "1:1"); // starts at 1:1
        assert!(index.index_data.get_index(1).unwrap().1.end_cv().to_string() == "1:2"); // ends at 1:2
        assert!(index.index_data.get_index(1).unwrap().1.start_index() == 3); // starts at entry index 3
        assert!(index.index_data.get_index(1).unwrap().1.end_index() == 8); // ends at entry index 8
        assert!(index.index_data.get_index(1).unwrap().1.reason_marker() == "c");
        assert!(index.index_data.get_index(1).unwrap().1.section_name() == "");

        assert!(index.index_data.get_index(2).unwrap().0.to_string() == "1:3"); // starts at 1:3
        assert!(index.index_data.get_index(2).unwrap().1.end_cv().to_string() == "1:4"); // ends at 1:4
        assert!(index.index_data.get_index(2).unwrap().1.start_index() == 9); // starts at entry index 9
        assert!(index.index_data.get_index(2).unwrap().1.end_index() == 14); // ends at entry index 14
        assert!(index.index_data.get_index(2).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(2).unwrap().1.section_name() == "First section heading");

        assert!(index.index_data.get_index(3).unwrap().0.to_string() == "1:4"); // starts at 1:4
        assert!(index.index_data.get_index(3).unwrap().1.end_cv().to_string() == "1:4"); // ends at 1:4
        assert!(index.index_data.get_index(3).unwrap().1.start_index() == 15); // starts at entry index 15
        assert!(index.index_data.get_index(3).unwrap().1.end_index() == 17); // ends at entry index 17
        assert!(index.index_data.get_index(3).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(3).unwrap().1.section_name() == "First alternative ending to Mark");

        assert!(index.index_data.get_index(4).unwrap().0.to_string() == "1:9"); // starts at 1:4
        assert!(index.index_data.get_index(4).unwrap().1.end_cv().to_string() == "1:9"); // ends at 1:4
        assert!(index.index_data.get_index(4).unwrap().1.start_index() == 18); // starts at entry index 18
        assert!(index.index_data.get_index(4).unwrap().1.end_index() == 21); // ends at entry index 21
        assert!(index.index_data.get_index(4).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(4).unwrap().1.section_name() == "Second alternative ending to Mark");

        assert!(index.len() == 5); // Headers, c, s1, s1 x2 (at end)
    }

    fn create_psa_test_entries() -> InternalBibleEntryList {
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
    fn test_build_section_index_psa() {
        let mut index = InternalBibleBookSectionIndex::new("ZSV", "PSA");
        index.build(create_psa_test_entries()).unwrap();
        log::trace!("PSA index:{}", index);
        assert!(index.is_indexed());

        // 0: Headers
        assert!(index.index_data.get_index(0).unwrap().0.to_string() == "-1:0");
        assert!(index.index_data.get_index(0).unwrap().1.end_cv().to_string() == "-1:2");
        assert!(index.index_data.get_index(0).unwrap().1.start_index() == 0); // starts at entry index 0
        assert!(index.index_data.get_index(0).unwrap().1.end_index() == 2); // ends at entry index 2
        assert!(index.index_data.get_index(0).unwrap().1.reason_marker() == "Headers");
        assert!(index.index_data.get_index(0).unwrap().1.section_name() == "PSA");

        // 1: Intro
        assert!(index.index_data.get_index(1).unwrap().0.to_string() == "-1:3");
        assert!(index.index_data.get_index(1).unwrap().1.end_cv().to_string() == "-1:4");
        assert!(index.index_data.get_index(1).unwrap().1.start_index() == 3); // starts at entry index 3
        assert!(index.index_data.get_index(1).unwrap().1.end_index() == 4); // ends at entry index 4
        assert!(index.index_data.get_index(1).unwrap().1.reason_marker() == "is1");
        assert!(index.index_data.get_index(1).unwrap().1.section_name() == "Introduction to Psalms");

        // 2: Chapter 1
        assert!(index.index_data.get_index(2).unwrap().0.to_string() == "1:1");
        assert!(index.index_data.get_index(2).unwrap().1.end_cv().to_string() == "1:2");
        assert!(index.index_data.get_index(2).unwrap().1.start_index() == 5); // starts at entry index 5
        assert!(index.index_data.get_index(2).unwrap().1.end_index() == 10); // ends at entry index 10
        assert!(index.index_data.get_index(2).unwrap().1.reason_marker() == "c");
        assert!(index.index_data.get_index(2).unwrap().1.section_name() == "");

        // 3: Mid-chapter heading
        assert!(index.index_data.get_index(3).unwrap().0.to_string() == "1:3");
        assert!(index.index_data.get_index(3).unwrap().1.end_cv().to_string() == "1:4");
        assert!(index.index_data.get_index(3).unwrap().1.start_index() == 11); // starts at entry index 11
        assert!(index.index_data.get_index(3).unwrap().1.end_index() == 16); // ends at entry index 16
        assert!(index.index_data.get_index(3).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(3).unwrap().1.section_name() == "First section heading mid-chapter");

        // 4: Chapter 2
        assert!(index.index_data.get_index(4).unwrap().0.to_string() == "2:1");
        assert!(index.index_data.get_index(4).unwrap().1.end_cv().to_string() == "2:2");
        assert!(index.index_data.get_index(4).unwrap().1.start_index() == 17); // starts at entry index 17
        assert!(index.index_data.get_index(4).unwrap().1.end_index() == 22); // ends at entry index 22
        assert!(index.index_data.get_index(4).unwrap().1.reason_marker() == "c");
        assert!(index.index_data.get_index(4).unwrap().1.section_name() == "");

        // 5: Chapter 3 (merged c/s1)
        assert!(index.index_data.get_index(5).unwrap().0.to_string() == "3:1");
        assert!(index.index_data.get_index(5).unwrap().1.end_cv().to_string() == "3:2");
        assert!(index.index_data.get_index(5).unwrap().1.start_index() == 23); // starts at entry index 23
        assert!(index.index_data.get_index(5).unwrap().1.end_index() == 29); // ends at entry index 29
        assert!(index.index_data.get_index(5).unwrap().1.reason_marker() == "c/s1");
        assert!(index.index_data.get_index(5).unwrap().1.section_name() == "Psa 3 section heading");

        assert!(index.len() == 6); // Headers, is1, c, s1, c, c/s1 (merged)
    }

    #[test]
    fn test_table_of_contents() {
        let mut index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        index.build(create_test_entries_1()).unwrap();

        let toc = index.table_of_contents();
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
        let mut index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        index.build(create_test_entries_1()).unwrap();

        // Get first section
        if let Some((cv, _)) = index.iter().next() {
            let entries = index.get_section_entries(cv).unwrap();
            assert!(!entries.is_empty());
        }
    }

    #[test]
    fn test_oet_rv_haggai_section_index_build() {
        let content = include_str!("OET-RV_HAG.ESFM");
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
        let entries_final = crate::processing::process_lines(raw_lines, "HAG", "OET-RV", &options);

        let mut index = InternalBibleBookSectionIndex::new("OET-RV", "HAG");
        index.build(entries_final).unwrap();

        // It should give the following seven entries:
        //    0 -1:0 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:12 ix=0–12 (cnt=13) Headers='HAG'
        //    1 -1:13 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:22 ix=13–22 (cnt=10) is1='Introduction'
        //    2 1:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:11 ix=24–69 (cnt=46) s1='God's command to rebuild the temple'
        //    3 1:12 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:15 ix=70–87 (cnt=18) s1='The people start rebuilding'
        //    4 2:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:9 ix=88–119 (cnt=32) s1='The splendour of the new temple'
        //    5 2:10 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:19 ix=120–164 (cnt=45) s1='Haggai consults the priests'
        //    6 2:20 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:23 ix=165–182 (cnt=18) s1='God's promise to Zerubavel'
        assert_eq!(index.len(), 7);

        // 0 -1:0 Headers='HAG'
        let (cv0, entry0) = index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:12");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 12);
        assert_eq!(entry0.reason_marker(), "Headers");
        assert_eq!(entry0.section_name(), "HAG");

        // 1 -1:13 is1='Introduction'
        let (cv1, entry1) = index.index_data.get_index(1).unwrap();
        assert_eq!(cv1.to_string(), "-1:13");
        assert_eq!(entry1.end_cv().to_string(), "-1:22");
        assert_eq!(entry1.start_index(), 13);
        assert_eq!(entry1.end_index(), 22);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:1 s1='God\'s command to rebuild the temple'
        let (cv2, entry2) = index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:1");
        assert_eq!(entry2.end_cv().to_string(), "1:11");
        assert_eq!(entry2.start_index(), 24);
        assert_eq!(entry2.end_index(), 69);
        assert_eq!(entry2.reason_marker(), "s1");
        assert_eq!(entry2.section_name(), "God's command to rebuild the temple");

        // 3 1:12 s1='The people start rebuilding'
        let (cv3, entry3) = index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:12");
        assert_eq!(entry3.end_cv().to_string(), "1:15");
        assert_eq!(entry3.start_index(), 70);
        assert_eq!(entry3.end_index(), 87);
        assert_eq!(entry3.reason_marker(), "s1");
        assert_eq!(entry3.section_name(), "The people start rebuilding");

        // 4 2:1 s1='The splendour of the new temple'
        let (cv4, entry4) = index.index_data.get_index(4).unwrap();
        assert_eq!(cv4.to_string(), "2:1");
        assert_eq!(entry4.end_cv().to_string(), "2:9");
        assert_eq!(entry4.start_index(), 88);
        assert_eq!(entry4.end_index(), 119);
        assert_eq!(entry4.reason_marker(), "s1");
        assert_eq!(entry4.section_name(), "The splendour of the new temple");

        // 5 2:10 s1='Haggai consults the priests'
        let (cv5, entry5) = index.index_data.get_index(5).unwrap();
        assert_eq!(cv5.to_string(), "2:10");
        assert_eq!(entry5.end_cv().to_string(), "2:19");
        assert_eq!(entry5.start_index(), 120);
        assert_eq!(entry5.end_index(), 164);
        assert_eq!(entry5.reason_marker(), "s1");
        assert_eq!(entry5.section_name(), "Haggai consults the priests");

        // 6 2:20 s1='God\'s promise to Zerubavel'
        let (cv6, entry6) = index.index_data.get_index(6).unwrap();
        assert_eq!(cv6.to_string(), "2:20");
        assert_eq!(entry6.end_cv().to_string(), "2:23");
        assert_eq!(entry6.start_index(), 165);
        assert_eq!(entry6.end_index(), 182);
        assert_eq!(entry6.reason_marker(), "s1");
        assert_eq!(entry6.section_name(), "God's promise to Zerubavel");
    }
}
