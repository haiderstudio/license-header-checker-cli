#!/bin/sh
# Copyright (c) 2026 Haider Ali
# SPDX-License-Identifier: MIT
#
# Run the checker on the bundled examples and show the report.
# The checker exits 1 because the examples contain files with
# bad headers; that is the point of the examples, so this script
# exits 0.
cd "$(dirname "$0")/.." || exit 2
python3 src/license_header_checker.py examples || true
