//! Section-based index for table of contents navigation.
//!
//! This module provides:
//! - `SectionIndexEntry` - Index entry for a single section
//! - `InternalBibleBookSectionIndex` - Section index for a book

use compact_str::CompactString;
use indexmap::IndexMap;

use crate::chapter_verse::ChapterVerse;
use crate::entry_extra_list::InternalBibleEntryList;
use crate::error::LookupError;

/// Markers that define section boundaries.
const SECTION_MARKERS: &[&str] = &[
    "is1", // Introductory sections
    "ms1", "ms2", "ms3", // Major sections
    "s1",  // Section headings
           // "c", // Chapters
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
    /// The marker that started this section (e.g., "s1", "c").
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
        ChapterVerse::new(
            self.end_chapter_num_str.as_str(),
            self.end_verse_num_str.as_str(),
        )
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
    book_code: CompactString,
    /// The section -> entry mapping (keyed by starting C:V).
    index_data: IndexMap<ChapterVerse, SectionIndexEntry>,
    /// The processed entries this index references.
    entries: InternalBibleEntryList,
    /// Whether the index has been built.
    indexed: bool,
}

impl InternalBibleBookSectionIndex {
    /// Create a new empty section index.
    pub fn new(work_name: impl Into<CompactString>, book_code: impl Into<CompactString>) -> Self {
        Self {
            work_name: work_name.into(),
            book_code: book_code.into(),
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
    pub fn book_code(&self) -> &str {
        &self.book_code
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
    pub fn get_section_entries(
        &self,
        cv: &ChapterVerse,
    ) -> Result<InternalBibleEntryList, LookupError> {
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
    pub fn build(
        &mut self,
        entries: InternalBibleEntryList,
    ) -> Result<(), crate::error::IndexError> {
        if entries.is_empty() {
            return Err(crate::error::IndexError::EmptyEntries);
        }

        self.entries = entries;
        self.index_data.clear();

        let mut current_chapter_num_str = CompactString::from("-1");
        let mut current_verse_num_str = CompactString::from("0");
        let mut pending: Option<PendingSection> = None;
        let mut context: Vec<CompactString> = Vec::new();

        for (i, entry) in self.entries.iter().enumerate() {
            let marker = entry.marker();

            if marker == "id" {
                pending = Some(PendingSection {
                    start_cv: Some(ChapterVerse::new(
                        current_chapter_num_str.as_str(),
                        current_verse_num_str.as_str(),
                    )),
                    start_index: i.try_into().unwrap(),
                    reason: CompactString::from("Headers"),
                    name: CompactString::from(
                        entry.clean_text().chars().take(3).collect::<String>(),
                    ),
                    is_transition: false,
                });
            }
            // Track current chapter/verse
            else if marker == "c" {
                let was_intro = current_chapter_num_str == "-1";

                // Transitioning from intro to content: close the intro section
                if was_intro {
                    if let Some(section) = pending.take() {
                        let end_idx = (i as u16).saturating_sub(1);
                        let (cv, entry) = section.into_closed(
                            "-1",
                            &end_idx.to_string(),
                            end_idx,
                            context.clone(),
                        );
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
                }

                current_chapter_num_str = CompactString::from(entry.clean_text());
                current_verse_num_str = CompactString::from("0");

                // Resolve pending section's start_cv (but not for intro->content transitions
                // where we want to wait for the first verse)
                if !was_intro
                    && let Some(section) = pending.as_mut().filter(|s| s.start_cv.is_none())
                {
                    section.start_cv = Some(ChapterVerse::new(
                        current_chapter_num_str.as_str(),
                        current_verse_num_str.as_str(),
                    ));
                }
            } else if marker == "v" {
                let verse_text = entry.clean_text();
                let verse_num = verse_text.split_whitespace().next().unwrap_or(verse_text);
                current_verse_num_str = CompactString::from(verse_num);
                if let Some(section) = pending.as_mut().filter(|s| s.start_cv.is_none()) {
                    section.start_cv = Some(ChapterVerse::new(
                        current_chapter_num_str.as_str(),
                        current_verse_num_str.as_str(),
                    ));
                }
            }
            // Check for section markers
            else if is_section_marker(marker) {
                if current_chapter_num_str == "-1" {
                    // In intro mode: close previous section with -1:(i-1) addressing
                    if let Some(section) = pending.take() {
                        let end_idx = (i as u16).saturating_sub(1);
                        let (cv, entry) = section.into_closed(
                            "-1",
                            &end_idx.to_string(),
                            end_idx,
                            context.clone(),
                        );
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
                    section.reason = CompactString::from(marker);
                    section.name = CompactString::from(entry.clean_text());
                    section.is_transition = false;
                } else {
                    // Normal content: close previous section and start new one
                    if let Some(section) = pending.take() {
                        let end_idx = (i as u16).saturating_sub(1);
                        let (cv, entry) = section.into_closed(
                            current_chapter_num_str.as_str(),
                            current_verse_num_str.as_str(),
                            end_idx,
                            context.clone(),
                        );
                        self.index_data.insert(cv, entry);
                        context.clear();
                    }
                    pending = Some(PendingSection {
                        start_cv: None,
                        start_index: i.try_into().unwrap(),
                        reason: CompactString::from(marker),
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
        let start_cv = self
            .start_cv
            .expect("section closed before start CV was resolved");
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
            self.work_name, self.book_code
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

    fn create_test_entries() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "GEN Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("ide", "UTF-8")); // 2

        // Section 2 (Intro)
        entries.push(InternalBibleEntry::simple("is1", "Introduction to Genesis")); // 3
        entries.push(InternalBibleEntry::simple(
            "ip",
            "An introductory paragraph.",
        )); // 4

        // Section 3
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("s1", "The Creation")); // 6
        entries.push(InternalBibleEntry::simple("p", "")); // 7
        entries.push(InternalBibleEntry::simple("v", "1")); // 8
        entries.push(InternalBibleEntry::simple("v~", "In the beginning...")); // 9
        entries.push(InternalBibleEntry::simple("v", "2")); // 10
        entries.push(InternalBibleEntry::simple(
            "v~",
            "And the earth was without form...",
        )); // 11
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

        entries
    }

    #[test]
    fn test_build_section_index() {
        let mut index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        index.build(create_test_entries()).unwrap();
        print!("{}", index);
        assert!(index.is_indexed());
        assert!(index.len() == 4); // Headers, Intro, Creation, Fall

        assert!(index.index_data.get_index(0).unwrap().0.to_string() == "-1:0"); // ID Header starts at -1:0
        assert!(
            index
                .index_data
                .get_index(0)
                .unwrap()
                .1
                .end_cv()
                .to_string()
                == "-1:2"
        ); // ID Header ends at -1:2
        assert!(index.index_data.get_index(0).unwrap().1.start_index() == 0); // starts at entry index 0
        assert!(index.index_data.get_index(0).unwrap().1.end_index() == 2); // ends at entry index 2
        assert!(index.index_data.get_index(0).unwrap().1.reason_marker() == "Headers");
        assert!(index.index_data.get_index(0).unwrap().1.section_name() == "GEN");

        assert!(index.index_data.get_index(1).unwrap().0.to_string() == "-1:3"); // starts at -1:3
        assert!(
            index
                .index_data
                .get_index(1)
                .unwrap()
                .1
                .end_cv()
                .to_string()
                == "-1:4"
        ); // ends at -1:4
        assert!(index.index_data.get_index(1).unwrap().1.start_index() == 3); // starts at entry index 3
        assert!(index.index_data.get_index(1).unwrap().1.end_index() == 4); // ends at entry index 4
        assert!(index.index_data.get_index(1).unwrap().1.reason_marker() == "is1");
        assert!(
            index.index_data.get_index(1).unwrap().1.section_name() == "Introduction to Genesis"
        );

        assert!(index.index_data.get_index(2).unwrap().0.to_string() == "1:1"); // starts at 1:1
        assert!(
            index
                .index_data
                .get_index(2)
                .unwrap()
                .1
                .end_cv()
                .to_string()
                == "2:1"
        ); // ends at 2:1
        assert!(index.index_data.get_index(2).unwrap().1.start_index() == 5); // starts at entry index 5
        assert!(index.index_data.get_index(2).unwrap().1.end_index() == 16); // ends at entry index 16
        assert!(index.index_data.get_index(2).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(2).unwrap().1.section_name() == "The Creation");

        assert!(index.index_data.get_index(3).unwrap().0.to_string() == "2:2"); // starts at 2:2
        assert!(
            index
                .index_data
                .get_index(3)
                .unwrap()
                .1
                .end_cv()
                .to_string()
                == "2:3"
        ); // ends at 2:3
        assert!(index.index_data.get_index(3).unwrap().1.start_index() == 17); // starts at entry index 17
        assert!(index.index_data.get_index(3).unwrap().1.end_index() == 22); // ends at entry index 22
        assert!(index.index_data.get_index(3).unwrap().1.reason_marker() == "s1");
        assert!(index.index_data.get_index(3).unwrap().1.section_name() == "The Fall");
    }

    #[test]
    fn test_table_of_contents() {
        let mut index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        index.build(create_test_entries()).unwrap();

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
        index.build(create_test_entries()).unwrap();

        // Get first section
        if let Some((cv, _)) = index.iter().next() {
            let entries = index.get_section_entries(cv).unwrap();
            assert!(!entries.is_empty());
        }
    }
}
