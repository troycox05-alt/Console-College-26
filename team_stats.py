"""team_stats.py — season team-stat dashboard and national ranks.

Stats come from the real snap-by-snap GameSim boxes.  An explosive play is a
20+ yard offensive play; we also keep the familiar 10+ rush / 20+ pass split.
"""
from collections import Counter

from ui import C, ask, clear, paint, pad, panel, columns, title_bar


def _games(league, team):
    out = []
    for week in sorted(getattr(league, "schedule", {})):
        for g in league.schedule[week]:
            if getattr(g, "played", False) and team in (g.home, g.away) and getattr(g, "box", None) is not None:
                out.append(g)
    return out


def _side_total(box, team, key):
    total = 0
    for p, c in getattr(box, "stats", {}).items():
        try:
            pt = box.team_of(p)
        except Exception:
            pt = team if p in getattr(team, "roster", []) else None
        if pt is team:
            total += c.get(key, 0)
    return total


def raw(league, team):
    """Aggregate the current season into one Counter plus opponent totals."""
    me, opp = Counter(), Counter()
    games = _games(league, team)
    for g in games:
        box = g.box
        other = g.opponent_of(team)
        mts = getattr(box, "team_stats", {}).get(team, {})
        ots = getattr(box, "team_stats", {}).get(other, {})
        for k, v in mts.items():
            if isinstance(v, (int, float)):
                me[k] += v
        for k, v in ots.items():
            if isinstance(v, (int, float)):
                opp[k] += v
        if getattr(box, "statbook_version", 0) >= 2:
            me["_tracked_games"] += 1
            opp["_tracked_games"] += 1
            me["_tracked_plays"] += mts.get("plays", 0)
            opp["_tracked_plays"] += ots.get("plays", 0)
        me["points"] += g.score_for(team)
        opp["points"] += g.score_for(other)
        me["sacks"] += _side_total(box, team, "sack")
        opp["sacks"] += _side_total(box, other, "sack")
        me["tfl"] += _side_total(box, team, "tfl")
        opp["tfl"] += _side_total(box, other, "tfl")
    return games, me, opp


def _pct(a, b):
    return 100.0 * a / b if b else 0.0


def values(league, team):
    games, me, opp = raw(league, team)
    n = len(games)
    pg = lambda x: x / n if n else 0.0
    plays = me.get("plays", 0)
    opp_plays = opp.get("plays", 0)
    adv_n = me.get("_tracked_games", 0)
    adv_pg = lambda x: x / adv_n if adv_n else 0.0
    adv_plays = me.get("_tracked_plays", 0)
    adv_opp_plays = opp.get("_tracked_plays", 0)
    return {
        "games": n,
        "tracked_games": adv_n,
        "ppg": pg(me["points"]),
        "opp_ppg": pg(opp["points"]),
        "total_off": pg(me["total_yds"]),
        "total_def": pg(opp["total_yds"]),
        "rush_off": pg(me["rush_yds"]),
        "rush_def": pg(opp["rush_yds"]),
        "pass_off": pg(me["pass_yds"]),
        "pass_def": pg(opp["pass_yds"]),
        "ypp": me["total_yds"] / plays if plays else 0.0,
        "opp_ypp": opp["total_yds"] / opp_plays if opp_plays else 0.0,
        "explosive": adv_pg(me["explosive_plays"]),
        "explosive_allowed": adv_pg(opp["explosive_plays"]),
        "explosive_rate": _pct(me["explosive_plays"], adv_plays),
        "explosive_rate_allowed": _pct(opp["explosive_plays"], adv_opp_plays),
        "plays20": adv_pg(me["plays_20_plus"]),
        "runs10": adv_pg(me["runs_10_plus"]),
        "passes20": adv_pg(me["passes_20_plus"]),
        "success_rate": _pct(me["successful_plays"], adv_plays),
        "success_rate_def": _pct(opp["successful_plays"], adv_opp_plays),
        "third": _pct(me["third_conv"], me["third_att"]),
        "third_def": _pct(opp["third_conv"], opp["third_att"]),
        "fourth": _pct(me["fourth_conv"], me["fourth_att"]),
        "fourth_def": _pct(opp["fourth_conv"], opp["fourth_att"]),
        "rz_td": _pct(me["red_zone_td"], me["red_zone_att"]),
        "rz_td_def": _pct(opp["red_zone_td"], opp["red_zone_att"]),
        "to_margin": pg(opp["turnovers"] - me["turnovers"]),
        "giveaways": pg(me["turnovers"]),
        "takeaways": pg(opp["turnovers"]),
        "sacks": pg(me["sacks"]),
        "sacks_allowed": pg(opp["sacks"]),
        "tfl": pg(me["tfl"]),
        "first_downs": pg(me["first_downs"]),
        "pen_yds": pg(me["pen_yds"]),
        "top": pg(me["top"]),
    }


# label, key, format, high-is-good
OFFENSE = [
    ("Scoring offense", "ppg", "{:.1f} pts/g", True),
    ("Total offense", "total_off", "{:.1f} yd/g", True),
    ("Yards per play", "ypp", "{:.2f}", True),
    ("Success rate", "success_rate", "{:.1f}%", True),
    ("Rushing offense", "rush_off", "{:.1f} yd/g", True),
    ("Passing offense", "pass_off", "{:.1f} yd/g", True),
    ("3rd-down conversion", "third", "{:.1f}%", True),
    ("4th-down conversion", "fourth", "{:.1f}%", True),
    ("Red-zone TD rate", "rz_td", "{:.1f}%", True),
    ("First downs", "first_downs", "{:.1f}/g", True),
]
EXPLOSIVE = [
    ("Explosive plays", "explosive", "{:.1f}/g", True),
    ("Explosive-play rate", "explosive_rate", "{:.1f}%", True),
    ("20+ yard plays", "plays20", "{:.1f}/g", True),
    ("Runs of 10+", "runs10", "{:.1f}/g", True),
    ("Passes of 20+", "passes20", "{:.1f}/g", True),
]
DEFENSE = [
    ("Scoring defense", "opp_ppg", "{:.1f} pts/g", False),
    ("Total defense", "total_def", "{:.1f} yd/g", False),
    ("Yards/play allowed", "opp_ypp", "{:.2f}", False),
    ("Opp. success rate", "success_rate_def", "{:.1f}%", False),
    ("Rushing defense", "rush_def", "{:.1f} yd/g", False),
    ("Passing defense", "pass_def", "{:.1f} yd/g", False),
    ("Explosives allowed", "explosive_allowed", "{:.1f}/g", False),
    ("3rd-down defense", "third_def", "{:.1f}%", False),
    ("4th-down defense", "fourth_def", "{:.1f}%", False),
    ("Red-zone TD defense", "rz_td_def", "{:.1f}%", False),
]
MISC = [
    ("Turnover margin", "to_margin", "{:+.2f}/g", True),
    ("Takeaways", "takeaways", "{:.1f}/g", True),
    ("Giveaways", "giveaways", "{:.1f}/g", False),
    ("Sacks", "sacks", "{:.1f}/g", True),
    ("Sacks allowed", "sacks_allowed", "{:.1f}/g", False),
    ("Tackles for loss", "tfl", "{:.1f}/g", True),
    ("Penalty yards", "pen_yds", "{:.1f}/g", False),
    ("Time of possession", "top", "{}", True),
]


def _eligible(league):
    vals = {}
    for t in league.teams:
        v = values(league, t)
        if v["games"]:
            vals[t] = v
    return vals


def _rank(all_vals, team, key, high_good):
    if team not in all_vals:
        return None
    ordered = sorted(all_vals, key=lambda t: all_vals[t][key], reverse=high_good)
    val = all_vals[team][key]
    # competition rank: ties share a rank
    return 1 + sum(1 for t in ordered if (all_vals[t][key] > val if high_good else all_vals[t][key] < val))


def _time(sec):
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def _rows(metrics, v, all_vals, team):
    out = []
    for label, key, fmt, good in metrics:
        rank = _rank(all_vals, team, key, good)
        val = _time(v[key]) if key == "top" else fmt.format(v[key])
        rk = f"#{rank}" if rank is not None else "—"
        rc = C.BGREEN if rank and rank <= 25 else C.BYELLOW if rank and rank <= 60 else C.GRAY
        out.append(f"{pad(label, 23)}{pad(val, 12, 'right')}   {paint(pad(rk, 5, 'right'), rc)}")
    return out


def screen(league, team):
    """A CFB-style stat profile with the team's national rank beside every number."""
    import screens
    while True:
        clear()
        color = C.BCYAN
        try:
            color = league.team_color(team)
        except Exception:
            pass
        v = values(league, team)
        all_vals = _eligible(league)
        print(title_bar(f"{team.school.upper()} · TEAM STATISTICS", color))
        print(paint(f"   {v['games']} games counted · national ranks are among FBS teams that have played", C.GRAY))
        print(paint("   Explosive play = a run of 10+ yards or a completed pass of 20+ yards.", C.BCYAN))
        if v["tracked_games"] < v["games"]:
            print(paint(f"   Advanced tracking covers {v['tracked_games']} game(s) played in v40.2+; older saved boxes still count for core stats.", C.BYELLOW))
        print()
        if not v["games"]:
            print(paint("   No games have been played yet, so there are no season statistics to rank.", C.GRAY))
        else:
            print("\n".join(columns(
                panel("OFFENSE", _rows(OFFENSE, v, all_vals, team), 50, color=color, title_color=color),
                panel("EXPLOSIVENESS", _rows(EXPLOSIVE, v, all_vals, team), 49, color=C.BMAGENTA, title_color=C.BMAGENTA), gap=1)))
            print("\n".join(columns(
                panel("DEFENSE", _rows(DEFENSE, v, all_vals, team), 50, color=C.BCYAN, title_color=C.BCYAN),
                panel("SITUATIONAL / DISCIPLINE", _rows(MISC, v, all_vals, team), 49, color=C.BYELLOW, title_color=C.BYELLOW), gap=1)))
        print()
        print(f"   {paint('[O]', C.BYELLOW)} Other team   {paint('[Enter]', C.BYELLOW)} Back")
        c = ask("Select:").strip().lower()
        if c == "o":
            other = screens.pick_team(league)
            if other is not None:
                team = other
            continue
        return
