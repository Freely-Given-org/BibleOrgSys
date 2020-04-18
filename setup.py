"""
A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""
from setuptools import setup # Always prefer setuptools over distutils
# from os import path

VERSION = '0.0.12'
LAST_MODIFIED_DATE = '2020-04-14' # by RJH — when setup.py was modified below


INCLUDE_DATA_SOURCE_FILES = False
INCLUDE_DERIVED_DATA_PICKLE_FILES = True
# INCLUDE_DERIVED_DATA_JSON_FILES = False


# this_folderpath = path.abspath(path.dirname(__file__))

# Get the long description from the README file
#with open(path.join(this_folderpath, 'README.md'), encoding='utf-8') as f:
#    long_description = f.read()


package_data_list = [
            'DataFiles/BibleBooksCodes.xml', 'DataFiles/BibleBooksCodes.rnc',
            'DataFiles/BibleOrganisationalSystems.xml', 'DataFiles/BibleOrganisationalSystems.rnc',
            'DataFiles/iso_639_3.xml', 'DataFiles/iso_639_3.rnc',
            'DataFiles/USFM2Markers.xml', 'DataFiles/USFM2Markers.rnc',
            'DataFiles/USFM3Markers.xml', 'DataFiles/USFM3Markers.rnc',

            'DataFiles/BookNames/BibleBooksNames.rnc',
            'DataFiles/BookNames/BibleBooksNames_deu_traditional.xml',
            'DataFiles/BookNames/BibleBooksNames_dut_traditional.xml',
            'DataFiles/BookNames/BibleBooksNames_eng_deuterocanon.xml',
            'DataFiles/BookNames/BibleBooksNames_eng_extensive.xml',
            'DataFiles/BookNames/BibleBooksNames_eng_traditional.xml',
            'DataFiles/BookNames/BibleBooksNames_fra_traditional.xml',
            'DataFiles/BookNames/BibleBooksNames_mbt.xml',
            'DataFiles/BookNames/BibleBooksNames_por_traditional.xml',
            'DataFiles/BookNames/BibleBooksNames_rus_traditional.xml',
            'DataFiles/BookNames/BibleBooksNames_spa_traditional.xml',

            'DataFiles/BookOrders/BibleBookOrder.rnc',
            'DataFiles/BookOrders/BibleBookOrder_ALL.xml',
            'DataFiles/BookOrders/BibleBookOrder_ArmenianNewTestament.xml',
            'DataFiles/BookOrders/BibleBookOrder_EthiopianProtestantBible.xml',
            'DataFiles/BookOrders/BibleBookOrder_EuropeanBible.xml',
            'DataFiles/BookOrders/BibleBookOrder_GutenbergNewTestament.xml',
            'DataFiles/BookOrders/BibleBookOrder_HebrewLetteris.xml',
            'DataFiles/BookOrders/BibleBookOrder_HebrewStuttgart.xml',
            'DataFiles/BookOrders/BibleBookOrder_KJVwithApocrypha.xml',
            'DataFiles/BookOrders/BibleBookOrder_Leningradensis.xml',
            'DataFiles/BookOrders/BibleBookOrder_LutheranBible.xml',
            'DataFiles/BookOrders/BibleBookOrder_MasoreticText.xml',
            'DataFiles/BookOrders/BibleBookOrder_ModernJewish.xml',
            'DataFiles/BookOrders/BibleBookOrder_NRSVwithApocrypha.xml',
            'DataFiles/BookOrders/BibleBookOrder_Septuagint.xml',
            'DataFiles/BookOrders/BibleBookOrder_SynodalBible.xml',
            'DataFiles/BookOrders/BibleBookOrder_SyriacNewTestament.xml',
            'DataFiles/BookOrders/BibleBookOrder_VulgateBible.xml',

            'DataFiles/PunctuationSystems/BiblePunctuationSystem.rnc',
            'DataFiles/PunctuationSystems/BiblePunctuationSystem_English_brief.xml',
            'DataFiles/PunctuationSystems/BiblePunctuationSystem_English.xml',
            'DataFiles/PunctuationSystems/BiblePunctuationSystem_Matigsalug.xml',

            'DataFiles/VersificationSystems/BibleVersificationSystem.rnc',
            'DataFiles/VersificationSystems/BibleVersificationSystem_BibMaxRef.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_CatholicEsther16.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Catholic.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Cebuano_BUGV.xml',
            '/DataFiles/VersificationSystems/BibleVersificationSystem_DutchTraditional.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_GNT92.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_GNTUK.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_KJV.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Luther.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_NIV84.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_NLT96.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_NRS89.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_NRSV.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Original.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Rahlfs.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_REB89.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_RSV52.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_RussianCanonical.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_RussianOrthodox.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Septuagint.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Spanish.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Synodal.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Syriac.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Vulgate1.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Vulgate2.xml',
            'DataFiles/VersificationSystems/BibleVersificationSystem_Vulgate.xml',
            ]
if INCLUDE_DERIVED_DATA_PICKLE_FILES:
    package_data_list += [
            'DataFiles/DerivedFiles/iso_639_3_Languages_Tables.pickle',
            'DataFiles/DerivedFiles/USFM2Markers_Tables.pickle',
            'DataFiles/DerivedFiles/USFM3Markers_Tables.pickle',

            'DataFiles/DerivedFiles/BibleBooksCodes_Tables.pickle',
            'DataFiles/DerivedFiles/BibleBooksNames_Tables.pickle',
            'DataFiles/DerivedFiles/BibleBookOrders_Tables.pickle',
            'DataFiles/DerivedFiles/BiblePunctuationSystems_Tables.pickle',
            'DataFiles/DerivedFiles/BibleVersificationSystems_Tables.pickle',
            'DataFiles/DerivedFiles/BibleOrganisationalSystems_Tables.pickle',

            'DistributedFiles/'
            ]
# if INCLUDE_DERIVED_DATA_JSON_FILES:
#     package_data_list += [
#                 'DataFiles/DerivedFiles/iso_639_3_Languages_Tables.json',
#                 'DataFiles/DerivedFiles/USFM2Markers_Tables.json',
#                 'DataFiles/DerivedFiles/USFM3Markers_Tables.json',

#                 'DataFiles/DerivedFiles/BibleBooksCodes_Tables.json',
#                 'DataFiles/DerivedFiles/BibleBooksNames_Tables.json',
#                 'DataFiles/DerivedFiles/BibleBookOrders_Tables.json',
#                 'DataFiles/DerivedFiles/BiblePunctuationSystems_Tables.json',
#                 'DataFiles/DerivedFiles/BibleVersificationSystems_Tables.json',
#                 'DataFiles/DerivedFiles/BibleOrganisationalSystems_Tables.json',
#                 ]


setup(
    name='BibleOrgSys',
    version=VERSION,

    packages=['BibleOrgSys',
            'BibleOrgSys.Apps',
            'BibleOrgSys.InputOutput',
            'BibleOrgSys.Internals',
            'BibleOrgSys.Formats',
            'BibleOrgSys.Misc',
            'BibleOrgSys.Online',
            'BibleOrgSys.OriginalLanguages',
            'BibleOrgSys.Reference',
            ],
    package_dir ={ 'BibleOrgSys': 'BibleOrgSys' },
    package_data={ 'BibleOrgSys': package_data_list },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    #
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],  # Optional

    # metadata to display on PyPI
    # This should be your name or the name of the organization which owns the project.
    author="Robert Hunt",
    author_email="Freely.Given.org+BOS@gmail.com",

    # This is a one-line description or tagline of what your project does. This
    # corresponds to the "Summary" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#summary
    description="Bible Organisational System — load, check, and/or export Bible files/folders",
    license='GPLv3',

    # This is an optional longer description of your project that represents
    # the body of text which users will see when they visit PyPI.
    #
    # Often, this is the same as your README, so you can just read it in from
    # that file directly (as we have already done above)
    #
    # This field corresponds to the "Description" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#description-optional
    long_description="""
**Bible Organisational System** / **BibleOrgSys** / **BOS**

A library of modules for importing and processing various book/chapter/verse (BCV) texts,
including Bibles of course, but also other related BCV materials like Bible commentaries.
Multiprocessing is used by default to load Bibles that have separate books in separate files.

This library also includes one app (similar to the demo app below) named **Bible2USX**
which can be run with:
    `Bible2USX path/to/BibleFileOrFolder`
or to view all the available options:
    `Bible2USX --help`
You can discover the version with:
    `Bible2USX --version`

The BibleOrgSys reads or creates a `BibleOrgSysData` folder in your home folder.
Log files are stored in a subfolder there and may be useful for reporting errors.
Output files will also be written by default into a sub-folder there.

NOTE: This packaging is still being tested following massive restructuring,
and is not necessarily fully functional until it is marked as v0.1.0 or higher.
We also have hopes to improve documentation before v0.2.0.

A future package of apps that use the BOS is also planned for release.
After that point, we also hope to release Docker and Snap versions.

This software has been developed in small chunks of spare time since 2010
(so it's not necessarily well-thought out, and definitely not polished).
However, it has been tested on hundreds of Bible filesets,
including USFM, OSIS, USX, USFX, and many other import formats.

This library forms the basis of the online Bible Drop Box service
hosted at http://Freely-Given.org/Software/BibleDropBox/.

This package will not reach v1.0.0 until versification mapping is added.

The API will not become fixed/stable until the v1.0.0 release.

Other than the multiprocessing mentioned above,
no attempt at all has been made at memory or speed optimisations
and this is not planned until after the release of v1.0.0.

Here is the code for a simple **Bible (e.g., USFM) to USX converter** using BibleOrgSys:

```
#!/usr/bin/env python3
#
# myBible2USX.py (minimal version)
#
# Command-line app to export a USX (XML) Bible.
#
# Copyright (C) 2019-2020 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# License: See gpl-3.0.txt
#
'''
A short command-line app as part of BOS (Bible Organisational System) demos.
This app inputs any known type of Bible file(s) from disk
    and then exports a USX version in the (default) BOSOutputFiles folder
        (inside the BibleOrgSys folder in your home folder).

Note that this app can be run from using the command:
        myBible2USX.py path/to/BibleFileOrFolder

You can discover the version with
        myBible2USX.py --version

You can discover the available command line parameters with
        myBible2USX.py --help

    e.g., for verbose mode
        myBible2USX.py --verbose path/to/BibleFileOrFolder
    or using the abbreviated option
        myBible2USX.py -v path/to/BibleFileOrFolder

This app also demonstrates how little code is required to use the BOS
    to load a Bible (in any of a large range of formats — see UnknownBible.py)
    and then to export it in your desired format (see options in BibleWriter.py).
'''
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.UnknownBible import UnknownBible

PROGRAM_NAME = "Bible to USX (minimal)"
PROGRAM_VERSION = '0.06'

# Configure basic Bible Organisational System (BOS) set-up
parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION )
parser.add_argument( "inputBibleFileOrFolder", help="path/to/BibleFileOrFolder" )
BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

# Do the actual Bible load and export work that we want
unknownBible = UnknownBible( BibleOrgSysGlobals.commandLineArguments.inputBibleFileOrFolder )
loadedBible = unknownBible.search( autoLoadAlways=True, autoLoadBooks=True ) # Load all the books if we find any
if not isinstance( loadedBible, str ): # i.e., not an error message
    loadedBible.toUSX2XML() # Export as USX files (USFM inside XML)
    vPrint( 'Quiet', debuggingThisModule, f"\\nOutput should be in {BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USX2_Export/' )}/ folder." )

# Do the BOS close-down stuff
BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
```

The BOS is developed and well-tested on Linux (Ubuntu) but also runs on Windows (although not so well tested).

See https://ubsicap.github.io/usfm/ for more information about USFM.

See https://ubsicap.github.io/usx/ for more information about USX.
""",
#    long_description=long_description,

    # Denotes that our long_description is in Markdown; valid values are
    # text/plain, text/x-rst, and text/markdown
    #
    # Optional if long_description is written in reStructuredText (rst) but
    # required for plain-text or Markdown; if unspecified, "applications should
    # attempt to render [the long_description] as text/x-rst; charset=UTF-8 and
    # fall back to text/plain if it is not valid rst" (see link below)
    #
    # This field corresponds to the "Description-Content-Type" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#description-content-type-optional
    long_description_content_type='text/markdown',

    # This field adds keywords for your project which will appear on the
    # project page. What does your project relate to?
    #
    # Note that this is a string of words separated by whitespace, not a list.
    keywords="Bible Scripture check import export index book chapter verse USFM USX",

    # This should be a valid link to your project's main homepage.
    #
    # This field corresponds to the "Home-Page" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#home-page-optional
    url="http://Freely-Given.org/Software/BibleOrganisationalSystem/",

    # List additional URLs that are relevant to your project as a dict.
    #
    # This field corresponds to the "Project-URL" metadata fields:
    # https://packaging.python.org/specifications/core-metadata/#project-url-multiple-use
    #
    # Examples listed include a pattern for specifying where the package tracks
    # issues, where the source is hosted, where to say thanks to the package
    # maintainers, and where to support the project financially. The key is
    # what's used to render the link text on PyPI.
    #project_urls={  # Optional
    #    'Bug Reports': 'https://github.com/pypa/sampleproject/issues',
    #    'Funding': 'https://donate.pypi.org',
    #    'Say Thanks!': 'http://saythanks.io/to/example',
    #    'Source': 'https://github.com/pypa/sampleproject/',
    #},
    project_urls={
        #"Bug Tracker": "https://bugs.example.com/HelloWorld/",
        #"Documentation": "https://docs.example.com/HelloWorld/",
        "Source Code": "https://github.com/openscriptures/BibleOrgSys/",
    },

    # Classifiers help users find your project by categorizing it.
    #
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        # How mature is this project? Common values are
        #   1 - Planning
        #   2 - Pre-Alpha
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 2 - Pre-Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Religion',
        'Topic :: Religion',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        # These classifiers are *not* checked by 'pip install'. See instead
        # 'python_requires' below.
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',

        'Operating System :: OS Independent',
    ],

    # Specify which Python versions you support. In contrast to the
    # 'Programming Language' classifiers above, 'pip install' will check this
    # and refuse to install the project if the version does not match. If you
    # do not support Python 2, you can simplify this to '>=3.5' or similar, see
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires
    python_requires='>=3.7',

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # `pip` to create the appropriate form of executable for the target
    # platform.
    #
    # For example, the following would provide a command called `sample` which
    # executes the function `main` from this package when invoked:
    # entry_points={  # Optional
    #     'console_scripts': [
    #         'sample=sample:main',
    #     ],
    # },
    entry_points={
        'console_scripts': [
            'myBible2USX=BibleOrgSys.Apps.myBible2USX:run',
        ],
    },
)
