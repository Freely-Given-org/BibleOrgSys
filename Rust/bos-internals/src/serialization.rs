//! High-performance Bible serialization using rkyv.

use std::fs::File;
use std::io::{Write, Read, BufWriter};
use std::path::Path;
use rkyv::{Archive, Serialize, Deserialize};
use crate::entry_lists::InternalBibleEntryList;
use crate::indexes::cv_index::{CVIndexEntry, InternalBibleBookCVIndex};
use crate::indexes::section_index::{SectionIndexEntry, InternalBibleBookSectionIndex};
use crate::chapter_verse::ChapterVerse;
use indexmap::IndexMap;
use crate::error::BosError;

const BOS_BIBLE_VERSION: u32 = 3;

/// Structure representing a serialized Bible book.
#[derive(Archive, Serialize, Deserialize)]
pub struct BOSBibleFile {
    pub version: u32,
    pub work_name: String,
    pub bos_book_code: String,
    pub entries: InternalBibleEntryList,
    pub cv_index_data: Option<IndexMap<ChapterVerse, CVIndexEntry>>,
    pub section_index_data: Option<IndexMap<ChapterVerse, SectionIndexEntry>>,
}

/// Save a Bible book and its indexes to a binary file.
pub fn save_bos_bible<P: AsRef<Path>>(
    path: P,
    work_name: &str,
    bos_book_code: &str,
    entries: InternalBibleEntryList,
    cv_index: Option<&InternalBibleBookCVIndex>,
    section_index: Option<&InternalBibleBookSectionIndex>,
) -> Result<(), BosError> {
    let file_data = BOSBibleFile {
        version: BOS_BIBLE_VERSION,
        work_name: work_name.to_string(),
        bos_book_code: bos_book_code.to_string(),
        entries,
        cv_index_data: cv_index.map(|idx| idx.index_data().clone()),
        section_index_data: section_index.map(|idx| idx.index_data().clone()),
    };

    let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&file_data).map_err(|e| {
        crate::error::BosError::Parse(crate::error::ParseError::Generic(format!("Serialization error: {}", e)))
    })?;

    let file = File::create(path).map_err(BosError::Io)?;
    let mut writer = BufWriter::new(file);
    writer.write_all(&bytes).map_err(BosError::Io)?;
    Ok(())
}

/// Load a Bible book from a binary file.
pub fn load_bos_bible<P: AsRef<Path>+Clone>(path: P) -> Result<BOSBibleFile, BosError> {
    let mut file = File::open(path.clone()).map_err(BosError::Io)?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes).map_err(BosError::Io)?;

    let deserialized = rkyv::from_bytes::<BOSBibleFile, rkyv::rancor::Error>(&bytes).map_err(|e| {
        crate::error::BosError::Parse(crate::error::ParseError::Generic(format!("Deserialization error: {}", e)))
    })?;

    if deserialized.version < BOS_BIBLE_VERSION {
        panic!("Serialised file from {} was v{} not v{}", path.as_ref().to_str().unwrap(), deserialized.version, BOS_BIBLE_VERSION);
    }
    
    Ok(deserialized)
}
