```text
examples/header-not-top.sh:4: license header is not at the top of the file (copyright line on line 4)
examples/missing-header.py:1: missing license header
examples/wrong-owner.java:2: wrong owner in license header: found 'Jane Doe', expected 'Haider Ali'
examples/wrong-year.js:1: wrong year in license header: found 2025, expected 2026
Checked 8 file(s), 4 problem(s) in 4 file(s).
```

Output of `sh examples/run-example.sh` — the checker on the whole
`examples/` folder. It exits 1, because the examples contain files
with bad headers on purpose; the script itself exits 0.
