//! Bible Organisational System - Main crate with Python bindings.
//!
//! This crate provides the main entry point for the Bible Organisational System
//! Rust implementation, including Python bindings via PyO3.
//!
//! The core internals are provided by the `bos-internals` crate.

pub mod cv_index_bindings;
pub mod extras_bindings;
pub mod parsing_bindings;
pub mod processing_bindings;
pub mod section_index_bindings;

// Re-export everything from bos-internals for convenience
pub use bos_internals::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chapter_verse() {
        let cv = ChapterVerse::new("1", "1");
        assert_eq!(cv.chapter(), "1");
        assert_eq!(cv.verse(), "1");
    }

    #[test]
    fn test_entry_list() {
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("c", "1"));
        assert_eq!(entries.len(), 1);
    }
}
