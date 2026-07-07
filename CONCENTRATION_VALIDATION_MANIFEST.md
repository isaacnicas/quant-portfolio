# CONCENTRATION VALIDATION — FILE MANIFEST

Analysis: concentration-gap hypothesis validation
Pull date: 2026-07-01
Manifest written: 2026-07-01

---

## Raw Immutable Pulls

These files must not be modified. Headers record source, field, and pull date.

| File | What it is | Type |
|------|-----------|------|
| `data/raw/SPY_ibkr_2026-07-01.csv` | SPY daily OHLCV bars, IBKR ADJUSTED_LAST, 6033 rows, 2002-07-08 to 2026-07-01 | raw / immutable |
| `data/raw/RSP_ibkr_2026-07-01.csv` | RSP daily OHLCV bars, IBKR ADJUSTED_LAST, 5829 rows, 2003-04-30 to 2026-07-01 | raw / immutable |
| `data/raw/SPY_yfinance_2026-07-01.csv` | SPY daily close, yfinance auto_adjust=True, 5850 rows, 2003-04-01 to 2026-07-01 | raw / immutable |
| `data/raw/RSP_yfinance_2026-07-01.csv` | RSP daily close, yfinance auto_adjust=True, 5829 rows, 2003-05-01 to 2026-07-01 | raw / immutable |

All four files carry `# IMMUTABLE RAW PULL — DO NOT MODIFY` in their header.
SPY and RSP yfinance files are used only for the §1.5 CAGR gate check and the
four month-end timing-artifact corrections. They do not enter the spread computation.

---

## Canonical Output

| File | What it is | Type |
|------|-----------|------|
| `CONCENTRATION_VALIDATION_REPORT.md` | Full technical record per §6 of spec. All numbers sourced from raw files and reconciled. Canonical version for review. | canonical |
| `CONCENTRATION_VALIDATION_MANIFEST.md` | This file. | canonical |

---

## Intermediate Report (superseded)

| File | What it is | Type |
|------|-----------|------|
| `reports/concentration_validation_report.md` | Earlier draft written during the analysis run. Numbers are consistent with the canonical report but lacks source citations and the reconciliation section. Superseded by `CONCENTRATION_VALIDATION_REPORT.md`. | derived / superseded |

---

## Governing Spec

| File | What it is | Type |
|------|-----------|------|
| `C:\Users\isaac\OneDrive\Desktop\CONCENTRATION_VALIDATION_SPEC.md` | User-authored specification. Not produced by this analysis. Not in the quant-portfolio repo. | spec / external |

---

## Analysis Scripts (scratchpad — not in repo)

These scripts were written and executed during the analysis run. They live in the
session scratchpad directory and are not committed to the repo. They are listed here
for traceability. The canonical report documents their outputs; the raw CSV files
contain the underlying data needed to reproduce any computation.

| Script | What it does |
|--------|-------------|
| `ibkr_pull_v2.py` | Pulls SPY and RSP from IBKR TWS using SelectorEventLoop fix for Python 3.14 compatibility. Saves raw CSVs. Runs §1.5 CAGR gate. |
| `verify_adjustment_basis.py` | Verifies IBKR ADJUSTED_LAST is total-return equivalent via CAGR cross-check and ex-dividend spot-check. |
| `concentration_s2_s3_s4a.py` | §0 artifact check, §1 month-end correction, §2 monthly series, §3 Claim A, §4.1 naive Claim B test. |
| `concentration_s4b.py` | §4.2 2000-exclusion fragility test (ETF-era analog). |
| `concentration_s4c.py` | §4.3 entry-drawdown stress test. Entry-date sensitivity sweep. |
| `concentration_s45_report.py` | §4.5 regime-conditioning test. §4.6 multiple-comparisons log. Writes `reports/concentration_validation_report.md`. |
| `verify_numbers.py` | Post-run recompute from raw CSVs to confirm all reported figures. Output recorded in Section 9 of the canonical report. |

Scratchpad path (session-specific, not persistent):
`C:\Users\isaac\AppData\Local\Temp\claude\C--Users-isaac-OneDrive-Desktop-ClaudeCodeTest\29d070a0-890a-44b8-b9ab-140c3dbf33c2\scratchpad\`

To reproduce any result: load the raw CSV files from `data/raw/`, apply the four
month-end corrections documented in Section 1 of the canonical report, then build
the monthly series and rolling 36m signal as described.

---

## No Plots Produced

No charts or figures were generated during this analysis. All results are tabular.

---

## Prior Session Files (PEAD validation — separate analysis)

These files are in the TrendFollowing repo and are unrelated to the concentration
validation. Listed here to avoid confusion with any cross-repo file searches.

| File | Location |
|------|---------|
| `timestamp_diff_report.txt` | `C:\QuantTrading\TrendFollowing\` |
| `pead_clean_rebuild_results.txt` | `C:\QuantTrading\TrendFollowing\` |
| `pead_concentration_diagnostics.txt` | `C:\QuantTrading\TrendFollowing\` |
| `docs\PEAD_PREREGISTRATION.md` | `C:\QuantTrading\TrendFollowing\docs\` |
