# Copyright (c) 2026 Haider Ali
# SPDX-License-Identifier: MIT
"""Tests for license-header-checker-cli. Standard library only."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src" / "license_header_checker.py"

sys.path.insert(0, str(ROOT / "src"))
import license_header_checker as lhc
from license_header_checker import (
    Problem, check_file, collect, default_header, scan_text, style_for,
)

EXPECTED = default_header()
GOOD_PY = "# Copyright (c) 2026 Haider Ali\n# SPDX-License-Identifier: MIT\nprint(1)\n"


def problems_as_tuples(text, style="hash"):
    return [(p.line, p.reason) for p in scan_text(text, "test.py", EXPECTED, style)]


class DefaultHeaderTests(unittest.TestCase):
    def test_default_lines(self):
        self.assertEqual(EXPECTED, ["Copyright (c) 2026 Haider Ali",
                                    "SPDX-License-Identifier: MIT"])

    def test_custom_year_owner(self):
        self.assertEqual(default_header("2020", "Jane Doe"),
                         ["Copyright (c) 2020 Jane Doe",
                          "SPDX-License-Identifier: MIT"])

    def test_no_spdx(self):
        self.assertEqual(default_header(spdx=None),
                         ["Copyright (c) 2026 Haider Ali"])

    def test_custom_spdx(self):
        self.assertEqual(default_header(spdx="Apache-2.0"),
                         ["Copyright (c) 2026 Haider Ali",
                          "SPDX-License-Identifier: Apache-2.0"])


class StyleTests(unittest.TestCase):
    def test_hash_extensions(self):
        for ext in ("py", "sh", "rb", "PY"):
            self.assertEqual(style_for(ext), "hash")

    def test_slash_extensions(self):
        for ext in ("js", "ts", "java", "c", "h", "cpp", "go", "rs"):
            self.assertEqual(style_for(ext), "slash")

    def test_unknown_extension(self):
        self.assertIsNone(style_for("md"))
        self.assertIsNone(style_for("txt"))
        self.assertIsNone(style_for(""))


class CleanFileTests(unittest.TestCase):
    def test_hash_header_passes(self):
        self.assertEqual(problems_as_tuples(GOOD_PY), [])

    def test_shebang_then_header_passes(self):
        text = ("#!/usr/bin/env python3\n" + GOOD_PY)
        self.assertEqual(problems_as_tuples(text), [])

    def test_blank_lines_before_header_pass(self):
        text = "\n\n" + GOOD_PY
        self.assertEqual(problems_as_tuples(text), [])

    def test_slash_header_passes(self):
        text = ("// Copyright (c) 2026 Haider Ali\n"
                "// SPDX-License-Identifier: MIT\n"
                "console.log(1);\n")
        self.assertEqual(problems_as_tuples(text, "slash"), [])

    def test_block_comment_passes(self):
        text = ("/*\n"
                " * Copyright (c) 2026 Haider Ali\n"
                " * SPDX-License-Identifier: MIT\n"
                " */\n"
                "public class Main {}\n")
        self.assertEqual(problems_as_tuples(text, "slash"), [])

    def test_one_line_block_comment_passes(self):
        text = ("/* Copyright (c) 2026 Haider Ali\n"
                "   SPDX-License-Identifier: MIT */\n"
                "int main() {}\n")
        self.assertEqual(problems_as_tuples(text, "slash"), [])

    def test_javadoc_style_passes(self):
        text = ("/**\n"
                " * Copyright (c) 2026 Haider Ali\n"
                " * SPDX-License-Identifier: MIT\n"
                " */\n"
                "public class Main {}\n")
        self.assertEqual(problems_as_tuples(text, "slash"), [])

    def test_extra_lines_after_header_pass(self):
        text = GOOD_PY.replace("print(1)\n",
                               "# All rights reserved.\nprint(1)\n")
        self.assertEqual(problems_as_tuples(text), [])

    def test_copyright_c_uppercase_passes(self):
        text = GOOD_PY.replace("(c)", "(C)")
        self.assertEqual(problems_as_tuples(text), [])

    def test_copyright_symbol_passes(self):
        text = GOOD_PY.replace("Copyright (c)", "Copyright \u00a9")
        self.assertEqual(problems_as_tuples(text), [])


class MissingHeaderTests(unittest.TestCase):
    def test_no_header_at_all(self):
        self.assertEqual(
            problems_as_tuples("print(1)\n"),
            [(1, "missing license header")])

    def test_empty_file(self):
        self.assertEqual(problems_as_tuples(""),
                         [(1, "missing license header")])

    def test_only_code_after_shebang(self):
        text = "#!/usr/bin/env python3\nprint(1)\n"
        self.assertEqual(problems_as_tuples(text),
                         [(2, "missing license header")])

    def test_other_comment_is_not_a_header(self):
        text = "# This module does things.\nprint(1)\n"
        self.assertEqual(
            problems_as_tuples(text),
            [(1, "license header line does not match: found "
                 "'This module does things.', expected "
                 "'Copyright (c) 2026 Haider Ali'"),
             (2, "missing line in license header: expected "
                 "'SPDX-License-Identifier: MIT'")])


class WrongHeaderTests(unittest.TestCase):
    def test_wrong_year(self):
        text = GOOD_PY.replace("2026", "2025")
        self.assertEqual(
            problems_as_tuples(text),
            [(1, "wrong year in license header: found 2025, "
                 "expected 2026")])

    def test_wrong_owner(self):
        text = GOOD_PY.replace("Haider Ali", "Jane Doe")
        self.assertEqual(
            problems_as_tuples(text),
            [(1, "wrong owner in license header: found 'Jane Doe', "
                 "expected 'Haider Ali'")])

    def test_wrong_year_and_owner(self):
        text = GOOD_PY.replace("2026 Haider Ali", "2020 Jane Doe")
        self.assertEqual(
            problems_as_tuples(text),
            [(1, "wrong year in license header: found 2020, "
                 "expected 2026"),
             (1, "wrong owner in license header: found 'Jane Doe', "
                 "expected 'Haider Ali'")])

    def test_wrong_spdx(self):
        text = GOOD_PY.replace("MIT", "Apache-2.0")
        self.assertEqual(
            problems_as_tuples(text),
            [(2, "wrong SPDX license identifier: found 'Apache-2.0', "
                 "expected 'MIT'")])

    def test_missing_spdx_line(self):
        text = "# Copyright (c) 2026 Haider Ali\nprint(1)\n"
        self.assertEqual(
            problems_as_tuples(text),
            [(2, "missing line in license header: expected "
                 "'SPDX-License-Identifier: MIT'")])

    def test_wrong_year_line_number_in_block(self):
        text = ("/*\n"
                " * Copyright (c) 2025 Haider Ali\n"
                " * SPDX-License-Identifier: MIT\n"
                " */\n"
                "public class Main {}\n")
        self.assertEqual(
            problems_as_tuples(text, "slash"),
            [(2, "wrong year in license header: found 2025, "
                 "expected 2026")])

    def test_header_not_at_top(self):
        text = ("#!/bin/sh\necho hello\n\n"
                "# Copyright (c) 2026 Haider Ali\n"
                "# SPDX-License-Identifier: MIT\n")
        self.assertEqual(
            problems_as_tuples(text),
            [(4, "license header is not at the top of the file "
                 "(copyright line on line 4)")])

    def test_header_not_at_top_slash_comment(self):
        text = ("var x = 1;\n"
                "// Copyright (c) 2026 Haider Ali\n"
                "// SPDX-License-Identifier: MIT\n")
        self.assertEqual(
            problems_as_tuples(text, "slash"),
            [(2, "license header is not at the top of the file "
                 "(copyright line on line 2)")])


class CheckFileTests(unittest.TestCase):
    def test_good_file_on_disk(self):
        self.assertEqual(
            check_file(ROOT / "examples" / "good.py", EXPECTED), [])

    def test_bad_file_on_disk(self):
        problems = check_file(ROOT / "examples" / "missing-header.py",
                              EXPECTED)
        self.assertEqual([(p.line, p.reason) for p in problems],
                         [(1, "missing license header")])

    def test_non_utf8_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.py"
            path.write_bytes(b"# Copyright (c) 2026 Haider Ali\n\xff\n")
            problems = check_file(path, EXPECTED)
            self.assertEqual([(p.line, p.reason) for p in problems],
                             [(1, "cannot read file: not valid UTF-8")])

    def test_missing_file(self):
        problems = check_file(Path("/nonexistent/file.py"), EXPECTED)
        self.assertEqual(len(problems), 1)
        self.assertIn("cannot read file", problems[0].reason)

    def test_direct_file_any_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            path.write_text(GOOD_PY)
            self.assertEqual(check_file(path, EXPECTED), [])


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "a.py").write_text(GOOD_PY)
        (self.root / "b.js").write_text(
            "// Copyright (c) 2026 Haider Ali\n"
            "// SPDX-License-Identifier: MIT\n")
        (self.root / "c.md").write_text("# notes\n")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "d.py").write_text(GOOD_PY)
        (self.root / ".git").mkdir()
        (self.root / ".git" / "hooks.py").write_text("print(1)\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_folder_walk_source_only(self):
        found = collect([str(self.root)])
        self.assertEqual(sorted(Path(f).name for f in found),
                         ["a.py", "b.js", "d.py"])

    def test_git_folder_skipped(self):
        found = collect([str(self.root)])
        self.assertNotIn("hooks.py", [Path(f).name for f in found])

    def test_no_recursive(self):
        found = collect([str(self.root)], recursive=False)
        self.assertEqual(sorted(Path(f).name for f in found),
                         ["a.py", "b.js"])

    def test_exclude_pattern(self):
        found = collect([str(self.root)], exclude=["*.py"])
        self.assertEqual([Path(f).name for f in found], ["b.js"])

    def test_direct_file_any_name(self):
        found = collect([str(self.root / "c.md")])
        self.assertEqual([Path(f).name for f in found], ["c.md"])

    def test_extensions_filter(self):
        found = collect([str(self.root)], extensions={"py"})
        self.assertEqual(sorted(Path(f).name for f in found),
                         ["a.py", "d.py"])

    def test_dedupe(self):
        found = collect([str(self.root / "a.py"), str(self.root / "a.py")])
        self.assertEqual(len(found), 1)


def run_cli(*args, stdin=None):
    return subprocess.run(
        [sys.executable, str(SRC), *args],
        input=stdin, capture_output=True, text=True, cwd=str(ROOT))


class CliTests(unittest.TestCase):
    def test_clean_file_exit_0(self):
        result = run_cli("examples/good.py")
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK — 1 file(s) checked", result.stdout)

    def test_bad_file_exit_1(self):
        result = run_cli("examples/missing-header.py")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing license header", result.stdout)
        self.assertIn("Checked 1 file(s), 1 problem(s) in 1 file(s).",
                      result.stdout)

    def test_folder_exit_1(self):
        result = run_cli("examples")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Checked 8 file(s), 4 problem(s) in 4 file(s).",
                      result.stdout)

    def test_stdin_clean(self):
        result = run_cli("--stdin", "--as", "js", stdin=(
            "// Copyright (c) 2026 Haider Ali\n"
            "// SPDX-License-Identifier: MIT\n"))
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK — 1 file(s) checked", result.stdout)

    def test_stdin_bad(self):
        result = run_cli("--stdin", stdin="print(1)\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("<stdin>:1: missing license header", result.stdout)

    def test_json_output(self):
        result = run_cli("examples/wrong-year.js", "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["files_checked"], 1)
        self.assertEqual(payload["files_with_problems"], 1)
        self.assertEqual(payload["problems"][0]["line"], 1)
        self.assertIn("wrong year", payload["problems"][0]["reason"])

    def test_year_flag(self):
        result = run_cli("examples/good.py", "--year", "2025")
        self.assertEqual(result.returncode, 1)
        self.assertIn("wrong year in license header: found 2026, "
                      "expected 2025", result.stdout)

    def test_no_spdx_flag(self):
        result = run_cli("--stdin", "--no-spdx", stdin=(
            "# Copyright (c) 2026 Haider Ali\nprint(1)\n"))
        self.assertEqual(result.returncode, 0)

    def test_header_file_flag(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as handle:
            handle.write("Copyright (c) 2025 Haider Ali\n"
                         "SPDX-License-Identifier: MIT\n")
            header_path = handle.name
        try:
            result = run_cli("examples/wrong-year.js",
                             "--header-file", header_path)
            self.assertEqual(result.returncode, 0)
        finally:
            os.unlink(header_path)

    def test_header_file_with_year_is_usage_error(self):
        result = run_cli("examples/good.py", "--header-file", "x.txt",
                         "--year", "2025")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot be used with", result.stderr)

    def test_unknown_as_is_usage_error(self):
        result = run_cli("--stdin", "--as", "docx", stdin="x\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown style", result.stderr)

    def test_version_flag(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("1.0.0", result.stdout)


class ExamplesTests(unittest.TestCase):
    def test_sample_output_matches_fresh_run(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(result.returncode, 0)
        sample = (ROOT / "examples" / "sample-output.md").read_text()
        self.assertIn("```text\n" + result.stdout + "```", sample)

    def test_readme_quotes_match_real_runs(self):
        readme = (ROOT / "README.md").read_text()
        checks = [
            (["examples/good.py"],
             "OK — 1 file(s) checked, all source files carry the "
             "right license header."),
            (["examples/missing-header.py"],
             "examples/missing-header.py:1: missing license header"),
            (["examples/wrong-year.js"],
             "examples/wrong-year.js:1: wrong year in license header: "
             "found 2025, expected 2026"),
            (["examples/wrong-owner.java"],
             "examples/wrong-owner.java:2: wrong owner in license "
             "header: found 'Jane Doe', expected 'Haider Ali'"),
            (["examples/header-not-top.sh"],
             "examples/header-not-top.sh:4: license header is not at "
             "the top of the file (copyright line on line 4)"),
            (["examples"],
             "Checked 8 file(s), 4 problem(s) in 4 file(s)."),
        ]
        for args, quote in checks:
            result = run_cli(*args)
            self.assertIn(quote, result.stdout)
            self.assertIn(quote, readme)


class DogfoodTests(unittest.TestCase):
    def test_repo_own_python_files_pass(self):
        result = run_cli("src", "tests")
        self.assertEqual(result.returncode, 0, result.stdout)


class HygieneTests(unittest.TestCase):
    def test_no_placeholder_or_banned_words(self):
        banned = ["TODO", "FIXME", "XXX", "lorem", "coming soon"]
        hits = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            parts = set(path.relative_to(ROOT).parts)
            if ".git" in parts or "__pycache__" in parts:
                continue
            if "tests" in parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for word in banned:
                if word.lower() in text.lower():
                    hits.append(f"{path}: {word}")
        self.assertEqual(hits, [])

    def test_gitignore_lists_env_first(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_no_yaml_import(self):
        self.assertNotIn("import yaml", SRC.read_text(encoding="utf-8"))
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8")
        self.assertNotIn("yaml", ci.lower())

    def test_no_absolute_paths_or_secrets(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            parts = set(path.relative_to(ROOT).parts)
            if ".git" in parts or "__pycache__" in parts:
                continue
            if "tests" in parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            self.assertNotIn(str(Path.home()), text)
            self.assertNotIn("api_key", text.lower())
            self.assertNotIn("password", text.lower())


if __name__ == "__main__":
    unittest.main()
