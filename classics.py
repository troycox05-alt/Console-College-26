"""
classics.py — Instant Classics: the games people will still be talking about.

Every game in your world — watched snap by snap, coached, fast-simmed, or simmed
thirty seasons at a time — is judged the moment it ends. The ones that earn it
go into the Instant Classics book for good:

  THE UPSET         an unranked team over a top-five one, a Group of Five or FCS
                    school over a Power program, a talent gap that shouldn't lose
  THE MARATHON      overtime, and the more overtimes the better (seven is legend)
  THE ENDING        a go-ahead score in the last two minutes, the last thirty
                    seconds, or as time expires; the overtime walk-off
  THE COMEBACK      the winner was down 17, 21, 28 and came back
  THE SEESAW        lead change after lead change
  THE SHOOTOUT      both teams past 45
  THE PERFORMANCE   500 passing yards, 300 rushing, 250 receiving, seven
                    touchdowns, five sacks, three picks
  THE STAKES        ranked against ranked, rivalry and trophy games, title games
                    and the playoff (stakes lift a great game; they never make a
                    blowout one)

Classics above the top line are LEGENDARY. Each keeps its story: the headline,
why it made the book, the line score, the scoring summary and the performances,
plus the full box score (from the season archive once the season is over).

Media Center → Instant Classics, a team page → [I], the Wire, and every week's
results screen (★).
"""
from collections import Counter

from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

CLASSIC = 50
LEGENDARY = 80


def book(league):
    return league.__dict__.setdefault("classics", [])


def key_of(g, year):
    return (year, g.week, g.home.school, g.away.school)


def is_classic(league, g):
    k = key_of(g, league.year) if not getattr(g, "archived", False) else key_of(g, g.year)
    return any(tuple(c["key"]) == k for c in book(league)[-400:])


def _clock(c):
    return f"{int(c) // 60}:{int(c) % 60:02d}"


def _when(q, clock):
    if q > 4:
        return f"overtime{'' if q == 5 else ''}"
    return f"{_clock(clock)} left in the {('first', 'second', 'third', 'fourth')[q - 1]} quarter"


# ═══ Judging a game ════════════════════════════════════════════════════════

def evaluate(league, g):
    """Returns a classic record, or None. Works on any finished live game."""
    sim = getattr(g, "box", None)
    if sim is None or not g.played:
        return None
    w, l = g.winner, g.loser
    ws, ls = g.score_for(w), g.score_for(l)
    m = ws - ls
    home = g.home
    tl = list(getattr(sim, "timeline", []) or [])
    ot = getattr(sim, "ot_round", 0) or 0
    ranks = getattr(g, "ranks", {}) or {}
    rw, rl = ranks.get(w), ranks.get(l)
    tags, why, pts = [], [], {}

    def add(tag, p, text):
        tags.append(tag)
        pts[tag] = pts.get(tag, 0) + p
        if text:
            why.append(text)

    # the scoreboard story
    sign = lambda h, a: (h > a) - (h < a)
    wlead = lambda h, a: (h - a) if w is home else (a - h)
    max_def, lead_changes, prev = 0, 0, 0
    deficit_at = None
    for q, clk, h, a in tl:
        d = wlead(h, a)
        if -d > max_def:
            max_def, deficit_at = -d, (q, clk)
        s = sign(h, a)
        if s and prev and s != prev:
            lead_changes += 1
        if s:
            prev = s
    # when the winner took the lead for good
    winning = None
    for i, (q, clk, h, a) in enumerate(tl):
        before = wlead(*tl[i - 1][2:]) if i else 0
        if wlead(h, a) > 0 and before <= 0 and all(wlead(hh, aa) > 0 for _, _, hh, aa in tl[i:]):
            winning = (q, clk, before)
            break
    last_play = None
    if getattr(sim, "scoring", None):
        for q, clk, team, desc in reversed(sim.scoring):
            if team is w:
                last_play = (q, clk, desc)
                break

    if ot:
        base = {1: 12, 2: 22, 3: 32}.get(ot, 32 + (ot - 3) * 9)
        add("marathon", base, f"{ot} overtime{'s' if ot != 1 else ''}" + (" — the longest game anyone can remember" if ot >= 5 else ""))
    if winning and winning[0] == 4 and m <= 8:
        q, clk, before = winning
        if clk <= 5:
            add("ending", 34, "the winning score came with no time left on the clock")
        elif clk <= 30:
            add("ending", 26, f"the go-ahead score came with {clk} seconds left")
        elif clk <= 120:
            add("ending", 15, f"took the lead for good with {_clock(clk)} to play")
    if ot and last_play and last_play[0] > 4:
        add("ending", 6, None)
    if max_def >= 14:
        p = (max_def - 10) * 2.2
        if deficit_at and deficit_at[0] >= 4:
            p *= 1.3
        add("comeback", p, f"{w.school} came back from {max_def} down"
            + (f" in the fourth quarter" if deficit_at and deficit_at[0] >= 4 else ""))
    if lead_changes >= 4:
        add("seesaw", (lead_changes - 2) * 4, f"{lead_changes} lead changes")
    if m <= 3:
        add("close", 6, None)
    elif m <= 7:
        add("close", 3, None)
    # the upset
    gap = l.team_ovr - w.team_ovr
    if getattr(w, "fcs", False) and not getattr(l, "fcs", False):
        add("upset", 34 + max(0, gap) * 0.8, f"an FCS school beat {l.school}")
    elif rl and not rw:
        add("upset", (26 - rl) * 1.7 + (12 if rl <= 5 else 0), f"unranked {w.school} took down No. {rl} {l.school}")
    elif rl and rw and rw - rl >= 10:
        add("upset", (rw - rl) * 0.9, f"No. {rw} over No. {rl}")
    if gap >= 8 and not getattr(w, "fcs", False):
        add("upset", (gap - 6) * 2.4, f"{l.school} had the far better roster" if "upset" not in tags[:-1] else None)
    from season import schedule_tier
    if schedule_tier(w) == "group" and schedule_tier(l) == "power" and not getattr(w, "fcs", False):
        add("upset", 8, f"a Group of Five team beat a Power program")
    # shootout
    if ws >= 45 and ls >= 45:
        add("shootout", 14 if m <= 8 else 6, f"{ws + ls} combined points")
    elif ws + ls >= 100:
        add("shootout", 8, f"{ws + ls} combined points")
    # the performances
    perf = []
    for p, c in sim.stats.items():
        team = sim.team_of(p)
        name = f"{p.first_name} {p.last_name}"
        tds = c["pass_td"] + c["rush_td"] + c["rec_td"]
        lines = []
        if c["pass_yds"] >= 500:
            lines.append(((c["pass_yds"] - 450) / 4 + 10, f"{name} threw for {c['pass_yds']} yards"))
        if c["rush_yds"] >= 300:
            lines.append(((c["rush_yds"] - 260) / 3 + 10, f"{name} ran for {c['rush_yds']} yards"))
        if c["rec_yds"] >= 250:
            lines.append(((c["rec_yds"] - 220) / 3 + 10, f"{name} had {c['rec_yds']} receiving yards"))
        if tds >= 7:
            lines.append(((tds - 6) * 6 + 8, f"{name} accounted for {tds} touchdowns"))
        if c["sack"] >= 5:
            lines.append(((c["sack"] - 4) * 6 + 8, f"{name} had {c['sack']:g} sacks"))
        if c["int"] >= 3:
            lines.append(((c["int"] - 2) * 7 + 6, f"{name} intercepted {c['int']} passes"))
        if c["kr_td"] + c["pr_td"] >= 2:
            lines.append((12, f"{name} returned {c['kr_td'] + c['pr_td']} kicks for touchdowns"))
        for v, text in lines:
            perf.append((v, text, team))
    for v, text, team in sorted(perf, key=lambda x: -x[0])[:2]:
        add("performance", v, text + (f" for {team.school}" if team is not None else ""))
    # the stakes — lift a great game, never make a lopsided one
    drama = sum(pts.values())
    lift = 0
    gt = getattr(g, "game_type", "Regular Season")
    import rivalries
    riv = rivalries.rivalry_name(g.home, g.away)
    tro = rivalries.trophy(g.home, g.away)
    if rw and rl:
        lift += 10 if max(rw, rl) <= 10 else 5
    if riv or tro or rivalries.is_rivalry(g.home, g.away):
        lift += 6
    lift += {"National Championship": 18, "NP Semifinal": 12, "NP Quarterfinal": 9, "NP First Round": 7,
             "Conference Championship": 6, "Bowl": 3}.get(gt, 0)
    lift *= min(1.0, drama / 30)
    if m >= 21 and "upset" not in tags and "performance" not in tags:
        drama *= 0.4
    total = drama + lift
    if total < CLASSIC:
        return None
    rec = {
        "key": key_of(g, league.year), "year": league.year, "week": g.week, "week_name": league.week_name(g.week),
        "game_type": gt, "bowl": getattr(g, "display_name", None) or getattr(g, "bowl_name", None),
        "home": g.home.school, "away": g.away.school, "hs": g.home_score, "as": g.away_score,
        "winner": w.school, "loser": l.school, "ws": ws, "ls": ls,
        "wrank": rw, "lrank": rl, "neutral": getattr(g, "neutral", False),
        "venue": (g.venue.split(",")[0] if getattr(g, "venue", None) else g.home.stadium),
        "conf": g.conference_game, "conference": g.home.conference if g.conference_game else None,
        "rivalry": riv or (f"the game for {tro}" if tro else None),
        "ot": ot, "tags": list(dict.fromkeys(tags)), "why": why, "score": round(total, 1),
        "tier": "LEGENDARY" if total >= LEGENDARY else "CLASSIC",
        "line": {"home": list(sim.line.get(g.home, [])), "away": list(sim.line.get(g.away, []))},
        "timeline": [tuple(x) for x in tl],
        "scoring": [(q, c, getattr(t, "school", str(t)), d) for q, c, t, d in getattr(sim, "scoring", [])],
        "last_play": (last_play[2], last_play[0], last_play[1]) if last_play else None,
        "lead_changes": lead_changes, "max_deficit": max_def,
        "attendance": getattr(g, "attendance", None),
    }
    rec["headline"] = headline(rec, pts)
    return rec


def headline(r, pts):
    W = f"No. {r['wrank']} {r['winner']}" if r["wrank"] else r["winner"]
    Lz = f"No. {r['lrank']} {r['loser']}" if r["lrank"] else r["loser"]
    s = f"{r['ws']}-{r['ls']}"
    top = max(pts, key=pts.get) if pts else "close"
    ot = r["ot"]
    lp = r["last_play"][0] if r.get("last_play") else None
    if top == "marathon" or ot >= 4:
        words = ("", "ONE OVERTIME", "DOUBLE OVERTIME", "TRIPLE OVERTIME", "FOUR OVERTIMES", "FIVE OVERTIMES",
                 "SIX OVERTIMES", "SEVEN OVERTIMES", "EIGHT OVERTIMES", "NINE OVERTIMES")
        wd = words[ot] if ot < len(words) else f"{ot} OVERTIMES"
        return f"{wd}: {W} outlasts {Lz}, {s}"
    if top == "upset":
        big = r["lrank"] and r["lrank"] <= 5 and not r["wrank"]
        return f"{'THE UPSET OF THE YEAR' if big else 'STUNNER'}: {W} knocks off {Lz}, {s}"
    if top == "ending":
        if lp and r.get("last_play") and r["last_play"][2] <= 5 and r["last_play"][1] == 4:
            return f"AT THE GUN: {W} beats {Lz} {s} — {lp}"
        return f"LATE DRAMA: {W} beats {Lz} {s}" + (f" — {lp}" if lp else "")
    if top == "comeback":
        return f"THE COMEBACK: {W} erases a {r['max_deficit']}-point deficit to beat {Lz}, {s}"
    if top == "seesaw":
        return f"BACK AND FORTH: {W} survives {Lz} after {r['lead_changes']} lead changes, {s}"
    if top == "shootout":
        return f"SHOOTOUT: {W} {r['ws']}, {Lz} {r['ls']}"
    if top == "performance":
        who = r["why"][-1] if r["why"] else ""
        return f"FOR THE RECORD BOOK: {who[0].upper() + who[1:] if who else W + ' wins'}; {W} beats {Lz}, {s}"
    return f"INSTANT CLASSIC: {W} beats {Lz}, {s}"


def consider(league, g):
    """Called after every game. Adds it to the book if it earned it."""
    try:
        rec = evaluate(league, g)
    except Exception:
        return None                                  # the book never gets in the way of a Saturday
    if rec is None:
        return None
    b = book(league)
    if any(tuple(c["key"]) == tuple(rec["key"]) for c in b[-50:]):
        return None
    b.append(rec)
    return rec


def this_week(league):
    return [c for c in book(league) if c["year"] == league.year and c["week"] == league.week]


# ═══ Finding the game again ════════════════════════════════════════════════

def find_game(league, rec):
    year, week, home, away = rec["key"]
    if year == league.year:
        for g in league.schedule.get(week, []):
            if g.home.school == home and g.away.school == away:
                return g
    for g in getattr(league, "archive", {}).get(year, []):
        if g.week == week and g.home.school == home and g.away.school == away:
            return g
    return None


# ═══ Screens ══════════════════════════════════════════════════════════════

TAG_WORDS = {"marathon": "OT", "ending": "FINISH", "comeback": "COMEBACK", "seesaw": "SEESAW", "upset": "UPSET",
             "shootout": "SHOOTOUT", "performance": "RECORD DAY", "close": ""}


def _row(i, c):
    W = (f"#{c['wrank']} " if c["wrank"] else "") + c["winner"]
    Lz = (f"#{c['lrank']} " if c["lrank"] else "") + c["loser"]
    tags = " ".join(TAG_WORDS[t] for t in c["tags"] if TAG_WORDS.get(t))
    star = paint("★★", C.BYELLOW, C.BOLD) if c["tier"] == "LEGENDARY" else paint(" ★", C.BYELLOW)
    when = f"{c['year']} {'Wk ' + str(c['week']) if c['week'] <= 13 else truncate(c['bowl'] or c['week_name'], 14)}"
    ot = f" ({c['ot']}OT)" if c["ot"] else ""
    return (f"   {paint(f'{i:>3}', C.BYELLOW)} {star} {pad(paint(when, C.GRAY), 22)}"
            f"{pad(truncate(W, 20), 21)}{c['ws']:>3}-{c['ls']:<3}{pad(truncate(Lz, 20) + ot, 26)}"
            f"{paint(truncate(tags, 28), C.BCYAN)}")


def classics_screen(league, team=None):
    """The book: sort by greatness or by date, filter by season or school."""
    mode, year, page = "great", None, 0
    while True:
        items = [c for c in book(league) if (team is None or team.school in (c["home"], c["away"]))
                 and (year is None or c["year"] == year)]
        items.sort(key=(lambda c: -c["score"]) if mode == "great" else (lambda c: (-c["year"], -c["week"])))
        clear()
        sub = f"{team.school} · " if team else ""
        print(title_bar(f"INSTANT CLASSICS  ·  {sub}{year or 'ALL-TIME'}  ·  {'GREATEST' if mode == 'great' else 'MOST RECENT'}"))
        print(paint(f"   {len(items)} game{'s' if len(items) != 1 else ''}"
                    f"{'  ·  ★★ = legendary' if items else ''}", C.GRAY))
        print()
        per = 20
        show = items[page * per:(page + 1) * per]
        if not show:
            print(paint("   No classics yet. They're earned on Saturdays — upsets, overtimes, comebacks, finishes nobody "
                        "believes.", C.GRAY))
        for i, c in enumerate(show, page * per + 1):
            print(_row(i, c))
        print(rule())
        print(paint("   [#] open   [G] greatest   [R] most recent   [Y] season (e.g. Y2031, Y = all)   "
                    "[N]/[P] page   Enter = back", C.GRAY))
        ch = ask("Select:").strip().lower()
        if not ch:
            return
        if ch == "g":
            mode, page = "great", 0
        elif ch == "r":
            mode, page = "recent", 0
        elif ch.startswith("y"):
            year = int(ch[1:]) if ch[1:].isdigit() else None
            page = 0
        elif ch == "n" and (page + 1) * per < len(items):
            page += 1
        elif ch == "p" and page:
            page -= 1
        elif ch.isdigit() and 1 <= int(ch) <= len(items):
            detail(league, items[int(ch) - 1])


def _points(desc):
    if "FG" in desc:
        return 3
    if desc.startswith("Safety"):
        return 2
    pts = 6
    if "(kick)" in desc:
        pts += 1
    elif "2-pt good" in desc:
        pts += 2
    return pts


def detail(league, c):
    while True:
        clear()
        print(title_bar(f"{'LEGENDARY' if c['tier'] == 'LEGENDARY' else 'INSTANT CLASSIC'}  ·  {c['year']}  ·  "
                        f"{truncate(c['bowl'] if c['game_type'] != 'Regular Season' and c['bowl'] else c['week_name'], 30).upper()}"))
        print()
        print("   " + paint(c["headline"], C.BYELLOW, C.BOLD))
        where = f"{c['venue']}" + (f"  ·  attendance {c['attendance']:,}" if c.get("attendance") else "")
        tags = []
        if c.get("rivalry"):
            tags.append(c["rivalry"][0].upper() + c["rivalry"][1:])
        if c.get("conference"):
            tags.append(f"{c['conference']} game")
        print(paint(f"   {where}" + (f"  ·  {'  ·  '.join(tags)}" if tags else ""), C.GRAY))
        print()
        # line score
        n = max(len(c["line"]["home"]), len(c["line"]["away"]), 4)
        hdr = "".join(pad(str(i + 1) if i < 4 else ("OT" if n == 5 else f"OT{i - 3}"), 5, "right") for i in range(n))
        print("   " + pad("", 24) + paint(hdr + pad("T", 6, "right"), C.GRAY))
        for side, school, total in (("away", c["away"], c["as"]), ("home", c["home"], c["hs"])):
            qs = c["line"][side] + [0] * (n - len(c["line"][side]))
            won = school == c["winner"]
            print("   " + pad(paint(truncate(school, 22), C.BWHITE if won else C.WHITE, C.BOLD if won else ""), 24)
                  + "".join(pad(str(x), 5, "right") for x in qs)
                  + pad(paint(str(total), C.BYELLOW if won else C.WHITE, C.BOLD), 6, "right"))
        print()
        print(section("WHY IT'S IN THE BOOK", C.BYELLOW))
        for w in c["why"]:
            print(f"   • {w[0].upper() + w[1:]}")
        if c.get("lead_changes"):
            print(paint(f"   {c['lead_changes']} lead change{'s' if c['lead_changes'] != 1 else ''}"
                        f" · biggest deficit overcome: {c['max_deficit']}", C.GRAY))
        if c["scoring"]:
            print()
            print(section("SCORING SUMMARY", C.BCYAN))
            run = {c["home"]: 0, c["away"]: 0}
            for q, clk, team, desc in c["scoring"]:
                qq = f"Q{q}" if q <= 4 else "OT"
                run[team] = run.get(team, 0) + _points(desc)
                score = f"{c['away']} {run[c['away']]}, {c['home']} {run[c['home']]}"
                print(f"   {paint(pad(qq, 3), C.GRAY)} {paint(pad(_clock(clk) if q <= 4 else '', 6), C.GRAY)}"
                      f"{pad(truncate(team, 16), 17)}{pad(truncate(desc, 46), 48)}{paint(score, C.GRAY)}")
        print(rule())
        g = find_game(league, c)
        opts = "   [B] full box score   " if g is not None and g.box is not None else "   "
        print(paint(opts + "Enter = back", C.GRAY))
        ch = ask("Select:").strip().lower()
        if ch == "b" and g is not None and g.box is not None:
            import screens
            screens.show_box_score(league, g)
            continue
        return
