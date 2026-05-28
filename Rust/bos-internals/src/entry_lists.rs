//! Typed list wrappers for Bible entries and extras.
//!
//! This module provides:
//! - `InternalBibleEntryList` - Collection of Bible text entries

use std::ops::{Index, IndexMut};
use std::slice::{Iter, IterMut};

use crate::entry::{InternalBibleEntry};

/// A specialized list for holding `InternalBibleEntry` items.
///
/// This represents the processed lines of a Bible book,
/// stored internally as `_processedLines` in Python.
///
/// # Example
///
/// ```
/// use bos_internals::{InternalBibleEntryList, InternalBibleEntry};
///
/// let mut entries = InternalBibleEntryList::new();
/// entries.push(InternalBibleEntry::simple("c", "1"));
/// entries.push(InternalBibleEntry::simple("v", "1"));
///
/// assert_eq!(entries.len(), 2);
/// ```
#[derive(Debug, Clone, Default, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleEntryList {
    data: Vec<InternalBibleEntry>,
}

impl InternalBibleEntryList {
    /// Create a new empty list.
    #[inline]
    pub fn new() -> Self {
        Self::default()
    }

    /// Create a new list with pre-allocated capacity.
    #[inline]
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            data: Vec::with_capacity(capacity),
        }
    }

    /// Create a list from an existing vector.
    #[inline]
    pub fn from_vec(data: Vec<InternalBibleEntry>) -> Self {
        Self { data }
    }

    /// Get the number of entries.
    #[inline]
    pub fn len(&self) -> usize {
        self.data.len()
    }

    /// Check if the list is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    /// Add an entry to the end of the list.
    #[inline]
    pub fn push(&mut self, entry: InternalBibleEntry) {
        self.data.push(entry);
    }

    /// Remove and return the last entry.
    #[inline]
    pub fn pop(&mut self) -> Option<InternalBibleEntry> {
        self.data.pop()
    }

    /// Extend with another list.
    #[inline]
    pub fn extend(&mut self, other: &InternalBibleEntryList) {
        self.data.extend(other.data.iter().cloned());
    }

    /// Clear all entries.
    #[inline]
    pub fn clear(&mut self) {
        self.data.clear();
    }

    /// Get an iterator over the entries.
    #[inline]
    pub fn iter(&self) -> Iter<'_, InternalBibleEntry> {
        self.data.iter()
    }

    /// Get a mutable iterator over the entries.
    #[inline]
    pub fn iter_mut(&mut self) -> IterMut<'_, InternalBibleEntry> {
        self.data.iter_mut()
    }

    /// Get a slice of entries as a new list.
    pub fn slice(&self, start: usize, end: usize) -> Self {
        let end = end.min(self.data.len());
        let start = start.min(end);
        Self {
            data: self.data[start..end].to_vec(),
        }
    }

    /// Search for the first entry with the given marker.
    ///
    /// Returns the index of the first match, or None if not found.
    ///
    /// # Arguments
    ///
    /// * `marker` - The marker to search for
    /// * `max_lines` - Optional limit on how many lines to search
    pub fn contains_marker(&self, marker: &str, max_lines: Option<usize>) -> Option<usize> {
        let limit = max_lines.unwrap_or(self.data.len());
        self.data.iter().take(limit).position(|e| e.marker() == marker)
    }

    /// Find all entries with the given marker.
    pub fn find_all(&self, marker: &str) -> Vec<(usize, &InternalBibleEntry)> {
        self.data
            .iter()
            .enumerate()
            .filter(|(_, e)| e.marker() == marker)
            .collect()
    }

    /// Get the last entry.
    #[inline]
    pub fn last(&self) -> Option<&InternalBibleEntry> {
        self.data.last()
    }

    /// Get a mutable reference to the last entry.
    #[inline]
    pub fn last_mut(&mut self) -> Option<&mut InternalBibleEntry> {
        self.data.last_mut()
    }

    /// Get the first entry.
    #[inline]
    pub fn first(&self) -> Option<&InternalBibleEntry> {
        self.data.first()
    }

    /// Get the underlying vector.
    #[inline]
    pub fn into_vec(self) -> Vec<InternalBibleEntry> {
        self.data
    }

    /// Get a reference to the underlying slice.
    #[inline]
    pub fn as_slice(&self) -> &[InternalBibleEntry] {
        &self.data
    }

    /// Get an entry by index, returning None if out of bounds.
    #[inline]
    pub fn get(&self, index: usize) -> Option<&InternalBibleEntry> {
        self.data.get(index)
    }

    /// Get a mutable entry by index, returning None if out of bounds.
    #[inline]
    pub fn get_mut(&mut self, index: usize) -> Option<&mut InternalBibleEntry> {
        self.data.get_mut(index)
    }
}

impl Index<usize> for InternalBibleEntryList {
    type Output = InternalBibleEntry;

    fn index(&self, index: usize) -> &Self::Output {
        &self.data[index]
    }
}

impl IndexMut<usize> for InternalBibleEntryList {
    fn index_mut(&mut self, index: usize) -> &mut Self::Output {
        &mut self.data[index]
    }
}

impl<'a> IntoIterator for &'a InternalBibleEntryList {
    type Item = &'a InternalBibleEntry;
    type IntoIter = Iter<'a, InternalBibleEntry>;

    fn into_iter(self) -> Self::IntoIter {
        self.data.iter()
    }
}

impl IntoIterator for InternalBibleEntryList {
    type Item = InternalBibleEntry;
    type IntoIter = std::vec::IntoIter<InternalBibleEntry>;

    fn into_iter(self) -> Self::IntoIter {
        self.data.into_iter()
    }
}

impl std::ops::Add for InternalBibleEntryList {
    type Output = Self;

    fn add(mut self, other: Self) -> Self {
        self.data.extend(other.data);
        self
    }
}

impl std::ops::AddAssign for InternalBibleEntryList {
    fn add_assign(&mut self, other: Self) {
        self.data.extend(other.data);
    }
}

impl std::fmt::Display for InternalBibleEntryList {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        const MAX_PRINTED: usize = 20;

        writeln!(f, "InternalBibleEntryList:")?;
        if self.data.is_empty() {
            writeln!(f, "  Empty.")?;
        } else {
            for (j, entry) in self.data.iter().enumerate() {
                if j >= MAX_PRINTED {
                    writeln!(f, "  … ({} total entries)", self.data.len())?;
                    break;
                }
                let text = entry.clean_text();
                let char_count = text.chars().count();
                let abbrev = if char_count > 60 {
                    // Find byte offset for the 30th character from start
                    let start_offset = text.char_indices().map(|(i, _)| i).nth(30).unwrap_or(text.len());

                    // Find byte offset for the 30th character from the end
                    let end_offset = text.char_indices().map(|(i, _)| i).nth(char_count - 30).unwrap_or(0);

                    format!("{}…{}", &text[..start_offset], &text[end_offset..])
                } else {
                    entry.clean_text().to_string()
                };
                writeln!(
                    f,
                    "  {:>3}/ {} = {:?}{}",
                    j,
                    entry.marker(),
                    abbrev,
                    if entry.has_extras() { " + extras" } else { "" }
                )?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_entry_list_basic() {
        let mut list = InternalBibleEntryList::new();
        assert!(list.is_empty());

        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("v", "1"));
        list.push(InternalBibleEntry::simple("v~", "In the beginning..."));

        println!("Test InternalBibleEntryList = ({} entries) {}", list.len(), list);
        assert_eq!(list.len(), 3);
        assert_eq!(list[0].marker(), "c");
        assert_eq!(list[1].marker(), "v");
    }

    #[test]
    fn test_entry_list_slice() {
        let mut list = InternalBibleEntryList::new();
        for i in 1..=10 {
            list.push(InternalBibleEntry::simple("v", i.to_string()));
            list.push(InternalBibleEntry::simple("v~", "Some verse text.".to_string()));
        }

        let slice = list.slice(4, 10);
        println!(
            "Test InternalBibleEntryList slice = ({} entries) {}",
            slice.len(),
            slice
        );
        assert_eq!(slice.len(), 6);
        assert_eq!(slice[0].clean_text(), "3");
        assert_eq!(slice[4].clean_text(), "5");
    }

    #[test]
    fn test_entry_list_contains_marker() {
        let mut list = InternalBibleEntryList::new();
        list.push(InternalBibleEntry::simple("c", "1"));
        list.push(InternalBibleEntry::simple("p", ""));
        list.push(InternalBibleEntry::simple("v", "1"));

        println!("Test InternalBibleEntryList = ({} entries) {}", list.len(), list);
        assert_eq!(list.contains_marker("c", None), Some(0));
        assert_eq!(list.contains_marker("v", None), Some(2));
        assert_eq!(list.contains_marker("v", Some(2)), None); // Limited search
        assert_eq!(list.contains_marker("q", None), None);
    }

    #[test]
    fn test_entry_list_add() {
        let mut list1 = InternalBibleEntryList::new();
        list1.push(InternalBibleEntry::simple("c", "1"));

        let mut list2 = InternalBibleEntryList::new();
        list2.push(InternalBibleEntry::simple("v", "1"));

        let combined = list1 + list2;

        println!(
            "Test combined InternalBibleEntryList = ({} entries) {}",
            combined.len(),
            combined
        );
        assert_eq!(combined.len(), 2);
        assert_eq!(combined[0].marker(), "c");
        assert_eq!(combined[1].marker(), "v");
    }
}
