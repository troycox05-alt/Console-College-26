"""
gameday_dossier.py — What the Campus Countdown crew knows before the show.

team_facts()  everything about one team this morning
dossier()     the featured game's storylines, ranked by how big they are
record_h2h()  called after every game so rivalries have a memory
"""
import campus_towns


# ═══ Head-to-head memory ════════════════════════════════════════════════════

def record_h2h(league, games):
    h2h = league.__dict__.setdefault("h2h", {})
    for g in games:
        if not g.played:
            continue
        key = frozenset((g.home.school, g.away.school))
        h2h.setdefault(key, []).append({"year": league.year, "week": g.week, "winner": g.winner.school,
                                        "loser": g.loser.school, "ws": g.score_for(g.winner),
                                        "ls": g.score_for(g.loser), "site": g.home.school})


def last_meeting(league, a, b, before_year=None, before_week=None):
    games = getattr(league, "h2h", {}).get(frozenset((a.school, b.school)), [])
    games = [m for m in games if (m["year"], m["week"]) < (before_year or 9999, before_week or 99)]
    return games[-1] if games else None


# ═══ One team ═══════════════════════════════════════════════════════════════

def _streak(league, team):
    kind, n = None, 0
    for g in reversed([g for g in league.team_games(team) if g.played]):
        k = "W" if g.winner is team else "L"
        if kind is None:
            kind = k
        if k != kind:
            break
        n += 1
    return kind, n


def _qb(team):
    """The quarterback who'll actually play today — not an injured starter."""
    qbs = [p for p in team.players_at("QB") if not getattr(p, "injured", False) and p not in team.injured()]
    return qbs[0] if qbs else (team.players_at("QB") or [None])[0]


def _star(team):
    best, score = None, -1
    out = set(team.injured())
    for p in team.roster:
        if p in out:
            continue
        s = p.season_stats
        v = (s["pass_yds"] * 0.05 + s["rush_yds"] * 0.1 + s["rec_yds"] * 0.1 + s["tkl"] * 1.2
             + s["sack"] * 6 + s["int"] * 8 + p.overall * 0.6)
        if v > score:
            best, score = p, v
    return best


def _defender(team):
    best, score = None, -1
    out = set(team.injured())
    for p in team.roster:
        if p in out or p.position not in ("DL", "LB", "CB", "S", "EDGE", "DE", "DT"):
            continue
        s = p.season_stats
        v = s["tkl"] + s["sack"] * 5 + s["int"] * 7 + s["tfl"] * 2 + p.overall * 0.4
        if v > score:
            best, score = p, v
    return best


def team_facts(league, t):
    R = league.rankings
    games = [g for g in league.team_games(t) if g.played]
    last = games[-1] if games else None
    n = max(1, t.wins + t.losses)
    qb = _qb(t)
    kind, streak = _streak(league, t)
    hurt = [p for p in t.injured() if p in t.players_at(p.position)[:1]]
    c = t.coach
    return {
        "school": t.school, "nick": t.nickname, "team": t, "rank": R.rank_of(t), "prev": R.previous_rank(t),
        "record": t.record, "w": t.wins, "l": t.losses, "crec": t.conf_record, "cw": t.conf_wins, "cl": t.conf_losses,
        "streak_kind": kind, "streak": streak, "ppg": t.points_for / n, "papg": t.points_against / n,
        "last": last, "last_won": (last.winner is t) if last else None,
        "last_opp": last.opponent_of(t).school if last else None,
        "last_score": f"{last.score_for(t)}-{last.score_for(last.opponent_of(t))}" if last else None,
        "qb": qb, "star": _star(t), "defender": _defender(t), "hurt": hurt,
        "coach": c.name, "seat": getattr(c, "seat", None), "hired": getattr(c, "hired_year", None),
        "first_year": getattr(c, "hired_year", None) == league.year,
        "old_schools": [s["school"] for s in getattr(c, "history", []) if s["school"] != t.school],
        "goals": getattr(t, "goals", []), "chant": t.chant, "town": campus_towns.town(t.school),
    }


# ═══ The featured game ══════════════════════════════════════════════════════

def dossier(league, g):
    """Returns (facts, storylines). Storylines are dicts with a kind, a score,
    and the data their scenes need, biggest first."""
    H, A = team_facts(league, g.home), team_facts(league, g.away)
    D = []

    def add(kind, weight, **data):
        D.append({"kind": kind, "weight": weight, **data})

    from commentary import rivalry_name
    riv = rivalry_name(g.home, g.away)
    if riv:
        add("rivalry", 90, riv=riv)
    if H["l"] == 0 and A["l"] == 0 and H["w"] >= 3 and A["w"] >= 3:
        add("unbeaten", 85, n=H["w"] + A["w"])
    if H["rank"] and A["rank"] and max(H["rank"], A["rank"]) <= 10:
        add("top10", 80)
    elif H["rank"] and A["rank"]:
        add("ranked", 55)
    for X, Y in ((H, A), (A, H)):
        if X["rank"] and not Y["rank"] and Y["team"] is g.home and not g.neutral:
            add("upset_alert", 60, fav=X["school"], dog=Y["school"], fav_rank=X["rank"])
        if X["streak_kind"] == "W" and X["streak"] >= 4:
            add("win_streak", 40 + X["streak"], team=X["school"], n=X["streak"])
        if X["streak_kind"] == "L" and X["streak"] >= 3:
            add("skid", 38 + X["streak"], team=X["school"], n=X["streak"])
        if X["prev"] and X["rank"] and X["prev"] - X["rank"] >= 5:
            add("riser", 45, team=X["school"], was=X["prev"], now=X["rank"])
        if X["prev"] and (not X["rank"] or X["rank"] - X["prev"] >= 5):
            add("faller", 45, team=X["school"], was=X["prev"], now=X["rank"] or "unranked")
        if X["last"] is not None and not X["last_won"] and X["w"] + X["l"] >= 2:
            add("bounce_back", 35, team=X["school"], opp=X["last_opp"], score=X["last_score"])
        if X["seat"] is not None and X["seat"] >= 68 and X["w"] + X["l"] >= 2:
            add("hot_seat", 55 + (X["seat"] - 68) // 2, team=X["school"], coach=X["coach"], rec=X["record"])
        if X["first_year"] and X["w"] + X["l"] >= 2:
            add("new_coach", 30, team=X["school"], coach=X["coach"], rec=X["record"])
        if Y["school"] in X["old_schools"]:
            add("coach_return", 70, team=X["school"], coach=X["coach"], old=Y["school"])
        if X["hurt"]:
            p = X["hurt"][0]
            add("injury", 50 if p.position == "QB" else 35, team=X["school"], player=p.name,
                pos=p.position, desc=getattr(p, "injury", None) or "injured")
        for p, _, blurb in league.rankings.heisman[:5]:
            if p.team is X["team"]:
                rank = [x[0] for x in league.rankings.heisman].index(p) + 1
                add("heisman", 65 - rank * 3, team=X["school"], player=p.name, hrank=rank, stats=_stat_words(p))
    qh, qa = H["qb"], A["qb"]
    if qh and qa and qh.season_stats["pass_yds"] > 900 and qa.season_stats["pass_yds"] > 900:
        add("qb_duel", 50, hqb=qh.name, aqb=qa.name, hstats=_stat_words(qh), astats=_stat_words(qa))
    if H["ppg"] >= 33 and A["ppg"] >= 33 and H["w"] + H["l"] >= 3:
        add("shootout", 45, hppg=f"{H['ppg']:.1f}", appg=f"{A['ppg']:.1f}")
    if H["papg"] <= 17 and A["papg"] <= 17 and H["w"] + H["l"] >= 3:
        add("defense_duel", 45, hpapg=f"{H['papg']:.1f}", apapg=f"{A['papg']:.1f}")
    if g.conference_game and H["cl"] <= 1 and A["cl"] <= 1 and H["cw"] + A["cw"] >= 4:
        add("conf_race", 55, conf=g.home.conference, hcrec=H["crec"], acrec=A["crec"])
    if (H["rank"] and A["rank"] and max(H["rank"], A["rank"]) <= 14 and g.week >= 8):
        add("playoff", 60)
    meet = last_meeting(league, g.home, g.away, league.year, g.week)
    if meet:
        add("revenge" if meet["loser"] in (g.home.school, g.away.school) else "rematch", 50,
            winner=meet["winner"], loser=meet["loser"], ws=meet["ws"], ls=meet["ls"], year=meet["year"])
    visits = getattr(league, "gameday", {}).get("visits", {}).get(g.home.school, [])
    if not g.neutral:
        import gameday_history
        been = bool(visits) or gameday_history.hosted_before(g.home.school)   # real-life visits count too
        add("first_visit" if not been else "return_visit", 25 if not been else 20,
            last_year=visits[-1][0] if visits else None)
    for goal in H["goals"]:
        if goal.kind == "beat_rival" and goal.param == g.away.school:
            add("goal_rival", 50, team=H["school"], rival=g.away.school)
    # trap game: a ranked team with a bigger game next week
    for X, Y in ((H, A), (A, H)):
        nxt = next((x for x in league.team_games(X["team"]) if x.week > g.week and not x.played), None)
        if nxt is not None and X["rank"] and not Y["rank"] and g.week <= 12:
            opp = nxt.opponent_of(X["team"])
            if league.rankings.rank_of(opp) or rivalry_name(X["team"], opp):
                add("trap", 42, team=X["school"], next=opp.school)
        if 4 <= X["w"] + X["l"] <= 11 and X["w"] == 5 and g.week <= 13:
            add("bowl_push", 30, team=X["school"], rec=X["record"])
    # the last time Campus Countdown came here, the home team lost
    for (yr, wk) in reversed(visits):
        prev = next((x for x in league.schedule.get(wk, []) if x.home is g.home and x.played), None) \
            if yr == league.year else None
        if prev is not None and prev.winner is not g.home:
            add("visit_curse", 40)
        break
    gap = H["team"].team_ovr - A["team"].team_ovr
    if abs(gap) >= 9:
        fav, dog = (H, A) if gap > 0 else (A, H)
        add("big_favorite", 28, fav=fav["school"], dog=dog["school"])
    stakes = {"National Championship": "The winner is the national champion.",
              "NP Semifinal": "The winner plays for the national championship.",
              "NP Quarterfinal": "Win, and you're one of the last four teams standing.",
              "NP First Round": "Win, or your season is over.",
              "Conference Championship": "The winner takes home a conference title.",
              "Bowl": "The last game of the season for both teams."}.get(g.game_type)
    if stakes:
        add("stakes", 95, round=league.week_name(league.week), stakes=stakes)
    D.sort(key=lambda s: -s["weight"])
    return H, A, D


def _stat_words(p):
    s = p.season_stats
    if p.position == "QB" and s["pass_yds"]:
        return f"{s['pass_yds']:,} yards and {s['pass_td']} touchdowns"
    if s["rush_yds"] >= s["rec_yds"] and s["rush_yds"]:
        return f"{s['rush_yds']:,} rushing yards and {s['rush_td']} touchdowns"
    if s["rec_yds"]:
        return f"{s['rec']} catches for {s['rec_yds']:,} yards"
    return f"{s['tkl']} tackles and {s['sack']:g} sacks"


# ═══ Upset Alert: find the hole ═════════════════════════════════════════════

POS_WORD = {"QB": "quarterback", "RB": "running back", "WR": "receiver", "TE": "tight end", "OL": "offensive line",
            "DL": "defensive line", "LB": "linebacker", "CB": "corner", "S": "safety"}


def _season_box(league, team):
    """Per-game averages from this season's box scores: what the stat sheet says."""
    tot = {"g": 0, "to": 0, "take": 0, "rush_alw": 0, "pass_alw": 0, "rush": 0, "pass": 0,
           "third_c": 0, "third_a": 0, "pen": 0}
    for g in league.team_games(team):
        if not g.played or g.box is None:
            continue
        ts = getattr(g.box, "team_stats", {})
        opp = g.opponent_of(team)
        me, them = ts.get(team), ts.get(opp)
        if me is None or them is None:
            continue
        tot["g"] += 1
        tot["to"] += me["turnovers"]
        tot["take"] += them["turnovers"]
        tot["rush"] += me["rush_yds"]
        tot["pass"] += me["pass_yds"]
        tot["rush_alw"] += them["rush_yds"]
        tot["pass_alw"] += them["pass_yds"]
        tot["third_c"] += me["third_conv"]
        tot["third_a"] += me["third_att"]
        tot["pen"] += me["penalties"]
    return tot


def upset_case(league, fav, dog, rng=None):
    """Reasons the underdog can win — player, coach, scheme, stat, situation.
    Returns a list of (kind, sentence), strongest first. There's always a hole somewhere."""
    import random
    rng = rng or random.Random(f"{fav.school}{dog.school}{league.year}{league.week}")
    out = []                                           # (weight, kind, sentence)
    fs, ds = fav.starters(), dog.starters()

    # ── players: where the underdog is better, man for man ──────────────
    for pos in ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S"):
        d_u, f_u = dog.unit_overall((pos,), ds), fav.unit_overall((pos,), fs)
        if d_u - f_u >= 3:
            star = max(ds[pos], key=lambda p: p.overall) if ds[pos] else None
            if pos in ("QB", "RB", "TE") and star is not None:
                out.append((d_u - f_u + 6, "player",
                            f"{dog.school} has the better {POS_WORD[pos]}. {star.name} is a problem, and {fav.school} "
                            f"hasn't seen one like him."))
            else:
                out.append((d_u - f_u + 3, "player",
                            f"{dog.school}'s {POS_WORD[pos]} group is better than {fav.school}'s. That's a real matchup edge."))
    d_front = dog.unit_overall(("DL",), ds)
    f_line = fav.unit_overall(("OL",), fs)
    if d_front - f_line >= 2:
        out.append((d_front - f_line + 5, "player",
                    f"{dog.school}'s defensive front can win against that {fav.school} offensive line. "
                    f"If they get home, it's a different game."))
    d_wr, f_cb = dog.unit_overall(("WR",), ds), fav.unit_overall(("CB",), fs)
    if d_wr - f_cb >= 3:
        out.append((d_wr - f_cb + 3, "player",
                    f"The {dog.school} receivers against the {fav.school} corners — I'd take the receivers."))
    hurt = [p for p in fav.injured() if p in fav.players_at(p.position)[:STARTER_N.get(p.position, 1)]]
    if hurt:
        p = max(hurt, key=lambda x: x.overall)
        out.append((8 + len(hurt), "player",
                    f"{fav.school} is without {p.name}" + (f" and {len(hurt) - 1} other starter{'s' if len(hurt) > 2 else ''}"
                                                            if len(hurt) > 1 else "") + ". That depth gets tested today."))

    # ── coaches ─────────────────────────────────────────────────────────
    fc, dc = fav.coach, dog.coach
    from traits import mod
    if dc is not None and fc is not None:
        if dc.overall - fc.overall >= 6:
            out.append((dc.overall - fc.overall, "coach",
                        f"{dc.name} is the better coach in this game. Give him a week to prepare and he'll have something."))
        if mod(dc, "big_game", 0.0) > 0:
            out.append((9, "coach", f"{dc.name}'s teams play up against ranked opponents. It's who he is."))
        if mod(fc, "big_game", 0.0) < 0:
            out.append((8, "coach", f"{fc.name} has a history of getting tight in big spots."))
        if getattr(fc, "hired_year", None) == league.year:
            out.append((5, "coach", f"{fc.name} is in year one at {fav.school}. The whole building is still learning him."))
        if (getattr(fc, "seat", 0) or 0) >= 70:
            out.append((6, "coach", f"The pressure on {fc.name} is real. A slow start and that stadium gets nervous."))

        # ── schemes ─────────────────────────────────────────────────────
        o = dc.offense_scheme
        if o == "Triple Option":
            out.append((12, "scheme", f"You get one week to prepare for {dog.school}'s triple option. One week. "
                                      f"Your scout team can't simulate it."))
        elif o in ("Air Raid", "Veer & Shoot") and fav.unit_overall(("CB", "S"), fs) <= dog.unit_overall(("WR",), ds) + 2:
            out.append((8, "scheme", f"{dog.school} is going to throw it fifty times. {fav.school}'s secondary hasn't "
                                     f"been tested like that."))
        elif o in ("Spread RPO", "Power Spread") and fav.unit_overall(("LB",), fs) <= 70:
            out.append((6, "scheme", f"{dog.school}'s run-pass options put {fav.school}'s linebackers in conflict on "
                                     f"every snap. Wrong read, big play."))
        elif o in ("Smashmouth", "Pro Style") and dog.unit_overall(("OL",), ds) >= fav.unit_overall(("DL",), fs):
            out.append((6, "scheme", f"{dog.school} wants to shorten this game — run it, milk the clock, keep "
                                     f"{fav.school}'s offense on the sideline."))
        d = dc.defense_scheme
        if d in ("Pressure 3-4", "3-3-5 Stack") and fs["QB"] and fs["QB"][0].overall < 75:
            out.append((7, "scheme", f"{dog.school} is going to bring pressure from everywhere, and {fav.school}'s "
                                     f"quarterback hasn't proven he can handle it."))
        if d == "3-3-5 Stack":
            out.append((4, "scheme", f"The 3-3-5 stack doesn't look like anything {fav.school} sees in its conference."))

    # ── the stat sheet ──────────────────────────────────────────────────
    F, D = _season_box(league, fav), _season_box(league, dog)
    if F["g"] >= 2 and D["g"] >= 2:
        if F["to"] / F["g"] >= 1.8:
            out.append((9, "stat", f"{fav.school} is turning it over {F['to'] / F['g']:.1f} times a game. "
                                   f"You can't do that on the road."))
        if (D["take"] - D["to"]) / D["g"] >= 1.0:
            out.append((8, "stat", f"{dog.school} is plus-{D['take'] - D['to']} in turnovers. They take the ball away."))
        if F["rush_alw"] / F["g"] >= 170 and D["rush"] / D["g"] >= 170:
            out.append((10, "stat", f"{fav.school} is giving up {F['rush_alw'] // F['g']} rushing yards a game, and "
                                    f"{dog.school} runs for {D['rush'] // D['g']}. That's the hole."))
        if F["pass_alw"] / F["g"] >= 250 and D["pass"] / D["g"] >= 250:
            out.append((10, "stat", f"{fav.school} allows {F['pass_alw'] // F['g']} passing yards a game. "
                                    f"{dog.school} throws for {D['pass'] // D['g']}."))
        if F["third_a"] and F["third_c"] / F["third_a"] < 0.36:
            out.append((6, "stat", f"{fav.school} converts {100 * F['third_c'] // F['third_a']}% on third down. "
                                   f"Get them to third-and-long and they punt."))
        if F["pen"] / F["g"] >= 8:
            out.append((5, "stat", f"{fav.school} is averaging {F['pen'] / F['g']:.0f} penalties a game. "
                                   f"Road crowds make that worse."))

    # ── the situation ───────────────────────────────────────────────────
    nxt = [g for g in league.team_games(fav) if not g.played and g.week > league.week]
    if nxt:
        opp = nxt[0].opponent_of(fav)
        if league.rankings.rank_of(opp):
            out.append((7, "situation", f"{fav.school} has No. {league.rankings.rank_of(opp)} {opp.school} next week. "
                                        f"Classic look-ahead spot."))
    last = [g for g in league.team_games(fav) if g.played]
    if last and last[-1].winner is fav and (getattr(last[-1], "ranks", {}) or {}).get(last[-1].opponent_of(fav)):
        out.append((6, "situation", f"{fav.school} is coming off a big win over a ranked team. Emotional letdown is real."))
    if dog.wins >= 1 and dog.losses == 0 and dog.wins + dog.losses >= 2:
        out.append((5, "situation", f"{dog.school} is {dog.record}. Nobody told them they're the underdog."))

    out.sort(key=lambda x: -x[0])
    seen, picked = set(), []
    for w, kind, text in out:                       # the best reason in each category first
        if kind not in seen:
            picked.append((kind, text))
            seen.add(kind)
    for w, kind, text in out:
        if (kind, text) not in picked:
            picked.append((kind, text))
    if not picked:
        picked.append(("situation", f"{dog.school} at home, and {fav.school} has to go win a road game. "
                                    f"Road games are hard. That's the whole case — but it's a real one."))
    return picked


STARTER_N = {"QB": 1, "RB": 1, "WR": 3, "TE": 1, "OL": 5, "DL": 4, "LB": 3, "CB": 2, "S": 2, "K": 1, "P": 1}
