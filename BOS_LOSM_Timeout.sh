#!/bin/bash
#
# BOS_LOSM_Timeout
#
# Linux shell script to kill LibreOffice ServiceManager after a timeout
#
# This is called from the BOS (BibleOrganizationalSystem) BibleWriter.py (on Linux only)
#
# Written: February 2018 by R.J. Hunt
#
# Last modified: 2018-02-28 by RJH
# Public domain
#

# Timeout should be the maximum it takes to process one long book
/bin/sleep 200s

# Hopefully this script will be killed before it gets this far
/usr/bin/pkill -kill -f "ServiceManager"
