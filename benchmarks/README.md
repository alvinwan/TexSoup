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

Run external converters without a timeout:

```bash
python3 benchmarks/arxiv.py 2004.05565 --backends latexml --command-timeout-seconds 0
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

The current README numbers were measured locally on April 5, 2026 against these
expanded arXiv sources:

- `2004.05565` (`FBNetV2`), `53,962` characters after expansion
- `1706.03762` (`Attention Is All You Need`), `73,870` characters after expansion
- `1512.03385` (`Deep Residual Learning for Image Recognition`), `78,331` characters after expansion
- `1810.04805` (`BERT`), `85,622` characters after expansion
- `2303.08774` (`GPT-4 Technical Report`), `124,947` characters after expansion
- `2103.00020` (`CLIP`), `252,082` characters after expansion
- `2010.11929` (`Vision Transformer`), `82,089` characters after expansion
- `1312.6114` (`Auto-Encoding Variational Bayes`), `51,535` characters after expansion
- `1406.2661` (`Generative Adversarial Nets`), `49,699` characters after expansion
- `1409.1556` (`VGG`), `71,509` characters after expansion

## Current Results

## 50-Paper Snapshot

![TexSoup robustness and speed](robustness_50.svg)

This larger snapshot compares TexSoup, plasTeX, and LaTeXML on a 50-paper
AI/ML arXiv set. The robustness panel breaks outcomes into successes,
timeouts, and other failures, and the speed panel reports mean runtime on
successful papers only.

`texsoup` and `latexwalker` below are the median of `5` timed runs after `1`
warmup, and the summary row reports the mean of those per-paper medians.
`plastex` and `latexml` are from the latest completed local pass on the same
10-paper set with `--repeats 1 --warmups 0`. The `latexml` column is an
end-to-end command runtime with `--command-timeout-seconds 0`, so it reflects
full conversion cost rather than pure parse cost.

| Backend | Success Rate | Mean Time |
| --- | ---: | ---: |
| TexSoup | `10/10` | `937 ms` |
| latexwalker | `10/10` | `276 ms` |
| plasTeX | `3/10` | `1,661 ms` on successes |
| LaTeXML | `9/10` | `151,521 ms` on successes |
| latex2html | `0/10` | local install broken |

| Paper | Chars | TexSoup | latexwalker | plasTeX | LaTeXML |
| --- | ---: | ---: | ---: | ---: | ---: |
| FBNetV2 `2004.05565` | `53,962` | `478 ms` | `145 ms` | fail | `35,218 ms` |
| Transformer `1706.03762` | `73,870` | `731 ms` | `184 ms` | fail | `50,986 ms` |
| ResNet `1512.03385` | `78,331` | `777 ms` | `222 ms` | `1,381 ms` | `78,464 ms` |
| BERT `1810.04805` | `85,622` | `755 ms` | `243 ms` | `2,699 ms` | `180,916 ms` |
| GPT-4 `2303.08774` | `124,947` | `1,164 ms` | `326 ms` | `902 ms` | `914,143 ms` |
| CLIP `2103.00020` | `252,082` | `2,910 ms` | `939 ms` | fail | `20,195 ms` |
| ViT `2010.11929` | `82,089` | `883 ms` | `238 ms` | fail | fail |
| VAE `1312.6114` | `51,535` | `573 ms` | `151 ms` | fail | `67,071 ms` |
| GAN `1406.2661` | `49,699` | `462 ms` | `120 ms` | fail | `7,506 ms` |
| VGG `1409.1556` | `71,509` | `635 ms` | `190 ms` | fail | `9,189 ms` |

## Notes

- `latexwalker` remains much faster than TexSoup, but it is a lighter syntax
  walker rather than a fault-tolerant tree/editing parser.
- LaTeXML completed `9/10` papers with no timeout, but the unrestricted run can
  take a very long time. The GPT-4 technical report alone took about
  `914,143 ms` (`15.2 min`).
- `plasTeX` numbers above are from the latest completed local pass on the same
  10-paper dataset. Reruns on this machine were not always stable.
- `latex2html` failed immediately in this local setup with
  `Error: No such image type ''` and a broken install-path warning, so it is
  not a meaningful baseline here.

## Failure Notes

- `plasTeX` failed on `2004.05565` and `1406.2661` with
  `TypeError: sequence item 12: expected str instance, @enumctr found`.
- `plasTeX` failed on `1706.03762`, `2010.11929`, and `1312.6114` with
  `ValueError: I/O operation on closed file`.
- `plasTeX` failed on `2103.00020` with
  `TypeError: sequence item 11: expected str instance, bgroup found`.
- `plasTeX` failed on `1409.1556` with
  `TypeError: sequence item 8: expected str instance, string found`.
- LaTeXML failed on `2010.11929` with `latexml failed with exit code 1`.
