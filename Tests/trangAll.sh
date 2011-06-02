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
# Author: Robert Hunt <robert316@users.sourceforge.net>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

