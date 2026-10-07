"""
draft.py — Awards season and the Pro League Draft.

awards_season()  Golden Helmet, the best player at every position, freshman and coach of
                 the year, and first- and second-team All-Americans
run_draft()      underclassmen decide whether to declare, then 7 rounds and 224
                 picks. Programs that produce picks earn a prestige bonus that
                 fades over three drafts — and prestige is what recruits look at.

Both run in the offseason after the season's stats are banked and before seniors
graduate, so everything reads the finished season.
"""
import random
from collections import Counter

NFL_TEAMS = ["Arizona", "Atlanta", "Baltimore", "Buffalo", "Carolina", "Chicago", "Cincinnati", "Cleveland",
             "Dallas", "Denver", "Detroit", "Green Bay", "Houston", "Indianapolis", "Jacksonville", "Kansas City",
             "Las Vegas", "Orange County", "Los Angeles", "Miami", "Minnesota", "New England", "New Orleans",
             "New York", "Brooklyn", "Philadelphia", "Pittsburgh", "San Francisco", "Seattle", "Tampa Bay",
             "Tennessee", "Washington"]
ROUNDS = 7
PICK_VALUE = {1: 1.0, 2: 0.6, 3: 0.4, 4: 0.26, 5: 0.17, 6: 0.11, 7: 0.07}

# How much the league values each position at the top of a draft.
POS_PREMIUM = {"QB": 5, "DL": 5, "CB": 4, "OL": 3, "WR": 3, "LB": 1, "S": 1, "TE": 0, "RB": -2, "K": -14, "P": -15}
# What Pro League scouts test at each position.
ATHLETIC = {"QB": ("iq", "playmaker"), "RB": ("speed", "quickness"), "WR": ("speed", "quickness"),
            "TE": ("strength", "speed"), "OL": ("strength", "iq"), "DL": ("strength", "quickness"),
            "LB": ("speed", "strength"), "CB": ("speed", "quickness"), "S": ("speed", "iq"),
            "K": ("strength", "iq"), "P": ("strength", "iq")}

AWARD_POSITIONS = [("QB", "Best Quarterback"), ("RB", "Best Running Back"), ("WR", "Best Receiver"),
                   ("TE", "Best Tight End"), ("OL", "Best Offensive Lineman"), ("DL", "Best Defensive Lineman"),
                   ("LB", "Best Linebacker"), ("DB", "Best Defensive Back"), ("K", "Best Kicker"), ("P", "Best Punter")]
ALL_AMERICAN = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "OL": 5, "DL": 4, "LB": 3, "DB": 4, "K": 1, "P": 1}


def _stats(league, p):
    return p.yearly_stats.get(league.year, Counter())


def _group(pos):
    return "DB" if pos in ("CB", "S") else pos


def season_score(league, team, p):
    """How good was his season? Production where there are stats, the film where there aren't."""
    s = _stats(league, p)
    win = team.wins / max(1, team.wins + team.losses)
    base = p.overall * 1.1 + win * 12
    pos = p.position
    if pos == "QB":
        rating = ((8.4 * s["pass_yds"] + 330 * s["pass_td"] + 100 * s["pass_cmp"] - 200 * s["pass_int"])
                  / s["pass_att"]) if s["pass_att"] >= 100 else 0
        return base + s["pass_yds"] * 0.012 + s["pass_td"] * 1.2 + s["rush_yds"] * 0.01 + (rating - 130) * 0.25
    if pos == "RB":
        return base + s["rush_yds"] * 0.025 + s["rush_td"] * 1.5 + s["rec_yds"] * 0.01
    if pos in ("WR", "TE"):
        return base + s["rec_yds"] * 0.025 + s["rec_td"] * 1.5 + s["rec"] * 0.1
    if pos in ("DL", "LB", "CB", "S"):
        return base + s["tkl"] * 0.2 + s["sack"] * 2.5 + s["tfl"] * 1 + s["int"] * 3 + s["pbu"] * 0.6 + s["ff"] * 2
    if pos == "K":
        return base + s["fg_made"] * 1.2 - (s["fg_att"] - s["fg_made"]) * 1.5
    if pos == "P":
        return base + (s["punt_yds"] / s["punts"] - 40) * 2 if s["punts"] else base
    return base + win * 8           # linemen: the film and the wins


def _line(league, p):
    s = _stats(league, p)
    pos = p.position
    if pos == "QB" and s["pass_att"]:
        return f"{s['pass_yds']:,} yds, {s['pass_td']} TD, {s['pass_int']} INT"
    if pos == "RB" and s["rush_att"]:
        return f"{s['rush_yds']:,} rush yds, {s['rush_td']} TD"
    if pos in ("WR", "TE") and s["rec"]:
        return f"{s['rec']} rec, {s['rec_yds']:,} yds, {s['rec_td']} TD"
    if pos in ("DL", "LB", "CB", "S") and (s["tkl"] or s["sack"] or s["int"]):
        bits = [f"{s['tkl']} tkl"]
        if s["sack"]:
            bits.append(f"{s['sack']:g} sacks")
        if s["int"]:
            bits.append(f"{s['int']} INT")
        return ", ".join(bits)
    if pos == "K" and s["fg_att"]:
        return f"{s['fg_made']}/{s['fg_att']} FG"
    if pos == "P" and s["punts"]:
        return f"{s['punt_yds'] / s['punts']:.1f} avg"
    return f"{__import__('scout').ovr_plain(p)}" + ("" if __import__('scout').hidden() else " overall")


# ═══ Awards season ══════════════════════════════════════════════════════════

def awards_season(league):
    pool = [(season_score(league, t, p), p, t) for t in league.teams for p in t.roster
            if _stats(league, p) or p.position in ("OL",)]
    by_group = {}
    for sc, p, t in pool:
        by_group.setdefault(_group(p.position), []).append((sc, p, t))
    for v in by_group.values():
        v.sort(key=lambda x: -x[0])
    out = {"year": league.year, "positional": [], "first": [], "second": [], "heisman": None,
           "freshman": None, "coach": None}
    if league.rankings.heisman:
        p = league.rankings.heisman[0][0]
        out["heisman"] = (p, p.team, _line(league, p))
    for grp, name in AWARD_POSITIONS:
        if by_group.get(grp):
            sc, p, t = by_group[grp][0]
            out["positional"].append((name, p, t, _line(league, p)))
    for grp, n in ALL_AMERICAN.items():
        ranked = by_group.get(grp, [])
        out["first"] += [(grp, p, t) for _, p, t in ranked[:n]]
        out["second"] += [(grp, p, t) for _, p, t in ranked[n:2 * n]]
    fr = sorted((x for x in pool if x[1].year == 0), key=lambda x: -x[0])
    if fr:
        out["freshman"] = (fr[0][1], fr[0][2], _line(league, fr[0][1]))
    import carousel as cz
    coached = [t for t in league.teams if t.wins + t.losses and t.coach]
    if coached:
        ovrs = cz.league_ovrs(league)
        t = max(coached, key=lambda t: t.win_pct - cz.expected_pct(t, league, ovrs) + t.wins * 0.01)
        out["coach"] = (t.coach.name, t, t.record)
    # Honors go in each player's story.
    for name, p, t, _ in out["positional"]:
        p.events[league.year].append(f"Won {name}")
    for grp, p, t in out["first"]:
        p.events[league.year].append("First-team All-American")
        p.all_american = getattr(p, "all_american", 0) + 1
    for grp, p, t in out["second"]:
        p.events[league.year].append("Second-team All-American")
    if out["heisman"]:
        out["heisman"][0].events[league.year].append("Won the Golden Helmet")
    league.__dict__.setdefault("awards", {})[league.year] = out
    return out


# ═══ The Pro League Draft ══════════════════════════════════════════════════════════

def draft_grade(league, p, rng):
    """A Pro League front office's number on him: tools, position, production, honors,
    and some noise, because scouts disagree."""
    a, b = ATHLETIC.get(p.position, ("speed", "strength"))
    tools = (p.fundamentals[a] + p.fundamentals[b]) / 2
    grade = p.overall * 0.9 + tools * 0.25 + POS_PREMIUM.get(p.position, 0)
    grade += min(8, season_score(league, p.team or _team_of(league, p), p) * 0.04 - p.overall * 0.04)
    if getattr(p, "all_american", 0):
        grade += 3
    if p.year < 3:
        grade += 2                          # younger, more upside
    return grade + rng.gauss(0, 3.5)


def _team_of(league, p):
    for t in league.teams:
        if p in t.roster:
            return t
    return None


def run_draft(league, rng):
    """Underclassmen declare, then the board goes seven rounds deep.
    Drafted underclassmen leave their rosters now; seniors leave at graduation."""
    rng = random.Random(f"draft:{league.seed}:{league.year}")
    board = []
    for t in league.teams:
        for p in t.roster:
            p.team = p.team or t
            senior = p.year == 3
            eligible_early = p.year == 2 or (p.year == 1 and p.redshirt)
            if senior or eligible_early:
                board.append((draft_grade(league, p, rng), p, t, senior))
    board.sort(key=lambda x: -x[0])
    # Underclassmen decide from where they project: a likely top-two-rounder
    # usually goes, a mid-rounder sometimes, everybody else comes back.
    prospects, declared = [], []
    spots = {}
    for spot, (g, p, t, senior) in enumerate(board, 1):
        if senior:
            prospects.append((g, p, t))
            continue
        # (fringe prospects overrate themselves — some leave early and go undrafted)
        odds = (0.9 if spot <= 80 else 0.6 if spot <= 160 else 0.35 if spot <= 260 else 0.2 if spot <= 400
                else 0.06 if spot <= 520 else 0.0)
        import personalities
        odds = personalities.declare_odds(p, spot, odds)       # who he is, and what his coach told him
        spots[id(p)] = spot
        if rng.random() < odds:
            declared.append((p, t))
            prospects.append((g, p, t))
    prospects.sort(key=lambda x: -x[0])
    order = NFL_TEAMS[:]
    rng.shuffle(order)
    picks = []
    for n, (g, p, t) in enumerate(prospects[:ROUNDS * 32]):
        rnd, pick = n // 32 + 1, n % 32 + 1
        picks.append({"round": rnd, "pick": pick, "overall_pick": n + 1, "nfl": order[pick - 1 if rnd % 2 else 31 - (pick - 1)],
                      "name": p.name, "pos": p.position, "school": t.school, "ovr": p.overall,
                      "cls": p.class_label, "early": p.year < 3, "player": p})
        p.events[league.year].append(f"Drafted: round {rnd}, pick {n + 1} overall")
        p.drafted = (league.year, rnd, n + 1)
    drafted = {id(x["player"]) for x in picks}
    # Underclassmen who declared: drafted or not, they're gone.
    left = []
    for p, t in declared:
        if p in t.roster:
            t.roster.remove(p)
            left.append((p, t, id(p) in drafted))
    # Program prestige: picks in the last three drafts, most recent weighted most.
    history = league.__dict__.setdefault("drafts", {})
    history[league.year] = [{k: v for k, v in x.items() if k != "player"} for x in picks]
    for t in league.teams:
        pts = 0.0
        for yr, w in ((league.year, 1.0), (league.year - 1, 0.6), (league.year - 2, 0.35)):
            pts += w * sum(PICK_VALUE[x["round"]] for x in history.get(yr, []) if x["school"] == t.school)
        t.draft_bonus = round(min(5.0, pts * 0.9), 2)
    import personalities
    personalities.after_draft(league, declared, spots)
    return {"picks": picks, "declared": left}
