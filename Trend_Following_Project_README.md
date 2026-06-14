# Building a Smoother Ride: A Systematic Trend-Following Strategy

## The idea

Most people investing for the long term are told to "buy and hold" an index fund like the S&P 500 or the Nasdaq-100 (QQQ) and ride out the ups and downs. That advice is reasonable, but it comes with a real cost: when markets fall hard, they fall *a lot*. QQQ lost nearly 41% in its worst year over the period studied here. The S&P 500 lost over 50% peak-to-trough during the 2008 financial crisis.

Trend following is a different approach. Instead of holding everything all the time, a trend-following strategy adjusts how much it owns based on whether prices are rising or falling, and how calm or turbulent markets currently are. The goal isn't to predict the future — it's to participate in rallies while stepping back during sustained downturns, so the overall ride is smoother.

I built, tested, and refined a systematic version of this idea over several iterations, using a basket of widely-traded ETFs covering US and international stocks, government bonds, gold, and currencies. This document summarizes what it does, how it performed historically, what I learned building it, and — most importantly — who something like this would actually be appropriate for.

---

## The results, in plain terms

Using twenty years of historical data (2008–2026), here's how the strategy compared to simply buying and holding the two most common benchmarks:

| | This Strategy | S&P 500 (SPY) | Nasdaq-100 (QQQ) |
|---|---|---|---|
| Average yearly return | 16.5% | 12.7% | 17.8% |
| Worst single year | **−22%** | −36% | **−41%** |
| Largest peak-to-trough loss | **−27%** | −52% | −49% |
| Return per unit of risk taken* | 0.87 | 0.64 | 0.79 |

*This last row is a measure called the Sharpe ratio — it answers "how much return did you get for how much bumpiness you had to tolerate." Higher is better. A 0.87 means this strategy delivered more return relative to its ups and downs than either benchmark.

**The headline takeaway:** the strategy kept pace with the S&P 500's long-term return and came close to the Nasdaq's, while cutting the worst-case losses roughly in half. In a year where the Nasdaq lost 41%, this strategy's worst year was −22%.

That tradeoff — giving up a little bit of upside during the very best years, in exchange for a much gentler ride during the worst ones — is the entire point of the exercise, and it's a tradeoff worth understanding deeply before deciding whether it's right for someone.

---

## Challenges and what I learned debugging it

The version above wasn't the first version — it was the result of several rounds of building, testing, and finding things that were quietly broken.

The most useful lesson came from an early version that, on paper, looked like it was managing risk beautifully — low volatility, small drawdowns — but its actual returns were disappointingly flat. After digging in, I found the cause: I had layered three separate "safety mechanisms" on top of each other, each designed independently to reduce risk during turbulent markets. Individually, each one made sense. But because they multiplied together, on an ordinary day the strategy might only be 30% invested even when nothing was actually wrong — three different systems were each cautiously pulling back a little, and those small individual caution levels compounded into the portfolio barely participating at all.

The fix wasn't to remove risk management — it was to simplify it into one clear, well-understood signal instead of three overlapping ones. That single change alone took the strategy from a disappointing 2% annual return to over 13%, without making it meaningfully riskier.

That experience stuck with me, because it's not really a "coding" lesson — it's a lesson about how layered safeguards in *any* financial product can interact in ways that aren't obvious from looking at each piece individually. A fund that combines several "protective" overlays might end up far more (or far less) defensive than any single overlay would suggest, and the only way to know is to actually test how they behave together. I suspect this applies just as much to structured products or multi-strategy funds as it does to a backtest in a notebook.

A second lesson came from a "fast exit" rule I added — a rule that cuts exposure quickly if markets drop sharply over a short window, as a kind of emergency brake. The first version of this rule worked, but it had a subtle flaw: once it triggered, it stayed defensive until a scheduled monthly check-in, even if markets had already started recovering. In a sharp-but-short selloff — the kind that happens more often than people expect — that meant the strategy could lock in a defensive position right as the market bounced back, missing the recovery entirely. The fix was to let the strategy "listen" for signs of recovery every day rather than waiting for the calendar, so it could re-engage as soon as the data supported it rather than on a fixed schedule.

Both of these taught me the same broader thing: the difference between a strategy that *looks* well-designed and one that *behaves* well-designed often comes down to testing how the pieces interact under realistic, sometimes adversarial scrutiny — not just whether each piece individually sounds reasonable.

---

## What I'd tell a client about something like this

If I were discussing a strategy like this with someone, here's how I'd frame it honestly:

**Who this could suit:** someone who already has meaningful exposure to growth-oriented investments like the Nasdaq or S&P 500, and who has been uncomfortable — or has made poor decisions — during past market downturns. Someone who says "I know stocks go up over time, but I sold in 2008/2020/2022 because I couldn't stomach the drop" might be a better long-term investor with something that's designed to reduce that drop, even if it means slightly lower returns in the very best years.

**Who this probably isn't for:** someone whose main goal is to maximize returns during strong bull markets and who is genuinely comfortable holding through large temporary losses, since historically that investor would have been better off in a simple index fund. Also not a fit for someone seeking guaranteed protection — this strategy reduces the *size* of losses in bad years, but it doesn't eliminate them, and a -22% year is still a meaningful drop.

**The honest tradeoff, in one sentence:** you're trading some of the spectacular years for protection during the terrible ones — and whether that trade is worth it depends entirely on how someone actually behaves when their portfolio drops by 40%, not how they think they'd behave.

This is, I think, the actual value an advisor brings — not picking the "best" strategy in the abstract, but matching the tradeoff to how a specific person is likely to react when things get difficult. Building this gave me a much more concrete, numbers-grounded appreciation for that.

---

## Status and next steps

Everything above is based on historical backtesting — running the strategy's rules against twenty years of past data to see how it *would have* performed. It has not yet been tested with real-time data or live trades.

The next step is paper trading: running the strategy on a live brokerage feed with simulated money, to see how it behaves with real-time prices and order execution rather than historical data. This is currently pending new hardware (my current laptop can't run the required trading software), but the plan and the code are ready to go once that's set up.

---

*Full technical detail and code available on request.*
