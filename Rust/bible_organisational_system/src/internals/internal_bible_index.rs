use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum BibleIndexError {
    #[error("CV key '{chapter}:{verse}' not found in {book_code}")]
    CvNotFound {
        chapter: String,
        verse: String,
        book_code: String,
    },
    #[error("Index {index} out of bounds for {book_code}")]
    IndexOutOfBounds { index: usize, book_code: String },
}

#[derive(Debug, Clone)]
pub struct InternalBibleBookCVIndexEntry {
    pub entry_index: usize,
    pub entry_count: u16,
    pub context: String,
}

impl InternalBibleBookCVIndexEntry {
    pub fn new(entry_index: usize, entry_count: u16, context: impl Into<String>) -> Self {
        Self {
            entry_index,
            entry_count,
            context: context.into(),
        }
    }
}

#[derive(Debug)]
pub struct InternalBibleBookCVIndex<'a> {
    pub work_name: &'a str,
    pub book_code: &'a str,
    given_entries: &'a [String],
    cv_index_map: HashMap<(&'a str, &'a str), usize>,
}

impl<'a> InternalBibleBookCVIndex<'a> {
    pub fn new(work_name: &'a str, book_code: &'a str, given_entries: &'a [String]) -> Self {
        Self {
            work_name,
            book_code,
            given_entries,
            cv_index_map: HashMap::new(),
        }
    }

    /// Look up verse entries by chapter:verse reference.
    ///
    /// If `strict` is false, after failing a direct lookup, it will also search
    /// for bridged verses starting with the requested verse.
    pub fn get_verse_entries(&self, cv: &(&str, &str), strict: bool) -> Result<&str, BibleIndexError> {
        // Try direct lookup first
        if let Some(&array_index) = self.cv_index_map.get(cv) {
            return self
                .given_entries
                .get(array_index)
                .map(|s| s.as_str())
                .ok_or_else(|| BibleIndexError::IndexOutOfBounds {
                    index: array_index,
                    book_code: self.book_code.to_string(),
                });
        }

        // If not strict, search for bridged verses starting with this verse
        if !strict {
            let verse_prefix = format!("{}-", cv.1);
            for (key, &index) in &self.cv_index_map {
                if key.0 == cv.0
                    && key.1.starts_with(&verse_prefix)
                    && let Some(entry) = self.given_entries.get(index)
                {
                    return Ok(entry.as_str());
                }
            }
        }

        Err(BibleIndexError::CvNotFound {
            chapter: cv.0.to_string(),
            verse: cv.1.to_string(),
            book_code: self.book_code.to_string(),
        })
    }

    /// Add a chapter:verse mapping to the index.
    pub fn add_entry(&mut self, chapter: &'a str, verse: &'a str, index: usize) {
        self.cv_index_map.insert((chapter, verse), index);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cv_index_entry_creation() {
        let entry = InternalBibleBookCVIndexEntry::new(123, 456, "My context");
        assert_eq!(entry.entry_index, 123);
        assert_eq!(entry.entry_count, 456);
        assert_eq!(entry.context, "My context");
    }

    #[test]
    fn test_cv_index_entry_clone() {
        let entry = InternalBibleBookCVIndexEntry::new(1, 2, "context");
        let cloned = entry.clone();
        assert_eq!(entry.entry_index, cloned.entry_index);
        assert_eq!(entry.context, cloned.context);
    }

    #[test]
    fn test_cv_index_lookup_missing() {
        let entries = vec!["Genesis 1:1".to_string(), "Genesis 1:2".to_string()];
        let index = InternalBibleBookCVIndex::new("KJV", "GEN", &entries);

        let result = index.get_verse_entries(&("1", "1"), true);
        assert!(matches!(result, Err(BibleIndexError::CvNotFound { .. })));

        let err = result.unwrap_err();
        assert_eq!(err.to_string(), "CV key '1:1' not found in GEN");
    }

    #[test]
    fn test_cv_index_lookup_success() {
        let entries = vec!["In the beginning...".to_string(), "And the earth was...".to_string()];
        let mut index = InternalBibleBookCVIndex::new("KJV", "GEN", &entries);
        index.add_entry("1", "1", 0);
        index.add_entry("1", "2", 1);

        let result = index.get_verse_entries(&("1", "1"), true);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "In the beginning...");

        let result2 = index.get_verse_entries(&("1", "2"), true);
        assert_eq!(result2.unwrap(), "And the earth was...");
    }

    #[test]
    fn test_cv_index_bridged_verse_lookup() {
        let entries = vec!["Verses 1-3 content".to_string()];
        let mut index = InternalBibleBookCVIndex::new("KJV", "GEN", &entries);
        index.add_entry("1", "1-3", 0);

        // Strict lookup for verse 1 should fail (only "1-3" exists)
        let strict_result = index.get_verse_entries(&("1", "1"), true);
        assert!(strict_result.is_err());

        // Non-strict lookup should find the bridged verse
        let relaxed_result = index.get_verse_entries(&("1", "1"), false);
        assert!(relaxed_result.is_ok());
        assert_eq!(relaxed_result.unwrap(), "Verses 1-3 content");
    }
}
