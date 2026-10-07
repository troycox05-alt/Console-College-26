"""
ad_market.py — Athletic directors as people, and the market they move in.

Every AD has a style (how he judges a coach, carousel.AD_STYLES), two character
traits, an age, a book of seasons and hires, and a hidden competence nobody sees
directly: it shows in how well he reads a coach's résumé, and over the years in
how his hires turn out. Presidents judge ADs on football and on the coaches they
hired. Bad ones get fired, good ones at small schools get hired away, old ones
retire, and the pool of available ADs (fired ADs, deputies, outsiders) is always
there.

  ensure(league)          older saves and new worlds: every AD gets a full profile
  offseason(league, rng)  the AD year: book the season, retire, fire, fill openings
  eye(team)               0..1, how well this AD reads paper
  fire_shift(team)        how his character moves the seat heat that gets a coach fired
  screen(league)          the AD market screen
"""
import random

from names import full_name

TRAITS = {
    "numbers":     ("Numbers Person", "reads a résumé in context, not by the headline"),
    "headline":    ("Headline Reader", "swayed by rings, last season and a good interview"),
    "alumni":      ("Alumni First", "wants one of the school's own in the job"),
    "network":     ("Old Network", "calls the coaches he already knows"),
    "pincher":     ("Penny Pincher", "won't pay top dollar for anybody"),
    "spender":     ("Big Spender", "will pay whatever it takes, buyouts included"),
    "loyal":       ("Loyal to a Fault", "stands by his coach longer than he should"),
    "trigger":     ("Itchy Trigger", "has the buyout math done by October"),
    "youth":       ("Youth Movement", "wants the next young star, not the last one"),
    "oldschool":   ("Old School", "wants a head coach who has done it before"),
    "coordinators": ("Coordinator Scout", "loves a hot coordinator for a first head job"),
    "local":       ("Regional Ties", "hires coaches who know the area"),
    "gambler":     ("Gambler", "takes big swings on unknowns"),
    "steady":      ("Steady Hand", "careful, thorough searches"),
    "fundraiser":  ("Fundraiser", "the boosters love him, and that buys him time"),
    "politician":  ("Campus Politician", "very hard for a president to fire"),
}
TRAIT_W = {"numbers": 8, "headline": 9, "alumni": 6, "network": 7, "pincher": 6, "spender": 5, "loyal": 6,
           "trigger": 6, "youth": 6, "oldschool": 7, "coordinators": 6, "local": 6, "gambler": 5, "steady": 7,
           "fundraiser": 7, "politician": 5}
CLASH = {("numbers", "headline"), ("pincher", "spender"), ("loyal", "trigger"), ("youth", "oldschool"),
         ("gambler", "steady")}
KINDS = ("deputy", "outsider", "former_coach", "small_school")


def _traits(rng):
    keys, w = list(TRAIT_W), list(TRAIT_W.values())
    a = rng.choices(keys, weights=w)[0]
    while True:
        b = rng.choices(keys, weights=w)[0]
        if b != a and (a, b) not in CLASH and (b, a) not in CLASH:
            return [a, b]


def _style(rng):
    import carousel as cz
    return rng.choices(list(cz.AD_WEIGHTS), weights=list(cz.AD_WEIGHTS.values()))[0]


def make_ad(rng, kind=None, origin=None, comp=None, age=None, style=None, name=None):
    """A brand-new AD profile (not yet at a school)."""
    kind = kind or rng.choice(KINDS)
    comp = comp if comp is not None else rng.gauss(62, 14)
    return {"name": name or full_name(rng), "style": style or _style(rng), "inherited": False, "since": None,
            "age": int(age if age is not None else max(34, min(68, rng.gauss(50, 7)))),
            "comp": int(max(25, min(95, round(comp)))), "traits": _traits(rng),
            "retire_age": int(max(60, min(78, rng.gauss(68, 4)))), "kind": kind,
            "origin": origin or "", "book": [], "hires": [], "past": [], "out_since": None}


def ad_of(team):
    return getattr(team, "ad", None) or {}


def _is_user(league, team):
    import ad_mode
    return ad_mode.is_mine(league, team) or bool(ad_of(team).get("user"))


def eye(team):
    """0..1: how well this AD reads a résumé."""
    ad = ad_of(team)
    comp = ad.get("comp", team.ratings.get("athletic_director", 65))
    v = (comp - 25) / 70
    tr = ad.get("traits", ())
    v += 0.15 if "numbers" in tr else 0
    v -= 0.12 if "headline" in tr else 0
    return max(0.0, min(1.0, v))


def fire_shift(team):
    tr = ad_of(team).get("traits", ())
    return (6 if "loyal" in tr else 0) - (6 if "trigger" in tr else 0)


def pay_mult(team):
    tr = ad_of(team).get("traits", ())
    return 0.85 if "pincher" in tr else 1.18 if "spender" in tr else 1.0


def taste(team, coach, league):
    """His character, applied to one candidate. Résumé only."""
    import carousel as cz
    ad = ad_of(team)
    tr = ad.get("traits", ())
    b = 0.0
    hist = getattr(coach, "history", []) or []
    if "alumni" in tr and getattr(coach, "alma_mater", None) == team.school:
        b += 7
    if "network" in tr:
        mine = {h["coach"] for h in ad.get("hires", [])} | {p["school"] for p in ad.get("past", [])}
        last = hist[-1]["school"] if hist else (coach.team.school if coach.team is not None else None)
        if coach.name in mine or last in mine:
            b += 6
    if "youth" in tr:
        b += max(0, 45 - coach.age) * 0.6 - max(0, coach.age - 52) * 0.5
    if "oldschool" in tr:
        b += min(6, len(hist)) * 1.0 - (5 if not hist else 0)
    if "coordinators" in tr and getattr(coach, "role", "HC") in ("OC", "DC"):
        b += 5
    if "local" in tr and coach.team is not None and cz.region_of(coach.team) == cz.region_of(team):
        b += 4
    if "gambler" in tr and not hist:
        b += 3
    return b


# ── The book ────────────────────────────────────────────────────────────────

def _season(league, team):
    s = getattr(team, "_season_line", None)
    if s and s.get("year") == league.year:
        return {"year": league.year, "school": team.school, "w": s["w"], "l": s["l"], "exp": s.get("exp", 0.5),
                "title": bool(s.get("title")), "cfp": bool(s.get("cfp"))}
    return {"year": league.year, "school": team.school, "w": team.wins, "l": team.losses, "exp": 0.5,
            "title": False, "cfp": False}


def hire_grade(league, h):
    """How a hire he made turned out, -1..1, or None while it's too early to tell."""
    c = h.get("_c")
    seasons = [s for s in getattr(c, "history", []) if s["school"] == h["school"] and s["year"] >= h["year"]] \
        if c is not None else []
    if not seasons:
        return None
    w = sum(s["w"] for s in seasons)
    g = w + sum(s["l"] for s in seasons)
    vs = (w / g if g else 0.5) - sum(s.get("exp", 0.5) for s in seasons) / len(seasons)
    vs += 0.1 * sum(1 for s in seasons if s.get("title")) + 0.03 * sum(1 for s in seasons if s.get("cfp"))
    gone = c.team is None or c.team.school != h["school"]
    if gone and len(seasons) <= 3 and vs < 0:
        return -1.0                                     # fired inside three years
    if len(seasons) < 2:
        return None
    return max(-1.0, min(1.0, vs * 5))


def ad_rep(league, ad):
    """The public read on an AD, 40-95: football under him, and how his hires went."""
    book = ad.get("book", [])[-8:]
    base = {"deputy": 58, "outsider": 55, "former_coach": 57, "small_school": 60}.get(ad.get("kind"), 58)
    if not book and not ad.get("hires"):
        return float(base)
    vs = [(b["w"] / (b["w"] + b["l"]) if b["w"] + b["l"] else 0.5) - b["exp"] for b in book]
    n = len(vs)
    perf = (sum(vs) / n) * (n / (n + 2)) if n else 0.0
    rings = sum(3 * b["title"] + 0.8 * b["cfp"] for b in book)
    grades = [g for g in (hire_grade(league, h) for h in ad.get("hires", [])[-4:]) if g is not None]
    hires = sum(grades) * 3
    level = max([b.get("prestige", 60) for b in book] or [60])
    return max(40.0, min(95.0, base + perf * 60 + min(8, rings) + hires + (level - 60) * 0.1))


# ── Setup ───────────────────────────────────────────────────────────────────

def fill(ad, team, seed):
    """Give an existing (old-style) AD the full profile."""
    r = random.Random(f"admkt:{seed}")
    ad.setdefault("comp", int(max(25, min(95, round(team.ratings.get("athletic_director", 65) + r.gauss(-4, 11))))))
    ad.setdefault("age", int(max(36, min(68, r.gauss(53, 7)))))
    ad.setdefault("traits", _traits(r))
    ad.setdefault("retire_age", int(max(60, min(78, r.gauss(68, 4)))))
    ad.setdefault("kind", r.choice(KINDS))
    ad.setdefault("origin", "")
    ad.setdefault("book", [])
    ad.setdefault("hires", [])
    ad.setdefault("past", [])
    ad.setdefault("since", 2026)
    team.ratings["athletic_director"] = ad["comp"]


def _fresh(league, rng, kind=None):
    kind = kind or rng.choices(KINDS, weights=(5, 2, 2, 3))[0]
    teams = [t for t in league.teams if not getattr(t, "fcs", False)]
    if kind == "deputy":
        src = rng.choice(teams)
        origin = f"deputy AD at {src.school}"
        comp = rng.gauss(60 + (src.prestige - 60) * 0.15, 13)
        age = rng.gauss(44, 6)
    elif kind == "outsider":
        origin = rng.choice(("business executive", "pro sports front office", "conference office", "bank president",
                             "TV network executive"))
        comp = rng.gauss(58, 17)
        age = rng.gauss(50, 7)
    elif kind == "former_coach":
        origin = "former college head coach"
        comp = rng.gauss(56, 14)
        age = rng.gauss(58, 5)
    else:
        fcs = getattr(league, "fcs_teams", None) or []
        origin = f"AD at {rng.choice(fcs).school}" if fcs else "Division II AD"
        comp = rng.gauss(61, 12)
        age = rng.gauss(47, 6)
    return make_ad(rng, kind=kind, origin=origin, comp=comp, age=age)


def ensure(league):
    for t in league.teams:
        if getattr(t, "ad", None) is None:
            continue
        if "comp" not in t.ad and not t.ad.get("user"):
            fill(t.ad, t, t.school)
    if not isinstance(league.__dict__.get("ad_pool"), list):
        rng = random.Random(f"adpool:{league.year}")
        league.ad_pool = [_fresh(league, rng) for _ in range(12)]
        for a in league.ad_pool:
            a["out_since"] = league.year
    league.__dict__.setdefault("ad_moves", [])


# ── The AD year ─────────────────────────────────────────────────────────────

def _move(league, text, kind):
    import carousel as cz
    cz._news(league, "ad", text)
    league.ad_moves.insert(0, (league.year, kind, text))
    del league.ad_moves[300:]


def note_hire(league, team, coach):
    """carousel.hire calls this: the hire goes in the AD's book."""
    ad = ad_of(team)
    if not ad or ad.get("user"):
        return
    ad.setdefault("hires", []).append({"year": league.year + 1, "coach": coach.name, "school": team.school,
                                       "_c": coach})
    del ad["hires"][:-10]


def _job_heat(league, team):
    """How the president feels about his AD, -1 (gone) .. +1."""
    ad = team.ad
    mine = [b for b in ad.get("book", []) if b["school"] == team.school][-4:]
    if len(mine) < 3:
        return 0.3
    vs = sum((b["w"] / (b["w"] + b["l"]) if b["w"] + b["l"] else 0.5) - b["exp"] for b in mine) / len(mine)
    grades = [g for g in (hire_grade(league, h) for h in ad.get("hires", []) if h["school"] == team.school)
              if g is not None]
    v = vs * 4 + (sum(grades) / len(grades) * 0.5 if grades else 0)
    v += 0.4 * sum(1 for b in mine if b["title"]) + 0.1 * sum(1 for b in mine if b["cfp"])
    tr = ad.get("traits", ())
    v += 0.25 if "fundraiser" in tr else 0
    v += 0.35 if "politician" in tr else 0
    return v


def offseason(league, rng):
    """Replaces the old 7% coin flip: ADs are judged, retire, move and get hired."""
    ensure(league)
    openings = []
    for team in league.teams:
        if getattr(team, "ad", None) is None or _is_user(league, team):
            continue
        ad = team.ad
        b = _season(league, team)
        b["prestige"] = team.prestige
        ad.setdefault("book", []).append(b)
        del ad["book"][:-14]
        ad["age"] = ad.get("age", 55) + 1
        tenure = league.year - (ad.get("since") or league.year) + 1
        if ad["age"] >= ad.get("retire_age", 68) and rng.random() < 0.6:
            _move(league, f"{team.school} AD {ad['name']} retires at {ad['age']} after {tenure} years", "retired")
            openings.append(team)
            continue
        heat = _job_heat(league, team)
        odds = 0.012 + max(0.0, -heat - 0.1) * 0.35        # a bad year or two is survivable; a bad run isn't
        if tenure >= 3 and rng.random() < min(0.4, odds):
            ad["past"].append({"school": team.school, "from": ad.get("since"), "to": league.year, "why": "fired"})
            ad["out_since"] = league.year
            league.ad_pool.append(ad)
            _move(league, f"{team.school} fires AD {ad['name']} after {tenure} years", "fired")
            openings.append(team)
    for a in league.ad_pool:
        if a.get("out_since") != league.year:
            a["age"] = a.get("age", 55) + 1
    league.ad_pool = [a for a in league.ad_pool if a.get("age", 55) < 71 and
                      league.year - (a.get("out_since") or league.year) <= 4]
    for _ in range(rng.randint(3, 6)):
        league.ad_pool.append(dict(_fresh(league, rng), out_since=league.year))
    _fill(league, rng, openings)          # a good AD at a smaller school can be hired away: his job opens too


def _fill(league, rng, openings):
    import carousel as cz
    done = set()
    for _ in range(200):
        open_ = sorted((t for t in openings if t.school not in done), key=lambda t: -t.prestige)
        if not open_:
            return
        team = open_[0]
        done.add(team.school)
        sitting = [t for t in league.teams if getattr(t, "ad", None) and not _is_user(league, t)
                   and t not in openings and t.prestige <= team.prestige - 8
                   and league.year - (t.ad.get("since") or league.year) + 1 >= 3]
        cands = [(ad_rep(league, a) + rng.gauss(0, 6), a, None) for a in league.ad_pool]
        cands += [(ad_rep(league, t.ad) + 3 + rng.gauss(0, 6), t.ad, t) for t in sitting]
        cands.sort(key=lambda x: -x[0])
        pick = None
        for _sc, a, src in cands[:8]:
            if src is not None and rng.random() < 0.45:
                continue                                  # happy where he is
            pick = (a, src)
            break
        if pick is None:
            pick = (dict(_fresh(league, rng), out_since=league.year), None)
        a, src = pick
        if src is not None:
            a["past"].append({"school": src.school, "from": a.get("since"), "to": league.year, "why": "left"})
            openings.append(src)
            src.ad = {"name": "(open)", "style": a["style"], "inherited": True, "since": league.year + 1,
                      "comp": 50, "traits": [], "book": [], "hires": [], "past": []}
            where = f"from {src.school}"
        else:
            if a in league.ad_pool:
                league.ad_pool.remove(a)
            where = f"({a.get('origin') or 'out of work'})" if not a.get("past") else \
                f"(formerly {a['past'][-1]['school']})"
        a["since"] = league.year + 1
        a["inherited"] = True
        a["out_since"] = None
        team.ad = a
        team.ratings["athletic_director"] = a["comp"]
        _move(league, f"{team.school} hires {a['name']} as AD {where} — "
                      f"{cz.AD_STYLES[a['style']][0]}, {' & '.join(TRAITS[x][0] for x in a.get('traits', []))}", "hired")
        cz.assign_goals(team, league, rng)
        team.goals_set = league.year + 1


# ── Screens ─────────────────────────────────────────────────────────────────

def traits_label(ad):
    return " · ".join(TRAITS[x][0] for x in ad.get("traits", []) if x in TRAITS)


def _record(ad, school=None):
    book = [b for b in ad.get("book", []) if school is None or b["school"] == school]
    return f"{sum(b['w'] for b in book)}-{sum(b['l'] for b in book)}" if book else "—"


def profile(league, ad, team=None):
    import carousel as cz
    from ui import C, clear, pad, paint, pause, title_bar
    clear()
    where = team.school if team is not None else "available"
    print(title_bar(f"ATHLETIC DIRECTOR · {ad['name'].upper()}", sub=where.upper()))
    print()
    style = cz.AD_STYLES.get(ad.get("style"), ("?", ""))
    print(f"   {paint(ad['name'], C.BWHITE, C.BOLD)}, {ad.get('age', '?')}   ·   {style[0]} — {paint(style[1], C.GRAY)}")
    for x in ad.get("traits", []):
        if x in TRAITS:
            print(f"   {paint(pad(TRAITS[x][0], 20), C.BYELLOW)}{paint(TRAITS[x][1], C.GRAY)}")
    import resume
    rep = ad_rep(league, ad)
    print(paint(f"\n   Reputation {resume.letter(rep)}   ·   came up as: {ad.get('origin') or ad.get('kind', '—')}", C.GRAY))
    if team is not None and ad.get("since"):
        print(paint(f"   AD at {team.school} since {ad['since']}  ·  football under him {_record(ad, team.school)}", C.GRAY))
    if ad.get("past"):
        print(paint("\n   EARLIER JOBS", C.BCYAN, C.BOLD))
        for p in ad["past"][-6:]:
            print(f"   {pad(p['school'], 22)}{p.get('from') or '?'}–{p['to']}   {_record(ad, p['school']):>7}   {p['why']}")
    if ad.get("hires"):
        print(paint("\n   COACHES HE HIRED", C.BCYAN, C.BOLD))
        for h in ad["hires"][-8:]:
            g = hire_grade(league, h)
            verdict = "too early" if g is None else "a hit" if g >= 0.4 else "a miss" if g <= -0.4 else "so-so"
            col = C.GRAY if g is None else C.BGREEN if g >= 0.4 else C.BRED if g <= -0.4 else C.BYELLOW
            print(f"   {h['year']}  {pad(h['coach'], 24)}{pad(h['school'], 20)}{paint(verdict, col)}")
    pause()


def screen(league):
    import carousel as cz
    import resume
    from ui import C, ask, clear, pad, paint, title_bar, truncate
    ensure(league)
    page = "1"
    while True:
        clear()
        print(title_bar("ATHLETIC DIRECTORS", sub=str(league.year)))
        print(paint("   [E] Every AD   [A] Available   [M] Moves   ·   [#] open a profile   [B] back\n", C.GRAY))
        rows = []
        if page == "1":
            teams = sorted((t for t in league.teams if getattr(t, "ad", None) and not getattr(t, "fcs", False)),
                           key=lambda t: -t.prestige)
            print(paint(f"   {'#':>3}  {'SCHOOL':<18}{'AD':<22}{'AGE':>4}  {'STYLE':<17}{'SINCE':>6}  {'REP':<4} TRAITS",
                        C.GRAY, C.BOLD))
            for i, t in enumerate(teams, 1):
                a = t.ad
                rows.append((a, t))
                rep = "you" if a.get("user") else resume.letter(ad_rep(league, a))
                print(f"   {i:>3}  {pad(truncate(t.school, 17), 18)}{pad(truncate(a['name'], 21), 22)}{a.get('age', ''):>4}  "
                      f"{pad(truncate(cz.AD_STYLES[a['style']][0], 16), 17)}{a.get('since') or '':>6}  {pad(rep, 4)} "
                      f"{paint(truncate(traits_label(a), 34), C.GRAY)}")
        elif page == "2":
            pool = sorted(league.ad_pool, key=lambda a: -ad_rep(league, a))
            print(paint(f"   {'#':>3}  {'AD':<22}{'AGE':>4}  {'STYLE':<17}{'REP':<5}{'BACKGROUND':<30}", C.GRAY, C.BOLD))
            for i, a in enumerate(pool, 1):
                rows.append((a, None))
                bg = f"fired at {a['past'][-1]['school']}" if a.get("past") else a.get("origin", "")
                print(f"   {i:>3}  {pad(truncate(a['name'], 21), 22)}{a.get('age', ''):>4}  "
                      f"{pad(truncate(cz.AD_STYLES[a['style']][0], 16), 17)}{pad(resume.letter(ad_rep(league, a)), 5)}"
                      f"{paint(truncate(bg, 30), C.GRAY)}")
        else:
            moves = league.ad_moves[:40]
            if not moves:
                print(paint("   No AD moves yet — they happen after the season.", C.GRAY))
            for yr, kind, text in moves:
                col = C.BRED if kind == "fired" else C.BGREEN if kind == "hired" else C.BYELLOW
                print(f"   {yr}  {paint(pad(kind, 8), col)}{truncate(text, 92)}")
        c = ask("Select:").strip().lower()
        if c in ("b", "", "q"):
            return
        if c in ("e", "a", "m"):
            page = {"e": "1", "a": "2", "m": "3"}[c]
            continue
        if c.isdigit() and 1 <= int(c) <= len(rows):
            a, t = rows[int(c) - 1]
            profile(league, a, t)
