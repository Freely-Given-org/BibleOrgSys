## Copenhagen Alliance Versification Sniffing

### Overview

The versification sniffer processes input files in various formats (`USX`, `USFM`, and `CSV`) to generate a custom versification file in JSON format. The main steps involve reading the input files, parsing the verse data, and applying versification rules to map verses according to a predefined set of rules. The output can also include a detailed versification file if specified.

### Input Formats

The program supports three main input formats:

1. **USX**: 
   - USX (Unified Standard XML) is a standardized XML format used to represent Bible texts.
   - The `USX_parser` class reads USX files and extracts verses from them, organizing the data into a structured dictionary for further processing.

2. **USFM**:
   - USFM (Unified Standard Format Markers) is a plain text format with markup used to represent Bible texts.
   - The `USFM_parser` class converts USFM files into a structured dictionary by parsing them into JSON format using an external library (`usfm-grammar`).

3. **CSV**:
   - CSV (Comma-Separated Values) files should contain a header and four fields: `Book`, `Chapter`, `Verse`, and `Text`.
   - The `CSV_parser` class reads these files and organizes the data into a structured dictionary for further processing.

### Processing Flow

1. **Input Parsing**:
   - The selected parser (`USX_parser`, `USFM_parser`, or `CSV_parser`) reads the input files from a specified directory, extracting the verses and organizing them into a dictionary with the structure:
     ```python
     books = {
       "BOOK_CODE": {
         chapter_number: {
           "verse_number": "verse_text"
         }
       }
     }
     ```

2. **Versification Mapping**:
   - The `Sniffer` class processes the structured verse data, applying versification mappings and rules to create a custom versification file.
   - It handles tasks such as determining the maximum verse numbers for each chapter, identifying partial verses, and applying complex mappings defined in a rules file (`merged_rules.json`).

3. **Output Generation**:
   - The final output is a JSON file containing the custom versification data, which can be saved to a specified output directory. If requested, additional versification details can also be generated.

### Command-Line Interface

The program can be executed from the command line with the following arguments:

- `-n`, `--name`: **Required**. The short name of the text (e.g., "NRSVUK" or "ESV"), which should match the input directory name.
- `-f`, `--format`: **Required**. The input file format (`usx`, `usfm`, `csv`).
- `-i`, `--indir`: Path to the directory containing input files (default: `../../data/`).
- `-o`, `--outdir`: Directory for the output (default: `../../data/output/`).
- `-m`, `--mappings`: Directory containing versification mappings (default: `../../versification-mappings/standard-mappings`).
- `-r`, `--rules`: Path to the merged rules file for mapping verses (default: `../rules/merged_rules.json`).
- `-v`, `--vrs`: Flag to generate versification in addition to the JSON file (default: `False`).

### Example Usage

```bash
python script_name.py -n "ESV" -f "usx" -i "../../data/input/" -o "../../data/output/" -m "../../versification-mappings/standard-mappings" -r "../rules/merged_rules.json" -v True
```

This command will create a custom versification file for the `ESV` text, using `USX` formatted input files, and save the output in the specified directory.

### Error Handling

- The program includes various checks to ensure the integrity of the input data, such as validating book codes, chapter numbers, and verse numbers.
- Logging is used extensively to record the progress and potential issues during execution, with logs saved to `debug2.log`.

### Dependencies

- Python libraries: `os`, `re`, `logging`, `subprocess`, `csv`, `argparse`, `lxml`, `json`
- External library: `usfm-grammar` (for parsing USFM files)

### Conclusion

This program offers a flexible solution for processing Bible texts from various formats and generating custom versification files, suitable for a wide range of textual analysis and comparison tasks.
