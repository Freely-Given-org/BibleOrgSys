//! Indexing structures for fast Bible content lookup.
//!
//! This module provides two indexing systems:
//! - `cv_index`: Chapter:Verse based lookup
//! - `section_index`: Section heading based lookup

pub mod cv_index;
pub mod section_index;

pub use cv_index::{CVIndexEntry, InternalBibleBookCVIndex};
pub use section_index::{InternalBibleBookSectionIndex, SectionIndexEntry};
