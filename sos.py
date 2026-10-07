"""
sos.py — Strength of schedule, for every FBS team, all season.

How good an opponent is: the same measure the Selection Committee reads (committee.py) —
his roster (team overall) plus 25 x his winning percentage. An FCS opponent counts as a 40
roster at .300. Early in the year a team's record is blended with last season's, so a
September schedule isn't judged on one or two games:

    record = (games x this year's pct + 3 x last year's pct) / (games + 3)

Three views of every schedule:
    FULL        every game on the schedule, played or not (postseason games once they're set)
    PLAYED      the games so far
    AHEAD       the games still to play

Every FBS team is ranked 1 (hardest) to 138 on each. Opponents' record is the combined
record of a team's FBS opponents in their other games (FCS schools' records don't count,
the way the CAB figures it).

In Coach Career you see ranks and words (brutal, tough, average, soft, very soft), never the
index itself: it's built from ratings you don't get to see. Every other mode shows the index.

At the end of every season the final table is kept (league.sos_history), so past seasons have
their strength of schedule too.
"""
from ui import C, paint

FCS_ROSTER, FCS_PCT = 40, 0.3
PRIOR_GAMES = 3

WORDS = ((15, "brutal", C.BRED), (40, "tough", C.BYELLOW), (85, "average", C.BWHITE),
         (115, "soft", C.BCYAN), (999, "very soft", C.GRAY))

_CACHE = {}


def _pct(t):
    if getattr(t, "fcs", False):
        return FCS_PCT
    n = t.wins + t.losses
    last = getattr(t, "last_season", None)
    prior = last[0] / (last[0] + last[1]) if last and (last[0] + last[1]) else 0.5
    return (n * (t.wins / n if n else 0) + PRIOR_GAMES * prior) / (n + PRIOR_GAMES)


def _quality(t, ovr):
    if getattr(t, "fcs", False):
        return FCS_ROSTER + 25 * FCS_PCT
    return ovr[t] + 25 * _pct(t)


def _fbs(league):
    return [t for t in league.teams if not getattr(t, "fcs", False)]


def table(league):
    """{team: {"full", "played", "ahead": index or None, "rank_full", "rank_played", "rank_ahead",
    "opp_w", "opp_l", "n_played", "n_ahead"}} for every FBS team, cached for the week."""
    played_total = sum(1 for wk in league.schedule.values() for g in wk if g.played)
    key = (id(league), league.year, league.week, played_total, sum(len(w) for w in league.schedule.values()))
    if _CACHE.get("key") == key:
        return _CACHE["table"]
    teams = _fbs(league)
    ovr = {}
    for t in teams:
        ovr[t] = t.team_ovr
    games_of = {t: [] for t in teams}
    for wk in sorted(league.schedule):
        for g in league.schedule[wk]:
            for side in (g.home, g.away):
                if side in games_of:
                    games_of[side].append(g)
    out = {}
    for t in teams:
        full, played, ahead = [], [], []
        opp_w = opp_l = 0
        for g in games_of[t]:
            o = g.opponent_of(t)
            if o not in ovr and not getattr(o, "fcs", False):
                ovr[o] = o.team_ovr
            q = _quality(o, ovr)
            full.append(q)
            (played if g.played else ahead).append(q)
            if not getattr(o, "fcs", False):
                w, l = o.wins, o.losses                 # his record in his other games
                if g.played:
                    if g.winner is o:
                        w -= 1
                    else:
                        l -= 1
                opp_w, opp_l = opp_w + max(0, w), opp_l + max(0, l)
        avg = lambda xs: sum(xs) / len(xs) if xs else None
        out[t] = {"full": avg(full), "played": avg(played), "ahead": avg(ahead),
                  "opp_w": opp_w, "opp_l": opp_l, "n_played": len(played), "n_ahead": len(ahead)}
    for k in ("full", "played", "ahead"):
        ranked = sorted((t for t in teams if out[t][k] is not None), key=lambda t: -out[t][k])
        for i, t in enumerate(ranked, 1):
            out[t]["rank_" + k] = i
        for t in teams:
            out[t].setdefault("rank_" + k, None)
    _CACHE.update(key=key, table=out)
    return out


def of(league, team, year=None):
    """This team's row (this season's, or a finished season's from the history). None if unknown."""
    if year is not None and year != league.year:
        return getattr(league, "sos_history", {}).get(year, {}).get(team.school)
    if getattr(team, "fcs", False):
        return None
    return table(league).get(team)


def word(rank):
    for cut, w, col in WORDS:
        if rank <= cut:
            return w, col
    return WORDS[-1][1], WORDS[-1][2]


def tag(rank, show_word=True):
    """'No. 12 (tough)', colored by the word."""
    if not rank:
        return paint("—", C.GRAY)
    w, col = word(rank)
    return paint(f"No. {rank}" + (f" ({w})" if show_word else ""), col, C.BOLD if rank <= 15 else "")


def opp_record(row):
    w, l = row.get("opp_w", 0), row.get("opp_l", 0)
    pct = w / (w + l) if w + l else 0
    return f"{w}-{l} ({pct:.3f})".replace("(0.", "(.") if w + l else "—"


def line(league, team, year=None, hide=False):
    """The one-line summary for a schedule screen."""
    row = of(league, team, year)
    if not row:
        return None
    parts = [paint("Strength of schedule", C.GRAY) + " " + tag(row.get("rank_full"))]
    if not hide and row.get("full") is not None:
        parts[0] += paint(f"  index {row['full']:.1f}", C.GRAY)
    if year in (None, league.year):
        if row.get("n_played") and row.get("n_ahead"):
            parts.append(paint("played ", C.GRAY) + tag(row.get("rank_played"), False))
            parts.append(paint("ahead ", C.GRAY) + tag(row.get("rank_ahead"), False))
    parts.append(paint("opponents ", C.GRAY) + opp_record(row))
    return "   " + paint("  ·  ", C.GRAY).join(parts)


def snapshot(league):
    """Keep this season's final table (called at the end of the season). The world-building
    years before 2026 play no games, so they keep nothing."""
    if not any(g.played for wk in league.schedule.values() for g in wk):
        return
    t = table(league)
    hist = league.__dict__.setdefault("sos_history", {})
    hist[league.year] = {team.school: {k: v for k, v in row.items()} for team, row in t.items()}


# ═══ The rankings screen ════════════════════════════════════════════════════

SORTS = {"f": ("full", "FULL SEASON"), "p": ("played", "PLAYED SO FAR"), "a": ("ahead", "STILL TO PLAY")}


def screen(league, focus=None):
    """Tab 5 RANKINGS -> [O]: every FBS team ranked by strength of schedule."""
    from ui import ask, clear, pad, title_bar, truncate, footer, key, back_key
    import scout
    from ui import short_school
    hide = scout.hidden(league)
    sort, conf, year = "f", None, league.year
    page = 0
    per = 35
    focus = focus or getattr(league, "user_team", None) or getattr(league, "follow_team", None)
    while True:
        past = year != league.year
        if past:
            rows_by_school = getattr(league, "sos_history", {}).get(year, {})
            teams = [t for t in _fbs(league) if t.school in rows_by_school]
            get = lambda t: rows_by_school[t.school]
        else:
            tb = table(league)
            teams = list(tb)
            get = lambda t: tb[t]
        field, label = SORTS[sort]
        if past and field != "full":
            field, label = "full", "FULL SEASON"
        rows = [t for t in teams if get(t).get("rank_" + field)]
        if conf:
            rows = [t for t in rows if t.conference == conf]
        rows.sort(key=lambda t: get(t)["rank_" + field])
        pages = max(1, (len(rows) + per - 1) // per)
        page = min(page, pages - 1)
        clear()
        print(title_bar(f"{year} · STRENGTH OF SCHEDULE · {label}" + (f" · {conf.upper()}" if conf else ""),
                        sub=f"PAGE {page + 1} OF {pages}"))
        print(paint("\n   How good every team's opponents are: roster plus record, the way the committee reads it."
                    + (" Ranks and words only —" if hide else ""), C.GRAY))
        if hide:
            print(paint("   the index is built from ratings your staff can't see.", C.GRAY))
        print()
        head = f"   {'RK':>3}  {'TEAM':<22}{'CONF':<14}{'REC':<7}{'SCHEDULE':<12}"
        head += "" if hide else f"{'INDEX':>6}  "
        head += f"{'PLAYED':<8}{'AHEAD':<8}OPPONENTS"
        print(paint(head, C.GRAY, C.BOLD))
        for t in rows[page * per:(page + 1) * per]:
            r = get(t)
            rk = r["rank_" + field]
            w, col = word(r.get("rank_full") or rk)
            rec = t.record if not past else next((f"{h[1]}-{h[2]}" for h in getattr(t, "historical_records", [])
                                                  if h[0] == year), "—")
            mark = paint("▶", C.BYELLOW, C.BOLD) if t is focus else " "
            idx = r.get(field)
            cells = (f"  {mark}{rk:>3}  {pad(paint(truncate(short_school(t.school, 21), 21), C.BWHITE), 22)}"
                     f"{pad(paint(truncate(t.conference, 13), league.conference_color(t.conference)), 14)}"
                     f"{pad(rec, 7)}{pad(paint(w, col), 12)}")
            if not hide:
                cells += f"{(f'{idx:.1f}' if idx is not None else '—'):>6}  "
            cells += (f"{pad(str(r.get('rank_played') or '—') if not past else '—', 8)}"
                      f"{pad(str(r.get('rank_ahead') or '—') if not past else '—', 8)}{opp_record(r)}")
            print(cells)
        if focus is not None and focus not in rows[page * per:(page + 1) * per] and \
                (not conf or focus.conference == conf) and focus in rows:
            r = get(focus)
            print(paint(f"   ...  ▶ {focus.school}: No. {r['rank_' + field]}", C.BYELLOW))
        years = sorted(getattr(league, "sos_history", {}))
        keys = [key("F", "full season"), key("P", "played"), key("A", "still to play"),
                key("C", "one conference" if not conf else "all teams")]
        if pages > 1:
            keys += [key("N", "next page"), key("L", "previous page")]
        if years:
            keys.append(key("Y", "another season"))
        keys.append(key("T#", "open the team at that rank"))
        footer(*keys, back_key())
        c = ask("Select:").strip().lower()
        if c in ("f", "p", "a"):
            sort, page = c, 0
        elif c == "c":
            if conf:
                conf = None
            else:
                from screens import pick_conference
                conf = pick_conference(league)
            page = 0
        elif c == "n" and pages > 1:
            page = (page + 1) % pages
        elif c == "l" and pages > 1:
            page = (page - 1) % pages
        elif c == "y" and years:
            opts = [league.year] + [y for y in years if y != league.year]
            pick = ask(f"Which season? ({', '.join(map(str, opts))})").strip()
            if pick.isdigit() and int(pick) in opts:
                year, page = int(pick), 0
        elif c.startswith("t") and c[1:].isdigit():
            i = int(c[1:])
            vis = rows
            if 1 <= i:
                t = next((x for x in vis if get(x)["rank_" + field] == i), None)
                if t is not None:
                    from screens import schedule_view
                    schedule_view(league, t, year=year if past else None)
        elif c in ("b", "", "q"):
            return
