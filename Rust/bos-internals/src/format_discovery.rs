//! Bible format discovery logic.
//!
//! This module provides logic for identifying various Bible formats in a given folder
//! or its subdirectories. It is intended to be faster than the original Python
//! implementation by using a single directory scan and parallel processing.

use std::fs;
use std::path::{Path, PathBuf};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum BibleFormat {
    Pickled,
    TheWord,
    MySword,
    ESword,
    ESwordCommentary,
    MyBible,
    PalmDB,
    GoBible,
    Sword,
    Unbound,
    Drupal,
    YET,
    ESFM,
    PTX8,
    ScriptureBurrito,
    USFM,
    DBL,
    USX,
    USFX,
    OSIS,
    OpenSong,
    Zefania,
    Haggai,
    VerseView,
    CSV,
    Forge,
    VPL,
    BCV,
}

impl BibleFormat {
    pub fn name(&self) -> &'static str {
        match self {
            BibleFormat::Pickled => "pickled Bible",
            BibleFormat::TheWord => "theWord Bible",
            BibleFormat::MySword => "MySword Bible",
            BibleFormat::ESword => "e-Sword Bible",
            BibleFormat::ESwordCommentary => "e-Sword Commentary",
            BibleFormat::MyBible => "MyBible Bible",
            BibleFormat::PalmDB => "PalmDB Bible",
            BibleFormat::GoBible => "GoBible Bible",
            BibleFormat::Sword => "Sword Bible",
            BibleFormat::Unbound => "Unbound Bible",
            BibleFormat::Drupal => "Drupal Bible",
            BibleFormat::YET => "YET Bible",
            BibleFormat::ESFM => "ESFM Bible",
            BibleFormat::PTX8 => "PTX8 Bible",
            BibleFormat::ScriptureBurrito => "SB Bible",
            BibleFormat::USFM => "USFM Bible",
            BibleFormat::DBL => "DBL Bible",
            BibleFormat::USX => "USX XML Bible",
            BibleFormat::USFX => "USFX XML Bible",
            BibleFormat::OSIS => "OSIS XML Bible",
            BibleFormat::OpenSong => "OpenSong XML Bible",
            BibleFormat::Zefania => "Zefania XML Bible",
            BibleFormat::Haggai => "Haggai XML Bible",
            BibleFormat::VerseView => "VerseView XML Bible",
            BibleFormat::CSV => "CSV Bible",
            BibleFormat::Forge => "Forge Bible",
            BibleFormat::VPL => "VPL Bible",
            BibleFormat::BCV => "BCV Bible",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectedBible {
    pub format: BibleFormat,
    pub path: PathBuf,
    pub name: String,
    pub confidence: u8, // 0-100
}

/// Metadata about a directory to avoid multiple scans.
pub struct DirectoryScan {
    pub path: PathBuf,
    pub files: Vec<String>,
    pub folders: Vec<String>,
}

impl DirectoryScan {
    pub fn scan(path: &Path) -> Self {
        let mut files = Vec::new();
        let mut folders = Vec::new();
        if let Ok(entries) = fs::read_dir(path) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                if let Ok(ft) = entry.file_type() {
                    if ft.is_dir() {
                        folders.push(name);
                    } else if ft.is_file() {
                        files.push(name);
                    }
                }
            }
        }
        DirectoryScan {
            path: path.to_path_buf(),
            files,
            folders,
        }
    }
}

/// Main entry point for detecting Bibles in a folder and its subdirectories (1 level deep).
pub fn detect_bibles(root: &Path, strict: bool) -> Vec<DetectedBible> {
    let root_scan = DirectoryScan::scan(root);
    let mut results = Vec::new();

    // 1. Check root
    results.extend(check_scan(&root_scan, strict));

    // 2. Check subfolders (1 level deep)
    let sub_results: Vec<DetectedBible> = root_scan.folders.par_iter()
        .filter(|f| !is_commonly_ignored(f))
        .flat_map(|f| {
            let sub_path = root.join(f);
            let sub_scan = DirectoryScan::scan(&sub_path);
            check_scan(&sub_scan, strict)
        })
        .collect();
    
    results.extend(sub_results);
    results
}

fn is_commonly_ignored(name: &str) -> bool {
    matches!(name, ".git" | ".hg" | ".gitignore" | ".github" | "__MACOSX" | "__pycache__" | ".venv")
}

fn check_scan(scan: &DirectoryScan, strict: bool) -> Vec<DetectedBible> {
    let mut detected = Vec::new();

    if let Some(res) = check_pickled(scan, strict) { detected.push(res); }
    if let Some(res) = check_mysword(scan, strict) { detected.push(res); }
    if let Some(res) = check_theword(scan, strict) { detected.push(res); }
    if let Some(res) = check_esword(scan, strict) { detected.push(res); }
    if let Some(res) = check_mybible(scan, strict) { detected.push(res); }
    if let Some(res) = check_palmdb(scan, strict) { detected.push(res); }
    if let Some(res) = check_gobible(scan, strict) { detected.push(res); }
    if let Some(res) = check_sword(scan, strict) { detected.push(res); }
    if let Some(res) = check_yet(scan, strict) { detected.push(res); }
    if let Some(res) = check_ptx8(scan, strict) { detected.push(res); }
    if let Some(res) = check_esfm(scan, strict) { detected.push(res); }
    if let Some(res) = check_forge(scan, strict) { detected.push(res); }
    if let Some(res) = check_scripture_burrito(scan, strict) { detected.push(res); }
    if let Some(res) = check_dbl(scan, strict) { detected.push(res); }
    if let Some(res) = check_usfm(scan, strict) { detected.push(res); }
    if let Some(res) = check_usx(scan, strict) { detected.push(res); }
    if let Some(res) = check_usfx(scan, strict) { detected.push(res); }
    if let Some(res) = check_osis(scan, strict) { detected.push(res); }
    if let Some(res) = check_opensong(scan, strict) { detected.push(res); }
    if let Some(res) = check_zefania(scan, strict) { detected.push(res); }
    if let Some(res) = check_haggai(scan, strict) { detected.push(res); }
    if let Some(res) = check_verseview(scan, strict) { detected.push(res); }
    if let Some(res) = check_drupal(scan, strict) { detected.push(res); }
    if let Some(res) = check_bcv(scan, strict) { detected.push(res); }
    if let Some(res) = check_csv(scan, strict) { detected.push(res); }
    if let Some(res) = check_vpl(scan, strict) { detected.push(res); }
    if let Some(res) = check_unbound(scan, strict) { detected.push(res); }

    detected
}

fn check_pickled(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| f.to_uppercase().ends_with(".PICKLE")) {
        return Some(DetectedBible {
            format: BibleFormat::Pickled,
            path: scan.path.join(f),
            name: f.clone(),
            confidence: 100,
        });
    }
    None
}

fn check_usfm(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        let upper = f.to_uppercase();
        if is_ignored_extension(&upper) { continue; }
        if upper.ends_with(".USFM") || upper.ends_with(".SFM") || upper.ends_with(".SCP") || upper.ends_with(".TXT") {
            let path = scan.path.join(f);
            if let Some(id) = crate::discovery_filenames::get_usfm_id_from_file(&path) {
                if let Ok(file) = fs::File::open(&path) {
                    let reader = BufReader::new(file);
                    for line_res in reader.lines().take(5) {
                        if let Ok(line) = line_res {
                            let l = line.to_lowercase();
                            if l.starts_with("\\usfm 3") || l.starts_with("\\usfm3") {
                                return Some(DetectedBible {
                                    format: BibleFormat::USFM,
                                    path: scan.path.clone(),
                                    name: id.to_string(),
                                    confidence: 100,
                                });
                            }
                        }
                    }
                }
            }
        }
    }
    None
}

fn check_usx(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        if f.to_uppercase().ends_with(".USX") {
            let path = scan.path.join(f);
            if let Some(id) = crate::discovery_filenames::get_usx_id_from_file(&path) {
                return Some(DetectedBible {
                    format: BibleFormat::USX,
                    path: scan.path.clone(),
                    name: id.to_string(),
                    confidence: 100,
                });
            }
        }
    }
    None
}

fn check_mysword(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| f.to_uppercase().ends_with(".MYBIBLE")) {
        return Some(DetectedBible {
            format: BibleFormat::MySword,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 100,
        });
    }
    None
}

fn check_theword(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| {
        let u = f.to_uppercase();
        u.ends_with(".ONT") || u.ends_with(".OT") || u.ends_with(".NT") || u.ends_with(".BBL")
    }) {
        return Some(DetectedBible {
            format: BibleFormat::TheWord,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 90,
        });
    }
    None
}

fn check_osis(scan: &DirectoryScan, strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        let u = f.to_uppercase();
        if u.ends_with(".OSIS") || u.ends_with(".XML") {
            if strict {
                if let Ok(file) = fs::File::open(scan.path.join(f)) {
                    let reader = BufReader::new(file);
                    for line_res in reader.lines().take(5) {
                        if let Ok(line) = line_res {
                            if line.contains("<osis") {
                                return Some(DetectedBible {
                                    format: BibleFormat::OSIS,
                                    path: scan.path.clone(),
                                    name: f.clone(),
                                    confidence: 100,
                                });
                            }
                        }
                    }
                }
            } else if u.ends_with(".OSIS") {
                return Some(DetectedBible {
                    format: BibleFormat::OSIS,
                    path: scan.path.clone(),
                    name: f.clone(),
                    confidence: 80,
                });
            }
        }
    }
    None
}

fn check_scripture_burrito(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if scan.files.iter().any(|f| f == "metadata.json") && scan.folders.iter().any(|f| f == "ingredients") {
        return Some(DetectedBible {
            format: BibleFormat::ScriptureBurrito,
            path: scan.path.clone(),
            name: "Scripture Burrito".to_string(),
            confidence: 100,
        });
    }
    None
}

fn check_dbl(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if scan.files.iter().any(|f| f.to_lowercase() == "metadata.xml") && scan.folders.iter().any(|f| f.starts_with("USX_") || f == "USX") {
        return Some(DetectedBible {
            format: BibleFormat::DBL,
            path: scan.path.clone(),
            name: "DBL Bundle".to_string(),
            confidence: 100,
        });
    }
    None
}

fn check_mybible(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| {
        let u = f.to_uppercase();
        u.ends_with(".SQLITE3") && (u.contains(".BBL.") || u.contains(".COMMENTARIES."))
    }) {
        return Some(DetectedBible {
            format: BibleFormat::MyBible,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 90,
        });
    }
    None
}

fn check_esword(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| f.to_uppercase().ends_with(".BBLX")) {
        return Some(DetectedBible {
            format: BibleFormat::ESword,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 100,
        });
    }
    if let Some(f) = scan.files.iter().find(|f| {
        let u = f.to_uppercase();
        u.ends_with(".CMTI") || u.ends_with(".CMTX")
    }) {
        return Some(DetectedBible {
            format: BibleFormat::ESwordCommentary,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 100,
        });
    }
    None
}

fn check_zefania(scan: &DirectoryScan, strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        if f.to_uppercase().ends_with(".XML") {
            if strict {
                if let Ok(file) = fs::File::open(scan.path.join(f)) {
                    let reader = BufReader::new(file);
                    for line_res in reader.lines().take(10) {
                        if let Ok(line) = line_res {
                            if line.contains("<XMLBIBLE") {
                                return Some(DetectedBible {
                                    format: BibleFormat::Zefania,
                                    path: scan.path.clone(),
                                    name: f.clone(),
                                    confidence: 100,
                                });
                            }
                        }
                    }
                }
            }
        }
    }
    None
}

fn check_opensong(scan: &DirectoryScan, strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        if f.to_uppercase().ends_with(".XML") {
            if strict {
                if let Ok(file) = fs::File::open(scan.path.join(f)) {
                    let reader = BufReader::new(file);
                    for line_res in reader.lines().take(10) {
                        if let Ok(line) = line_res {
                            if line.contains("<bible") {
                                return Some(DetectedBible {
                                    format: BibleFormat::OpenSong,
                                    path: scan.path.clone(),
                                    name: f.clone(),
                                    confidence: 100,
                                });
                            }
                        }
                    }
                }
            }
        }
    }
    None
}

fn check_sword(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if scan.folders.iter().any(|f| f == "mods.d") && scan.folders.iter().any(|f| f == "modules") {
        return Some(DetectedBible {
            format: BibleFormat::Sword,
            path: scan.path.clone(),
            name: "Sword Module".to_string(),
            confidence: 100,
        });
    }
    None
}

fn check_unbound(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    let count = scan.files.iter().filter(|f| {
        let upper = f.to_uppercase();
        (upper.ends_with(".TXT") || upper.ends_with(".CSV")) && bos_books_codes::BIBLE_BOOKS_CODES_ARRAY.iter().any(|entry| upper.contains(entry.BOS_book_code))
    }).count();

    if count > 5 {
        return Some(DetectedBible {
            format: BibleFormat::Unbound,
            path: scan.path.clone(),
            name: "Unbound Bible".to_string(),
            confidence: 60,
        });
    }
    None
}

fn check_csv(scan: &DirectoryScan, strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        let u = f.to_uppercase();
        if u.ends_with(".CSV") || u.ends_with(".TSV") {
            if strict {
                if let Ok(file) = fs::File::open(scan.path.join(f)) {
                    let reader = BufReader::new(file);
                    for line_res in reader.lines().take(5) {
                        if let Ok(line) = line_res {
                            if line.contains("Book") && line.contains("Chapter") && line.contains("Verse") {
                                return Some(DetectedBible {
                                    format: BibleFormat::CSV,
                                    path: scan.path.clone(),
                                    name: f.clone(),
                                    confidence: 90,
                                });
                            }
                        }
                    }
                }
            } else {
                return Some(DetectedBible {
                    format: BibleFormat::CSV,
                    path: scan.path.clone(),
                    name: f.clone(),
                    confidence: 50,
                });
            }
        }
    }
    None
}

fn check_vpl(scan: &DirectoryScan, strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        let u = f.to_uppercase();
        if u.ends_with(".VPL") || u.ends_with(".TXT") {
            if strict {
                if let Ok(file) = fs::File::open(scan.path.join(f)) {
                    let reader = BufReader::new(file);
                    if let Some(Ok(line)) = reader.lines().next() {
                        if line.split_whitespace().next().map(|s| bos_books_codes::is_valid_bos_book_code(s)).unwrap_or(false) {
                            return Some(DetectedBible {
                                format: BibleFormat::VPL,
                                path: scan.path.clone(),
                                name: f.clone(),
                                confidence: 70,
                            });
                        }
                    }
                }
            }
        }
    }
    None
}

fn check_yet(scan: &DirectoryScan, strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        if f.to_uppercase().ends_with(".YET") {
            if strict {
                if let Ok(file) = fs::File::open(scan.path.join(f)) {
                    let reader = BufReader::new(file);
                    if let Some(Ok(line)) = reader.lines().next() {
                        if line.starts_with("info\t") {
                            return Some(DetectedBible {
                                format: BibleFormat::YET,
                                path: scan.path.clone(),
                                name: f.clone(),
                                confidence: 100,
                            });
                        }
                    }
                }
            } else {
                return Some(DetectedBible {
                    format: BibleFormat::YET,
                    path: scan.path.clone(),
                    name: f.clone(),
                    confidence: 80,
                });
            }
        }
    }
    None
}

fn check_ptx8(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if scan.files.iter().any(|f| f == "Settings.xml") {
        return Some(DetectedBible {
            format: BibleFormat::PTX8,
            path: scan.path.clone(),
            name: "Paratext 8/9 Project".to_string(),
            confidence: 100,
        });
    }
    None
}

fn check_esfm(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        let upper = f.to_uppercase();
        if upper.ends_with(".ESFM") || upper.ends_with(".SFM") {
            let path = scan.path.join(f);
            if let Ok(file) = fs::File::open(&path) {
                let reader = BufReader::new(file);
                if let Some(Ok(line)) = reader.lines().next() {
                    if line.starts_with("\\esfm") {
                        return Some(DetectedBible {
                            format: BibleFormat::ESFM,
                            path: scan.path.clone(),
                            name: f.clone(),
                            confidence: 100,
                        });
                    }
                }
            }
        }
    }
    None
}

fn check_forge(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        if f.to_uppercase().ends_with(".TXT") {
            let path = scan.path.join(f);
            if let Ok(file) = fs::File::open(&path) {
                let reader = BufReader::new(file);
                if let Some(Ok(line)) = reader.lines().next() {
                    if line.starts_with("; TITLE:") {
                        return Some(DetectedBible {
                            format: BibleFormat::Forge,
                            path: scan.path.clone(),
                            name: f.clone(),
                            confidence: 100,
                        });
                    }
                }
            }
        }
    }
    None
}

fn check_usfx(scan: &DirectoryScan, strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        if f.to_uppercase().ends_with(".XML") {
            if strict {
                if let Ok(file) = fs::File::open(scan.path.join(f)) {
                    let reader = BufReader::new(file);
                    for line_res in reader.lines().take(5) {
                        if let Ok(line) = line_res {
                            if line.contains("<usfx") {
                                return Some(DetectedBible {
                                    format: BibleFormat::USFX,
                                    path: scan.path.clone(),
                                    name: f.clone(),
                                    confidence: 100,
                                });
                            }
                        }
                    }
                }
            }
        }
    }
    None
}

fn check_haggai(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| f.to_uppercase().ends_with(".HAG")) {
        return Some(DetectedBible {
            format: BibleFormat::Haggai,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 100,
        });
    }
    None
}

fn check_verseview(scan: &DirectoryScan, strict: bool) -> Option<DetectedBible> {
    for f in &scan.files {
        if f.to_uppercase().ends_with(".XML") {
            if strict {
                if let Ok(file) = fs::File::open(scan.path.join(f)) {
                    let reader = BufReader::new(file);
                    let mut lines = reader.lines();
                    let _line1 = lines.next().and_then(|r| r.ok()).unwrap_or_default();
                    let line2 = lines.next().and_then(|r| r.ok()).unwrap_or_default();
                    let line3 = lines.next().and_then(|r| r.ok()).unwrap_or_default();
                    if line2.contains("<bible>") && line3.contains("<fname>") {
                        return Some(DetectedBible {
                            format: BibleFormat::VerseView,
                            path: scan.path.clone(),
                            name: f.clone(),
                            confidence: 100,
                        });
                    }
                }
            }
        }
    }
    None
}

fn check_drupal(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| f.to_uppercase().ends_with(".BC")) {
        return Some(DetectedBible {
            format: BibleFormat::Drupal,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 100,
        });
    }
    None
}

fn check_bcv(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| f.to_uppercase().ends_with(".BCV")) {
        return Some(DetectedBible {
            format: BibleFormat::BCV,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 100,
        });
    }
    None
}

fn check_palmdb(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if let Some(f) = scan.files.iter().find(|f| f.to_uppercase().ends_with(".PDB")) {
        return Some(DetectedBible {
            format: BibleFormat::PalmDB,
            path: scan.path.clone(),
            name: f.clone(),
            confidence: 100,
        });
    }
    None
}

fn check_gobible(scan: &DirectoryScan, _strict: bool) -> Option<DetectedBible> {
    if scan.files.iter().any(|f| f.to_uppercase().ends_with(".JAR")) && scan.files.iter().any(|f| f.to_uppercase().ends_with(".LDS")) {
        return Some(DetectedBible {
            format: BibleFormat::GoBible,
            path: scan.path.clone(),
            name: "GoBible".to_string(),
            confidence: 100,
        });
    }
    None
}

fn is_ignored_extension(upper: &str) -> bool {
    crate::discovery_filenames::EXTENSIONS_TO_IGNORE.iter().any(|ext| upper.ends_with(ext))
}
