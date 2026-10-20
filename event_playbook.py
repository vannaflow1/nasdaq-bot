"""
event_playbook.py - what NQ historically does on FOMC / CPI / jobs-report days.
Stats from 1-minute NQ, 2017-2025 (models/event_stats.json; 104 CPI, 102 NFP, 71 FOMC days).
"""
import json, os
import events

HERE = os.path.dirname(os.path.abspath(__file__))
ST = json.load(open(os.path.join(HERE, "models", "event_stats.json")))


def lines(day, nq):
    s = day.isoformat()
    L = lambda h, m: events.lux(day, h, m)
    todo = [("FOMC", f"FOMC decision ({L(14, 0)} Lux, Powell {L(14, 30)})", s in events.FOMC),
            ("CPI", f"CPI inflation ({L(8, 30)} Lux)", s in events.CPI),
            ("NFP", f"Jobs report ({L(8, 30)} Lux)", s in events.NFP)]
    out = []
    for key, label, on in todo:
        if not on:
            continue
        e = ST[key]; pts = lambda pct: f"~{pct / 100 * nq:,.0f} pts"
        out += [f"📋 PLAYBOOK - {label}  (based on {int(e['n'])} past {key} days, 2017-2025)",
                f"  • First 15 min after the release: NQ moves {e['first15_range_pct']:.2f}% high-to-low ({pts(e['first15_range_pct'])}) "
                f"- {e['first15_range_pct'] / e['first15_normal_pct']:.1f}x a normal 15 minutes. About "
                f"{e['share_of_day_range_in_first15']:.0%} of the whole day's range happens right there.",
                f"  • Whole day: only ~{(e['session_range_vs_normal'] - 1) * 100:.0f}% bigger than a normal day - options already price it "
                f"(the brain's range forecast is about right on these days).",
                f"  • After the first 15 min the market continued the first move {1 - e['reversal_rate']:.0%} of the time and reversed "
                f"{e['reversal_rate']:.0%} - a coin flip. No edge in chasing OR fading the first move."]
        if key == "FOMC":
            out.append(f"  • Before the decision the session is QUIET: median {e['pre_range_pct']:.2f}% range vs {e['pre_normal_pct']:.2f}% on "
                       f"normal days - don't expect much until the decision.")
        out.append("  • What to do: be flat or small into the release, wait for the first 15 minutes to print, size for a "
                   "bigger candle than usual.")
    return out
