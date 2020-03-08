"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

lastModifiedDate = '2020-03-08' # by RJH

# Always prefer setuptools over distutils
from setuptools import setup
from os import path

this_folderpath = path.abspath(path.dirname(__file__))

# Get the long description from the README file
#with open(path.join(this_folderpath, 'README.md'), encoding='utf-8') as f:
#    long_description = f.read()


# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    # This is the name of your project. The first time you publish this
    # package, this name will be registered for you. It will determine how
    # users can install this project, e.g.:
    #
    # $ pip install sampleproject
    #
    # And where it will live on PyPI: https://pypi.org/project/sampleproject/
    #
    # There are some restrictions on what makes a valid project name
    # specification here:
    # https://packaging.python.org/specifications/core-metadata/#name
    name='BibleOrgSys',

    # Versions should comply with PEP 440:
    # https://www.python.org/dev/peps/pep-0440/
    #
    # For a discussion on single-sourcing the version across setup.py and the
    # project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.0.2',

    # You can just specify package directories manually here if your project is
    # simple. Or you can use find_packages().
    #
    # Alternatively, if you just want to distribute a single Python file, use
    # the `py_modules` argument instead as follows, which will expect a file
    # called `my_module.py` to exist:
    #
    #   py_modules=["my_module"],
    #
    #packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    # packages=find_packages(),
    packages=['','Formats', 'InputOutput', 'Internals', 'Misc', 'Online', 'OriginalLanguages', 'Reference'],
      package_dir={'':'BibleOrgSys',
                   'Formats':'BibleOrgSys/Formats',
                   'InputOutput':'BibleOrgSys/Formats',
                   'Internals':'BibleOrgSys/Internals',
                   'Misc':'BibleOrgSys/Misc',
                   'Online':'BibleOrgSys/Online',
                   'OriginalLanguages':'BibleOrgSys/OriginalLanguages',
                   'Reference':'BibleOrgSys/Reference',
                   },

    # If there are data files included in your packages that need to be
    # installed, specify them here.
    # package_data={  # Optional
    #     'sample': ['package_data.dat'],
    # },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    #
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],  # Optional
    data_files=[('DataFiles', [
                    'DataFiles/BibleBooksCodes.xml', 'DataFiles/BibleBooksCodes.rnc',
                    'DataFiles/BibleOrganisationalSystems.xml', 'DataFiles/BibleOrganisationalSystems.rnc',
                    'DataFiles/iso_639_3.xml', 'DataFiles/iso_639_3.rnc',
                    'DataFiles/USFM2Markers.xml', 'DataFiles/USFM2Markers.rnc',
                    'DataFiles/USFM3Markers.xml', 'DataFiles/USFM3Markers.rnc',
                    ]),
                ('DataFiles/BookNames', [
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
                    ]),
                ('DataFiles/BookOrders', [
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
                    ]),
                ('DataFiles/PunctuationSystems', [
                    'DataFiles/PunctuationSystems/BiblePunctuationSystem.rnc',
                    'DataFiles/PunctuationSystems/BiblePunctuationSystem_English_brief.xml',
                    'DataFiles/PunctuationSystems/BiblePunctuationSystem_English.xml',
                    'DataFiles/PunctuationSystems/BiblePunctuationSystem_Matigsalug.xml',
                    ]),
                ('DataFiles/VersificationSystems', [
                    'DataFiles/VersificationSystems/BibleVersificationSystem.rnc',
                    'DataFiles/VersificationSystems/BibleVersificationSystem_BibMaxRef.xml',
                    'DataFiles/VersificationSystems/BibleVersificationSystem_CatholicEsther16.xml',
                    'DataFiles/VersificationSystems/BibleVersificationSystem_Catholic.xml',
                    'DataFiles/VersificationSystems/BibleVersificationSystem_Cebuano_BUGV.xml',
                    'DataFiles/VersificationSystems/BibleVersificationSystem_DutchTraditional.xml',
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
                    ]),
                ],

    # metadata to display on PyPI
    # This should be your name or the name of the organization which owns the project.
    author="Robert Hunt",
    author_email="Freely.Given.org+BOS@gmail.com",

    # This is a one-line description or tagline of what your project does. This
    # corresponds to the "Summary" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#summary
    description="Bible Organisational System",
    license='GPLv3',

    # This is an optional longer description of your project that represents
    # the body of text which users will see when they visit PyPI.
    #
    # Often, this is the same as your README, so you can just read it in from
    # that file directly (as we have already done above)
    #
    # This field corresponds to the "Description" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#description-optional
    long_description="A system for importing and extracting various chapter/verse texts.",
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
        'Development Status :: 1 - Planning',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Religion',
        'Topic :: Religion',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        # These classifiers are *not* checked by 'pip install'. See instead
        # 'python_requires' below.
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',

        'Operating System :: OS Independent',
    ],

    # Specify which Python versions you support. In contrast to the
    # 'Programming Language' classifiers above, 'pip install' will check this
    # and refuse to install the project if the version does not match. If you
    # do not support Python 2, you can simplify this to '>=3.5' or similar, see
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires
    #python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4',
    python_requires='>=3.6',

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

