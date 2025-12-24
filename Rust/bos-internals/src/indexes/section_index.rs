//! Section-based index for table of contents navigation.
//!
//! This module provides:
//! - `SectionIndexEntry` - Index entry for a single section
//! - `InternalBibleBookSectionIndex` - Section index for a book

use compact_str::CompactString;
use indexmap::IndexMap;

use crate::chapter_verse::ChapterVerse;
use crate::entry_list::InternalBibleEntryList;
use crate::error::LookupError;

/// Markers that define section boundaries.
const SECTION_MARKERS: &[&str] = &[
    "ms1", "ms2", "ms3", // Major sections
    "s", "s1", "s2", "s3", "s4", // Section headings
    "c", // Chapters
];

/// An entry in the section index.
///
/// Each entry represents a section (usually defined by a heading)
/// and contains the range of entries it covers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SectionIndexEntry {
    /// Chapter where this section ends.
    end_chapter: CompactString,
    /// Verse where this section ends.
    end_verse: CompactString,
    /// Index of the first entry for this section.
    start_index: usize,
    /// Index of the last entry for this section (inclusive).
    end_index: usize,
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
        start_index: usize,
        end_index: usize,
        reason_marker: impl Into<CompactString>,
        section_name: impl Into<CompactString>,
        context: Vec<CompactString>,
    ) -> Self {
        Self {
            end_chapter: end_chapter.into(),
            end_verse: end_verse.into(),
            start_index,
            end_index,
            reason_marker: reason_marker.into(),
            section_name: section_name.into(),
            context,
        }
    }

    /// Get the ending chapter:verse as a ChapterVerse.
    pub fn end_cv(&self) -> ChapterVerse {
        ChapterVerse::new(self.end_chapter.as_str(), self.end_verse.as_str())
    }

    /// Get the ending chapter.
    #[inline]
    pub fn end_chapter(&self) -> &str {
        &self.end_chapter
    }

    /// Get the ending verse.
    #[inline]
    pub fn end_verse(&self) -> &str {
        &self.end_verse
    }

    /// Get the starting entry index.
    #[inline]
    pub fn start_index(&self) -> usize {
        self.start_index
    }

    /// Get the ending entry index (inclusive).
    #[inline]
    pub fn end_index(&self) -> usize {
        self.end_index
    }

    /// Get the count of entries in this section.
    #[inline]
    pub fn entry_count(&self) -> usize {
        self.end_index + 1 - self.start_index
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
            "SectionEntry({} [{}:{}-{}] {:?})",
            self.reason_marker,
            self.start_index,
            self.end_index,
            self.end_cv(),
            self.section_name
        )
    }
}

/// Index for section-based lookup in a Bible book.
///
/// This index maps section starting points (C:V) to section entries,
/// useful for table of contents navigation and section-based access.
#[derive(Debug)]
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
    pub fn get_section_entries(&self, cv: &ChapterVerse) -> Result<InternalBibleEntryList, LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }

        let entry = self
            .index_data
            .get(cv)
            .ok_or_else(|| LookupError::SectionNotFound(cv.clone()))?;

        Ok(self.entries.slice(entry.start_index, entry.end_index + 1))
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

        let entries = self.entries.slice(entry.start_index, entry.end_index + 1);
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

        self.entries = entries;
        self.index_data.clear();

        let mut current_chapter = CompactString::from("0");
        let mut current_verse = CompactString::from("0");
        let mut section_start: Option<(ChapterVerse, usize, CompactString, CompactString)> = None;
        let mut context: Vec<CompactString> = Vec::new();

        for (i, entry) in self.entries.iter().enumerate() {
            let marker = entry.marker();

            // Track current chapter/verse
            if marker == "c" {
                current_chapter = CompactString::from(entry.clean_text());
                current_verse = CompactString::from("0");
            } else if marker == "v" {
                let verse_text = entry.clean_text();
                let verse_num = verse_text.split_whitespace().next().unwrap_or(verse_text);
                current_verse = CompactString::from(verse_num);
            }

            // Check for section markers
            if is_section_marker(marker) {
                // Close previous section
                if let Some((start_cv, start_idx, reason, name)) = section_start.take() {
                    let entry = SectionIndexEntry::new(
                        current_chapter.as_str(),
                        current_verse.as_str(),
                        start_idx,
                        i.saturating_sub(1),
                        reason,
                        name,
                        context.clone(),
                    );
                    self.index_data.insert(start_cv, entry);
                }

                // Start new section
                let section_name = entry.clean_text().to_string();
                let start_cv = ChapterVerse::new(current_chapter.as_str(), current_verse.as_str());
                section_start = Some((
                    start_cv,
                    i,
                    CompactString::from(marker),
                    CompactString::from(section_name),
                ));
            }

            // Track context (simplified)
            if !crate::markers::is_end_marker(marker) {
                if crate::markers::paragraph_markers::is_paragraph(marker) {
                    // Reset paragraph context
                    context.retain(|m| !crate::markers::paragraph_markers::is_paragraph(m));
                    context.push(CompactString::from(marker));
                }
            }
        }

        // Close final section
        if let Some((start_cv, start_idx, reason, name)) = section_start {
            let entry = SectionIndexEntry::new(
                current_chapter.as_str(),
                current_verse.as_str(),
                start_idx,
                self.entries.len() - 1,
                reason,
                name,
                context,
            );
            self.index_data.insert(start_cv, entry);
        }

        self.indexed = true;
        Ok(())
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

        // Section 1
        entries.push(InternalBibleEntry::simple("s1", "The Creation"));
        entries.push(InternalBibleEntry::simple("c", "1"));
        entries.push(InternalBibleEntry::simple("p", ""));
        entries.push(InternalBibleEntry::simple("v", "1"));
        entries.push(InternalBibleEntry::simple("v~", "In the beginning..."));

        // Section 2
        entries.push(InternalBibleEntry::simple("s1", "The Fall"));
        entries.push(InternalBibleEntry::simple("c", "3"));
        entries.push(InternalBibleEntry::simple("v", "1"));
        entries.push(InternalBibleEntry::simple("v~", "Now the serpent..."));

        entries
    }

    #[test]
    fn test_build_section_index() {
        let mut index = InternalBibleBookSectionIndex::new("ESV", "GEN");
        index.build(create_test_entries()).unwrap();

        assert!(index.is_indexed());
        assert!(!index.is_empty());
    }

    #[test]
    fn test_table_of_contents() {
        let mut index = InternalBibleBookSectionIndex::new("ESV", "GEN");
        index.build(create_test_entries()).unwrap();

        let toc = index.table_of_contents();
        assert!(!toc.is_empty());

        // Check that section names are captured
        let names: Vec<&str> = toc.iter().map(|(_, name, _)| *name).collect();
        assert!(names.iter().any(|n| n.contains("Creation") || n.contains("Fall") || n == &"1" || n == &"3"));
    }

    #[test]
    fn test_get_section_entries() {
        let mut index = InternalBibleBookSectionIndex::new("ESV", "GEN");
        index.build(create_test_entries()).unwrap();

        // Get first section
        if let Some((cv, _)) = index.iter().next() {
            let entries = index.get_section_entries(cv).unwrap();
            assert!(!entries.is_empty());
        }
    }
}
