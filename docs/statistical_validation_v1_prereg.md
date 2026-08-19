# Statistical Validation v1 — Pre-Registration

**Status: APPROVED, sealed before any test runs.** Written and approved before any test in this document runs — no reopening after seeing results, same discipline as `equity_carry_gate1_leverage_prereg.md`. Governs Trend, MeanReversion, and VRP — the three currently-live sleeves. Companion to `docs/statistical_validation_v1_weights_seal.json` (sealed 2026-08-19, commit `1a63e9e`).

## Inputs (from Step 0's audit, summarized — see that report for full detail)

| Sleeve | Source | Net-of-cost? | Range used |
|---|---|---|---|
| Trend | `trend_v4_daily_returns.csv`, column `strategy_net` | Yes — `tc_bps=6` applied to daily turnover | 2008-01-03 to **2026-06-17** |
| MeanReversion | `MeanReversionStrategy(use_vix_gate=False).backtest(start='2019-01-01')['daily_pnl']` | Yes — `COST_BPS=5` applied to position changes | 2019-07-08 to 2026-08-18 |
| VRP | `VRPStrategy(capital_allocation=0.10).backtest(start='2015-01-01')['strategy_return']`, **cost-adjusted per below** | Adjusted (placeholder), see below | 2015-01-05 to 2026-07-17 |

### Disclosed limitation 1 — Trend data staleness

`trend_v4_daily_returns.csv` was last regenerated 2026-06-18 and is not being refreshed for this pass — regenerating it is a separate task, not worth blocking this validation on. **Trend's result in this document reflects real history through 2026-06-17, not present-day.** Roughly two months of subsequent live history exist in other logs but are not included in the bootstrap input.

### Disclosed limitation 2 — VRP cost adjustment is a placeholder, not a derived figure

Checked directly for an existing VRP/SVXY-specific transaction-cost estimate anywhere in the codebase (order_engine.py's cost modeling, adjacent docs, prior sessions' work) — **none exists.** `vrp_strategy.py`'s `.backtest()` computes gross returns only (`strategy_return = weight.shift(1) * svxy_return`, no cost term anywhere in the method).

Per the resolved methodology decision: apply a disclosed placeholder rather than test gross. **VRP_COST_BPS = 7**, applied the same way as the other two sleeves (`daily_cost = position_change * COST_BPS / 10,000`, position change measured as the day-over-day change in the sleeve's `weight` — 0↔1 entries/exits, since VRP is binary-weighted). 7bps sits inside the 5-10bps range spanning MR's 5 and Trend's 6, chosen slightly above both because SVXY (a leveraged/inverse VIX-futures ETF) is structurally less liquid than MR's equity basket or Trend's large-cap-ETF universe.

**Stated plainly, per instruction: VRP's cost estimate is not independently derived for this specific instrument's real trading costs; it uses a placeholder consistent with the other two sleeves' cost methodology, pending a dedicated VRP transaction-cost study.** Any VRP result in this document should be read with that caveat attached — it is a reasonable, disclosed estimate, not evidence-grounded the way Trend's and MR's real cost figures are.

## Step 1 — Individual sleeve tests

Identical treatment for all three sleeves — no asymmetry.

**Methodology:** Stationary block bootstrap (`arch.bootstrap.StationaryBootstrap`, confirmed available in this environment) on each sleeve's real net-of-cost daily return series (VRP: cost-adjusted per above). Block length via `arch.bootstrap.optimal_block_length` (Politis & White 2004 automatic data-dependent selection) — not a hand-picked round number. **10,000 resamples.**

**Hypothesis:** H0: annualized net Sharpe ≤ 0. One-sided p-value = proportion of the 10,000 bootstrap-resampled annualized Sharpe ratios that are ≤ 0.

**Reported for each sleeve:** point estimate (annualized net Sharpe on the real series), 95% CI (2.5th/97.5th percentile of the bootstrap distribution), one-sided p-value.

**DSR/PBO:** retained as a reported diagnostic alongside the bootstrap result, never as pass/fail. Prior committed DSR work (`sleeve_falsification_results.md`, `sleeve_falsification_empirical_null_sensitivity.md`) stands as-is and is not re-opened or re-litigated here — this document adds a new, separate standard (see the retirement statement below), it doesn't retroactively touch the old one.

## Step 2 — Cross-variant selection test (Reality Check / SPA)

**Methodology:** `arch.bootstrap.RealityCheck` and `arch.bootstrap.SPA` (confirmed available), applied wherever a genuine "tried several, picked one" population actually exists in the documented design record — not a hypothetical grid.

**Trend — applies. Real n=6 population** (reconstructed in `sleeve_falsification_empirical_null_sensitivity.md` from `trend_following_strategy.ipynb`'s actual v3→v4 design record, not invented for this document):

| Variant | Sharpe | Disposition |
|---|---|---|
| Kalman signal (standalone) | 0.208 | Rejected |
| Carry signal (standalone) | 0.357 | Rejected |
| CS-Mom (standalone) | 0.339 | Kept (20% weight) |
| v3 combined (HRP + 3 gates) | 0.24 | Superseded |
| TSMOM (standalone) | 0.52 | Kept (80% weight) |
| v4 final | 0.87 (prior full-series figure; this document's own point estimate supersedes it) | Live — the one under test |

Test: does v4 (the selected variant) show genuine superior predictive ability once evaluated against the full n=6 population it was actually chosen from, not in isolation.

**MeanReversion — applies. Real n=2 population** (`RESEARCH.md`'s "Development path: what failed first"):

| Variant | Sharpe | Disposition |
|---|---|---|
| Single-name z-score, no dead-band | -0.30 | Rejected — 70% weekly turnover ate the edge |
| Final (dead-band + momentum filter) | 0.45 | Live — the one under test |

Caveat carried forward honestly: n=2 gives Reality Check/SPA very little power here. Reported as the real, available test — not treated as a strong result either way given the tiny population.

**VRP — does not apply, stated explicitly rather than silently skipped.** Checked directly: `vrp_strategy.py`'s own module docstring states the mechanism was built as "the highest-conviction new build per all six counsel opinions" — a single specification converged on directly, not selected from among competing backtested variants. No alternative VRP mechanism's Sharpe is documented anywhere in this codebase. There is no "we tried several and picked one" population for VRP to test against — Reality Check/SPA is not run for this sleeve, and this is a scope statement, not a gap in the test.

## Step 3 — Frozen portfolio test

Constructed using the **sealed live sizing fractions** from `statistical_validation_v1_weights_seal.json` (commit `1a63e9e`, true seal date 2026-07-25 per that file's own provenance) — MR_SLEEVE_FRACTION=0.075, VRP_SLEEVE_FRACTION=0.05 (cost-adjusted return series per above), Trend sized via its existing leverage-capped vol-target exposure (max_leverage=1.5, bull_leverage=1.2), **not** `compute_erc_weights()`'s observation-mode/equal-weight output — that computation has no live sizing authority (see the weights-seal file's own `erc_observation_mode_note`).

Blended daily series constructed over each sleeve's available overlap window (bounded by Trend's 2026-06-17 staleness limit and VRP's 2026-07-17 `^VIX3M`-limited range — the blended series' usable range is therefore capped at 2026-06-17, the shortest of the three).

**Methodology:** identical stationary block bootstrap treatment as Step 1, applied to the blended series. H0: blended portfolio net Sharpe ≤ 0. Reported: point estimate, 95% CI, one-sided p-value.

## Step 4 — Pre-registered forward-review rules (governs future decisions only, not retrospective)

**Real live history is far shorter than a 24-month window would need — checked directly via C8 and each sleeve's actual state-log span before proposing anything, per instruction.** C8 currently reports MATURE (all sleeves ≥ 21 trading days, its own threshold), but that 21-day bar is specific to the ERC observation-mode computation, not a meaningful review-cadence window. The *real* calendar span of live state-log history, checked directly: Trend 25 unique days (2026-07-08 to 2026-08-13), MeanReversion 27 days (2026-07-06 to 2026-08-13), VRP 27 days (2026-07-06 to 2026-08-13) — **roughly five to six weeks for every sleeve.** A 24-month proposal would be disconnected from reality by a factor of ~20x.

**Proposed cadence:** **Monthly review**, using all available live history to date as the rolling window until 12 months of live history accrue per sleeve, at which point transition to a rolling 12-month window. (24-month windows can be reconsidered once 24 months of live history actually exist — not before.) This is itself a provisional structure, explicitly revisit-eligible as real history accumulates; stated here so the *criterion for revisiting* is pre-registered too, not left informal.

**Trigger conditions — reusing this project's own existing live-monitoring thresholds where they already exist (`multi_strategy_monitor.py`'s `THRESHOLDS` dict), rather than inventing new numbers for sleeves that already have one:**

| Sleeve | Risk-cut trigger | Source |
|---|---|---|
| MeanReversion | Rolling net Sharpe < 0.20, OR rolling drawdown < -20% | Existing `THRESHOLDS["MeanReversion"]`, reused as-is |
| VRP | Rolling net Sharpe < 0.50, OR rolling drawdown < -35% | Existing `THRESHOLDS["VRP"]`, reused as-is |
| Trend | Rolling net Sharpe < 0.30, OR rolling drawdown < -15% | **No existing entry in `THRESHOLDS` — proposed new**, calibrated to Trend's own leverage-capped (post-2026-07-25) exposure; the -15% figure sits below Trend's historical standalone max drawdown (-26.96%, pre-leverage-reduction) since the leverage cap was explicitly reduced to lower tail risk |

**Increased-allocation consideration trigger (all three sleeves):** rolling net Sharpe exceeds this document's own Step 1 point estimate for that sleeve, sustained for 3 consecutive monthly reviews.

**Decommission consideration (all three sleeves):** risk-cut trigger active for 6 consecutive monthly reviews without recovery, OR a single-event loss exceeding 1.5× the sleeve's designed position-cap tolerance in one day.

**Stated plainly, per instruction:** this ruleset governs decisions made from this point forward. It does not retroactively justify or condemn the 2026-07-25 sizing-fraction revision, the original DSR FAIL-A verdicts, or any other already-made decision.

## Step 5 — DSR retirement, stated explicitly

**As of this document, DSR ≥ 0.95 is retired as the platform's pass/fail conviction threshold for Trend, MeanReversion, and VRP.** The standard going forward is: Step 1's bootstrap p-value + 95% CI, Step 2's Reality Check/SPA result where applicable, Step 3's frozen-portfolio result, and Step 4's forward-review rules, together. DSR/PBO continue to be reported as diagnostics (Step 1), not as the gate.

---

**Approved as written on 2026-08-19, all six flagged decisions confirmed: VRP_COST_BPS=7, `arch.bootstrap` tooling, VRP excluded from Reality Check/SPA (reasoning stated above), 12-month rolling review window (not 24), Trend's new Sharpe<0.30/DD<-15% thresholds, and the frozen-portfolio 2026-06-17 cap. Nothing in Steps 1-3 executed before this line was written.**

## Seal

**SHA-256: `9c950d6e4ac431dd98e9ff783578098342afcb9a22bd1e5183a6441bdc8f5ab0`**

This hash covers the document's full content from the title through the approval line directly above this section — i.e., everything except this Seal section itself, which cannot include its own hash without altering it. The same hash is recorded in the commit message that adds this section. Step 3 has not run as of this seal.
