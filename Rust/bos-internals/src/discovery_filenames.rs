//! Bible project filename discovery logic.

use std::fs;
use std::path::{Path, PathBuf};
use compact_str::CompactString;
use bos_books_codes::BIBLE_BOOKS_CODES_ARRAY;
use std::collections::HashMap;
use crate::io::BOM;

/// Filenames to ignore during discovery.
pub const FILENAMES_TO_IGNORE: &[&str] = &[
    "AUTOCORRECT.TXT", "HYPHENATEDWORDS.TXT", "PRINTDRAFTCHANGES.TXT", "README.TXT", "BOOK_NAMES.TXT",
];

/// Filename endings to ignore (e.g., zip files).
pub const FILENAME_ENDINGS_TO_IGNORE: &[&str] = &[".ZIP.GO", ".ZIP.DATA"];

/// Extensions to ignore during discovery.
pub const EXTENSIONS_TO_IGNORE: &[&str] = &[
    "ASC", "BAK", "BAK2", "BAK3", "BAK4", "BBLX", "BC", "CCT", "CSS", "DOC", "DTS", "HTM", "HTML",
    "JAR", "LDS", "LOG", "MYBIBLE", "NT", "NTX", "ODT", "ONT", "ONTX", "OSIS", "OT", "OTX", "PDB",
    "SAV", "SAVE", "STY", "SSF", "VRS", "YET", "XML", "ZIP",
];

/// Bibledit standard filenames.
pub const BIBLEDIT_FILENAMES: &[&str] = &[
    "1_Genesis", "2_Exodus", "3_Leviticus", "4_Numbers", "5_Deuteronomy", "6_Joshua", "7_Judges", "8_Ruth", "9_1_Samuel", "10_2_Samuel",
    "11_1_Kings", "12_2_Kings", "13_1_Chronicles", "14_2_Chronicles", "15_Ezra", "16_Nehemiah", "17_Esther", "18_Job", "19_Psalms", "20_Proverbs", "21_Ecclesiastes",
    "22_Song_of_Solomon", "23_Isaiah", "24_Jeremiah", "25_Lamentations", "26_Ezekiel", "27_Daniel", "28_Hosea", "29_Joel", "30_Amos", "31_Obadiah", "32_Jonah",
    "33_Micah", "34_Nahum", "35_Habakkuk", "36_Zephaniah", "37_Haggai", "38_Zechariah", "39_Malachi",
    "40_Matthew", "41_Mark", "42_Luke", "43_John", "44_Acts", "45_Romans", "46_1_Corinthians", "47_2_Corinthians", "48_Galatians", "49_Ephesians", "50_Philippians",
    "51_Colossians", "52_1_Thessalonians", "53_2_Thessalonians", "54_1_Timothy", "55_2_Timothy", "56_Titus", "57_Philemon",
    "58_Hebrews", "59_James", "60_1_Peter", "61_2_Peter", "62_1_John", "63_2_John", "64_3_John", "65_Jude", "66_Revelation",
    "67_Front_Matter", "68_Back_Matter", "69_Other_Material", "70_Tobit", "71_Judith", "72_Esther_(Greek)", "73_Wisdom_of_Solomon", "74_Sirach", "75_Baruch",
    "76_Letter_of_Jeremiah", "77_Song_of_the_Three_Children", "78_Susanna", "79_Bel_and_the_Dragon", "80_1_Maccabees", "81_2_Maccabees",
    "82_1_Esdras", "83_Prayer_of_Manasses", "84_Psalm_151", "85_3_Maccabees", "86_2_Esdras", "87_4_Maccabees", "88_Daniel_(Greek)",
];

/// OEB-style alternate filenames.
pub const ALTERNATE_FILENAMES: &[&str] = &[
    "01-Genesis", "02-Exodus", "03-Leviticus", "04-Numbers", "05-Deuteronomy", "06-Joshua", "07-Judges", "08-Ruth", "09-1 Samuel", "10-2 Samuel",
    "11-1 Kings", "12-2 Kings", "13-1 Chronicles", "14-2 Chronicles", "15-Ezra", "16-Nehemiah", "17-Esther", "18-Job", "19-Psalms", "20-Proverbs", "21-Ecclesiastes",
    "22-Song-of-Solomon", "23-Isaiah", "24-Jeremiah", "25-Lamentations", "26-Ezekiel", "27-Daniel", "28-Hosea", "29-Joel", "30-Amos", "31-Obadiah", "32-Jonah",
    "33-Micah", "34-Nahum", "35-Habakkuk", "36-Zephaniah", "37-Haggai", "38-Zechariah", "39-Malachi",
    "40-Matthew", "41-Mark", "42-Luke", "43-John", "44-Acts", "45-Romans", "46-1 Corinthians", "47-2 Corinthians", "48-Galatians", "49-Ephesians", "50-Philippians",
    "51-Colossians", "52-1 Thessalonians", "53-2 Thessalonians", "54-1 Timothy", "55-2 Timothy", "56-Titus", "57-Philemon",
    "58-Hebrews", "59-James", "60-1 Peter", "61-2 Peter", "62-1 John", "63-2 John", "64-3 John", "65-Jude", "66-Revelation",
];

/// Options for filename discovery.
#[derive(Debug, Clone, Default)]
pub struct DiscoveryOptions {
    pub strict_check: bool,
}

/// Results of filename discovery.
#[derive(Debug, Clone, Default)]
pub struct DiscoveryResults {
    pub folder: PathBuf,
    pub pattern: CompactString,
    pub file_extension: CompactString,
    pub matched_files: Vec<(String, String)>, // (BBB, filename)
    pub unused_filenames: Vec<String>,
}

/// Try to get the BOS book code from the USFM book code on one of the first two lines of a file (should actually be on the first line).
pub fn get_code_from_usfm_id_line<P: AsRef<Path>>(path: P) -> Option<CompactString> {
    let file = fs::File::open(path).ok()?;
    let reader = std::io::BufReader::new(file);
    use std::io::BufRead;

    for (i, line_res) in reader.lines().enumerate() {
        if i >= 2 { break; }
        let mut line = line_res.ok()?;
        if i == 0 && line.starts_with(BOM) {
            line.remove(0);
        }
        let line = line.trim();
        if line.starts_with("\\id ") {
            let content = &line[4..].trim();
            let tokens: Vec<&str> = content.split_whitespace().collect();
            if tokens.is_empty() { continue; }
            
            let mut token0 = tokens[0].to_uppercase();
            // Port logic from Python
            if token0 == "I" { token0 = "1".to_string(); }
            else if token0 == "II" { token0 = "2".to_string(); }
            else if token0 == "III" { token0 = "3".to_string(); }
            else if token0 == "IV" { token0 = "4".to_string(); }
            else if token0 == "V" { token0 = "5".to_string(); }

            if matches!(token0.as_str(), "1" | "2" | "3" | "4" | "5") && tokens.len() >= 2 {
                token0.push_str(&tokens[1].to_uppercase());
            }

            if token0.starts_with("JUDG") {
                token0 = format!("J{}", &token0[2..]);
            }
            if token0.len() > 2 && matches!(token0.as_bytes()[1], b'_' | b'-') {
                token0 = format!("{}{}", &token0[0..1], &token0[2..]);
            }

            // Check if valid USFM abbreviation (ignoring case)
            if let Ok(bbb) = bos_books_codes::usfm_abbrev_to_bos_book_code(&token0, false) {
                return Some(CompactString::from(bbb));
            }
            // Try 3-char prefix
            if token0.len() >= 3 {
                if let Ok(bbb) = bos_books_codes::usfm_abbrev_to_bos_book_code(&token0[..3], false) {
                    return Some(CompactString::from(bbb));
                }
            }
        }
    }
    None
}

/// Try to get the BOS book code from the USX book code on one of the first few lines of the XML file
pub fn get_code_from_usx_xml<P: AsRef<Path>>(path: P) -> Option<CompactString> {
    let file = fs::File::open(path).ok()?;
    let reader = std::io::BufReader::new(file);
    use std::io::BufRead;

    let mut found_usx = false;
    for (i, line_res) in reader.lines().enumerate() {
        if i >= 10 { break; }
        let line = line_res.ok()?;
        if line.contains("<usx") {
            found_usx = true;
        }
        if found_usx {
            // Find book code in attributes (could be in <usx> or <book>)
            if let Some(pos) = line.find("code=\"") {
                let start = pos + 6;
                if let Some(end) = line[start..].find('"') {
                    // return Some(line[start..start+end].to_uppercase().to_compact_string());
                    // Check if valid USFM abbreviation (ignoring case)
                    if let Ok(bbb) = bos_books_codes::usfm_abbrev_to_bos_book_code(&line[start..start+end], false) {
                        return Some(CompactString::from(bbb));
                    }
                }
            }
        }
    }
    None
}

/// Unified discovery for ESFM/USFM/USX files.
pub fn discover_filenames<P: AsRef<Path>>(
    folder: P,
    is_usx: bool,
    _options: &DiscoveryOptions,
) -> Result<DiscoveryResults, Box<dyn std::error::Error>> {
    let mut results = DiscoveryResults {
        folder: folder.as_ref().to_path_buf(),
        ..Default::default()
    };

    let entries = fs::read_dir(&folder)?;
    let mut all_filenames = Vec::new();
    let mut file_list = Vec::new();

    for entry in entries {
        let entry = entry?;
        let path = entry.path();
        if !path.is_file() { continue; }
        
        let filename = path.file_name().unwrap().to_string_lossy().to_string();
        all_filenames.push(filename.clone());

        let upper_filename = filename.to_uppercase();
        if FILENAMES_TO_IGNORE.contains(&upper_filename.as_str()) { continue; }
        
        let mut ignore = false;
        for ending in FILENAME_ENDINGS_TO_IGNORE {
            if upper_filename.ends_with(ending) { ignore = true; break; }
        }
        if ignore || upper_filename.ends_with('~') { continue; }

        if let Some(ext) = path.extension().and_then(|s| s.to_str()) {
            let upper_ext = ext.to_uppercase();
            if EXTENSIONS_TO_IGNORE.contains(&upper_ext.as_str()) { continue; }
            if is_usx && upper_ext != "USX" { continue; }
            file_list.push(filename);
        }
    }

    log::info!("Read {} filenames, filtered down to {} for discovery in {:?}", all_filenames.len(), file_list.len(), folder.as_ref());

    // Pattern deduction and mapping
    let mut bbb_to_file = HashMap::new();
    let mut file_to_bbb = HashMap::new();

    // 1. Internal ID method (highest confidence)
    for filename in &file_list {
        let path = folder.as_ref().join(filename);
        let bbb_opt = if is_usx { get_code_from_usx_xml(&path) } else { get_code_from_usfm_id_line(&path) };
        if let Some(bbb) = bbb_opt {
            // if let Ok(bbb) = bos_books_codes::usfm_abbrev_to_bos_book_code(&id, false) {
            // let bbb_str = bbb.to_string();
            let bbb_str = bbb.to_string();
            bbb_to_file.insert(bbb_str.clone(), filename.clone());
            file_to_bbb.insert(filename.clone(), bbb_str);
            // }
        }
    }

    log::info!("Internal ID method matched {} files", bbb_to_file.len());

    // 2. Pattern Deduction and External Mapping
    if !file_list.is_empty() {
        // Try to deduce pattern from the first few matched files or just the file list
        let mut best_ext = CompactString::new("");
        let mut ext_counts = HashMap::new();
        for f in &file_list {
            if let Some(ext) = Path::new(f).extension().and_then(|s| s.to_str()) {
                *ext_counts.entry(ext.to_lowercase()).or_insert(0) += 1;
            }
        }
        if let Some((ext, _)) = ext_counts.into_iter().max_by_key(|&(_, count)| count) {
            best_ext = CompactString::from(ext);
        }
        results.file_extension = best_ext;

        // Deduction logic for self.pattern
        for filename in &file_list {
            if file_to_bbb.contains_key(filename) {
                // Deduce pattern from known mapping
                let bbb = &file_to_bbb[filename];
                let stem = Path::new(filename).file_stem().unwrap().to_string_lossy();
                let upper_stem = stem.to_uppercase();
                
                // Port deduction logic from Python
                // ... (simplified for now, focusing on triplets)
                for entry in BIBLE_BOOKS_CODES_ARRAY.iter() {
                    if entry.BOS_book_code == bbb {
                        let digits = if is_usx { entry.USX_number_str } else { entry.USFM_number_str };
                        let abbrev = entry.USFM_abbreviation;
                        
                        if let Some(d) = digits {
                            if let Some(pos_d) = upper_stem.find(d) {
                                let mut pat_chars: Vec<char> = stem.chars().map(|_| '*').collect();
                                // Replace digits in pattern
                                // Note: digits and abbrev are expected to be ASCII, so byte indices match char indices
                                for i in pos_d..pos_d + d.len() {
                                    if i < pat_chars.len() {
                                        pat_chars[i] = 'd';
                                    }
                                }

                                if let Some(a) = abbrev {
                                    if let Some(pos_a) = upper_stem.find(&a.to_uppercase()) {
                                        for i in pos_a..pos_a + a.len() {
                                            if i < pat_chars.len() {
                                                pat_chars[i] = 'b'; // We'll use 'b' for 'bbb'
                                            }
                                        }
                                    }
                                }
                                
                                // Convert back to string and refine (e.g. bbb instead of bbb, dd instead of dddd)
                                let mut pat = pat_chars.into_iter().collect::<String>();
                                while pat.contains("bb") { pat = pat.replace("bb", "b"); }
                                pat = pat.replace('b', "bbb");
                                while pat.contains("dd") { pat = pat.replace("dd", "d"); }
                                pat = pat.replace('d', "dd");
                                
                                results.pattern = CompactString::from(pat);
                                break;
                            }
                        }
                    }
                }
                if !results.pattern.is_empty() { break; }
            }
        }

        // External mapping for remaining files
        for filename in &file_list {
            if file_to_bbb.contains_key(filename) { continue; }
            
            let upper_filename = filename.to_uppercase();
            let stem = Path::new(&upper_filename).file_stem().unwrap().to_string_lossy();
            
            for entry in BIBLE_BOOKS_CODES_ARRAY.iter() {
                let usfm_digits = entry.USFM_number_str;
                let usfm_abbrev = entry.USFM_abbreviation;
                let usx_digits = entry.USX_number_str;
                let bbb = entry.BOS_book_code;

                if is_usx {
                    if let Some(d) = usx_digits {
                        if stem.contains(d) && stem.contains(bbb) {
                            bbb_to_file.insert(bbb.to_string(), filename.clone());
                            file_to_bbb.insert(filename.clone(), bbb.to_string());
                            break;
                        }
                    }
                } else {
                    if let Some(d) = usfm_digits {
                        if let Some(a) = usfm_abbrev {
                            let ua = a.to_uppercase();
                            if stem.contains(d) && (stem.contains(&ua) || stem.contains(bbb)) {
                                bbb_to_file.insert(bbb.to_string(), filename.clone());
                                file_to_bbb.insert(filename.clone(), bbb.to_string());
                                break;
                            }
                        }
                    }
                }
            }
        }
    }

    // Final sorting by sequence number
    let mut matched: Vec<(String, String)> = bbb_to_file.into_iter().collect();
    matched.sort_by_key(|(bbb, _)| bos_books_codes::get_sequence_number(bbb).unwrap_or(u16::MAX));

    results.matched_files = matched;
    results.unused_filenames = all_filenames.into_iter()
        .filter(|f| !file_to_bbb.contains_key(f))
        .collect();

    Ok(results)
}
