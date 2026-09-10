#!/bin/sh
#
# trangAll.sh
#
#   Last modified: 2011-06-02 by RJH
#
# Create the rng files for the RNC schema files in the DataFiles folder
# This should be run from the BibleOrgSys folder
#       e.g., Tests/trangAll.sh
#
# Copyright (C) 2010-2011 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

dataFolder="DataFiles"
outputFolder="$dataFolder/DerivedFiles"

echo "Creating RelaxNG files from rnc files..."

# In the main data files folder
trang $dataFolder/iso_639_3.rnc $outputFolder/iso_639_3.rng
trang $dataFolder/BibleBooksCodes.rnc $outputFolder/BibleBooksCodes.rng
trang $dataFolder/USFMMarkers.rnc $outputFolder/USFMMarkers.rng
trang $dataFolder/BibleOrganizationalSystems.rnc $outputFolder/BibleOrganizationalSystems.rng

# In data files subfolders
trang $dataFolder/VersificationSystems/BibleVersificationSystem.rnc $outputFolder/BibleVersificationSystem.rng
trang $dataFolder/PunctuationSystems/BiblePunctuationSystem.rnc $outputFolder/BiblePunctuationSystem.rng
trang $dataFolder/BookOrders/BibleBookOrder.rnc $outputFolder/BibleBookOrder.rng
trang $dataFolder/BookNames/BibleBooksNames.rnc $outputFolder/BibleBooksNames.rng

