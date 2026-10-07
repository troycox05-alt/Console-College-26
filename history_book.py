"""
history_book.py — The whole story, nothing cut off.

PROGRAM HISTORY (any team): every season since the world began — record, conference
record, final rank, postseason, head coach, recruiting class, honors — a page at a time,
newest or oldest first. Plus the coaching eras, the trophy case (titles, conference
titles, playoff trips, bowls, Heisman winners, All-Americans, draft picks) and the
all-time series against every opponent.

COACH CAREER (any coach): every season as a head coach, every season as a coordinator,
each job's totals, every move he made and why, and his career before this world began.

Every list pages ([N] next, [P] previous, [O] flips the order), so a 60-season program or a
35-year career reads the same as a new one.
"""
from ui import C, ask, clear, pad, paint, rule, title_bar, truncate

PER = 24


# ── Paging ──────────────────────────────────────────────────────────────────

def pager(title, rows, header=None, top=(), tabs=(), per=PER, newest_first=True, flip=True):
    """Show `rows` a page at a time. tabs: [(key, label, fn)] — another view to jump to.
    Returns the key of a tab that was picked, or None for back."""
    page, rev = 0, newest_first
    while True:
        data = list(reversed(rows)) if rev else list(rows)
        pages = max(1, (len(data) + per - 1) // per)
        page = max(0, min(page, pages - 1))
        clear()
        print(title_bar(title, sub=f"PAGE {page + 1} OF {pages}" if pages > 1 else None))
        for ln in top:
            print(ln)
        if header:
            print(paint(header, C.GRAY, C.BOLD))
        for ln in data[page * per:(page + 1) * per] or [paint("   Nothing on record yet.", C.GRAY)]:
            print(ln)
        print(rule())
        keys = []
        if pages > 1:
            keys += [f"{paint('[N]', C.BYELLOW, C.BOLD)} next", f"{paint('[P]', C.BYELLOW, C.BOLD)} previous"]
        if len(data) > 1 and flip:
            keys.append(f"{paint('[O]', C.BYELLOW, C.BOLD)} {'oldest' if rev else 'newest'} first")
        keys += [f"{paint('[' + k.upper() + ']', C.BCYAN, C.BOLD)} {lbl}" for k, lbl in tabs]
        keys.append(f"{paint('[B]', C.GRAY, C.BOLD)} back")
        print("   " + "   ".join(keys))
        c = ask("Select:").strip().lower()
        if c in ("", "b", "q"):
            return None
        if c == "n":
            page = min(pages - 1, page + 1)
        elif c == "p":
            page = max(0, page - 1)
        elif c == "o" and flip:
            rev, page = not rev, 0
        elif c.isdigit() and 1 <= int(c) <= pages:
            page = int(c) - 1
        elif any(c == k for k, _l in tabs):
            return c


# ── Program data ────────────────────────────────────────────────────────────

def _everyone(league):
    """Every coach object the world still knows (head coaches, the pool, coordinators, retired)."""
    import carousel as cz
    out, seen = [], set()
    pools = [cz.all_coaches(league), getattr(league, "coach_pool", []), getattr(league, "retired_coaches", [])]
    try:
        import staff
        pools.append(staff.coordinators(league))
    except Exception:                                    # noqa: BLE001, S110
        pass
    pools.append([c for c in getattr(league, "staff_pool", []) or []])
    for grp in pools:
        for c in grp or []:
            if c is not None and id(c) not in seen:
                seen.add(id(c))
                out.append(c)
    return out


def team_seasons(league, team):
    """{year: row} for every season this program has played in this world."""
    rows = {}
    for r in getattr(team, "historical_records", []) or []:
        yr, w, l, cw, cl = r[:5]
        rows[yr] = {"year": yr, "w": w, "l": l, "cw": cw, "cl": cl, "ach": list(r[5]) if len(r) > 5 else [],
                    "conf": r[6] if len(r) > 6 else team.conference}
    for s in team.__dict__.get("season_log", []) or []:
        row = rows.setdefault(s["year"], {"year": s["year"]})
        for k, v in s.items():
            if k == "coach":
                if v and v not in row.setdefault("coaches", []):
                    row["coaches"].append(v)
            elif row.get(k) in (None, "", False):
                row[k] = v
    for c in _everyone(league):
        for s in getattr(c, "history", []) or []:
            if s.get("school") != team.school:
                continue
            row = rows.setdefault(s["year"], {"year": s["year"]})
            for k in ("w", "l", "cw", "cl"):
                row.setdefault(k, s.get(k))
            for k in ("final_rank", "post", "class_rank", "title", "cfp", "conf_champ", "bowl_win", "roster"):
                if row.get(k) in (None, "", False):
                    row[k] = s.get(k)
            names = row.setdefault("coaches", [])
            if c.name not in names:
                names.append(c.name)
            row.setdefault("conf", s.get("conf", team.conference))
    # Archived games fill in anything missing (and know the coach on the sideline each Saturday).
    import archive
    for yr in archive.seasons(league):
        games = archive.games_for(league, yr, team.school)
        if not games:
            continue
        row = rows.setdefault(yr, {"year": yr})
        if row.get("w") is None:
            me = [g for g in games if g.home_score is not None]
            row["w"] = sum(1 for g in me if g.winner.school == team.school)
            row["l"] = len(me) - row["w"]
        if not row.get("coaches"):
            hcs = []
            for g in games:
                stub = g.home if g.home.school == team.school else g.away
                n = (g.hc or {}).get(stub)
                if n and n not in hcs:
                    hcs.append(n)
            if hcs:
                row["coaches"] = hcs
    # This season, while it's being played.
    if league.year not in rows and team.wins + team.losses and not league.season_complete:
        rows[league.year] = {"year": league.year, "w": team.wins, "l": team.losses, "cw": team.conf_wins,
                             "cl": team.conf_losses, "conf": team.conference, "live": True,
                             "coaches": [team.coach.name] if team.coach else []}
    for yr, row in rows.items():
        if row.get("coach") and not row.get("coaches"):
            row["coaches"] = [row["coach"]]
        row.setdefault("ach", [])
        champ = league.champion_of(yr) if hasattr(league, "champion_of") else None
        if champ and champ.champion == team.school:
            row["title"] = True
    return dict(sorted(rows.items()))


def _season_row(row):
    yr = row["year"]
    w, l = row.get("w"), row.get("l")
    rec = f"{w}-{l}" if w is not None else "—"
    conf = f"{row.get('cw', 0)}-{row.get('cl', 0)}" if row.get("cw") is not None else "—"
    rank = f"#{row['final_rank']}" if row.get("final_rank") else "—"
    post = row.get("post") or ("in progress" if row.get("live") else "—")
    if row.get("title"):
        post = "NATIONAL CHAMPION"
    cls = f"#{row['class_rank']}" if row.get("class_rank") else "—"
    coach = " / ".join(row.get("coaches") or []) or "—"
    champ = row.get("conf_champ") or any("Champion" in a and "National" not in a for a in row.get("ach", []))
    col = C.BYELLOW if row.get("title") else C.BWHITE
    star = paint("★", C.BYELLOW) if champ else " "
    return (f"  {star}{paint(str(yr), col, C.BOLD)}  {pad(rec, 6)}{pad(conf, 6)}{pad(truncate(row.get('conf') or '', 12), 13)}"
            f"{pad(rank, 6)}{pad(truncate(post, 28), 29)}{pad(truncate(coach, 24), 25)}{cls}")


def _totals(rows):
    w = sum(r.get("w") or 0 for r in rows)
    l = sum(r.get("l") or 0 for r in rows)
    return w, l


def _eras(rows):
    """Consecutive seasons under the same head coach."""
    eras = []
    for r in rows:
        name = (r.get("coaches") or ["—"])[-1]
        if eras and eras[-1]["coach"] == name:
            eras[-1]["rows"].append(r)
        else:
            eras.append({"coach": name, "rows": [r]})
    return eras


def program_history(league, team):
    view = "s"
    while True:
        seasons = list(team_seasons(league, team).values())
        w, l = _totals(seasons)
        titles = [r["year"] for r in seasons if r.get("title")]
        confs = [r["year"] for r in seasons if r.get("conf_champ") or any("Champion" in a and "National" not in a
                                                                           for a in r.get("ach", []))]
        cfp = sum(1 for r in seasons if r.get("cfp"))
        bowls = [r for r in seasons if (r.get("post") or "").startswith(("Won", "Lost")) and "Bowl" in (r.get("post") or "")]
        bw = sum(1 for r in bowls if r["post"].startswith("Won"))
        top = [paint(f"   {team.full_name} · {len(seasons)} season{'s' if len(seasons) != 1 else ''} on record · "
                     f"{w}-{l} all-time ({w / max(1, w + l):.3f})", C.BWHITE, C.BOLD),
               paint(f"   National titles {len(titles)}{' (' + ', '.join(map(str, titles)) + ')' if titles else ''}"
                     f"   ·   Conference titles {len(confs)}   ·   Playoff trips {cfp}   ·   Bowls {bw}-{len(bowls) - bw}",
                     C.BYELLOW if titles else C.GRAY), ""]
        tabs = [("s", "seasons"), ("c", "coaches"), ("t", "trophy case"), ("v", "series vs every opponent")]
        tabs = [t for t in tabs if t[0] != view]
        if view == "s":
            header = (f"   {'YEAR':<6}{'W-L':<6}{'CONF':<6}{'LEAGUE':<13}{'RANK':<6}{'POSTSEASON':<29}"
                      f"{'HEAD COACH':<25}CLASS      ★ = conference champion")
            pick = pager(f"{team.school.upper()} · PROGRAM HISTORY", [_season_row(r) for r in seasons], header, top, tabs)
        elif view == "c":
            rows = []
            for e in _eras(seasons):
                ew, el = _totals(e["rows"])
                ys = [r["year"] for r in e["rows"]]
                t = sum(1 for r in e["rows"] if r.get("title"))
                cf = sum(1 for r in e["rows"] if r.get("conf_champ"))
                po = sum(1 for r in e["rows"] if r.get("cfp"))
                ranked = sum(1 for r in e["rows"] if r.get("final_rank"))
                span = f"{ys[0]}" + (f"–{ys[-1]}" if ys[-1] != ys[0] else "")
                rows.append(f"   {pad(span, 11)}{pad(truncate(e['coach'], 24), 25)}{pad(str(len(ys)), 5)}"
                            f"{pad(f'{ew}-{el}', 9)}{pad(f'{ew / max(1, ew + el):.3f}', 7)}{pad(str(ranked), 8)}"
                            f"{pad(str(po), 6)}{pad(str(cf), 6)}{t}")
            header = (f"   {'YEARS':<11}{'HEAD COACH':<25}{'YRS':<5}{'W-L':<9}{'PCT':<7}{'RANKED':<8}"
                      f"{'NP':<6}{'CONF':<6}TITLES")
            pick = pager(f"{team.school.upper()} · HEAD COACHES", rows, header, top, tabs)
        elif view == "t":
            pick = pager(f"{team.school.upper()} · TROPHY CASE", _trophies(league, team, seasons), None, top, tabs,
                         newest_first=False)
        else:
            rows, hdr = _series(league, team)
            pick = pager(f"{team.school.upper()} · ALL-TIME SERIES", rows, hdr, top, tabs, newest_first=False, flip=False)
        if pick is None:
            return
        view = pick


def _trophies(league, team, seasons):
    out = []
    for r in seasons:
        bits = []
        if r.get("title"):
            bits.append("National champions")
        bits += [a for a in r.get("ach", []) if "National Champion" not in a]
        if r.get("cfp") and not r.get("title"):
            bits.append("Playoff")
        if (r.get("post") or "").startswith("Won") and "Bowl" in (r.get("post") or ""):
            bits.append(r["post"])
        if bits:
            out.append(f"   {paint(str(r['year']), C.BYELLOW, C.BOLD)}  " + " · ".join(bits))
    for yr, aw in sorted((getattr(league, "awards", {}) or {}).items()):
        if aw.get("heisman") and aw["heisman"][1].school == team.school:
            out.append(f"   {paint(str(yr), C.BYELLOW, C.BOLD)}  Golden Helmet: {aw['heisman'][0].name}")
        for name, p, t, _line in aw.get("positional", []):
            if t.school == team.school:
                out.append(f"   {paint(str(yr), C.BCYAN)}  {name}: {p.name}")
        aa = [p.name for grp, p, t in aw.get("first", []) if t.school == team.school]
        if aa:
            out.append(f"   {paint(str(yr), C.GRAY)}  First-team All-Americans: {', '.join(aa)}")
    for yr, picks in sorted((getattr(league, "drafts", {}) or {}).items()):
        mine = [x for x in picks if x["school"] == team.school]
        if mine:
            r1 = [x["name"] for x in mine if x["round"] == 1]
            out.append(f"   {paint(str(yr), C.GRAY)}  {len(mine)} drafted" + (f" — first round: {', '.join(r1)}" if r1 else ""))
    return out


def _series(league, team):
    import archive
    rec = {}

    def add(opp, won, yr, sc):
        r = rec.setdefault(opp, {"w": 0, "l": 0, "last": None, "streak": [], "big": None})
        r["w" if won else "l"] += 1
        r["last"] = (yr, "W" if won else "L", sc)
        r["streak"].append("W" if won else "L")
    for yr in sorted(archive.seasons(league)):
        for g in archive.games_for(league, yr, team.school):
            if g.home_score is None:
                continue
            me_home = g.home.school == team.school
            opp = g.away.school if me_home else g.home.school
            mine, theirs = (g.home_score, g.away_score) if me_home else (g.away_score, g.home_score)
            add(opp, mine > theirs, yr, f"{mine}-{theirs}")
    for g in league.team_games(team) if not league.season_complete else []:
        if g.played:
            opp = g.opponent_of(team)
            add(opp.school, g.winner is team, league.year, f"{g.score_for(team)}-{g.score_for(opp)}")
    try:
        import rivalries
        rivals = {o for o in rec if rivalries.is_rivalry(team.school, o)}
    except Exception:                                    # noqa: BLE001
        rivals = set()
    order = sorted(rec.items(), key=lambda kv: (kv[0] not in rivals, -(kv[1]["w"] + kv[1]["l"]), kv[0]))
    rows = []
    for opp, r in order:
        st = r["streak"]
        n = 1
        while n < len(st) and st[-n - 1] == st[-1]:
            n += 1
        yr, res, sc = r["last"]
        tag = paint(" rival", C.BMAGENTA) if opp in rivals else ""
        rows.append(f"   {pad(truncate(opp, 22), 23)}{pad(str(r['w']) + '-' + str(r['l']), 8)}"
                    f"{pad(st[-1] + str(n), 7)}{pad(f'{yr} {res} {sc}', 18)}{tag}")
    return rows, f"   {'OPPONENT':<23}{'SERIES':<8}{'STREAK':<7}{'LAST MEETING':<18}"


# ── Coach career ────────────────────────────────────────────────────────────

def coach_career(league, coach):
    import carousel as cz
    view = "s"
    while True:
        hist = list(getattr(coach, "history", []) or [])
        car = cz.splits(hist)
        top = [paint(f"   {coach.name}, {coach.age}  ·  head coach record {car['w']}-{car['l']}"
                     f"  ·  {car['titles']} national title{'s' if car['titles'] != 1 else ''}  ·  "
                     f"{car['confs']} conference title{'s' if car['confs'] != 1 else ''}  ·  "
                     f"{car['cfp']} playoff trip{'s' if car['cfp'] != 1 else ''}", C.BWHITE, C.BOLD), ""]
        tabs = [("s", "head coach seasons"), ("j", "jobs"), ("o", "coordinator years"), ("m", "moves")]
        if getattr(coach, "stops", None):
            tabs.append(("e", "before this world"))
        tabs = [t for t in tabs if t[0] != view]
        if view == "s":
            rows = []
            for s in hist:
                rank = f"#{s['final_rank']}" if s.get("final_rank") else "—"
                cls = f"#{s['class_rank']}" if s.get("class_rank") else "—"
                post = "NATIONAL CHAMPION" if s.get("title") else (s.get("post") or "—")
                col = C.BYELLOW if s.get("title") else C.BWHITE
                rows.append(f"   {paint(str(s['year']), col, C.BOLD)}  {pad(truncate(s['school'], 19), 20)}"
                            f"{pad(str(s['w']) + '-' + str(s['l']), 7)}{pad(str(s['cw']) + '-' + str(s['cl']), 7)}"
                            f"{pad(str(s.get('t25w', 0)) + '-' + str(s.get('t25l', 0)), 7)}{pad(rank, 6)}"
                            f"{pad(cls, 7)}{truncate(post, 30)}")
            hdr = f"   {'YEAR':<6}{'SCHOOL':<20}{'W-L':<7}{'CONF':<7}{'T25':<7}{'RANK':<6}{'CLASS':<7}POSTSEASON"
            pick = pager(f"{coach.name.upper()} · EVERY SEASON", rows, hdr, top, tabs)
        elif view == "j":
            jobs = []
            for s in hist:
                if jobs and jobs[-1]["school"] == s["school"] and jobs[-1]["to"] == s["year"] - 1:
                    jobs[-1]["rows"].append(s)
                    jobs[-1]["to"] = s["year"]
                else:
                    jobs.append({"school": s["school"], "from": s["year"], "to": s["year"], "rows": [s]})
            rows = []
            for j in jobs:
                t = cz.splits(j["rows"])
                span = f"{j['from']}" + (f"–{j['to']}" if j["to"] != j["from"] else "")
                rows.append(f"   {pad(span, 11)}{pad(truncate(j['school'], 22), 23)}{pad(str(len(j['rows'])), 5)}"
                            f"{pad(str(t['w']) + '-' + str(t['l']), 9)}{pad(str(t['cw']) + '-' + str(t['cl']), 9)}"
                            f"{pad(str(t['cfp']), 5)}{pad(str(t['confs']), 6)}{t['titles']}")
            hdr = f"   {'YEARS':<11}{'SCHOOL':<23}{'YRS':<5}{'W-L':<9}{'CONF':<9}{'NP':<5}{'CONF':<6}TITLES"
            pick = pager(f"{coach.name.upper()} · JOBS", rows, hdr, top, tabs)
        elif view == "o":
            rows = []
            for s in getattr(coach, "coord_history", []) or []:
                rows.append(f"   {s['year']}  {pad(truncate(s['school'], 19), 20)}{pad(s['role'], 4)}"
                            f"{pad('unit #' + str(s['rank']), 11)}{pad('talent #' + str(s['exp']), 13)}"
                            f"{s['ppg']:.1f} ppg {'allowed' if s['role'] == 'DC' else ''}")
            hdr = f"   {'YEAR':<6}{'SCHOOL':<20}{'ROLE':<4}{'UNIT':<11}{'TALENT':<13}POINTS"
            pick = pager(f"{coach.name.upper()} · COORDINATOR YEARS", rows, hdr, top, tabs)
        elif view == "m":
            import coach_screens
            rows = [f"   {paint(str(yr), C.GRAY)}  {text}" for yr, text in coach_screens.career_moves(league, coach)]
            pick = pager(f"{coach.name.upper()} · EVERY MOVE", rows, None, top, tabs)
        else:
            stops = getattr(coach, "stops", None) or []
            rows = [f"   {s if isinstance(s, str) else ' · '.join(str(x) for x in s)}" for s in stops]
            pick = pager(f"{coach.name.upper()} · BEFORE THIS WORLD", rows, None, top, tabs, newest_first=False)
        if pick is None:
            return
        view = pick


# ── Pickers (Go To, the media desk) ─────────────────────────────────────────

def pick_team_history(league):
    from screens import pick_team
    t = pick_team(league)
    if t is not None:
        program_history(league, t)


def pick_coach_career(league):
    q = ask("Coach's name (part of it is fine):").strip().lower()
    if not q:
        return
    hits = [c for c in _everyone(league) if q in c.name.lower()]
    if not hits:
        print(paint("   Nobody by that name.", C.BYELLOW))
        ask("Enter:")
        return
    if len(hits) > 1:
        clear()
        print(title_bar("WHICH COACH?"))
        for i, c in enumerate(hits[:20], 1):
            where = c.team.school if getattr(c, "team", None) is not None else getattr(c, "status", "")
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {c.name} — {where}")
        s = ask("Number:").strip()
        if not (s.isdigit() and 1 <= int(s) <= min(20, len(hits))):
            return
        hits = [hits[int(s) - 1]]
    coach_career(league, hits[0])


def book_season(league, team, s, coach):
    """carousel.end_of_season: the program keeps its own copy of every season (coaches come and go)."""
    log = team.__dict__.setdefault("season_log", [])
    if log and log[-1].get("year") == s.get("year"):
        return
    keep = {k: s.get(k) for k in ("year", "w", "l", "cw", "cl", "final_rank", "post", "class_rank", "title", "cfp",
                                   "conf_champ", "bowl_win", "conf")}
    keep["coach"] = coach.name if coach is not None else None
    log.append(keep)

