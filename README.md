# license-header-checker-cli

Check source files carry the right license header, fail CI on a missing header.

[![CI](https://github.com/haiderstudio/license-header-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/license-header-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`license_header_checker` reads a source file and checks it starts
with the expected license header — by default a MIT-style
`Copyright (c) <year> <owner>` line plus an
`SPDX-License-Identifier: MIT` line — and reports every file that
is missing it or has a wrong one, with the file and the line
number. It exits 1 when any problem is found, so it can fail a
CI run. A clean file exits 0.

- A file shipped without its license header is a real problem:
  nobody can tell under what terms the code may be used, and
  some teams refuse to accept it at all. This tool catches the
  missing header before the file ships, and points at the exact
  line.
- The wrong year or the wrong owner is reported as its own
  problem, not a vague mismatch — so a header copied from
  another project is caught, not just a missing one.
- A header that sits below the code is reported too: the header
  has to be at the top of the file, after an optional shebang
  line. A shebang (`#!/usr/bin/env python3` and the like) is
  allowed at the very top; anything else before the header
  fails the file.
- Comment styles are picked from the file extension: `#` for
  `.py`, `.sh` and `.rb`; `//` (or a `/* */` block) for `.js`,
  `.ts`, `.java`, `.c`, `.h`, `.cpp`, `.go` and `.rs`. A file
  given directly on the command line is always checked,
  whatever its name. A folder is walked for source files only,
  recursively by default (`--no-recursive` stops at the top
  level). `.git` folders are never walked, and directory links
  are never followed. `--exclude` skips files and folders by
  name pattern.
- The expected header is configurable: `--year` and `--owner`
  change the copyright line, `--spdx` changes the identifier
  (`--no-spdx` drops that line), and `--header-file` reads the
  whole expected header from a file, one line per line.
- `--json` prints the result as JSON (the human-readable lines
  go to standard error), and `--stdin` checks one file read
  from standard input (`--as` says the comment style, e.g.
  `--as js`).

## Who it is for

Anyone who ships source code under a licence — open-source
maintainers, teams that require a header on every file, and
anyone who has ever found a file in their repo with no licence
terms on it at all.

## What it does NOT do

- It does not add or fix a header. That is a formatter's job,
  not a checker's — this tool is report-only, and it never
  touches a file. If you want a tool that writes headers for
  you, use one of the fixers named below.
- It does not check whether the licence itself is valid, or
  whether two licences in one project conflict. It checks one
  thing: the header at the top of the file matches the one you
  asked for.
- It does not check the licence of a dependency. That is a
  different tool entirely.
- It never touches the network.

## How this differs

- fast/hawkeye (188 stars) is a license header checker and
  formatter — it checks headers, and it can also write and
  reformat them. This tool only checks: it never writes a
  file, so it can sit in CI as a strict gate with no risk of
  a run rewriting your code.
- apache/skywalking-eyes (317 stars) is a full-featured
  license tool: it checks and fixes headers, and it also
  resolves the licences of your dependencies. This tool is
  the small slice — headers only, one job, standard library
  only, no build step.
- lluissm/license-header-checker (35 stars) checks headers
  and can also insert or replace them. This tool checks only.
- There is no exact-name rival: a GitHub search for
  `"license-header-checker-cli"` returns 0 results
  (checked Nov 8, 2026).

## Install

Python 3.10 or newer, nothing else to install.

```sh
git clone https://github.com/haiderstudio/license-header-checker-cli.git
cd license-header-checker-cli
```

## Usage

Check one clean file:

```sh
python3 src/license_header_checker.py examples/good.py
```

```text
OK — 1 file(s) checked, all source files carry the right license header.
```

Check a file with no header:

```sh
python3 src/license_header_checker.py examples/missing-header.py
```

```text
examples/missing-header.py:1: missing license header
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

The exit code is 1, so a CI run fails.

Check a file with the wrong year:

```sh
python3 src/license_header_checker.py examples/wrong-year.js
```

```text
examples/wrong-year.js:1: wrong year in license header: found 2025, expected 2026
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Check a file with the wrong owner, in a block comment:

```sh
python3 src/license_header_checker.py examples/wrong-owner.java
```

```text
examples/wrong-owner.java:2: wrong owner in license header: found 'Jane Doe', expected 'Haider Ali'
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Check a file whose header sits below the code:

```sh
python3 src/license_header_checker.py examples/header-not-top.sh
```

```text
examples/header-not-top.sh:4: license header is not at the top of the file (copyright line on line 4)
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Check a whole folder:

```sh
python3 src/license_header_checker.py examples
```

```text
examples/header-not-top.sh:4: license header is not at the top of the file (copyright line on line 4)
examples/missing-header.py:1: missing license header
examples/wrong-owner.java:2: wrong owner in license header: found 'Jane Doe', expected 'Haider Ali'
examples/wrong-year.js:1: wrong year in license header: found 2025, expected 2026
Checked 8 file(s), 4 problem(s) in 4 file(s).
```

Check one file from standard input:

```sh
printf '# Copyright (c) 2026 Haider Ali\n# SPDX-License-Identifier: MIT\nprint(1)\n' | python3 src/license_header_checker.py --stdin
```

```text
OK — 1 file(s) checked, all source files carry the right license header.
```

Check against a different year:

```sh
python3 src/license_header_checker.py examples/good.py --year 2025
```

```text
examples/good.py:2: wrong year in license header: found 2026, expected 2025
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Machine-readable output:

```sh
python3 src/license_header_checker.py examples/wrong-year.js --json
```

```json
{
  "files_checked": 1,
  "problems": [
    {
      "file": "examples/wrong-year.js",
      "line": 1,
      "reason": "wrong year in license header: found 2025, expected 2026"
    }
  ],
  "files_with_problems": 1
}
```

## Examples

- `examples/good.py` — a clean Python file: shebang, then the
  right header, then code. Passes.
- `examples/good.js` — a clean JavaScript file with a `//`
  header. Passes.
- `examples/missing-header.py` — no header at all. Fails with
  exit 1.
- `examples/wrong-year.js` — the header says 2025, not 2026.
  Fails with exit 1.
- `examples/wrong-owner.java` — a `/* */` block header with
  the wrong owner. Fails with exit 1.
- `examples/header-not-top.sh` — the header sits below the
  code, not at the top. Fails with exit 1.
- `examples/configs/good.rs` — a clean Rust file in a
  subfolder. Passes.
- `sh examples/run-example.sh` runs the checker on the whole
  `examples/` folder. Its output is in
  `examples/sample-output.md`.

## How it is tested

```sh
python3 tests/test_license_header_checker.py
```

The tests cover: the default and custom headers, comment
styles per extension, clean files (shebang, blank lines
before the header, `//` headers, `/* */` blocks, one-line
blocks, Javadoc-style blocks, extra lines after the header),
missing headers (no header, empty file, code after a
shebang, a different comment instead of a header), wrong
headers (wrong year, wrong owner, both at once, wrong SPDX,
missing SPDX line, header not at the top), files on disk
(non-UTF-8, missing file, a direct file with any
extension), folder walking (source files only, `.git`
skipped, `--no-recursive`, `--exclude`, extension filter,
dedupe), the command line (`--stdin`, `--json`, `--year`,
`--no-spdx`, `--header-file`, usage errors, exit codes
0/1/2), and the bundled examples (the sample output is
compared byte-for-byte against a fresh run, and the outputs
quoted in this README are checked against real runs). The
repo's own Python files carry the header too, and a test
checks they pass it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea of
checking license headers is a common one — hawkeye,
skywalking-eyes and the others named above do related jobs —
but the code, the wording, and the tests are original.
