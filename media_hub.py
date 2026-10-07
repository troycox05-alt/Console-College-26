"""
media_hub.py — The Media Center as a dashboard.

Four pages of panels, the way the main menu works: the whole sport at a glance, and one key
from any panel into the full screen behind it.

  1 THE WEEK      the wire, players of the week, upsets and statements, next week's big games
  2 THE RACES     the playoff picture, the Golden Helmet, the other awards, every conference race,
                  the top 10 in both polls
  3 THE NUMBERS   stat leaders, team leaders, the toughest schedules, the unbeaten and the streaks
  4 THE SPORT     the hot seat, who's hurt, the coaching carousel, off the field, recruiting

Every letter works from every page; each page lists its own.
"""
from ui import (
    WIDTH,
    C,
    ask,
    clear,
    clip,
    columns,
    command_bar,
    key,
    pad,
    paint,
    panel,
    pause,
    section,
    tabs,
    title_bar,
    truncate,
)

TABS = ["THE WEEK", "THE RACES", "THE NUMBERS", "THE SPORT"]
W3 = (34, 32, 32)
W2 = (50, 49)


def _mc():
    import media_center
    return media_center


def _fbs(league):
    return [t for t in league.teams if not getattr(t, "fcs", False)]


def _rk(league, t):
    r = league.rankings.rank_of(t)
    return f"#{r} " if r else ""


def _res(league, g):
    """'#4 Texas 31, #9 Georgia 27' from the winner's side."""
    w, l_ = g.winner, g.loser
    r = getattr(g, "ranks", None) or {}
    rw, rl = r.get(w), r.get(l_)
    return (f"{'#' + str(rw) + ' ' if rw else ''}{w.school} {g.score_for(w)}, "
            f"{'#' + str(rl) + ' ' if rl else ''}{l_.school} {g.score_for(l_)}")


# ═══ The panels ═════════════════════════════════════════════════════════════

def p_wire(league, w, n=7):
    mc = _mc()
    lines = []
    for kind, text in mc.headlines(league)[:n]:
        lines.append(paint(f"{kind[:8]:<9}", mc.KIND_COLOR.get(kind, C.GRAY), C.BOLD) + text)
    return panel("THE WIRE  [W]", lines or [paint("A quiet week.", C.GRAY)], w, height=n)


def p_potw(league, w, n=7):
    mc = _mc()
    wk, games = mc._last_week(league)
    lines = []
    if wk:
        aw = mc.week_awards(league, games)
        for k, lab, side in (("off", "OFF", "off"), ("def", "DEF", "def"), ("fr", "FR", None), ("st", "ST", "st")):
            p, _s, c, t = aw[k]
            if p is None:
                continue
            sd = side or ("def" if mc._def_score(c) * 1.3 > mc._off_score(c) else "off")
            lines.append(f"{paint(pad(lab, 4), C.BYELLOW, C.BOLD)}{paint(truncate(p.name, 18), C.BWHITE, C.BOLD)} "
                         f"{paint(p.position + ' · ' + truncate(t.school, 12), C.GRAY)}")
            lines.append("    " + paint(truncate(mc._line(p, c, sd), w - 8), C.GRAY))
    return panel("PLAYERS OF THE WEEK  [P]", lines or [paint("No games yet.", C.GRAY)], w, height=n)


def upsets(league, wk=None):
    """[(how big, kind, game)] for a week: upsets of ranked teams, ranked-vs-ranked, thrillers."""
    mc = _mc()
    if wk is None:
        wk, games = mc._last_week(league)
    else:
        games = [g for g in league.schedule.get(wk, []) if g.played]
    import carousel as cz
    out = []
    for g in games:
        r = getattr(g, "ranks", None) or {}
        w, l_ = g.winner, g.loser
        rw, rl = r.get(w), r.get(l_)
        if rl and (not rw or rw > rl):
            size = (26 - rl) * 2 + (10 if not rw else 0)
            out.append((size, "UPSET", g))
        elif rw and rl:
            out.append((30 - min(rw, rl), "TOP 25", g))
        elif abs(g.home_score - g.away_score) <= 3 and (rw or rl):
            out.append((8, "THRILLER", g))
        else:
            try:
                p = cz.win_prob(w, l_, 0, league)
                if p < 0.25:
                    out.append(((0.25 - p) * 40, "STUNNER", g))
            except Exception:                           # noqa: BLE001, S112 — a bad estimate just isn't listed
                continue
    out.sort(key=lambda x: -x[0])
    return out


KIND_COL = {"UPSET": C.BRED, "TOP 25": C.BCYAN, "THRILLER": C.BMAGENTA, "STUNNER": C.BYELLOW}


def p_upsets(league, w, n=7):
    rows = upsets(league)
    lines = [paint(f"{k:<9}", KIND_COL[k], C.BOLD) + truncate(_res(league, g), w - 13) for _s, k, g in rows[:n]]
    return panel("UPSETS & STATEMENTS  [U]", lines or [paint("Nothing that shook the poll.", C.GRAY)], w, height=n)


def big_games(league, wk=None):
    """Next week's games worth watching, best first."""
    wk = wk or league.week + 1
    out = []
    for g in league.schedule.get(wk, []):
        if g.played:
            continue
        ra, rb = league.rankings.rank_of(g.home), league.rankings.rank_of(g.away)
        if not ra and not rb:
            continue
        score = (26 - (ra or 40)) + (26 - (rb or 40)) + (12 if ra and rb else 0)
        try:
            import rivalries
            if rivalries.rivalry_name(g.home, g.away):
                score += 8
        except Exception:                               # noqa: BLE001, S110
            pass
        out.append((score, g))
    out.sort(key=lambda x: -x[0])
    return [g for _s, g in out]


def p_big_games(league, w, n=7):
    lines = []
    for g in big_games(league)[:n]:
        tag = ""
        try:
            import rivalries
            nm = rivalries.rivalry_name(g.home, g.away)
            tag = paint("  " + nm, C.BMAGENTA) if nm else ""
        except Exception:                               # noqa: BLE001, S110
            pass
        at = "vs" if g.neutral else "at"
        lines.append(truncate(f"{_rk(league, g.away)}{g.away.school} {at} {_rk(league, g.home)}{g.home.school}", w - 4) + tag)
    nxt = league.week_name(league.week + 1) if league.week < 18 else ""
    return panel(f"NEXT: {nxt.upper()}  [G]" if nxt else "NEXT WEEK  [G]",
                 [clip(x, w - 4) for x in lines] or [paint("No ranked teams in action.", C.GRAY)], w, height=n)


def p_field(league, w, n=13):
    mc = _mc()
    lines = []
    if any(t.wins + t.losses for t in league.teams):
        field, auto, bubble = mc.projection(league)
        for i, t in enumerate(field, 1):
            lines.append(f"{paint(f'{i:>2}', C.BYELLOW if i <= 4 else C.BWHITE, C.BOLD)} {pad(truncate(t.school, 17), 18)}"
                         f"{pad(t.record, 6)}{paint('*' if t in auto else '', C.BGREEN)}")
        if bubble:
            lines.append(paint("out: " + ", ".join(truncate(t.school, 10) for t in bubble[:2]), C.GRAY))
    return panel("PLAYOFF PICTURE  [J]", lines or [paint("Check back after week 1.", C.GRAY)], w, height=n)


def p_helmet(league, w, n=13):
    lines = []
    for i, (p, _score, blurb) in enumerate(league.rankings.heisman[:6], 1):
        mv = league.rankings.heisman_movement(p)
        arrow = "" if mv is None or mv == i else paint("▲", C.BGREEN) if mv > i else paint("▼", C.BRED)
        lines.append(f"{paint(f'{i}.', C.BYELLOW, C.BOLD)} {paint(truncate(p.name, 19), C.BWHITE, C.BOLD)} {arrow}")
        lines.append(paint(f"   {p.position} · {truncate(p.team.school if p.team else '', 14)}", C.GRAY))
    return panel("GOLDEN HELMET  [A]", lines or [paint("The race hasn't started.", C.GRAY)], w, height=n)


def p_awards(league, w, n=13):
    mc = _mc()
    players = [(p, t) for t in _fbs(league) for p in t.roster]
    lines = []
    if any(p.season_stats for p, _t in players[:400]):
        dp = sorted(players, key=lambda x: -(mc._def_score(x[0].season_stats) * (1.1 if x[1].win_pct >= .7 else 1)))[:3]
        lines.append(paint("DEFENSE", C.BCYAN, C.BOLD))
        lines += [f" {truncate(p.name, 17):<18}{paint(truncate(t.school, 10), C.GRAY)}" for p, t in dp]
        fr = sorted((x for x in players if x[0].year == 0),
                    key=lambda x: -max(mc._off_score(x[0].season_stats), mc._def_score(x[0].season_stats) * 1.3))[:3]
        lines.append(paint("FRESHMAN", C.BGREEN, C.BOLD))
        lines += [f" {truncate(p.name, 17):<18}{paint(truncate(t.school, 10), C.GRAY)}" for p, t in fr]
        import carousel as cz
        teams = [t for t in _fbs(league) if t.wins + t.losses >= 3]
        if teams:
            ovrs = cz.league_ovrs(league)
            cy = sorted(teams, key=lambda t: -(t.win_pct - cz.expected_pct(t, league, ovrs) + t.wins * 0.01))[:3]
            lines.append(paint("COACH", C.BMAGENTA, C.BOLD))
            lines += [f" {truncate(t.coach.name, 17):<18}{paint(truncate(t.school, 10), C.GRAY)}" for t in cy if t.coach]
    return panel("THE OTHER AWARDS  [A]", lines or [paint("Once games are played.", C.GRAY)], w, height=n)


def conf_rows(league):
    """[(conference, leader, its conference record, the chaser, games back)] — Power leagues first."""
    from rankings import POWER_LEAGUES
    out = []
    for conf in sorted({t.conference for t in _fbs(league) if t.conference != "Independent"},
                       key=lambda c: (c not in POWER_LEAGUES, c)):
        st = league.standings(conf)
        if len(st) < 2:
            continue
        a, b = st[0], st[1]
        gb = ((a.conf_wins - b.conf_wins) + (b.conf_losses - a.conf_losses)) / 2
        out.append((conf, a, b, gb))
    return out


def p_confs(league, w, n=10):
    lines = []
    for conf, a, b, gb in conf_rows(league)[:n]:
        col = league.conference_color(conf)
        chase = f"{truncate(b.school, 14)} {'tied' if gb <= 0 else f'{gb:g} GB'}"
        lines.append(f"{paint(pad(truncate(conf, 12), 13), col, C.BOLD)}{pad(truncate(_rk(league, a) + a.school, 18), 19)}"
                     f"{pad(a.conf_record, 5)}" + paint(truncate(chase, w - 41), C.GRAY))
    return panel("CONFERENCE RACES  [C]", lines or [paint("No conference games yet.", C.GRAY)], w, height=n)


def p_top10(league, w, n=10):
    import committee
    c = committee.get(league)
    live = c.released and c.year == league.year
    lines = [paint(f"{'':4}{'MEDIA':<19}" + ("NP RANKINGS" if live else ""), C.GRAY, C.BOLD)]
    for i, t in enumerate(league.rankings.order[:n - 1], 1):
        prev = league.rankings.previous_rank(t)
        mv = "" if prev is None or league.week == 0 else (paint(f"▲{prev - i}", C.BGREEN) if prev > i else
                                                          paint(f"▼{i - prev}", C.BRED) if prev < i else paint("—", C.GRAY))
        right = ""
        if live and i <= len(c.order):
            ct = c.order[i - 1]
            right = truncate(ct.school, 12)
        lines.append(f"{paint(f'{i:>2}', C.BYELLOW, C.BOLD)}  {pad(truncate(t.school, 13), 14)}{pad(mv, 5)}{right}")
    return panel("TOP 10  [T] [R]", lines, w, height=n)


def _season_leader(league, k, label, fmt="{:,}"):
    best = None
    for t in _fbs(league):
        for p in t.roster:
            v = p.season_stats.get(k, 0)
            if v and (best is None or v > best[0]):
                best = (v, p, t)
    if not best:
        return None
    v, p, t = best
    val = f"{v:g}" if isinstance(v, float) else fmt.format(v)
    return (f"{paint(pad(label, 10), C.GRAY)}{pad(truncate(p.name, 16), 17)}{paint(pad(truncate(t.school, 11), 12), C.GRAY)}"
            f"{paint(val, C.BWHITE, C.BOLD)}")


def p_leaders(league, w, n=9):
    rows = [("pass_yds", "Passing"), ("pass_td", "Pass TD"), ("rush_yds", "Rushing"), ("rush_td", "Rush TD"),
            ("rec_yds", "Receiving"), ("rec", "Catches"), ("tkl", "Tackles"), ("sack", "Sacks"), ("int", "INTs")]
    lines = [x for x in (_season_leader(league, k, lab) for k, lab in rows[:n]) if x]
    return panel("STAT LEADERS  [S]", lines or [paint("No stats yet.", C.GRAY)], w, height=n)


def p_team_leaders(league, w, n=9):
    mc = _mc()
    teams = [t for t in _fbs(league) if t.wins + t.losses]
    lines = []
    if teams:
        nums = {t: mc.team_numbers(t) for t in teams}
        for lab, k, high, fmt in (("Scoring", "ppg", True, "{:.1f}"), ("Defense", "papg", False, "{:.1f}"),
                                  ("Yards", "ypg", True, "{:.0f}"), ("Rushing", "rypg", True, "{:.0f}"),
                                  ("Passing", "pypg", True, "{:.0f}"), ("Margin", "diff", True, "{:+.1f}"),
                                  ("Sacks", "sacks", True, "{:g}"), ("INTs", "ints", True, "{:g}")):
            order = sorted(teams, key=lambda t: -nums[t][k] if high else nums[t][k])[:2]
            a = order[0]
            b = order[1] if len(order) > 1 else None
            lines.append(f"{paint(pad(lab, 9), C.GRAY)}{pad(truncate(a.school, 14), 15)}{paint(pad(fmt.format(nums[a][k]), 7), C.BWHITE, C.BOLD)}"
                         + (paint(truncate(f"{b.school} {fmt.format(nums[b][k])}", w - 36), C.GRAY) if b else ""))
    return panel("TEAM LEADERS  [M]", lines or [paint("No games yet.", C.GRAY)], w, height=n)


def p_sos(league, w, n=7):
    lines = []
    try:
        import sos
        tbl = sos.table(league)
        rows = sorted((r.get("rank_played") or 999, t) for t, r in tbl.items() if r.get("rank_played"))
        for rk, t in rows[:n]:
            lines.append(f"{paint(f'{rk:>2}', C.BYELLOW, C.BOLD)}  {pad(truncate(_rk(league, t) + t.school, 22), 23)}{pad(t.record, 6)}"
                         f"{paint(truncate(t.conference, 12), league.conference_color(t.conference))}")
    except Exception:                                   # noqa: BLE001, S110
        pass
    return panel("TOUGHEST SCHEDULES  [O]", lines or [paint("After a few weeks.", C.GRAY)], w, height=n)


def p_unbeaten(league, w, n=7):
    teams = [t for t in _fbs(league) if t.wins + t.losses]
    unb = sorted((t for t in teams if t.losses == 0 and t.wins), key=lambda t: (league.rankings.rank_of(t) or 99, -t.wins))
    lines = []
    if unb:
        lines.append(paint(f"{len(unb)} UNBEATEN", C.BGREEN, C.BOLD))
        import textwrap
        wrapped = textwrap.wrap(", ".join(f"{_rk(league, t)}{t.school}" for t in unb), w - 4)
        lines += wrapped[:2]
        if len(wrapped) > 2:
            lines[-1] = truncate(lines[-1] + " …", w - 4)
    streaks = []
    for t in teams:
        seq = [g for g in sorted(league.team_games(t), key=lambda g: g.week) if g.played]
        k = 0
        for g in reversed(seq):
            if g.winner is t:
                k += 1
            else:
                break
        if k >= 4 and t.losses:
            streaks.append((k, t))
    streaks.sort(key=lambda x: -x[0])
    if streaks:
        lines.append(paint("HOT (won since a loss)", C.BYELLOW, C.BOLD))
        for k, t in streaks[:n - len(lines)]:
            lines.append(f"{pad(truncate(_rk(league, t) + t.school, 24), 25)}{paint(f'W{k}', C.BGREEN)}  {paint(t.record, C.GRAY)}")
    return panel("UNBEATEN & STREAKING", lines or [paint("Everybody's 0-0.", C.GRAY)], w, height=n)


def p_heat(league, w, n=7):
    import carousel as cz
    rows = sorted(((getattr(t.coach, "seat", 0), t) for t in _fbs(league) if t.coach and not cz.is_interim(t.coach)),
                  key=lambda x: -x[0])
    lines = []
    for h, t in rows[:n]:
        col = C.BRED if h >= 70 else C.BYELLOW if h >= 50 else C.BWHITE
        filled = int(h / 100 * 8)
        bar = paint("━" * filled, col, C.BOLD) + paint("─" * (8 - filled), "\033[38;5;238m")
        lines.append(f"{pad(truncate(t.coach.name, 15), 16)}{pad(truncate(t.school, 11), 12)}{pad(t.record, 5)}{bar} "
                     f"{paint(str(h), col, C.BOLD)}")
    return panel("HOT SEAT  [H]", lines, w, height=n)


def p_hurt(league, w, n=7):
    rows = []
    for t in _fbs(league):
        rk = league.rankings.rank_of(t)
        for p in t.injured():
            if p in t.players_at(p.position)[:1] and "opted out" not in str(getattr(p, "inj_desc", "")):
                rows.append(((rk or 40), -p.overall, t, p))
    rows.sort(key=lambda x: (x[0], x[1]))
    lines = []
    for _rk_, _o, t, p in rows[:n]:
        out = "season" if p.inj_games >= 99 else f"{p.inj_games} wk"
        lines.append(f"{pad(truncate(_rk(league, t) + t.school, 17), 18)}{paint(pad(p.position, 3), C.BCYAN)} "
                     f"{pad(truncate(p.name, 15), 16)}{paint(out, C.BRED if p.inj_games >= 99 else C.BYELLOW)}")
    return panel("WHO'S HURT  [I]", lines or [paint("A healthy week.", C.GRAY)], w, height=n)


def p_carousel(league, w, n=6):
    items = list(getattr(league, "midseason_news", {}).get(league.year, []))
    if not items:
        items = list(getattr(league, "carousel", {}).get(league.year - 1, []) or [])
    lines = []
    from coach_screens import KIND_COLORS
    for kind, text in items[-n:][::-1]:
        lines.append(paint(f"{kind.upper()[:7]:<8}", KIND_COLORS.get(kind, C.GRAY), C.BOLD) + truncate(text, w - 13))
    return panel("COACHING CAROUSEL  [E]", lines or [paint("Every coach is safe. For now.", C.GRAY)], w, height=n)


def p_offfield(league, w, n=6):
    lines = []
    try:
        import compliance
        for x in compliance.recent_news(league, n=n):
            lines.append(paint("● ", C.BRED) + truncate(x["text"], w - 6))
    except Exception:                                   # noqa: BLE001, S110
        pass
    return panel("OFF THE FIELD  [X]", lines or [paint("Nothing on the wire.", C.GRAY)], w, height=n)


def p_recruit_wire(league, w, n=6):
    lines = []
    for _wk, kind, text in league.recruiting.news[:n]:
        col = C.BGREEN if kind == "commit" else C.BRED if kind == "decommit" else C.BCYAN
        lines.append(paint("● ", col) + truncate(text, w - 6))
    return panel("RECRUITING WIRE  [N]", lines or [paint("No news yet.", C.GRAY)], w, height=n)


# ═══ The refined screens the hub adds ═══════════════════════════════════════

def upsets_screen(league):
    mc = _mc()
    wk, _g = mc._last_week(league)
    while True:
        clear()
        print(title_bar(f"UPSETS, STATEMENTS & THRILLERS · {league.week_name(wk).upper() if wk else 'PRESEASON'}"))
        rows = upsets(league, wk) if wk else []
        if not rows:
            print(paint("\n   Nothing that shook the poll.", C.GRAY))
        for _s, k, g in rows[:24]:
            site = "neutral" if g.neutral else f"at {g.home.school}"
            m = abs(g.home_score - g.away_score)
            print(clip(f"   {paint(f'{k:<9}', KIND_COL[k], C.BOLD)}{pad(_res(league, g), 58)}{paint(f'{site} · by {m}', C.GRAY)}", WIDTH))
        print(paint("\n   UPSET: a ranked team loses to a lower-ranked or unranked one · TOP 25: two ranked teams ·\n"
                    "   STUNNER: the favorite by a mile loses · THRILLER: three points or fewer with a ranked team.", C.GRAY))
        c = ask("Week # to look back, Enter = back:").strip()
        if c.isdigit() and 1 <= int(c) <= max(1, league.week):
            wk = int(c)
        else:
            return


def big_games_screen(league):
    import carousel as cz
    wk = league.week + 1
    clear()
    print(title_bar(f"GAMES TO WATCH · {league.week_name(wk).upper()}"))
    games = big_games(league, wk)
    if not games:
        print(paint("\n   No ranked teams in action.", C.GRAY))
    print(paint(f"\n   {'MATCHUP':<52}{'FAVORITE':<26}SITE", C.GRAY, C.BOLD))
    for g in games[:25]:
        p = cz.win_prob(g.home, g.away, 0 if g.neutral else 1, league)
        fav, pf = (g.home, p) if p >= 0.5 else (g.away, 1 - p)
        tag = ""
        try:
            import rivalries
            nm = rivalries.rivalry_name(g.home, g.away)
            tag = paint(f"  {nm}", C.BMAGENTA) if nm else ""
        except Exception:                               # noqa: BLE001, S110
            pass
        m = f"{_rk(league, g.away)}{g.away.school} ({g.away.record}) {'vs' if g.neutral else 'at'} {_rk(league, g.home)}{g.home.school} ({g.home.record})"
        print(clip(f"   {pad(truncate(m, 50), 52)}{pad(f'{fav.school} {pf * 100:.0f}%', 26)}"
                   f"{paint('neutral' if g.neutral else g.home.stadium, C.GRAY)}{tag}", WIDTH))
    pause()


def conf_races_screen(league):
    from rankings import POWER_LEAGUES
    confs = sorted({t.conference for t in _fbs(league) if t.conference != "Independent"}, key=lambda c: (c not in POWER_LEAGUES, c))
    clear()
    print(title_bar(f"CONFERENCE RACES · {league.week_name(league.week).upper() if league.week else 'PRESEASON'}"))
    for conf in confs:
        st = league.standings(conf)
        if not st:
            continue
        a = st[0]
        print(section(conf.upper(), league.conference_color(conf)))
        line = []
        for t in st[:5]:
            gb = ((a.conf_wins - t.conf_wins) + (t.conf_losses - a.conf_losses)) / 2
            line.append(f"{_rk(league, t)}{t.school} {t.conf_record}" + (paint(f" ({gb:g} GB)", C.GRAY) if gb > 0 else ""))
        print(clip("   " + paint(" · ", C.GRAY).join(line), WIDTH))
    pause()


# ═══ The hub ════════════════════════════════════════════════════════════════

def page(league, tab):
    if tab == 1:
        rows = columns(p_wire(league, 60), p_potw(league, 39))
        rows += columns(p_upsets(league, 50), p_big_games(league, 49))
        acts = [key("W", "wire"), key("P", "players of the week"), key("U", "upsets & thrillers"),
                key("G", "games to watch"), key("D", "Campus Countdown desk")]
    elif tab == 2:
        rows = columns(p_field(league, W3[0]), p_helmet(league, W3[1]), p_awards(league, W3[2]))
        rows += columns(p_confs(league, 60, n=11), p_top10(league, 39, n=11))
        acts = [key("J", "playoff projection"), key("A", "award races"), key("C", "conference races"),
                key("T", "media Top 25"), key("R", "NP Playoff Rankings"), key("K", "the committee")]
    elif tab == 3:
        rows = columns(p_leaders(league, W2[0]), p_team_leaders(league, W2[1]))
        rows += columns(p_sos(league, W2[0]), p_unbeaten(league, W2[1]))
        acts = [key("S", "stat leaders"), key("M", "team rankings"), key("O", "strength of schedule"),
                key("Y", "parity report"), key("RB", "record book")]
    else:
        rows = columns(p_heat(league, W2[0]), p_hurt(league, W2[1]))
        rows += columns(p_carousel(league, W2[0]), p_offfield(league, W2[1]))
        rows += columns(p_recruit_wire(league, 100))
        acts = [key("H", "hot seat"), key("I", "injuries"), key("E", "carousel"), key("X", "compliance"),
                key("N", "recruiting news"), key("V", "rivalry trophies"), key("L", "realignment"),
                key("Z", "awards archive"), key("F", "the draft"), key("Q", "history lookup"), key("CL", "instant classics")]
    return rows, acts


def _open(league, c):
    mc = _mc()
    import screens as sc
    table = {
        "w": mc.wire, "p": mc.players_of_week, "u": upsets_screen, "g": big_games_screen, "d": mc.gameday_desk,
        "j": mc.playoff_projection, "a": mc.award_races, "c": conf_races_screen, "t": sc.top_25,
        "r": lambda lg: __import__("committee_screens").playoff_rankings(lg),
        "k": lambda lg: __import__("committee_screens").members_screen(lg),
        "s": mc.stat_leaders, "m": mc.team_rankings, "o": lambda lg: __import__("sos").screen(lg),
        "y": mc._parity, "rb": lambda lg: __import__("record_screens").hub(lg),
        "h": mc.hot_seat_watch, "i": mc.injury_report, "e": lambda lg: __import__("coach_screens").carousel_news(lg),
        "x": mc._compliance, "n": lambda lg: __import__("recruiting_screens").news_screen(lg), "v": mc._trophies,
        "l": mc._realign, "z": mc._awards, "f": mc._draft, "q": mc._history, "cl": mc._classics,
    }
    fn = table.get(c)
    if fn is None:
        return False
    fn(league)
    return True


def hub(league, tab=1):
    mc = _mc()
    while True:
        clear()
        wk, _g = mc._last_week(league)
        sub = f"through {league.week_name(wk)}" if wk else "preseason"
        print(title_bar(f"MEDIA CENTER · {league.year} · {sub.upper()}"))
        print(tabs(TABS, tab))
        rows, acts = page(league, tab)
        for ln in rows:
            print(ln)
        for ln in command_bar([key("1-4", "pages", C.GRAY)] + acts + [key("Enter", "back", C.GRAY)]):
            print(ln)
        c = ask("Select:").strip().lower()
        if c in ("1", "2", "3", "4"):
            tab = int(c)
        elif not c or c == "back":
            return
        elif not _open(league, c):
            print(paint("   That's not a key here.", C.BYELLOW))
