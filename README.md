# Bible Organisational System (BibleOrgSys or BOS)

Python library for processing Bibles in various formats


<table>
    <tr>
        <td>License</td>
        <td><img src='https://img.shields.io/pypi/l/BibleOrgSys.svg'></td>
        <td>Version</td>
        <td><img src='https://img.shields.io/pypi/v/BibleOrgSys.svg'></td>
    </tr>
    <tr>
        <td>Travis CI</td>
        <td><img src='https://travis-ci.org/openscriptures/BibleOrgSys.svg?branch=restructure'></td>
        <td>Coverage</td>
        <td><img src='https://codecov.io/gh/openscriptures/BibleOrgSys/branch/restructure/graph/badge.svg'></td>
    </tr>
    <tr>
        <td>Wheel</td>
        <td><img src='https://img.shields.io/pypi/wheel/BibleOrgSys.svg'></td>
        <td>Implementation</td>
        <td><img src='https://img.shields.io/pypi/implementation/BibleOrgSys.svg'></td>
    </tr>
    <tr>
        <td>Status</td>
        <td><img src='https://img.shields.io/pypi/status/BibleOrgSys.svg'></td>
        <td>Downloads</td>
        <td><img src='https://img.shields.io/pypi/dm/BibleOrgSys.svg'></td>
    </tr>
    <tr>
        <td>Supported versions</td>
        <td><img src='https://img.shields.io/pypi/pyversions/BibleOrgSys.svg'></td>
    </tr>
</table>

## Getting started

BibleOrgSys requires Python 3.13+ and uses [uv](https://docs.astral.sh/uv/) for project management.

```bash
# Clone and set up
git clone https://github.com/Freely-Given-org/BibleOrgSys.git
cd BibleOrgSys
uv sync

# Run the included Bible2USX converter
uv run Bible2USX path/to/BibleFileOrFolder

# Run tests
uv run python -m pytest Tests/

# Use as a library
uv run python -c "from BibleOrgSys import BibleOrgSysGlobals"

# Run type checking. currently this produces alot of errors
uv run ty 
```

The project includes a Rust extension (`bibleorgsys-rust`) built with [maturin](https://www.maturin.rs/) and [PyO3](https://pyo3.rs/) for performance-critical internals. `uv sync` handles building and linking it automatically via the workspace configuration.

## Introduction

The Bible Organisational System (BibleOrgSys or BOS) came from starting to write Python3 code to read and display Bibles back in 2010.
It didn't take too many little projects, before realising that they had things in common, especially the need to iterate through Bible ‘books’, chapters, and verses.

The other realisation was the need for data standards, e.g., for Bible Books codes, Bible abbreviations (for linking from one Bible resource to another), etc., etc.
So this project was begun (after playing with JSON and rejecting it for inability to include comments) by hand-crafting some XML files for data sets.
(XML was chosen for being a standard that could be loaded into most computer language systems, and hence usable by others beyond this Python library.)
These can be found in the [DataFiles](BibleOrgSys/DataFiles/) folder.
Each of these datafiles also has a ‘converter’ script to load, validate, and convert the data into Python lists and dicts (and from there, easily exportable as JSON or pickles or whatever).

This led on to writing modules to provide an API for these datasets which can be found in the [Reference](BibleOrgSys/Reference/) folder.

Other modules to import and export various Bible formats can be found in the [Formats](BibleOrgSys/Formats/) folder.

An internal, indexed Bible resource representation was created as seen in the [Internals](BibleOrgSys/Internals/) folder.
The internal representation is based on [USFM](https://ubsicap.github.io/usfm/) lines (because USFM is used in real life for MANY Bible translations) along with some additional, custom markers for additional fields and also to ease processing (such as segment end markers).

(More of the original design thinking and (oldish) documentation can be seen in the [Documentation](Documentation/) folder.)

Eventually the BibleOrgSys became the basis for the Freely-Given.org [Bible Drop Box](https://Freely-Given.org/Software/BibleDropBox/) service which had the benefit of enabling the library to become robust enough to handle Bible formats in various stages of correctness and completeness, i.e., it can also handle ‘in-progress’ Bible translations.

## Primary functions of the BibleOrgSys

1. To load a Bible representation into memory. Some Bible formats use a single file for the entire Bible, others (like USFM and ESFM) use a separate file for each Bible ‘book’. There are also ways to add metadata (like copyright, version, licence, etc.) to the actual verse data.
2. Many checks are done as the Bible is loaded. If you just want to display someone else's Bible, that's not so important. However, it will be important if you're working on a Bible translation and want to have your formatting checked.
3. That internal Bible representation must then be serialisable. Currently we use the Python [pickle](https://docs.python.org/3/library/pickle.html) format for that. Of course, it will be MUCH faster to load the pre-processed InternalBible class that has been serialised, than loading and checking the original Bible text (or occassionally binary) files line by line.
4. Once the Bible object or objects are checked and loaded, there are two main functions of the library:
   1. Export the internal Bible to a different format, or
   2. Use the API to extract single or multiple verses in order to use or display them in your Python program, e.g., [Biblelator](https://github.com/Freely-Given-org/Biblelator) uses BibleOrgSys (and [tkinter](https://docs.python.org/3/library/tkinter.html)) to make a ESFM Bible-editor. The [getContextVerseData](https://github.com/Freely-Given-org/BibleOrgSys/blob/main/BibleOrgSys/Internals/InternalBible.py#L2274) function is one that's commonly used.

## Essential requirements for an easy-to-use Bible library

1. A way to define a Bible along with metadata (such as name, abbreviation, publication year, translators, copyright, licence, etc., etc.)
1. Must be able to handle original language (Hebrew, Greek) Bibles as well as translations in any world language (including RTL languages)
2. A way to iterate through works, ‘books’, chapters, and verses (W/B/C/V)
2. A way to communicate this W/B/C/V information between windows and even between apps -- see [here](https://GitHub.com/Freely-Given-org/biblesync)
3. A way to map between different versifications, i.e., the numbering of chapters and verses can differ but we still want to find the same content. (NOTE: Although versification mapping is allowed for in most parts of the system, this vital part has never been completed -- see [here](https://github.com/Copenhagen-Alliance/versification-specification) for more information on what is expected.)
1. A standard, internal Bible representation
4. Parsers to read various different Bible formats into the internal representation -- these might be individual files or folders of files (which can be loaded by multiple threads)
4. The parsers require a strict mode to catch and document errors (for a Bible translator trying to fix/improve their work) and also a forgiving mode to load a Bible file into a reader even if it's not perfect
5. Exporters to write various different Bible formats from the internal representation
9. A way to integrate additional resources (such as Bible dictionaries) with internal Bibles (e.g., to create a Bible-study app)

## Importers

1. These can be found in the [Formats](BibleOrgSys/Formats/) folder.
2. The importers are expected to remain in Python. This is because Bible files are typically human edited and until very recently, there's been no reference implementation of even the the most commonly used formats -- [USFM, USX, and the new USJ](https://github.com/usfm-bible/tcdocs). This has meant that hand-crafted Bible files from the previous several decades (such as those available for download from [eBible.org](https://ebible.org/download.php)) tend to require much manual correction to be able to load them and ignore any inconsistencies and/or errors. It's easier to most people to be able to do this in Python rather than Rust.
3. It should be noted that many Bible formats (especially the most commonly used USFM) very designed in floppy disk days, and only contain the basic biblical text like headings and the actual verses. They don't necessarily contain metadata like the copyright owner, the revision year or number, the licence, the [versification system](https://github.com/Copenhagen-Alliance/versification-specification), etc.

## Internal Bible representation

1. The InternalBible class contains an ordered collection (list) of InternalBibleBook instances.
2. InternalBibleBook classes contain a number of ‘processed lines’ (derived from the ‘raw lines’ that were read from the file). Each processed line represents a single line of [USFM paragraph markers](https://github.com/usfm-bible/tcdocs/tree/main/markers) with their optional text contents (which might include [USFM character markers](https://github.com/usfm-bible/tcdocs/tree/main/markers/char) and/or [footnote](https://github.com/usfm-bible/tcdocs/blob/main/markers/note/f.adoc) or [cross-reference](https://github.com/usfm-bible/tcdocs/blob/main/markers/note/x.adoc) markers), or it might be [ESFM paragraph markers](https://github.com/Freely-Given-org/ESFM) which is a superset of USFM and which likely contain word numbers attached by ‘¦’ to each word in the translation and that refer to a row in an associated ‘word table’.

## Exporters

1. Someof these can be found beside their importers in the [Formats](BibleOrgSys/Formats/) folder, but most are in a single, huge [BibleWriter file](https://github.com/Freely-Given-org/BibleOrgSys/blob/main/BibleOrgSys/BibleWriter.py).
2. These exporters should be broken into separate modules and moved to a separate Exporters folder, and can be rewritten in Rust.


## Strictness modes

1. BibleOrgSys can run in three strictness modes. This mostly applies to the importers.
2. The default mode is to try to handle any inconsistencies or minor user errors, but to issue an error or warning as seems appropriate.
3. The --strict (-c) mode is intended for the creator of a Bible translation (or editor of a Hebrew or Greek Bible) to be able to stop and fix any errors or inconsistencies in their work, and then restart the program.
4. The --mission-critical (-m) mode (not yet very developed) is intended for use in automated build systems where we want the BibleOrgSys to continue through as many errors as possible -- trying to deduce what might be a reasonable automatic correction.

## Verboseness modes

1. There are three sets of command line flags that influence what is output to the user. The default is for critical errors to be displayed, along with a summary of what major steps the package is about to execute.
2. If the --warnings (-w) or --errors (-e) flags are given, then warning and/or error messages will be displayed on the console.
3. If the --quiet (-q) or --silent (-s) flag is given, then less progress output will displayed or none at all.
4. If the --informative (-i) or --verbose (-v) flag is given, then more progress output will be displayed.
5. If the --debug (-d) flag is given, a lot of additional debug output is displayed.

## Multiprocessing modes

1. The BibleOrgSys is designed to make good use multicore CPUs using the Python multiprocessing library. If, for example, a certain Bible format has each Bible ‘book’ in a separate file, it will try to use all the cores to load them simultaneously. (This can cause any warning messages from processing various ‘books’ to be interspersed.)
2. The --single (-1) flag is given, then only a single CPU core will be used. This is commonly used for debugging (and is also forced on by the --debug flag) so that progress and warning & error messages are output to the console in a sensible order in order to track down where a fault is occurring.

## To Do

1. **Rust internals**: Some internals have been written in Rust with PyO3 interfaces to save memory and improve speed, but the Python code is not yet using those Rust functions. They need testing and integration.
2. **API consistency**: Some functions begin with 'make' and others with 'create' — should be standardised.
3. **Versification mapping**: The package will not reach v1.0.0 until versification mapping is completed.
4. **Codebase modernisation**: Migrate `os.path` calls to `pathlib`, convert `.format()` to f-strings, break up the monolithic `BibleWriter.py` into separate exporter modules.
