"""
records.py — The record book: every record set from 2026 on, national and school by school.

    league.record_book = RecordBook
      .game[scope][key]    single-game player records     scope: "FBS" or a school name
      .season[scope][key]  single-season player records
      .team_game[scope][k] team single-game records (points, yards, margin...)
      .team_season[scope][k] team single-season records (wins, points, defense...)
      .streaks             current winning streaks; the longest are team records
      .files[pid]          career files: one per notable player, kept after he leaves
                           (the Hall of Fame reads these; see halloffame.py)

Career records (national and school) are added up from the career files plus the
current season of anyone still playing, so a senior chasing the career rushing
record climbs the board week by week. Coach records come from the coaches' own
books (carousel: coach.history), so they are tracked from 2026 like everything else.

Updated after every game (season.simulate_game -> after_game) and every offseason
(season.run_offseason -> close_season, then after_awards). A new national or school
record makes the headlines.
"""
from collections import Counter

# (key, label, how to read the line, format). "max" stats are single-play longs.
PLAYER_STATS = [
    ("pass_yds", "Passing yards", "sum"),
    ("pass_td", "Passing touchdowns", "sum"),
    ("pass_cmp", "Completions", "sum"),
    ("rush_yds", "Rushing yards", "sum"),
    ("rush_td", "Rushing touchdowns", "sum"),
    ("rec", "Receptions", "sum"),
    ("rec_yds", "Receiving yards", "sum"),
    ("rec_td", "Receiving touchdowns", "sum"),
    ("scrim", "Yards from scrimmage", "sum"),
    ("total_td", "Total touchdowns", "sum"),
    ("tackles", "Tackles", "sum"),
    ("tfl", "Tackles for loss", "sum"),
    ("sack", "Sacks", "sum"),
    ("int", "Interceptions", "sum"),
    ("fg_made", "Field goals made", "sum"),
    ("ret_yds", "Return yards", "sum"),
    ("rush_long", "Longest run", "max"),
    ("rec_long", "Longest reception", "max"),
    ("fg_long", "Longest field goal", "max"),
]
LABEL = {k: lab for k, lab, _ in PLAYER_STATS}
KIND = {k: kind for k, _, kind in PLAYER_STATS}
GROUPS = [("PASSING", ("pass_yds", "pass_td", "pass_cmp")),
          ("RUSHING", ("rush_yds", "rush_td", "rush_long")),
          ("RECEIVING", ("rec", "rec_yds", "rec_td", "rec_long")),
          ("ALL-PURPOSE", ("scrim", "total_td", "ret_yds")),
          ("DEFENSE", ("tackles", "tfl", "sack", "int")),
          ("KICKING", ("fg_made", "fg_long"))]
# Longs don't make a career board; a career is added up.
CAREER_KEYS = [k for k, _, kind in PLAYER_STATS if kind == "sum"]

TEAM_GAME = [("points", "Points in a game"), ("margin", "Margin of victory"), ("total_yds", "Total yards"),
             ("rush_yds", "Rushing yards"), ("pass_yds", "Passing yards"), ("combined", "Combined points (both teams)")]
TEAM_SEASON = [("wins", "Wins"), ("points", "Points scored"), ("ppg", "Points per game"),
               ("fewest_ppg", "Fewest points allowed per game"), ("diff", "Point differential"),
               ("streak", "Longest winning streak")]
TEAM_GAME_LABEL = dict(TEAM_GAME)
TEAM_SEASON_LABEL = dict(TEAM_SEASON)
LOWER_IS_BETTER = {"fewest_ppg"}

NATIONAL = "FBS"
KEEP = {NATIONAL: 10}           # entries kept per board
KEEP_SCHOOL_GAME = 3
KEEP_SCHOOL_SEASON = 5
MIN_GAME = {"pass_yds": 250, "rush_yds": 120, "rec_yds": 120, "scrim": 150, "pass_td": 3, "rush_td": 2, "rec_td": 2,
            "total_td": 2, "rec": 8, "pass_cmp": 20, "tackles": 8, "sack": 1, "tfl": 2, "int": 1, "fg_made": 2,
            "ret_yds": 80, "rush_long": 40, "rec_long": 40, "fg_long": 45}
PPG_MIN_GAMES = 10
# A record only makes the news when it's remarkable on its own (the board starts empty in 2026).
NEWS_MIN = {"pass_yds": 460, "rush_yds": 260, "rec_yds": 230, "scrim": 320, "pass_td": 6, "rush_td": 5, "rec_td": 4,
            "total_td": 5, "rec": 15, "pass_cmp": 38, "tackles": 18, "sack": 4, "tfl": 5, "int": 3, "fg_made": 5,
            "ret_yds": 260, "rush_long": 92, "rec_long": 92, "fg_long": 57}
TEAM_NEWS_MIN = {"points": 70, "margin": 63}
# Season marks worth a headline when passed: the stat, and how big the old record has to be.
SEASON_NEWS = {"pass_yds": 4200, "pass_td": 42, "rush_yds": 1900, "rush_td": 24, "rec_yds": 1500, "rec": 115,
               "total_td": 26, "tackles": 150, "sack": 16, "int": 8, "scrim": 2300}
SCHOOL_SEASON_NEWS = {k: v * 0.72 for k, v in SEASON_NEWS.items()}

# A career file is kept for good only if the player did enough to be remembered.
KEEP_FILE = {"pass_yds": 2500, "rush_yds": 1200, "rec_yds": 1200, "tackles": 150, "sack": 12, "int": 7,
             "fg_made": 30, "total_td": 18, "scrim": 2500}


class RecordBook:
    def __init__(self):
        self.game, self.season = {}, {}
        self.team_game, self.team_season = {}, {}
        self.streaks = {}                 # school -> current winning streak (games)
        self.files = {}                   # pid -> career file (dict)
        self.news = {}                    # year -> [(week, priority, text)]
        self.announced = set()            # (year, pid, key, scope) season records already in the news
        self.next_pid = 1
        self.since = None


def book(league):
    b = league.__dict__.get("record_book")
    if b is None:
        b = league.record_book = RecordBook()
    return b


def pid(league, p):
    """A player's permanent id (players move schools; names repeat)."""
    v = p.__dict__.get("pid")
    if v is None:
        b = book(league)
        v = p.pid = b.next_pid
        b.next_pid += 1
    return v


# ── derived lines ────────────────────────────────────────────────────────────
def derive(line):
    """The record book's view of a stat line (a game, a season or a career)."""
    g = line.get
    return {
        "pass_yds": g("pass_yds", 0), "pass_td": g("pass_td", 0), "pass_cmp": g("pass_cmp", 0),
        "rush_yds": g("rush_yds", 0), "rush_td": g("rush_td", 0),
        "rec": g("rec", 0), "rec_yds": g("rec_yds", 0), "rec_td": g("rec_td", 0),
        "scrim": g("rush_yds", 0) + g("rec_yds", 0),
        "total_td": g("rush_td", 0) + g("rec_td", 0) + g("kr_td", 0) + g("pr_td", 0),
        "tackles": g("tkl", 0) + g("ast", 0), "tfl": g("tfl", 0), "sack": g("sack", 0), "int": g("int", 0),
        "fg_made": g("fg_made", 0), "ret_yds": g("kr_yds", 0) + g("pr_yds", 0),
        "rush_long": g("rush_long", 0), "rec_long": g("rec_long", 0), "fg_long": g("fg_long", 0),
    }


def phrase(key, v):
    """'412 passing yards', or 'a 64-yard field goal' for the longs."""
    if KIND.get(key) == "max":
        what = {"rush_long": "run", "rec_long": "reception", "fg_long": "field goal"}.get(key, LABEL[key].lower())
        return f"a {fmt(key, v)}-yard {what}"
    return f"{fmt(key, v)} {LABEL[key].lower()}"


def fmt(key, v):
    if isinstance(v, float):
        return f"{v:.1f}" if abs(v - round(v)) > 1e-9 else f"{int(round(v)):,}"
    return f"{v:,}"


# ── boards ───────────────────────────────────────────────────────────────────
# An entry: (value, name, pos, school, year, week, detail, pid)

def _board(store, scope, key):
    return store.setdefault(scope, {}).setdefault(key, [])


def _place(store, scope, key, entry, keep, lower=False):
    """Put an entry on a board. Returns its place (1 = the record) or None."""
    lst = _board(store, scope, key)
    v = entry[0]
    if len(lst) >= keep:
        worst = lst[-1][0]
        if (v >= worst) if lower else (v <= worst):
            return None
    lst.append(entry)
    lst.sort(key=lambda e: (e[0] if lower else -e[0], e[4], e[5]))
    del lst[keep:]
    try:
        return lst.index(entry) + 1
    except ValueError:
        return None


def top(store, scope, key):
    lst = store.get(scope, {}).get(key, [])
    return lst[0] if lst else None


def _news(league, week, priority, text):
    book(league).news.setdefault(league.year, []).append((week, priority, text))


def _who(e):
    return f"{e[2]} {e[1]}" if e[2] else e[1]


# ── after every game ─────────────────────────────────────────────────────────
def after_game(league, game):
    """Single-game records (players and teams), streaks, and season marks passed."""
    if league is None or game.box is None:
        return
    sim = game.box
    b = book(league)
    if b.since is None:
        b.since = league.year                      # the first game on the books
    wk = game.week
    fbs = {t for t in (game.home, game.away) if not getattr(t, "fcs", False)}
    for p, line in sim.stats.items():
        team = sim.team_of(p)
        if team not in fbs:
            continue
        opp = sim.other(team)
        d = derive(line)
        for key, v in d.items():
            if not v or v < MIN_GAME.get(key, 1):
                continue
            e = (v, p.name, p.position, team.school, league.year, wk, f"vs {opp.school}", pid(league, p))
            nat = _place(b.game, NATIONAL, key, e, KEEP[NATIONAL])
            sch = _place(b.game, team.school, key, e, KEEP_SCHOOL_GAME)
            seasoned = league.year > b.since
            if nat == 1 and len(b.game[NATIONAL][key]) > 1 and v >= NEWS_MIN.get(key, 10 ** 9):
                _news(league, wk, 86, f"RECORD: {team.school}'s {p.name} sets the FBS single-game record "
                                       f"with {phrase(key, v)} vs {opp.school}")
            elif sch == 1 and seasoned and len(b.game[team.school][key]) >= KEEP_SCHOOL_GAME \
                    and v >= NEWS_MIN.get(key, 10 ** 9) * 0.8:
                _news(league, wk, 55, f"{p.name} sets a {team.school} single-game record: {phrase(key, v)} "
                                      f"vs {opp.school}")
        # Season marks, the week they're passed.
        season = derive(p.season_stats)
        for key in SEASON_NEWS:
            v = season.get(key, 0)
            if not v:
                continue
            for scope, pr, floor in ((NATIONAL, 84, SEASON_NEWS), (team.school, 58, SCHOOL_SEASON_NEWS)):
                rec = top(b.season, scope, key)
                tag = (league.year, pid(league, p), key, scope)
                if rec and v > rec[0] >= floor[key] and rec[7] != pid(league, p) and tag not in b.announced:
                    b.announced.add(tag)
                    where = "the FBS" if scope == NATIONAL else f"the {team.school}"
                    _news(league, wk, pr, f"RECORD: {p.name} passes {rec[1]} ({rec[4]}) for {where} single-season "
                                          f"record in {LABEL[key].lower()} ({fmt(key, v)} and counting)")
    # Team game records.
    ts = sim.team_stats
    for team in fbs:
        opp = sim.other(team)
        pts, opp_pts = sim.score[team], sim.score[opp]
        vals = {"points": pts, "total_yds": ts[team].get("total_yds", 0), "rush_yds": ts[team].get("rush_yds", 0),
                "pass_yds": ts[team].get("pass_yds", 0), "margin": pts - opp_pts if pts > opp_pts else 0,
                "combined": pts + opp_pts}
        for key, v in vals.items():
            if v <= 0 or (key == "combined" and team is not game.home and game.home in fbs):
                continue
            e = (v, team.school, "", team.school, league.year, wk, f"{pts}-{opp_pts} vs {opp.school}", 0)
            nat = _place(b.team_game, NATIONAL, key, e, KEEP[NATIONAL])
            _place(b.team_game, team.school, key, e, KEEP_SCHOOL_GAME)
            if nat == 1 and len(b.team_game[NATIONAL][key]) > 1 and v >= TEAM_NEWS_MIN.get(key, 10 ** 9):
                _news(league, wk, 80, f"RECORD: {team.school} sets the FBS record for "
                                      f"{TEAM_GAME_LABEL[key].lower()}, {pts}-{opp_pts} over {opp.school}")
    # Streaks.
    for team in (game.home, game.away):
        if getattr(team, "fcs", False):
            continue
        won = game.winner is team
        s = b.streaks.get(team.school, 0) + 1 if won else 0
        b.streaks[team.school] = s
        if s >= 5:
            e = (s, team.school, "", team.school, league.year, wk, "active", 0)
            # one entry per streak: replace this team's active entry
            for scope in (NATIONAL, team.school):
                lst = _board(b.team_season, scope, "streak")
                lst[:] = [x for x in lst if not (x[1] == team.school and x[6] == "active")]
                _place(b.team_season, scope, "streak", e, KEEP[NATIONAL] if scope == NATIONAL else KEEP_SCHOOL_SEASON)
        if not won:
            for scope in (NATIONAL, team.school):
                for i, x in enumerate(b.team_season.get(scope, {}).get("streak", [])):
                    if x[1] == team.school and x[6] == "active":
                        b.team_season[scope]["streak"][i] = x[:6] + (f"ended {league.year}",) + x[7:]


# ── end of the season ────────────────────────────────────────────────────────
def close_season(league):
    """Called by run_offseason before season stats roll into careers."""
    if not any(t.wins + t.losses for t in league.teams):
        return                                     # the burn-in years: nobody played
    b = book(league)
    y = league.year
    for old in [k for k in b.news if k < y]:
        del b.news[old]                            # headlines are this season's; the boards keep the rest
    b.announced = {t for t in b.announced if t[0] >= y}
    for team in league.teams:
        games = team.wins + team.losses
        for p in team.roster:
            if not p.games_played and not sum(p.season_stats.values()):
                continue
            d = derive(p.season_stats)
            i = pid(league, p)
            for key in CAREER_KEYS:
                v = d.get(key, 0)
                if not v:
                    continue
                e = (v, p.name, p.position, team.school, y, 0, f"{p.games_played} games", i)
                _place(b.season, NATIONAL, key, e, KEEP[NATIONAL])
                _place(b.season, team.school, key, e, KEEP_SCHOOL_SEASON)
            f = b.files.get(i)
            if f is None:
                f = b.files[i] = {"pid": i, "name": p.name, "pos": p.position, "first": y, "last": y,
                                  "years": {}, "honors": [], "drafted": None, "hs_stars": getattr(p, "hs_stars", 0),
                                  "peak_ovr": p.overall, "titles": []}
            f["name"], f["pos"], f["last"] = p.name, p.position, y
            f["peak_ovr"] = max(f.get("peak_ovr", 0), p.overall)
            line = {k: v for k, v in Counter(p.season_stats).items() if v}
            f["years"][y] = {"school": team.school, "games": p.games_played, "line": line,
                             "cls": p.class_label, "ovr": p.overall,
                             "coach": team.coach.name if team.coach is not None else None}
            if "National Champion" in getattr(team, "achievements", []):
                f["titles"].append((y, team.school))
        if games:
            vals = {"wins": team.wins, "points": team.points_for, "diff": team.points_for - team.points_against}
            if games >= PPG_MIN_GAMES:
                vals["ppg"] = round(team.points_for / games, 1)
                vals["fewest_ppg"] = round(team.points_against / games, 1)
            rec = f"{team.wins}-{team.losses}"
            for key, v in vals.items():
                if key != "fewest_ppg" and v <= 0:
                    continue
                e = (v, team.school, "", team.school, y, 0, rec, 0)
                low = key in LOWER_IS_BETTER
                _place(b.team_season, NATIONAL, key, e, KEEP[NATIONAL], lower=low)
                _place(b.team_season, team.school, key, e, KEEP_SCHOOL_SEASON, lower=low)


def after_awards(league, awards, draft):
    """Honors and draft picks go in the career files (run_offseason, after the draft)."""
    b = book(league)
    y = league.year

    def honor(p, text):
        f = b.files.get(p.__dict__.get("pid"))
        if f is not None and (y, text) not in [tuple(h) for h in f["honors"]]:
            f["honors"].append((y, text))
    if awards:
        if awards.get("heisman"):
            honor(awards["heisman"][0], "Golden Helmet")
        for name, p, t, _ in awards.get("positional", []):
            honor(p, name)
        for grp, p, t in awards.get("first", []):
            honor(p, "First-team All-American")
        for grp, p, t in awards.get("second", []):
            honor(p, "Second-team All-American")
        if awards.get("freshman"):
            honor(awards["freshman"][0], "Freshman of the Year")
    for pick in (draft or {}).get("picks", []):
        p = pick.get("player")
        f = b.files.get(p.__dict__.get("pid")) if p is not None else None
        if f is not None:
            f["drafted"] = (y, pick["round"], pick["overall_pick"], pick["nfl"])
    prune(league)


def active_pids(league):
    return {p.__dict__.get("pid") for t in league.teams for p in t.roster if p.__dict__.get("pid")}


def career_totals(f, school=None):
    tot = Counter()
    games = 0
    for y, yr in f["years"].items():
        if school is None or yr["school"] == school:
            for k, v in yr["line"].items():
                tot[k] = max(tot[k], v) if k.endswith("_long") else tot[k] + v   # a career long is the longest
            games += yr["games"]
    return tot, games


def notable(f):
    tot, _ = career_totals(f)
    d = derive(tot)
    if f.get("honors") or (f.get("drafted") and f["drafted"][1] <= 3):
        return True
    return any(d.get(k, 0) >= v for k, v in KEEP_FILE.items())


def prune(league):
    """Careers that are over and forgettable leave the book (the save stays small)."""
    b = book(league)
    live = active_pids(league)
    for i in [i for i, f in b.files.items() if i not in live and f["last"] < league.year and not notable(f)]:
        del b.files[i]


# ── career boards (computed) ─────────────────────────────────────────────────
def career_board(league, key, school=None, n=10):
    b = book(league)
    live = {}
    for t in league.teams:
        for p in t.roster:
            i = p.__dict__.get("pid")
            if i is not None:
                live[i] = (p, t)
    out = []
    seen = set()
    for i, f in b.files.items():
        tot, games = career_totals(f, school)
        cur = live.get(i)
        if cur is not None and (school is None or cur[1].school == school):
            tot = tot + Counter(cur[0].season_stats)
            games += cur[0].games_played
        v = derive(tot).get(key, 0)
        if v:
            schools = sorted({yr["school"] for yr in f["years"].values()}, key=lambda s: -sum(
                1 for yr in f["years"].values() if yr["school"] == s))
            yrs = f"{f['first']}-{f['last'] if cur is None else league.year}"
            out.append((v, f["name"], f["pos"], school or " / ".join(schools), f["first"], 0,
                        f"{yrs} · {games} games" + (" · active" if cur is not None else ""), i))
            seen.add(i)
    # Players in their first season have no file yet.
    for i, (p, t) in live.items():
        if i in seen or (school is not None and t.school != school):
            continue
        v = derive(p.season_stats).get(key, 0)
        if v:
            out.append((v, p.name, p.position, t.school, league.year, 0, f"{league.year} · {p.games_played} games · active", i))
    out.sort(key=lambda e: -e[0])
    return out[:n]


def career_tops(league, n=3):
    """Every career board at once, national and school by school, in one pass:
    {"FBS": {key: [entries]}, school: {key: [entries]}}. Cached for the week."""
    c = league.__dict__.get("_career_tops")
    if c is not None and c[0] == (league.year, league.week, len(book(league).files)):
        return c[1]
    b = book(league)
    live = {}
    for t in league.teams:
        for p in t.roster:
            i = p.__dict__.get("pid")
            if i is not None:
                live[i] = (p, t)
    out = {}

    def push(scope, key, e):
        lst = out.setdefault(scope, {}).setdefault(key, [])
        lst.append(e)
        if len(lst) > n * 3:
            lst.sort(key=lambda x: -x[0])
            del lst[n:]
    for i, f in b.files.items():
        per = {}
        for y, yr in f["years"].items():
            per.setdefault(yr["school"], Counter()).update(yr["line"])
        cur = live.get(i)
        if cur is not None:
            per.setdefault(cur[1].school, Counter()).update(cur[0].season_stats)
        total = Counter()
        for sch, tot in per.items():
            total.update(tot)
            d = derive(tot)
            for k in CAREER_KEYS:
                if d[k]:
                    push(sch, k, (d[k], f["name"], f["pos"], sch, f["first"], 0, "", i))
        d = derive(total)
        for k in CAREER_KEYS:
            if d[k]:
                push(NATIONAL, k, (d[k], f["name"], f["pos"], "", f["first"], 0, "", i))
    for scope in out.values():
        for k, lst in scope.items():
            lst.sort(key=lambda x: -x[0])
            del lst[n:]
    league._career_tops = ((league.year, league.week, len(b.files)), out)
    return out


def season_board(league, key, school=None, n=10, live=True):
    """The finished-season board, with this season's leaders mixed in while it's going."""
    b = book(league)
    scope = school or NATIONAL
    out = list(b.season.get(scope, {}).get(key, []))
    if live and not getattr(league, "_season_closed", False):
        for t in league.teams:
            if school is not None and t.school != school:
                continue
            for p in t.roster:
                v = derive(p.season_stats).get(key, 0)
                if v:
                    out.append((v, p.name, p.position, t.school, league.year, 0,
                                f"{p.games_played} games · in progress", p.__dict__.get("pid", 0)))
    out.sort(key=lambda e: (-e[0], e[4]))
    return out[:n]


def coach_board(league, key, school=None, n=10):
    """Coaches' records from their books: wins (career / at one school), titles."""
    import carousel
    seen, rows = set(), []
    coaches = carousel.all_coaches(league) + list(getattr(league, "coach_pool", [])) + \
        list(getattr(league, "retired_coaches", []))
    for c in coaches:
        if id(c) in seen:
            continue
        seen.add(id(c))
        hist = list(getattr(c, "history", []) or [])
        cur = c.team if c.team is not None and c in carousel.all_coaches(league) else None
        if cur is not None and not (hist and hist[-1].get("year") == league.year):
            hist.append({"year": league.year, "school": cur.school, "w": cur.wins, "l": cur.losses,
                         "title": False, "conf_champ": False})
        if school is not None:
            hist = [h for h in hist if h.get("school") == school]
        if not hist:
            continue
        w = sum(h.get("w", 0) for h in hist)
        l_ = sum(h.get("l", 0) for h in hist)
        titles = sum(1 for h in hist if h.get("title"))
        confs = sum(1 for h in hist if h.get("conf_champ"))
        val = {"wins": w, "titles": titles, "conf": confs, "seasons": len({h["year"] for h in hist})}[key]
        if val:
            first, last = min(h["year"] for h in hist), max(h["year"] for h in hist)
            rows.append((val, c.name, "", school or (cur.school if cur else hist[-1].get("school", "")), first, 0,
                         f"{w}-{l_} · {first}-{last}", 0))
    rows.sort(key=lambda e: (-e[0], e[4]))
    return rows[:n]


COACH_KEYS = [("wins", "Wins"), ("titles", "National championships"), ("conf", "Conference championships"),
              ("seasons", "Seasons")]


def news(league, week=None, year=None):
    b = league.__dict__.get("record_book")
    if b is None:
        return []
    items = b.news.get(year or league.year, [])
    return [x for x in items if week is None or x[0] >= week]


def migrate(league):
    """Older saves: the book starts empty this season."""
    book(league)
