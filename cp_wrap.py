"""
cp_wrap.py — The Weekly Wrap's other pages (Coach Career).

The wrap's front page (career_plus.wrap) is the week at a glance. These are the pages behind it:

  [G] The game        line score, team stats side by side, unit grades, the scoring, the stars
  [C] The league      your conference race: standings, games back, what's left, who you need to lose
  [P] The playoff     the field if it were picked today, the bubble, your résumé, the odds of winning out
  [N] Next opponent   a scouting page: form, leaders, units against yours, injuries, the series, the line
  [F] Fans & room     the fan pulse and its trend, the message boards, chemistry, morale, who's unhappy
"""
import math
import random

from ui import (
    WIDTH,
    C,
    bar,
    clear,
    clip,
    columns,
    meter,
    pad,
    paint,
    panel,
    section,
    title_bar,
    truncate,
)


def _cp():
    import career_plus
    return career_plus


def _my_game(league, team, games):
    return next((x for x in games if team in (x.home, x.away) and x.played), None)


def _clock(sec):
    sec = int(sec or 0)
    return f"{sec // 60}:{sec % 60:02d}"


def _ratio(a, b):
    return f"{a}/{b}" if b else "0/0"


# ═══ Unit grades ════════════════════════════════════════════════════════════

def unit_grades(team, g):
    """{'Offense': 'B+', 'Defense': 'C', 'Special teams': 'A'} for one game, or {}."""
    from cp_cards import grade
    box = getattr(g, "box", None)
    if box is None:
        return {}
    opp = g.opponent_of(team)
    me, them = box.team_stats.get(team), box.team_stats.get(opp)
    if not me or not them:
        return {}
    ypp = me["total_yds"] / me["plays"] if me["plays"] else 0
    oypp = them["total_yds"] / them["plays"] if them["plays"] else 0
    pts, opts = g.score_for(team), g.score_for(opp)
    off = (ypp - 5.6) / 3.0 + (pts - 27) / 40 - me["turnovers"] * 0.08
    dfn = (5.6 - oypp) / 3.0 + (24 - opts) / 40 + them["turnovers"] * 0.08
    st_ = 0.0
    fga = fgm = rtd = 0
    for p, c in box.stats.items():
        if p in team.roster:
            fga += c.get("fg_att", 0)
            fgm += c.get("fg_made", 0)
            rtd += c.get("kr_td", 0) + c.get("pr_td", 0)
    if fga:
        st_ += (fgm / fga - 0.75) * 0.8
    st_ += 0.35 * rtd
    return {"Offense": grade(off), "Defense": grade(dfn), "Special teams": grade(st_)}


def grades_line(team, g):
    from cp_cards import GRADE_COLOR
    ug = unit_grades(team, g)
    if not ug:
        return ""
    return "   ".join(f"{paint(k, C.GRAY)} {paint(v, GRADE_COLOR.get(v[0], C.BWHITE), C.BOLD)}" for k, v in ug.items())


# ═══ [G] The game ═══════════════════════════════════════════════════════════

def page_game(league, team, games):
    g = _my_game(league, team, games)
    clear()
    print(title_bar(f"THE GAME · {team.school.upper()}", league.team_color(team)))
    if g is None or getattr(g, "box", None) is None:
        print(paint("\n   No game this week.", C.GRAY))
        return
    box = g.box
    opp = g.opponent_of(team)
    a, h = g.away, g.home
    n = max(len(box.line.get(a, [])), 4)
    hdr = "".join(pad(str(i + 1) if i < 4 else ("OT" if i == 4 else f"{i - 3}OT"), 5, "right") for i in range(n))
    print()
    print(paint("   " + pad("", 24) + hdr + pad("T", 6, "right"), C.GRAY))
    for t in (a, h):
        qs = "".join(pad(str(x), 5, "right") for x in box.line.get(t, []))
        col = C.BGREEN if t is g.winner else C.BWHITE
        print("   " + pad(paint(t.school, col, C.BOLD), 24) + qs + paint(pad(str(g.score_for(t)), 6, "right"), col, C.BOLD))
    # the difference
    mine_q, their_q = box.line.get(team, []), box.line.get(opp, [])
    if mine_q and their_q:
        diffs = [(mine_q[i] - their_q[i], i) for i in range(min(len(mine_q), len(their_q)))]
        d, i = max(diffs) if g.winner is team else min(diffs)
        qn = ("first quarter", "second quarter", "third quarter", "fourth quarter")[i] if i < 4 else "overtime"
        if d:
            print(paint(f"\n   The difference: a {mine_q[i]}-{their_q[i]} {qn}.", C.BCYAN))
    ug = grades_line(team, g)
    if ug:
        print(f"   {paint('Unit grades', C.GRAY)}  {ug}")
    # team stats
    ts_m, ts_o = box.team_stats[team], box.team_stats[opp]
    rows = [("First downs", ts_m["first_downs"], ts_o["first_downs"]),
            ("Total yards", ts_m["total_yds"], ts_o["total_yds"]),
            ("  Passing", ts_m["pass_yds"], ts_o["pass_yds"]),
            ("  Rushing", ts_m["rush_yds"], ts_o["rush_yds"]),
            ("Yards per play", f"{ts_m['total_yds'] / ts_m['plays']:.1f}" if ts_m["plays"] else "-",
             f"{ts_o['total_yds'] / ts_o['plays']:.1f}" if ts_o["plays"] else "-"),
            ("Explosive plays", ts_m["explosive_plays"], ts_o["explosive_plays"]),
            ("3rd down", _ratio(ts_m["third_conv"], ts_m["third_att"]), _ratio(ts_o["third_conv"], ts_o["third_att"])),
            ("Red zone TDs", _ratio(ts_m["red_zone_td"], ts_m["red_zone_att"]), _ratio(ts_o["red_zone_td"], ts_o["red_zone_att"])),
            ("Turnovers", ts_m["turnovers"], ts_o["turnovers"]),
            ("Penalties", f"{ts_m['penalties']}-{ts_m['pen_yds']}", f"{ts_o['penalties']}-{ts_o['pen_yds']}"),
            ("Possession", _clock(ts_m["top"]), _clock(ts_o["top"]))]
    left = [paint(pad("", 18) + pad(team.abbr, 9, "right") + pad(opp.abbr, 9, "right"), C.GRAY)]
    for lab, x, y in rows:
        left.append(pad(lab, 18) + pad(str(x), 9, "right") + paint(pad(str(y), 9, "right"), C.GRAY))
    # stars
    right = []
    for side, who in ((team, "YOURS"), (opp, "THEIRS")):
        scored = []
        for p, c in box.stats.items():
            if p not in side.roster:
                continue
            v = (c.get("pass_yds", 0) * 0.05 + c.get("pass_td", 0) * 4 - c.get("pass_int", 0) * 3 + c.get("rush_yds", 0) * 0.1
                 + c.get("rush_td", 0) * 6 + c.get("rec_yds", 0) * 0.1 + c.get("rec_td", 0) * 6 + c.get("tkl", 0)
                 + c.get("sack", 0) * 4 + c.get("int", 0) * 5)
            scored.append((v, p, c))
        scored.sort(key=lambda x: -x[0])
        right.append(paint(f"{who}", C.BYELLOW if side is team else C.GRAY, C.BOLD))
        for _v, p, c in scored[:3]:
            right.append(f"{paint(pad(p.position, 3), C.BCYAN)} {pad(truncate(p.name, 18), 19)}"
                         f"{paint(truncate(_cp()._line(c), 24), C.GRAY)}")
    for ln in columns(panel("TEAM STATS", left, 40, height=12), panel("THE STARS", right, 59, height=12)):
        print(ln)
    # the scoring
    sc = list(getattr(box, "scoring", []) or [])
    if sc:
        print(section("THE SCORING", C.BCYAN))
        for q, clk, t, desc in sc[-8:]:
            mine = getattr(t, "school", t) == team.school
            qn = f"Q{q}" if q <= 4 else "OT"
            print(clip(f"   {paint(pad(qn, 4), C.GRAY)}{paint(pad(_clock(clk) if isinstance(clk, (int, float)) else str(clk), 6), C.GRAY)}"
                       f"{paint(pad(getattr(t, 'abbr', str(t)), 6), C.BGREEN if mine else C.BRED, C.BOLD)}{truncate(desc, 78)}", WIDTH))
        if len(sc) > 8:
            print(paint(f"   …{len(sc) - 8} earlier scores in the box score (Schedule → the game).", C.GRAY))


# ═══ [C] The league ═════════════════════════════════════════════════════════

def page_league(league, team):
    clear()
    conf = team.conference
    print(title_bar(f"THE {conf.upper()} RACE · WEEK {league.week}", league.team_color(team)))
    if conf == "Independent":
        print(paint("\n   No conference race for an independent. Your road to the playoff is the whole schedule (P).", C.GRAY))
        return
    div = getattr(team, "division", None)
    rows = league.standings(conf, div) if div else league.standings(conf)
    lead = rows[0] if rows else team
    print(paint(f"\n   {'':4}{'TEAM':<24}{'CONF':<8}{'ALL':<8}{'GB':<6}{'LEFT':<6}{'STREAK':<8}NEXT", C.GRAY, C.BOLD))
    for i, t in enumerate(rows, 1):
        gb = ((lead.conf_wins - t.conf_wins) + (t.conf_losses - lead.conf_losses)) / 2
        left = sum(1 for x in league.team_games(t) if not x.played and x.conference_game)
        seq = [x for x in sorted(league.team_games(t), key=lambda x: x.week) if x.played]
        stk = ""
        if seq:
            w = seq[-1].winner is t
            n = 0
            for x in reversed(seq):
                if (x.winner is t) == w:
                    n += 1
                else:
                    break
            stk = f"{'W' if w else 'L'}{n}"
        nx = next((x for x in sorted(league.team_games(t), key=lambda x: x.week) if not x.played), None)
        nxt = f"{'vs' if nx and (nx.home is t or nx.neutral) else 'at'} {nx.opponent_of(t).school}" if nx else "—"
        rk = league.rankings.rank_of(t)
        me = t is team
        name = (f"#{rk} " if rk else "") + t.school
        print(clip(f"   {paint(pad(str(i), 3), C.GRAY)} {paint(pad(truncate(name, 23), 24), C.BGREEN if me else C.BWHITE, C.BOLD if me else '')}"
                   f"{pad(t.conf_record, 8)}{pad(t.record, 8)}{pad('—' if gb <= 0 else f'{gb:g}', 6)}{pad(str(left), 6)}"
                   f"{paint(pad(stk, 8), C.BGREEN if stk.startswith('W') else C.BRED)}{paint(truncate(nxt, 22), C.GRAY)}", WIDTH))
    # where you stand
    print(section("WHERE YOU STAND", C.BYELLOW))
    above = [t for t in rows if t is not team and t.conf_losses < team.conf_losses]
    tied = [t for t in rows if t is not team and t.conf_losses == team.conf_losses]
    mine_left = [x for x in sorted(league.team_games(team), key=lambda x: x.week) if not x.played and x.conference_game]
    if not above:
        print(paint("   You control your own destiny: nobody has fewer conference losses than you."
                    + (f" Tied in the loss column with {', '.join(t.school for t in tied[:3])}." if tied else ""), C.BGREEN))
    else:
        print(paint(f"   You need help: {', '.join(t.school for t in above[:4])} {'has' if len(above) == 1 else 'have'} fewer conference losses.",
                    C.BYELLOW))
        root = []
        for t in above[:3]:
            nx = [x for x in league.team_games(t) if not x.played and x.conference_game]
            if nx:
                o = nx[0].opponent_of(t)
                root.append(f"{o.school} over {t.school} ({league.week_name(nx[0].week)})")
        if root:
            print(paint("   Root for: " + "; ".join(root), C.GRAY))
    if mine_left:
        import carousel as cz
        bits = []
        for x in mine_left:
            o = x.opponent_of(team)
            p = cz.win_prob(team, o, 0 if x.neutral else (1 if x.home is team else -1), league)
            bits.append(f"{'vs' if x.home is team or x.neutral else 'at'} {o.school} {paint(f'{p * 100:.0f}%', C.BGREEN if p >= 0.6 else C.BYELLOW if p >= 0.4 else C.BRED)}")
        print("   Left in the league: " + ",  ".join(bits))
    elif league.week <= 13:
        print(paint("   Your conference schedule is done.", C.GRAY))


# ═══ [P] The playoff ════════════════════════════════════════════════════════

def projected_field(league):
    """[(team, rank, champion?)] — if the committee picked today: five conference leaders, seven at-large."""
    order = None
    try:
        import committee
        c = committee.get(league)
        if c.released and c.year == league.year:
            order = [t for t in c.order[:40]] if hasattr(c, "order") else None
    except Exception:                                   # noqa: BLE001, S110
        pass
    if not order:
        order = list(league.rankings.order[:40])
    fbs_confs = {t.conference for t in league.teams if not getattr(t, "fcs", False) and t.conference != "Independent"}
    leaders = set()
    for conf in fbs_confs:
        st = league.standings(conf)
        if st:
            leaders.add(st[0])
    champs = [t for t in order if t in leaders][:5]
    rest = [t for t in order if t not in champs][:max(0, 12 - len(champs))]
    field = sorted(champs + rest, key=lambda t: order.index(t))
    bubble = [t for t in order if t not in field][:4]
    return [(t, order.index(t) + 1, t in leaders) for t in field], [(t, order.index(t) + 1) for t in bubble]


def page_playoff(league, team):
    import carousel as cz
    clear()
    print(title_bar(f"THE PLAYOFF PICTURE · WEEK {league.week}", league.team_color(team)))
    field, bubble = projected_field(league)
    try:
        import committee
        c = committee.get(league)
        src = "the committee's rankings" if c.released and c.year == league.year else "the media poll (the committee hasn't released yet)"
    except Exception:                                   # noqa: BLE001
        src = "the media poll"
    print(paint(f"\n   If it were picked today, from {src}: the five best conference leaders, then seven at-large.", C.GRAY))
    left = []
    for i, (t, rk, ch) in enumerate(field, 1):
        me = t is team
        left.append(f"{paint(f'{i:>2}.', C.BYELLOW if i <= 4 else C.BWHITE, C.BOLD)} "
                    f"{paint(pad(truncate(t.school, 18), 19), C.BGREEN if me else C.BWHITE, C.BOLD if me else '')}"
                    f"{pad(t.record, 6)}{paint('lead' if ch else '', C.GRAY)}")
    left.append(paint("BUBBLE", C.GRAY, C.BOLD))
    for t, rk in bubble:
        me = t is team
        left.append(f"    {paint(pad(truncate(t.school, 18), 19), C.BGREEN if me else C.GRAY)}{paint(pad(t.record, 6), C.GRAY)}"
                    f"{paint(f'#{rk}', C.GRAY)}")
    # résumé
    s = cz.season_line(league, team)
    bad = 0
    for g in league.team_games(team):
        if g.played and g.winner is not team and not (getattr(g, "ranks", None) or {}).get(g.opponent_of(team)):
            bad += 1
    try:
        import sos
        row = sos.of(league, team)
        sos_txt = sos.tag(row.get("rank_played")) if row else "—"
    except Exception:                                   # noqa: BLE001
        sos_txt = "—"
    rk = league.rankings.rank_of(team)
    inside = any(t is team for t, _r, _c in field)
    right = [f"{paint('Record', C.GRAY)}        {team.record}  ({team.conf_record} conf)",
             f"{paint('Ranked', C.GRAY)}        {('No. ' + str(rk)) if rk else 'no'}",
             f"{paint('Ranked wins', C.GRAY)}   {s['t25w']}" + (f"  ({s['t25_road_w']} on the road)" if s["t25_road_w"] else ""),
             f"{paint('Bad losses', C.GRAY)}    {bad}",
             f"{paint('Schedule', C.GRAY)}      {sos_txt}",
             ""]
    left_games = [x for x in sorted(league.team_games(team), key=lambda x: x.week) if not x.played and x.game_type == "Regular Season"]
    p_all = 1.0
    chances = []
    for x in left_games:
        o = x.opponent_of(team)
        p = cz.win_prob(team, o, 0 if x.neutral else (1 if x.home is team else -1), league)
        p_all *= p
        if league.rankings.rank_of(o):
            chances.append(f"#{league.rankings.rank_of(o)} {o.school}")
    if left_games:
        w_out = f"{team.wins + len(left_games)}-{team.losses}"
        right.append(f"{paint('Win out', C.GRAY)}       {w_out} · {paint(f'{p_all * 100:.0f}% chance', C.BYELLOW)}")
        right.append(f"{paint('To impress', C.GRAY)}    " + (", ".join(chances[:3]) if chances else "no ranked teams left"))
    verdict = ("In the field today. Keep winning." if inside else
               "On the bubble. One more big win changes everything." if any(t is team for t, _ in bubble) else
               "Outside looking in. You need wins and help." if rk else
               "Not in the conversation yet.")
    right.append("")
    right.append(paint(verdict, C.BGREEN if inside else C.BYELLOW, C.BOLD))
    for ln in columns(panel("THE FIELD TODAY", left, 46, height=18), panel("YOUR RÉSUMÉ", right, 53, height=18)):
        print(ln)


# ═══ [N] Next opponent ══════════════════════════════════════════════════════

def _leaders(t):
    out = []
    for k, lab, pos in (("pass_yds", "pass", ("QB",)), ("rush_yds", "rush", None), ("rec_yds", "rec", None),
                        ("tkl", "tackles", None), ("sack", "sacks", None)):
        best = max((p for p in t.roster if p.season_stats.get(k, 0) and (pos is None or p.position in pos)),
                   key=lambda p: p.season_stats.get(k, 0), default=None)
        if best is not None:
            v = best.season_stats.get(k, 0)
            out.append(f"{paint(pad(lab, 8), C.GRAY)}{paint(pad(best.position, 3), C.BCYAN)} {pad(truncate(best.name, 18), 19)}"
                       f"{v:g}" + (" yds" if "yds" in k else ""))
    return out


def page_next(league, team):
    import carousel as cz
    import scout
    import week as _wk
    nxt = _wk.next_game(league, team)
    clear()
    if nxt is None:
        print(title_bar("NEXT OPPONENT", league.team_color(team)))
        print(paint("\n   No game left on the schedule.", C.GRAY))
        return
    o = nxt.opponent_of(team)
    site = 0 if nxt.neutral else (1 if nxt.home is team else -1)
    print(title_bar(f"SCOUTING · {o.full_name.upper()}", league.team_color(o)))
    rk = league.rankings.rank_of(o)
    where = "neutral site" if nxt.neutral else ("at home" if nxt.home is team else f"at {o.stadium}")
    hc = getattr(o.coach, "name", "?")
    scheme = getattr(o.coach, "offense_scheme", "")
    print(f"\n   {paint(('#' + str(rk) + ' ') if rk else '', C.BYELLOW, C.BOLD)}{paint(o.school, C.BWHITE, C.BOLD)} "
          f"({o.record}, {o.conf_record} {o.conference})   {paint(league.week_name(nxt.week) + ' · ' + where, C.GRAY)}")
    print(paint(f"   Head coach {hc}" + (f" · {scheme} offense" if scheme else ""), C.GRAY))
    form = []
    for x in [x for x in sorted(league.team_games(o), key=lambda x: x.week) if x.played][-4:]:
        oo = x.opponent_of(o)
        w = x.winner is o
        form.append(paint(f"{'W' if w else 'L'} {x.score_for(o)}-{x.score_for(oo)} {'vs' if x.home is o else 'at'} {oo.school}",
                          C.BGREEN if w else C.BRED))
    if form:
        print("   Form  " + paint("  ·  ", C.GRAY).join(form))
    # units
    units = [("Offense", team.offense_ovr, o.defense_ovr, "your offense vs their defense"),
             ("Defense", team.defense_ovr, o.offense_ovr, "your defense vs their offense")]
    left = []
    for lab, a, b, what in units:
        edge = a - b
        word = "big edge" if edge >= 6 else "edge" if edge >= 2 else "even" if edge > -2 else "their edge" if edge > -6 else "their big edge"
        left.append(f"{paint(pad(lab, 9), C.BWHITE, C.BOLD)}{pad(scout.team(a), 12)} vs {pad(scout.team(b), 12)}"
                    f"{paint(word, C.BGREEN if edge >= 2 else C.BRED if edge <= -2 else C.GRAY, C.BOLD)}")
        left.append(paint(f"         {what}", C.GRAY))
    p = cz.win_prob(team, o, site, league)
    spread = -math.log(p / (1 - p)) * 6.5 if 0.01 < p < 0.99 else (-30 if p >= 0.99 else 30)
    line = f"{team.abbr} {spread:+.1f}".replace("+-", "-") if abs(spread) >= 0.5 else "pick 'em"
    left += ["", f"{paint('Win chance', C.GRAY)} {paint(f'{p * 100:.0f}%', C.BYELLOW, C.BOLD)}   {paint('Line', C.GRAY)} {line}"]
    try:
        import rivalries
        s = rivalries.series(league, team, o)
        if s.n:
            last = s.last
            left.append(f"{paint('Series', C.GRAY)}     {s.record_str(team.school)} (since {s.since})"
                        + (f" · last: {last.year}" if last else ""))
        else:
            left.append(paint("Series     first meeting", C.GRAY))
    except Exception:                                   # noqa: BLE001, S110
        pass
    hurt = [p_ for p_ in o.roster if getattr(p_, "inj_games", 0) > 0 and _cp()._is_starter(o, p_)]
    left.append(f"{paint('Their hurt', C.GRAY)} " + (", ".join(f"{x.position} {x.last_name}" for x in hurt[:4]) or "nobody"))
    for ln in columns(panel("THE MATCHUP", left, 55, height=11), panel("THEIR LEADERS", _leaders(o) or [paint("No stats yet.", C.GRAY)], 44, height=11)):
        print(ln)
    print(paint("\n   The full dossier — tendencies, the depth chart, the plan — opens on game day.", C.GRAY))


# ═══ [F] Fans & the room ════════════════════════════════════════════════════

def pulse(league, team):
    """0-100: how the fan base feels this week."""
    import carousel as cz
    xw, _n = cz.expected_wins(league, team)
    v = 50 + (team.wins - xw) * 9
    seq = [x for x in sorted(league.team_games(team), key=lambda x: x.week) if x.played]
    for i, x in enumerate(seq[-3:]):
        v += (6 if x.winner is team else -7) * (0.6 + 0.2 * i)
    rk = league.rankings.rank_of(team)
    if rk:
        v += 12 - rk * 0.35
    try:
        import rivalries
        for x in seq:
            if rivalries.rivalry_name(team, x.opponent_of(team)):
                v += 8 if x.winner is team else -10
    except Exception:                                   # noqa: BLE001, S110
        pass
    return max(0, min(100, round(v)))


def pulse_word(v):
    return ("delirious" if v >= 85 else "fired up" if v >= 70 else "happy" if v >= 58 else "restless" if v >= 45
            else "grumbling" if v >= 32 else "angry" if v >= 18 else "in revolt")


HANDLES = ["BleedTheColors", "OldGrad74", "Section112", "TailgateKing", "RecruitingGuru", "SeasonTicket40Yrs",
           "BoosterBob", "FireTheOC", "ProcessTruster", "CouchCoach", "HomecomingQueen", "DawnPatrol"]


def board_posts(league, team, v, games):
    rng = random.Random(f"posts:{league.year}:{league.week}:{team.school}")
    g = _my_game(league, team, games)
    won = g is not None and g.winner is team
    opp = g.opponent_of(team).school if g is not None else None
    good = [f"Best I've felt about this program in years. {team.nickname} up.",
            "Recruits are noticing. My phone's blowing up with offer news.",
            f"{opp} never had a chance. Book the hotel for December." if opp and won else "Book the hotel for December.",
            "The coach gets it. Give the man an extension.",
            "Defense is flying around. That's coaching."]
    mid = ["Fine. Not great. Fine.", "We'll know who we are after the next two.",
           "Play-calling on third down still makes me nervous.", "Trust the process, I guess.",
           f"Win against {opp}, but we left points out there." if opp and won else "We need a signature win."]
    bad = [f"Losing to {opp}? Unacceptable." if opp and not won else "This is unacceptable.",
           "How long until the AD notices what we all see?", "Same mistakes every week. Who's coaching the coaches?",
           "I'm not renewing my tickets if this keeps up.", "Recruits are watching this. Scary."]
    pool = good if v >= 62 else mid if v >= 42 else bad
    picks = rng.sample(pool, 3)
    return [(rng.choice(HANDLES), t) for t in picks]


def track_pulse(league, team):
    """career_plus.weekly: keep the fan pulse and your seat, week by week."""
    st = _cp().state(league)
    row = st.setdefault("pulse", {}).setdefault(str(league.year), {})
    row[str(league.week)] = [pulse(league, team), getattr(league.user_coach, "seat", 0)]


def spark(vals, lo=0, hi=100):
    ticks = "▁▂▃▄▅▆▇█"
    if not vals:
        return ""
    return "".join(ticks[max(0, min(7, int((v - lo) / max(1, hi - lo) * 7.99)))] for v in vals)


def page_fans(league, team, games):
    import morale
    import personalities
    clear()
    print(title_bar(f"FANS & THE LOCKER ROOM · WEEK {league.week}", league.team_color(team)))
    st = _cp().state(league)
    row = st.get("pulse", {}).get(str(league.year), {})
    wk = sorted(row, key=int)
    v = pulse(league, team)
    col = C.BGREEN if v >= 58 else C.BYELLOW if v >= 40 else C.BRED
    pv = [row[w][0] for w in wk]
    sv = [row[w][1] for w in wk]
    left = [f"{paint('Fan pulse', C.GRAY)}  {bar(v, 20, 100, col)} {paint(str(v), col, C.BOLD)} {paint(pulse_word(v), col)}",
            f"{paint('Season', C.GRAY)}     {paint(spark(pv), C.BCYAN)}  " + paint(f"weeks {wk[0]}-{wk[-1]}" if wk else "", C.GRAY),
            f"{paint('Hot seat', C.GRAY)}   {paint(spark(sv), C.BRED)}  {paint(f'now {league.user_coach.seat}', C.GRAY)}", ""]
    for who, txt in board_posts(league, team, v, games):
        left.append(paint(f"@{who}", C.BCYAN))
        left.append("  " + truncate(txt, 50))
    ch = personalities.chemistry(team)
    mo = morale.avg(team.roster)
    right = [f"{paint('Chemistry', C.GRAY)} {meter(ch, 14)} {ch:.0f}", f"{paint('Morale', C.GRAY)}    {meter(mo, 14)} {mo:.0f}", ""]
    low = sorted((p for p in team.roster if morale.get(p) < 38), key=lambda p: morale.get(p))
    right.append(paint("UNHAPPY", C.BRED, C.BOLD) if low else paint("Nobody's unhappy. Rare.", C.BGREEN))
    for p in low[:5]:
        why = (p.__dict__.get("mood_log") or [(None, 0, "")])[-1][2]
        right.append(f"{paint(pad(p.position, 3), C.BCYAN)} {pad(truncate(p.name, 17), 18)}{paint(truncate(why or morale.word(morale.get(p)), 22), C.GRAY)}")
    high = sorted(team.roster, key=lambda p: -morale.get(p))[:3]
    right.append(paint("LOVING IT", C.BGREEN, C.BOLD))
    for p in high:
        right.append(f"{paint(pad(p.position, 3), C.BCYAN)} {truncate(p.name, 20)}")
    caps = [p for p in (getattr(team, "captains", None) or []) if p in team.roster]
    if caps:
        right.append(paint("Captains: " + ", ".join(p.last_name for p in caps[:4]), C.GRAY))
    for ln in columns(panel("THE FANS", left, 56, height=14), panel("THE ROOM", right, 43, height=14)):
        print(ln)


PAGES = {"g": "the game", "c": "the league", "p": "the playoff", "n": "next opponent", "f": "fans & room"}


def open_page(league, team, games, k):
    {"g": lambda: page_game(league, team, games), "c": lambda: page_league(league, team),
     "p": lambda: page_playoff(league, team), "n": lambda: page_next(league, team),
     "f": lambda: page_fans(league, team, games)}[k]()
