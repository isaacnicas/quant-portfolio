# Building a Smoother Ride: What I Learned Designing a Trend-Following Strategy

## The idea

Most advice about long-term investing boils down to: buy a broad index fund — something like the S&P 500 or the Nasdaq-100 (QQQ) — and hold it through the ups and downs. It's reasonable advice. But "the ups and downs" hides a lot. The Nasdaq-100 lost nearly 41% in its worst year over the period I studied. The S&P 500 dropped more than 50% from peak to trough during the 2008 financial crisis. Living through that, even with a "buy and hold forever" mindset, is a lot harder than it sounds on paper — which is exactly why so many people sell at the bottom and miss the recovery.

Trend following is a different way of approaching this. Instead of holding everything, all the time, no matter what, a trend-following strategy adjusts how much it owns based on whether prices are generally rising or falling, and how calm or chaotic the market currently feels. The goal isn't to predict the next crash — nobody can do that reliably — it's to participate in the good times while gradually stepping back during sustained downturns, so the overall ride is less likely to wreck your nerves (or your retirement timeline).

I spent a good chunk of time building, testing, and — more importantly — breaking and fixing a systematic version of this idea, using a mix of widely-traded ETFs covering US and international stocks, government bonds, gold, and currencies. Below is the whole story: what it does, how it performed over the last eighteen years of market history, what went wrong along the way (more than once), and who something like this would actually make sense for.

---

## The results

Here's the headline comparison, using eighteen years of historical data (2008–2026). *(There's also an [interactive version](interactive_results.html) of the two charts below — hover over any point to see the exact numbers for that month.)*

![Growth of $10,000 chart comparing the strategy to SPY and QQQ from 2008 to 2026](images/chart1_growth.png)

A $10,000 investment in 2008 would have grown to roughly $148,000 with this strategy — landing almost exactly between the S&P 500 ($71,670) and the Nasdaq-100 ($166,373). On pure growth, it's competitive with two of the best-performing benchmarks of the last two decades.

But growth alone doesn't tell the real story. Here's the one that matters more:

![Bar chart showing the worst single year for the strategy versus SPY and QQQ](images/chart2_worst_year.png)

In the worst calendar year of the entire backtest, this strategy lost 22%. Over the same period, the S&P 500's worst year was a 36% loss, and the Nasdaq-100's was 41%. That's roughly half the pain, in the worst-case scenario, for a return that's nearly identical to the S&P 500's average.

And it's not just about single bad years — it's about how long and how deep the underwater periods get:

![Drawdown chart showing how deep each strategy fell from its previous peak over time](images/chart3_drawdown.png)

This is sometimes called a "drawdown" chart, and I think it's the most honest way to look at any investment. It shows, at every single point in time, how far below its previous high point the portfolio currently sits. Looking at the real output, the strategy is actually in some kind of drawdown more often than you might expect from the headline numbers alone — that's just the nature of investing, nothing ever goes straight up. What matters is the depth: during the 2008 crisis and the 2020–2022 period, both of which dragged the S&P 500 and Nasdaq-100 down by roughly half, the strategy's worst point was a 27% drop. Shallower troughs, and noticeably faster recoveries back to the high-water mark.

Here's the whole picture in one frame:

![Scorecard summarizing average yearly return, worst single year, and largest drawdown for the strategy versus benchmarks](images/chart4_scorecard.png)

**The honest summary:** you give up a little bit of the spectacular years — the strategy doesn't fully keep pace with the Nasdaq-100 during its best stretches — in exchange for cutting your worst-case losses roughly in half. That trade-off is the entire point, and whether it's worth it depends entirely on how you'd actually feel and behave watching your account drop 40% versus 22%.

---

## The numbers, month by month

If the yearly view feels too zoomed-out, here's every single month of the backtest, color-coded green for gains and red for losses:

![Heatmap showing every monthly return of the strategy from 2008 to 2026, color-coded from red for losses to green for gains](images/chart5_heatmap.png)

A few things jump out looking at it this way. 2022 — the year inflation fears and rising interest rates hit growth stocks hard — was genuinely the worst year of the whole run for this strategy, at −22.1%. But look at how it's distributed: most of that loss came from a rough October 2022 and a sharp start in January. Compare that to 2008, where the damage was concentrated in September and October during the worst of the financial crisis, but the year overall ended at "only" −14.9% because the strategy had already started pulling back before the worst of it hit.

You can also see the strategy doesn't win every month — nobody's strategy does — but the green cells noticeably outnumber and outweigh the red ones over eighteen years.

## What's actually driving the returns

The strategy isn't a single idea — it's a blend of two different ways of reading the market, working together:

![Chart comparing the standalone performance of two underlying signals against their combined result, plus a bar chart of their Sharpe ratios](images/chart6_attribution.png)

The orange line ("CS-Mom," short for cross-sectional momentum) asks a relative question: *which of these assets are currently the strongest performers compared to each other?* The blue line ("TSMOM," time-series momentum) asks an absolute question: *is this specific asset trending up or down compared to its own history?*

Interestingly, on its own, the relative-strength signal (orange) actually outperforms the combined strategy (green) over this period. That might seem like an argument for using it alone — but the time-series signal plays a different role than raw return suggests. It's the one most responsible for recognizing when *everything* is trending down at once and pulling back across the board, which is exactly the behavior that produces the smoother ride shown earlier. Blending the two gives up a little of the relative-strength signal's raw upside in exchange for that broader downside awareness.

## The actual code output

For anyone who wants to see this isn't just charts I made in isolation — here's the full dashboard exactly as it was generated by the backtest itself, all in one frame:

![Full backtest dashboard showing cumulative returns, drawdowns, rolling Sharpe ratio, annual returns, regime and leverage signals, and a daily return scatter plot](images/chart_full_dashboard.png)

---

## What went wrong (more than once) — and what it taught me

The version above wasn't the first attempt. It was the result of several rounds of building something that looked good on paper, testing it more rigorously, finding out it was quietly broken, and fixing it. Two of those moments stuck with me, because the lessons go well beyond spreadsheets and code.

**The strategy that was "safe" but barely invested.** An early version of this looked fantastic at first glance — low volatility, small drawdowns, very smooth-looking returns. The problem was that its actual gains were disappointing, hovering around 2% a year. When I dug into why, I found the cause: I had stacked three separate "safety mechanisms" on top of each other, each one independently designed to reduce risk when markets got choppy. Individually, each one made sense. But because they multiplied together rather than working as a team, on a perfectly ordinary day the strategy might only be 30% invested — three different systems were each being a little cautious, and those small individual caution levels compounded into the portfolio barely participating in anything.

The fix wasn't to rip out the risk controls. It was to simplify three overlapping, redundant safeguards into one clear, well-understood rule. That single change took the strategy from a disappointing 2% a year to over 13%, without making it meaningfully riskier on paper.

What I took away from this is bigger than backtesting: **layered safeguards in any financial product can interact in ways that aren't obvious from looking at each one separately.** A fund that combines several "protective" overlays — a hedge here, a stop-loss there, a volatility filter somewhere else — might end up far more defensive (or far less) than any single piece would suggest on its own. The only way to know is to actually test how the pieces behave *together*, under realistic conditions. I suspect this applies just as much to complex structured products as it does to a notebook full of Python.

**The emergency brake that locked in losses.** I also added a rule designed as a kind of circuit breaker — if markets dropped sharply over a short window, the strategy would quickly pull back to reduce exposure, as a defensive move. The first version of this rule worked technically, but it had a subtle flaw: once it triggered, it stayed defensive until a scheduled monthly check-in, even if the market had already started bouncing back.

In a sharp-but-short selloff — which happens more often than people expect — this meant the strategy could end up locking in its most defensive position *right as the market started recovering*, missing the bounce entirely. The fix was to make the strategy "listen" for signs of recovery every day, rather than waiting for a calendar date, so it could re-engage as soon as the data actually supported it.

Both of these moments taught me the same underlying thing: the gap between a strategy that *looks* well-designed and one that *behaves* well-designed often comes down to testing how the pieces interact — including under adversarial, "what if this goes wrong" scrutiny — not just whether each piece sounds reasonable in isolation.

---

## What this means for the average investor

If you're not building strategies yourself but you're trying to figure out what any of this means for your own money, here's how I'd put it.

**If you've ever sold during a crash and regretted it later** — this is the kind of thing that exists for you. The entire premise is reducing how bad the worst years feel, on the theory that an investor who doesn't panic-sell during a 22% drawdown is going to come out ahead of one who panic-sells during a 40% one, even if the smoother strategy's average return is a touch lower.

**If you're young, have a long time horizon, and genuinely don't check your portfolio during crashes** — a simple index fund might actually serve you better. Historically, that investor would have ended up with more money in the Nasdaq-100 than in this strategy, full stop. The "smoother ride" has a real cost, and if you don't need the smoothing, you're paying for something you don't use.

**The number that matters most isn't the average return — it's the worst year.** A strategy that returns 16.5% a year on average but loses 22% in its worst year is a very different experience to actually live through than one that returns 17.8% on average but loses 41% in its worst year, even though the difference in average returns looks small on a spreadsheet. Averages are what you calculate after the fact. Worst years are what you actually feel while they're happening.

I came away from this project with a much more concrete, numbers-grounded appreciation for that distinction — and for how much "which strategy is better" depends on the person holding it, not just the numbers themselves.

---

## Where this stands now

Everything above comes from backtesting — running the strategy's rules against eighteen years of historical price data to see how it *would have* performed, with realistic trading costs built in. It has not yet been tested with live, real-time data or real trades.

The next step is paper trading: connecting the strategy to a live brokerage feed and running it with simulated money, so I can see how it behaves with real-time prices and order execution rather than historical data. That's next on the list, currently waiting on some new hardware to get set up — but the code and the plan are ready to go.

---

*Built using Python, eighteen years of ETF price history, and a fair amount of trial and error.*
