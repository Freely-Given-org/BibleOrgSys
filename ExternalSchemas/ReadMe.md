BibleOrgSys Schemas ReadMe
==========================

Last updated: 2018-03-01 by RJH

This folder contains schemas for EXTERNALLY DEFINED data files.
    (Our internal BOS schemas are in the DataFiles folder.)

On Linux, to convert to RNG, use
      trang xyz.rnc DerivedFiles/xyz.rng
On Linux, to validate against the .rng file, use
      xmllint --noout --relaxng DerivedFiles/xyz.rng xyz.xml
or to validate against both this and the internal DTD, use
      xmllint --noout --relaxng DerivedFiles/xyz.rng --valid xyz.xml
