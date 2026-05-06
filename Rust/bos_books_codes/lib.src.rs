//WARNINGS_GO_HERE

#![allow(non_snake_case)]
// #![allow(unused)]

use std::error::Error;
use std::fmt;

use phf::phf_map;

//STATIC_STRUCTS_GO_HERE


#[derive(Debug, PartialEq)]
pub enum LookupError<'a> {
    AbbrevNotFound(&'a str, &'a str),
    // ValueIsNone(String),
}

impl<'a> fmt::Display for LookupError<'a> {
    #[inline]
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LookupError::AbbrevNotFound(t,k) => write!(f, "{} abbreviation '{}' not found", t,k),
            // LookupError::ValueIsNone(k) => write!(f, "Key '{}' found but value is None", k),
        }
    }
}

impl Error for LookupError<'_> {}


#[inline]
pub fn is_valid_reference_abbreviation(reference_abbreviation: &str) -> bool {
    REFERENCE_ABBREVIATION_MAP.contains_key(reference_abbreviation)
}

#[inline]
fn get_array_index(reference_abbreviation: &str) -> Result<usize, LookupError<'_>> {
    REFERENCE_ABBREVIATION_MAP.get(reference_abbreviation)
        .copied()
        .ok_or_else(|| LookupError::AbbrevNotFound("Reference", reference_abbreviation))
}

pub fn get_reference_number(reference_abbreviation: &str) -> Result<u16, LookupError<'_>> {
    let array_index = get_array_index(reference_abbreviation)?;
    Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_reference_number)
}

pub fn get_bbb_from_reference_number(reference_number: u16) -> Option<&'static str> {
    BIBLE_BOOKS_CODES_ARRAY.iter()
        .find(|e| e.BOS_reference_number == reference_number)
        .map(|e| e.BOS_reference_abbreviation)
}

pub fn get_all_reference_abbreviations() -> Vec<&'static str> {
    BIBLE_BOOKS_CODES_ARRAY.iter()
        .map(|e| e.BOS_reference_abbreviation)
        .collect()
}

pub fn get_all_osis_abbreviations() -> Vec<&'static str> {
    BIBLE_BOOKS_CODES_ARRAY.iter()
        .filter_map(|e| e.OSIS_abbreviation)
        .collect()
}

pub fn get_sequence_list() -> Vec<&'static str> {
    let mut entries: Vec<_> = BIBLE_BOOKS_CODES_ARRAY.iter().collect();
    entries.sort_by_key(|e| e.BOS_sequence_number);
    entries.into_iter()
        .map(|e| e.BOS_reference_abbreviation)
        .collect()
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn is_ot_nr(reference_abbreviation: &str) -> bool {
    if let Ok(num) = get_reference_number(reference_abbreviation) {
        return 1 <= num && num <= 39;
    }
    false
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn is_nt_nr(reference_abbreviation: &str) -> bool {
    if let Ok(num) = get_reference_number(reference_abbreviation) {
        return 40 <= num && num <= 66;
    }
    false
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn is_dc_nr(reference_abbreviation: &str) -> bool {
    matches!(reference_abbreviation, "TOB"|"JDT"|"ESG"|"WIS"|"SIR"|"BAR"|"LJE"|"PAZ"|"SUS"|"BEL"|"MA1"|"MA2"|"GES"|"LES"|"MAN")
}

pub fn get_ccel_number(reference_abbreviation: &str) -> Option<u16> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].CCEL_number)
}

pub fn get_short_abbreviation(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].short_abbreviation)
}

pub fn get_sbl_abbreviation(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].SBL_abbreviation)
}

pub fn get_osis_abbreviation(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].OSIS_abbreviation)
}

pub fn get_sword_abbreviation(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Sword_abbreviation)
}

pub fn get_usfm_num_str(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].USFM_number_str)
}

pub fn get_usx_num_str(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].USX_number_str)
}

pub fn get_unbound_bible_code(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Unbound_Code)
}

pub fn get_bibledit_num_str(reference_abbreviation: &str) -> Option<u16> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Bibledit_number)
}

pub fn get_possible_alternative_books(reference_abbreviation: &str) -> Vec<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .map(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].possible_alternative_books_codes.to_vec())
        .unwrap_or_default()
}

pub fn get_logos_num_str(reference_abbreviation: &str) -> Option<u16> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Logos_number)
}

pub fn get_net_bible_abbreviation(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].NET_Bible_abbreviation)
}

pub fn get_drupal_bible_abbreviation(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Drupal_Bible_abbreviation)
}

pub fn get_byzantine_abbreviation(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].Byzantine_abbreviation)
}

pub fn get_expected_chapters_list(reference_abbreviation: &str) -> Vec<u16> {
    if let Ok(idx) = get_array_index(reference_abbreviation) {
        match BIBLE_BOOKS_CODES_ARRAY[idx].expected_num_chapters {
            OptionalNumberOrTwoNumbers::Number(n) => vec![n],
            OptionalNumberOrTwoNumbers::TwoNumbers(nums) => vec![nums[0], nums[1]],
            OptionalNumberOrTwoNumbers::None => vec![],
        }
    } else {
        vec![]
    }
}

pub fn get_max_chapters(reference_abbreviation: &str) -> i16 {
    let list = get_expected_chapters_list(reference_abbreviation);
    if list.is_empty() {
        -1
    } else {
        *list.iter().max().unwrap() as i16
    }
}

pub fn get_single_chapter_books_list() -> Vec<&'static str> {
    BIBLE_BOOKS_CODES_ARRAY.iter()
        .filter(|e| matches!(e.expected_num_chapters, OptionalNumberOrTwoNumbers::Number(1)))
        .map(|e| e.BOS_reference_abbreviation)
        .collect()
}

pub fn get_osis_single_chapter_books_list() -> Vec<&'static str> {
    BIBLE_BOOKS_CODES_ARRAY.iter()
        .filter(|e| matches!(e.expected_num_chapters, OptionalNumberOrTwoNumbers::Number(1)))
        .filter_map(|e| e.OSIS_abbreviation)
        .collect()
}

pub fn is_single_chapter_book(reference_abbreviation: &str) -> bool {
    if let Ok(idx) = get_array_index(reference_abbreviation) {
        return matches!(BIBLE_BOOKS_CODES_ARRAY[idx].expected_num_chapters, OptionalNumberOrTwoNumbers::Number(1));
    }
    false
}

pub fn is_chapter_verse_book(reference_abbreviation: &str) -> bool {
    if let Ok(idx) = get_array_index(reference_abbreviation) {
        return !matches!(BIBLE_BOOKS_CODES_ARRAY[idx].expected_num_chapters, OptionalNumberOrTwoNumbers::None);
    }
    false
}

pub fn get_typical_section(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .and_then(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].typical_section)
}

pub fn continues_through_chapters(reference_abbreviation: &str) -> bool {
    !matches!(reference_abbreviation, "PSA" | "PS2" | "LAM")
}

pub fn get_book_name(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .map(|idx| BIBLE_BOOKS_CODES_ARRAY[idx].original_language_book_name)
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn get_english_name_nr(reference_abbreviation: &str) -> Option<&'static str> {
    get_array_index(reference_abbreviation).ok()
        .map(|idx| {
            let guide = BIBLE_BOOKS_CODES_ARRAY[idx].book_name_English_guide;
            guide.split('/').next().unwrap_or(guide).trim()
        })
}

// nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
pub fn get_english_name_list_nr(reference_abbreviation: &str) -> Vec<&'static str> {
    if let Ok(idx) = get_array_index(reference_abbreviation) {
        BIBLE_BOOKS_CODES_ARRAY[idx].book_name_English_guide
            .split('/')
            .map(|s| s.trim())
            .collect()
    } else {
        vec![]
    }
}

pub fn tidy_bbb(bbb: &str, title_case: bool, allow_four_chars: bool, insert_char: &str) -> String {
    if title_case {
        if allow_four_chars {
            match bbb {
                "RUT" => return "Ruth".to_string(),
                "SA1" => return format!("1{}Sam", insert_char),
                "SA2" => return format!("2{}Sam", insert_char),
                "CH1" => return format!("1{}Chr", insert_char),
                "CH2" => return format!("2{}Chr", insert_char),
                "EZR" => return "Ezra".to_string(),
                "PRO" => return "Prov".to_string(),
                "JOL" => return "Joel".to_string(),
                "AMO" => return "Amos".to_string(),
                "MA1" => return format!("1{}Mac", insert_char),
                "MA2" => return format!("2{}Mac", insert_char),
                "MA3" => return format!("3{}Mac", insert_char),
                "MA4" => return format!("4{}Mac", insert_char),
                "MRK" => return "Mark".to_string(),
                "LUK" => return "Luke".to_string(),
                "JHN" => return "John".to_string(),
                "ACT" => return "Acts".to_string(),
                "CO1" => return format!("1{}Cor", insert_char),
                "CO2" => return format!("2{}Cor", insert_char),
                "TI1" => return format!("1{}Tim", insert_char),
                "TI2" => return format!("2{}Tim", insert_char),
                "PE1" => return format!("1{}Pet", insert_char),
                "PE2" => return format!("2{}Pet", insert_char),
                "JN1" => return format!("1{}Jhn", insert_char),
                "JN2" => return format!("2{}Jhn", insert_char),
                "JN3" => return format!("3{}Jhn", insert_char),
                "JDE" => return "Jude".to_string(),
                _ => {}
            }
        }
        let bbb_chars: Vec<char> = bbb.chars().collect();
        if bbb_chars.len() >= 3 && bbb_chars[2].is_ascii_digit() {
            return format!("{}{}{}{}", bbb_chars[2], insert_char, bbb_chars[0], bbb_chars[1].to_lowercase());
        } else {
            return format!("{}{}", bbb_chars[0], bbb[1..].to_lowercase());
        }
    }

    if allow_four_chars {
        match bbb {
            "RUT" => return "RUTH".to_string(),
            "SA1" => return format!("1{}SAM", insert_char),
            "SA2" => return format!("2{}SAM", insert_char),
            "CH1" => return format!("1{}CHR", insert_char),
            "CH2" => return format!("2{}CHR", insert_char),
            "EZR" => return "EZRA".to_string(),
            "PRO" => return "PROV".to_string(),
            "JOL" => return "JOEL".to_string(),
            "AMO" => return "AMOS".to_string(),
            "MA1" => return format!("1{}MAC", insert_char),
            "MA2" => return format!("2{}MAC", insert_char),
            "MA3" => return format!("3{}MAC", insert_char),
            "MA4" => return format!("4{}MAC", insert_char),
            "MRK" => return "MARK".to_string(),
            "LUK" => return "LUKE".to_string(),
            "JHN" => return "JOHN".to_string(),
            "ACT" => return "ACTS".to_string(),
            "CO1" => return format!("1{}COR", insert_char),
            "CO2" => return format!("2{}COR", insert_char),
            "TI1" => return format!("1{}TIM", insert_char),
            "TI2" => return format!("2{}TIM", insert_char),
            "PE1" => return format!("1{}PET", insert_char),
            "PE2" => return format!("2{}PET", insert_char),
            "JN1" => return format!("1{}JHN", insert_char),
            "JN2" => return format!("2{}JHN", insert_char),
            "JN3" => return format!("3{}JHN", insert_char),
            "JDE" => return "JUDE".to_string(),
            _ => {}
        }
    }

    let bbb_chars: Vec<char> = bbb.chars().collect();
    if bbb_chars.len() >= 3 && bbb_chars[2].is_ascii_digit() {
        return format!("{}{}{}", bbb_chars[2], insert_char, &bbb[0..2]);
    }

    bbb.to_string()
}

#[inline]
pub fn reference_abbrev_to_usfm_abbrev<'a>(
    reference_abbreviation: &str,
) -> Result<Option<&'static str>, LookupError<'_>> {
    let array_index = *REFERENCE_ABBREVIATION_MAP.get(reference_abbreviation)
        .ok_or_else(|| LookupError::AbbrevNotFound("Reference", reference_abbreviation))?;

    Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].USFM_abbreviation)
        // .as_ref()
        // .ok_or_else(|| Box::new(LookupError::ValueIsNone(reference_abbreviation.to_string())) as Box<dyn Error>)?)
}

#[inline]
pub fn usfm_abbrev_to_reference_abbrev<'a>(
    usfm_abbreviation: &'a str,
) -> Result<&'static str, LookupError<'a>> {
    // println!("usfm_abbrev_to_reference_abbrev for {}", &usfm_abbreviation);
    // let USFM_ABBREVIATION_MAP: HashMap<&str, usize> = hash_map!{ "NEG"=>1,"OXE"=>2,"VEL"=>3,};
    // println!("The unmutable hash map is {:?}", USFM_ABBREVIATION_MAP);
    // let mut USFMAbbreviationDict: HashMap<&str, usize> = HashMap::new();
    // println!(
    //     "USFMAbbreviationDict length = {}",
    //     USFMAbbreviationDict.len()
    // );

    // if USFMAbbreviationDict.len() == 0 {
    //     // we need to create the index
    //     for (i, el) in BIBLE_BOOKS_CODES_ARRAY.iter().enumerate() {
    //         println!("The current element is {:#?}", el);
    //         USFMAbbreviationDict.insert(el.usfm_abbreviation, i);
    //     }
    //     println!("The new hash map is {:?}", USFMAbbreviationDict);
    // }
    if let Some(&array_index) = USFM_ABBREVIATION_MAP.get(usfm_abbreviation) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_reference_abbreviation)
    } else if let Some(&array_index) = UPPERCASE_USFM_ABBREVIATION_MAP.get(usfm_abbreviation) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_reference_abbreviation)
    } else {
        Err(LookupError::AbbrevNotFound("USFM", usfm_abbreviation))
    }
}

#[inline]
pub fn osis_abbrev_to_reference_abbrev<'a>(
    osis_abbreviation: &'a str,
) -> Result<&'static str, LookupError<'a>> {
    if let Some(&array_index) = OSIS_ABBREVIATION_MAP.get(osis_abbreviation) {
        Ok(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_reference_abbreviation)
    } else {
        Err(LookupError::AbbrevNotFound("OSIS", osis_abbreviation))
    }
}

pub fn english_name_to_reference_abbrev(english_name: &str,) -> Option<&'static str> {
    let adj_english_name = english_name.to_uppercase();
    if let Some(&array_index) = ENGLISH_NAME_MAP.get(&adj_english_name) {
        return Some(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_reference_abbreviation)
    }

    let pairs = [
        ("1.", "1"), ("I ", "1"), ("I.", "1"),
        ("2.", "2"), ("II ", "2"), ("II.", "2"),
        ("3.", "3"), ("III ", "3"), ("III.", "3"),
        ("4.", "4"), ("IV ", "4"), ("IV.", "4"),
        ("5.", "5"), ("V ", "5"), ("V.", "5"),
        ("6.", "6"), ("VI ", "6"), ("VI.", "6"),
    ];

    for (s1, s2) in pairs {
        if adj_english_name.starts_with(s1) {
            if let Some(&array_index) = ENGLISH_NAME_MAP.get(&format!("{}{}", s2, &adj_english_name[s1.len()..])) {
                return Some(BIBLE_BOOKS_CODES_ARRAY[array_index].BOS_reference_abbreviation)
            }
        }
    }

    None
}

// pub fn usfm_num_to_usfm_abbreviation(usfm_num_str: &str) -> Result<String, Box<dyn Error>> {
//     println!("usfm_num_to_usfm_bbb for {:?}", usfm_num_str);
//     if !&self.USFMNumberDict.contains_key(usfm_num_str) {
//         return Err("Invalid USFM number: '".to_owned() + &usfm_num_str + "'")?; // I never actually figured out why I need the question mark?
//     }
//     let bbbStringOrListOfStrings =
//         &self.USFMNumberDict[usfm_num_str].USFMAbbreviationOrAbbreviations;
//     match bbbStringOrListOfStrings {
//         StringOrListOfStrings::Abbreviation(bbb) => Ok(bbb.to_string()),
//         StringOrListOfStrings::ListOfAbbreviations(bbb_list) => Ok(bbb_list[0].to_string()),
//     }
// }

// pub fn usfm_num_to_reference_abbreviation(usfm_num_str: &str) -> Result<String, Box<dyn Error>> {
//     println!("usfm_num_to_usfm_bbb for {:?}", usfm_num_str);
//     if !&self.USFMNumberDict.contains_key(usfm_num_str) {
//         return Err("Invalid USFM number: '".to_owned() + &usfm_num_str + "'")?; // I never actually figured out why I need the question mark?
//     }
//     let bbbStringOrListOfStrings =
//         &self.USFMNumberDict[usfm_num_str].referenceAbbreviationOrAbbreviations;
//     match bbbStringOrListOfStrings {
//         StringOrListOfStrings::Abbreviation(bbb) => Ok(bbb.to_string()),
//         StringOrListOfStrings::ListOfAbbreviations(bbb_list) => Ok(bbb_list[0].to_string()),
//     }
// }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loaded_books_codes() {
        println!(
            "    Loaded Bible books codes data for {:?} books.",
            BIBLE_BOOKS_CODES_ARRAY.len()
        );
        assert_eq!(
            BIBLE_BOOKS_CODES_ARRAY.len(),
            REFERENCE_ABBREVIATION_MAP.len()
        );
        assert!(BIBLE_BOOKS_CODES_ARRAY.len() > USFM_ABBREVIATION_MAP.len());
    }

    #[test]
    fn test_is_valid_reference_abbreviation() {
        assert_eq!(is_valid_reference_abbreviation("SAM"), true);
        assert_eq!(is_valid_reference_abbreviation("SIM"), false);
    }

    #[test]
    fn test_reference_abbrev_to_usfm_abbrev() {
        assert_eq!(reference_abbrev_to_usfm_abbrev("EXO"), Ok(Some("Exo")));
        assert_eq!(reference_abbrev_to_usfm_abbrev("CH1"), Ok(Some("1Ch")));
        println!(
            "    reference_abbrev_to_usfm_abbrev for 'SAM' got {:?}",
            reference_abbrev_to_usfm_abbrev("SAM")
        );
        println!(
            "    reference_abbrev_to_usfm_abbrev for 'XyZ' got {:?}",
            reference_abbrev_to_usfm_abbrev("XyZ")
        );
        assert_eq!(reference_abbrev_to_usfm_abbrev("SAM"), Ok(None));
        assert!(matches!(reference_abbrev_to_usfm_abbrev("XyZ"), Err(LookupError::AbbrevNotFound("Reference",ref key)) if *key == "XyZ"));
        assert!(matches!(reference_abbrev_to_usfm_abbrev("XyZ"), Err(LookupError::AbbrevNotFound("Reference","XyZ"))));
    }

    #[test]
    fn test_usfm_to_reference_abbreviation() {
        assert_eq!(usfm_abbrev_to_reference_abbrev("Exo"), Ok("EXO"));
        assert_eq!(usfm_abbrev_to_reference_abbrev("1Ki"), Ok("KI1"));
        assert_eq!(usfm_abbrev_to_reference_abbrev("MAT"), Ok("MAT"));
        assert_eq!(usfm_abbrev_to_reference_abbrev("1PE"), Ok("PE1"));
        assert!(usfm_abbrev_to_reference_abbrev("XyZ").is_err());
        assert!(matches!(usfm_abbrev_to_reference_abbrev("XyZ"), Err(LookupError::AbbrevNotFound("USFM","XyZ"))));
    }

    #[test]
    fn test_osis_to_reference_abbreviation() {
        assert_eq!(osis_abbrev_to_reference_abbrev("Exod"), Ok("EXO"));
        assert!(osis_abbrev_to_reference_abbrev("XyZ").is_err());
        assert!(matches!(osis_abbrev_to_reference_abbrev("XyZ"), Err(LookupError::AbbrevNotFound("OSIS","XyZ"))));
    }

    #[test]
    fn test_english_name_to_reference_abbrev() {
        assert_eq!(english_name_to_reference_abbrev("Exodus"), Some("EXO"));
        assert_eq!(english_name_to_reference_abbrev("Esther"), Some("EST"));
        assert_eq!(english_name_to_reference_abbrev("Ester"), Some("EST"));
        assert_eq!(english_name_to_reference_abbrev("Eccle"), Some("ECC"));
        assert_eq!(english_name_to_reference_abbrev("1 Cor"), Some("CO1"));
        assert_eq!(english_name_to_reference_abbrev("1 Co"), Some("CO1"));
        assert_eq!(english_name_to_reference_abbrev("1Cor"), Some("CO1"));
        assert_eq!(english_name_to_reference_abbrev("1Co"), Some("CO1"));
        assert_eq!(english_name_to_reference_abbrev("1.Cor"), Some("CO1"));
        assert_eq!(english_name_to_reference_abbrev("1.Co"), Some("CO1"));
        assert_eq!(english_name_to_reference_abbrev("XyZ"), None);
    }

    #[test]
    fn test_book_metadata_lookups() {
        assert_eq!(get_bbb_from_reference_number(1), Some("GEN"));
        assert_eq!(get_bbb_from_reference_number(66), Some("REV"));
        assert_eq!(get_bbb_from_reference_number(999), Some("UNK"));
        assert_eq!(get_bbb_from_reference_number(1000), None);

        assert_eq!(get_ccel_number("GEN"), Some(1));
        assert_eq!(get_short_abbreviation("GEN"), Some("Ge"));
        assert_eq!(get_sbl_abbreviation("GEN"), Some("Gen"));
        assert_eq!(get_osis_abbreviation("GEN"), Some("Gen"));
        assert_eq!(get_sword_abbreviation("GEN"), Some("Gen"));
        assert_eq!(get_usfm_num_str("MAT"), Some("41"));
        assert_eq!(get_usx_num_str("MAT"), Some("040"));
        assert_eq!(get_unbound_bible_code("GEN"), Some("01O"));
        assert_eq!(get_bibledit_num_str("MAT"), Some(40));
        assert_eq!(get_logos_num_str("MAT"), Some(61));
        assert_eq!(get_net_bible_abbreviation("SNG"), Some("Sos"));
        assert_eq!(get_drupal_bible_abbreviation("SNG"), Some("Son"));
        assert_eq!(get_byzantine_abbreviation("MAT"), Some("MT"));
    }

    #[test]
    fn test_chapter_lookups() {
        assert_eq!(get_expected_chapters_list("EST"), vec![10]);
        assert_eq!(get_expected_chapters_list("PSA"), vec![150, 151]);
        assert_eq!(get_expected_chapters_list("XyZ"), vec![]);

        assert_eq!(get_max_chapters("PSA"), 151);
        assert_eq!(get_max_chapters("EST"), 10);
        assert_eq!(get_max_chapters("XyZ"), -1);

        assert!(is_single_chapter_book("PHM"));
        assert!(!is_single_chapter_book("GEN"));
        assert!(is_chapter_verse_book("GEN"));

        let osis_single = get_osis_single_chapter_books_list();
        assert!(osis_single.contains(&"Phlm"));
        assert!(!osis_single.contains(&"Gen"));
    }

    #[test]
    fn test_categorization() {
        // nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
        assert!(is_ot_nr("GEN"));
        assert!(!is_ot_nr("TOB"));
        assert!(!is_ot_nr("MAT"));
        assert!(is_nt_nr("MAT"));
        assert!(!is_nt_nr("TOB"));
        assert!(!is_nt_nr("GEN"));
        assert!(is_dc_nr("TOB"));
        assert!(!is_dc_nr("GEN"));
        assert!(!is_dc_nr("MRK"));

        assert!(!is_ot_nr("FRT"));
        assert!(!is_nt_nr("FRT"));
        assert!(!is_dc_nr("FRT"));

        assert_eq!(get_typical_section("GEN"), Some("OT"));
        assert_eq!(get_typical_section("MAT"), Some("NT"));
        assert!(continues_through_chapters("GEN"));
        assert!(!continues_through_chapters("PSA"));
    }

    #[test]
    fn test_name_lookups() {
        assert_eq!(get_book_name("GEN"), Some("בְּרֵאשִׁית"));
        // nr stands for "Not Recommended" (because ideally the proper versification functions should be used instead)
        assert_eq!(get_english_name_nr("GEN"), Some("Genesis"));
        assert_eq!(get_english_name_list_nr("GEN"), vec!["Genesis", "1 Moses"]);
    }

    #[test]
    fn test_tidy_bbb() {
        assert_eq!(tidy_bbb("SA1", false, true, ""), "1SAM");
        assert_eq!(tidy_bbb("SA1", true, true, ""), "1Sam");
        assert_eq!(tidy_bbb("SA1", true, true, " "), "1 Sam");
        assert_eq!(tidy_bbb("GEN", true, true, ""), "Gen");
        assert_eq!(tidy_bbb("RUT", true, true, ""), "Ruth");
        assert_eq!(tidy_bbb("SA1", false, false, "-"), "1-SA");
    }
}

//WARNINGS_GO_HERE
