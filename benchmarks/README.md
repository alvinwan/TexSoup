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

## 50-Paper Snapshot

![TexSoup robustness and speed](robustness_50.svg)

This larger snapshot compares TexSoup, plasTeX, and LaTeXML on a 50-paper
AI/ML arXiv set. The robustness panel breaks outcomes into successes,
timeouts, and other failures, and the speed panel reports mean runtime on
successful papers only.

The 50-paper chart uses a `10` second timeout for all tools, and the speed
panel reports mean runtime on successful papers only. The raw per-paper results
below come directly from the latest completed local runs on April 7, 2026.

| Backend | Success Rate | Mean Time |
| --- | ---: | ---: |
| TexSoup | `50/50` | `932 ms` on successes |
| plasTeX | `11/50` | `829 ms` on successes |
| LaTeXML | `29/50` | `5,231 ms` on successes |

## 50-Paper Raw Results

| Paper | Chars | TexSoup | plasTeX | LaTeXML |
| --- | ---: | ---: | ---: | ---: |
| `1706.03762` | `73,870` | `1156 ms` | `fail` | `4839 ms` |
| `1810.04805` | `85,622` | `1031 ms` | `1599 ms` | `timeout` |
| `1512.03385` | `78,331` | `756 ms` | `812 ms` | `timeout` |
| `1409.1556` | `71,509` | `1446 ms` | `fail` | `5143 ms` |
| `1406.2661` | `49,699` | `563 ms` | `timeout` | `4300 ms` |
| `1312.6114` | `51,535` | `590 ms` | `fail` | `timeout` |
| `2004.05565` | `53,962` | `438 ms` | `timeout` | `4534 ms` |
| `2006.02049` | `72,438` | `656 ms` | `fail` | `5991 ms` |
| `2004.00221` | `78,325` | `700 ms` | `fail` | `fail` |
| `2103.00020` | `252,082` | `2353 ms` | `fail` | `timeout` |
| `2010.11929` | `82,089` | `726 ms` | `fail` | `fail` |
| `2303.08774` | `124,947` | `1757 ms` | `507 ms` | `timeout` |
| `1905.11946` | `63,805` | `1827 ms` | `fail` | `4664 ms` |
| `1908.09791` | `58,817` | `1201 ms` | `fail` | `fail` |
| `1905.02244` | `64,484` | `546 ms` | `timeout` | `4915 ms` |
| `1801.04381` | `75,774` | `2290 ms` | `fail` | `5568 ms` |
| `1704.04861` | `51,317` | `436 ms` | `fail` | `4122 ms` |
| `1608.06993` | `77,726` | `605 ms` | `fail` | `4063 ms` |
| `1512.02325` | `66,067` | `571 ms` | `1276 ms` | `4523 ms` |
| `1506.01497` | `76,206` | `608 ms` | `fail` | `8008 ms` |
| `1506.02640` | `58,295` | `447 ms` | `fail` | `4752 ms` |
| `1703.06870` | `72,928` | `655 ms` | `timeout` | `8761 ms` |
| `1612.03144` | `60,386` | `470 ms` | `timeout` | `9296 ms` |
| `1708.02002` | `63,902` | `517 ms` | `timeout` | `8292 ms` |
| `1709.01507` | `84,505` | `1047 ms` | `306 ms` | `6218 ms` |
| `1511.08458` | `29,311` | `190 ms` | `1356 ms` | `timeout` |
| `1505.04597` | `25,168` | `185 ms` | `fail` | `2521 ms` |
| `1312.5602` | `63,103` | `452 ms` | `fail` | `4410 ms` |
| `1509.02971` | `56,329` | `398 ms` | `fail` | `4845 ms` |
| `1707.06347` | `220` | `3 ms` | `606 ms` | `1684 ms` |
| `1802.05365` | `96,706` | `1162 ms` | `1205 ms` | `5253 ms` |
| `1907.11692` | `48,059` | `447 ms` | `fail` | `timeout` |
| `1910.10683` | `267,488` | `2209 ms` | `timeout` | `fail` |
| `1909.11942` | `74,016` | `791 ms` | `fail` | `fail` |
| `2003.10555` | `81,025` | `667 ms` | `fail` | `6913 ms` |
| `2002.04745` | `91,201` | `1243 ms` | `fail` | `timeout` |
| `1804.02767` | `15,660` | `151 ms` | `timeout` | `2565 ms` |
| `1605.07146` | `50,810` | `1170 ms` | `fail` | `4394 ms` |
| `1607.06450` | `57,796` | `1623 ms` | `fail` | `fail` |
| `1609.03499` | `44,649` | `362 ms` | `fail` | `4054 ms` |
| `2006.11239` | `86,175` | `842 ms` | `488 ms` | `timeout` |
| `2010.02502` | `82,089` | `1997 ms` | `fail` | `fail` |
| `2106.08254` | `74,190` | `1946 ms` | `462 ms` | `timeout` |
| `2012.12877` | `58,706` | `1798 ms` | `fail` | `timeout` |
| `2201.03545` | `95,601` | `1179 ms` | `fail` | `timeout` |
| `2111.06377` | `86,386` | `721 ms` | `fail` | `8948 ms` |
| `2002.05709` | `105,789` | `895 ms` | `fail` | `timeout` |
| `2006.10029` | `80,661` | `626 ms` | `505 ms` | `5773 ms` |
| `2104.14294` | `18,696` | `137 ms` | `timeout` | `2340 ms` |
| `2112.10752` | `211,624` | `1994 ms` | `fail` | `timeout` |

## Notes

- TexSoup parsed all `50/50` papers in this batch.
- plasTeX finished `11/50` papers: `9` timed out and `30` failed before the timeout.
- LaTeXML finished `29/50` papers: `14` timed out and `7` failed before the timeout.
- The speed panel intentionally reports successful-paper runtimes only; otherwise,
  plasTeX and LaTeXML timeout behavior would dominate the chart.

## Failure Notes

- Most LaTeXML failures in this 50-paper batch were practical `10` second timeouts
  rather than hard converter crashes.
- Most plasTeX failures were hard parse/runtime errors rather than timeouts.
