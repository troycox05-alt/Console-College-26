"""
cp_sched.py — Non-conference scheduling, deeper (Coach Career).

You book real games, years out, the way athletic departments do:

  Home-and-home    one at your place, one at theirs (two seasons)
  2-for-1          two at your place, one at theirs (three seasons) — only if you're the bigger name
  Guarantee game   they come to you and you pay them (FCS, Group of Five, the odd Power team)
  Paycheck game    you go to them and they pay you (a smaller program visiting a bigger one)
  Neutral site     a kickoff game in a pro stadium, a payout for both sides

Every opponent decides for itself — the odds show before you ask, and a "no" stands for the year.
Fees come out of that season's NIL pool; payouts go into it. Your AD has opinions about all of it.
Whatever dates you don't book, he fills with your philosophy (career_plus.PLANS).

  screen(league)                         the planner
  booked(league, year)                   [(deal, side)] for one season (season._requested_games)
"""
import random

from ui import (
    WIDTH,
    C,
    ask,
    clear,
    clip,
    footer,
    key,
    pad,
    paint,
    pause,
    section,
    title_bar,
    truncate,
)

KINDS = {
    "hh": ("Home-and-home", "one here, one there"),
    "two_one": ("2-for-1", "two here, one there"),
    "buy": ("Guarantee game", "they come here, you pay"),
    "road_buy": ("Paycheck game", "you go there, they pay"),
    "neutral": ("Neutral site", "a pro stadium, a payout"),
}
FEE = {"fcs": 450_000, "group": 1_400_000, "power": 2_600_000}
PAYCHECK = 1_300_000
NEUTRAL_PAY = 2_000_000
MAX_PER_YEAR = 4


def _cp():
    import career_plus
    return career_plus


def _tier(t):
    if getattr(t, "fcs", False):
        return "fcs"
    from season import schedule_tier
    return "power" if schedule_tier(t) == "power" else "group"


def deals(league):
    st = _cp().state(league)
    me = league.user_team.school if league.user_team else None
    return [d for d in st.setdefault("deals", []) if d.get("team") == me and d.get("status") == "signed"]


def booked(league, year):
    """[(deal, 'home'|'away'|'neutral')] for that season."""
    return [(d, d["games"][str(year)]) for d in deals(league) if str(year) in d["games"]]


def _venues():
    import postseason as ps
    seen, out = set(), []
    for stadium, city, tier, _d in ps.BOWLS.values():
        if tier == 1 and stadium not in seen:
            seen.add(stadium)
            out.append((stadium, city))
    return out


def odds(league, opp, kind):
    me = league.user_team
    if opp.conference == me.conference and opp.conference != "Independent":
        return 0.0
    pd = opp.prestige - me.prestige
    mt, ot = _tier(me), _tier(opp)
    if ot == "fcs" and kind not in ("buy",):
        return 0.0
    if kind == "hh":
        p = 0.85 - max(0, pd) * 0.03 - (0.12 if ot == "power" and mt != "power" else 0)
    elif kind == "two_one":
        p = 0.25 - pd * 0.035 - (0.3 if ot == "power" and mt != "power" else 0.15 if ot == "power" else 0)
    elif kind == "buy":
        p = 0.95 if ot == "fcs" else 0.8 - max(0, pd) * 0.03 if ot == "group" else 0.12 - pd * 0.01
    elif kind == "road_buy":
        p = 0.9 if (ot == "power" and mt != "power") or pd >= 12 else 0.25
    else:
        p = 0.65 - abs(pd) * 0.018 + (0.12 if mt == ot == "power" else 0)
    return max(0.02, min(0.97, p))


def money_of(league, opp, kind):
    """Positive: you pay. Negative: you're paid."""
    if kind == "buy":
        return FEE[_tier(opp)]
    if kind == "road_buy":
        return -PAYCHECK
    if kind == "neutral":
        return -NEUTRAL_PAY
    return 0


def _years_for(kind, first):
    if kind == "hh":
        return {str(first): "home", str(first + 1): "away"}
    if kind == "two_one":
        return {str(first): "home", str(first + 1): "away", str(first + 2): "home"}
    if kind == "buy":
        return {str(first): "home"}
    if kind == "road_buy":
        return {str(first): "away"}
    return {str(first): "neutral"}


def _sign(league, opp, kind, first, venue=None, away_first=False):
    import finance
    st = _cp().state(league)
    team = league.user_team
    games = _years_for(kind, first)
    if away_first and kind == "hh":
        games = {str(first): "away", str(first + 1): "home"}
    fee = money_of(league, opp, kind)
    d = {"id": len(st.setdefault("deals", [])) + 1, "team": team.school, "school": opp.school, "kind": kind,
         "games": games, "fee": fee, "venue": venue, "signed": league.year, "status": "signed"}
    st["deals"].append(d)
    for y in games:
        if fee > 0:
            team.__dict__.setdefault("fac_spend", []).append((int(y), fee, f"guarantee game: {opp.school}"))
        elif fee < 0:
            team.__dict__.setdefault("income", []).append({"what": f"{KINDS[kind][0].lower()}: {opp.school}",
                                                          "amount": -fee, "year": int(y)})
    _cp()._log(league, (league.year, f"Scheduled {opp.school}: {KINDS[kind][0].lower()} ({', '.join(games)})."))
    return d, (f"{finance.money(fee)} a game out of that year's NIL pool" if fee > 0 else
               f"{finance.money(-fee)} a game into that year's NIL pool" if fee < 0 else "no money changes hands")


def cancel(league, d):
    import ad_trust
    import finance
    team = league.user_team
    left = [y for y in d["games"] if int(y) > league.year]
    if not left:
        return "Those games are already played."
    buyout = max(500_000, abs(d["fee"]) // 2) * len(left)
    team.__dict__.setdefault("fac_spend", []).append((league.year + 1, buyout, f"buyout: {d['school']}"))
    # the money that was coming or going for those years goes away too
    team.fac_spend[:] = [x for x in team.fac_spend if not (x[2] == f"guarantee game: {d['school']}" and str(x[0]) in left)]
    team.__dict__["income"] = [i for i in getattr(team, "income", []) if not (str(i["year"]) in left and d["school"] in i["what"])]
    d["status"] = "cancelled"
    ad_trust.change(league, -2, f"bought out the {d['school']} series")
    _cp()._log(league, (league.year, f"Bought out the {d['school']} series ({finance.money(buyout)})."))
    return f"Done. The buyout is {finance.money(buyout)}, out of next year's NIL pool."


# ═══ The projection ═════════════════════════════════════════════════════════

def projection(league, year):
    """(expected non-conference wins, home games, power opponents, an AD line, approval 0-100)."""
    import carousel as cz
    team = league.user_team
    by = {t.school: t for t in league.teams + list(getattr(league, "fcs_teams", []))}
    xw = home = power = 0
    marquee = False
    for d, side in booked(league, year):
        o = by.get(d["school"])
        if o is None:
            continue
        site = 1 if side == "home" else -1 if side == "away" else 0
        xw += cz.win_prob(team, o, site, league)
        home += side == "home"
        power += _tier(o) == "power"
        marquee = marquee or (_tier(o) == "power" and o.prestige >= 72) or side == "neutral"
    n = len(booked(league, year))
    style = (team.ad or {}).get("style", "patient")
    if n == 0:
        return 0.0, 0, 0, "Nothing booked yet. I'll fill the dates with your philosophy if you don't.", 50
    if style == "win_now":
        a = 50 + (xw / n - 0.6) * 120
        line = "Winnable games. Good." if a >= 55 else "Why are we scheduling losses? We need wins this year."
    elif style == "big_game":
        a = 45 + 25 * marquee + 10 * power
        line = "That's a game people will remember." if marquee else "Where's the big one? Get me a game on national TV."
    elif style == "booster":
        a = 40 + 12 * home + 15 * marquee
        line = "Home games and a marquee night. The donors will love it." if a >= 60 else "The money wants home games and a big name."
    elif style == "traditionalist":
        a = 45 + 12 * home
        line = "Home games, regional teams. That's how it's done." if a >= 60 else "Too much travel. Bring them here."
    elif style == "conference":
        a = 55
        line = "Fine. None of it matters as much as the league."
    elif style in ("analytics", "recruiting"):
        a = 50 + 10 * power + 10 * (any(side == "neutral" for _d, side in booked(league, year)))
        line = "Good exposure. Recruits watch those games." if a >= 60 else "I'd like one game recruits will actually watch."
    else:
        a = 50 + (xw / n - 0.55) * 80
        line = "A schedule a young team can grow into." if a >= 55 else "Let's not throw the kids to the wolves."
    return xw, home, power, line, max(0, min(100, round(a)))


# ═══ The planner ════════════════════════════════════════════════════════════

def _row(league, d, side, by):
    import carousel as cz
    team = league.user_team
    o = by.get(d["school"])
    if o is None:
        return paint(f"   {d['school']} (no longer playing)", C.GRAY)
    site = 1 if side == "home" else -1 if side == "away" else 0
    p = cz.win_prob(team, o, site, league)
    where = {"home": "vs", "away": "at", "neutral": "vs*"}[side]
    rk = league.rankings.rank_of(o)
    money = ""
    if d["fee"] > 0 and side == "home":
        import finance
        money = paint(f"pay {finance.money(d['fee'])}", C.BRED)
    elif d["fee"] < 0:
        import finance
        money = paint(f"get {finance.money(-d['fee'])}", C.BGREEN)
    col = C.BGREEN if p >= 0.65 else C.BYELLOW if p >= 0.4 else C.BRED
    return clip(f"   {pad(where, 4)}{paint(pad(truncate(('#' + str(rk) + ' ' if rk else '') + o.school, 22), 23), C.BWHITE, C.BOLD)}"
                f"{paint(pad(_tier(o).replace('group', 'G5').replace('power', 'Power').replace('fcs', 'FCS'), 7), C.GRAY)}"
                f"{pad(o.record, 7)}{paint(pad(f'{p * 100:.0f}%', 6), col, C.BOLD)}{paint(pad(KINDS[d['kind']][0], 16), C.GRAY)}{money}"
                + (paint(f"  {d['venue']}", C.GRAY) if side == "neutral" and d.get("venue") else ""), WIDTH)


def screen(league):
    cp = _cp()
    if not cp.mine(league):
        return
    team = league.user_team
    nxt = league.year + 1
    plan = cp.state(league)["nonconf"].setdefault(str(nxt), {"style": "balanced", "opener": None, "ask": []})
    msg = ""
    while True:
        by = {t.school: t for t in league.teams + list(getattr(league, "fcs_teams", []))}
        clear()
        print(title_bar(f"NON-CONFERENCE SCHEDULING · {team.school.upper()}", league.team_color(team)))
        print(paint(f"\n   Book real games, years out. Conference games and protected rivalries are set by the league;\n"
                    f"   whatever you leave open, your AD fills with your philosophy when the {nxt} schedule is made.", C.GRAY))
        xw, home, power, line, appr = projection(league, nxt)
        print(section(f"{nxt} · {len(booked(league, nxt))} OF ~{MAX_PER_YEAR - 1} DATES BOOKED", C.BYELLOW))
        bk = booked(league, nxt)
        if not bk:
            print(paint("   Nothing booked. [F] finds an opponent.", C.GRAY))
        print(paint(f"   {'':4}{'OPPONENT':<23}{'TIER':<7}{'NOW':<7}{'WIN':<6}{'DEAL':<16}MONEY", C.GRAY, C.BOLD)) if bk else None
        deal_ix = []
        for d, side in bk:
            deal_ix.append(d)
            print(_row(league, d, side, by))
        if bk:
            from ui import bar
            col = C.BGREEN if appr >= 60 else C.BYELLOW if appr >= 40 else C.BRED
            print(f"\n   {paint('Expected wins', C.GRAY)} {xw:.1f} of {len(bk)}   {paint('Home', C.GRAY)} {home}   "
                  f"{paint('Power opponents', C.GRAY)} {power}   {paint('Your AD', C.GRAY)} {bar(appr, 12, 100, col)}")
        print(paint(f"   AD {team.ad['name']}: \"{line}\"", C.BCYAN, C.ITALIC))
        print(section(f"THE REST OF {nxt}: YOUR PHILOSOPHY", C.BYELLOW))
        for i, (k, (name, blurb)) in enumerate(cp.PLANS.items(), 1):
            on = plan["style"] == k
            print(clip(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(pad(name, 12), C.BGREEN if on else C.BWHITE, C.BOLD)}"
                       f"{paint('● ' if on else '  ', C.BGREEN)}{paint(blurb, C.GRAY)}", WIDTH))
        fut = [(y, booked(league, y)) for y in range(nxt + 1, nxt + 4)]
        if any(b for _y, b in fut):
            print(section("FURTHER OUT", C.BCYAN))
            for y, b in fut:
                if b:
                    txt = ", ".join(f"{'vs' if s == 'home' else 'at' if s == 'away' else 'vs*'} {d['school']}" for d, s in b)
                    print(clip(f"   {paint(str(y), C.BWHITE, C.BOLD)}  {txt}", WIDTH))
        if msg:
            print(paint("\n   " + msg, C.BGREEN if not msg.startswith("No") else C.BYELLOW))
            msg = ""
        alld = deals(league)
        footer(key("F", "find an opponent"), key("1-4", "philosophy"), *([key("X", "buy out a deal")] if alld else []),
               key("B", "done", C.GRAY))
        c = ask("Select:").strip().lower()
        if c in ("1", "2", "3", "4"):
            plan["style"] = list(cp.PLANS)[int(c) - 1]
        elif c == "f":
            msg = find(league) or ""
        elif c == "x" and alld:
            msg = _cancel_flow(league, alld) or ""
        else:
            return


def _cancel_flow(league, alld):
    clear()
    print(title_bar("BUY OUT A DEAL"))
    print()
    for i, d in enumerate(alld, 1):
        yrs = ", ".join(f"{y} {s}" for y, s in d["games"].items())
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(d['school'], 22)}{pad(KINDS[d['kind']][0], 16)}{paint(yrs, C.GRAY)}")
    c = ask("Which one? (Enter = none):").strip()
    if c.isdigit() and 1 <= int(c) <= len(alld):
        d = alld[int(c) - 1]
        if ask(f"Buy out {d['school']}? It costs money and a little of your AD's trust. (y/n)").strip().lower() == "y":
            return cancel(league, d)
    return None


def candidates(league, tier):
    me = league.user_team
    out = []
    for t in league.teams + list(getattr(league, "fcs_teams", [])):
        if t is me or (t.conference == me.conference and t.conference != "Independent"):
            continue
        tt = _tier(t)
        if tier != "all" and tt != tier:
            continue
        out.append(t)
    return out


def _best_kind(league, t):
    ks = [k for k in KINDS if odds(league, t, k) > 0.02]
    return max(ks, key=lambda k: odds(league, t, k)) if ks else None


def find(league):
    import season
    me = league.user_team
    st = _cp().state(league)
    declined = st.setdefault("declined", {})
    tier = "power"
    sort = "odds"
    page = 0
    while True:
        rows = candidates(league, tier)
        if sort == "odds":
            rows.sort(key=lambda t: (-max(odds(league, t, k) for k in KINDS), -t.prestige))
        elif sort == "prestige":
            rows.sort(key=lambda t: -t.prestige)
        else:
            rows.sort(key=lambda t: (-season._nearby(me, t), -t.prestige))
        per = 15
        page = max(0, min(page, (len(rows) - 1) // per))
        shown = rows[page * per:(page + 1) * per]
        clear()
        print(title_bar(f"FIND AN OPPONENT · {tier.replace('group', 'Group of Five').replace('fcs', 'FCS').replace('all', 'everyone').upper()}"))
        print(paint(f"\n   {'':6}{'SCHOOL':<22}{'CONF':<14}{'NOW':<7}{'PRES':<6}{'NEAR':<6}{'SERIES':<9}BEST DEAL", C.GRAY, C.BOLD))
        import rivalries
        for i, t in enumerate(shown, 1):
            k = _best_kind(league, t)
            p = odds(league, t, k) if k else 0
            s = rivalries.series(league, me, t)
            ser = s.record_str(me.school) if s.n else "—"
            no = declined.get(t.school) == league.year
            nb = season._nearby(me, t)
            near = "state" if nb >= 3 else "close" if nb >= 1.8 else ""
            col = C.BGREEN if p >= 0.6 else C.BYELLOW if p >= 0.3 else C.BRED
            deal = paint("said no this year", C.GRAY) if no else (paint(f"{KINDS[k][0]} {p * 100:.0f}%", col) if k else paint("—", C.GRAY))
            print(clip(f"   {paint(f'[{i:>2}]', C.BYELLOW, C.BOLD)} {pad(truncate(t.school, 21), 22)}{paint(pad(truncate(t.conference, 13), 14), C.GRAY)}"
                       f"{pad(t.record, 7)}{pad(str(round(t.prestige)), 6)}{pad(near, 6)}{pad(ser, 9)}{deal}", WIDTH))
        print(paint(f"\n   Page {page + 1} of {max(1, (len(rows) + per - 1) // per)} · sorted by "
                    f"{ {'odds': 'the chance they say yes', 'prestige': 'prestige', 'near': 'distance'}[sort]}", C.GRAY))
        footer(key("#", "pick"), key("P", "Power"), key("G", "Group of Five"), key("C", "FCS"), key("A", "all"),
               key("S", "sort"), key("N", "next page"), key("V", "previous"), key("B", "back", C.GRAY))
        c = ask("Select:").strip().lower()
        if c in ("p", "g", "c", "a"):
            tier, page = {"p": "power", "g": "group", "c": "fcs", "a": "all"}[c], 0
        elif c == "s":
            sort = {"odds": "prestige", "prestige": "near", "near": "odds"}[sort]
        elif c == "n":
            page += 1
        elif c == "v":
            page -= 1
        elif c.isdigit() and 1 <= int(c) <= len(shown):
            t = shown[int(c) - 1]
            if declined.get(t.school) == league.year:
                return f"No — {t.school} already turned you down this year."
            r = _offer(league, t)
            if r:
                return r
        else:
            return None


def _offer(league, t):
    import finance
    st = _cp().state(league)
    nxt = league.year + 1
    clear()
    print(title_bar(f"A DEAL WITH {t.school.upper()}"))
    print(paint(f"\n   {t.full_name} · {t.conference} · {t.record} · prestige {round(t.prestige)}", C.GRAY))
    print()
    opts = [k for k in KINDS if odds(league, t, k) > 0.02]
    if not opts:
        print(paint("   They won't play you. (Conference-mates, or an FCS team that only takes guarantee games.)", C.BYELLOW))
        pause()
        return None
    for i, k in enumerate(opts, 1):
        name, how = KINDS[k]
        m = money_of(league, t, k)
        mtxt = paint(f"you pay {finance.money(m)} a game", C.BRED) if m > 0 else \
            paint(f"you get {finance.money(-m)}", C.BGREEN) if m < 0 else paint("no money", C.GRAY)
        p = odds(league, t, k)
        col = C.BGREEN if p >= 0.6 else C.BYELLOW if p >= 0.3 else C.BRED
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(pad(name, 16), C.BWHITE, C.BOLD)}{pad(how, 26)}{pad(mtxt, 30)}"
              f"{paint(f'{p * 100:.0f}% they say yes', col)}")
    c = ask("Which deal? (Enter = back):").strip()
    if not c.isdigit() or not 1 <= int(c) <= len(opts):
        return None
    kind = opts[int(c) - 1]
    span = len(_years_for(kind, nxt))
    yr = ask(f"Starting when? [1] {nxt}  [2] {nxt + 1}  [3] {nxt + 2}").strip()
    first = nxt + (int(yr) - 1 if yr in ("1", "2", "3") else 0)
    clash = [y for y in _years_for(kind, first) if any(d["school"] == t.school for d, _s in booked(league, int(y)))]
    full = [y for y in _years_for(kind, first) if len(booked(league, int(y))) >= MAX_PER_YEAR]
    if clash:
        return f"No — you already play {t.school} in {', '.join(clash)}."
    if full:
        return f"No — {', '.join(full)} {'is' if len(full) == 1 else 'are'} already full."
    venue = None
    away_first = False
    if kind == "neutral":
        vs = _venues()
        for i, (s_, city) in enumerate(vs, 1):
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {s_}, {city}")
        v = ask("Which stadium? (Enter = the first)").strip()
        s_, city = vs[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(vs) else vs[0]
        venue = f"{s_}, {city}"
    elif kind == "hh":
        away_first = ask("Who hosts first? [1] you  [2] them").strip() == "2"
    rng = random.Random(f"deal:{league.seed}:{league.year}:{t.school}:{kind}")
    if rng.random() >= odds(league, t, kind):
        st.setdefault("declined", {})[t.school] = league.year
        return f"No — {t.school}'s AD passed on the {KINDS[kind][0].lower()}. Ask again next year."
    _d, money = _sign(league, t, kind, first, venue, away_first)
    span_txt = f"{first}" if span == 1 else f"{first}-{first + span - 1}"
    _cp()._story(league, "landmark", f"Scheduling: {league.user_team.school} and {t.school} agree to a "
                                     f"{KINDS[kind][0].lower()} ({span_txt}).")
    st["stories"][-1]["w"] = 8
    return f"Signed: {KINDS[kind][0]} with {t.school}, {span_txt} — {money}."
