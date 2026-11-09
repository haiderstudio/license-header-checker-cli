# Copyright (c) 2026 Haider Ali
# SPDX-License-Identifier: MIT
"""license-header-checker-cli: check source files carry the right license header, fail CI on a missing header.

Reads one or more source files (or folders of them), checks each one
starts with the expected license header — by default a MIT-style
"Copyright (c) <year> <owner>" line plus an SPDX identifier — and
reports every file that is missing it or has a wrong one, with the
file and the line number. Report-only: it never rewrites a file.
Exit 0 when every file is clean, 1 when any problem is found, 2 for
a usage error.

A header may sit after a shebang line (#!/usr/bin/env python3 and
the like), which is allowed at the very top. Anything else before
the header — code, a blank line, a different comment — means the
header is not at the top, and the file fails.

Comment styles are picked from the file extension: '#' for .py,
.sh and .rb; '//' (or a /* */ block) for .js, .ts, .java, .c,
.h, .cpp, .go and .rs. Files given directly are always checked,
whatever their extension; a folder is walked for source files
only. Use --as to say the style of a file whose extension the
tool does not know.
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

__version__ = "1.0.0"

DEFAULT_YEAR = "2026"
DEFAULT_OWNER = "Haider Ali"
DEFAULT_SPDX = "MIT"

HASH_EXTENSIONS = {"py", "sh", "rb"}
SLASH_EXTENSIONS = {"js", "ts", "jsx", "tsx", "java", "c", "h",
                    "cpp", "cc", "hpp", "go", "rs"}
KNOWN_EXTENSIONS = HASH_EXTENSIONS | SLASH_EXTENSIONS

COPYRIGHT_RE = re.compile(
    r"^Copyright\s+(?:\(c\)|©)\s+(\d{4})\s+(.+?)\s*$", re.IGNORECASE)
SPDX_RE = re.compile(r"^SPDX-License-Identifier:\s*(\S+)\s*$")


class Problem:
    """One problem in one file: path, line number, plain reason."""

    def __init__(self, path, line, reason):
        self.path = path
        self.line = line
        self.reason = reason

    def text(self):
        return f"{self.path}:{self.line}: {self.reason}"

    def as_dict(self):
        return {"file": self.path, "line": self.line, "reason": self.reason}


def default_header(year=DEFAULT_YEAR, owner=DEFAULT_OWNER,
                   spdx=DEFAULT_SPDX):
    """The expected header lines, plain text without comment marks."""
    lines = [f"Copyright (c) {year} {owner}"]
    if spdx:
        lines.append(f"SPDX-License-Identifier: {spdx}")
    return lines


def style_for(extension):
    """The comment style for an extension: 'hash', 'slash', or None."""
    ext = extension.lower().lstrip(".")
    if ext in HASH_EXTENSIONS:
        return "hash"
    if ext in SLASH_EXTENSIONS:
        return "slash"
    return None


def _line_comment_content(line, marker):
    """The text of a line comment, marker and whitespace removed."""
    stripped = line.strip()
    if not stripped.startswith(marker):
        return None
    return stripped[len(marker):].strip()


def _block_comment_content(line):
    """The text of one line inside a /* */ block comment."""
    s = line.strip()
    if s.startswith("/*"):
        s = s[2:]
    if s.endswith("*/"):
        s = s[:-2]
    s = s.strip()
    if s.startswith("*"):
        s = s[1:].strip()
    return s


def _top_comment_block(lines, style):
    """The comment lines at the top of a file, as plain text.

    `lines` is the file split into lines. Returns a list of
    (line_number, text) pairs — each comment line with its
    marker removed — or [] when there is no comment block at
    the top. A shebang line and blank lines before the block
    are skipped.
    """
    idx = 0
    if lines and lines[0].startswith("#!"):
        idx = 1
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return []
    if style == "slash" and lines[idx].strip().startswith("/*"):
        content = []
        while idx < len(lines):
            content.append((idx + 1, _block_comment_content(lines[idx])))
            if "*/" in lines[idx]:
                idx += 1
                break
            idx += 1
        while content and content[0][1] == "":
            content.pop(0)
        while content and content[-1][1] == "":
            content.pop()
        return content
    marker = "#" if style == "hash" else "//"
    content = []
    while idx < len(lines):
        text = _line_comment_content(lines[idx], marker)
        if text is None:
            break
        content.append((idx + 1, text))
        idx += 1
    return content


def _check_block(content, expected, path):
    """Compare a top comment block against the expected header lines."""
    problems = []
    for i, wanted in enumerate(expected):
        if i >= len(content):
            line_no = content[-1][0] + 1 if content else 1
            problems.append(Problem(
                path, line_no,
                f"missing line in license header: expected '{wanted}'"))
            continue
        line_no, found = content[i]
        if found == wanted:
            continue
        want_copy = COPYRIGHT_RE.match(wanted)
        got_copy = COPYRIGHT_RE.match(found)
        if want_copy and got_copy:
            if got_copy.group(1) != want_copy.group(1):
                problems.append(Problem(
                    path, line_no,
                    "wrong year in license header: found "
                    f"{got_copy.group(1)}, expected "
                    f"{want_copy.group(1)}"))
            if got_copy.group(2) != want_copy.group(2):
                problems.append(Problem(
                    path, line_no,
                    "wrong owner in license header: found "
                    f"'{got_copy.group(2)}', expected "
                    f"'{want_copy.group(2)}'"))
            continue
        want_spdx = SPDX_RE.match(wanted)
        got_spdx = SPDX_RE.match(found)
        if want_spdx and got_spdx:
            problems.append(Problem(
                path, line_no,
                "wrong SPDX license identifier: found "
                f"'{got_spdx.group(1)}', expected "
                f"'{want_spdx.group(1)}'"))
            continue
        problems.append(Problem(
            path, line_no,
            "license header line does not match: found "
            f"'{found}', expected '{wanted}'"))
    return problems


def scan_text(text, path, expected, style="hash"):
    """Check one file's text for the expected header.

    Returns a list of Problem. `style` is 'hash' or 'slash'.
    """
    lines = text.splitlines()
    content = _top_comment_block(lines, style)
    if content:
        return _check_block(content, expected, path)
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        for marker in ("#", "//"):
            if stripped.startswith(marker):
                stripped = stripped[len(marker):].strip()
                break
        if stripped.startswith("*"):
            stripped = stripped[1:].strip()
        if COPYRIGHT_RE.match(stripped):
            return [Problem(
                path, lineno,
                "license header is not at the top of the file "
                f"(copyright line on line {lineno})")]
    top = 1
    if lines and lines[0].startswith("#!"):
        top = 2
    while top <= len(lines) and lines[top - 1].strip() == "":
        top += 1
    return [Problem(path, top, "missing license header")]


def check_file(path, expected, style=None):
    """Check one file on disk. Returns a list of Problem."""
    path = str(path)
    ext = Path(path).suffix.lstrip(".")
    use_style = style or style_for(ext) or "hash"
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [Problem(path, 1, "cannot read file: not valid UTF-8")]
    except OSError as exc:
        return [Problem(path, 1, f"cannot read file: {exc.strerror}")]
    return scan_text(text, path, expected, use_style)


def collect(paths, recursive=True, exclude=(), extensions=None):
    """Gather the files to check from paths (files and folders).

    A file given directly is always checked, whatever its name.
    A folder is walked for source files only. `.git` folders are
    never walked, and directory links are never followed.
    """
    wanted = set(extensions) if extensions else KNOWN_EXTENSIONS
    files = []
    seen = set()
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                files.append(str(path))
            continue
        if not path.is_dir():
            print(f"warning: no such file or folder: {raw}",
                  file=sys.stderr)
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames
                           if d != ".git"
                           and not any(fnmatch.fnmatch(d, pat)
                                       for pat in exclude)]
            for name in sorted(filenames):
                if any(fnmatch.fnmatch(name, pat) for pat in exclude):
                    continue
                ext = Path(name).suffix.lstrip(".").lower()
                if ext not in wanted:
                    continue
                full = str(Path(dirpath) / name)
                key = str(Path(full).resolve())
                if key not in seen:
                    seen.add(key)
                    files.append(full)
            if not recursive:
                break
    return files


def run(paths, expected, recursive=True, exclude=(), extensions=None,
        as_style=None, stdin_text=None):
    """Check paths (and optionally stdin text). Returns (problems, count)."""
    problems = []
    if stdin_text is not None:
        style = as_style or "hash"
        problems.extend(scan_text(stdin_text, "<stdin>", expected, style))
        checked = 1
    else:
        files = collect(paths, recursive, exclude, extensions)
        checked = len(files)
        for path in files:
            problems.extend(check_file(path, expected, as_style))
    return problems, checked


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check source files carry the right license header.")
    parser.add_argument("paths", nargs="*", default=["."],
                        help="files or folders to check (default: .)")
    parser.add_argument("--year", default=DEFAULT_YEAR,
                        help="year in the copyright line "
                             f"(default: {DEFAULT_YEAR})")
    parser.add_argument("--owner", default=DEFAULT_OWNER,
                        help="owner in the copyright line "
                             f"(default: {DEFAULT_OWNER})")
    parser.add_argument("--spdx", default=DEFAULT_SPDX,
                        help="SPDX identifier line to expect "
                             f"(default: {DEFAULT_SPDX})")
    parser.add_argument("--no-spdx", action="store_true",
                        help="do not expect an SPDX identifier line")
    parser.add_argument("--header-file",
                        help="file with the expected header, one "
                             "line per line (overrides --year, "
                             "--owner and --spdx)")
    parser.add_argument("--as", dest="as_ext", default=None,
                        help="comment style for files whose extension "
                             "is unknown, e.g. --as js (default: #)")
    parser.add_argument("--extensions", default=None,
                        help="comma-separated extensions to check in "
                             "folders, e.g. --extensions py,js "
                             "(default: all known source extensions)")
    parser.add_argument("--exclude", action="append", default=[],
                        help="skip files and folders by name pattern "
                             "(repeatable)")
    parser.add_argument("--no-recursive", action="store_true",
                        help="do not walk subfolders")
    parser.add_argument("--stdin", action="store_true",
                        help="check one file read from standard input")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    if args.header_file:
        if (args.year != DEFAULT_YEAR or args.owner != DEFAULT_OWNER
                or args.spdx != DEFAULT_SPDX or args.no_spdx):
            parser.error("--header-file cannot be used with --year, "
                         "--owner, --spdx or --no-spdx")
        try:
            raw = Path(args.header_file).read_text(encoding="utf-8")
        except OSError as exc:
            parser.error(f"cannot read header file: {exc.strerror}")
        expected = [line.rstrip() for line in raw.splitlines()]
        while expected and expected[-1] == "":
            expected.pop()
        if not expected:
            parser.error("header file is empty")
    else:
        expected = default_header(args.year, args.owner,
                                  None if args.no_spdx else args.spdx)

    extensions = None
    if args.extensions:
        extensions = {e.strip().lower().lstrip(".")
                      for e in args.extensions.split(",") if e.strip()}
        if not extensions:
            parser.error("--extensions needs at least one extension")

    as_style = None
    if args.as_ext:
        as_style = style_for(args.as_ext)
        if as_style is None:
            parser.error(f"unknown style for --as: {args.as_ext} "
                         "(use a known extension like py or js)")

    if args.stdin:
        stdin_text = sys.stdin.read()
        problems, checked = run([], expected, as_style=as_style,
                                stdin_text=stdin_text)
    else:
        problems, checked = run(args.paths, expected,
                                recursive=not args.no_recursive,
                                exclude=args.exclude,
                                extensions=extensions,
                                as_style=as_style)

    if args.json:
        payload = {
            "files_checked": checked,
            "problems": [p.as_dict() for p in problems],
            "files_with_problems": len({p.path for p in problems}),
        }
        print(json.dumps(payload, indent=2))
    else:
        for problem in problems:
            print(problem.text())
        if problems:
            files_bad = len({p.path for p in problems})
            print(f"Checked {checked} file(s), {len(problems)} "
                  f"problem(s) in {files_bad} file(s).")
        else:
            print(f"OK — {checked} file(s) checked, all source files "
                  "carry the right license header.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
