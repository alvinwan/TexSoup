# arXiv Benchmarks

This directory holds the reproducible arXiv benchmark harness for TexSoup and a
few relevant comparison tools. The canonical entry point is
`benchmarks/arxiv.py`.

## Usage

Benchmark the default backend set on one or more arXiv source packages:

```bash
python3 benchmarks/arxiv.py 2004.05565 1706.03762 1512.03385 --repeats 3 --warmups 1
```

Restrict the run to a subset of backends:

```bash
python3 benchmarks/arxiv.py 2004.05565 --backends texsoup latexwalker plastex
```

The script:

- downloads the arXiv `e-print` source package
- safely extracts the source tree
- picks the most likely top-level `.tex` file
- expands common `\input` and `\include` patterns
- optionally inlines `.bbl` content
- runs each backend on the same expanded source text

## Backends

- `texsoup`: TexSoup itself
- `latexwalker`: `pylatexenc`'s syntax walker
- `plastex`: `plasTeX`
- `latexml`: LaTeXML
- `latex2html`: latex2html

These are intentionally lumped together in one harness, but they are not doing
the exact same job. `latexwalker` is a lightweight syntax walker, while
`latexml` and `latex2html` are full document converters.

## Dataset

The current README numbers were measured locally on April 4, 2026 against these
expanded arXiv sources:

- `2004.05565` (`FBNetV2`), `53,962` characters after expansion
- `1706.03762` (`Attention Is All You Need`), `73,871` characters after expansion
- `1512.03385` (`Deep Residual Learning for Image Recognition`), `78,331` characters after expansion

## Current Results

`texsoup`, `latexwalker`, and `plastex` below are the mean of `3` timed runs
after `1` warmup. The `latexml` and `latex2html` numbers are end-to-end command
runtimes from the same local benchmark pass, so compare them cautiously.

| Paper | TexSoup | latexwalker | plasTeX | LaTeXML | latex2html |
| --- | ---: | ---: | ---: | ---: | ---: |
| FBNetV2 `2004.05565` | `546 ms` | `84 ms` | fail | `28,363 ms` | fail in `84 ms` |
| Attention Is All You Need `1706.03762` | `629 ms` | `82 ms` | fail | `5,190 ms` | fail in `96 ms` |
| ResNet `1512.03385` | `989 ms` | `133 ms` | `851 ms` | `11,816 ms` | fail in `115 ms` |

## Failure Notes

- `plasTeX` failed on `2004.05565` with `TypeError: sequence item 12: expected str instance, @enumctr found`.
- `plasTeX` failed on `1706.03762` with `ValueError: I/O operation on closed file`.
- `latex2html` failed immediately on all three papers in this local setup with `Error: No such image type ''`.
