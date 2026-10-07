"""
cp_stories.py — The season's storylines, deeper (Coach Career).

career_plus tells the first stories (breakouts, milestones, the QB job, Senior Day...). This adds
the rest of what a beat writer would cover, every week:

  the team      win streaks and skids, upsets (both kinds), revenge games, shutouts, blowouts,
                comebacks, overtime, rivalry trophies, bowl eligibility, the Top 25, No. 1
  the players   stat streaks (100-yard games, TD passes, sacks), slumps, school-record chases,
                the Golden Helmet watch, true freshmen, transfer debuts, comebacks from injury
  recruiting    big commitments, and the ones who walk away

and the ways to read them:

  arcs(league, year)          season-long threads: every story about one player, in order
  season_review(league, year) the ten biggest stories of a season
  screen(league)              the Storylines screen: by week, by player, by kind, the year in review
"""
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

# what each kind of story is about, and how big it is (for the year in review)
CAT = {
    "breakout": "Players", "big day": "Players", "milestone": "Players", "walk-on": "Players",
    "stat streak": "Players", "slump": "Players", "record": "Players", "helmet watch": "Players",
    "freshman": "Players", "transfer": "Players", "return": "Players", "honor": "Players",
    "qb battle": "Team", "qb change": "Team", "captains": "Team", "injury": "Team", "senior day": "Team",
    "streak": "Team", "skid": "Team", "revenge": "Team", "upset": "Team", "upset loss": "Team",
    "shutout": "Team", "blowout": "Team", "comeback": "Team", "overtime": "Team", "rivalry": "Team",
    "landmark": "Team",
    "commit": "Recruiting", "decommit": "Recruiting",
    "achievement": "Legacy", "jersey": "Legacy", "statue": "Legacy", "story start": "Legacy",
    "chapter": "Legacy", "tree": "Legacy", "report card": "Legacy",
}
WEIGHT = {
    "statue": 100, "chapter": 60, "achievement": 22, "upset": 45, "rivalry": 40, "landmark": 35, "jersey": 50,
    "record": 38, "helmet watch": 36, "comeback": 34, "streak": 30, "revenge": 28, "breakout": 26, "overtime": 22,
    "upset loss": 30, "skid": 24, "injury": 22, "qb change": 24, "commit": 20, "decommit": 18, "milestone": 20,
    "walk-on": 22, "senior day": 15, "shutout": 18, "blowout": 12, "stat streak": 16, "slump": 12, "freshman": 14,
    "transfer": 12, "return": 12, "captains": 8, "qb battle": 14, "big day": 10, "story start": 25, "tree": 26,
    "honor": 30, "report card": 10,
}
CAT_COLOR = {"Players": C.BGREEN, "Team": C.BCYAN, "Recruiting": C.BMAGENTA, "Legacy": C.BYELLOW}


def _cp():
    import career_plus
    return career_plus


def _say(league, kind, text, p=None, weight=None):
    cp = _cp()
    cp._story(league, kind, text, p)
    if weight is not None:
        cp.state(league)["stories"][-1]["w"] = weight


def _flags(league):
    return _cp().state(league)["flags"]


def _played(league, team):
    return sorted((g for g in league.team_games(team) if g.played), key=lambda g: g.week)


def _vs(g, team):
    return "vs" if g.home is team or g.neutral else "at"


# ═══ The team ═══════════════════════════════════════════════════════════════

def _team(league, team, g):
    import random
    opp = g.opponent_of(team)
    won = g.winner is team
    me, them = g.score_for(team), g.score_for(opp)
    ranks = getattr(g, "ranks", None) or {}
    rk_me, rk_opp = ranks.get(team), ranks.get(opp)
    ropp = f"No. {rk_opp} {opp.school}" if rk_opp else opp.school
    rng = random.Random(f"st:{league.year}:{g.week}:{team.school}")
    seq = _played(league, team)
    # streaks and skids
    run = 0
    for x in reversed(seq):
        if (x.winner is team) == won:
            run += 1
        else:
            break
    before = 0
    for x in reversed(seq[:len(seq) - run]):
        if (x.winner is team) != won:
            before += 1
        else:
            break
    if won and run in (4, 6, 8, 10, 12, 14):
        _say(league, "streak", f"Streak: {run} straight wins after beating {opp.school}. "
             + rng.choice(("Nobody wants to see this team right now.", "The locker room has stopped talking about it.",
                           "The longest run since the program's last title push." if run >= 8 else "It's starting to feel real.")))
    elif not won and run in (3, 5, 7):
        _say(league, "skid", f"Skid: {run} losses in a row after {opp.school}. "
             + rng.choice(("The message boards are loud.", "Practice gets a little longer this week.",
                           "The staff needs an answer before it gets away from them.")))
    if run == 1 and won and before >= 3:
        _say(league, "streak", f"Skid over: the win over {opp.school} ends a {before}-game losing streak.")
    elif run == 1 and not won and before >= 5:
        _say(league, "skid", f"The streak is over at {before}: {opp.school} ends your {before}-game winning run, "
                             f"{them}-{me}.")
    # upsets
    if won and rk_opp and (not rk_me or rk_me - rk_opp >= 8):
        _say(league, "upset", f"Upset: {'unranked ' if not rk_me else f'No. {rk_me} '}{team.school} "
                              f"{'beats' if g.home is team or g.neutral else 'goes on the road and beats'} {ropp}, {me}-{them}.")
    elif not won and rk_me and rk_me <= 15 and not rk_opp and not getattr(opp, "fcs", False):
        _say(league, "upset loss", f"Stunner: No. {rk_me} {team.school} falls to unranked {opp.school}, {them}-{me}.")
    elif not won and getattr(opp, "fcs", False):
        _say(league, "upset loss", f"Embarrassment: {team.school} loses to FCS {opp.school}, {them}-{me}. "
                                   f"Your AD did not take it well.", weight=60)
    # revenge
    try:
        import archive
        last = [x for x in archive.games_for(league, league.year - 1, team.school)
                if opp.school in (x.home.school, x.away.school)]
        if last and won and last[-1].winner.school != team.school:
            lx = last[-1]
            _say(league, "revenge", f"Revenge: last year {opp.school} won {max(lx.home_score, lx.away_score)}-"
                                    f"{min(lx.home_score, lx.away_score)}. This year, {me}-{them} the other way.")
    except Exception:                                   # noqa: BLE001, S110 — a story is never worth a crash
        pass
    # the scoreboard
    if won and them == 0:
        _say(league, "shutout", f"Shutout: the defense pitches a {me}-0 shutout {_vs(g, team)} {ropp}.")
    elif won and me - them >= 35:
        _say(league, "blowout", f"Rout: {me}-{them} {_vs(g, team)} {opp.school}. The starters sat the fourth quarter.")
    box = getattr(g, "box", None)
    if box is not None and team in box.line:
        a, b = box.line[team], box.line.get(opp, [])
        worst = run_a = run_b = 0
        for q in range(min(len(a), len(b))):
            run_a += a[q]
            run_b += b[q]
            if q < len(a) - 1 or len(a) <= 4:
                worst = max(worst, run_b - run_a)
        after3 = sum(b[:3]) - sum(a[:3]) if len(a) >= 3 and len(b) >= 3 else 0
        if won and (worst >= 14 or after3 >= 10):
            _say(league, "comeback", f"Comeback: down {max(worst, after3)}"
                                     f"{' going into the fourth' if after3 >= 10 else ''}, {team.school} rallies to beat "
                                     f"{opp.school}, {me}-{them}.")
        ot = getattr(box, "ot_round", 0) or 0
        if ot:
            _say(league, "overtime", f"{'Overtime win' if won else 'Overtime loss'}: {me}-{them} {_vs(g, team)} "
                                     f"{opp.school} in {'one overtime' if ot == 1 else f'{ot} overtimes'}.")
    # the rivalry
    try:
        import rivalries
        name = rivalries.rivalry_name(team, opp)
        if name:
            s = rivalries.series(league, team, opp)
            tro = getattr(s, "trophy", None)
            rec = s.record_str(team.school)
            name = name[:1].upper() + name[1:]
            if won:
                _say(league, "rivalry", f"{name}: {team.school} wins {me}-{them}"
                                        + (f" and keeps the {tro} home" if tro and g.home is team else
                                           f" and takes the {tro}" if tro else "")
                                        + f". The series: {rec}.", weight=45)
            else:
                _say(league, "rivalry", f"{name}: {opp.school} wins {them}-{me}. A long year until the next one. "
                                        f"The series: {rec}.", weight=38)
    except Exception:                                   # noqa: BLE001, S110
        pass
    # landmarks
    if g.game_type == "Regular Season" and won and team.wins == 6:
        _say(league, "landmark", f"Bowl eligible: win No. 6 {_vs(g, team)} {opp.school}.", weight=20)
    if g.game_type == "Regular Season" and won and team.wins == 10:
        _say(league, "landmark", "Ten wins. Double digits, and the season isn't over.", weight=30)


def _poll(league, team):
    fl = _flags(league)
    rk = league.rankings.rank_of(team)
    k = f"rk:{league.year}"
    prev = fl.get(k, "start")
    fl[k] = rk
    if prev == "start" or league.week < 1:
        if rk == 1:
            fl[f"no1:{league.year}"] = True
        return
    best = fl.get(f"best:{team.school}")
    if rk == 1 and prev != 1:
        _say(league, "landmark", f"No. 1: {team.school} is the top team in the country"
                                 + ("" if fl.get(f"no1:{league.year}") else " for the first time this season") + ".", weight=50)
        fl[f"no1:{league.year}"] = True
    elif rk and not prev:
        gone = fl.get(f"out:{team.school}")
        _say(league, "landmark", f"Ranked: {team.school} enters the Top 25 at No. {rk}"
                                 + (f", the first time since {gone}" if gone and gone < league.year else "") + ".")
    elif rk and prev and rk <= 10 < prev:
        _say(league, "landmark", f"Top 10: up to No. {rk}.", weight=24)
    elif prev and not rk:
        _say(league, "landmark", f"Out: {team.school} drops out of the Top 25 (was No. {prev}).", weight=18)
        fl[f"out:{team.school}"] = league.year
    if rk and (best is None or rk < best):
        fl[f"best:{team.school}"] = rk


# ═══ The players ════════════════════════════════════════════════════════════

STREAKS = (("rush_yds", 100, "100-yard rushing games"), ("rec_yds", 100, "100-yard receiving games"),
           ("pass_td", 1, "games with a touchdown pass"), ("sack", 1, "games with a sack"),
           ("int", 1, "games with an interception"))
RECORD_KEYS = (("pass_yds", "passing yards", 2000), ("pass_td", "touchdown passes", 18), ("rush_yds", "rushing yards", 900),
               ("rush_td", "rushing touchdowns", 10), ("rec_yds", "receiving yards", 800), ("rec", "catches", 50),
               ("sack", "sacks", 7), ("int", "interceptions", 5), ("tkl", "tackles", 80))


def _players(league, team, g):
    fl = _flags(league)
    box = getattr(g, "box", None)
    if box is None:
        return
    opp = g.opponent_of(team)
    played = {p: c for p, c in box.stats.items() if p in team.roster}
    for p, c in played.items():
        # streaks of good games
        for k, cut, label in STREAKS:
            if k == "pass_td" and p.position != "QB":
                continue
            fk = f"s:{p.name}:{k}"
            if c.get(k, 0) >= cut:
                fl[fk] = fl.get(fk, 0) + 1
                n = fl[fk]
                if n in (3, 5, 8, 12, 16, 20) and (k in ("rush_yds", "rec_yds") or n >= 5):
                    _say(league, "stat streak", f"Streak: {p.position} {p.name} has {n} straight {label}.", p)
            else:
                fl[fk] = 0
        # slumps
        if p.position == "QB" and c.get("pass_int", 0) >= 3:
            n = fl.get(f"slump:{p.name}", 0) + 1
            fl[f"slump:{p.name}"] = n
            _say(league, "slump", f"Rough day: QB {p.name} throws {c['pass_int']} interceptions {_vs(g, team)} {opp.school}."
                                  + (" Two weeks running. The backup is getting reps." if n >= 2 else ""), p)
        elif p.position == "QB" and c.get("pass_att", 0) >= 10:
            fl[f"slump:{p.name}"] = 0
        # firsts
        if p.year == 0 and not getattr(p, "redshirt", False) and _cp()._is_starter(team, p) \
                and not fl.get(f"fr:{p.name}") and p.games_played <= 2:
            fl[f"fr:{p.name}"] = league.year
            _say(league, "freshman", f"True freshman: {p.position} {p.name} starts {_vs(g, team)} {opp.school}"
                                     f"{' — a ' + str(p.hs_stars) + '-star from ' + p.home_state if p.home_state else ''}.", p)
        if getattr(p, "prev_school", None) and not fl.get(f"tr:{p.name}") and p.games_played <= 2:
            fl[f"tr:{p.name}"] = league.year
            line = _cp()._line(c)
            _say(league, "transfer", f"Transfer debut: {p.position} {p.name} (from {p.prev_school}) plays his first game "
                                     f"for {team.school}" + (f": {line}." if line else "."), p)
    # school records
    try:
        import records
        bk = records.book(league)
        for p in team.roster:
            if p not in played:
                continue
            now = records.derive(p.season_stats)
            for k, label, floor in RECORD_KEYS:
                board = bk.season.get(team.school, {}).get(k, [])
                v = now.get(k, 0)
                if not board or v < floor:
                    continue
                top = board[0]
                if top[1] == p.name and top[4] == league.year:
                    continue
                rec = top[0]
                fk = f"rec:{league.year}:{p.name}:{k}"
                if v > rec and fl.get(fk) != "broke":
                    fl[fk] = "broke"
                    _say(league, "record", f"School record: {p.position} {p.name} has {v:g} {label}, passing "
                                           f"{top[1]}'s {rec:g} ({top[4]}).", p, weight=45)
                elif v >= rec * 0.85 and not fl.get(fk) and league.week <= 12:
                    fl[fk] = "chase"
                    _say(league, "record", f"Record watch: {p.position} {p.name} is at {v:g} {label}. The school record "
                                           f"is {rec:g} ({top[1]}, {top[4]}).", p)
    except Exception:                                   # noqa: BLE001, S110
        pass


def _helmet(league, team):
    fl = _flags(league)
    board = getattr(league.rankings, "heisman", []) or []
    for i, (p, _score, _blurb) in enumerate(board[:5], 1):
        if p not in team.roster:
            continue
        k = f"hw:{league.year}:{p.name}"
        best = fl.get(k)
        if best is None:
            fl[k] = i
            _say(league, "helmet watch", f"Golden Helmet watch: {p.position} {p.name} is No. {i} in the race.", p)
        elif i == 1 and best != 1:
            fl[k] = 1
            _say(league, "helmet watch", f"Golden Helmet: {p.position} {p.name} is the front-runner.", p, weight=45)


def _returns(league, team):
    fl = _flags(league)
    k = f"hurt:{team.school}"
    was = set(fl.get(k, []))
    now = {p.name for p in team.roster if getattr(p, "inj_games", 0) > 0}
    for p in team.roster:
        if p.name in was and p.name not in now and "suspend" not in str(getattr(p, "inj_desc", "") or "") \
                and _cp()._is_starter(team, p):
            _say(league, "return", f"Back: {p.position} {p.name} returns from injury.", p)
    fl[k] = sorted(now)


def _recruits(league, team):
    fl = _flags(league)
    cyc = league.recruiting
    k = f"commits:{league.year}"
    was = set(fl.get(k, []))
    now = {}
    for r in cyc.commitments(team):
        now[r.name] = r
    for name, r in now.items():
        if name not in was and r.stars >= 4:
            where = f" from {r.home_state}" if getattr(r, "home_state", None) else ""
            _say(league, "commit", f"Commitment: {r.stars}★ {r.position} {r.name}{where} picks {team.school}.",
                 weight=20 + 8 * (r.stars - 4))
    for name in was - set(now):
        r = next((x for x in cyc.pool if x.name == name), None)
        if r is not None and r.committed_to is not None and r.committed_to is not team:
            _say(league, "decommit", f"Flipped: {r.stars}★ {r.position} {r.name} backs off his pledge and picks "
                                     f"{r.committed_to.school}.")
    fl[k] = sorted(now)


def weekly(league, team, games):
    """career_plus.weekly: after the week is played."""
    for g in games:
        if team in (g.home, g.away) and g.played:
            _team(league, team, g)
            _players(league, team, g)
    _poll(league, team)
    _helmet(league, team)
    _returns(league, team)
    _recruits(league, team)


def season_honors(league):
    """Season end: your All-Americans and award winners become stories."""
    team = league.user_team
    aw = (getattr(league, "awards", {}) or {}).get(league.year) or {}
    fl = _flags(league)
    if fl.get(f"honors:{league.year}"):
        return
    fl[f"honors:{league.year}"] = True
    if aw.get("heisman") and aw["heisman"][1] is team:
        p = aw["heisman"][0]
        _say(league, "honor", f"Golden Helmet: {p.position} {p.name} wins it.", p, weight=90)
    aas = [p for _g, p, t in aw.get("first", []) or [] if t is team]
    if aas:
        _say(league, "honor", f"All-Americans: {', '.join(f'{p.position} {p.name}' for p in aas[:5])}"
                              + (f" and {len(aas) - 5} more" if len(aas) > 5 else "") + ".", weight=30)


# ═══ Reading them ═══════════════════════════════════════════════════════════

def arcs(league, year):
    """[(name, position, [stories])] — a player with two or more stories this season, biggest first."""
    by = {}
    for s in _cp().stories(league, year):
        who = s.get("who")
        if who:
            by.setdefault(who, []).append(s)
    out = [(who, rows[0].get("pos", ""), rows) for who, rows in by.items() if len(rows) >= 2]
    out.sort(key=lambda r: -sum(WEIGHT.get(s["kind"], 10) for s in r[2]))
    return out


def arc_title(who, rows):
    kinds = {s["kind"] for s in rows}
    if "honor" in kinds and any("Golden Helmet: " in s["text"] and "wins it" in s["text"] for s in rows):
        return f"{who} wins the Golden Helmet"
    if "helmet watch" in kinds:
        return f"{who}'s Golden Helmet run"
    if "record" in kinds:
        return f"{who} and the record book"
    if "breakout" in kinds:
        return f"The breakout of {who}"
    if "transfer" in kinds:
        return f"{who}, the transfer"
    if "injury" in kinds and "return" in kinds:
        return f"{who}'s way back"
    if "slump" in kinds:
        return f"{who}'s up-and-down year"
    if "freshman" in kinds:
        return f"{who}, true freshman"
    return f"{who}'s season"


def season_review(league, year, n=10):
    rows = _cp().stories(league, year)
    scored = [(s.get("w") or WEIGHT.get(s["kind"], 10), i, s) for i, s in enumerate(rows)]
    scored.sort(key=lambda x: (-x[0], x[1]))
    keep, per = [], {}
    for x in scored:                                    # no more than two of any one kind
        k = x[2]["kind"]
        if per.get(k, 0) < 2:
            per[k] = per.get(k, 0) + 1
            keep.append(x)
        if len(keep) >= n:
            break
    keep.sort(key=lambda x: x[1])
    return [s for _, _, s in keep]


def _wk(league, w):
    return league.week_name(w) if w else "Preseason"


def _print_rows(league, rows, limit=40):
    last = None
    for s in rows[-limit:]:
        if s["week"] != last:
            last = s["week"]
            print(paint(f"\n   {_wk(league, s['week'])}", C.BCYAN, C.BOLD))
        cat = CAT.get(s["kind"], "Team")
        col = C.BYELLOW if cat == "Legacy" else C.BWHITE
        print(clip(f"     {paint(pad(s['kind'], 13), CAT_COLOR.get(cat, C.GRAY))}{paint(s['text'], col)}", WIDTH))


def screen(league, year=None):
    cp = _cp()
    year = year or league.year
    mode, cat = "week", None
    while True:
        clear()
        team = league.user_team
        print(title_bar(f"{year} STORYLINES · {team.school.upper() if team else ''}"))
        rows = cp.stories(league, year)
        counts = {}
        for s in rows:
            c_ = CAT.get(s["kind"], "Team")
            counts[c_] = counts.get(c_, 0) + 1
        chips = "   ".join(paint(f"{c_} {counts.get(c_, 0)}", CAT_COLOR[c_]) for c_ in ("Team", "Players", "Recruiting", "Legacy"))
        print(f"\n   {len(rows)} stories   {chips}")
        if not rows:
            print(paint("\n   No stories yet this season. Breakouts, streaks, upsets, record chases, the Golden Helmet race,\n"
                        "   big commitments and every landmark land here as they happen.", C.GRAY))
        elif mode == "week":
            shown = [s for s in rows if cat is None or CAT.get(s["kind"], "Team") == cat]
            if cat:
                print(paint(f"   Showing: {cat}", CAT_COLOR[cat], C.BOLD))
            _print_rows(league, shown, 34)
        elif mode == "arcs":
            ar = arcs(league, year)
            print(section("PLAYER ARCS · EVERY STORY ABOUT ONE MAN", C.BGREEN))
            if not ar:
                print(paint("   No player has two stories yet.", C.GRAY))
            for i, (who, pos, rs) in enumerate(ar[:16], 1):
                print(clip(f"   {paint(f'[{i:>2}]', C.BYELLOW, C.BOLD)} {paint(pad(truncate(arc_title(who, rs), 40), 41), C.BWHITE, C.BOLD)}"
                           f"{paint(pad(f'{len(rs)} stories', 11), C.GRAY)}{paint(truncate(rs[-1]['text'], 44), C.GRAY)}", WIDTH))
        elif mode == "review":
            print(section(f"THE {year} SEASON IN TEN STORIES", C.BYELLOW))
            for i, s in enumerate(season_review(league, year), 1):
                print(clip(f"   {paint(f'{i:>2}.', C.BYELLOW, C.BOLD)} {paint(pad(_wk(league, s['week']), 22), C.GRAY)}{s['text']}", WIDTH))
        years = sorted({s["year"] for s in cp.state(league)["stories"]})
        items = [key("W", "by week"), key("P", "player arcs"), key("V", "year in review"), key("F", "filter")]
        if mode == "arcs":
            items.insert(0, key("#", "open an arc"))
        if len(years) > 1:
            items.append(key("Y", "another season"))
        footer(*items, key("B", "back", C.GRAY))
        c = ask("Select:").strip().lower()
        if c == "w":
            mode, cat = "week", None
        elif c == "p":
            mode = "arcs"
        elif c == "v":
            mode = "review"
        elif c == "f":
            mode = "week"
            opts = ["Team", "Players", "Recruiting", "Legacy"]
            f = ask("Filter: [1] Team  [2] Players  [3] Recruiting  [4] Legacy  (Enter = everything)").strip()
            cat = opts[int(f) - 1] if f.isdigit() and 1 <= int(f) <= 4 else None
        elif c.isdigit() and mode == "arcs":
            ar = arcs(league, year)
            if 1 <= int(c) <= len(ar):
                who, _pos, rs = ar[int(c) - 1]
                clear()
                print(title_bar(f"{arc_title(who, rs).upper()} · {year}"))
                _print_rows(league, rs, 60)
                pause()
        elif c == "y" and len(years) > 1:
            y = ask(f"Which season? ({', '.join(map(str, years))})").strip()
            if y.isdigit() and int(y) in years:
                year = int(y)
        else:
            return
