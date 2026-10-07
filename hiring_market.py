"""Hiring-market realism for user staff searches.

Candidates have an interest level driven by program stature, current job, résumé,
relationships and money. User hires use a contact -> interview -> offer/counter flow;
a name on the candidate list is not an automatic signing.
"""
import math
import random


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def coord_interest(league, team, c, role, tie=False, offer=None):
    """0-100 willingness. Elite assistants require elite jobs unless there is a real tie."""
    import finance
    cur = getattr(c, "team", None)
    prestige = float(getattr(team, "prestige", 50))
    curp = float(getattr(cur, "prestige", 42)) if cur is not None else 35.0
    ovr = float(getattr(c, "overall", 65))
    # Elite coaches expect national-caliber jobs. This is the main guard against a 97 taking UNLV.
    expected = 35 + max(0, ovr - 55) * 1.55
    stature = (prestige - expected) * 1.7
    jump = (prestige - curp) * 1.15
    score = 48 + stature + jump
    if cur is None or getattr(c, "status", "") == "unemployed":
        score += 17
    if tie:
        score += 20
    if getattr(c, "moved_year", None) == league.year:
        return 0
    tenure = league.year - getattr(c, "coord_since", league.year) + 1
    if cur is not None and tenure < 2 and not tie:
        score -= 35
    if offer is not None:
        try:
            ratio = finance.money_ratio(league, c, offer, role, team)
            score += (ratio - 1.0) * 38
        except Exception:
            pass
    # Nobody at the very top takes a massive downward step just because the dice liked it.
    if ovr >= 92 and prestige < 76 and not tie:
        return min(18, _clamp(score))
    if ovr >= 96 and prestige < 84 and not tie:
        return min(8, _clamp(score))
    return int(_clamp(score))


def pos_interest(league, team, c, offer_mult=1.0):
    import poscoach
    cur = next((t for t in league.teams if t.school == getattr(c, "school", None)), None)
    prestige = float(getattr(team, "prestige", 50))
    curp = float(getattr(cur, "prestige", 38)) if cur else 32.0
    ovr = float(getattr(c, "overall", 60))
    expected = 30 + max(0, ovr - 50) * 1.45
    score = 52 + (prestige - expected) * 1.55 + (prestige - curp) * 1.0
    if cur is None:
        score += 18
    if getattr(c, "kind", "") == "Climber":
        score += 8
    if getattr(c, "kind", "") == "Loyalist":
        coord = None
        try:
            import staff
            coord = staff.side_coach(team, "QB" if poscoach.SIDE[c.group] == "OC" else "LB")
        except Exception:
            pass
        score += 15 if coord is not None and coord.name in getattr(c, "ties", set()) else -9
    if getattr(c, "since", None) is not None and c.since >= league.year + 1:
        return 0                         # hired this same offseason: off limits
    score += (offer_mult - 1.0) * 45
    if ovr >= 90 and prestige < 72:
        return min(15, int(_clamp(score)))
    if ovr >= 95 and prestige < 82:
        return min(7, int(_clamp(score)))
    return int(_clamp(score))


def word(score):
    if score >= 82: return "very interested"
    if score >= 65: return "interested"
    if score >= 48: return "listening"
    if score >= 30: return "long shot"
    return "unlikely"


def _roll(seed, score):
    r = random.Random(seed)
    # Even a strong fit can say no; truly bad fits almost always do.
    chance = 1 / (1 + math.exp(-(score - 52) / 10.0))
    return r.random() < chance


# Coordinator pursuits live in coord_search.py (contact -> interviews -> package -> counters -> retention).


def negotiate_pos(league, team, c):
    """Interactive position-coach pursuit. Returns True when he accepts."""
    from ui import C, ask, clear, paint, pause, title_bar
    initial = pos_interest(league, team, c)
    clear(); print(title_bar(f"STAFF SEARCH · {c.name.upper()}"))
    print(paint(f"\n   Initial interest: {word(initial)}.", C.BWHITE))
    if initial < 14:
        print(paint("   His camp declines the call. This job is too large a step down right now.", C.BRED)); pause(); return False
    if ask("   Bring him in for an interview? (y/n):").strip().lower() not in ("y","yes"):
        return False
    print(paint("\n   The interview covers his room, recruiting territory, coordinator fit and career path.", C.GRAY))
    ch = ask("   [1] make standard offer   [2] offer 15% premium   [3] offer 30% premium   [Enter] pass:").strip()
    if not ch: return False
    mult = {"1":1.0,"2":1.15,"3":1.30}.get(ch)
    if mult is None: return False
    final = pos_interest(league, team, c, mult)
    ok = _roll(f"pos-offer:{league.seed}:{league.year}:{team.school}:{c.name}:{mult}", final)
    rr = random.Random(f"pos-retain:{league.seed}:{league.year}:{team.school}:{c.name}:{mult}")
    if ok and getattr(c, "school", None) and rr.random() < 0.14:
        print(paint(f"\n   {c.school} counters to keep him. He stays where he is.", C.BRED, C.BOLD))
        pause(); return False
    print(paint("\n   He accepts the job." if ok else "\n   He turns you down and stays on the market.", C.BGREEN if ok else C.BRED, C.BOLD))
    pause()
    if ok:
        c.__dict__["hire_pay_mult"] = mult
    return ok
