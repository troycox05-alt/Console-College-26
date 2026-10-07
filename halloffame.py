"""
halloffame.py — The College Football Hall of Fame, and every program's own.

THE NATIONAL HALL
  Players are eligible HOF_WAIT seasons after their last college season; coaches once
  they've been out of a head-coaching job that long (or retired), with enough seasons
  on the books (records are kept from 2026). Every offseason a ballot goes to a panel
  of VOTERS writers and former coaches. Each has a lean (stat sheets, winners, awards,
  his own part of the country) and votes for up to VOTES_PER_BALLOT players and COACH_VOTES
  coaches (two categories, like the real Hall). 75% gets you
  in; a class is capped at MAX_PLAYERS players and MAX_COACHES coaches (highest share
  first). Under DROP_PCT, or BALLOT_YEARS on the ballot, and you're off it for good.
  A few voters retire every year; their replacements have their own leans.

PROGRAM HALLS
  Each school inducts its own greats every offseason, judged on what they did there:
  up to PROGRAM_CLASS names. National inductees go into their main school's hall too.
  Your school (Coach Career, AD mode): the committee brings you its nominees and you
  make the selections (hall hub -> [S], or the offseason report). Leave it and the
  committee's recommendations go in when Week 1 kicks off.

    league.hall = Hall
      .inducted   [entry]                 national inductees, every class
      .classes    {year: {...}}           each year's ballot and vote
      .ballot     {key: years on ballot}
      .dropped    set of keys
      .program    {school: [entry]}
      .pending    {school: {"year", "nominees", "picks"}}   your selections, waiting
      .voters     [{"name", "lean", "since"}]
"""
import random
import textwrap
from collections import Counter

import records
from ui import (C, ask, back_key, clear, footer, key, menu_item, pad, paint, pause, section, title_bar,
                truncate)

HOF_WAIT = 2
BALLOT_YEARS = 8
DROP_PCT = 5
THRESHOLD = 75
MAX_PLAYERS = 6
MAX_COACHES = 2
VOTERS = 20
VOTES_PER_BALLOT = 8          # players
COACH_VOTES = 2               # coaches, a separate category
BALLOT_SIZE = 24
BALLOT_FLOOR = 38             # worthiness to reach the ballot at all
PROGRAM_CLASS = 3             # most a program inducts in a year (you pick up to this many)
PROGRAM_AI_CLASS = 2          # other programs' committees are pickier
PROGRAM_FLOOR = 32            # to be nominated
PROGRAM_PICK = 50             # the committee recommends at this case
COACH_MIN_SEASONS = 6

HONOR_POINTS = {"Golden Helmet": 45, "First-team All-American": 16, "Second-team All-American": 6,
                "Freshman of the Year": 4}
AWARD_POINTS = 18             # any positional award (Maxwell, Butkus-style trophies)

# What an elite college career looks like here (about the national career top five).
BENCH = {"pass_yds": 11000, "pass_td": 95, "rush_yds": 4600, "rush_td": 52, "rec": 250, "rec_yds": 3900,
         "rec_td": 36, "scrim": 5600, "total_td": 56, "tackles": 380, "sack": 30, "tfl": 52, "int": 16,
         "fg_made": 72}
POS_KEYS = {"QB": ("pass_yds", "pass_td", "rush_yds"), "RB": ("rush_yds", "rush_td", "scrim", "total_td"),
            "WR": ("rec_yds", "rec", "rec_td"), "TE": ("rec_yds", "rec", "rec_td"),
            "DL": ("sack", "tfl", "tackles"), "LB": ("tackles", "tfl", "sack", "int"),
            "CB": ("int", "tackles"), "S": ("int", "tackles"), "K": ("fg_made",), "P": ()}

LEANS = {
    "stats": ("the numbers guy", "Reads the career line and nothing else."),
    "winners": ("wants rings", "Titles and big seasons first."),
    "honors": ("award voter", "If the country didn't honor him then, why now?"),
    "trenches": ("line guy", "Somebody has to vote for linemen and defenders."),
    "regional": ("regional", "Never met a player from his part of the country he didn't like."),
    "old_school": ("old school", "A small Hall is a great Hall. Votes for few."),
}
LEAN_WEIGHTS = {"stats": 5, "winners": 4, "honors": 4, "trenches": 2, "regional": 3, "old_school": 2}
OUTLETS = ("The Gridiron Ledger", "the wire service", "the network", "The Tribune", "the Evening Dispatch", "Saturday Weekly",
           "the Herald", "the Gazette", "a radio booth", "the Chronicle", "retired head coach", "the Courier")
REGIONS = {"SCC": "South", "Seaboard": "East", "Continental": "Midwest", "Meridian": "Plains", "Golden West": "West",
           "Federal": "South", "High Country": "West", "Coastal Plains": "South", "Lake Country": "Midwest",
           "Crossroads": "South", "Independent": "East"}


class Hall:
    def __init__(self):
        self.inducted = []
        self.classes = {}
        self.ballot = {}
        self.dropped = set()
        self.program = {}
        self.pending = {}
        self.voters = []
        self.seen_class = None


def hall(league):
    h = league.__dict__.get("hall")
    if h is None:
        h = league.hall = Hall()
    if not h.voters:
        rng = random.Random(f"voters:{league.seed}")
        h.voters = [_new_voter(rng, league.year) for _ in range(VOTERS)]
    return h


def _new_voter(rng, year):
    from names import full_name
    keys, w = zip(*LEAN_WEIGHTS.items())
    lean = rng.choices(keys, weights=w)[0]
    return {"name": full_name(rng), "lean": lean, "since": year, "outlet": rng.choice(OUTLETS),
            "region": rng.choice(sorted(set(REGIONS.values())))}


# ═══ Candidates ══════════════════════════════════════════════════════════════

def _school_of(f):
    c = Counter()
    for yr in f["years"].values():
        c[yr["school"]] += 1
    return c.most_common(1)[0][0] if c else ""


def production(tot, pos):
    """0-60: how close his career line came to an elite one, at his position."""
    d = records.derive(tot)
    keys = POS_KEYS.get(pos) or tuple(BENCH)
    parts = sorted((min(1.6, d.get(k, 0) / BENCH[k]) for k in keys if k in BENCH), reverse=True)
    if not parts:
        return 0.0
    return 30 * parts[0] + 15 * (parts[1] if len(parts) > 1 else 0) + 5 * (parts[2] if len(parts) > 2 else 0)


def honors_points(honors):
    pts = 0
    for _, h in honors:
        pts += HONOR_POINTS.get(h, AWARD_POINTS if h not in HONOR_POINTS else 0)
    return pts


def player_worth(league, f, school=None):
    """Worthiness: honors + production + titles + the draft + records held."""
    tot, games = records.career_totals(f, school)
    hon = [h for h in f.get("honors", [])
           if school is None or f["years"].get(h[0], {}).get("school") == school]
    w = honors_points(hon) + production(tot, f["pos"])
    titles = [t for t in f.get("titles", []) if school is None or t[1] == school]
    w += 6 * len(titles)
    dr = f.get("drafted")
    if dr and (school is None or f["years"].get(dr[0], {}).get("school", _school_of(f)) == (school or _school_of(f))):
        w += 12 if dr[2] <= 10 else 9 if dr[1] == 1 else 5 if dr[1] == 2 else 2 if dr[1] == 3 else 0
    if f["pos"] in ("OL",):
        w += 0.6 * max(0, f.get("peak_ovr", 60) - 70) + (8 if hon else 0)      # linemen: the tape
    held = 0
    tops = records.career_tops(league).get(school or records.NATIONAL, {})
    for k in records.CAREER_KEYS:
        for place, e in enumerate(tops.get(k, [])[:3], 1):
            if e[7] == f["pid"]:
                held += 6 if place == 1 else 2
    return round(w + min(18, held), 1)


def _coach_hist(c):
    return [h for h in (getattr(c, "history", []) or []) if h.get("school")]


def coach_worth(hist):
    if not hist:
        return 0.0
    w = sum(h.get("w", 0) for h in hist)
    l_ = sum(h.get("l", 0) for h in hist)
    pct = w / max(1, w + l_)
    titles = sum(1 for h in hist if h.get("title"))
    confs = sum(1 for h in hist if h.get("conf_champ"))
    cfp = sum(1 for h in hist if h.get("cfp"))
    return round(w * 0.35 + max(0, pct - .5) * 60 + titles * 25 + confs * 5 + cfp * 3, 1)


def _all_coaches(league):
    import carousel
    seen, out = set(), []
    for c in carousel.all_coaches(league) + list(getattr(league, "coach_pool", [])) + \
            list(getattr(league, "retired_coaches", [])):
        if id(c) not in seen:
            seen.add(id(c))
            out.append(c)
    return out


def _coach_eligible(league, c):
    hist = _coach_hist(c)
    if len({h["year"] for h in hist}) < COACH_MIN_SEASONS:
        return False
    import carousel
    if c in carousel.all_coaches(league):
        return False
    last = max(h["year"] for h in hist)
    return getattr(c, "status", "") == "retired" or last <= league.year - HOF_WAIT


def _ckey(c):
    return f"coach:{c.name}"


def _entry_player(league, f, worth, school=None):
    tot, games = records.career_totals(f, school)
    schools = []
    for y in sorted(f["years"]):
        s = f["years"][y]["school"]
        if s not in schools:
            schools.append(s)
    coaches = Counter(yr.get("coach") for yr in f["years"].values() if yr.get("coach"))
    return {"kind": "player", "key": f"p:{f['pid']}", "pid": f["pid"], "name": f["name"], "pos": f["pos"],
            "coach": coaches.most_common(1)[0][0] if coaches else None, "stars": f.get("hs_stars", 3),
            "schools": schools, "years": (f["first"], f["last"]), "games": games,
            "line": summary(tot, f["pos"]), "honors": list(f.get("honors", [])), "drafted": f.get("drafted"),
            "titles": list(f.get("titles", [])), "worth": worth}


def _entry_coach(league, c, worth, school=None):
    hist = _coach_hist(c)
    if school:
        hist = [h for h in hist if h["school"] == school]
    w = sum(h.get("w", 0) for h in hist)
    l_ = sum(h.get("l", 0) for h in hist)
    schools = []
    for h in hist:
        if h["school"] not in schools:
            schools.append(h["school"])
    titles = [h["year"] for h in hist if h.get("title")]
    confs = sum(1 for h in hist if h.get("conf_champ"))
    return {"kind": "coach", "key": _ckey(c), "name": c.name, "pos": "HC", "schools": schools,
            "years": (min(h["year"] for h in hist), max(h["year"] for h in hist)), "games": w + l_,
            "line": f"{w}-{l_} ({w / max(1, w + l_):.3f})" + (f" · {len(titles)} national title"
                                                              f"{'s' if len(titles) != 1 else ''}" if titles else "")
                    + (f" · {confs} conference title{'s' if confs != 1 else ''}" if confs else ""),
            "honors": [(y, "National Champion") for y in titles], "drafted": None, "titles": titles, "worth": worth}


def summary(tot, pos):
    """One line of career numbers, the ones that matter for his position."""
    d = records.derive(tot)
    f = records.fmt
    bits = []
    if d["pass_yds"] >= 500:
        bits.append(f"{f('pass_yds', d['pass_yds'])} pass yds, {d['pass_td']} TD")
    if d["rush_yds"] >= 400:
        bits.append(f"{f('rush_yds', d['rush_yds'])} rush yds, {d['rush_td']} TD")
    if d["rec_yds"] >= 400:
        bits.append(f"{d['rec']} rec, {f('rec_yds', d['rec_yds'])} yds, {d['rec_td']} TD")
    if d["tackles"] >= 60 or pos in ("DL", "LB", "CB", "S"):
        extra = [f"{d['tackles']} tkl"]
        if d["tfl"]:
            extra.append(f"{f('tfl', d['tfl'])} TFL")
        if d["sack"]:
            extra.append(f"{f('sack', d['sack'])} sack{'' if d['sack'] == 1 else 's'}")
        if d["int"]:
            extra.append(f"{d['int']} INT")
        bits.append(", ".join(extra))
    if d["fg_made"]:
        bits.append(f"{d['fg_made']} FG (long {d['fg_long']})")
    if not bits:
        bits.append("the film says it all" if pos == "OL" else "—")
    return " · ".join(bits)


def national_candidates(league):
    h = hall(league)
    b = records.book(league)
    live = records.active_pids(league)
    have = {e["key"] for e in h.inducted}
    out = []
    for f in b.files.values():
        k = f"p:{f['pid']}"
        if k in have or k in h.dropped or f["pid"] in live or f["last"] > league.year - HOF_WAIT:
            continue
        w = player_worth(league, f)
        if w >= BALLOT_FLOOR or k in h.ballot:
            out.append(_entry_player(league, f, w))
    for c in _all_coaches(league):
        k = _ckey(c)
        if k in have or k in h.dropped or not _coach_eligible(league, c):
            continue
        w = coach_worth(_coach_hist(c))
        if w >= BALLOT_FLOOR or k in h.ballot:
            out.append(_entry_coach(league, c, w))
    players = sorted((e for e in out if e["kind"] == "player"), key=lambda e: -e["worth"])[:BALLOT_SIZE]
    coaches = sorted((e for e in out if e["kind"] == "coach"), key=lambda e: -e["worth"])[:6]
    return players + coaches


# ═══ The vote ════════════════════════════════════════════════════════════════

def _region(school, league):
    t = next((t for t in league.teams if t.school == school), None)
    return REGIONS.get(getattr(t, "conference", ""), "South") if t else ""


def _perceived(league, voter, e, rng):
    v = e["worth"]
    lean = voter["lean"]
    if lean == "stats":
        v += 0.25 * (v - honors_points(e["honors"]))
    elif lean == "winners":
        v += 8 * len(e["titles"])
    elif lean == "honors":
        v += 0.3 * honors_points(e["honors"]) - 6
    elif lean == "trenches" and e["pos"] in ("OL", "DL", "LB", "CB", "S"):
        v += 9
    elif lean == "regional" and any(_region(s, league) == voter["region"] for s in e["schools"]):
        v += 10
    elif lean == "old_school":
        v -= 7
    return v + rng.gauss(0, 7)


def run_vote(league):
    h = hall(league)
    y = league.year
    ballot = national_candidates(league)
    rng = random.Random(f"hof:{league.seed}:{y}")
    # Voters come and go.
    for i in rng.sample(range(len(h.voters)), k=min(2, len(h.voters))):
        if y - h.voters[i]["since"] >= 3:
            h.voters[i] = _new_voter(rng, y)
    votes = Counter()
    by_voter = {}
    for v in h.voters:
        cut = 72 if v["lean"] == "old_school" else 66
        picks = []
        for kind, n_votes in (("player", VOTES_PER_BALLOT), ("coach", COACH_VOTES)):   # two categories, like the real one
            want = sorted(((_perceived(league, v, e, rng), e["key"]) for e in ballot if e["kind"] == kind), reverse=True)
            picks += [k for s, k in want[:n_votes] if s >= cut]
        by_voter[v["name"]] = picks
        votes.update(picks)
    n = max(1, len(h.voters))
    rows = []
    for e in ballot:
        e = dict(e)
        e["pct"] = round(100 * votes[e["key"]] / n)
        e["ballot_year"] = h.ballot.get(e["key"], 0) + 1
        rows.append(e)
    rows.sort(key=lambda e: (-e["pct"], -e["worth"]))
    players = [e for e in rows if e["kind"] == "player" and e["pct"] >= THRESHOLD][:MAX_PLAYERS]
    coaches = [e for e in rows if e["kind"] == "coach" and e["pct"] >= THRESHOLD][:MAX_COACHES]
    inducted = {e["key"] for e in players + coaches}
    for e in rows:
        if e["key"] in inducted:
            e["status"] = "inducted"
            h.ballot.pop(e["key"], None)
        elif e["pct"] < DROP_PCT or e["ballot_year"] >= BALLOT_YEARS:
            e["status"] = "dropped"
            h.dropped.add(e["key"])
            h.ballot.pop(e["key"], None)
        else:
            e["status"] = "returns"
            h.ballot[e["key"]] = e["ballot_year"]
    for e in players + coaches:
        e["class"] = y
        e["speech"] = _speech(e, rng)
        h.inducted.append(e)
        home = e["schools"][0] if e["kind"] == "coach" else _main_school(e)
        _program_add(league, home, dict(e, via="national"))
    h.classes[y] = {"players": players, "coaches": coaches, "ballot": rows, "voters": len(h.voters),
                    "by_voter": by_voter}
    return h.classes[y]


def _main_school(e):
    return e["schools"][0] if len(e["schools"]) == 1 else e["schools"][-1] if e.get("games") else e["schools"][0]


SPEECH = [
    "I didn't get here alone. {coach} saw something in me when nobody else did.",
    "Every rep, every 5 a.m. lift — this is for the guys who were in that locker room.",
    "{school} gave a {cls} kid a chance. I've been trying to pay that back ever since.",
    "My mother drove four hours to every home game. Mom, this one's yours.",
    "They say you play for the name on the front. I played for the one on the back of my dad's truck.",
    "I still dream about {year}. I think I always will.",
    "To the fans at {school}: you were louder than anybody. We heard every bit of it.",
]
COACH_SPEECH = [
    "Coaching is a people business. I just had a lot of great people.",
    "I'd trade this for one more fall camp with those kids. Maybe two.",
    "{school} took a chance on me. We built something, and it's still standing.",
    "The wins are nice. The weddings, the phone calls twenty years later — that's the job.",
]


def _speech(e, rng):
    if e["kind"] == "coach":
        return rng.choice(COACH_SPEECH).format(school=e["schools"][0])
    stars = e.get("stars", 3)
    cls = {0: "walk-on", 1: "one-star", 2: "two-star", 3: "three-star", 4: "four-star", 5: "five-star"}.get(stars, "skinny")
    lines = SPEECH if stars <= 3 else [x for x in SPEECH if "{cls}" not in x]
    coach = e.get("coach")
    if not coach:
        lines = [x for x in lines if "{coach}" not in x]
    return rng.choice(lines).format(coach=f"Coach {coach.split()[-1]}" if coach else "", school=_main_school(e),
                                    cls=cls, year=e["years"][1])


# ═══ Program halls ═══════════════════════════════════════════════════════════

def _program_add(league, school, e):
    lst = hall(league).program.setdefault(school, [])
    if not any(x["key"] == e["key"] for x in lst):
        e.setdefault("class", league.year)
        lst.append(e)


def program_nominees(league, school, n=8):
    h = hall(league)
    b = records.book(league)
    live = records.active_pids(league)
    have = {e["key"] for e in h.program.get(school, [])}
    out = []
    for f in b.files.values():
        k = f"p:{f['pid']}"
        if k in have or f["pid"] in live or f["last"] > league.year - HOF_WAIT:
            continue
        seasons_here = sum(1 for yr in f["years"].values() if yr["school"] == school)
        if not seasons_here:
            continue
        w = player_worth(league, f, school=school) + 2 * seasons_here
        if w >= PROGRAM_FLOOR:
            out.append(_entry_player(league, f, w, school=school))
    for c in _all_coaches(league):
        k = _ckey(c)
        if k in have:
            continue
        hist = [x for x in _coach_hist(c) if x["school"] == school]
        seasons = len({x["year"] for x in hist})
        if seasons < 4:
            continue
        import carousel
        if c in carousel.all_coaches(league) and c.team is not None and c.team.school == school:
            continue                                   # still coaching there
        if max(x["year"] for x in hist) > league.year - 1 and getattr(c, "status", "") != "retired" and \
                c in carousel.all_coaches(league):
            continue
        w = coach_worth(hist) + 4
        w_, l_ = sum(x.get("w", 0) for x in hist), sum(x.get("l", 0) for x in hist)
        if w >= PROGRAM_FLOOR and (w_ / max(1, w_ + l_) >= .6 or any(x.get("title") for x in hist)):
            out.append(_entry_coach(league, c, w, school=school))
    out.sort(key=lambda e: -e["worth"])
    return out[:n]


def user_school(league):
    mode = getattr(league, "mode", None)
    if mode == "career" and getattr(league, "user_coach", None) is not None and \
            getattr(league.user_coach, "team", None) is not None:
        return league.user_coach.team.school
    if mode == "ad" and getattr(league, "ad_user", None):
        t = getattr(league, "user_team", None)
        return t.school if t is not None else None
    return None


def program_classes(league):
    """Every school's committee picks its class; yours waits for you."""
    h = hall(league)
    mine = None if getattr(league, "autosim", False) else user_school(league)
    out = {}
    for t in league.teams:
        noms = program_nominees(league, t.school)
        if not noms:
            continue
        if t.school == mine:
            h.pending[t.school] = {"year": league.year, "nominees": noms,
                                   "picks": [e["key"] for e in noms[:PROGRAM_CLASS] if e["worth"] >= PROGRAM_PICK]}
            continue
        picks = [e for e in noms if e["worth"] >= PROGRAM_PICK][:PROGRAM_AI_CLASS]
        for e in picks:
            _program_add(league, t.school, dict(e, via="committee"))
        if picks:
            out[t.school] = picks
    return out


def finalize_pending(league, school=None):
    """Your picks go in (or the committee's, if you never looked)."""
    h = hall(league)
    for s in [school] if school else list(h.pending):
        p = h.pending.pop(s, None)
        if not p:
            continue
        chosen = [e for e in p["nominees"] if e["key"] in p["picks"]]
        for e in chosen:
            _program_add(league, s, dict(e, via="you" if p.get("touched") else "committee", **{"class": p["year"]}))


def offseason(league):
    """run_offseason calls this after the draft."""
    if not getattr(league, "archive", None) and not records.book(league).files:
        return None
    for s in list(hall(league).pending):
        finalize_pending(league, s)            # last year's, if you never got to them
    national = run_vote(league)
    programs = program_classes(league)
    return {"national": national, "programs": programs}


# ═══ Screens ═════════════════════════════════════════════════════════════════

def _honor_line(e, width=90):
    counts = Counter(h for _, h in e["honors"])
    bits = []
    for name in ("Golden Helmet", "First-team All-American", "Second-team All-American"):
        if counts.get(name):
            bits.append(f"{name}" + (f" x{counts[name]}" if counts[name] > 1 else ""))
    for name, n in counts.items():
        if name not in HONOR_POINTS and name != "National Champion":
            bits.append(name + (f" x{n}" if n > 1 else ""))
    if e["titles"]:
        bits.append(f"National champion {', '.join(str(t if isinstance(t, int) else t[0]) for t in e['titles'])}")
    d = e.get("drafted")
    if d:
        bits.append(f"Drafted {d[0]}, round {d[1]} (No. {d[2]})")
    return truncate(" · ".join(bits), width) if bits else ""


def _print_entry(e, show_pct=False, n=None):
    tag = f"{n:>2}. " if n is not None else "    "
    where = " / ".join(e["schools"])
    head = f"{paint(e['name'], C.BWHITE, C.BOLD)} {paint(e['pos'], C.BCYAN)} · {where} · {e['years'][0]}-{e['years'][1]}"
    if show_pct and "pct" in e:
        col = C.BGREEN if e["pct"] >= THRESHOLD else C.BYELLOW if e["pct"] >= 40 else C.GRAY
        head += "  " + paint(f"{e['pct']}%", col, C.BOLD)
        if e.get("ballot_year", 1) > 1:
            head += paint(f" (year {e['ballot_year']} on the ballot)", C.GRAY)
    print(f"  {tag}{head}")
    print(paint(f"        {e['line']}", C.GRAY))
    hl = _honor_line(e)
    if hl:
        print(paint(f"        {hl}", C.BYELLOW))


def hub(league):
    h = hall(league)
    while True:
        clear()
        print(title_bar("HALL OF FAME", sub=f"{len(h.inducted)} INDUCTED"))
        last = max(h.classes) if h.classes else None
        mine = user_school(league)
        print()
        if not h.inducted and last is None:
            print(paint(f"   Records are kept from {records.book(league).since or league.year}. Players become eligible "
                        f"{HOF_WAIT} seasons after their last college game;", C.GRAY))
            print(paint(f"   coaches after {COACH_MIN_SEASONS}+ seasons, once they've stepped away. The first ballot "
                        "goes out when someone qualifies.", C.GRAY))
            print()
        print(menu_item("C", "The latest class", f"Class of {last}" if last else "no class yet"))
        print(menu_item("A", "Every inductee", f"{len(h.inducted)} players and coaches"))
        print(menu_item("V", "The vote", "every name on every ballot, and how the panel voted"))
        print(menu_item("W", "Ballot watch", "who's eligible next, and who's building a case"))
        print(menu_item("P", "Program halls", "every school's own Hall of Fame"))
        if mine:
            pend = h.pending.get(mine)
            print(menu_item("S", f"{mine} selections", paint("waiting for you", C.BMAGENTA) if pend
                            else "done for this year", color=C.BMAGENTA if pend else None))
        print(menu_item("M", "The panel", f"{len(h.voters)} voters and how they lean"))
        footer(back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "c" and last:
            ceremony(league, last)
        elif c == "a":
            all_inductees(league)
        elif c == "v":
            vote_screen(league)
        elif c == "w":
            ballot_watch(league)
        elif c == "p":
            program_screen(league)
        elif c == "s" and mine:
            selection_screen(league, mine)
        elif c == "m":
            panel_screen(league)


def ceremony(league, year):
    h = hall(league)
    k = h.classes.get(year)
    clear()
    print(title_bar(f"HALL OF FAME · CLASS OF {year}", sub="INDUCTION"))
    if not k or not (k["players"] or k["coaches"]):
        print(paint(f"\n   Nobody reached {THRESHOLD}% in {year}. The panel keeps a small Hall.\n", C.GRAY))
        if k and k["ballot"]:
            top = k["ballot"][0]
            print(paint(f"   Closest: {top['name']} ({top['pct']}%).", C.GRAY))
        pause()
        return
    print()
    for e in k["players"] + k["coaches"]:
        _print_entry(e, show_pct=True)
        for ln in textwrap.wrap(f"“{e.get('speech', '')}”", 86):
            print(paint(f"        {ln}", C.BCYAN))
        print()
    h.seen_class = year
    pause()


def all_inductees(league):
    h = hall(league)
    clear()
    print(title_bar("HALL OF FAME · EVERY INDUCTEE", sub=f"{len(h.inducted)}"))
    if not h.inducted:
        print(paint("\n   Nobody yet.\n", C.GRAY))
        pause()
        return
    for y in sorted({e["class"] for e in h.inducted}, reverse=True):
        print(section(f"CLASS OF {y}", C.BYELLOW))
        for e in [e for e in h.inducted if e["class"] == y]:
            _print_entry(e, show_pct=True)
        print()
    pause()


def vote_screen(league):
    h = hall(league)
    years = sorted(h.classes, reverse=True)
    if not years:
        clear()
        print(title_bar("HALL OF FAME · THE VOTE"))
        print(paint("\n   No ballot yet.\n", C.GRAY))
        pause()
        return
    i = 0
    while True:
        y = years[i]
        k = h.classes[y]
        clear()
        print(title_bar(f"HALL OF FAME · {y} BALLOT", sub=f"{k['voters']} VOTERS · {THRESHOLD}% TO GET IN"))
        print()
        for n, e in enumerate(k["ballot"], 1):
            st = {"inducted": paint("IN", C.BGREEN, C.BOLD), "dropped": paint("off", C.GRAY),
                  "returns": paint("back next year", C.GRAY)}[e["status"]]
            name = pad(paint(truncate(e["name"], 24), C.BWHITE), 25)
            where = pad(truncate(" / ".join(e["schools"]), 26), 27)
            pct = paint(f"{e['pct']:>3}%", C.BWHITE, C.BOLD)
            print(f"  {n:>2}. {name}{e['pos']:<4}{where}{pct}  {st}")
        footer(key("<", "earlier") if i < len(years) - 1 else "", key(">", "later") if i else "",
               key("#", "a name's case"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "<" and i < len(years) - 1:
            i += 1
        elif c == ">" and i:
            i -= 1
        elif c.isdigit() and 1 <= int(c) <= len(k["ballot"]):
            e = k["ballot"][int(c) - 1]
            clear()
            print(title_bar(f"{e['name'].upper()} · THE CASE", sub=f"{y} BALLOT"))
            print()
            _print_entry(e, show_pct=True)
            yes = [v for v, picks in k.get("by_voter", {}).items() if e["key"] in picks]
            print()
            print(paint(f"   Voted for him ({len(yes)}): " + (", ".join(yes) if yes else "nobody"), C.GRAY))
            pause()


def ballot_watch(league):
    clear()
    print(title_bar("HALL OF FAME · BALLOT WATCH", sub=f"THE {league.year} OFFSEASON"))
    print(paint(f"\n   Eligible when the season ends: last college game in {league.year - HOF_WAIT} or earlier. "
                "Worthiness is the staff's read, not the vote.\n", C.GRAY))
    cands = national_candidates(league)
    if not cands:
        print(paint("   Nobody eligible has a case yet.\n", C.GRAY))
    for n, e in enumerate(cands[:15], 1):
        _print_entry(e, n=n)
        print(paint(f"        worthiness {e['worth']:.0f}", C.GRAY))
    print(section("STILL PLAYING, BUILDING A CASE", C.BCYAN))
    b = records.book(league)
    live = records.active_pids(league)
    building = sorted(((player_worth(league, f), f) for i, f in b.files.items() if i in live),
                      key=lambda x: -x[0])[:8]
    for w, f in building:
        tot, _ = records.career_totals(f)
        print(f"   {paint(f['name'], C.BWHITE)} {paint(f['pos'], C.BCYAN)} · {_school_of(f)} · "
              f"{paint(summary(tot, f['pos']), C.GRAY)}  {paint(f'{w:.0f}', C.BYELLOW)}")
    print()
    pause()


def program_screen(league, school=None):
    h = hall(league)
    follow = getattr(league, "follow_team", None)
    school = school or user_school(league) or (follow.school if follow is not None else None)
    if school is None:
        from screens import pick_team
        t = pick_team(league)
        if t is None:
            return
        school = t.school
    while True:
        lst = sorted(h.program.get(school, []), key=lambda e: (-e["class"], e["name"]))
        clear()
        print(title_bar(f"{school.upper()} HALL OF FAME", sub=f"{len(lst)} INDUCTED"))
        print()
        if not lst:
            print(paint("   Nobody yet. The program's first class is waiting for someone to earn it.\n", C.GRAY))
        cur = None
        for e in lst:
            if e["class"] != cur:
                cur = e["class"]
                print(section(f"CLASS OF {cur}", C.BYELLOW))
            _print_entry(e)
            if e.get("via") == "national":
                print(paint("        also in the College Football Hall of Fame", C.BGREEN))
        footer(key("O", "another school"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "o":
            from screens import pick_team
            t = pick_team(league)
            if t is not None:
                school = t.school


def selection_screen(league, school):
    h = hall(league)
    while True:
        p = h.pending.get(school)
        clear()
        print(title_bar(f"{school.upper()} HALL OF FAME · SELECTIONS", sub=f"CLASS OF {p['year'] if p else league.year}"))
        if not p:
            print(paint("\n   This year's class is in. The committee meets again after next season.\n", C.GRAY))
            pause()
            return
        print(paint(f"\n   The committee's nominees, strongest case first. Pick up to {PROGRAM_CLASS}. "
                    "Anyone you pass on can be nominated again.\n", C.GRAY))
        for n, e in enumerate(p["nominees"], 1):
            mark = paint("[x]", C.BGREEN, C.BOLD) if e["key"] in p["picks"] else paint("[ ]", C.GRAY)
            print(f"  {mark}", end="")
            _print_entry(e, n=n)
            rec = "committee recommends" if e["worth"] >= PROGRAM_PICK else "borderline"
            print(paint(f"        case {e['worth']:.0f} · {rec}", C.GRAY))
        footer(key("#", "select / unselect"), key("D", "done: induct them", C.BGREEN), back_key("Later"))
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c.isdigit() and 1 <= int(c) <= len(p["nominees"]):
            k = p["nominees"][int(c) - 1]["key"]
            p["touched"] = True
            if k in p["picks"]:
                p["picks"].remove(k)
            elif len(p["picks"]) < PROGRAM_CLASS:
                p["picks"].append(k)
        elif c == "d":
            p["touched"] = True
            n = len(p["picks"])
            finalize_pending(league, school)
            print(paint(f"\n   {n} inducted into the {school} Hall of Fame." if n else
                        "\n   No class this year. The committee will be back.", C.BGREEN))
            pause()
            return


def panel_screen(league):
    h = hall(league)
    clear()
    print(title_bar("HALL OF FAME · THE PANEL", sub=f"{len(h.voters)} VOTERS"))
    print()
    for v in sorted(h.voters, key=lambda v: v["since"]):
        lean, blurb = LEANS[v["lean"]]
        extra = f" ({v['region']})" if v["lean"] == "regional" else ""
        print(f"   {pad(paint(v['name'], C.BWHITE), 26)}{pad(paint(v['outlet'], C.GRAY), 28)}"
              f"{pad(paint(lean + extra, C.BCYAN), 22)}{paint('since ' + str(v['since']), C.GRAY)}")
    print(paint(f"\n   Each votes for up to {VOTES_PER_BALLOT} players and {COACH_VOTES} coaches. "
                f"{THRESHOLD}% gets you in.\n", C.GRAY))
    pause()


def report_lines(league, hall_report):
    """For the offseason report: the class, and your selections."""
    out = []
    if not hall_report:
        return out
    nat = hall_report.get("national") or {}
    names = [f"{e['name']} ({e['pos']}, {_main_school(e)})" for e in nat.get("players", []) + nat.get("coaches", [])]
    if names:
        out.append((C.BYELLOW, f"Hall of Fame, Class of {league.year - 1 if league.week == 0 else league.year}: "
                               + ", ".join(names)))
    elif nat.get("ballot"):
        top = nat["ballot"][0]
        out.append((C.GRAY, f"Hall of Fame: nobody reached {THRESHOLD}%. Closest: {top['name']} ({top['pct']}%)"))
    mine = user_school(league)
    if mine and mine in hall(league).pending:
        out.append((C.BMAGENTA, f"The {mine} Hall of Fame committee has nominees. Make your selections: "
                                "Rankings tab -> [F] -> [S]"))
    return out


def migrate(league):
    hall(league)
