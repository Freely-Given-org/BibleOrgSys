"""
A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""
VERSION = '0.0.7'
LAST_MODIFIED_DATE = '2020-04-06' # by RJH — when setup.py was modified below

INCLUDE_DATA_SOURCE_FILES = False
INCLUDE_DERIVED_DATA_PICKLE_FILES = True
# INCLUDE_DERIVED_DATA_JSON_FILES = False


from setuptools import setup # Always prefer setuptools over distutils
# from os import path

# this_folderpath = path.abspath(path.dirname(__file__))

# Get the long description from the README file
#with open(path.join(this_folderpath, 'README.md'), encoding='utf-8') as f:
#    long_description = f.read()


package_data_list = []
if INCLUDE_DATA_SOURCE_FILES:
    package_data_list += [
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
Bible Organisational System / BibleOrgSys / BOS

A system for importing and extracting various book/chapter/verse (BCV) texts,
including Bibles of course, but also other related BCV materials like Bible commentaries.

NOTE: This packaging is still being tested following massive restructuring,
and is not necessarily fully functional until it is marked as v0.1.0 or higher.
We also have hopes to improve documentation before v0.2.0.

A future package of apps that use the BOS is also planned for release.
After that point, we also hope to release a Snap version.

This software has been developed in small chunks of spare time since 2010
(so it's not necessarily well-thought out, and definitely not polished).
However, it has been tested on hundreds of Bible filesets,
including USFM, OSIS, USX, USFX, and other import formats.

No attempt at all has been made at memory or speed optimisations
and this is not planned until after the release of v1.0.0.

This software forms the basis of the online Bible Drop Box service
hosted at http://Freely-Given.org/Software/BibleDropBox/.

This package will not reach v1.0.0 until versification mapping is added.

The API will not become fixed/stable until the v1.0.0 release.
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
    keywords="Bible index book chapter verse USFM USX",

    # This should be a valid link to your project's main homepage.
    #
    # This field corresponds to the "Home-Page" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#home-page-optional
    url="http://freely-given.org/Software/BibleOrganisationalSystem/",

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

    # This field lists other packages that your project depends on to run.
    # Any package you put here will be installed by pip when your project is
    # installed, so they must be valid existing projects.
    #
    # For an analysis of "install_requires" vs pip's requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    #install_requires=['peppercorn'],  # Optional

    # List additional groups of dependencies here (e.g. development
    # dependencies). Users will be able to install these using the "extras"
    # syntax, for example:
    #
    #   $ pip install sampleproject[dev]
    #
    # Similar to `install_requires` above, these must be valid existing
    # projects.
    #extras_require={  # Optional
    #    'dev': ['check-manifest'],
    #    'test': ['coverage'],
    #},

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
)
