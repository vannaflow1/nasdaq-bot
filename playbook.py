"""
Turns the raw briefing into plain risk instructions for an intraday NQ trader
(Lucid funded account, end-of-day trailing drawdown, max 2 contracts).

Philosophy: nobody reliably knows the DIRECTION a headline or data release will
push the market. What is predictable is WHEN volatility spikes and HOW BIG moves
are likely to be. So every rule here is about size and timing, not long/short.
"""
import re

LEVELS = ["LOW", "NORMAL", "ELEVATED", "HIGH"]


def _bump(level, to):
    return LEVELS[max(LEVELS.index(level), LEVELS.index(to))]


def advise(quintile=None, events_today=(), trump_hot=False, earnings_after_close=()):
    """Returns (risk_level, [action lines])."""
    level, acts = "NORMAL", []

    if quintile == 1:
        level = _bump(level, "ELEVATED")
        acts.append("Low gamma: moves tend to be ~75% bigger than on calm days. Trade 1 contract "
                    "instead of 2, or keep your stop in points but halve the size.")
    elif quintile == 2:
        acts.append("Gamma on the low side: slightly bigger moves than usual. Normal plan, no extra size.")
    elif quintile == 5:
        level = "LOW" if level == "NORMAL" else level
        acts.append("High gamma: calmer day expected. Normal size is fine; far targets get hit less often, "
                    "so don't expect big runners.")

    for e in events_today:
        if "FOMC" in e:
            t = re.search(r"decision (\d\d:\d\d)", e)
            level = _bump(level, "HIGH")
            acts.append(f"FED DECISION at {t.group(1) if t else '20:00'} Lux, then Powell speaks. Be FLAT "
                        "15 min before. The first move after the statement often reverses during the press "
                        "conference - don't chase it. Many pros just skip this window.")
        elif "CPI" in e or "NFP" in e:
            t = re.search(r"(\d\d:\d\d) Lux", e)
            name = "Inflation (CPI)" if "CPI" in e else "Jobs report"
            level = _bump(level, "HIGH")
            acts.append(f"{name} at {t.group(1) if t else '14:30'} Lux, before the US open. NQ can gap "
                        "40-150 points at the release. Don't hold a position through it, and let the first "
                        "15-30 min after the 15:30 open settle before trading.")

    if earnings_after_close:
        level = _bump(level, "ELEVATED")
        names = ", ".join(earnings_after_close)
        acts.append(f"{names} report after the close: big overnight gap risk for NQ. You trade intraday, "
                    "so just make sure you're flat by the close (you should be anyway).")

    if trump_hot:
        level = _bump(level, "ELEVATED")
        acts.append("Trump posted about tariffs/China/the Fed recently. These have caused sharp, fast drops "
                    "before (e.g. 10 Oct 2025, China tariff threat: Nasdaq -3.6% that day). Keep stops tight, "
                    "don't add to losers, don't chase the first spike.")

    if quintile == 5 and level == "HIGH":
        acts[0] = ("High gamma would normally mean a calmer day, but a scheduled event overrides that "
                   "around its release time.")
    if not acts:
        acts.append("Nothing special. Trade your normal plan.")
    if level == "HIGH":
        acts.append("Rule of thumb on HIGH days: one bad trade can hit your trailing drawdown. "
                    "Skipping the day costs you nothing.")
    return level, acts


def trump_meaning(labels):
    """One plain-English line for an instant Trump alert."""
    if "trade/tariffs" in labels or "China/Taiwan" in labels:
        return ("What it means: tariff/China escalation = usually risk-OFF, Nasdaq and chip stocks hit "
                "hardest; de-escalation ('deal', 'pause') = usually a rally. Either way: volatility now. "
                "If you're in a trade, tighten your stop; don't chase the first candle.")
    if "Fed/rates" in labels:
        return ("What it means: pressure on the Fed rarely moves markets much by itself - most of the "
                "time this is noise. Watch for a reaction, don't trade the post.")
    if "tech/chips" in labels:
        return ("What it means: can move the named company (and NQ through it) for a few minutes. "
                "Usually a short-lived spike.")
    if "stock market" in labels:
        return "What it means: mostly commentary. Rarely moves anything. Information only."
    if "oil/geopolitics" in labels:
        return ("What it means: military/war news = possible fast risk-off move, oil up. Size down until "
                "the dust settles.")
    return "What it means: probably minor for the Nasdaq. Information only."


def render(level, acts):
    icon = {"LOW": "🟢", "NORMAL": "⚪", "ELEVATED": "🟠", "HIGH": "🔴"}[level]
    return [f"WHAT THIS MEANS FOR YOU - risk {icon} {level}"] + [f"- {a}" for a in acts]
