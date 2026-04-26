//! USFM marker types and constants.
//!
//! This module defines the various marker types used in Bible text representation,
//! based on the USFM3 standard and BibleOrgSys custom extensions.

use compact_str::CompactString;

/// Types of "extra" content (footnotes, cross-references, etc.)
/// that are extracted from the main text flow.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub enum ExtraType {
    /// Footnote (`fn` -> USFM marker `\f`)
    Footnote,
    /// Endnote (`en` -> USFM marker `\fe`)
    Endnote,
    /// Cross-reference (`xr` -> USFM marker `\x`)
    CrossRef,
    /// Figure (`fig` -> USFM marker `\fig`)
    Figure,
    /// Strong's number (`str` -> USFM marker `\str`)
    Strongs,
    /// Semantic/translation info (`sem` -> USFM marker `\sem`)
    Semantic,
    /// Word wrapper with full attributes (`ww` -> USFM marker `\ww`)
    WordWithAttributes,
    /// Published verse number (`vp` -> USFM marker `\vp`)
    VersePublished,
}

impl ExtraType {
    /// Get the USFM marker string for this extra type.
    #[inline]
    pub fn marker(&self) -> &'static str {
        match self {
            Self::Footnote => "f",
            Self::Endnote => "fe",
            Self::CrossRef => "x",
            Self::Figure => "fig",
            Self::Strongs => "str",
            Self::Semantic => "sem",
            Self::WordWithAttributes => "ww",
            Self::VersePublished => "vp",
        }
    }

    /// Get the internal type string (used in Python BOS).
    #[inline]
    pub fn type_str(&self) -> &'static str {
        match self {
            Self::Footnote => "fn",
            Self::Endnote => "en",
            Self::CrossRef => "xr",
            Self::Figure => "fig",
            Self::Strongs => "str",
            Self::Semantic => "sem",
            Self::WordWithAttributes => "ww",
            Self::VersePublished => "vp",
        }
    }

    /// Parse an extra type from its type string.
    pub fn from_type_str(s: &str) -> Option<Self> {
        match s {
            "fn" => Some(Self::Footnote),
            "en" => Some(Self::Endnote),
            "xr" => Some(Self::CrossRef),
            "fig" => Some(Self::Figure),
            "str" => Some(Self::Strongs),
            "sem" => Some(Self::Semantic),
            "ww" => Some(Self::WordWithAttributes),
            "vp" => Some(Self::VersePublished),
            _ => None,
        }
    }

    /// Parse an extra type from its USFM marker.
    pub fn from_marker(s: &str) -> Option<Self> {
        match s {
            "f" => Some(Self::Footnote),
            "fe" => Some(Self::Endnote),
            "x" => Some(Self::CrossRef),
            "fig" => Some(Self::Figure),
            "str" => Some(Self::Strongs),
            "sem" => Some(Self::Semantic),
            "ww" => Some(Self::WordWithAttributes),
            "vp" => Some(Self::VersePublished),
            _ => None,
        }
    }

    /// Get all extra types as a slice.
    pub fn all() -> &'static [ExtraType] {
        &[
            Self::Footnote,
            Self::Endnote,
            Self::CrossRef,
            Self::Figure,
            Self::Strongs,
            Self::Semantic,
            Self::WordWithAttributes,
            Self::VersePublished,
        ]
    }
}

impl std::fmt::Display for ExtraType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.type_str())
    }
}

/// Custom content markers used by BibleOrgSys.
///
/// These are markers that BOS adds to the internal representation
/// beyond standard USFM markers.
pub mod custom_content {
    /// `c~` - Anything after the chapter number on a `\c` line
    pub const CHAPTER_TEXT: &str = "c~";
    /// `c#` - The chapter number in the correct position to be printed
    pub const CHAPTER_NUMBER: &str = "c#";
    /// `v=` - Verse number (not to be printed) that following fields belong to
    pub const VERSE_BRIDGE: &str = "v=";
    /// `v~` - Verse text (anything after the verse number on a `\v` line)
    pub const VERSE_TEXT: &str = "v~";
    /// `p~` - Paragraph text (anything on a paragraph line like `\p`, `\q`, etc.)
    pub const PARAGRAPH_TEXT: &str = "p~";
    /// `cl¤` - Chapter label BEFORE `\c 1` (represents text for "chapter" throughout book)
    pub const CHAPTER_LABEL_BOOK: &str = "cl¤";
    /// `vp#` - Published verse number converted to a separate newline field
    pub const VERSE_PUBLISHED: &str = "vp#";

    /// All custom content markers as a slice.
    pub const ALL: &[&str] = &[
        CHAPTER_TEXT,
        CHAPTER_NUMBER,
        VERSE_BRIDGE,
        VERSE_TEXT,
        PARAGRAPH_TEXT,
        CHAPTER_LABEL_BOOK,
        VERSE_PUBLISHED,
    ];

    /// Check if a marker is a custom content marker.
    #[inline]
    pub fn is_custom_content(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// Custom nesting markers used by BibleOrgSys.
///
/// These markers are inserted to provide structure that may not be
/// explicit in the original USFM.
pub mod custom_nesting {
    /// `headers` - Header section marker
    pub const HEADERS: &str = "headers";
    /// `intro` - Inserted at the start of book introductions
    pub const INTRO: &str = "intro";
    /// `ilist` - Inserted at the start of introduction lists (before `\ili` markers)
    pub const INTRO_LIST: &str = "ilist";
    /// `chapters` - Inserted after introduction, before first Bible content
    pub const CHAPTERS: &str = "chapters";
    /// `list` - Inserted at the start of lists (before `\li` markers)
    pub const LIST: &str = "list";
    /// `iot` - Introduction outline title (added if not already present)
    pub const INTRO_OUTLINE_TITLE: &str = "iot";

    /// All custom nesting markers as a slice.
    pub const ALL: &[&str] = &[HEADERS, INTRO, INTRO_LIST, CHAPTERS, LIST, INTRO_OUTLINE_TITLE];

    /// Check if a marker is a custom nesting marker.
    #[inline]
    pub fn is_custom_nesting(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// Regular USFM nesting markers that require closing.
pub mod regular_nesting {
    /// Chapter marker
    pub const CHAPTER: &str = "c";
    /// Verse marker
    pub const VERSE: &str = "v";

    /// All regular nesting markers.
    pub const ALL: &[&str] = &[CHAPTER, VERSE];
}

/// Bible paragraph markers from USFM.
pub mod paragraph_markers {
    pub const P: &str = "p";
    pub const PC: &str = "pc";
    pub const PR: &str = "pr";
    pub const M: &str = "m";
    pub const MI: &str = "mi";
    pub const PM: &str = "pm";
    pub const PMO: &str = "pmo";
    pub const PMC: &str = "pmc";
    pub const PMR: &str = "pmr";
    pub const CLS: &str = "cls";
    pub const PI: &str = "pi";
    pub const PI1: &str = "pi1";
    pub const PI2: &str = "pi2";
    pub const PI3: &str = "pi3";
    pub const PI4: &str = "pi4";
    pub const PH: &str = "ph";
    pub const PH1: &str = "ph1";
    pub const PH2: &str = "ph2";
    pub const PH3: &str = "ph3";
    pub const PH4: &str = "ph4";
    pub const Q: &str = "q";
    pub const Q1: &str = "q1";
    pub const Q2: &str = "q2";
    pub const Q3: &str = "q3";
    pub const Q4: &str = "q4";
    pub const QR: &str = "qr";
    pub const QM: &str = "qm";
    pub const QM1: &str = "qm1";
    pub const QM2: &str = "qm2";
    pub const QM3: &str = "qm3";
    pub const QM4: &str = "qm4";
    pub const LI: &str = "li";
    pub const LI1: &str = "li1";
    pub const LI2: &str = "li2";
    pub const LI3: &str = "li3";
    pub const LI4: &str = "li4";

    pub const NB: &str = "nb";

    /// All paragraph markers.
    pub const ALL: &[&str] = &[
        P, PC, PR, M, MI, PM, PMO, PMC, PMR, CLS, PI, PI1, PI2, PI3, PI4, PH, PH1, PH2, PH3, PH4, Q, Q1, Q2, Q3, Q4,
        QR, QM, QM1, QM2, QM3, QM4, LI, LI1, LI2, LI3, LI4, NB,
    ];

    /// Check if a marker is a paragraph marker.
    #[inline]
    pub fn is_paragraph(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// USFM introduction markers.
pub mod introduction_markers {
    pub const ALL: &[&str] = &[
        "imt", "imt1", "imt2", "imt3", "imt4", "is", "is1", "is2", "is3", "is4", "ip", "ipi", "im",
        "imi", "ipq", "imq", "ipr", "iq", "iq1", "iq2", "iq3", "io", "io1", "io2", "io3", "io4",
        "iot", "ior", "ili", "ili1", "ili2", "ili3", "ili4", "iex", "ib",
    ];

    #[inline]
    pub fn is_introduction(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// USFM heading markers.
pub mod heading_markers {
    pub const ALL: &[&str] = &[
        "s", "s1", "s2", "s3", "s4", "sr", "is", "is1", "is2", "is3", "is4", "mr", "qa", "qc",
    ];

    #[inline]
    pub fn is_heading(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// USFM intro outline markers.
pub mod intro_outline_markers {
    pub const ALL: &[&str] = &["io", "io1", "io2", "io3", "io4"];

    #[inline]
    pub fn is_intro_outline(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// USFM intro list markers.
pub mod intro_list_markers {
    pub const ALL: &[&str] = &["ili", "ili1", "ili2", "ili3", "ili4"];

    #[inline]
    pub fn is_intro_list(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// USFM main text list markers.
pub mod main_text_list_markers {
    pub const ALL: &[&str] = &["li", "li1", "li2", "li3", "li4"];

    #[inline]
    pub fn is_main_text_list(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// Major section markers.
pub mod major_section_markers {
    pub const MS: &str = "ms";
    pub const MS1: &str = "ms1";
    pub const MS2: &str = "ms2";
    pub const MS3: &str = "ms3";
    pub const MS4: &str = "ms4";

    pub const ALL: &[&str] = &[MS, MS1, MS2, MS3, MS4];

    #[inline]
    pub fn is_major_section(marker: &str) -> bool {
        ALL.contains(&marker)
    }
}

/// Check if a marker has "Never" content type (like \b, \ib, \nb).
#[inline]
pub fn is_never_content_marker(marker: &str) -> bool {
    matches!(marker, "b" | "ib" | "nb" | "ts")
}

/// Normalize a marker to its standard numbered form if applicable.
/// E.g., "mt" -> "mt1", "s" -> "s1".
pub fn normalize_marker(marker: &str) -> &str {
    match marker {
        "imt" => "imt1",
        "is" => "is1",
        "iq" => "iq1",
        "ili" => "ili1",
        "io" => "io1",
        "imte" => "imte1",
        "mt" => "mt1",
        "mte" => "mte1",
        "ms" => "ms1",
        "s" => "s1",
        "pi" => "pi1",
        "li" => "li1",
        "ph" => "ph1",
        "q" => "q1",
        "qm" => "qm1",
        "th" => "th1",
        "thr" => "thr1",
        "tc" => "tc1",
        "tcr" => "tcr1",
        "qt-s" => "qt1-s",
        "qt-e" => "qt1-e",
        _ => marker,
    }
}

/// Generate an end marker for a given marker.
///
/// End markers are prefixed with `¬` ('not' sign).
#[inline]
pub fn end_marker(marker: &str) -> CompactString {
    let mut end = CompactString::from("¬");
    end.push_str(marker);
    end
}

/// Check if a marker is an end marker (starts with `¬`).
#[inline]
pub fn is_end_marker(marker: &str) -> bool {
    marker.starts_with('¬')
}

/// Get the base marker from an end marker (removes `¬` prefix).
#[inline]
pub fn base_marker(end_marker: &str) -> Option<&str> {
    end_marker.strip_prefix('¬')
}

/// All markers that require nesting (and thus have end markers).
pub fn all_nesting_markers() -> Vec<&'static str> {
    let mut markers = Vec::with_capacity(50);
    markers.extend_from_slice(regular_nesting::ALL);
    markers.extend_from_slice(custom_nesting::ALL);
    markers.extend_from_slice(paragraph_markers::ALL);
    markers.extend_from_slice(major_section_markers::ALL);
    markers
}

/// Generate all end markers for nesting markers.
pub fn all_end_markers() -> Vec<CompactString> {
    all_nesting_markers().iter().map(|m| end_marker(m)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extra_type_roundtrip() {
        for et in ExtraType::all() {
            let type_str = et.type_str();
            let parsed = ExtraType::from_type_str(type_str);
            assert_eq!(parsed, Some(*et));

            let marker = et.marker();
            let parsed_marker = ExtraType::from_marker(marker);
            assert_eq!(parsed_marker, Some(*et));
        }
    }

    #[test]
    fn test_end_marker() {
        assert_eq!(end_marker("v"), "¬v");
        assert_eq!(end_marker("pc"), "¬pc");
        assert_eq!(end_marker("chapters"), "¬chapters");
    }

    #[test]
    fn test_is_end_marker() {
        assert!(is_end_marker("¬v"));
        assert!(is_end_marker("¬chapters"));
        assert!(!is_end_marker("v"));
        assert!(!is_end_marker("pc"));
    }

    #[test]
    fn test_base_marker() {
        assert_eq!(base_marker("¬v"), Some("v"));
        assert_eq!(base_marker("¬chapters"), Some("chapters"));
        assert_eq!(base_marker("v"), None);
    }

    #[test]
    fn test_custom_content() {
        assert!(custom_content::is_custom_content("v~"));
        assert!(custom_content::is_custom_content("c#"));
        assert!(!custom_content::is_custom_content("v"));
    }

    #[test]
    fn test_custom_nesting() {
        assert!(custom_nesting::is_custom_nesting("intro"));
        assert!(custom_nesting::is_custom_nesting("chapters"));
        assert!(!custom_nesting::is_custom_nesting("v"));
    }
}
