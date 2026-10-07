"""
coord_search.py — Hiring a coordinator the way it actually happens (Coach Career).

A coordinator search is a short, competitive process with limited time:

  BOARD       Search-firm names and the public read on each one. The read is fuzzy until
              someone on your staff actually talks to his camp.
  CALLS       A quiet call to his agent (5 per opening). Tells you whether he's really
              interested, what kind of coach he is, and the one thing he cares about most.
  INTERVIEWS  A formal sit-down (3 per opening). His camp lays out what it would take:
              salary, years, play-calling, a title, an out-clause for head-coaching jobs.
              You hear what's pulling him toward the job and what's pushing him away.
  OFFER       A package, not just a number. He accepts, counters with specific terms, or
              declines. Lowballs sour him; three rounds and the talks are over.
  RETENTION   A sitting assistant's school can match. You get one chance to top it.
  FUNDING     Only after a verbal yes does your AD have to find the money, so you never
              cut NIL deals for a coach who then says no.

The market doesn't wait: every call, interview and offer takes days, and candidates you
haven't engaged can take themselves out of your search. Every candidate's floor and
priorities are fixed for the search (seeded), so re-offering a few dollars more never
re-rolls a decision. Computer-controlled schools still hire through staff.py; this module
is only the human side of the table.
"""
import random

import finance as fi
import staff
from ui import C, ask, clear, pad, paint, pause, rating, rule, title_bar, truncate

CALLS = 5                 # quiet calls to agents, per opening
INTERVIEWS = 3            # formal interviews, per opening
ROUNDS = 3                # offer rounds before talks end
BOARD = 12                # names on the board
ACCEPT_AT = 62            # package-adjusted interest a coach needs to say yes
COUNTER_AT = 44           # ...and the level where he'll at least come back with terms
MARKET_ODDS = 0.17        # chance per action that an unengaged name leaves your search

READS = [(82, "very interested"), (65, "interested"), (48, "open to it"), (32, "long shot"), (0, "not interested")]
FUZZY = [(88, "strong buzz"), (70, "some buzz"), (50, "quiet"), (0, "cold")]
PRIORITY_TEXT = {"money": "getting paid", "calls": "calling plays", "security": "job security (years)",
                 "stage": "a bigger stage", "title": "the assistant head coach title",
                 "path": "a path to a head-coaching job", "loyalty": "loyalty to the people he works with"}


def _read(score, table=READS):
    return next(w for lo, w in table if score >= lo)


def _rng(league, team, role, c, tag):
    return random.Random(f"cs:{league.seed}:{league.year}:{team.school}:{role}:{c.name}:{tag}")


# ═══ Search state (saved with the league) ═══════════════════════════════════

def _state(league, team, role):
    """The open search for this chair. A finished search stays on the books for the year,
    and anyone who withdrew or declined stays out of a second search that same winter."""
    book = league.__dict__.setdefault("coord_searches", {})
    base = f"{league.year}:{team.school}:{role}"
    n = 0
    while book.get(f"{base}:{n}", {}).get("closed"):
        n += 1
    key = f"{base}:{n}"
    if key not in book:
        carry = {}
        for k in range(n):
            for name, row in book.get(f"{base}:{k}", {}).get("cand", {}).items():
                if row.get("status") in ("declined", "withdrew", "stayed"):
                    carry[name] = {"status": row["status"], "note": row.get("note", "")}
        book[key] = {"calls": CALLS, "interviews": INTERVIEWS, "actions": 0, "cand": carry, "news": [],
                     "closed": False}
    return book[key]


def _row(st, c):
    return st["cand"].setdefault(c.name, {"status": "", "rounds": 0, "mood": 0, "note": ""})


# ═══ Who he is ══════════════════════════════════════════════════════════════

def kind_of(team, c):
    pc = c.__dict__.get("_from_pos")
    if pc is not None:
        return "own" if pc.school == team.school else "promotion"
    if c.team is not None and staff.role_of(c) in ("OC", "DC"):
        return "sitting"
    if staff.role_of(c) == "HC" or (c.history and c.team is None):
        return "former_hc"
    return "available"


def _current_school(c):
    pc = c.__dict__.get("_from_pos")
    if pc is not None:
        return pc.school
    return c.team.school if c.team is not None else None


def _current_prestige(league, c):
    school = _current_school(c)
    t = next((x for x in league.teams if x.school == school), None) if school else None
    return (t.prestige if t is not None else None), t


def _calls_now(c):
    """Is he calling plays where he is right now?"""
    t = c.team
    if t is None or staff.role_of(c) not in ("OC", "DC"):
        return staff.role_of(c) == "HC"                        # a former head coach ran the whole thing
    side = "off" if staff.role_of(c) == "OC" else "def"
    try:
        return staff.calls(t)[side] == staff.role_of(c)
    except Exception:
        return False


def _seat(team):
    coach = team.coach
    if coach is None:
        return 0.0, 0.0
    try:
        import carousel
        line = carousel.fire_line(team)
    except Exception:
        line = 80
    return float(getattr(coach, "seat", 30) or 30), float(line)


def _region_of(team):
    try:
        import carousel
        return carousel.region_of(team)
    except Exception:
        return None


def _home_region(c):
    try:
        import carousel
        return carousel.home_region(c)
    except Exception:
        return None


def profile(league, team, role, c, tie):
    """Everything fixed about this candidate for this search: interest and why, plus the
    terms his camp will need. Deterministic for (world, year, school, role, coach)."""
    r = _rng(league, team, role, c, "profile")
    kind = kind_of(team, c)
    prestige = float(team.prestige)
    curp, cur_team = _current_prestige(league, c)
    ovr = float(c.overall)
    pers = getattr(c, "personality", "builder") or "builder"
    why = []

    def add(pts, text):
        pts = round(pts)
        if pts:
            why.append((pts, text))

    # Stature: good coaches expect good jobs. An 88 expects a top-25 type program.
    expected = 35 + max(0, ovr - 55) * 1.55
    add((prestige - expected) * 1.1, f"{team.school}'s stature for a coach of his level")
    # The step from where he is.
    if kind == "sitting" and curp is not None:
        add((prestige - curp) * 0.9, f"step {'up' if prestige >= curp else 'down'} from {cur_team.school}")
        from season import BIG_CONFERENCES
        if cur_team.conference not in BIG_CONFERENCES and team.conference in BIG_CONFERENCES:
            add(7, "jump to a Power conference")
        tenure = league.year - getattr(c, "coord_since", league.year) + 1
        if tenure < 2 and not tie:
            add(-24, f"only just arrived at {cur_team.school}")
        if pers == "loyalist":
            add(-16, f"loyal to {cur_team.school}")
        if pers == "survivor" and cur_team.coach is not None:
            hs, hl = _seat(cur_team)
            if hs >= hl - 12:
                add(16, f"his boss at {cur_team.school} is on the hot seat")
    elif kind == "promotion":
        add(20, "first chance to be a coordinator")
        if curp is not None and curp > prestige + 15:
            add(-(curp - prestige - 15) * 0.8, f"would leave {_current_school(c)} for a smaller program")
    elif kind == "own":
        add(30, "a promotion inside your own building")
    elif kind == "former_hc":
        if prestige >= 70:
            add(10, "a big stage to rebuild his name")
        else:
            add(-10, "a former head coach wants a bigger platform")
        add(12, "out of work")
    else:
        add(15, "out of work")
    # People.
    if tie:
        add(22, "he's worked with you before")
    elif team.coach is not None and team.coach.name in getattr(c, "staff_ties", set()):
        add(14, "knows you from an old staff")
    if getattr(c, "alma_mater", None) == team.school:
        add(18, f"played at {team.school}")
    # Place.
    if pers == "homebody" and not tie:
        home, here = _home_region(c), _region_of(team)
        if home and here and home != here:
            add(-38, f"won't leave the {home}")
        elif home and here == home:
            add(6, "stays close to home")
    if getattr(c, "recruit_region", None) and getattr(c, "recruit_region", None) == _region_of(team):
        add(4, "already recruits this region")
    # Personality and ambition.
    if pers == "blue_blood" and prestige < 82:
        add(-22, "only wants the biggest programs")
    elif pers == "blue_blood":
        add(8, "a blue-blood job")
    if pers in ("climber", "mercenary") and prestige >= 70:
        add(7, "a springboard to a head-coaching job")
    if pers == "fixer" and prestige < 60:
        add(8, "likes a program that needs fixing")
    if pers == "journeyman":
        add(5, "always ready to move")
    if pers == "short_timer" and getattr(c, "age", 45) >= 56:
        add(-8, "not sure how many more years he'll coach")
    # Your situation: assistants get fired with their head coach.
    seat, line = _seat(team)
    if seat >= line - 8:
        add(-18, "your seat is hot — staffs get fired together")
    elif seat >= line - 20:
        add(-7, "your seat is warming up")
    elif seat <= 20:
        add(4, "you look secure at this job")
    # Scheme: unless he calls the plays, he coaches yours.
    mine = team.coach.offense_scheme if role == "OC" else team.coach.defense_scheme
    his = c.offense_scheme if role == "OC" else c.defense_scheme
    scheme_gap = his != mine

    base = 50 + sum(p for p, _ in why) + r.gauss(0, 4)
    if getattr(c, "moved_year", None) == league.year:
        base = 0
        why = [(-99, "just signed somewhere else this winter")]

    # Terms. The floor is what he'll actually take; the ask is where his agent starts.
    mw = fi.money_weight(c) if hasattr(fi, "money_weight") else 1.0
    try:
        asking = fi.asking(league, c, role, team)
    except Exception:
        asking = fi.COORD_SHARE * fi.budget(team)
    if kind == "own":
        asking = max(asking * 0.85, fi.COORD_SHARE * fi.budget(team) * 0.55)
    floor = asking * r.uniform(0.92, 1.02) * (1 + (mw - 1) * 0.12)
    if kind == "sitting" and fi.contract(c):
        floor = max(floor, fi.salary(c) * 1.08)                 # nobody moves for a pay cut
    pc = c.__dict__.get("_from_pos")
    if pc is not None and cur_team is not None:
        import poscoach
        try:                                                    # a promotion still has to be a raise
            floor = max(floor, poscoach.salary(pc, cur_team) * (1.15 if kind == "own" else 1.25))
        except Exception:
            pass
    floor = fi._round(floor, 5_000)
    opening = fi._round(floor * r.uniform(1.08, 1.18), 5_000)

    age = getattr(c, "age", 45)
    want_years = 4 if age >= 52 or seat >= line - 15 else 3
    if pers in ("climber", "mercenary", "journeyman") and age < 50:
        want_years = 2 if seat < line - 15 else 3
    calls_now = _calls_now(c)
    if calls_now and ovr >= 70:
        calls = "must"
    elif calls_now or (pers in ("climber", "mercenary", "blue_blood") and ovr >= 68) or scheme_gap:
        calls = "wants"
    else:
        calls = "no"
    wants_title = pers in ("climber", "blue_blood", "mercenary") or (ovr >= 78 and r.random() < 0.4)
    out_clause = (pers in ("climber", "mercenary", "blue_blood") or getattr(c, "ceiling", 0) - ovr >= 8) \
        and age < 55 and kind != "own"

    weights = {"money": 1.0 * mw, "calls": {"must": 1.6, "wants": 1.0, "no": 0.2}[calls],
               "security": 1.2 if want_years >= 4 else 0.5, "stage": 0.9 if pers in ("blue_blood", "climber") else 0.4,
               "title": 0.9 if wants_title else 0.1, "path": 1.0 if out_clause else 0.1,
               "loyalty": 1.3 if pers == "loyalist" or tie else 0.2}
    top = max(weights, key=weights.get)

    # Retention: how likely his school matches once he says yes.
    match = 0.0
    if kind == "sitting" and cur_team is not None:
        match = 0.12 + max(0.0, (curp - prestige)) * 0.012 + (0.12 if pers == "loyalist" else 0) \
            + (0.08 if c.overall >= 80 else 0) - (0.08 if pers in ("mercenary", "journeyman") else 0)
        match *= {"booster": 1.3, "big_game": 1.2, "win_now": 1.15, "recruiting": 0.8,
                  "analytics": 0.85}.get(getattr(cur_team, "ad", {}).get("style", ""), 1.0)
    elif kind == "promotion" and cur_team is not None:
        match = 0.10 + (0.08 if cur_team.prestige > prestige else 0)
    match = max(0.0, min(0.5, match))

    return {"kind": kind, "interest": max(0, min(100, round(base))), "why": sorted(why), "floor": floor,
            "opening": opening, "years": want_years, "calls": calls, "title": wants_title,
            "out": out_clause, "top": top, "match": match, "match_roll": r.random(),
            "noise": r.gauss(0, 3), "fuzz": r.gauss(0, 9), "scheme_gap": scheme_gap, "his_scheme": his,
            "mine": mine, "current": _current_school(c)}


# ═══ Judging a package ══════════════════════════════════════════════════════

def evaluate(prof, mood, offer):
    """(score, problems): package-adjusted interest, and what's still wrong with the offer."""
    score = prof["interest"] + mood + prof["noise"]
    problems = []
    ratio = offer["salary"] / max(1, prof["floor"])
    if ratio < 1.0:
        score -= (1.0 - ratio) * 120
        problems.append("money")
    else:
        score += min(14, (ratio - 1.0) * 70)
    gap = offer["years"] - prof["years"]
    if gap < 0:
        score -= 5 * -gap * (1.5 if prof["years"] >= 4 else 1.0)
        problems.append("years")
    if offer["years"] == 1:
        score -= 10
    if prof["calls"] == "must" and not offer["calls"]:
        score -= 30
        problems.append("calls")
    elif prof["calls"] == "wants" and not offer["calls"]:
        score -= 9
        problems.append("calls")
    elif offer["calls"]:
        score += 6 if prof["calls"] != "no" else 2
    if offer["title"]:
        score += 8 if prof["title"] else 2
    elif prof["title"]:
        score -= 3
    if offer["out"]:
        score += 7 if prof["out"] else 0
    elif prof["out"]:
        score -= 4
        problems.append("out")
    return score, problems


def _counter(prof, offer):
    """The terms his agent sends back: fix every shortfall, ask a little extra on money."""
    want = dict(offer)
    want["salary"] = max(offer["salary"], fi._round(prof["floor"] * 1.04, 5_000))
    want["years"] = max(offer["years"], prof["years"])
    if prof["calls"] in ("must", "wants"):
        want["calls"] = True
    if prof["out"]:
        want["out"] = True
    return want


# ═══ Screens ════════════════════════════════════════════════════════════════

def _side(c, role):
    keys = staff.SIDE_KEYS[role]
    return round(sum(c.ratings[k] for k in keys) / len(keys))


def _now(c, kind):
    pc = c.__dict__.get("_from_pos")
    if pc is not None:
        import poscoach
        return f"{pc.school or 'free'} {poscoach.TITLE[pc.group]} coach"
    if kind == "sitting":
        return f"{c.team.school} {staff.role_of(c)}"
    if kind == "former_hc" and c.history:
        return f"former {c.history[-1]['school']} HC"
    if getattr(c, "coord_history", None):
        return f"available · was {c.coord_history[-1]['school']}"
    return c.origin


def _last_unit(c):
    last = c.coord_history[-1] if getattr(c, "coord_history", None) else None
    if not last:
        return "no coordinator résumé yet"
    what = "offense" if last.get("role") == "OC" else "defense"
    return f"{last.get('year', '')} {last['school']} {what} #{last['rank']} (talent #{last['exp']})"


def _fit(bits, width):
    """Keep whole pieces of a detail line, dropping the last ones that don't fit."""
    import re
    out, used = [], 0
    for b in bits:
        n = len(re.sub(r"\x1b\[[0-9;]*m", "", b)) + (3 if out else 0)
        if used + n > width:
            break
        out.append(b)
        used += n
    return out


def _status_word(row):
    s = row.get("status")
    return {"called": paint("called", C.BCYAN), "interviewed": paint("interviewed", C.BGREEN),
            "declined": paint("declined", C.BRED), "withdrew": paint("withdrew", C.BRED),
            "stayed": paint("stayed put", C.BRED), "talks": paint("in talks", C.BYELLOW)}.get(s, "")


def _board(league, team, role, options):
    """The names worth a call: top of the market, plus everyone you've worked with."""
    seen, out = set(), []
    for c, tie in options:
        if c.name in seen or getattr(c, "moved_year", None) == league.year:
            continue
        seen.add(c.name)
        prof = profile(league, team, role, c, tie)
        if prof["interest"] < 8 and not tie and prof["kind"] != "own":
            continue                                   # his agent won't return the call
        out.append((c, tie, prof))
    out.sort(key=lambda x: -(staff._score(team, x[0], role, league) + (6 if x[1] else 0)))
    return out[:BOARD]


def _tick(league, team, role, st, board, engaged):
    """Time passes in a search. Someone you haven't talked to may leave the market."""
    st["actions"] += 1
    r = random.Random(f"cs-market:{league.seed}:{league.year}:{team.school}:{role}:{st['actions']}")
    if r.random() >= MARKET_ODDS:
        return None
    pool = [(c, prof) for c, _, prof in board
            if not _row(st, c).get("status") and c.name != engaged and prof["kind"] != "own"]
    if not pool:
        return None
    pool.sort(key=lambda x: -x[0].overall)
    c, prof = pool[0] if r.random() < 0.55 else r.choice(pool)
    row = _row(st, c)
    if prof["kind"] == "sitting":
        row["status"], row["note"] = "stayed", f"commits to staying at {prof['current']}"
    else:
        row["status"], row["note"] = "withdrew", "takes his name out — other jobs are further along"
    line = f"{c.name} {row['note']}."
    st["news"].append(line)
    return line


def _header(league, team, role, st):
    clear()
    title = f"{'OFFENSIVE' if role == 'OC' else 'DEFENSIVE'} COORDINATOR SEARCH  ·  {team.school.upper()}"
    print(title_bar(title))
    seat, line = _seat(team)
    heat = "hot" if seat >= line - 8 else "warm" if seat >= line - 20 else "stable"
    free = fi.available(league, team)
    est = fi.COORD_SHARE * fi.budget(team)
    print(paint(f"   Calls left {st['calls']}/{CALLS}  ·  interviews left {st['interviews']}/{INTERVIEWS}  ·  "
                f"your seat: {heat}  ·  standard coordinator pay {fi.money(est)}  ·  free money {fi.money(free)}",
                C.GRAY))


def _show_board(league, team, role, st, board):
    _header(league, team, role, st)
    import carousel as cz
    for line in st["news"][-3:]:
        print(paint(f"   ▸ {line}", C.BYELLOW))
    print(paint(f"\n   {'#':>2}  {'COACH':<22}{'AGE':>4}{'OVR':>5}{'SIDE':>5}  {'THE READ':<17}{'NOW':<28}{'STATUS'}",
                C.GRAY, C.BOLD))
    for i, (c, tie, prof) in enumerate(board, 1):
        row = _row(st, c)
        known = row.get("status") in ("called", "interviewed", "talks")
        if row.get("status") in ("declined", "withdrew", "stayed"):
            read = paint("—", C.GRAY)
        elif known:
            read = paint(_read(prof["interest"] + row.get("mood", 0)), C.BWHITE)
        else:
            read = paint(_read(prof["interest"] + prof["fuzz"], FUZZY) + "?", C.GRAY)
        star = paint("★", C.BYELLOW, C.BOLD) if tie else " "
        print(f"   {i:>2} {star}{pad(truncate(c.name, 21), 22)}{c.age:>4}{pad(rating(c.overall), 5, 'right')}"
              f"{pad(rating(_side(c, role)), 5, 'right')}  {pad(read, 17)}"
              f"{pad(paint(truncate(_now(c, prof['kind']), 27), C.GRAY), 28)}{_status_word(row)}")
        bits = []
        if known:
            bits.append(paint(cz.PERSONALITIES.get(c.personality, ("—",))[0], C.BCYAN))
        if _calls_now(c):
            bits.append("calls plays")
        bits += [f"Pot. {staff.potential_word(c)}", f"REC {c.ratings['recruiting']}", _last_unit(c)]
        if prof["scheme_gap"]:
            bits.append(f"runs {prof['his_scheme']}")
        print(paint("        ", C.GRAY) + paint(" · ", C.GRAY).join(
            b if "\x1b" in b else paint(b, C.GRAY) for b in _fit(bits, 90)))
    print(paint("\n   THE READ is public buzz (?) until your staff talks to his camp. ★ = worked with you.", C.GRAY))
    print(rule())
    print(f"   {paint('[C#]', C.BCYAN)} quiet call   {paint('[I#]', C.BGREEN)} formal interview   "
          f"{paint('[O#]', C.BYELLOW, C.BOLD)} make an offer   {paint('[V#]', C.GRAY)} résumé   "
          f"{paint('[A]', C.GRAY)} let your AD hire   {paint('[?]', C.GRAY)} how this works")


def _help():
    clear()
    print(title_bar("HOW A COORDINATOR SEARCH WORKS"))
    for line in (
        "Every opening gets 5 quiet calls and 3 formal interviews. Spend them carefully.",
        "",
        "QUIET CALL: tells you his real interest, his personality and what he cares about most.",
        "INTERVIEW: his camp lays out its terms and you hear what's pulling him toward (and",
        "           away from) your job. You need an interview before you can make an offer,",
        "           unless he's worked with you before or he's already on your staff.",
        "OFFER: salary, years, play-calling, the assistant head coach title, and an out-clause",
        "       for head-coaching jobs. He accepts, counters with specific terms, or declines.",
        "       A lowball sours him. After three rounds the talks are over.",
        "",
        "The market moves. Every call, interview and offer takes days, and good coaches you",
        "haven't talked to can commit to staying put or take themselves out of your search.",
        "",
        "A sitting coordinator's school can match your offer once he says yes. You get one",
        "chance to top it. Only after he agrees does your AD have to find the money.",
        "",
        "Promises count. Take play-calling away from a coordinator you promised it to and he'll",
        "start listening when other schools call.",
        "",
        "What moves interest: your program's stature for his level, the step from his current",
        "job, a jump to a Power league, a first coordinator job, ties to you, his alma mater,",
        "home region, personality, how hot your seat is, and whether he'd have to run your scheme.",
    ):
        print(paint("   " + line, C.WHITE if line.isupper() or line[:5].isupper() else C.GRAY))
    pause()


def _call(league, team, role, st, board, idx):
    c, tie, prof = board[idx]
    row = _row(st, c)
    if row.get("status") in ("declined", "withdrew", "stayed"):
        print(paint(f"   {c.name} is out of this search: {row.get('note') or row['status']}.", C.BRED)); pause(); return
    if row.get("status") in ("called", "interviewed", "talks"):
        print(paint(f"   You've already talked to {c.name}'s camp.", C.BYELLOW)); pause(); return
    if st["calls"] <= 0:
        print(paint("   You've used every quiet call this search. Interview someone or make an offer.", C.BYELLOW))
        pause(); return
    st["calls"] -= 1
    row["status"] = "called"
    import carousel as cz
    pname, blurb, _ = cz.PERSONALITIES.get(c.personality, ("—", "", {}))
    print(paint(f"\n   Your staff calls {c.name}'s agent.", C.GRAY))
    print(paint(f"   The real read: {_read(prof['interest'] + row.get('mood', 0))}.", C.BWHITE, C.BOLD))
    print(paint(f"   What kind of coach: {pname} — {blurb.lower()}.", C.GRAY))
    print(paint(f"   What matters most to him: {PRIORITY_TEXT[prof['top']]}.", C.BCYAN))
    if prof["interest"] < 32:
        print(paint("   His agent is polite, but it would take something special.", C.BYELLOW))
    news = _tick(league, team, role, st, board, c.name)
    if news:
        print(paint(f"\n   ▸ Meanwhile: {news}", C.BYELLOW))
    pause()


def _interview(league, team, role, st, board, idx):
    c, tie, prof = board[idx]
    row = _row(st, c)
    if row.get("status") in ("declined", "withdrew", "stayed"):
        print(paint(f"   {c.name} is out of this search: {row.get('note') or row['status']}.", C.BRED)); pause(); return
    if row.get("status") in ("interviewed", "talks"):
        _terms_sheet(league, team, role, c, prof, row); pause(); return
    if st["interviews"] <= 0:
        print(paint("   You're out of interview slots for this opening.", C.BYELLOW)); pause(); return
    if prof["interest"] + row.get("mood", 0) < 26 and not tie and prof["kind"] != "own":
        # No interview slot spent, but the search still lost a few days finding out.
        print(paint(f"   {c.name}'s camp declines the interview. He doesn't see {team.school} as the right move.",
                    C.BRED))
        row["status"], row["note"] = "declined", "declined to interview"
        news = _tick(league, team, role, st, board, c.name)
        if news:
            print(paint(f"\n   ▸ Meanwhile: {news}", C.BYELLOW))
        pause(); return
    st["interviews"] -= 1
    row["status"] = "interviewed"
    # The sit-down itself moves him a little: your program, your pitch, your plan.
    r = _rng(league, team, role, c, "interview")
    pitch = r.gauss(0, 5) + (team.coach.overall - 70) * 0.15 + (3 if not prof["scheme_gap"] else -2)
    row["mood"] = row.get("mood", 0) + round(pitch)
    clear()
    print(title_bar(f"INTERVIEW  ·  {c.name.upper()}  ·  {staff.ROLE_NAMES[role].upper()}"))
    print(paint(f"\n   {c.name}, {c.age} · OVR {c.overall} · {_now(c, prof['kind'])} · {_last_unit(c)}", C.GRAY))
    print(paint(f"   He asks about autonomy, staff resources, your timeline and what the job really is.", C.GRAY))
    if pitch >= 4:
        print(paint("   The meeting goes well. He leaves more interested than he came in.", C.BGREEN))
    elif pitch <= -4:
        print(paint("   It's a flat meeting. Something didn't click.", C.BYELLOW))
    _terms_sheet(league, team, role, c, prof, row)
    news = _tick(league, team, role, st, board, c.name)
    if news:
        print(paint(f"\n   ▸ Meanwhile: {news}", C.BYELLOW))
    pause()


def _terms_sheet(league, team, role, c, prof, row):
    print(paint(f"\n   Where he stands: {_read(prof['interest'] + row.get('mood', 0))}", C.BWHITE, C.BOLD))
    pulls = [t for p, t in prof["why"] if p > 0][-4:][::-1]
    pushes = [t for p, t in prof["why"] if p < 0][:4]
    if pulls:
        print(paint("   Pulling him toward the job:  " + "; ".join(pulls), C.BGREEN))
    if pushes:
        print(paint("   Holding him back:            " + "; ".join(pushes), C.BRED))
    calls = {"must": "He calls the plays, period. That's not negotiable.",
             "wants": "He wants to call the plays.",
             "no": "Play-calling isn't a sticking point for him."}[prof["calls"]]
    if prof["scheme_gap"] and prof["calls"] != "must":
        calls += f" (He runs {prof['his_scheme']}; you run {prof['mine']}.)"
    print(paint(f"\n   HIS CAMP'S TERMS", C.BYELLOW, C.BOLD))
    print(paint(f"   · Salary: they open at {fi.money(prof['opening'])}/yr", C.WHITE))
    print(paint(f"   · Years: wants at least {prof['years']}", C.WHITE))
    print(paint(f"   · {calls}", C.WHITE))
    if prof["title"]:
        print(paint("   · Would value the assistant head coach title", C.WHITE))
    if prof["out"]:
        print(paint("   · Wants an out-clause if a head-coaching job comes open", C.WHITE))
    print(paint(f"   · Biggest thing for him: {PRIORITY_TEXT[prof['top']]}", C.BCYAN))
    if prof["match"] >= 0.25:
        print(paint(f"   · {prof['current']} will fight to keep him.", C.BYELLOW))


def _ask_offer(league, team, role, c, prof, last=None):
    """Build a package at the keyboard. Returns an offer dict or None."""
    seed = last or {"salary": prof["opening"], "years": prof["years"], "calls": prof["calls"] == "must",
                    "title": False, "out": False}
    print(paint(f"\n   BUILD THE OFFER  (Enter keeps the value in brackets)", C.BYELLOW, C.BOLD))
    amt = ask(f"Salary per year [{fi.money(seed['salary'])}]:").strip()
    pay = seed["salary"] if not amt else fi.parse_money(amt)
    if not pay or pay <= 0:
        return None
    cap = fi.COORD_CAP * fi.budget(team)
    if pay > cap * 1.25:
        print(paint(f"   Your AD won't sign off on more than {fi.money(cap * 1.25)} for a coordinator.", C.BRED))
        pay = int(cap * 1.25)
    yrs = ask(f"Years 1-5 [{seed['years']}]:").strip()
    years = int(yrs) if yrs.isdigit() and 1 <= int(yrs) <= 5 else seed["years"]

    def yn(label, cur):
        a = ask(f"{label} (y/n) [{'y' if cur else 'n'}]:").strip().lower()
        return cur if not a else a in ("y", "yes")
    side = "offense" if role == "OC" else "defense"
    calls = yn(f"He calls the {side}?", seed["calls"])
    title = yn("Assistant head coach title?", seed["title"])
    out = yn("Out-clause for head-coaching jobs?", seed["out"])
    return {"salary": int(pay), "years": years, "calls": calls, "title": title, "out": out}


def _package_line(o, role):
    bits = [f"{fi.money(o['salary'])}/yr", f"{o['years']} yr{'s' if o['years'] != 1 else ''}"]
    if o["calls"]:
        bits.append(f"calls the {'offense' if role == 'OC' else 'defense'}")
    if o["title"]:
        bits.append("AHC title")
    if o["out"]:
        bits.append("HC out-clause")
    return " · ".join(bits)


def _to_contract(team, role, o):
    """The finance-side offer the rest of the game signs."""
    ad = fi._ad(team)
    offer = {"salary": int(o["salary"]), "years": int(o["years"]), "role": role,
             "buyout": round(max(0.25, ad["buyout"] - (0.25 if o["out"] else 0)), 2)}
    if o["calls"]:
        offer["play_calling"] = True
    if o["title"]:
        offer["ahc"] = True
    if o["out"]:
        offer["hc_out"] = True
    return offer


def _negotiate(league, team, role, st, board, idx):
    """Rounds of offers and counters. Returns a contract offer, or None."""
    c, tie, prof = board[idx]
    row = _row(st, c)
    if row.get("status") in ("declined", "withdrew", "stayed"):
        print(paint(f"   {c.name} is out of this search: {row.get('note') or row['status']}.", C.BRED)); pause(); return None
    if row.get("status") not in ("interviewed", "talks") and not tie and prof["kind"] != "own":
        print(paint(f"   Interview {c.name} first — no camp takes an offer from a school it hasn't sat down with.",
                    C.BYELLOW)); pause(); return None
    if row.get("status") not in ("interviewed", "talks"):
        _terms_sheet(league, team, role, c, prof, row)  # you know him: no interview needed
    row["status"] = "talks"
    last = None
    while row["rounds"] < ROUNDS:
        clear()
        print(title_bar(f"OFFER  ·  {c.name.upper()}  ·  ROUND {row['rounds'] + 1} OF {ROUNDS}"))
        _terms_sheet(league, team, role, c, prof, row)
        free = fi.available(league, team)
        print(paint(f"\n   Standard coordinator pay here: {fi.money(fi.COORD_SHARE * fi.budget(team))}  ·  "
                    f"free money: {fi.money(free)}", C.GRAY))
        o = _ask_offer(league, team, role, c, prof, last)
        if o is None:
            print(paint("   You step away from the table. He's still on the board.", C.GRAY))
            row["status"] = "interviewed"
            pause(); return None
        row["rounds"] += 1
        score, problems = evaluate(prof, row.get("mood", 0), o)
        _tick(league, team, role, st, board, c.name)
        print(paint(f"\n   Offer sent: {_package_line(o, role)}. His camp takes a day with it…", C.GRAY))
        if o["salary"] < prof["floor"] * 0.82:
            row["mood"] = row.get("mood", 0) - 8
            print(paint("   His agent calls it a lowball. That didn't help.", C.BRED))
        if score >= ACCEPT_AT and not ("calls" in problems and prof["calls"] == "must") \
                and o["salary"] >= prof["floor"] * 0.97:
            print(paint(f"   {c.name} says yes, pending the paperwork.", C.BGREEN, C.BOLD))
            pause()
            return _close(league, team, role, st, c, prof, row, o)
        if score >= COUNTER_AT and row["rounds"] < ROUNDS:
            want = _counter(prof, o)
            # A counter has to actually get there; if even his terms wouldn't, say so honestly.
            if evaluate(prof, row.get("mood", 0), want)[0] >= ACCEPT_AT:
                print(paint(f"   His agent counters: {_package_line(want, role)}.", C.BYELLOW, C.BOLD))
                a = ask("[Y] accept the counter   [N] make a new offer   [W] walk away:").strip().lower()
                if a in ("y", "yes"):
                    print(paint(f"   Done. {c.name} agrees to terms.", C.BGREEN, C.BOLD))
                    pause()
                    return _close(league, team, role, st, c, prof, row, want)
                if a in ("w", "walk"):
                    row["status"], row["note"] = "declined", "talks ended when you walked away"
                    pause(); return None
                last = want
                row["mood"] = row.get("mood", 0) - 2           # patience runs thin
                continue
        if score >= COUNTER_AT - 10 and row["rounds"] < ROUNDS:
            short = {"money": "the money", "years": "the length", "calls": "play-calling",
                     "out": "a way out for a head job"}
            if problems:
                what = ", ".join(short[p] for p in problems)
                print(paint(f"   Not there yet. Sticking points: {what}.", C.BYELLOW))
            else:
                print(paint("   The terms are fine — it's the fit. It would take more money or a bigger role "
                            "(play-calling, the title) to move him.", C.BYELLOW))
            row["mood"] = row.get("mood", 0) - 3
            last = o
            pause()
            continue
        break
    row["status"], row["note"] = "declined", "turned down your offer"
    reason = ("the fit was never strong enough" if prof["interest"] + row.get("mood", 0) < 45
              else "the package never got where it needed to be")
    print(paint(f"   {c.name} declines — {reason}. He's out of this search.", C.BRED, C.BOLD))
    pause()
    return None


def _close(league, team, role, st, c, prof, row, o):
    """Verbal yes → his school's counter → the AD finds the money → signed."""
    if prof["match"] > 0 and prof["match_roll"] < prof["match"]:
        theirs = fi._round(o["salary"] * 1.12, 5_000)
        print(paint(f"\n   {prof['current']} isn't letting him go quietly: they match and raise to "
                    f"{fi.money(theirs)}/yr.", C.BYELLOW, C.BOLD))
        a = ask(f"[T] top it   [Enter] let him stay:").strip().lower()
        if a != "t":
            row["status"], row["note"] = "stayed", f"took {prof['current']}'s counteroffer"
            print(paint(f"   {c.name} stays at {prof['current']}.", C.BRED)); pause(); return None
        amt = ask(f"Your final number (must beat {fi.money(theirs)}):").strip()
        pay = fi.parse_money(amt) if amt else 0
        cap = fi.COORD_CAP * fi.budget(team) * 1.25
        loyal = getattr(c, "personality", "") == "loyalist"
        r = _rng(league, team, role, c, "retain")
        if not pay or pay < theirs * 1.03 or pay > cap or (loyal and r.random() < 0.5):
            row["status"], row["note"] = "stayed", f"took {prof['current']}'s counteroffer"
            why = "your AD can't go that high" if pay and pay > cap else "it wasn't enough to pull him away"
            print(paint(f"   {c.name} stays at {prof['current']} — {why}.", C.BRED, C.BOLD)); pause(); return None
        o = dict(o, salary=int(pay))
        print(paint(f"   You top it. {c.name} is coming.", C.BGREEN, C.BOLD))
    est = fi.COORD_SHARE * fi.budget(team)
    free = fi.available(league, team)
    if o["salary"] - est > max(0, free):
        import budget_fix
        if not budget_fix.cover(league, team, o["salary"] - est, f"{c.name}'s salary: {fi.money(o['salary'])}/yr"):
            row["status"], row["note"] = "withdrew", "the money couldn't be approved"
            print(paint(f"   Your AD can't approve the money. {c.name}'s camp moves on.", C.BRED, C.BOLD))
            pause(); return None
    offer = _to_contract(team, role, o)
    print(paint(f"   {c.name} signs: {fi.terms(offer)}" + (f" · {_package_line(o, role).split(' · ', 2)[-1]}"
                                                            if any((o['calls'], o['title'], o['out'])) else ""),
                C.BGREEN, C.BOLD))
    st["closed"] = True
    return offer


# ═══ Entry point ════════════════════════════════════════════════════════════

def pick(league, team, role, options):
    """Run your search. Returns (coach, offer), or None to let the AD choose."""
    st = _state(league, team, role)
    board = _board(league, team, role, options)
    if not board:
        print(paint("   Nobody on the market will take the call for this job. Your AD will find someone.", C.BYELLOW))
        pause()
        return None
    while True:
        _show_board(league, team, role, st, board)
        ch = ask("Your move:").strip().lower()
        if ch == "a":
            if ask("Let your AD make the hire? (y/n)").strip().lower() in ("y", "yes"):
                return None
            continue
        if ch == "?":
            _help()
            continue
        verb, num = (ch[:1], ch[1:]) if ch[:1] in ("c", "i", "o", "v") else ("c", ch)
        if not num.isdigit() or not 1 <= int(num) <= len(board):
            continue
        idx = int(num) - 1
        if verb == "v":
            import coach_screens
            coach_screens.coach_view(league, board[idx][0])
        elif verb == "c":
            _call(league, team, role, st, board, idx)
        elif verb == "i":
            _interview(league, team, role, st, board, idx)
        elif verb == "o":
            offer = _negotiate(league, team, role, st, board, idx)
            if offer is not None:
                c = board[idx][0]
                was = f" from {_current_school(c)}" if _current_school(c) else ""
                league.__dict__.setdefault("career_log", []).append(
                    (league.year, f"Hired {c.name} as {staff.ROLE_NAMES[role]}{was} ({fi.terms(offer, total=False)})."))
                pause()
                return c, offer


def after_hire(league, team, role, c, offer):
    """Make the package real once he's signed: play-calling, the title, the promise."""
    if not offer:
        return
    if offer.get("ahc"):
        c.__dict__["ahc_title"] = True
    if offer.get("hc_out"):
        c.__dict__["hc_out_clause"] = True
    if offer.get("play_calling"):
        side = "off" if role == "OC" else "def"
        staff.set_calls(team, **({"off": role} if side == "off" else {"df": role}))
        c.__dict__["promised_calls"] = (league.year, side)
