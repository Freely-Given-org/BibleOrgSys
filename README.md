BOS README.md

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

## Introduction

The Bible Organisational System (BibleOrgSys or BOS) came from starting to write Python code to read and display Bibles back in 2010.
It didn't take too many little projects, before realising that they had things in common, especially the need to iterate through Bible "books", chapters, and verses.

The other realisation was the need for data standards, e.g., for Bible Books codes, Bible abbreviations (for linking from one Bible resource to another), etc., etc.
So this project was begun (after playing with JSON and rejecting it for inability to include comments) by hand-crafting some XML files for data sets.
(XML was chosen for being a standard that could be loaded into most computer language systems, and hence usable by others beyond this Python library.)
These can be found in the [DataFiles](BibleOrgSys/DataFiles/) folder.
Each of these datafiles also has a "converter" script to load, validate, and convert the data into Python lists and dicts (and from there, easily exportable as JSON or pickles or whatever).

This led on to writing modules to provide an API for these datasets which can be found in the [Reference](BibleOrgSys/Reference/) folder.

Other modules to import and export various Bible formats can be found in the [Formats](BibleOrgSys/Formats/) folder.

An internal, indexed Bible resource representation was created as seen in the [Internals](BibleOrgSys/Internals/) folder.
The internal representation is based on [USFM](https://ubsicap.github.io/usfm/) lines (because USFM is used in real life for MANY Bible translations) along with some additional, custom markers for additional fields and also to ease processing (such as segment end markers).

(More of the original design thinking and (oldish) documentation can be seen in the [Documentation](Documentation/) folder.)

Eventually the BibleOrgSys became the basis for the Freely-Given.org [Bible Drop Box](https://Freely-Given.org/Software/BibleDropBox/) service which had the benefit of enabling the library to become robust enough to handle Bible formats in various stages of correctness.

## Essential requirements for an easy-to-use Bible library

1. A way to define a Bible along with metadata (such as name, abbreviation, copyright, licence, etc., etc.)
1. Must be able to handle original language (Hebrew, Greek) Bibles as well as translations in any world language
2. A way to iterate "works", "books", chapters, and verses (W/B/C/V)
2. A way to communicate this W/B/C/V information between windows and even between apps -- see [here](https://GitHub.com/Freely-Given-org/biblesync)
3. A way to map between different versifications, i.e., the numbering of chapters and verses can differ but we still want to find the same content. (NOTE: Allow versification mapping is allowed for in most parts of the system, this vital part has never been completed -- see [here](https://github.com/Copenhagen-Alliance/versification-specification) for more information on what is expected.)
1. A standard, internal Bible representation
4. Parsers to read various different Bible formats into the internal representation -- these might be individual files or folders of files (which can be loaded by multiple threads)
4. The parsers require a strict mode to catch and document errors (for a Bible translator trying to fix/improve their work) and also a forgiving mode to load a Bible file into a reader even if it's not perfect
5. Exporters to write various different Bible formats from the internal representation
9. A way to integrate additional resources (such as Bible dictionaries) with internal Bibles (e.g., to create a Bible-study app)

## Current plans (Feb 2023)

An old version of BibleOrgSys is on PyPI, but we are in the (slow) process of breaking BibleOrgSys into smaller components and putting each of them separately onto PyPI. We hope to implement versification mapping and complete the PyPI uploading by the end of 2024.

We are also investigating ways of speeding up the system including:

1. C or Rust functions for CPython
2. Python compilers such as PyPy or Py2Exe or PyInstaller
3. A stand-alone Rust or Go Bible compiler (to build to our internal Bible format)
