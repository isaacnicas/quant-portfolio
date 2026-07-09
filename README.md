[README.md](https://github.com/user-attachments/files/29614179/README.md)
# Building a Smoother Ride: From One Trend-Following Strategy to a Multi-Sleeve Trading System

> **Paper trading is live and running.** The trend-following anchor entered its first positions on June 18, 2026 on an Interactive Brokers paper account (~$994K starting NAV). Since then the account has moved with the market, including drawdown weeks. That's expected, and it's the actual point of paper trading before any capital is real. Automated daily monitoring and monthly rebalancing run via Windows Task Scheduler, with the [live dashboard](https://isaacnicas.github.io/quant-portfolio/live-dashboard.html) updating daily. First rebalance: July 28, 2026.
>
> *This README documents the original trend-following anchor and its eighteen-year backtest, the strategy the rest of the system is built around. It has since grown into a multi-sleeve system: a mean-reversion sleeve is live alongside the anchor, a volatility-risk-premium sleeve is live with a gate-governed order path, and a post-earnings-drift sleeve is mid-revalidation after a forensic audit caught lookahead bias in its early backtest. See [Where the system stands now](#where-the-system-stands-now) for all three, [RESEARCH.md](RESEARCH.md) for the full backtest process and results behind each addition, [CHANGELOG.md](CHANGELOG.md) for the full history, and [OPERATIONS.md](OPERATIONS.md) for the current architecture.*

---

## The idea

Most long-term investing advice boils down to: buy a broad index fund and hold it through the ups and downs. It's reasonable advice. But "the ups and downs" hides a lot. The Nasdaq-100 lost nearly 41% in its worst year over the 2008–2026 period I studied. The S&P 500 dropped more than 50% from peak to trough during the 2008 financial crisis. Living through that with a "hold forever" mindset is a lot harder than it sounds on paper, which is exactly why so many people sell at the bottom and miss the recovery.

Trend following takes a different approach. Instead of holding everything all the time, the strategy adjusts how much it owns based on whether prices are generally rising or falling, and how calm or chaotic the market currently feels. The goal isn't to predict crashes. It's to participate in the good times while gradually stepping back during sustained downturns, so the overall ride is less likely to wreck your nerves or your retirement timeline.

I spent a good chunk of time building, testing, and fixing a systematic version of this idea across a mix of ETFs covering US and international stocks, government bonds, gold, and currencies. Below is the full story: what it does, how it performed over eighteen years of history, what went wrong along the way, and who something like this would actually make sense for.

---

## The results

Here's the headline comparison using eighteen years of historical data (2008–2026). There's also an [interactive version](https://isaacnicas.github.io/quant-portfolio/interactive_results.html) of the two charts below where you can hover over any point to see exact values for that month.

![Growth of $10,000 chart comparing the strategy to SPY and QQQ from 2008 to 2026](images/chart1_growth.png)

A $10,000 investment in 2008 would have grown to roughly $148,000 with this strategy, landing almost exactly between the S&P 500 ($71,670) and the Nasdaq-100 ($166,373). On pure growth, it lands between the two major equity benchmarks I compared it against.

But growth alone doesn't tell the real story. Here's the number that matters more:

![Bar chart showing the worst single year for the strategy versus SPY and QQQ](images/chart2_worst_year.png)

In the worst calendar year of the entire backtest, this strategy lost 22%. Over the same period, the S&P 500's worst year was a 36% loss and the Nasdaq-100's was 41%. That's roughly half the pain in the worst-case scenario, for a return that's nearly identical to the S&P 500's average. Though 22% drawdowns are far from painless — that still means watching more than a fifth of your portfolio disappear before it recovers.

And it's not just about single bad years. It's about how long and how deep the underwater periods get:

![Drawdown chart showing how deep each strategy fell from its previous peak over time](images/chart3_drawdown.png)

This is sometimes called a drawdown chart, and I think it's the most honest way to look at any investment. It shows, at every single point in time, how far below its previous high point the portfolio sits. The strategy is actually in some kind of drawdown more often than you might expect from the headline numbers alone. That's just the nature of investing; nothing ever goes straight up. What matters is the depth. During the 2008 crisis and the 2020–2022 period, both of which dragged the major indices down by roughly half, the strategy's worst point was a 27% drop. Shallower troughs, and noticeably faster recoveries.

Here's the whole picture in one frame:

![Scorecard summarizing average yearly return, worst single year, and largest drawdown](images/chart4_scorecard.png)

| Metric | Strategy | SPY | QQQ |
|---|---|---|---|
| CAGR (2008–2026) | ~16.1% | ~11.6% | ~16.9% |
| Sharpe Ratio | — | — | — |
| Max Drawdown | ~27% | >50% | — |
| Worst Year | −22% | −36% | −41% |

The real trade-off: you give up a little of the spectacular years in exchange for cutting your worst-case losses roughly in half. Whether that trade-off is worth it depends entirely on how you'd actually feel and behave watching your account drop 40% versus 22%.

> *Backtested performance is hypothetical. Real trading involves slippage, commissions, taxes, and the behavioral difficulty of staying invested through drawdowns. Past results do not guarantee future performance. Nothing here is investment advice.*

---

## The numbers, month by month

If the yearly view feels too zoomed out, here's every single month of the backtest, color-coded green for gains and red for losses:

![Heatmap showing every monthly return of the strategy from 2008 to 2026](images/chart5_heatmap.png)

A few things jump out. 2022 was genuinely the worst year of the whole run at -22.1%, with most of that damage concentrated in January and October. Compare that to 2008, where the loss ended at "only" -14.9% because the strategy had already started pulling back before the worst of the crisis hit.

The green cells noticeably outnumber and outweigh the red ones over eighteen years. Nobody wins every month, but the distribution matters.

## What's actually driving the returns

The strategy blends two different ways of reading the market:

![Chart comparing the standalone performance of two signals against their combined result](images/chart6_attribution.png)

The orange line (CS-Mom, short for cross-sectional momentum) asks a relative question: which of these assets are currently the strongest performers compared to each other? The blue line (TSMOM, time-series momentum) asks an absolute question: is this specific asset trending up or down compared to its own history?

On its own, the relative-strength signal actually outperforms the combined strategy over this period. That might seem like an argument for using it alone, but the time-series signal plays a different role. It's most responsible for recognizing when everything is trending down at once and pulling back across the board. Blending the two gives up a little of the relative-strength signal's raw upside in exchange for that broader downside awareness.

## The actual code output

Here's the full dashboard exactly as the backtest generated it:

![Full backtest dashboard showing cumulative returns, drawdowns, rolling Sharpe, annual returns, regime signals, and a daily return scatter](images/chart_full_dashboard.png)

---

## What went wrong (more than once) and what it taught me

The version above wasn't the first attempt. It was the result of several rounds of building, testing, finding out something was quietly broken, and fixing it. Two moments stuck with me because the lessons go well beyond backtesting.

**The strategy that was "safe" but barely invested.** An early version looked fantastic at first glance: low volatility, small drawdowns, very smooth returns. The problem was that its actual gains were disappointing, hovering around 2% a year. When I dug in, I found the cause. I had stacked three separate safety mechanisms on top of each other, each one independently designed to reduce risk when markets got choppy. Individually, each made sense. But because they multiplied together rather than working as a team, the strategy might only be 30% invested on a perfectly ordinary day. Three systems being a little cautious each compounded into the portfolio barely participating in anything.

The fix wasn't to rip out the risk controls. It was to simplify three overlapping safeguards into one clear, well-understood rule. That single change took the strategy from 2% a year to over 13%, without making it meaningfully riskier.

The broader lesson: **layered safeguards in any financial product can interact in ways that aren't obvious from looking at each piece separately.** A fund combining several protective overlays might end up far more defensive (or far less) than any single piece suggests. The only way to know is to test how they behave together, under realistic conditions.

**The emergency brake that locked in losses.** I added a circuit breaker: if markets dropped sharply over a short window, the strategy would pull back its exposure as a defensive move. The first version worked technically, but had a subtle flaw. Once it triggered, it stayed defensive until a scheduled monthly check-in, even if markets had already started bouncing back.

In a sharp but short selloff, which happens more often than people expect, this meant the strategy could end up locking in its most defensive position right as the market started recovering, missing the bounce entirely. The fix was to make the strategy listen for signs of recovery every day rather than wait for a calendar date, so it could re-engage as soon as the data supported it.

Both moments taught me the same thing: the gap between a strategy that looks well-designed and one that behaves well-designed comes down to testing how the pieces interact under adversarial scrutiny, not just whether each piece sounds reasonable in isolation.

---

## What this means for the average investor

**If you've ever sold during a crash and regretted it later,** this is the kind of thing that exists for you. The entire premise is reducing how bad the worst years feel. An investor who doesn't panic-sell during a 22% drawdown is going to come out ahead of one who panic-sells during a 40% one, even if the smoother strategy's average return is a touch lower. But even a 22% drawdown is enough to shake many investors out — that's still more than a fifth of the account erased before recovery begins. The smoother ride only helps if you actually stay on it.

**If you're young, have a long time horizon, and genuinely don't check your portfolio during crashes,** a simple index fund might serve you better. Historically, that investor ends up with more money in the Nasdaq-100 than in this strategy, full stop. The smoother ride has a real cost, and if you don't need the smoothing, you're paying for something you don't use.

**The number that matters most isn't the average return. It's the worst year.** A strategy returning 16.5% on average but losing 22% in its worst year is a very different experience to live through than one returning 17.8% on average but losing 41% in its worst year. Averages are what you calculate after the fact. Worst years are what you actually feel while they're happening.

---

## Where this stands now

**Backtesting is complete** across eighteen years of daily price data with realistic trading costs built in.

**Paper trading is live.** The strategy is running on a simulated brokerage account through Interactive Brokers, with positions entered in June 2026. The pipeline runs automatically: prices refresh daily after market close, performance is logged, and the strategy rebalances on the last trading day of each month. The key question paper trading answers that backtesting cannot is whether real fill prices, data feeds, and order execution match the assumptions built into the backtest. Results and a comparison against backtest expectations will be added here as data accumulates.

The original trend-following strategy launched on a five-script execution stack:

- `data_feed.py`: pulls daily price history for all 12 assets from Interactive Brokers
- `signal_engine.py`: computes TSMOM and CS-Mom signals, regime filter, and fast-exit trigger
- `position_sizer.py`: converts signals to target portfolio weights using vol-targeting and exposure caps
- `order_engine.py`: sizes orders in shares, applies the tiered dead-band, and submits to IBKR
- `monitor.py`: logs daily NAV and P&L, saves current weights for the next rebalance

That five-script stack was the starting point. It has since grown, and the current architecture is documented in [OPERATIONS.md](OPERATIONS.md).

```
┌──────────────────────────────────────────────────────────┐
│                     data_feed.py                         │
│          pulls daily prices from IB → prices.csv         │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                   signal_engine.py                        │
│        TSMOM + CS-Mom signals + VIX regime filter         │
└──────────┬────────────────────────────┬──────────┬───────┘
           │                            │          │
┌──────────▼──────────┐  ┌─────────────▼────┐  ┌──▼────────────────┐
│    Trend Sleeve     │  │    MR Sleeve      │  │    VRP Sleeve     │
│    (Proposer)       │  │    (Proposer)     │  │    (Proposer)     │
│ target weights per  │  │ z-score entries   │  │  SVXY carry,      │
│       ETF           │  │     & exits       │  │  VIX-gate sized   │
└──────────┬──────────┘  └──────────┬────────┘  └──────┬────────────┘
           └──────────────────┬──────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────┐
│                       Governor                            │
│     VIX gate · reduce_50pct · position caps               │
│     dead-band filter · order sizing                       │
└─────────────────────────────┬────────────────────────────┘
                              │  pending_orders.json
┌─────────────────────────────▼────────────────────────────┐
│             submit_orders_premarket.py                    │
│               places market orders at IBKR                │
└─────────────────────────────┬────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────┐
│                      monitor.py                           │
│            logs NAV and P&L · pushes dashboard            │
└──────────────────────────────────────────────────────────┘
```

The sleeves are designed to be independent return sources. The trend sleeve takes long positions in whichever of its 12 ETFs are trending upward and reduces exposure when momentum fades. The mean-reversion sleeve enters counter-trend positions — buying what has fallen too far, selling what has risen too far. The two strategies tend to struggle in different conditions: trend-following underperforms in choppy, sideways markets where no sustained direction forms, while mean-reversion tends to underperform during extended directional runs. Running them side by side is an attempt to smooth the combined equity curve.

Each sleeve acts as a Proposer — it generates the orders it would like to place based purely on its own signal, without awareness of what the other sleeve is doing. The trend sleeve computes target portfolio weights from momentum and volatility readings, then sizes each position in shares. The mean-reversion sleeve computes z-score-based entries and exits for its universe and does the same. Both sets of proposed orders pass to a shared execution layer.

Between the Proposers and the live orders sits a governance layer. A three-condition VIX gate can reduce overall exposure if volatility spikes above thresholds and holds there for two or more consecutive days. A separate reduce_50pct flag cuts mean-reversion capital in half during elevated regimes. A dead-band filter suppresses small rebalancing trades below a minimum threshold — trades that would cost more in spread and slippage than they could recover in expected signal. Position caps prevent any single name from dominating a sleeve's risk budget.

Every order the system places is tagged with the sleeve that generated it, the signal date, and the intended target quantity. This per-order attribution makes it possible to separate what trend-following contributed from what mean-reversion contributed on any given day, and to trace a specific P&L outcome back to its originating signal. If a sleeve's live performance diverges from backtest expectations, the per-sleeve logs are where the investigation starts.

---

## Where the system stands now

This started as one trend-following strategy. It hasn't stayed that way. What actually happened next: a sleeve that earned its place, one that's built but deliberately not trusted yet, and one that got caught in a mistake and pulled back for repair.

A single strategy, however well-tested, is still a single bet: it draws down when its own edge stops working, full stop. Everything added since the anchor is an attempt at return streams that don't draw down at the same time, for the same reason. That only counts if it's measured, not assumed. Here's what the measurement actually showed for each addition.

### Mean-reversion: live, and it does what it was built to do

The mean-reversion sleeve buys what's fallen too far and sells what's risen too far, on the theory that it should struggle in different conditions than trend-following struggles in. The first version of this sleeve lost money (−3.2% annualised, Sharpe −0.30) because trading costs from constant re-entry were eating the edge alive. Adding a dead-band (hold the position until the signal fully resets, instead of re-trading on every wiggle) cut weekly turnover from 70% to 17% and turned it into a real, if modest, standalone strategy: +0.45 Sharpe in-sample, +0.24 out-of-sample. That decay is expected and it's the bar the strategy had to clear on data it never saw during design.

A +0.24 Sharpe wouldn't be worth running alone. The case for it is diversification, and that case is measured:

![Bar charts comparing max drawdown and Sharpe ratio between the trend-following anchor alone, the mean-reversion sleeve alone, and the two blended together](images/chart7_mr_diversification.png)

Blending the anchor with the mean-reversion sleeve under live portfolio weighting cuts the max drawdown from −26.96% to −17.73%, 9.2 percentage points shallower, while giving up only a little Sharpe (1.07 → 0.95). That's the trade the sleeve exists to make: a meaningfully smoother ride, bought with a small amount of standalone return.

### Volatility risk premium: live, gate-governed

The VRP sleeve harvests the tendency of implied volatility to trade above realised volatility, via a 0.5× inverse VIX-futures ETF (SVXY). It's a genuinely different return source from the other two sleeves, and it's also the most dangerous thing on the book: rare, violent left-tail losses are the whole risk profile.

![Bar charts showing the sleeve's standalone drawdown versus its portfolio-level impact at a 15% position cap, and confirmation that the risk gate fired during both required historical stress events](images/chart8_vrp_gate_and_cap.png)

The risk gate correctly fired during both required historical stress events (February 2018's "Volmageddon" and the March 2020 crash), but the sleeve still drew down −65.4% standalone. The central lesson: on 2018-02-05, SVXY gapped down roughly 80% at the open, and a daily-bar gate generates its exit on the close, after the loss is already locked in. The gate detects regimes; it cannot prevent gap losses. The real protection is the position cap: at a 10% NAV allocation, that same −65.4% standalone drawdown becomes roughly −6.5% at the total-portfolio level.

The sleeve has a live order path. Sizing is governed by the three-condition VIX gate: `suspend` (no orders), `reduce_50pct` (sleeve capital halved), or `active` (full 10% NAV allocation). The cap is enforced in code, not just documented in design. As of 2026-07-08, all three VIX gates are clear and the sleeve is running at full size.

### Post-earnings drift: built, and currently being re-audited

The PEAD sleeve trades the tendency of stocks to keep drifting after an earnings surprise. Its first backtest looked promising, until a forensic audit of the underlying earnings-timestamp data found that a majority of the historical trades had been generated using data that wouldn't actually have been available on the trade date. That's lookahead bias, and it's exactly the kind of thing a backtest can hide if you don't go looking for it. The sample was rebuilt on verified point-in-time data, which cut it down substantially and confirmed that most of the strategy's apparent edge was a methodological artifact, not signal. A sealed pre-registration policy now governs what evidence bar the strategy has to clear (set before seeing the results) before it's allowed to place a single live order. It currently isn't. I'd rather show that process than a number I don't trust yet.

### Shared infrastructure

Underneath all three sleeves sits a governance layer that pulls risk when conditions deteriorate (a three-condition VIX gate with two-day confirmation) and a risk engine (ERC) that computes each sleeve's risk-parity weight daily and logs it — currently in observation mode, building track record before being granted live sizing authority; live orders use fixed sleeve fractions in the meantime. The execution stack runs headless and unattended: it rebalances on schedule and pushes its own results to the [live dashboard](https://isaacnicas.github.io/quant-portfolio/live-dashboard.html) without anyone touching it day to day.

I keep a running record of every meaningful change as the project grows. The full backtest process and results behind each addition live in [RESEARCH.md](RESEARCH.md), the dated history lives in the [changelog](CHANGELOG.md), and the current technical architecture is documented in [OPERATIONS.md](OPERATIONS.md).

---

*Built using Python, eighteen years of ETF price history, and a fair amount of trial and error.*
